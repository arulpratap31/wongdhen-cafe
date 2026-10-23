"""V25 Grand Maison — public, data-backed discovery and owner-safe exports.
Only published original menu/photo records are searchable. No fabricated food or venue metadata.
"""
from __future__ import annotations
import csv
import io
import json
from datetime import datetime, timedelta, time
from zoneinfo import ZoneInfo
from pathlib import Path

from fastapi import HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import select, or_, func

PUBLIC_PAGES = (
    ('The Menu', 'Explore the original café menu', '/menu', 'menu'),
    ('Gallery', 'Original café photography', '/gallery', 'photography'),
    ('Photo Book', 'An editorial collection of photographs', '/photo-book', 'photography'),
    ('Visual Journal', 'Café moments and editorial collections', '/journal', 'photography'),
    ('The House Guide', 'Explore Wongdhen Café', '/concierge', 'guide'),
    ('About Wongdhen', 'Discover the café through its story and photography', '/about', 'guide'),
    ('Visit Wongdhen', 'Location and practical visitor information', '/visit', 'guide'),
    ('Table Reservations', 'Request and manage reservations', '/reservations', 'booking'),
    ('My Wongdhen', 'Saved dishes, themes and photographs', '/account', 'account'),
    ('Food Discovery', 'Explore real dishes from the published menu', '/discover', 'menu'),
)


def install_grand_maison(app, Session, MenuItem, Photo, Contact, booking_models, root: Path, owner_only):
    manifest = json.loads((root/'docs'/'V10_MEDIA_MANIFEST.json').read_text(encoding='utf-8'))
    sources = {photo['id']: photo for photo in manifest}

    @app.get('/api/v25/search')
    def grand_search(q: str = '', scope: str = 'all', limit: int = 8):
        """Search published records. Search is bounded and read-only."""
        query = ' '.join(q.strip().split())
        if len(query) > 80:
            raise HTTPException(422, 'Search term must be 80 characters or fewer')
        if scope not in ('all', 'menu', 'photos', 'pages'):
            raise HTTPException(422, 'Unknown search scope')
        limit = max(1, min(limit, 12))
        if not query:
            return {'query':'', 'results':[], 'suggestions':list(PUBLIC_PAGES[:5]), 'scope':scope}
        if len(query) < 2:
            return {'query':query, 'results':[], 'suggestions':[], 'scope':scope}
        # Escape SQL LIKE metacharacters: searching % must not enumerate the catalog.
        pattern = '%' + query.replace('\\','\\\\').replace('%','\\%').replace('_','\\_') + '%'
        results = []
        if scope in ('all', 'pages'):
            for title, description, href, category in PUBLIC_PAGES:
                if query.casefold() in (title + ' ' + description + ' ' + category).casefold():
                    results.append({'kind':'page','title':title,'subtitle':description,'href':href,'category':category})
            results = results[:limit]
        with Session() as db:
            if scope in ('all', 'menu'):
                items = db.scalars(select(MenuItem).where(MenuItem.published.is_(True), or_(
                    MenuItem.name.ilike(pattern, escape='\\'), MenuItem.category.ilike(pattern, escape='\\')))
                    .order_by(MenuItem.category,MenuItem.name,MenuItem.id).limit(limit)).all()
                results += [{'kind':'dish','title':i.name,'subtitle':i.category+' · '+i.price_display,
                              'href':'/menu?item='+str(i.id),'category':i.category,'source_page':i.source_page,
                              'price_is_current_verified':False} for i in items]
            if scope in ('all','photos'):
                photos = db.scalars(select(Photo).where(Photo.published.is_(True),or_(
                    Photo.caption.ilike(pattern,escape='\\'), Photo.category.ilike(pattern,escape='\\')))
                    .order_by(Photo.featured.desc(),Photo.display_order,Photo.id).limit(limit)).all()
                for p in photos:
                    src = sources.get(p.id)
                    if src:
                        results.append({'kind':'photo','title':p.caption or p.category.title(),
                                        'subtitle':p.category.title()+' photograph', 'href':'/gallery',
                                        'category':p.category,'thumbnail':src['optimized_paths']['thumb'], 'photo_id':p.id})
        return {'query':query,'results':results[:limit*3], 'suggestions':[], 'scope':scope,
                'notice':'Digital menu prices and dietary information require current owner verification.'}

    @app.get('/api/v25/admin/menu-export')
    def owner_menu_export(request: Request):
        # Owner-only; not permitted for staff, and does not include customer data.
        owner_only(request)
        out=io.StringIO(newline='')
        writer=csv.writer(out)
        writer.writerow(['id','category','name','price_display','source_page','owner_approved','public'])
        def excel_safe(value):
            text=str(value if value is not None else '')
            # Spreadsheet applications can execute formulas from imported CSVs.
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        with Session() as db:
            rows=db.scalars(select(MenuItem).order_by(MenuItem.id)).all()
            for item in rows:
                writer.writerow([item.id,excel_safe(item.category),excel_safe(item.name),excel_safe(item.price_display),
                                 item.source_page,'yes' if item.approved else 'no', 'yes' if item.published else 'no'])
        resp=Response(out.getvalue(), media_type='text/csv; charset=utf-8', headers={
            'Content-Disposition':'attachment; filename="wongdhen-menu-owner-export.csv"',
            'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff'})
        return resp

    @app.get('/api/v25/admin/daily-brief')
    def owner_daily_brief(request: Request):
        """Actual operational counts, not projected revenue or fabricated table availability."""
        owner_only(request)
        cafe_today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
        begin = datetime.combine(cafe_today, time.min)
        end = begin + timedelta(days=1)
        Reservation = booking_models['Reservation']
        with Session() as db:
            statuses = dict(db.execute(select(Reservation.status,func.count(Reservation.id))
                       .where(Reservation.start_at >= begin,Reservation.start_at < end)
                       .group_by(Reservation.status)).all())
            new_enquiries = db.scalar(select(func.count(Contact.id)).where(Contact.status == 'new')) or 0
            not_verified = db.scalar(select(func.count(MenuItem.id)).where(
                MenuItem.published.is_(True),MenuItem.approved.is_(False))) or 0
            photos = db.scalar(select(func.count(Photo.id)).where(Photo.published.is_(True))) or 0
        return {'local_date':cafe_today.isoformat(),'timezone':'Asia/Kolkata',
                'booking_status_counts':statuses, 'total_reservations':sum(statuses.values()),
                'unreviewed_contact_enquiries':new_enquiries,
                'published_menu_entries_awaiting_price_approval':not_verified,
                'published_photographs':photos,
                'metrics_notice':'Actual database counts only. Not revenue, occupancy, table availability, or business forecasts.'}
