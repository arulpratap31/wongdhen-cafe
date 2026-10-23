"""Wongdhen V3 reservation operations.

Owner-configured capacity only. Public reservations are disabled until real table
inventory, hours, and operating policy are explicitly verified by the owner.
The transaction-critical operation locks the SQLite writer (BEGIN IMMEDIATE) or
PostgreSQL table inventory (SELECT FOR UPDATE) before checking for overlaps.
"""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, func, select

TZ = ZoneInfo('Asia/Kolkata')
BLOCKING = ('pending','confirmed','checked_in','seated')
STATUSES = {'pending','confirmed','checked_in','seated','completed','cancelled','declined','no_show'}
TRANSITIONS = {
    'pending': {'confirmed','declined','cancelled'},
    'confirmed': {'checked_in','cancelled','no_show'},
    'checked_in': {'seated','cancelled','no_show'},
    'seated': {'completed'},
    'completed': set(), 'cancelled': set(), 'declined': set(), 'no_show': set()
}

class PolicyInput(BaseModel):
    enabled: bool = False
    owner_verified: bool = False
    opening: str = Field(default='', max_length=5)
    closing: str = Field(default='', max_length=5)
    slot_minutes: int = Field(default=30, ge=15, le=120)
    duration_minutes: int = Field(default=90, ge=30, le=300)
    minimum_notice_minutes: int = Field(default=60, ge=0, le=10080)
    horizon_days: int = Field(default=30, ge=1, le=120)
    max_party_size: int = Field(default=12, ge=1, le=100)
    closed_weekdays: str = Field(default='', max_length=20)
    blackout_dates: str = Field(default='', max_length=1000)

    @field_validator('opening','closing')
    @classmethod
    def time_string(cls, v):
        if v and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',v):
            raise ValueError('Use 24-hour HH:MM times')
        return v

    @field_validator('closed_weekdays')
    @classmethod
    def weekdays(cls,v):
        if v.strip() and not all(x.strip() in tuple(str(i) for i in range(7)) for x in v.split(',')):
            raise ValueError('Closed weekdays must be 0–6, separated by commas (Monday=0)')
        return v.strip()

    @field_validator('blackout_dates')
    @classmethod
    def blackout(cls,v):
        if v.strip():
            for s in v.split(','):
                try: date.fromisoformat(s.strip())
                except ValueError: raise ValueError('Blackout dates must be YYYY-MM-DD, comma separated')
        return v.strip()

class DateExceptionInput(BaseModel):
    """Owner-entered one-day opening-hours exception, never enabled automatically."""
    closed: bool = False
    opening: str = Field(default='', max_length=5)
    closing: str = Field(default='', max_length=5)
    note: str = Field(default='', max_length=180)

    @field_validator('opening', 'closing')
    @classmethod
    def valid_hours(cls, value):
        if value and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', value):
            raise ValueError('Time must use 24-hour HH:MM')
        return value


class TableInput(BaseModel):
    label: str = Field(min_length=1,max_length=50)
    seats: int = Field(ge=1, le=50)
    area: str = Field(default='Main dining',min_length=1,max_length=100)
    active: bool = True

class BookingInput(BaseModel):
    visit_date: date
    visit_time: str
    party_size: int = Field(ge=1,le=100)
    name: str = Field(min_length=2,max_length=120)
    email: str = Field(min_length=5,max_length=200)
    phone: str = Field(min_length=7,max_length=30)
    notes: str = Field(default='',max_length=500)
    consent: bool = False
    website: str = Field(default='',max_length=200)
    table_id: int | None = Field(default=None,ge=1)  # Optional V7 exact table request

    @field_validator('visit_time')
    @classmethod
    def time_format(cls,v):
        if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',v):
            raise ValueError('Invalid booking time')
        return v

class BookingToken(BaseModel):
    token: str = Field(min_length=32,max_length=150)

class RescheduleInput(BaseModel):
    token: str = Field(min_length=32,max_length=150)
    visit_date: date
    visit_time: str = Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    table_id: int | None = Field(default=None, ge=1)

class BookingStatusInput(BaseModel):
    status: str
    table_id: int | None = None

