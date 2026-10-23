"""V28 additive public discovery and owner-only launch quality endpoints.

Business data comes exclusively from stored published source records.
No payment, ingredient, allergy or real-time availability claims are generated.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from fastapi import HTTPException, Query, Request
from sqlalchemy import func, select


def install_signature_v28(app, Session, MenuItem, Setting, booking_models, owner_only, photo_model):
    Table = booking_models['Table']
    Policy = booking_models['Policy']

    def safe_query(value: str) -> str:
        return value.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')

    @app.get('/api/v28/menu/browse')
    def browse_menu(q: str = Query('', max_length=80),
                    category: str = Query('', max_length=120),
                    limit: int = Query(24, ge=1, le=60),
                    offset: int = Query(0, ge=0, le=10000)):
        term = q.strip()
        with Session() as db:
            query = select(MenuItem).where(MenuItem.published.is_(True))
            if category:
                query = query.where(MenuItem.category == category)
            if term:
                query = query.where(MenuItem.name.ilike('%'+safe_query(term)+'%', escape='\\'))
            total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
            rows = db.scalars(query.order_by(MenuItem.category, MenuItem.name, MenuItem.id)
                              .offset(offset).limit(limit)).all()
        return {
            'items': [{'id':row.id,'name':row.name,'category':row.category,
                       'price_display':row.price_display,'source_page':row.source_page,
                       'owner_approved':bool(row.approved)} for row in rows],
            'total':total,'offset':offset,'page_size':limit,
            'has_more':offset+len(rows)<total,
            'data_notice':'Menu transcription from supplied source. Confirm current prices, dietary information and availability with café staff.',
        }

    @app.get('/api/v28/public/readiness')
    def public_readiness():
        """No owner operational details or private customer data in public response."""
        with Session() as db:
            policy = db.get(Policy,1)
            active_tables = db.scalar(select(func.count(Table.id)).where(Table.active.is_(True))) or 0
            booking_enabled = bool(policy and policy.enabled and policy.owner_verified and
                                   policy.opening and policy.closing and policy.opening < policy.closing and active_tables)
        return {'online_booking_requests_enabled':booking_enabled,
                'menu_prices_verified_current':False,
                'message':'Booking requests depend on live owner configuration and must not be treated as confirmed reservations.'}

    @app.get('/api/v28/admin/readiness')
    def owner_readiness(request: Request):
        owner_only(request)
        with Session() as db:
            total = db.scalar(select(func.count(MenuItem.id)).where(MenuItem.published.is_(True))) or 0
            unapproved = db.scalar(select(func.count(MenuItem.id)).where(
                MenuItem.published.is_(True),MenuItem.approved.is_(False))) or 0
            photos = db.scalar(select(func.count(photo_model.id)).where(photo_model.published.is_(True))) or 0
            tables = db.scalar(select(func.count(Table.id)).where(Table.active.is_(True))) or 0
            vals={k:(db.get(Setting,k).value.strip() if db.get(Setting,k) else '')
                  for k in ('address','hours','phone')}
            policy=db.get(Policy,1)
            booking_ready=bool(policy and policy.enabled and policy.owner_verified and
                               policy.opening and policy.closing and policy.opening < policy.closing and tables)
        configured_google=bool(os.getenv('GOOGLE_CLIENT_ID') and os.getenv('GOOGLE_CLIENT_SECRET'))
        checks=[
            ('Menu approvals',unapproved==0 and total>0,f'{unapproved} published entries need owner approval','Review the original menu and approve current descriptions/prices in Menu Management.'),
            ('Business details',all(vals.values()),'Missing: '+(', '.join(k for k,v in vals.items() if not v) or 'none'),'Add verified location, hours, and contact details in Owner Settings.'),
            ('Reservations',booking_ready,'Bookings enabled with verified rules' if booking_ready else 'Not fully configured or disabled','Configure opening hours, policy verification, capacity, and active tables.'),
            ('Published photography',photos>0,f'{photos} published photos','Review authorized café media placements.'),
            ('Google customer sign-in credentials',configured_google,'Configured' if configured_google else 'Not configured','Set the café owner’s OAuth credentials and test the real provider flow.'),
            ('HTTPS public domain',bool(os.getenv('PUBLIC_BASE_URL','').startswith('https://')),'Configured' if os.getenv('PUBLIC_BASE_URL','').startswith('https://') else 'Not configured','Configure a real HTTPS domain before public launch.'),
        ]
        return {'release':'V28 Quality & Experience','checked_at_utc':datetime.now(timezone.utc).isoformat(),
                'checks':[{'name':name,'configured':good,'detail':detail,'next_action':action} for name,good,detail,action in checks],
                'configured_count':sum(int(x[1]) for x in checks),'total_checks':len(checks),
                'production_approved':False,
                'warning':'Configuration is not equivalent to integration/security testing or owner sign-off. No production approval is implied.'}

    @app.get('/api/v28/health')
    def health():
        with Session() as db:
            db.execute(select(func.count(MenuItem.id))).scalar()
        return {'status':'ok','release':'V28 development','production_approved':False}
