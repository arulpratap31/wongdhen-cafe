"""Wongdhen Café V8: additive, source-of-truth commercial workflows.

No fake product availability, payments, or order fulfillment. The owner configures
ordering and item stock via authenticated endpoints. V7 tables are preserved.
"""
from __future__ import annotations
import csv, io, hashlib, hmac, secrets, re, json, os, base64
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from decimal import Decimal, InvalidOperation
from typing import Literal
from fastapi import HTTPException, Request
from fastapi.responses import Response, PlainTextResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, select, func

UTC=lambda:datetime.now(timezone.utc).replace(tzinfo=None)
STATES={'untracked','available','sold_out','paused','hidden'}
ORDER_NEXT={'placed':{'accepted','cancelled'},'accepted':{'preparing','cancelled'},'preparing':{'ready','cancelled'},'ready':{'fulfilled','cancelled'},'fulfilled':set(),'cancelled':set()}

class StockInput(BaseModel):
    status:Literal['untracked','available','sold_out','paused','hidden']
class CommerceSettings(BaseModel):
    enabled:bool=False
    fulfill_mode:Literal['pickup','dine_in']='pickup'
    instructions:str=Field(default='',max_length=400)
class OrderLineIn(BaseModel):
    item_id:int=Field(ge=1)
    quantity:int=Field(ge=1,le=20)
