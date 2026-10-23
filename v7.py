"""V7 additive hospitality features. Never claims live inventory or offers without owner configuration."""
from __future__ import annotations
import hashlib, hmac, secrets, re, json
from pathlib import Path
from io import BytesIO
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from fastapi import HTTPException, Request, UploadFile, File, Form
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint, select, func
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

TZ=ZoneInfo('Asia/Kolkata')
NOW=lambda:datetime.now(TZ).replace(tzinfo=None)

class TableLayoutIn(BaseModel):
    x: float=Field(ge=0,le=100)
    y: float=Field(ge=0,le=100)
    visible: bool=True

class PairingIn(BaseModel):
    item_id:int=Field(ge=1)
    paired_item_id:int=Field(ge=1)
    enabled:bool=True
    reason:str=Field(default='',max_length=140)

class MediaIn(BaseModel):
    item_id:int=Field(ge=1)
    enabled:bool=False
    order:int=Field(default=0,ge=0,le=10000)

class QueueJoin(BaseModel):
    name:str=Field(min_length=2,max_length=120)
    party_size:int=Field(ge=1,le=50)
    phone:str=Field(default='',max_length=30)
    consent:bool=False

class QueueToken(BaseModel):
    token:str=Field(min_length=30,max_length=150)

class QueueUpdate(BaseModel):
    status:str

class OccasionIn(BaseModel):
    booking_token:str=Field(min_length=32,max_length=150)
    occasion:str=Field(max_length=60,min_length=2)
    notes:str=Field(default='',max_length=600)

class OccasionStatus(BaseModel):
    status:str

class LoyaltyJoin(BaseModel):
    name:str=Field(min_length=2,max_length=100)
    consent:bool=False

class LoyaltyToken(BaseModel):
    token:str=Field(min_length=30,max_length=150)

class LoyaltyEarn(BaseModel):
    member_id:int=Field(ge=1)
    verification_reference:str=Field(min_length=5,max_length=120)

class LoyaltyRedeem(BaseModel):
    token:str=Field(min_length=30,max_length=150)
    reward_id:int=Field(ge=1)

class RedemptionStatus(BaseModel):
    status:str

class MediaStatus(BaseModel):
    published:bool

class RewardIn(BaseModel):
    label:str=Field(min_length=3,max_length=120)
    points_required:int=Field(ge=1,le=100000)
    active:bool=False
    terms:str=Field(min_length=3,max_length=600)

class RuleIn(BaseModel):
    points_per_verified_visit:int=Field(default=0,ge=0,le=1000)
    queue_enabled:bool=False
    loyalty_enabled:bool=False

class DiscoveryQuery(BaseModel):
    dietary:str=Field(default='',max_length=30)
    egg_free:bool=False
    protein:str=Field(default='',max_length=60)


