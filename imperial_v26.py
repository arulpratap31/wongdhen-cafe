"""V26 Imperial Grand Maison: isolated incremental features.
Never treat development menu prices as owner-verified; never enable integrations implicitly.
"""
from __future__ import annotations
import io, json, os, re, secrets
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import qrcode
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, String, Text, DateTime, select, func
from itsdangerous import URLSafeSerializer, BadSignature


class EstimateRequest(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=20)


class ShiftNoteIn(BaseModel):
    text: str = Field(min_length=3, max_length=900)
    shift: str = Field(default='General', min_length=2, max_length=40)


class IssueIn(BaseModel):
    title: str = Field(min_length=4, max_length=140)
    details: str = Field(default='', max_length=1000)
    severity: str = Field(default='normal', pattern=r'^(low|normal|high)$')


class IssueUpdate(BaseModel):
    status: str = Field(pattern=r'^(open|in_progress|resolved)$')


def install_imperial(app, Base, engine, Session, MenuItem, booking_models, owner_only, audit, root: Path, key: str, check_origin, throttle):
    class ShiftNote(Base):
        __tablename__ = 'v26_shift_handover'
        id = Column(Integer, primary_key=True)
        shift = Column(String(40), nullable=False)
        text = Column(Text, nullable=False)
        created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    class ServiceIssue(Base):
        __tablename__ = 'v26_service_issues'
        id = Column(Integer, primary_key=True)
        title = Column(String(140), nullable=False)
        details = Column(Text, nullable=False, default='')
        severity = Column(String(12), nullable=False, default='normal')
        status = Column(String(20), nullable=False, default='open')
        created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Older schema uses create_all at startup. A separate Alembic migration is also supplied.
    Base.metadata.create_all(engine, tables=[ShiftNote.__table__, ServiceIssue.__table__], checkfirst=True)
    signer = URLSafeSerializer(key, salt='v26-table-view-only')
    Table = booking_models['Table']

    @app.get('/admin/imperial')
    def owner_studio(request:Request):
        owner_only(request)
        return FileResponse(root/'static'/'v26'/'owner.html', media_type='text/html', headers={'Cache-Control':'no-store'})

    @app.get('/manifest.webmanifest')
    def manifest():
        return FileResponse(root/'static'/'v26'/'manifest.webmanifest',media_type='application/manifest+json',headers={'Cache-Control':'public, max-age=300'})

    @app.get('/service-worker.js')
    def worker():
        return FileResponse(root/'static'/'v26'/'service-worker.js',media_type='text/javascript',headers={'Cache-Control':'no-cache','Service-Worker-Allowed':'/'})

    @app.get('/offline')
    def offline():
        return FileResponse(root/'static'/'v26'/'offline.html',media_type='text/html',headers={'Cache-Control':'public, max-age=600'})

    @app.post('/api/v26/menu/estimate')
    def estimate(payload: EstimateRequest, request: Request):
        check_origin(request)
        throttle(request,'menu-estimate',30,60)
        # Duplicate IDs must never multiply prices silently.
        if len(set(payload.item_ids)) != len(payload.item_ids):
            raise HTTPException(422,'Duplicate dish identifiers are not allowed')
        with Session() as db:
            rows = db.scalars(select(MenuItem).where(MenuItem.id.in_(payload.item_ids),MenuItem.published.is_(True))).all()
        if len(rows) != len(payload.item_ids):
            raise HTTPException(404,'One or more published menu items are unavailable')
        mapped={r.id:r for r in rows}
        entries=[]; total=0; incomplete=False
        for item_id in payload.item_ids:
            r=mapped[item_id]
            raw=r.price_display.strip()
            # Slash-separated multi-variant prices cannot be safely aggregated.
            parsed=int(raw.replace(',','')) if re.fullmatch(r'[0-9]{1,6}(?:,[0-9]{3})*',raw) else None
            if parsed is None: incomplete=True
            else: total+=parsed
            entries.append({'id':r.id,'name':r.name,'category':r.category,'published_price_text':raw,
                            'amount_inr':parsed,'price_owner_approved':bool(r.approved)})
        return {'items':entries,'subtotal_inr':None if incomplete else total,'partial_known_total_inr':total,
                'all_prices_unambiguous':not incomplete,'currency':'INR','is_order':False,
                'pricing_note':'Planning estimate from the supplied menu PDF only. Prices, taxes, service charges and actual availability require current owner confirmation.'}

    @app.get('/api/v26/admin/tables/{table_id}/qr')
    def table_qr(table_id:int, request:Request):
        owner_only(request)
        with Session() as db:
            row=db.get(Table,table_id)
            if not row or not row.active:raise HTTPException(404,'Active table not found')
            label=row.label
        token=signer.dumps({'table':table_id})
        public_base=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
        if os.environ.get('ENVIRONMENT')=='production' and not public_base.startswith('https://'):
            raise HTTPException(503,'A verified HTTPS PUBLIC_BASE_URL is required for production QR links')
        if not public_base:public_base='http://127.0.0.1:8000'
        return {'table':label,'url':public_base+'/menu?table_code='+quote(token,safe=''),
                'notice':'Read-only menu context. A QR scan does not create an order or confirm a reservation.'}

    @app.get('/api/v26/admin/tables/{table_id}/qr.png')
    def table_qr_image(table_id:int, request:Request):
        data=table_qr(table_id,request)
        img=qrcode.make(data['url'])
        output=io.BytesIO();img.save(output,format='PNG')
        return Response(output.getvalue(),media_type='image/png',headers={'Cache-Control':'no-store'})

    @app.get('/api/v26/table/context')
    def table_context(code:str=''):
        try:
            obj=signer.loads(code)
            table_id=obj['table']
            if not isinstance(table_id,int):raise ValueError
        except (BadSignature,ValueError,TypeError,KeyError):
            raise HTTPException(400,'Invalid table QR code')
        with Session() as db:
            row=db.get(Table,table_id)
            if not row or not row.active:raise HTTPException(404,'Table is unavailable')
            return {'table_label':row.label,'area':row.area,'read_only':True,
                    'notice':'Browsing this menu does not submit a food order.'}

    @app.get('/api/v26/admin/shift-notes')
    def shift_notes(request:Request,limit:int=30):
        owner_only(request)
        with Session() as db:
            rows=db.scalars(select(ShiftNote).order_by(ShiftNote.id.desc()).limit(max(1,min(limit,100)))).all()
            return {'notes':[{'id':r.id,'shift':r.shift,'text':r.text,'created_at':r.created_at.isoformat()} for r in rows]}

    @app.post('/api/v26/admin/shift-notes',status_code=201)
    def add_shift_note(payload:ShiftNoteIn,request:Request):
        owner_only(request,write=True)
        with Session.begin() as db:
            row=ShiftNote(shift=payload.shift,text=payload.text)
            db.add(row);db.flush()
            audit(db,'v26.shift_note.created',f'note_id={row.id}')
            note_id=row.id
        return {'id':note_id,'status':'recorded'}

    @app.get('/api/v26/admin/issues')
    def get_issues(request:Request,status:str='all'):
        owner_only(request)
        if status not in ('all','open','in_progress','resolved'):raise HTTPException(422,'Invalid issue status')
        with Session() as db:
            stmt=select(ServiceIssue).order_by(ServiceIssue.id.desc()).limit(100)
            if status!='all':stmt=stmt.where(ServiceIssue.status==status)
            rows=db.scalars(stmt).all()
            return {'issues':[{'id':r.id,'title':r.title,'details':r.details,'severity':r.severity,
                                'status':r.status,'created_at':r.created_at.isoformat()} for r in rows]}

    @app.post('/api/v26/admin/issues',status_code=201)
    def add_issue(payload:IssueIn,request:Request):
        owner_only(request,write=True)
        with Session.begin() as db:
            row=ServiceIssue(**payload.model_dump())
            db.add(row);db.flush()
            audit(db,'v26.issue.created',f'issue_id={row.id} severity={row.severity}')
            item_id=row.id
        return {'id':item_id,'status':'open'}

    @app.patch('/api/v26/admin/issues/{issue_id}')
    def update_issue(issue_id:int,payload:IssueUpdate,request:Request):
        owner_only(request,write=True)
        with Session.begin() as db:
            row=db.get(ServiceIssue,issue_id)
            if not row:raise HTTPException(404,'Issue not found')
            row.status=payload.status
            audit(db,'v26.issue.updated',f'issue_id={issue_id} status={row.status}')
        return {'id':issue_id,'status':payload.status}

    @app.get('/api/v26/admin/release-checks')
    def release_checks(request:Request):
        owner_only(request)
        with Session() as db:
            unapproved=db.scalar(select(func.count(MenuItem.id)).where(MenuItem.published.is_(True),MenuItem.approved.is_(False))) or 0
            tables=db.scalar(select(func.count(Table.id)).where(Table.active.is_(True))) or 0
        checks={'https_base_configured':os.environ.get('PUBLIC_BASE_URL','').startswith('https://'),
                'google_client_configured':bool(os.environ.get('GOOGLE_CLIENT_ID') and os.environ.get('GOOGLE_CLIENT_SECRET')),
                'session_secret_configured':bool(os.environ.get('SESSION_SECRET')),
                'admin_password_configured':bool(os.environ.get('ADMIN_PASSWORD')),
                'owner_approved_menu':unapproved==0,'active_tables_configured':tables>0}
        return {'checks':checks,'all_passed':all(checks.values()),'published_unapproved_menu_count':unapproved,
                'warning':'Configuration checks only, not proof of live OAuth, owner approval or commercial launch readiness.'}

    @app.get('/api/v26/health')
    def health():
        return {'status':'ok','release':'V26 development','production_approved':False}

    return {'ShiftNote':ShiftNote,'ServiceIssue':ServiceIssue}
