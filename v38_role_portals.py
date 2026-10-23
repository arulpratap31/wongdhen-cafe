"""V38 role-specific workspaces and owner-only *recorded* financial ledger.

The order workflow currently records requests and fulfilment, not payment settlement.
Never derive turnover or profit from it. Owner-posted revenue and expenses are
reported separately with provenance, and no invented restaurant metrics.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, select, func, Text

class LedgerEntryIn(BaseModel):
    kind: Literal['revenue','expense']
    amount_inr: Decimal = Field(gt=Decimal('0'), le=Decimal('10000000'), decimal_places=2)
    category: Literal['dine_in','takeaway','other_income','ingredients','payroll','rent','utilities','marketing','maintenance','other_expense']
    description: str = Field(min_length=3, max_length=160)
    reference: str = Field(default='',max_length=80)


def install_role_portals(app, Base, engine, Session, authenticated, owner_only, admin_write, audit,
                         StaffAccount, Contact, MenuItem, booking_models, v8_models, customer_models):
    class LedgerEntry(Base):
        __tablename__='v38_owner_finance_ledger'
        id=Column(Integer,primary_key=True)
        kind=Column(String(10),nullable=False,index=True)
        amount_paise=Column(Integer,nullable=False)
        category=Column(String(32),nullable=False)
        description=Column(String(160),nullable=False)
        reference=Column(String(80),nullable=False,default='')
        created_at=Column(DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))

    Base.metadata.create_all(engine,tables=[LedgerEntry.__table__])
    Order=v8_models['Order']; Reservation=booking_models['Reservation']; Customer=customer_models['Customer']

    def role_name(request):
        identity=authenticated(request)
        return identity['role'], identity

    def count(db,model,filter_=None):
        q=select(func.count()).select_from(model)
        if filter_ is not None:q=q.where(filter_)
        return int(db.scalar(q) or 0)

    @app.get('/api/v38/workspace/summary',tags=['V38 role workspaces'])
    def workspace_summary(request:Request):
        role,identity=role_name(request)
        with Session() as db:
            booking_counts={str(k):int(n) for k,n in db.execute(select(Reservation.status,func.count(Reservation.id)).group_by(Reservation.status))}
            order_counts={str(k):int(n) for k,n in db.execute(select(Order.status,func.count(Order.id)).group_by(Order.status))}
            result={'role':role,'display_role':{'admin':'Owner','manager':'Manager','booking_staff':'Reservations staff',
                     'kitchen_staff':'Kitchen staff','content_editor':'Content staff'}.get(role,'Staff'),
                    'capabilities':{'can_manage_team':role=='admin','can_see_finance':role=='admin',
                                    'can_see_customer_directory':role=='admin','can_oversee_service':role in ('admin','manager'),
                                    'can_manage_bookings':role in ('admin','manager','booking_staff'),
                                    'can_manage_orders':role in ('admin','manager','kitchen_staff'),
                                    'can_curate_menu':role in ('admin','manager','content_editor')},
                    'service':{},'notice':'Counts represent recorded service activity. No paid-sale amounts or guest attendance inferred.'}
            # Return only the metrics relevant to each employee's responsibilities.
            if role in ('admin','manager','booking_staff'):
                result['service']['reservations']=booking_counts
                result['service']['active_reservations']=sum(n for s,n in booking_counts.items() if s in ('pending','confirmed'))
            if role in ('admin','manager','kitchen_staff'):
                result['service']['orders']=order_counts
                result['service']['active_orders']=sum(n for s,n in order_counts.items() if s in ('placed','accepted','preparing','ready'))
            if role in ('admin','manager','content_editor'):
                result['service']['published_menu_items']=count(db,MenuItem,MenuItem.published.is_(True))
                result['service']['pending_menu_approvals']=count(db,MenuItem,MenuItem.approved.is_(False))
            if role in ('admin','manager'):
                result['service']['new_enquiries']=count(db,Contact,Contact.status=='new')
            if role=='admin':result['service']['staff_accounts']=count(db,StaffAccount,StaffAccount.active.is_(True))
            return result

    @app.get('/api/v38/workspace/manager',tags=['V38 role workspaces'])
    def manager_workspace(request:Request):
        role,_=role_name(request)
        if role not in ('admin','manager'):raise HTTPException(403,'Manager role required')
        with Session() as db:
            orders={str(k):int(n) for k,n in db.execute(select(Order.status,func.count(Order.id)).group_by(Order.status))}
            reservations={str(k):int(n) for k,n in db.execute(select(Reservation.status,func.count(Reservation.id)).group_by(Reservation.status))}
            return {'role':'manager','service':{
                'orders_waiting':sum(n for k,n in orders.items() if k in ('placed','accepted','preparing','ready')),
                'bookings_to_review':reservations.get('pending',0),
                'confirmed_bookings':reservations.get('confirmed',0),
                'new_enquiries':count(db,Contact,Contact.status=='new'),
                'published_menu_items':count(db,MenuItem,MenuItem.published.is_(True))},
                'notice':'Operational totals from the database; no financial or customer-account details.'}

    def entry_public(row):
        return {'id':row.id,'kind':row.kind,'amount_inr':str(Decimal(row.amount_paise)/100),
                'category':row.category,'description':row.description,'reference':row.reference,
                'recorded_at':row.created_at.isoformat() if row.created_at else ''}

    def finance_summary(db):
        rows=db.scalars(select(LedgerEntry).order_by(LedgerEntry.id.desc()).limit(200)).all()
        totals=dict(db.execute(select(LedgerEntry.kind,func.coalesce(func.sum(LedgerEntry.amount_paise),0)).group_by(LedgerEntry.kind)).all())
        revenue=int(totals.get('revenue',0));expense=int(totals.get('expense',0))
        since=datetime.now(timezone.utc).replace(tzinfo=None)-timedelta(days=29)
        recent=db.execute(select(LedgerEntry.kind,func.coalesce(func.sum(LedgerEntry.amount_paise),0)).where(LedgerEntry.created_at>=since).group_by(LedgerEntry.kind)).all()
        recent_totals=dict(recent)
        return {'revenue_inr':str(Decimal(revenue)/100),'expenses_inr':str(Decimal(expense)/100),
                'net_result_inr':str(Decimal(revenue-expense)/100),
                'last_30_days_revenue_inr':str(Decimal(int(recent_totals.get('revenue',0)))/100),
                'last_30_days_expenses_inr':str(Decimal(int(recent_totals.get('expense',0)))/100),
                'entries':[entry_public(r) for r in rows],
                'record_count':count(db,LedgerEntry),
                'status':'manual_ledger_only',
                'notice':'Figures include manually recorded entries only. Not POS-verified; net result is revenue minus recorded expenses, not certified accounting profit. Online orders are NOT assumed paid.'}

    @app.get('/api/v38/workspace/owner',tags=['V38 owner financial console'])
    def owner_dashboard(request:Request):
        owner_only(request)
        with Session() as db:
            return {'finance':finance_summary(db),
                    'business':{'registered_customer_accounts':count(db,Customer),
                                'total_order_requests':count(db,Order),
                                'fulfilled_order_requests':count(db,Order,Order.status=='fulfilled'),
                                'confirmed_reservations':count(db,Reservation,Reservation.status=='confirmed'),
                                'active_team_members':count(db,StaffAccount,StaffAccount.active.is_(True)),
                                'unread_enquiries':count(db,Contact,Contact.status=='new')},
                    'notice':'Registered customer accounts are not deduplicated physical visitors; order requests are not proof of payments.'}

    @app.get('/api/v38/workspace/finance',tags=['V38 owner financial console'])
    def owner_finance(request:Request):
        owner_only(request)
        with Session() as db:return finance_summary(db)

    @app.post('/api/v38/workspace/finance',status_code=201,tags=['V38 owner financial console'])
    def owner_record_entry(payload:LedgerEntryIn,request:Request):
        owner_only(request,write=True)
        if payload.kind=='revenue' and payload.category not in ('dine_in','takeaway','other_income'):
            raise HTTPException(422,'Choose a revenue category')
        if payload.kind=='expense' and payload.category in ('dine_in','takeaway','other_income'):
            raise HTTPException(422,'Choose an expense category')
        with Session() as db:
            row=LedgerEntry(kind=payload.kind,amount_paise=int(payload.amount_inr*100),category=payload.category,
                            description=payload.description.strip(),reference=payload.reference.strip())
            db.add(row);db.flush();audit(db,'v38.finance.create',f'id={row.id} type={row.kind} amount_paise={row.amount_paise}')
            db.commit()
            return {'created':True,'entry':entry_public(row)}

    @app.delete('/api/v38/workspace/finance/{entry_id}',tags=['V38 owner financial console'])
    def owner_remove_entry(entry_id:int,request:Request):
        owner_only(request,write=True)
        with Session() as db:
            row=db.get(LedgerEntry,entry_id)
            if row is None:raise HTTPException(404,'Entry not found')
            audit(db,'v38.finance.delete',f'id={row.id} type={row.kind} amount_paise={row.amount_paise}')
            db.delete(row);db.commit()
            return {'deleted':True}

    @app.get('/api/v38/workspace/customers',tags=['V38 owner customers'])
    def owner_customers(request:Request,limit:int=50):
        owner_only(request)
        with Session() as db:
            total=count(db,Customer)
            rows=db.scalars(select(Customer).order_by(Customer.id.desc()).limit(min(max(limit,1),100))).all()
            return {'total':total,'items':[{'id':r.id,'name':r.name,'email':r.email,
                       'joined_at':r.created_at.isoformat() if r.created_at else ''} for r in rows],
                    'notice':'Owner-confidential customer account directory; these are registered accounts, not verified footfall.'}

    return {'LedgerEntry':LedgerEntry}