def install_v7(app,Base,engine,Session,MenuItem,booking_models,authenticated,admin_write,check_origin,throttle,audit,root:Path):
    Table=booking_models['Table'];Policy=booking_models['Policy'];Reservation=booking_models['Reservation']
    class Layout(Base):
        __tablename__='v7_table_layout'
        table_id=Column(Integer,ForeignKey('v3_dining_tables.id'),primary_key=True)
        x=Column(Integer,nullable=False);y=Column(Integer,nullable=False);visible=Column(Boolean,default=True,nullable=False)
    class Pairing(Base):
        __tablename__='v7_pairings'
        id=Column(Integer,primary_key=True)
        item_id=Column(Integer,ForeignKey('menu_items.id'),nullable=False,index=True)
        paired_item_id=Column(Integer,ForeignKey('menu_items.id'),nullable=False)
        reason=Column(String(140),default='')
        enabled=Column(Boolean,default=True,nullable=False)
        __table_args__=(UniqueConstraint('item_id','paired_item_id',name='uq_v7_pair'),)
    class Panorama(Base):
        __tablename__='v7_panoramas'
        id=Column(Integer,primary_key=True)
        path=Column(String(320),nullable=False)
        label=Column(String(100),nullable=False)
        approved=Column(Boolean,nullable=False,default=False)
    class Reel(Base):
        __tablename__='v7_reels'
        id=Column(Integer,primary_key=True)
        item_id=Column(Integer,ForeignKey('menu_items.id'),unique=True,nullable=False)
        video_path=Column(String(320),nullable=False)
        approved=Column(Boolean,nullable=False,default=False)
        sort_order=Column(Integer,default=0,nullable=False)
    class Occasion(Base):
        __tablename__='v7_occasions'
        id=Column(Integer,primary_key=True)
        reservation_id=Column(Integer,ForeignKey('v3_reservations.id'),unique=True,nullable=False)
        occasion=Column(String(60),nullable=False)
        notes=Column(String(600),default='')
        status=Column(String(30),default='pending',nullable=False)
    class Queue(Base):
        __tablename__='v7_queue'
        id=Column(Integer,primary_key=True)
        token_hash=Column(String(64),unique=True,nullable=False)
        reference=Column(String(32),unique=True,nullable=False)
        name=Column(String(120),nullable=False)
        phone=Column(String(30),default='')
        party_size=Column(Integer,nullable=False)
        status=Column(String(24),default='waiting',nullable=False)
        created_at=Column(DateTime,default=NOW,nullable=False)
        updated_at=Column(DateTime,default=NOW,nullable=False)
    class Member(Base):
        __tablename__='v7_members'
        id=Column(Integer,primary_key=True)
        token_hash=Column(String(64),unique=True,nullable=False)
        name=Column(String(100),nullable=False)
        active=Column(Boolean,default=True,nullable=False)
        created_at=Column(DateTime,default=NOW)
    class Ledger(Base):
        __tablename__='v7_loyalty_ledger'
        id=Column(Integer,primary_key=True)
        member_id=Column(Integer,ForeignKey('v7_members.id'),nullable=False,index=True)
        delta=Column(Integer,nullable=False)
        event_type=Column(String(30),nullable=False)
        event_ref=Column(String(120),nullable=False,unique=True)
        created_at=Column(DateTime,default=NOW)
    class Reward(Base):
        __tablename__='v7_rewards'
        id=Column(Integer,primary_key=True)
        label=Column(String(120),nullable=False)
        terms=Column(String(600),nullable=False)
        points_required=Column(Integer,nullable=False)
        active=Column(Boolean,default=False,nullable=False)
    class Redemption(Base):
        __tablename__='v7_redemptions'
        id=Column(Integer,primary_key=True)
        member_id=Column(Integer,ForeignKey('v7_members.id'),nullable=False)
        reward_id=Column(Integer,ForeignKey('v7_rewards.id'),nullable=False)
        ledger_id=Column(Integer,ForeignKey('v7_loyalty_ledger.id'),unique=True,nullable=False)
        status=Column(String(20),nullable=False,default='pending')
        created_at=Column(DateTime,default=NOW)
    class QueueEvent(Base):
        __tablename__='v7_queue_events'
        id=Column(Integer,primary_key=True)
        queue_id=Column(Integer,ForeignKey('v7_queue.id'),nullable=False,index=True)
        status=Column(String(24),nullable=False)
        at=Column(DateTime,nullable=False,default=NOW)
    class Rule(Base):
        __tablename__='v7_rules'
        id=Column(Integer,primary_key=True,default=1)
        points_per_verified_visit=Column(Integer,default=0,nullable=False)
        queue_enabled=Column(Boolean,default=False,nullable=False)
        loyalty_enabled=Column(Boolean,default=False,nullable=False)
    Base.metadata.create_all(engine,tables=[m.__table__ for m in (Layout,Pairing,Panorama,Reel,Occasion,Queue,Member,Ledger,Reward,Redemption,QueueEvent,Rule)])
    with Session() as db:
        if db.get(Rule,1) is None: db.add(Rule(id=1));db.commit()
    sha=lambda t:hashlib.sha256(t.encode()).hexdigest()
    def lock(db):
        if engine.dialect.name=='sqlite':db.connection().exec_driver_sql('BEGIN IMMEDIATE')
    def balance(db,member_id):
        return int(db.scalar(select(func.coalesce(func.sum(Ledger.delta),0)).where(Ledger.member_id==member_id)) or 0)
    def approved_item(db,id):
        item=db.get(MenuItem,id)
        if not item or not item.published:raise HTTPException(404,'Dish not found')
        return item
    def public_item(db,row):
        return {'id':row.id,'name':row.name,'category':row.category,'price_display':row.price_display,
                'price_confirmed':bool(row.approved)}

    @app.get('/api/v7/experience/status')
    def experience_status():
        with Session() as db:
            rules=db.get(Rule,1)
            return {'queue_enabled':rules.queue_enabled,'loyalty_enabled':rules.loyalty_enabled,
                    'panoramas':db.scalar(select(func.count(Panorama.id)).where(Panorama.approved.is_(True))),
                    'reels':db.scalar(select(func.count(Reel.id)).where(Reel.approved.is_(True)))}

    @app.get('/api/v7/tables')
    def public_tables(visit_date:date,visit_time:str,party_size:int=1):
        if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',visit_time):raise HTTPException(422,'Invalid time')
        with Session() as db:
            p=db.get(Policy,1)
            live=bool(p and p.enabled and p.owner_verified and p.opening and p.closing and p.opening<p.closing)
            if not live: return {'enabled':False,'tables':[],'note':'Live table selection is unavailable; contact café staff for booking arrangements.'}
            today=NOW().date()
            if visit_date<today or visit_date>today+timedelta(days=p.horizon_days):raise HTTPException(422,'Outside booking date range')
            if party_size<1 or party_size>p.max_party_size:raise HTTPException(422,'Invalid party size')
            if visit_date.weekday() in {int(x) for x in p.closed_weekdays.split(',') if x}:raise HTTPException(422,'Closed weekday')
            if visit_date.isoformat() in {x.strip() for x in p.blackout_dates.split(',') if x.strip()}:raise HTTPException(422,'Blackout date')
            start=datetime.fromisoformat(f'{visit_date}T{visit_time}');end=start+timedelta(minutes=p.duration_minutes)
            if start<NOW()+timedelta(minutes=p.minimum_notice_minutes) or start.hour*60+start.minute < int(p.opening[:2])*60+int(p.opening[3:]) or end.time()>datetime.strptime(p.closing,'%H:%M').time():
                raise HTTPException(422,'Time outside allowed reservation windows')
            minutes=int(visit_time[:2])*60+int(visit_time[3:])-(int(p.opening[:2])*60+int(p.opening[3:]))
            if minutes%p.slot_minutes:raise HTTPException(422,'Time is not a configured booking slot')
            occupied=set(db.scalars(select(Reservation.table_id).where(Reservation.status.in_(('pending','confirmed','checked_in','seated')),Reservation.start_at<end,Reservation.end_at>start)).all())
            layouts={l.table_id:l for l in db.scalars(select(Layout)).all()}
            data=[]
            for t in db.scalars(select(Table).order_by(Table.id)):
                l=layouts.get(t.id)
                data.append({'id':t.id,'label':t.label,'area':t.area,'seats':t.seats,
                    'available':bool(t.active and t.seats>=party_size and t.id not in occupied),
                    'x':l.x if l and l.visible else None,'y':l.y if l and l.visible else None})
            return {'enabled':True,'tables':data,'exact_table_request_supported':True,'status':'Pending until staff confirms reservation',
                    'layout_configured':any(t['x'] is not None for t in data)}

    @app.put('/api/v7/admin/tables/{table_id}/layout')
    def save_layout(table_id:int,payload:TableLayoutIn,request:Request):
        admin_write(request)
        with Session() as db:
            if not db.get(Table,table_id):raise HTTPException(404,'Unknown table')
            l=db.get(Layout,table_id)
            if not l:l=Layout(table_id=table_id);db.add(l)
            l.x=round(payload.x);l.y=round(payload.y);l.visible=payload.visible
            audit(db,'v7.layout',f'table={table_id}');db.commit()
            return {'saved':True}

    @app.get('/api/v7/admin/tables/layout')
    def admin_table_layout(request:Request):
        authenticated(request)
        with Session() as db:
            rows=db.scalars(select(Layout).order_by(Layout.table_id)).all()
            return {'positions':[{'table_id':x.table_id,'x':x.x,'y':x.y,'visible':x.visible} for x in rows]}

    @app.get('/api/v7/pairings/{item_id}')
    def get_pairings(item_id:int):
        with Session() as db:
            approved_item(db,item_id)
            rows=db.scalars(select(Pairing).where(Pairing.item_id==item_id,Pairing.enabled.is_(True)).order_by(Pairing.id).limit(10)).all()
            from sqlalchemy import text
            d=db.execute(text('SELECT dietary_class,dietary_verified,egg_verified,contains_egg FROM menu_item_details_v6 WHERE menu_item_id=:id'),{'id':item_id}).first()
            matches=[]
            for pair in rows:
                r=db.get(MenuItem,pair.paired_item_id)
                if not r or not r.published:continue
                rd=db.execute(text('SELECT dietary_class,dietary_verified,egg_verified,contains_egg FROM menu_item_details_v6 WHERE menu_item_id=:id'),{'id':r.id}).first()
                # If the main item has verified dietary/egg restrictions, never suggest a conflicting or unverified alternative.
                if d and d[1] and d[0]=='vegan' and (not rd or not rd[1] or rd[0]!='vegan'):continue
                if d and d[1] and d[0]=='vegetarian' and (not rd or not rd[1] or rd[0] not in ('vegetarian','vegan')):continue
                if d and d[2] and not bool(d[3]) and (not rd or not rd[2] or bool(rd[3])):continue
                matches.append({**public_item(db,r),'reason':pair.reason})
            return {'pairs':matches,'status':'Owner-curated relationships only'}

    @app.get('/api/v7/admin/pairings')
    def get_admin_pairs(request:Request):
        authenticated(request)
        with Session() as db:return {'pairs':[{'id':x.id,'item_id':x.item_id,'paired_item_id':x.paired_item_id,'reason':x.reason,'enabled':x.enabled} for x in db.scalars(select(Pairing).order_by(Pairing.id.desc()).limit(200)).all()]}

    @app.post('/api/v7/admin/pairings')
    def add_pair(payload:PairingIn,request:Request):
        admin_write(request)
        if payload.item_id==payload.paired_item_id:raise HTTPException(422,'Select two different dishes')
        with Session() as db:
            approved_item(db,payload.item_id);approved_item(db,payload.paired_item_id)
            existing=db.scalar(select(Pairing).where(Pairing.item_id==payload.item_id,Pairing.paired_item_id==payload.paired_item_id))
            if existing:raise HTTPException(409,'Pairing already exists')
            db.add(Pairing(**payload.model_dump()));audit(db,'v7.pairing',f'{payload.item_id}->{payload.paired_item_id}');db.commit();return {'saved':True}

    @app.delete('/api/v7/admin/pairings/{pair_id}')
    def delete_pair(pair_id:int,request:Request):
        admin_write(request)
        with Session() as db:
            p=db.get(Pairing,pair_id)
            if not p:raise HTTPException(404,'Not found')
            db.delete(p);audit(db,'v7.pair.delete',str(pair_id));db.commit();return {'deleted':True}

    @app.get('/api/v7/discover')
    def discover(dietary:str='',egg_free:bool=False,protein:str='',limit:int=30):
        if dietary not in ('','vegetarian','vegan','non_vegetarian'):raise HTTPException(422,'Unsupported dietary filter')
        from sqlalchemy import text
        with Session() as db:
            if not dietary and not egg_free and not protein:
                rows=db.scalars(select(MenuItem).where(MenuItem.published.is_(True)).order_by(MenuItem.category,MenuItem.name).limit(max(1,min(limit,100)))).all()
                return {'items':[public_item(db,x) for x in rows],'strict_verification':True,'note':'Unfiltered browse: dietary information is not inferred.'}
            clauses=['m.published = :yes']
            bind={'yes':True}
            if dietary:
                clauses.append('d.dietary_verified = :yes AND d.dietary_class = :dietary')
                bind['dietary']=dietary
            if egg_free: clauses.append('d.egg_verified = :yes AND d.contains_egg = :no');bind['no']=False
            if protein: clauses.append('d.protein_verified = :yes')
            stmt=text('SELECT m.id, d.protein_sources FROM menu_items m JOIN menu_item_details_v6 d ON d.menu_item_id=m.id WHERE '+' AND '.join(clauses)+' ORDER BY m.id LIMIT 2000')
            records=db.execute(stmt,bind).all()
            if protein:
                records=[r for r in records if protein.lower() in {str(v).lower() for v in json.loads(r[1] or '[]')}]
            records=records[:max(1,min(limit,100))]
            return {'items':[public_item(db,db.get(MenuItem,r[0])) for r in records], 'strict_verification':True,
                    'note':'Strictly owner-verified dietary and protein attributes; unknown items are excluded from filtered results.'}

    @app.get('/api/v7/tour')
    def tour():
        with Session() as db:
            rows=db.scalars(select(Panorama).where(Panorama.approved.is_(True)).order_by(Panorama.id)).all()
            return {'scenes':[{'id':x.id,'label':x.label,'image':x.path} for x in rows],
                    'note':'Genuine owner-approved 360° panoramas only. Gallery remains available otherwise.'}

    @app.post('/api/v7/admin/tour')
    async def upload_tour(request:Request,file:UploadFile=File(...),label:str=Form(...),rights_confirmed:bool=Form(False),genuine_panorama:bool=Form(False)):
        admin_write(request)
        if not rights_confirmed or not genuine_panorama:raise HTTPException(422,'Real panorama and commercial rights confirmation required')
        if not 2<=len(label.strip())<=100:raise HTTPException(422,'Scene label required')
        data=await file.read(12_000_001)
        if len(data)>12_000_000:raise HTTPException(413,'Image exceeds 12 MB')
        try:
            image=Image.open(BytesIO(data));image.verify();image=Image.open(BytesIO(data)).convert('RGB')
        except (OSError,ValueError,UnidentifiedImageError):raise HTTPException(422,'Invalid image')
        if image.width*image.height>40_000_000 or not 1.95<=image.width/image.height<=2.05:
            raise HTTPException(422,'Equirectangular panorama must be approximately 2:1')
        filename='pano-'+secrets.token_hex(12)+'.webp';directory=root/'static'/'v7';directory.mkdir(exist_ok=True)
        image.thumbnail((4096,2048));image.save(directory/filename,'WEBP',quality=85)
        with Session() as db:
            row=Panorama(path='/static/v7/'+filename,label=label.strip(),approved=True);db.add(row)
            audit(db,'v7.tour.upload',filename);db.commit();return {'id':row.id,'saved':True}

    @app.put('/api/v7/admin/tour/{scene_id}/publish')
    def publish_tour(scene_id:int,payload:MediaStatus,request:Request):
        admin_write(request)
        with Session() as db:
            r=db.get(Panorama,scene_id)
            if not r: raise HTTPException(404,'Scene not found')
            r.approved=payload.published;audit(db,'v7.panorama.publish',f'{scene_id}:{r.approved}');db.commit()
            return {'saved':True}

    @app.get('/api/v7/admin/tour')
    def admin_tour(request:Request):
        authenticated(request)
        with Session() as db:
            return {'scenes':[{'id':r.id,'label':r.label,'published':r.approved} for r in db.scalars(select(Panorama).order_by(Panorama.id)).all()]}

    @app.get('/api/v7/reels')
    def reels():
        with Session() as db:
            rows=db.scalars(select(Reel).where(Reel.approved.is_(True)).order_by(Reel.sort_order,Reel.id)).all()
            live=[]
            for x in rows:
                item=db.get(MenuItem,x.item_id)
                if item and item.published:live.append({**public_item(db,item),'video':x.video_path})
            return {'reels':live,'note':'Only owner-approved, item-specific footage appears here.'}

    @app.post('/api/v7/admin/reels')
    async def upload_reel(request:Request,file:UploadFile=File(...),item_id:int=Form(...),rights_confirmed:bool=Form(False),exact_item_confirmed:bool=Form(False)):
        admin_write(request)
        if not rights_confirmed or not exact_item_confirmed:raise HTTPException(422,'Exact item and usage rights must be confirmed')
        with Session() as db:approved_item(db,item_id)
        if file.content_type!='video/mp4':raise HTTPException(422,'Only MP4 supported')
        payload=await file.read(20_000_001)
        if len(payload)>20_000_000:raise HTTPException(413,'Maximum video size 20 MB')
        if not (len(payload)>12 and payload[4:8]==b'ftyp'):raise HTTPException(422,'Invalid MP4 container')
        dirname=root/'static'/'v7';dirname.mkdir(exist_ok=True)
        name='reel-'+secrets.token_hex(12)+'.mp4';(dirname/name).write_bytes(payload)
        with Session() as db:
            row=db.scalar(select(Reel).where(Reel.item_id==item_id))
            old=row.video_path if row else ''
            if not row:row=Reel(item_id=item_id,video_path='/static/v7/'+name);db.add(row)
            row.video_path='/static/v7/'+name;row.approved=True
            audit(db,'v7.reel.upload',str(item_id));db.commit()
        # Old media retained for administrative reconciliation/backup; not deleted automatically.
        return {'saved':True,'item_id':item_id}

    @app.get('/api/v7/admin/reels')
    def admin_reels(request:Request):
        authenticated(request)
        with Session() as db:
            return {'reels':[{'id':r.id,'item_id':r.item_id,'published':r.approved} for r in db.scalars(select(Reel).order_by(Reel.id)).all()]}

    @app.put('/api/v7/admin/reels/{id}/publish')
    def reel_publish(id:int,payload:MediaStatus,request:Request):
        admin_write(request)
        with Session() as db:
            r=db.get(Reel,id)
            if not r:raise HTTPException(404,'Reel not found')
            r.approved=payload.published;audit(db,'v7.reel.publish',f'{id}:{r.approved}');db.commit()
            return {'saved':True}

    @app.post('/api/v7/occasions')
    def occasion_create(payload:OccasionIn,request:Request):
        throttle(request,'v7_occ',6,600);check_origin(request)
        with Session() as db:
            reservation=db.scalar(select(Reservation).where(Reservation.token_hash==sha(payload.booking_token)))
            if not reservation:raise HTTPException(404,'Reservation token not found')
            if reservation.status in ('cancelled','declined','completed','no_show'):
                raise HTTPException(409,'Occasion request unavailable for this booking status')
            # An occasion is a request for consideration only, not a guaranteed service.
            row=db.scalar(select(Occasion).where(Occasion.reservation_id==reservation.id))
            if row and row.status=='approved':raise HTTPException(409,'Approved arrangements require staff assistance to modify')
            if row:row.occasion=payload.occasion.strip();row.notes=payload.notes.strip();row.status='pending'
            else:db.add(Occasion(reservation_id=reservation.id,occasion=payload.occasion.strip(),notes=payload.notes.strip()))
            audit(db,'v7.occasion.request',reservation.reference);db.commit()
            return {'saved':True,'status':'pending','message':'Special arrangement request received, not approved or priced. Staff will review.'}

    @app.post('/api/v7/occasions/status')
    def occasion_status(payload:LoyaltyToken,request:Request):
        throttle(request,'v7_occasion_status',16,300);check_origin(request)
        with Session() as db:
            reservation=db.scalar(select(Reservation).where(Reservation.token_hash==sha(payload.token)))
            if not reservation:raise HTTPException(404,'Booking token not found')
            row=db.scalar(select(Occasion).where(Occasion.reservation_id==reservation.id))
            return {'status':row.status if row else 'not_requested','occasion':row.occasion if row else None,
                    'notice':'Special arrangements are separate from table booking confirmation.'}

    @app.get('/api/v7/admin/occasions')
    def occasion_admin(request:Request):
        authenticated(request)
        with Session() as db:
            data=[]
            for r in db.scalars(select(Occasion).order_by(Occasion.id.desc()).limit(150)).all():
                b=db.get(Reservation,r.reservation_id)
                data.append({'id':r.id,'reservation_reference':b.reference if b else '', 'occasion':r.occasion,'notes':r.notes,'status':r.status})
            return {'occasions':data}

    @app.patch('/api/v7/admin/occasions/{id}')
    def occasion_change(id:int,payload:OccasionStatus,request:Request):
        admin_write(request)
        if payload.status not in ('pending','approved','unavailable','cancelled'):raise HTTPException(422,'Invalid status')
        with Session() as db:
            row=db.get(Occasion,id)
            if not row:raise HTTPException(404,'Unknown request')
            row.status=payload.status;audit(db,'v7.occasion.update',f'{id}:{row.status}');db.commit()
            return {'saved':True,'status':row.status}

    def queue_public(row):
        return {'reference':row.reference,'status':row.status,'party_size':row.party_size,
                'queue_position':None,'estimated_wait_minutes':None,
                'note':'Queue position and wait time are not estimated. Contact the café if called.'}

    @app.post('/api/v7/queue')
    def join_queue(payload:QueueJoin,request:Request):
        throttle(request,'v7_queue',3,600);check_origin(request)
        if not payload.consent:raise HTTPException(422,'Consent is required')
        if payload.phone and not re.fullmatch(r'[+\d ()-]{7,30}',payload.phone):raise HTTPException(422,'Invalid phone number')
        with Session() as db:
            if not db.get(Rule,1).queue_enabled:raise HTTPException(503,'Walk-in queue is not active')
            token=secrets.token_urlsafe(40)
            row=Queue(name=payload.name.strip(),phone=payload.phone.strip(),party_size=payload.party_size,
                      reference='WQ-'+secrets.token_hex(6).upper(),token_hash=sha(token))
            db.add(row);db.flush();db.add(QueueEvent(queue_id=row.id,status='waiting'));audit(db,'v7.queue.join',row.reference);db.commit()
            return {'token':token,'queue':queue_public(row),'message':'Your entry is waiting; this is not a table reservation.'}

    @app.post('/api/v7/queue/status')
    def queue_status(payload:QueueToken,request:Request):
        throttle(request,'v7_queue_status',20,300);check_origin(request)
        with Session() as db:
            row=db.scalar(select(Queue).where(Queue.token_hash==sha(payload.token)))
            if not row:raise HTTPException(404,'No queue entry found')
            if row.created_at.date()<NOW().date() and row.status in ('waiting','called','arrived'):
                row.status='expired';row.updated_at=NOW();db.add(QueueEvent(queue_id=row.id,status='expired'));db.commit()
            events=db.scalars(select(QueueEvent).where(QueueEvent.queue_id==row.id).order_by(QueueEvent.id)).all()
            return {'queue':queue_public(row),'history':[{'status':x.status,'at':x.at.isoformat()} for x in events]}

    @app.post('/api/v7/queue/cancel')
    def queue_cancel(payload:QueueToken,request:Request):
        throttle(request,'v7_queue_cancel',5,300);check_origin(request)
        with Session() as db:
            lock(db)
            row=db.scalar(select(Queue).where(Queue.token_hash==sha(payload.token)))
            if not row:raise HTTPException(404,'No queue entry found')
            if row.status not in ('waiting','called'):raise HTTPException(409,'Entry cannot be cancelled')
            row.status='cancelled';row.updated_at=NOW();db.add(QueueEvent(queue_id=row.id,status='cancelled'));audit(db,'v7.queue.cancel',row.reference);db.commit()
            return {'queue':queue_public(row)}

    @app.get('/api/v7/admin/queue')
    def admin_queue(request:Request):
        authenticated(request)
        with Session() as db:
            today=NOW().date()
            rows=db.scalars(select(Queue).where(Queue.created_at>=datetime.combine(today,datetime.min.time())).order_by(Queue.id.desc()).limit(200)).all()
            return {'queue':[{'id':x.id,'reference':x.reference,'name':x.name,'phone':x.phone,'party_size':x.party_size,'status':x.status} for x in rows]}

    @app.patch('/api/v7/admin/queue/{id}')
    def admin_queue_update(id:int,payload:QueueUpdate,request:Request):
        admin_write(request)
        transitions={'waiting':{'called','cancelled','expired'},'called':{'arrived','waiting','cancelled','expired'},
                     'arrived':{'seated','cancelled','expired'},'seated':set(),'cancelled':set(),'expired':set()}
        with Session() as db:
            lock(db)
            row=db.get(Queue,id)
            if not row:raise HTTPException(404,'Queue entry not found')
            if payload.status not in transitions[row.status]:raise HTTPException(409,'Invalid queue transition')
            row.status=payload.status;row.updated_at=NOW();db.add(QueueEvent(queue_id=row.id,status=row.status));audit(db,'v7.queue.update',row.reference+':'+row.status);db.commit()
            return {'saved':True,'status':row.status}

    @app.get('/api/v7/admin/rules')
    def get_rules(request:Request):
        authenticated(request)
        with Session() as db:
            r=db.get(Rule,1)
            return {k:getattr(r,k) for k in RuleIn.model_fields}

    @app.put('/api/v7/admin/rules')
    def put_rules(payload:RuleIn,request:Request):
        admin_write(request)
        with Session() as db:
            r=db.get(Rule,1)
            for k,v in payload.model_dump().items():setattr(r,k,v)
            audit(db,'v7.rules.update',str(payload.model_dump()));db.commit()
            return {'saved':True}

    @app.post('/api/v7/loyalty/join')
    def member_join(payload:LoyaltyJoin,request:Request):
        throttle(request,'v7_loyalty_join',3,1800);check_origin(request)
        if not payload.consent:raise HTTPException(422,'Consent required for optional membership')
        with Session() as db:
            if not db.get(Rule,1).loyalty_enabled:raise HTTPException(503,'Loyalty program not active')
            token=secrets.token_urlsafe(40)
            member=Member(name=payload.name.strip(),token_hash=sha(token));db.add(member)
            audit(db,'v7.loyalty.join','new membership');db.commit()
            return {'token':token,'member_id':member.id,'balance':0,'message':'Save this private member access token to return to your rewards.'}

    @app.post('/api/v7/loyalty/me')
    def loyalty_me(payload:LoyaltyToken,request:Request):
        throttle(request,'v7_loyalty_lookup',20,300);check_origin(request)
        with Session() as db:
            member=db.scalar(select(Member).where(Member.token_hash==sha(payload.token),Member.active.is_(True)))
            if not member:raise HTTPException(404,'Membership not found')
            rewards=db.scalars(select(Reward).where(Reward.active.is_(True)).order_by(Reward.id)).all()
            return {'member_id':member.id,'name':member.name,'balance':balance(db,member.id),
                    'rewards':[{'id':r.id,'label':r.label,'points_required':r.points_required,'terms':r.terms} for r in rewards]}

    @app.get('/api/v7/admin/loyalty')
    def loyalty_admin(request:Request):
        authenticated(request)
        with Session() as db:
            members=db.scalars(select(Member).order_by(Member.id.desc()).limit(100)).all()
            redemptions=db.scalars(select(Redemption).order_by(Redemption.id.desc()).limit(100)).all()
            return {'members':[{'id':r.id,'name':r.name,'active':r.active,'balance':balance(db,r.id)} for r in members],
                'rewards':[{'id':r.id,'label':r.label,'points_required':r.points_required,'active':r.active,'terms':r.terms} for r in db.scalars(select(Reward).order_by(Reward.id)).all()],
                'redemptions':[{'id':r.id,'member_id':r.member_id,'reward_id':r.reward_id,'status':r.status} for r in redemptions]}

    @app.post('/api/v7/admin/loyalty/earn')
    def loyalty_earn(payload:LoyaltyEarn,request:Request):
        admin_write(request)
        with Session() as db:
            lock(db)
            r=db.get(Rule,1);member=db.get(Member,payload.member_id)
            if not r.loyalty_enabled or r.points_per_verified_visit<1:raise HTTPException(503,'Staff reward issuance not enabled')
            if not member or not member.active:raise HTTPException(404,'Active membership not found')
            ref='visit:'+payload.verification_reference.strip()
            if db.scalar(select(Ledger).where(Ledger.event_ref==ref)):raise HTTPException(409,'Verified visit already counted')
            db.add(Ledger(member_id=member.id,delta=r.points_per_verified_visit,event_type='staff_verified_visit',event_ref=ref))
            audit(db,'v7.loyalty.earn',f'member={member.id},reference={ref}');db.commit()
            return {'saved':True,'balance':balance(db,member.id)}

    @app.post('/api/v7/admin/loyalty/rewards')
    def reward_add(payload:RewardIn,request:Request):
        admin_write(request)
        with Session() as db:
            row=Reward(**payload.model_dump());db.add(row);audit(db,'v7.reward.create',row.label);db.commit()
            return {'saved':True,'id':row.id}

    @app.post('/api/v7/loyalty/redeem')
    def redeem(payload:LoyaltyRedeem,request:Request):
        throttle(request,'v7_loyalty_redeem',6,600);check_origin(request)
        with Session() as db:
            lock(db)
            member=db.scalar(select(Member).where(Member.token_hash==sha(payload.token),Member.active.is_(True)))
            reward=db.get(Reward,payload.reward_id)
            if not member:raise HTTPException(404,'Membership not found')
            if not db.get(Rule,1).loyalty_enabled or not reward or not reward.active:raise HTTPException(409,'Reward not currently available')
            if balance(db,member.id)<reward.points_required:raise HTTPException(409,'Insufficient points')
            ledger=Ledger(member_id=member.id,delta=-reward.points_required,event_type='redemption_requested',event_ref='redeem:'+secrets.token_hex(16))
            db.add(ledger);db.flush();redemption=Redemption(member_id=member.id,reward_id=reward.id,ledger_id=ledger.id,status='pending');db.add(redemption)
            audit(db,'v7.loyalty.redeem',f'member={member.id},reward={reward.id}');db.commit()
            return {'status':'redemption_requested','redemption_id':redemption.id,'message':'Redemption request recorded. Show the result to staff for fulfillment; no physical reward is guaranteed by this message.','balance':balance(db,member.id)}

    @app.patch('/api/v7/admin/loyalty/redemptions/{id}')
    def update_redemption(id:int,payload:RedemptionStatus,request:Request):
        admin_write(request)
        if payload.status not in ('fulfilled','declined'):raise HTTPException(422,'Invalid outcome')
        with Session() as db:
            lock(db)
            r=db.get(Redemption,id)
            if not r:raise HTTPException(404,'Unknown redemption')
            if r.status!='pending':raise HTTPException(409,'Redemption was already handled')
            if payload.status=='declined':
                prior=db.get(Ledger,r.ledger_id)
                db.add(Ledger(member_id=r.member_id,delta=-prior.delta,event_type='redemption_refund',event_ref='refund:'+str(r.id)))
            r.status=payload.status;audit(db,'v7.loyalty.redemption',f'{id}:{r.status}');db.commit()
            return {'saved':True,'status':r.status,'balance':balance(db,r.member_id)}

    @app.post('/api/v7/loyalty/leave')
    def leave(payload:LoyaltyToken,request:Request):
        throttle(request,'v7_loyalty_leave',4,600);check_origin(request)
        with Session() as db:
            member=db.scalar(select(Member).where(Member.token_hash==sha(payload.token)))
            if not member:raise HTTPException(404,'Membership not found')
            member.active=False;audit(db,'v7.loyalty.optout',str(member.id));db.commit()
            return {'left':True}

    return {'tables_layout':Layout,'queue':Queue,'loyalty':Member}
