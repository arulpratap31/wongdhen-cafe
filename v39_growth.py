"""V39 Growth Studio & daily service standards.
Privacy-aware, zero invented sales: enquiries and reservations are *requests*.
Only the owner may curate campaigns or see cross-period business summaries.
Managers can run task checklists, never access owner business endpoints.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, DateTime, Boolean, select, func, UniqueConstraint

DESTINATIONS={'/menu','/food-theatre','/reservations','/visit','/plan-your-moment','/atelier','/contact'}
PICTURES={
    'house':('/static/images/hero-night.webp','Actual café ambience photograph'),
    'interior':('/static/images/interior-day.webp','Café interior photograph'),
    'food':('/static/images/v10-food.webp','Photograph from the café food collection'),
    'coffee':('/static/images/coffee-art.webp','Coffee photograph'),
    'entrance':('/static/images/v10-entrance.webp','Café entrance photograph')
}
TASKS=(
 ('arrival','Review the booking calendar',"Check today's actual booking requests and arrivals."),
 ('availability','Check menu availability','Confirm which published items are actually available.'),
 ('inbox','Review guest enquiries','Reply to outstanding customer service messages.'),
 ('floor','Inspect the dining area','Complete physical cleanliness and table checks.'),
 ('team','Coordinate kitchen and floor',"Confirm that the team understands today's service."),
 ('close','Complete the handover','Record that the next shift has received its briefing.'),
)
TASK_KEYS={t[0] for t in TASKS}

class CampaignIn(BaseModel):
    slug: str = Field(min_length=3,max_length=40,pattern=r'^[a-z0-9]+(?:-[a-z0-9]+)*$')
    title: str = Field(min_length=6,max_length=78)
    description: str = Field(min_length=18,max_length=210)
    cta: str = Field(min_length=3,max_length=30)
    destination: Literal['/menu','/food-theatre','/reservations','/visit','/plan-your-moment','/atelier','/contact']
    picture: Literal['house','interior','food','coffee','entrance']
    published: bool = False

class PublishIn(BaseModel):
    published: bool

class TaskIn(BaseModel):
    done: bool


def install_v39(app,Base,engine,Session,owner_only,admin_write,authenticated,audit,Contact,Reservation,root):
    class Campaign(Base):
        __tablename__='v39_growth_campaigns'
        id=Column(Integer,primary_key=True)
        slug=Column(String(40),unique=True,nullable=False,index=True)
        title=Column(String(78),nullable=False)
        description=Column(String(210),nullable=False)
        cta=Column(String(30),nullable=False)
        destination=Column(String(45),nullable=False)
        picture=Column(String(25),nullable=False)
        published=Column(Boolean,nullable=False,default=False)
        created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None),nullable=False)

    class Checklist(Base):
        __tablename__='v39_daily_service_checks'
        __table_args__=(UniqueConstraint('service_date','task_key',name='v39_check_date_task'),)
        id=Column(Integer,primary_key=True)
        service_date=Column(String(10),nullable=False,index=True)
        task_key=Column(String(30),nullable=False)
        done=Column(Boolean,nullable=False,default=False)
        changed_at=Column(DateTime,nullable=False,default=lambda:datetime.now(timezone.utc).replace(tzinfo=None))
    Base.metadata.create_all(engine,tables=[Campaign.__table__,Checklist.__table__])

    def check_manager(request,write=False):
        identity=admin_write(request) if write else authenticated(request)
        if identity['role'] not in ('manager','admin'):
            raise HTTPException(403,'Manager or owner access required')
        return identity

    def campaign_dict(row):
        photo=PICTURES[row.picture]
        return {'id':row.id,'slug':row.slug,'title':row.title,'description':row.description,
                'cta':row.cta,'destination':row.destination,'picture':row.picture,
                'image':photo[0],'image_alt':photo[1],'published':bool(row.published)}

    @app.get('/api/v39/public/campaigns',tags=['V39 growth'])
    def campaigns_public():
        with Session() as db:
            rows=db.scalars(select(Campaign).where(Campaign.published.is_(True)).order_by(Campaign.id.desc()).limit(6)).all()
            return {'items':[campaign_dict(x) for x in rows],
                    'notice':'Owner-published visit stories. No unverified discounts or availability claims.'}

    @app.get('/api/v39/owner/campaigns',tags=['V39 owner growth'])
    def campaigns_owner(request:Request):
        owner_only(request)
        with Session() as db:
            rows=db.scalars(select(Campaign).order_by(Campaign.id.desc()).limit(100)).all()
            return {'items':[campaign_dict(x) for x in rows]}

    @app.post('/api/v39/owner/campaigns',status_code=201,tags=['V39 owner growth'])
    def campaign_create(payload:CampaignIn,request:Request):
        owner_only(request,write=True)
        if not (root/PICTURES[payload.picture][0].lstrip('/')).is_file():
            raise HTTPException(422,'Selected original media not found')
        with Session() as db:
            if db.scalar(select(Campaign.id).where(Campaign.slug==payload.slug)) is not None:
                raise HTTPException(409,'Campaign slug already exists')
            row=Campaign(**payload.model_dump())
            db.add(row);db.flush();result=campaign_dict(row)
            audit(db,'v39.campaign.created',f'campaign={row.id} published={row.published}')
            db.commit()
            return {'created':True,'campaign':result}

    @app.patch('/api/v39/owner/campaigns/{campaign_id}',tags=['V39 owner growth'])
    def campaign_publish(campaign_id:int,payload:PublishIn,request:Request):
        owner_only(request,write=True)
        with Session() as db:
            row=db.get(Campaign,campaign_id)
            if not row:raise HTTPException(404,'Campaign not found')
            row.published=payload.published
            audit(db,'v39.campaign.publish',f'campaign={row.id} published={row.published}')
            db.commit()
            return {'saved':True,'published':row.published}

    @app.get('/api/v39/owner/insights',tags=['V39 owner growth'])
    def owner_insights(request:Request):
        owner_only(request)
        now=datetime.now(timezone.utc).replace(tzinfo=None)
        current=now-timedelta(days=30)
        previous=now-timedelta(days=60)
        with Session() as db:
            def count(model,filters):
                query=select(func.count()).select_from(model)
                for f in filters:query=query.where(f)
                return int(db.scalar(query) or 0)
            return {'period_days':30,'enquiries':{
                      'current':count(Contact,[Contact.received_at>=current]),
                      'previous':count(Contact,[Contact.received_at>=previous,Contact.received_at<current])},
                    'reservation_requests':{
                      'current':count(Reservation,[Reservation.created_at>=current]),
                      'previous':count(Reservation,[Reservation.created_at>=previous,Reservation.created_at<current])},
                    'confirmed_reservations_all_time':count(Reservation,[Reservation.status=='confirmed']),
                    'campaigns':{'published':count(Campaign,[Campaign.published.is_(True)]),'drafts':count(Campaign,[Campaign.published.is_(False)])},
                    'notice':'These are real database counts of submitted enquiries and reservation requests, NOT attributed conversions, footfall, settled sales or proof of customer visits.'}

    def local_day():return datetime.now(ZoneInfo('Asia/Kolkata')).date().isoformat()

    @app.get('/api/v39/manager/checklist',tags=['V39 manager operations'])
    def checklist_read(request:Request):
        check_manager(request)
        today=local_day()
        with Session() as db:
            recorded={r.task_key:r for r in db.scalars(select(Checklist).where(Checklist.service_date==today))}
            return {'date':today,'items':[{'key':key,'label':label,'description':description,
                    'done':bool(recorded[key].done) if key in recorded else False} for key,label,description in TASKS],
                    'notice':'Manual daily completion marks; not automated verification of physical work.'}

    @app.put('/api/v39/manager/checklist/{task_key}',tags=['V39 manager operations'])
    def checklist_update(task_key:str,payload:TaskIn,request:Request):
        check_manager(request,write=True)
        if task_key not in TASK_KEYS:raise HTTPException(404,'Checklist item not found')
        today=local_day()
        with Session() as db:
            entry=db.scalar(select(Checklist).where(Checklist.service_date==today,Checklist.task_key==task_key))
            if entry is None:
                entry=Checklist(service_date=today,task_key=task_key,done=payload.done)
                db.add(entry)
            else:entry.done=payload.done
            entry.changed_at=datetime.now(timezone.utc).replace(tzinfo=None)
            audit(db,'v39.checklist.updated',f'{today}:{task_key} done={payload.done}')
            db.commit()
            return {'saved':True,'date':today,'task_key':task_key,'done':payload.done}

    return {'Campaign':Campaign,'Checklist':Checklist}