class WaitlistInput(BaseModel):
    visit_date: date
    preferred_time: str = Field(default='',max_length=5)
    party_size: int = Field(ge=1,le=100)
    name: str = Field(min_length=2,max_length=120)
    email: str = Field(min_length=5,max_length=200)
    phone: str = Field(min_length=7,max_length=30)
    consent: bool = False

class StatusInput(BaseModel):
    status: str

class WalkinInput(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    party_size: int = Field(ge=1,le=100)
    phone: str = Field(default='',max_length=30)


def install_reservations(app, Base, engine, Session, authenticated, admin_write, throttle, check_origin, audit):
    """Mount the V3 booking API without rewriting existing app or menu storage."""

    class BookingPolicy(Base):
        __tablename__ = 'v3_booking_policy'
        id = Column(Integer, primary_key=True, default=1)
        enabled = Column(Boolean, default=False, nullable=False)
        owner_verified = Column(Boolean, default=False, nullable=False)
        opening = Column(String(5), default='', nullable=False)
        closing = Column(String(5), default='', nullable=False)
        slot_minutes = Column(Integer,default=30,nullable=False)
        duration_minutes = Column(Integer,default=90,nullable=False)
        minimum_notice_minutes = Column(Integer,default=60,nullable=False)
        horizon_days = Column(Integer,default=30,nullable=False)
        max_party_size = Column(Integer,default=12,nullable=False)
        closed_weekdays = Column(String(20),default='',nullable=False)
        blackout_dates = Column(Text,default='',nullable=False)

    class DateException(Base):
        __tablename__ = 'v23_booking_date_exceptions'
        visit_date = Column(String(10), primary_key=True)
        closed = Column(Boolean, default=False, nullable=False)
        opening = Column(String(5), default='', nullable=False)
        closing = Column(String(5), default='', nullable=False)
        note = Column(String(180), default='', nullable=False)
        updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class DiningTable(Base):
        __tablename__ = 'v3_dining_tables'
        id = Column(Integer, primary_key=True)
        label = Column(String(50),unique=True,nullable=False)
        seats = Column(Integer,nullable=False)
        area = Column(String(100),nullable=False)
        active = Column(Boolean,nullable=False,default=True)

    class Reservation(Base):
        __tablename__ = 'v3_reservations'
        id = Column(Integer,primary_key=True)
        reference = Column(String(30),nullable=False,unique=True,index=True)
        token_hash = Column(String(64),nullable=False,unique=True,index=True)
        table_id = Column(Integer,ForeignKey('v3_dining_tables.id'),nullable=False,index=True)
        start_at = Column(DateTime,nullable=False,index=True)  # restaurant local Asia/Kolkata
        end_at = Column(DateTime,nullable=False)
        party_size = Column(Integer,nullable=False)
        name = Column(String(120),nullable=False)
        email = Column(String(200),nullable=False)
        phone = Column(String(30),nullable=False)
        notes = Column(String(500),nullable=False,default='')
        status = Column(String(30),nullable=False,default='pending',index=True)
        created_at = Column(DateTime,nullable=False,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None))

    class BookingEvent(Base):
        __tablename__ = 'v3_booking_events'
        id = Column(Integer,primary_key=True)
        reservation_id = Column(Integer,ForeignKey('v3_reservations.id'),nullable=False,index=True)
        action = Column(String(80),nullable=False)
        detail = Column(String(300),nullable=False,default='')
        created_at = Column(DateTime,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None))

    class Waitlist(Base):
        __tablename__ = 'v3_waitlist'
        id = Column(Integer,primary_key=True)
        reference = Column(String(30),unique=True,nullable=False)
        visit_date = Column(String(10),nullable=False)
        preferred_time = Column(String(5),nullable=False,default='')
        party_size = Column(Integer,nullable=False)
        name = Column(String(120),nullable=False)
        email = Column(String(200),nullable=False)
        phone = Column(String(30),nullable=False)
        status = Column(String(20),default='waiting',nullable=False)
        created_at = Column(DateTime,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None))

    class Walkin(Base):
        __tablename__ = 'v3_walkins'
        id = Column(Integer,primary_key=True)
        name = Column(String(120),nullable=False)
        party_size = Column(Integer,nullable=False)
        phone = Column(String(30),default='')
        status = Column(String(20),default='waiting',nullable=False)
        created_at = Column(DateTime,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None))

    Base.metadata.create_all(engine)
    with Session() as db:
        if db.get(BookingPolicy,1) is None:
            db.add(BookingPolicy(id=1))
            db.commit()

    router = APIRouter(prefix='/api/v3',tags=['V3 Reservations'])

    def policy_dict(p):
        return {k:getattr(p,k) for k in PolicyInput.model_fields}

    def configured(p):
        return bool(p.enabled and p.owner_verified and p.opening and p.closing and p.opening < p.closing)

    def available_tables(db, start, end, party_size, lock=False, exclude_id=None):
        query=select(DiningTable).where(DiningTable.active.is_(True),DiningTable.seats>=party_size).order_by(DiningTable.seats,DiningTable.id)
        if lock and not engine.dialect.name.startswith('sqlite'):
            query=query.with_for_update()
        tables=db.scalars(query).all()
        occupied=select(Reservation.table_id).where(
            Reservation.status.in_(BLOCKING),
            Reservation.start_at < end,
            Reservation.end_at > start,
        )
        if exclude_id is not None:
            occupied=occupied.where(Reservation.id != exclude_id)
        reserved=set(db.scalars(occupied).all())
        return [t for t in tables if t.id not in reserved]

    def slot_start(d:date, s:str):
        return datetime.fromisoformat(f'{d.isoformat()}T{s}')

    def resolve_day(db, p, date_value):
        """Return effective opening hours and closure state for a real calendar date."""
        exception = db.get(DateException, date_value.isoformat())
        if date_value.isoformat() in {x.strip() for x in p.blackout_dates.split(',') if x.strip()}:
            return {'closed': True, 'opening': '', 'closing': '', 'source': 'blackout'}
        if exception is not None:
            return {'closed': bool(exception.closed), 'opening': exception.opening or p.opening,
                    'closing': exception.closing or p.closing, 'source': 'exception'}
        if date_value.weekday() in {int(x) for x in p.closed_weekdays.split(',') if x}:
            return {'closed': True, 'opening': '', 'closing': '', 'source': 'weekly'}
        return {'closed': False, 'opening': p.opening, 'closing': p.closing, 'source': 'regular'}

    def verify_date(p, date_value, db):
        today = datetime.now(TZ).date()
        if date_value < today or date_value > today + timedelta(days=p.horizon_days):
            raise HTTPException(422, 'Requested date is outside the allowed booking window')
        day = resolve_day(db, p, date_value)
        if day['closed']:
            raise HTTPException(422, 'Restaurant is closed for bookings on this date')
        if not day['opening'] or not day['closing'] or day['opening'] >= day['closing']:
            raise HTTPException(422, 'There are no verified booking hours for this date')

    def slots_for(db,p,d,party_size):
        day=resolve_day(db,p,d)
        opening=slot_start(d,day['opening'])
        closing=slot_start(d,day['closing'])
        current=opening
        min_at=datetime.now(TZ).replace(tzinfo=None)+timedelta(minutes=p.minimum_notice_minutes)
        all_slots=[]
        while current+timedelta(minutes=p.duration_minutes) <= closing:
            end=current+timedelta(minutes=p.duration_minutes)
            if current >= min_at:
                available=available_tables(db,current,end,party_size)
                all_slots.append({'time':current.strftime('%H:%M'),'available':bool(available),'tables_available':len(available)})
            current+=timedelta(minutes=p.slot_minutes)
        return all_slots

    def secure_hash(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def validate_guest(name,email,phone):
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email.strip()):
            raise HTTPException(422,'Enter a valid email')
        if not re.fullmatch(r'[+\d ()-]{7,30}',phone.strip()):
            raise HTTPException(422,'Enter a valid phone number')

    def reservation_public(row):
        return {'reference':row.reference,'visit_date':row.start_at.date().isoformat(),
                'visit_time':row.start_at.strftime('%H:%M'),'party_size':row.party_size,
                'status':row.status,'name':row.name,'notification':'Email/SMS notifications are not configured in this build.'}

    def reservation_admin(row):
        data=reservation_public(row)
        data.update({'id':row.id,'table_id':row.table_id,'email':row.email,'phone':row.phone,
                     'notes':row.notes,'end_time':row.end_at.strftime('%H:%M')})
        return data

    def lock_inventory(db):
        if engine.dialect.name=='sqlite':
            db.connection().exec_driver_sql('BEGIN IMMEDIATE')

    @router.get('/booking/config')
    def booking_config():
        with Session() as db:
            p=db.get(BookingPolicy,1)
            count=db.scalar(select(func.count(DiningTable.id)).where(DiningTable.active.is_(True)))
            enabled=configured(p) and count>0
            return {'enabled':enabled,'timezone':'Asia/Kolkata','slot_minutes':p.slot_minutes,
                    'horizon_days':p.horizon_days,'max_party_size':p.max_party_size,
                    'hours':f'{p.opening}–{p.closing}' if p.opening and p.closing else '',
                    'note':'Booking uses owner-configured tables; requests require staff confirmation.' if enabled else
                           'Booking unavailable until the owner verifies tables, hours and booking policy.'}

    @router.get('/booking/availability')
    def booking_availability(visit_date:date,party_size:int=1):
        with Session() as db:
            p=db.get(BookingPolicy,1)
            if not configured(p):raise HTTPException(503,'Booking not enabled by owner')
            if party_size < 1 or party_size>p.max_party_size:raise HTTPException(422,'Invalid party size')
            verify_date(p,visit_date,db)
            return {'date':visit_date.isoformat(),'party_size':party_size,'timezone':'Asia/Kolkata',
                    'slots':slots_for(db,p,visit_date,party_size),'status':'Live availability from configured table inventory'}

    @router.post('/booking/reservations',status_code=201)
    def request_booking(payload:BookingInput,request:Request):
        throttle(request,'booking_request',6,600);check_origin(request)
        if payload.website:return {'status':'received'}  # honeypot
        if not payload.consent:raise HTTPException(422,'Consent to use details for reservation handling is required')
        validate_guest(payload.name,payload.email,payload.phone)
        with Session() as db:
            lock_inventory(db)
            p=db.get(BookingPolicy,1)
            if not configured(p):raise HTTPException(503,'Reservations are disabled pending owner configuration')
            verify_date(p,payload.visit_date,db)
            if payload.party_size>p.max_party_size:raise HTTPException(422,'Party size exceeds configured booking limit')
            options={x['time'] for x in slots_for(db,p,payload.visit_date,payload.party_size)}
            if payload.visit_time not in options:raise HTTPException(422,'Invalid or expired booking time')
            start=slot_start(payload.visit_date,payload.visit_time)
            end=start+timedelta(minutes=p.duration_minutes)
            tables=available_tables(db,start,end,payload.party_size,lock=True)
            if not tables:raise HTTPException(409,'That slot is no longer available. Choose another time.')
            if payload.table_id is not None:
                tables=[t for t in tables if t.id==payload.table_id]
                if not tables: raise HTTPException(409,'That table is no longer available; choose another.')
            token=secrets.token_urlsafe(36)
            row=Reservation(reference='WC-'+secrets.token_hex(5).upper(),token_hash=secure_hash(token),
                table_id=tables[0].id,start_at=start,end_at=end,party_size=payload.party_size,
                name=payload.name.strip(),email=payload.email.strip().lower(),phone=payload.phone.strip(),notes=payload.notes.strip(),status='pending')
            db.add(row);db.flush()
            db.add(BookingEvent(reservation_id=row.id,action='requested',detail='Pending staff confirmation'))
            audit(db,'booking.request',row.reference)
            db.commit()
            return {'booking':reservation_public(row),'selected_table_id':row.table_id,'manage_token':token,
                    'message':'Reservation request saved. It is NOT confirmed until staff approves it. No email has been sent.'}

    @router.post('/booking/manage')
    def manage_booking(payload:BookingToken,request:Request):
        throttle(request,'booking_manage',16,300);check_origin(request)
        with Session() as db:
            row=db.scalar(select(Reservation).where(Reservation.token_hash==secure_hash(payload.token)))
            if not row:raise HTTPException(404,'Reservation not found')
            return {'booking':reservation_public(row)}

    @router.post('/booking/cancel')
    def cancel_booking(payload:BookingToken,request:Request):
        throttle(request,'booking_cancel',8,300);check_origin(request)
        with Session() as db:
            lock_inventory(db)
            row=db.scalar(select(Reservation).where(Reservation.token_hash==secure_hash(payload.token)))
            if not row:raise HTTPException(404,'Reservation not found')
            if row.status not in ('pending','confirmed'):
                raise HTTPException(409,'This reservation cannot be cancelled online. Contact the café.')
            row.status='cancelled'
            db.add(BookingEvent(reservation_id=row.id,action='customer.cancelled'))
            audit(db,'booking.cancel',row.reference)
            db.commit()
            return {'booking':reservation_public(row),'message':'Reservation request cancelled. No cancellation notification was sent.'}

    @router.post('/booking/reschedule')
    def reschedule_booking(payload:RescheduleInput,request:Request):
        """Token-authenticated reservation move, transactional availability verification."""
        throttle(request,'booking_reschedule',6,300);check_origin(request)
        with Session() as db:
            lock_inventory(db)
            row=db.scalar(select(Reservation).where(Reservation.token_hash==secure_hash(payload.token)))
            if row is None:raise HTTPException(404,'Reservation not found')
            if row.status not in ('pending','confirmed'):
                raise HTTPException(409,'This reservation is not eligible for online rescheduling')
            p=db.get(BookingPolicy,1)
            if not configured(p):raise HTTPException(503,'Online rescheduling is unavailable')
            verify_date(p,payload.visit_date,db)
            if row.party_size > p.max_party_size:
                raise HTTPException(409,'Party size is no longer eligible under booking policy')
            times={x['time'] for x in slots_for(db,p,payload.visit_date,row.party_size)}
            if payload.visit_time not in times:
                raise HTTPException(422,'Invalid or expired booking slot')
            start=slot_start(payload.visit_date,payload.visit_time)
            end=start+timedelta(minutes=p.duration_minutes)
            if start==row.start_at and (payload.table_id is None or payload.table_id==row.table_id):
                return {'booking':reservation_public(row),'message':'Reservation time is unchanged.'}
            candidates=available_tables(db,start,end,row.party_size,lock=True,exclude_id=row.id)
            if payload.table_id is not None:
                candidates=[t for t in candidates if t.id==payload.table_id]
            if not candidates:
                raise HTTPException(409,'Requested table/time is not available')
            previous=f'{row.start_at.isoformat()} table={row.table_id}'
            row.start_at=start;row.end_at=end;row.table_id=candidates[0].id
            # A previously confirmed booking remains confirmed only if its owner-configured policy
            # allows rescheduling; the real table has been atomically allocated above.
            db.add(BookingEvent(reservation_id=row.id,action='customer.rescheduled',
                    detail=(previous+' -> '+start.isoformat()+f' table={row.table_id}')[:300]))
            audit(db,'booking.reschedule',row.reference)
            db.commit()
            return {'booking':reservation_public(row),'selected_table_id':row.table_id,
                    'message':'Reservation updated in the booking system. No email/SMS was sent.'}

    @router.post('/booking/waitlist',status_code=201)
    def join_waitlist(payload:WaitlistInput,request:Request):
        throttle(request,'waitlist',5,600);check_origin(request)
        if not payload.consent:raise HTTPException(422,'Consent is required')
        validate_guest(payload.name,payload.email,payload.phone)
        if payload.preferred_time and not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d',payload.preferred_time):
            raise HTTPException(422,'Invalid preferred time')
        with Session() as db:
            p=db.get(BookingPolicy,1)
            if not configured(p):raise HTTPException(503,'Waitlist is unavailable until owner enables bookings')
            verify_date(p,payload.visit_date,db)
            if payload.party_size>p.max_party_size:raise HTTPException(422,'Party size exceeds configured limit')
            r=Waitlist(reference='WW-'+secrets.token_hex(5).upper(),visit_date=payload.visit_date.isoformat(),
                preferred_time=payload.preferred_time,party_size=payload.party_size,name=payload.name.strip(),
                email=payload.email.strip().lower(),phone=payload.phone.strip(),status='waiting')
            db.add(r);audit(db,'waitlist.join',r.reference);db.commit()
            return {'reference':r.reference,'status':'waiting','message':'Waitlist request saved. This is not a reservation or guarantee of a table.'}

    @router.get('/admin/booking/date-exceptions')
    def booking_date_exceptions(request: Request):
        authenticated(request)
        with Session() as db:
            rows = db.scalars(select(DateException).order_by(DateException.visit_date)).all()
            return {'dates': [
                {'date': x.visit_date, 'closed': x.closed, 'opening': x.opening,
                 'closing': x.closing, 'note': x.note} for x in rows]}

    @router.put('/admin/booking/date-exceptions/{visit_date}')
    def set_booking_date_exception(visit_date: date, payload: DateExceptionInput, request: Request):
        admin_write(request)
        today = datetime.now(TZ).date()
        if not today <= visit_date <= today + timedelta(days=365):
            raise HTTPException(422, 'Choose a date within the next 365 days')
        if not payload.closed and (not payload.opening or not payload.closing or payload.opening >= payload.closing):
            raise HTTPException(422, 'Enter valid opening and closing times for an open date')
        with Session() as db:
            lock_inventory(db)
            first = datetime.combine(visit_date, datetime.min.time())
            last = first + timedelta(days=1)
            active = db.scalars(select(Reservation).where(
                Reservation.start_at >= first, Reservation.start_at < last,
                Reservation.status.in_(BLOCKING))).all()
            if active and (payload.closed or any(
                    row.start_at.strftime('%H:%M') < payload.opening
                    or row.end_at.strftime('%H:%M') > payload.closing for row in active)):
                raise HTTPException(409, 'Existing reservations conflict with these hours. Resolve them first.')
            row = db.get(DateException, visit_date.isoformat())
            if row is None:
                row = DateException(visit_date=visit_date.isoformat())
                db.add(row)
            row.closed = payload.closed
            row.opening = payload.opening
            row.closing = payload.closing
            row.note = payload.note.strip()
            row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
            audit(db, 'booking.day_override.save', visit_date.isoformat())
            db.commit()
            return {'date': row.visit_date, 'closed': row.closed,
                    'opening': row.opening, 'closing': row.closing, 'note': row.note}

    @router.delete('/admin/booking/date-exceptions/{visit_date}')
    def delete_booking_date_exception(visit_date: date, request: Request):
        admin_write(request)
        with Session() as db:
            lock_inventory(db)
            row = db.get(DateException, visit_date.isoformat())
            if not row:
                raise HTTPException(404, 'No exception configured')
            # Removing an exception can reactivate a regular closed-day rule.
            p = db.get(BookingPolicy, 1)
            first = datetime.combine(visit_date, datetime.min.time())
            active = db.scalars(select(Reservation).where(
                Reservation.start_at >= first, Reservation.start_at < first + timedelta(days=1),
                Reservation.status.in_(BLOCKING))).all()
            default_closed = visit_date.weekday() in {
                int(x) for x in p.closed_weekdays.split(',') if x
            } or visit_date.isoformat() in {x.strip() for x in p.blackout_dates.split(',') if x.strip()}
            if active and (default_closed or any(
                    booking.start_at.strftime('%H:%M') < p.opening
                    or booking.end_at.strftime('%H:%M') > p.closing for booking in active)):
                raise HTTPException(409, 'Removing this exception would conflict with existing reservations')
            db.delete(row)
            audit(db, 'booking.day_override.delete', visit_date.isoformat())
            db.commit()
            return {'deleted': True, 'date': visit_date.isoformat()}

    @router.get('/admin/booking/day-board')
    def booking_day_board(request: Request, visit_date: date):
        authenticated(request)
        with Session() as db:
            p = db.get(BookingPolicy, 1)
            table_rows = db.scalars(select(DiningTable).order_by(DiningTable.label)).all()
            start = datetime.combine(visit_date, datetime.min.time())
            bookings = db.scalars(select(Reservation).where(
                Reservation.start_at >= start,
                Reservation.start_at < start + timedelta(days=1)).order_by(
                    Reservation.start_at, Reservation.id)).all()
            day = resolve_day(db, p, visit_date)
            return {
                'date': visit_date.isoformat(), 'timezone': 'Asia/Kolkata',
                'bookings_enabled': bool(configured(p) and any(x.active for x in table_rows)),
                'hours': day, 'table_count': sum(x.active for x in table_rows),
                'seats_total': sum(x.seats for x in table_rows if x.active),
                'pending': sum(x.status == 'pending' for x in bookings),
                'confirmed': sum(x.status == 'confirmed' for x in bookings),
                'tables': [{
                    'id': t.id, 'label': t.label, 'area': t.area, 'seats': t.seats,
                    'active': t.active,
                    'bookings': [{
                        'id': x.id, 'reference': x.reference, 'guest': x.name,
                        'party_size': x.party_size, 'status': x.status,
                        'start': x.start_at.strftime('%H:%M'),
                        'end': x.end_at.strftime('%H:%M')
                    } for x in bookings if x.table_id == t.id]
                } for t in table_rows]
            }

    @router.get('/admin/booking/policy')
    def admin_policy(request:Request):
        authenticated(request)
        with Session() as db:
            return policy_dict(db.get(BookingPolicy,1))

    @router.put('/admin/booking/policy')
    def update_policy(payload:PolicyInput,request:Request):
        admin_write(request)
        if payload.enabled:
            if not payload.owner_verified:raise HTTPException(422,'Owner verification required')
            if not payload.opening or not payload.closing or payload.opening>=payload.closing:
                raise HTTPException(422,'Enter verified opening and closing times')
            with Session() as db:
                if not db.scalar(select(func.count(DiningTable.id)).where(DiningTable.active.is_(True))):
                    raise HTTPException(422,'Add real active tables before enabling reservations')
        with Session() as db:
            p=db.get(BookingPolicy,1)
            for k,v in payload.model_dump().items():setattr(p,k,v)
            audit(db,'booking.policy.update',f'bookings enabled={payload.enabled}')
            db.commit()
            return policy_dict(p)

    @router.get('/admin/booking/tables')
    def list_tables(request:Request):
        authenticated(request)
        with Session() as db:
            return {'tables':[{'id':t.id,'label':t.label,'seats':t.seats,'area':t.area,'active':t.active}
                             for t in db.scalars(select(DiningTable).order_by(DiningTable.id)).all()]}

    @router.post('/admin/booking/tables',status_code=201)
    def create_table(payload:TableInput,request:Request):
        admin_write(request)
        with Session() as db:
            label=payload.label.strip()
            if db.scalar(select(DiningTable).where(DiningTable.label==label)):
                raise HTTPException(409,'Table identifier already exists')
            t=DiningTable(**{**payload.model_dump(),'label':label,'area':payload.area.strip()})
            db.add(t);audit(db,'booking.table.create',label);db.commit()
            return {'id':t.id,'label':t.label,'seats':t.seats,'area':t.area,'active':t.active}

    @router.put('/admin/booking/tables/{table_id}')
    def update_table(table_id:int,payload:TableInput,request:Request):
        admin_write(request)
        with Session() as db:
            t=db.get(DiningTable,table_id)
            if not t:raise HTTPException(404,'Unknown table')
            existing=db.scalar(select(DiningTable).where(DiningTable.label==payload.label.strip(),DiningTable.id!=table_id))
            if existing:raise HTTPException(409,'Table identifier already exists')
            now=datetime.now(TZ).replace(tzinfo=None)
            bookings=db.scalars(select(Reservation).where(Reservation.table_id==table_id,
                Reservation.status.in_(BLOCKING),Reservation.end_at>now)).all()
            if bookings and (not payload.active or any(b.party_size>payload.seats for b in bookings)):
                raise HTTPException(409,'Existing reservations require this table and capacity; reassign them first')
            for k,v in payload.model_dump().items():setattr(t,k,v.strip() if isinstance(v,str) else v)
            audit(db,'booking.table.update',f'table {table_id}')
            db.commit()
            return {'id':t.id,'label':t.label,'seats':t.seats,'area':t.area,'active':t.active}

    @router.get('/admin/booking/reservations')
    def reservations_admin(request:Request, visit_date:date|None=None):
        authenticated(request)
        with Session() as db:
            query=select(Reservation).order_by(Reservation.start_at.desc(),Reservation.id.desc()).limit(300)
            if visit_date is not None:
                query=query.where(Reservation.start_at>=datetime.combine(visit_date,datetime.min.time()),
                                  Reservation.start_at<datetime.combine(visit_date+timedelta(days=1),datetime.min.time()))
            rows=db.scalars(query).all()
            return {'reservations':[reservation_admin(x) for x in rows]}

    @router.patch('/admin/booking/reservations/{reservation_id}')
    def change_reservation(reservation_id:int,payload:BookingStatusInput,request:Request):
        admin_write(request)
        if payload.status not in STATUSES:raise HTTPException(422,'Invalid status')
        with Session() as db:
            lock_inventory(db)
            row=db.get(Reservation,reservation_id)
            if not row:raise HTTPException(404,'Reservation not found')
            if payload.status!=row.status and payload.status not in TRANSITIONS[row.status]:
                raise HTTPException(409,'Invalid reservation status transition')
            desired_table=payload.table_id if payload.table_id is not None else row.table_id
            if payload.status in BLOCKING:
                valid=available_tables(db,row.start_at,row.end_at,row.party_size,lock=True,exclude_id=row.id)
                if desired_table not in {t.id for t in valid}:
                    raise HTTPException(409,'Selected table conflicts with another reservation or its capacity')
            if payload.status!=row.status or row.table_id!=desired_table:
                db.add(BookingEvent(reservation_id=row.id,action='staff.change',detail=f'{row.status} -> {payload.status}, table {row.table_id} -> {desired_table}'))
            row.status=payload.status;row.table_id=desired_table
            audit(db,'booking.staff_update',f'{row.reference} status={row.status}')
            db.commit()
            return reservation_admin(row)

    @router.get('/admin/booking/waitlist')
    def waitlist_admin(request:Request):
        authenticated(request)
        with Session() as db:
            rows=db.scalars(select(Waitlist).order_by(Waitlist.id.desc()).limit(200)).all()
            return {'waitlist':[{'id':r.id,'reference':r.reference,'date':r.visit_date,'time':r.preferred_time,
                    'party_size':r.party_size,'name':r.name,'email':r.email,'phone':r.phone,'status':r.status} for r in rows]}

    @router.patch('/admin/booking/waitlist/{entry_id}')
    def update_waitlist(entry_id:int,payload:StatusInput,request:Request):
        admin_write(request)
        if payload.status not in ('waiting','contacted','closed'):
            raise HTTPException(422,'Invalid waitlist status')
        with Session() as db:
            r=db.get(Waitlist,entry_id)
            if not r:raise HTTPException(404,'Unknown waitlist request')
            r.status=payload.status;audit(db,'waitlist.update',f'{r.reference}: {r.status}');db.commit()
            return {'saved':True,'status':r.status}

    @router.get('/admin/booking/walkins')
    def walkins_admin(request:Request):
        authenticated(request)
        with Session() as db:
            rows=db.scalars(select(Walkin).order_by(Walkin.id.desc()).limit(150)).all()
            return {'walkins':[{'id':r.id,'name':r.name,'party_size':r.party_size,'phone':r.phone,'status':r.status} for r in rows]}

    @router.post('/admin/booking/walkins',status_code=201)
    def add_walkin(payload:WalkinInput,request:Request):
        admin_write(request)
        with Session() as db:
            row=Walkin(**payload.model_dump());db.add(row);audit(db,'walkin.create',row.name);db.commit()
            return {'id':row.id,'status':row.status}

    @router.patch('/admin/booking/walkins/{walkin_id}')
    def update_walkin(walkin_id:int,payload:StatusInput,request:Request):
        admin_write(request)
        if payload.status not in ('waiting','seated','cancelled'):
            raise HTTPException(422,'Invalid walk-in status')
        with Session() as db:
            row=db.get(Walkin,walkin_id)
            if not row:raise HTTPException(404,'Unknown walk-in')
            row.status=payload.status;audit(db,'walkin.update',f'{walkin_id}:{row.status}');db.commit()
            return {'saved':True,'status':row.status}

    app.include_router(router)
    return {'Policy':BookingPolicy,'Table':DiningTable,'Reservation':Reservation}
