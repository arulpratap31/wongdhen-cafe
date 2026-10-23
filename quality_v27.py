"""V27 quality consolidation. All figures are derived from local published or admin-authorized rows.
No guest/customer data is exposed, and audit endpoints are owner-only.
"""
from __future__ import annotations
from datetime import datetime, timezone
from fastapi import Request
from sqlalchemy import select, func


def install_quality(app, Session, MenuItem, Photo, Setting, booking_models, v26_models, owner_only):
    Reservation = booking_models['Reservation']
    Table = booking_models['Table']
    Issue = v26_models['ServiceIssue']
    ShiftNote = v26_models['ShiftNote']

    @app.get('/api/v27/menu/categories')
    def categories():
        """Bounded public category list; no unpublished data or speculative diet claims."""
        with Session() as db:
            groups=db.execute(select(MenuItem.category, func.count(MenuItem.id))
                .where(MenuItem.published.is_(True))
                .group_by(MenuItem.category).order_by(MenuItem.category)).all()
        return {'categories':[{'name':str(name),'count':int(count)} for name,count in groups],
                'total':sum(int(count) for _,count in groups),
                'source_notice':'Published digital menu transcription; prices and ingredients may need owner reconfirmation.'}

    @app.get('/api/v27/admin/quality')
    def owner_quality(request: Request):
        owner_only(request)
        with Session() as db:
            published=db.scalar(select(func.count(MenuItem.id)).where(MenuItem.published.is_(True))) or 0
            approved=db.scalar(select(func.count(MenuItem.id)).where(MenuItem.published.is_(True),MenuItem.approved.is_(True))) or 0
            photographed=db.scalar(select(func.count(Photo.id)).where(Photo.published.is_(True))) or 0
            tables=db.scalar(select(func.count(Table.id)).where(Table.active.is_(True))) or 0
            issues=db.execute(select(Issue.status,func.count(Issue.id)).group_by(Issue.status)).all()
            shifts=db.scalar(select(func.count(ShiftNote.id))) or 0
            booking_status=db.execute(select(Reservation.status,func.count(Reservation.id)).group_by(Reservation.status)).all()
            missing_settings={}
            for k in ('address','hours','phone'):
                row=db.get(Setting,k)
                missing_settings[k]=not bool(row and row.value.strip())
        checks=[
            {'name':'Published menu records', 'state':'review' if published!=approved else 'ok', 'detail':f'{approved} owner-approved of {published} published entries'},
            {'name':'Café contact information', 'state':'review' if any(missing_settings.values()) else 'ok', 'detail':'Missing fields: '+(', '.join(k for k,v in missing_settings.items() if v) or 'none')},
            {'name':'Table configuration','state':'review' if tables==0 else 'ok','detail':f'{tables} active tables configured'},
            {'name':'Photography','state':'review' if photographed==0 else 'ok','detail':f'{photographed} published photo records'},
        ]
        return {'release':'V27 quality development','checked_at_utc':datetime.now(timezone.utc).isoformat(),
                'production_approved':False,'checks':checks,
                'counts':{'published_menu':published,'owner_approved_menu':approved,'published_photos':photographed,
                          'active_tables':tables,'shift_handover_notes':shifts,
                          'service_issues':{str(s):int(c) for s,c in issues},
                          'reservations_by_status':{str(s):int(c) for s,c in booking_status}},
                'notice':'Counts are from this environment only; no live OAuth, payment, capacity or business approval is implied.'}

    @app.get('/api/v27/health')
    def health():
        with Session() as db:
            db.execute(select(func.count(MenuItem.id))).scalar()
        return {'status':'ok','release':'V27 development','database':'reachable','production_approved':False}
