"""V38 Living Atelier: verified-media editor, moderated guest notes, aggregate only opt-in events.
No artificial table availability, reviews, visitor identifiers, or marketing claims.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Literal
import json, re
from fastapi import HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Column, Integer, String, DateTime, Boolean, select, func, UniqueConstraint
from sqlalchemy.orm import declarative_base

PHOTO_SLOTS=('hero','interior','food','coffee','evening','dessert')
EVENT_TYPES=('atelier_visit','atelier_save','atelier_share','atelier_postcard','guest_story_open','guest_note_submit')

class SpotlightIn(BaseModel):
    headline: str = Field(min_length=5,max_length=90)
    subtitle: str = Field(min_length=12,max_length=260)
    photo_id: str = Field(min_length=2,max_length=20)
    cta_text: str = Field(min_length=3,max_length=36)
    cta_path: Literal['/menu','/food-theatre','/reservations','/visit','/living-house']

    @field_validator('headline','subtitle','cta_text')
    @classmethod
    def plain_text(cls,v):
        value=' '.join(v.split())
        if '<' in value or '>' in value: raise ValueError('Plain text only')
        return value

class NoteIn(BaseModel):
    first_name: str = Field(min_length=2,max_length=36)
    message: str = Field(min_length=12,max_length=500)
    consent: bool
    website: str = Field(default='',max_length=100)

    @field_validator('first_name','message')
    @classmethod
    def clean(cls,v):
        val=' '.join(v.split())
        if '<' in val or '>' in val: raise ValueError('Plain text only')
        return val

class ModerationIn(BaseModel):
    status: Literal['published','rejected','pending']

class EngagementIn(BaseModel):
    event: Literal['atelier_visit','atelier_save','atelier_share','atelier_postcard','guest_story_open','guest_note_submit']
    consent: bool


def install_v38(app,Base,engine,Session,Setting,owner_only,admin_write,throttle,check_origin,audit,root:Path):
    class GuestNote(Base):
        __tablename__='v38_guest_notes'
        id=Column(Integer,primary_key=True)
        first_name=Column(String(36),nullable=False)
        message=Column(String(500),nullable=False)
        state=Column(String(20),nullable=False,default='pending',index=True)
        consent=Column(Boolean,nullable=False,default=False)
        created_at=Column(DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))

    class Engagement(Base):
        __tablename__='v38_engagement_daily'
        __table_args__=(UniqueConstraint('day','event',name='v38_daily_event_unique'),)
        id=Column(Integer,primary_key=True)
        day=Column(String(10),nullable=False,index=True)
        event=Column(String(30),nullable=False)
        count=Column(Integer,nullable=False,default=0)

    Base.metadata.create_all(engine,tables=[GuestNote.__table__,Engagement.__table__])
    media=json.loads((root/'docs/V10_MEDIA_MANIFEST.json').read_text(encoding='utf-8'))
    verified={p['id']:p for p in media if p.get('publication_state')=='published' and not p.get('archival_only') and (root/p['optimized_paths']['large'].lstrip('/')).exists()}
    # Curated photographic defaults are from the actual project archive, not a synthetic set.
    by_category={}
    for p in verified.values():
        by_category.setdefault(p.get('category',''),[]).append(p)
    for ps in by_category.values(): ps.sort(key=lambda p:(-p.get('quality_score',0),p['id']))
    preferred=(by_category.get('ambience',[])+by_category.get('interior',[])+by_category.get('place',[])+list(verified.values()))
    initial=preferred[0]['id'] if preferred else next(iter(verified),'')
    defaults={'headline':'A house full of little moments',
              'subtitle':'Step into real Wongdhen photographs, explore the menu, and keep a moment to share.',
              'photo_id':initial,'cta_text':'EXPLORE THE MENU','cta_path':'/food-theatre'}

    def spotlight(db):
        rows={k:(db.get(Setting,'v38_spotlight_'+k).value if db.get(Setting,'v38_spotlight_'+k) else v) for k,v in defaults.items()}
        if rows['photo_id'] not in verified:rows['photo_id']=initial
        if rows['cta_path'] not in ('/menu','/food-theatre','/reservations','/visit','/living-house'):
            rows['cta_path']='/food-theatre'
        photo=verified.get(rows['photo_id'])
        return dict(rows,photo_url=photo['optimized_paths']['large'] if photo else '/static/images/hero-night.webp',
                    photo_alt=photo.get('alt_text','Original Wongdhen Café photograph') if photo else 'Wongdhen Café photograph')

    def public_note(n):
        return {'id':n.id,'first_name':n.first_name,'message':n.message}

    @app.get('/api/v38/editorial')
    def public_editorial():
        with Session() as db:return {'release':'V38','spotlight':spotlight(db),'review_status':'Guest messages are moderated and are not independently verified customer reviews.',
                                  'approved_photo_count':len(verified),'media_notice':'Only published photographs from the existing project archive.'}

    @app.get('/api/v38/photos')
    def photo_choices(category:str='all',limit:int=40):
        if category not in ('all',*by_category.keys()):raise HTTPException(422,'Unsupported photo category')
        pics=list(verified.values()) if category=='all' else by_category.get(category,[])
        pics=sorted(pics,key=lambda p:(-p.get('quality_score',0),p['id']))[:min(max(limit,1),80)]
        return {'categories':sorted(by_category),'items':[{'id':p['id'],'category':p['category'],'src':p['optimized_paths']['thumb'],'large':p['optimized_paths']['large'],'alt':p['alt_text']} for p in pics]}

    @app.put('/api/v38/admin/editorial')
    def owner_editorial(payload:SpotlightIn,request:Request):
        owner_only(request,write=True)
        if payload.photo_id not in verified:raise HTTPException(422,'Choose a published original photo ID')
        with Session() as db:
            for k,v in payload.model_dump().items():
                key='v38_spotlight_'+k
                item=db.get(Setting,key)
                if item:item.value=v
                else:db.add(Setting(key=key,value=v))
            audit(db,'v38.spotlight','Updated public editorial spotlight')
            db.commit()
            return {'saved':True,'spotlight':spotlight(db)}

    @app.post('/api/v38/notes',status_code=202)
    def submit_note(payload:NoteIn,request:Request):
        check_origin(request)
        throttle(request,'v38_notes',3,86400)
        if payload.website: return {'accepted':True,'status':'pending'}  # honeypot
        if not payload.consent:raise HTTPException(422,'Publishing consent is required')
        # Never store email, IP, contact details, photos, passwords or session IDs.
        if re.search(r'\b[\w.+-]+@[\w.-]+\.\w+\b',payload.message) or re.search(r'\b\d{10,}\b',payload.message):
            raise HTTPException(422,'Do not include contact details')
        with Session() as db:
            db.add(GuestNote(first_name=payload.first_name,message=payload.message,consent=True))
            db.commit()
        return {'accepted':True,'status':'pending','notice':'Your note will appear only after manual moderation.'}

    @app.get('/api/v38/notes')
    def public_notes(limit:int=12):
        with Session() as db:
            notes=db.scalars(select(GuestNote).where(GuestNote.state=='published',GuestNote.consent.is_(True))
                             .order_by(GuestNote.id.desc()).limit(min(max(1,limit),24))).all()
            return {'items':[public_note(n) for n in notes],
                    'notice':'Guest-submitted notes, manually moderated; not independently authenticated as customer reviews.'}

    @app.get('/api/v38/admin/notes')
    def pending_notes(request:Request,state:Literal['pending','published','rejected']='pending'):
        owner_only(request)
        with Session() as db:
            notes=db.scalars(select(GuestNote).where(GuestNote.state==state).order_by(GuestNote.id.desc()).limit(100)).all()
            return {'items':[dict(public_note(n),status=n.state,created_at=n.created_at.isoformat() if n.created_at else '') for n in notes]}

    @app.patch('/api/v38/admin/notes/{note_id}')
    def moderate_note(note_id:int,payload:ModerationIn,request:Request):
        owner_only(request,write=True)
        with Session() as db:
            note=db.get(GuestNote,note_id)
            if note is None:raise HTTPException(404,'Guest note not found')
            note.state=payload.status
            audit(db,'v38.note.moderation',f'note={note_id} state={payload.status}')
            db.commit()
            return {'saved':True,'status':payload.status}

    @app.delete('/api/v38/admin/notes/{note_id}')
    def delete_note(note_id:int,request:Request):
        owner_only(request,write=True)
        with Session() as db:
            note=db.get(GuestNote,note_id)
            if note is None:raise HTTPException(404,'Guest note not found')
            db.delete(note)
            audit(db,'v38.note.deleted',f'note={note_id}')
            db.commit()
        return {'deleted':True}

    @app.post('/api/v38/events',status_code=202)
    def opt_in_event(payload:EngagementIn,request:Request):
        check_origin(request)
        if not payload.consent:raise HTTPException(422,'Analytics opt-in is required')
        throttle(request,'v38_metrics',60,3600)
        day=date.today().isoformat()
        # Portable daily counter. Single transaction; SQLite serializes writes.
        from sqlalchemy import update
        with Session() as db:
            row=db.scalar(select(Engagement).where(Engagement.day==day,Engagement.event==payload.event))
            if row:row.count+=1
            else:db.add(Engagement(day=day,event=payload.event,count=1))
            db.commit()
        return {'accepted':True}

    @app.get('/api/v38/admin/insights')
    def aggregate_insights(request:Request):
        owner_only(request)
        with Session() as db:
            rows=db.scalars(select(Engagement).order_by(Engagement.day.desc()).limit(240)).all()
            notes=db.scalar(select(func.count(GuestNote.id)).where(GuestNote.state=='pending')) or 0
            return {'counts':[{'date':r.day,'event':r.event,'count':r.count} for r in rows],
                    'pending_guest_notes':notes,
                    'notice':'Opt-in event counts only. Not unique visitors, actual reservations or revenue. No IP or visitor ID is saved.'}

    return {'GuestNote':GuestNote,'Engagement':Engagement,'photo_count':len(verified)}