class PlaceOrder(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    contact:str=Field(min_length=5,max_length=140)
    notes:str=Field(default='',max_length=350)
    consent:bool=False
    idempotency_key:str=Field(min_length=16,max_length=100)
    table_code:str|None=Field(default=None,max_length=400)
    items:list[OrderLineIn]=Field(min_length=1,max_length=20)
class PrivateToken(BaseModel):
    token:str=Field(min_length=32,max_length=150)
class OrderChange(BaseModel):
    status:Literal['accepted','preparing','ready','fulfilled','cancelled']
class EventIn(BaseModel):
    event:Literal['menu_open','dish_open','booking_start','booking_complete','compare_open','order_start','order_complete','pairing_open']
    item_id:int|None=Field(default=None,ge=1)
class GroupIn(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    contact:str=Field(min_length=5,max_length=150)
    requested_date:str=Field(min_length=10,max_length=10)
    party_size:int=Field(ge=6,le=200)
    notes:str=Field(default='',max_length=1000)
    consent:bool=False
class CheckinRequest(BaseModel):
    code:str=Field(min_length=20,max_length=400)
class PromoIn(BaseModel):
    eyebrow:str=Field(default="",max_length=75)
    headline:str=Field(min_length=3,max_length=120)
    detail:str=Field(default="",max_length=230)
    link_label:str=Field(default="EXPLORE THE MENU",max_length=60)
    link_path:str=Field(default="/menu",max_length=130)
    active:bool=False
class GroupStatus(BaseModel):
    status:Literal['new','contacted','closed']


def install_v8(app,Base,engine,Session,MenuItem,booking_models,visual_details,authenticated,admin_write,throttle,audit,session_key):
    checkin_signer=URLSafeTimedSerializer(session_key,salt='wongdhen-v8-checkin-pass')
    table_signer=URLSafeTimedSerializer(session_key,salt='wongdhen-v8-table-order')
    class MenuStock(Base):
        __tablename__='v8_menu_stock'
        menu_item_id=Column(Integer,ForeignKey('menu_items.id'),primary_key=True)
        status=Column(String(25),nullable=False,default='untracked')
        updated_at=Column(DateTime,default=UTC)
    class TableAccess(Base):
        __tablename__='v8_table_qr'
        table_id=Column(Integer,ForeignKey('v3_dining_tables.id'),primary_key=True)
        nonce_hash=Column(String(64),nullable=False)
        enabled=Column(Boolean,default=True,nullable=False)
    class TableOrder(Base):
        __tablename__='v8_order_table'
        order_id=Column(Integer,ForeignKey('v8_orders.id'),primary_key=True)
        table_id=Column(Integer,ForeignKey('v3_dining_tables.id'),nullable=False)
    class OrderConfig(Base):
        __tablename__='v8_order_config'
        id=Column(Integer,primary_key=True)
        enabled=Column(Boolean,default=False,nullable=False)
        fulfill_mode=Column(String(20),default='pickup',nullable=False)
        instructions=Column(String(400),default='',nullable=False)
    class Order(Base):
        __tablename__='v8_orders'
        id=Column(Integer,primary_key=True)
        reference=Column(String(36),unique=True,nullable=False)
        token_hash=Column(String(64),unique=True,nullable=False)
        idempotency_key=Column(String(100),unique=True,nullable=False)
        name=Column(String(120),nullable=False)
        contact=Column(String(140),nullable=False)
        notes=Column(String(350),nullable=False,default='')
        status=Column(String(24),nullable=False,default='placed')
        mode=Column(String(20),nullable=False)
        total_paise=Column(Integer,nullable=False)
        items_json=Column(Text,nullable=False)
        created_at=Column(DateTime,default=UTC)
    class OrderEvent(Base):
        __tablename__='v8_order_events'
        id=Column(Integer,primary_key=True)
        order_id=Column(Integer,ForeignKey('v8_orders.id'),nullable=False)
        status=Column(String(24),nullable=False)
        created_at=Column(DateTime,default=UTC)
    class GroupInquiry(Base):
        __tablename__='v8_group_inquiries'
        id=Column(Integer,primary_key=True)
        token_hash=Column(String(64),unique=True,nullable=False)
        reference=Column(String(30),unique=True,nullable=False)
        name=Column(String(100),nullable=False)
        contact=Column(String(150),nullable=False)
        requested_date=Column(String(10),nullable=False)
        party_size=Column(Integer,nullable=False)
        notes=Column(String(1000),default='',nullable=False)
        status=Column(String(25),default='new',nullable=False)
        created_at=Column(DateTime,default=UTC)
    class VisitEvent(Base):
        __tablename__='v8_aggregate_events'
        id=Column(Integer,primary_key=True)
        event=Column(String(40),nullable=False,index=True)
        item_id=Column(Integer,nullable=True)
        created_at=Column(DateTime,default=UTC,index=True)
    class Promo(Base):
        __tablename__='v8_home_promo'
        id=Column(Integer,primary_key=True)
        eyebrow=Column(String(75),nullable=False,default='')
        headline=Column(String(120),nullable=False)
        detail=Column(String(230),nullable=False,default='')
        link_label=Column(String(60),nullable=False,default='')
        link_path=Column(String(130),nullable=False,default='/menu')
        active=Column(Boolean,nullable=False,default=False)
    Base.metadata.create_all(engine)
    with Session() as db:
        if db.get(OrderConfig,1) is None:
            db.add(OrderConfig(id=1));db.commit()

    def lock(db):
        if engine.dialect.name=='sqlite':
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')
        else:
            db.execute(select(OrderConfig).where(OrderConfig.id==1).with_for_update()).first()
    def state(db,item_id):
        x=db.get(MenuStock,item_id)
        return x.status if x else 'untracked'
    def paise(price_display):
        # Reject ambiguous sizes, currencies, slashes and unapproved variants.
        raw=price_display.strip().replace(',','')
        m=re.fullmatch(r'(?:₹\s*)?(\d{1,6})(?:\.(\d{1,2}))?',raw)
        if not m:return None
        d=Decimal(m.group(1)+('.'+m.group(2) if m.group(2) else ''))
        value=int(d*100)
        return value if 0<value<=10000000 else None
    def table_for_code(db,code):
        DiningTable=booking_models['Table']
        try:value=table_signer.loads(code,max_age=366*86400)
        except (BadSignature,SignatureExpired):raise HTTPException(403,'Invalid or expired table QR reference')
        if not isinstance(value,dict) or not isinstance(value.get('id'),int) or not isinstance(value.get('nonce'),str):
            raise HTTPException(403,'Invalid table QR reference')
        ref=db.get(TableAccess,value['id']);table=db.get(DiningTable,value['id'])
        if not ref or not ref.enabled or not table or not table.active or not hmac.compare_digest(ref.nonce_hash,hashlib.sha256(value['nonce'].encode()).hexdigest()):
            raise HTTPException(403,'This table QR reference is inactive')
        return table

    def order_public(row):
        return {'reference':row.reference,'status':row.status,'mode':row.mode,'items':json.loads(row.items_json),
                'total_paise':row.total_paise,'currency':'INR','payment_status':'not_collected_online',
                'created_at':row.created_at.isoformat() if row.created_at else ''}

    @app.get('/api/v8/promo')
    def public_promo():
        with Session() as db:
            row=db.scalar(select(Promo).where(Promo.active.is_(True)).order_by(Promo.id.desc()))
            return {'promotion':None if row is None else {'eyebrow':row.eyebrow,'headline':row.headline,
                    'detail':row.detail,'link_label':row.link_label,'link_path':row.link_path}}

    @app.get('/api/v8/admin/promo')
    def owner_promo(request:Request):
        authenticated(request)
        with Session() as db:
            row=db.get(Promo,1)
            return {'promotion':None if row is None else {'eyebrow':row.eyebrow,'headline':row.headline,'detail':row.detail,
                  'link_label':row.link_label,'link_path':row.link_path,'active':row.active}}

    @app.put('/api/v8/admin/promo')
    def save_promo(payload:PromoIn,request:Request):
        admin_write(request)
        if not re.fullmatch(r'/(?:[a-z0-9][a-z0-9/-]{0,125})?',payload.link_path):
            raise HTTPException(422,'Promotional link must be a local public page')
        with Session() as db:
            row=db.get(Promo,1)
            if not row:row=Promo(id=1);db.add(row)
            for k,v in payload.model_dump().items():setattr(row,k,v)
            audit(db,'v8.promo.update',row.headline)
            db.commit();return {'saved':True}

    @app.get('/api/v8/status')
    def v8_status():
        with Session() as db:
            c=db.get(OrderConfig,1)
            tracked=db.scalar(select(func.count(MenuStock.menu_item_id)).where(MenuStock.status!='untracked'))
            return {'edition':'V8 commercial development','online_ordering_enabled':c.enabled,
                    'fulfillment_mode':c.fulfill_mode,'tracked_menu_items':tracked,
                    'payment_gateway_connected':False,'guest_portal':False,
                    'ordering_notice':'Orders are recorded for staff fulfillment; no payment is collected on this website.'}

    @app.get('/api/v8/compare')
    def compare(ids:str=''):
        try: keys=list(dict.fromkeys(int(x) for x in ids.split(',') if x.strip()))
        except ValueError:raise HTTPException(422,'Expected numeric menu item IDs')
        if not 1<=len(keys)<=4:raise HTTPException(422,'Select 1–4 dishes to compare')
        with Session() as db:
            found={x.id:x for x in db.scalars(select(MenuItem).where(MenuItem.id.in_(keys),MenuItem.published.is_(True))).all()}
            if len(found)!=len(keys):raise HTTPException(404,'One or more dishes unavailable')
            Detail=visual_details['model']
            result=[]
            for key in keys:
                item=found[key];detail=db.scalar(select(Detail).where(Detail.menu_item_id==key))
                result.append({'id':item.id,'name':item.name,'category':item.category,'price_display':item.price_display,
                  'price_confirmed':bool(item.approved),'availability':state(db,key),
                  'details':visual_details['serialize'](detail)})
            return {'items':result}

    @app.get('/api/v8/menu-stock')
    def stock_list():
        with Session() as db:
            return {'items':[{'item_id':x.menu_item_id,'status':x.status} for x in db.scalars(select(MenuStock).where(MenuStock.status!='untracked')).all()],
                    'note':'Untracked items have no asserted real-time stock status.'}

    @app.put('/api/v8/admin/menu-stock/{item_id}')
    def set_stock(item_id:int,payload:StockInput,request:Request):
        admin_write(request)
        with Session() as db:
            if not db.get(MenuItem,item_id):raise HTTPException(404,'Unknown menu item')
            entry=db.get(MenuStock,item_id)
            if entry is None:entry=MenuStock(menu_item_id=item_id);db.add(entry)
            entry.status=payload.status;entry.updated_at=UTC();audit(db,'v8.stock.update',f'{item_id}:{payload.status}')
            db.commit();return {'saved':True,'item_id':item_id,'status':payload.status}

    @app.get('/api/v8/ordering/config')
    def ordering_config():
        with Session() as db:
            c=db.get(OrderConfig,1)
            return {'enabled':c.enabled,'fulfill_mode':c.fulfill_mode,'instructions':c.instructions,
                    'payment_available':False,'payment_method':'pay_at_cafe'}

    @app.put('/api/v8/admin/ordering/config')
    def set_ordering_config(payload:CommerceSettings,request:Request):
        admin_write(request)
        with Session() as db:
            row=db.get(OrderConfig,1)
            for k,v in payload.model_dump().items():setattr(row,k,v)
            audit(db,'v8.ordering.configure',f'enabled={payload.enabled} mode={payload.fulfill_mode}')
            db.commit();return {'saved':True}

    @app.get('/api/v8/admin/tables/qr')
    def admin_table_qr_list(request:Request):
        authenticated(request)
        DiningTable=booking_models['Table']
        with Session() as db:
            rows=db.scalars(select(DiningTable).order_by(DiningTable.id)).all()
            return {'tables':[{'id':t.id,'label':t.label,'active':t.active,
                       'qr_enabled':bool((r:=db.get(TableAccess,t.id)) and r.enabled)} for t in rows]}

    @app.post('/api/v8/admin/tables/{table_id}/qr')
    def activate_table_qr(table_id:int,request:Request):
        admin_write(request)
        DiningTable=booking_models['Table']
        with Session() as db:
            table=db.get(DiningTable,table_id)
            if not table or not table.active:raise HTTPException(404,'Active café table not found')
            nonce=secrets.token_urlsafe(32)
            rec=db.get(TableAccess,table_id)
            if rec is None:rec=TableAccess(table_id=table_id);db.add(rec)
            rec.nonce_hash=hashlib.sha256(nonce.encode()).hexdigest();rec.enabled=True
            code=table_signer.dumps({'id':table_id,'nonce':nonce})
            base=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
            qr_value=base+'/order#table='+code if base.startswith('https://') else 'WONGDHEN-TABLE:'+code
            import qrcode
            image=qrcode.make(qr_value);output=io.BytesIO();image.save(output,format='PNG')
            audit(db,'v8.table.qr.rotate',f'table {table_id}')
            db.commit()
            return {'table_id':table.id,'label':table.label,'table_code':code,
                    'qr_data_url':'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode(),
                    'qr_value':qr_value,'note':'Previous QR codes for this table are invalidated.'}

    @app.post('/api/v8/ordering/table/verify')
    def verify_table_code(payload:CheckinRequest,request:Request):
        throttle(request,'v8_table_verify',30,60)
        with Session() as db:
            table=table_for_code(db,payload.code)
            return {'table_id':table.id,'table_label':table.label,'active':True}

    @app.get('/api/v8/ordering/catalog')
    def ordering_catalog():
        with Session() as db:
            config=db.get(OrderConfig,1)
            if not config.enabled:return {'enabled':False,'items':[]}
            rows=db.scalars(select(MenuItem).where(MenuItem.published.is_(True),MenuItem.approved.is_(True)).order_by(MenuItem.category,MenuItem.name)).all()
            return {'enabled':True,'items':[{'id':x.id,'name':x.name,'category':x.category,'price_paise':paise(x.price_display),
                                           'stock':state(db,x.id)} for x in rows if state(db,x.id)=='available' and paise(x.price_display) is not None]}

    @app.post('/api/v8/ordering/orders')
    def place_order(payload:PlaceOrder,request:Request):
        throttle(request,'v8_order',4,60)
        if not payload.consent:raise HTTPException(422,'Order contact consent is required')
        # Hash the client-generated key to prevent sensitive tokens in idempotency index.
        idem=hashlib.sha256(payload.idempotency_key.encode()).hexdigest()
        if len({x.item_id for x in payload.items})!=len(payload.items):raise HTTPException(422,'Merge duplicate item IDs')
        with Session() as db:
            lock(db)
            old=db.scalar(select(Order).where(Order.idempotency_key==idem))
            if old:raise HTTPException(409,'Order already submitted. Use the private receipt returned by the first successful request.')
            config=db.get(OrderConfig,1)
            if not config.enabled:raise HTTPException(409,'Ordering is currently unavailable')
            table=None
            if config.fulfill_mode=='dine_in':
                if not payload.table_code:raise HTTPException(422,'Scan the QR code for an active café table before submitting a dine-in order')
                table=table_for_code(db,payload.table_code)
            lines=[];total=0
            for line in payload.items:
                item=db.get(MenuItem,line.item_id)
                if not item or not item.published or not item.approved or state(db,item.id)!='available':
                    raise HTTPException(409,f'Dish {line.item_id} is not available for ordering')
                unit=paise(item.price_display)
                if unit is None:raise HTTPException(409,f'Dish {item.id} does not have a single confirmed price')
                sub=unit*line.quantity;total+=sub
                lines.append({'id':item.id,'name':item.name,'quantity':line.quantity,'unit_paise':unit,'subtotal_paise':sub})
            if total>10_000_000:raise HTTPException(422,'Order exceeds supported maximum')
            token=secrets.token_urlsafe(40)
            order=Order(reference='WC8-'+secrets.token_hex(6).upper(),token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        idempotency_key=idem,name=payload.name.strip(),contact=payload.contact.strip(),notes=payload.notes.strip(),
                        mode=config.fulfill_mode,total_paise=total,items_json=json.dumps(lines),status='placed')
            db.add(order);db.flush()
            if table:db.add(TableOrder(order_id=order.id,table_id=table.id))
            db.add(OrderEvent(order_id=order.id,status='placed'))
            audit(db,'v8.order.create',order.reference);db.commit()
            return {'order':dict(order_public(order),table_label=table.label if table else None),'private_token':token,'message':'Order received in staff dashboard; payment has not been collected.'}

    @app.post('/api/v8/ordering/track')
    def track_order(payload:PrivateToken,request:Request):
        throttle(request,'v8_order_tracking',30,60)
        with Session() as db:
            row=db.scalar(select(Order).where(Order.token_hash==hashlib.sha256(payload.token.encode()).hexdigest()))
            if row is None:raise HTTPException(404,'Order reference not found')
            return {'order':dict(order_public(row),table_label=table_label(db,row.id))}

    def table_label(db,order_id):
        link=db.get(TableOrder,order_id)
        table=db.get(booking_models['Table'],link.table_id) if link else None
        return table.label if table else None

    @app.get('/api/v8/admin/orders')
    def admin_orders(request:Request):
        identity=authenticated(request)
        with Session() as db:
            rows=db.scalars(select(Order).order_by(Order.id.desc()).limit(200)).all()
            # Managers and kitchen staff do not receive financial totals or full customer profiles.
            # Item-level fulfilment details are operational, not payment confirmation.
            if identity['role'] in ('manager','kitchen_staff'):
                return {'orders':[{'id':x.id,'reference':x.reference,'status':x.status,
                       'mode':x.mode,'table_label':table_label(db,x.id),
                       'items':[{'id':line.get('id'),'name':line.get('name'),'quantity':line.get('quantity')}
                                  for line in json.loads(x.items_json or '[]')],
                       **({'name':x.name} if identity['role']=='manager' else {})} for x in rows],
                       'privacy':'Guest contact information and monetary totals are reserved for owner access.'}
            return {'orders':[dict(order_public(x),id=x.id,name=x.name,contact=x.contact,notes=x.notes,table_label=table_label(db,x.id)) for x in rows]}

    @app.patch('/api/v8/admin/orders/{order_id}')
    def update_order(order_id:int,payload:OrderChange,request:Request):
        admin_write(request)
        with Session() as db:
            lock(db)
            row=db.get(Order,order_id)
            if not row:raise HTTPException(404,'Unknown order')
            if payload.status not in ORDER_NEXT[row.status]:raise HTTPException(409,'Invalid order status transition')
            row.status=payload.status;db.add(OrderEvent(order_id=row.id,status=payload.status))
            audit(db,'v8.order.status',f'{row.reference}:{payload.status}')
            db.commit();return {'saved':True,'order':order_public(row)}

    @app.post('/api/v8/booking/checkin-pass')
    def guest_checkin_pass(payload:PrivateToken,request:Request):
        throttle(request,'v8_checkin_pass',10,60)
        Reservation=booking_models['Reservation']
        hashed=hashlib.sha256(payload.token.encode()).hexdigest()
        with Session() as db:
            reservation=db.scalar(select(Reservation).where(Reservation.token_hash==hashed))
            if reservation is None:raise HTTPException(404,'Booking not found')
            if reservation.status!='confirmed':raise HTTPException(409,'A confirmed booking is required for check-in')
            code=checkin_signer.dumps({'reservation_id':reservation.id,'reference':reservation.reference})
            target=(os.environ.get('PUBLIC_BASE_URL','').rstrip('/')+'/checkin?code='+code)
            if not target.startswith('https://'):target='WONGDHEN-CHECKIN:'+code
            try:
                import qrcode
                img=qrcode.make(target)
                image_buffer=io.BytesIO();img.save(image_buffer,format='PNG')
                qr='data:image/png;base64,'+base64.b64encode(image_buffer.getvalue()).decode()
            except ImportError:qr=None
            return {'reference':reservation.reference,'checkin_code':code,'qr_data_url':qr,
                    'status':reservation.status,'note':'Staff verification is needed on arrival. QR is not proof of completed check-in.'}

    @app.post('/api/v8/admin/booking/checkin')
    def owner_checkin(payload:CheckinRequest,request:Request):
        admin_write(request)
        Reservation=booking_models['Reservation']
        try:verified=checkin_signer.loads(payload.code,max_age=30*86400)
        except (BadSignature,SignatureExpired):raise HTTPException(404,'Invalid or expired check-in pass')
        if not isinstance(verified,dict) or not isinstance(verified.get('reservation_id'),int):
            raise HTTPException(404,'Invalid pass')
        with Session() as db:
            lock(db)
            r=db.get(Reservation,verified['reservation_id'])
            if not r or r.reference!=verified.get('reference'):raise HTTPException(404,'Booking not found')
            if r.status!='confirmed':raise HTTPException(409,'Only confirmed bookings can be checked in once')
            from zoneinfo import ZoneInfo
            if r.start_at.date()!=datetime.now(ZoneInfo('Asia/Kolkata')).date():
                raise HTTPException(409,'Check-in is only available on the reservation date')
            r.status='checked_in';audit(db,'v8.booking.checkin',r.reference);db.commit()
            return {'reference':r.reference,'status':r.status,'guest_name':r.name}

    @app.post('/api/v8/groups')
    def group_request(payload:GroupIn,request:Request):
        throttle(request,'v8_group',3,300)
        if not payload.consent:raise HTTPException(422,'Contact consent is required')
        try:visit=datetime.strptime(payload.requested_date,'%Y-%m-%d').date()
        except ValueError:raise HTTPException(422,'Invalid date')
        if visit<datetime.now(ZoneInfo('Asia/Kolkata')).date():raise HTTPException(422,'Choose a future date')
        token=secrets.token_urlsafe(40)
        with Session() as db:
            row=GroupInquiry(reference='WCG-'+secrets.token_hex(6).upper(),token_hash=hashlib.sha256(token.encode()).hexdigest(),
                             **{k:v for k,v in payload.model_dump().items() if k!='consent'})
            db.add(row);audit(db,'v8.group.request',row.reference);db.commit()
            return {'reference':row.reference,'status':row.status,'private_token':token,'message':'Group enquiry saved; no seating or service is guaranteed.'}

    @app.post('/api/v8/groups/track')
    def group_track(payload:PrivateToken,request:Request):
        throttle(request,'v8_group_track',15,60)
        with Session() as db:
            row=db.scalar(select(GroupInquiry).where(GroupInquiry.token_hash==hashlib.sha256(payload.token.encode()).hexdigest()))
            if row is None:raise HTTPException(404,'Inquiry not found')
            return {'reference':row.reference,'status':row.status,'date':row.requested_date}

    @app.get('/api/v8/admin/groups')
    def admin_groups(request:Request):
        authenticated(request)
        with Session() as db:
            rows=db.scalars(select(GroupInquiry).order_by(GroupInquiry.id.desc()).limit(200)).all()
            return {'inquiries':[{'id':x.id,'reference':x.reference,'date':x.requested_date,'name':x.name,
                'party_size':x.party_size,'contact':x.contact,'notes':x.notes,'status':x.status} for x in rows]}

    @app.patch('/api/v8/admin/groups/{inquiry_id}')
    def change_group(inquiry_id:int,payload:GroupStatus,request:Request):
        admin_write(request)
        with Session() as db:
            row=db.get(GroupInquiry,inquiry_id)
            if not row:raise HTTPException(404,'Unknown inquiry')
            row.status=payload.status;audit(db,'v8.group.status',f'{row.reference}:{row.status}')
            db.commit();return {'saved':True,'status':row.status}

    @app.post('/api/v8/analytics/event')
    def analytics_event(payload:EventIn,request:Request):
        throttle(request,'v8_analytics',40,60)
        with Session() as db:
            db.add(VisitEvent(event=payload.event,item_id=payload.item_id));db.commit()
        return {'saved':True}

    @app.get('/api/v8/admin/overview')
    def admin_overview(request:Request):
        authenticated(request)
        Reservation=booking_models['Reservation']
        with Session() as db:
            order_counts=dict(db.execute(select(Order.status,func.count(Order.id)).group_by(Order.status)).all())
            group_counts=dict(db.execute(select(GroupInquiry.status,func.count(GroupInquiry.id)).group_by(GroupInquiry.status)).all())
            event_counts=dict(db.execute(select(VisitEvent.event,func.count(VisitEvent.id)).group_by(VisitEvent.event)).all())
            return {'metrics':{'menu_items':db.scalar(select(func.count(MenuItem.id))),
                 'verified_prices':db.scalar(select(func.count(MenuItem.id)).where(MenuItem.approved.is_(True))),
                 'confirmed_reservations':db.scalar(select(func.count(Reservation.id)).where(Reservation.status=='confirmed')),
                 'orders':order_counts,'group_inquiries':group_counts,'events':event_counts},
                 'note':'Engagement events are interaction counts, not transactions or unique people.'}

    @app.get('/api/v8/admin/content-health')
    def content_health(request:Request):
        authenticated(request)
        Detail=visual_details['model']
        with Session() as db:
            rows=db.scalars(select(MenuItem).order_by(MenuItem.id)).all()
            details={x.menu_item_id:x for x in db.scalars(select(Detail)).all()}
            result=[]
            for item in rows:
                d=details.get(item.id)
                missing=[]
                if not item.approved:missing.append('current_price')
                if not d or not (d.image_exact_verified and d.image_rights_confirmed and d.image_path):missing.append('exact_photo')
                if not d or not d.ingredients_verified:missing.append('ingredients')
                if not d or not d.dietary_verified:missing.append('dietary')
                if not d or not d.allergens_verified:missing.append('allergens')
                if missing:result.append({'id':item.id,'name':item.name,'missing':missing})
            return {'total':len(rows),'incomplete':len(result),'items':result}

    @app.get('/api/v8/admin/export/orders.csv')
    def export_orders(request:Request):
        authenticated(request)
        buffer=io.StringIO();writer=csv.writer(buffer)
        writer.writerow(['reference','status','mode','total_inr','created_at'])
        with Session() as db:
            for x in db.scalars(select(Order).order_by(Order.id.desc())).all():
                writer.writerow([x.reference,x.status,x.mode,str(Decimal(x.total_paise)/100),x.created_at])
        return Response('\ufeff'+buffer.getvalue(),media_type='text/csv; charset=utf-8',headers={
          'Content-Disposition':'attachment; filename="wongdhen-v8-orders.csv"','Cache-Control':'no-store'})

    return {'MenuStock':MenuStock,'Order':Order,'GroupInquiry':GroupInquiry,'OrderConfig':OrderConfig,'Promo':Promo}
