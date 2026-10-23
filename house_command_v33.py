"""Wongdhen V33: owner-only operating intelligence and actionable guest inbox.

This module intentionally uses existing database records and permission/session
primitives. It doesn't add fake revenues, alter reservation availability or
introduce new database migrations. All timestamps of restaurant service are
stored as naive Asia/Kolkata wall-clock dates by the V3 booking subsystem.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta, time, timezone
from io import StringIO
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from typing import Literal
from sqlalchemy import select, func, or_, update

LOCAL = ZoneInfo('Asia/Kolkata')
STATUSES = ('new', 'in_progress', 'replied', 'archived')


class TriageChange(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['new', 'in_progress', 'replied', 'archived']
    expected_status: Literal['new', 'in_progress', 'replied', 'archived']


def _as_iso(value):
    return value.isoformat() if value else None


def _safe_csv(value):
    """Prevent spreadsheet formula execution in exported user-authored cells."""
    s = str(value or '').replace('\x00', '')
    if s.lstrip(' \t\r\n').startswith(('=', '+', '-', '@')) or s.startswith(('\t', '\r', '\n')):
        return "'" + s
    return s


def _where_contacts(query, Contact, status, term):
    if status != 'all':
        query = query.where(Contact.status == status)
    if term:
        term = term.strip().lower()
        # Escape SQL LIKE metacharacters, so a literal search never acts as a wildcard.
        term = term.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        needle = f'%{term}%'
        query = query.where(or_(func.lower(Contact.name).like(needle, escape='\\'),
                                func.lower(Contact.subject).like(needle, escape='\\'),
                                func.lower(Contact.email).like(needle, escape='\\')))
    return query


def install_v33(app, Session, owner_only, audit, models, bookings):
    Contact, MenuItem, Gallery, Audit, StaffAccount, Setting = (models[k] for k in
        ('Contact', 'MenuItem', 'Gallery', 'Audit', 'StaffAccount', 'Setting'))
    Reservation, Table, Policy = (bookings[k] for k in ('Reservation', 'Table', 'Policy'))

    @app.get('/api/v33/admin/command', tags=['V33 owner command'])
    def command(request: Request, days: int = Query(7, ge=7, le=30)):
        owner_only(request)
        if days not in (7, 14, 30):
            raise HTTPException(422, 'Choose a 7, 14 or 30 day view')
        day = datetime.now(LOCAL).date()
        start_date = day - timedelta(days=days - 1)
        start = datetime.combine(start_date, time.min)
        stop = datetime.combine(day + timedelta(days=1), time.min)
        next_week = datetime.combine(day + timedelta(days=8), time.min)
        with Session() as db:
            period = db.execute(select(func.date(Reservation.start_at),
                         Reservation.status, func.count(Reservation.id))
                    .where(Reservation.start_at >= start, Reservation.start_at < stop)
                    .group_by(func.date(Reservation.start_at), Reservation.status)).all()
            series = { (str(d), status): int(number) for d, status, number in period}
            status_totals = {}
            daily = []
            for offset in range(days):
                date_key = (start_date + timedelta(days=offset)).isoformat()
                statuses = {}
                count = 0
                for (date_value, status), number in series.items():
                    if date_value == date_key:
                        statuses[status] = number
                        status_totals[status] = status_totals.get(status, 0) + number
                        count += number
                daily.append({'date': date_key, 'count': count, 'statuses': statuses})
            upcoming = db.scalars(select(Reservation)
                .where(Reservation.start_at >= datetime.combine(day, time.min),
                       Reservation.start_at < next_week,
                       Reservation.status.notin_(['cancelled', 'declined', 'no_show']))
                .order_by(Reservation.start_at, Reservation.id).limit(8)).all()
            cnt = lambda mdl, *clauses: int(db.scalar(select(func.count(mdl.id)).where(*clauses)) or 0)
            enquiries = {state: cnt(Contact, Contact.status == state) for state in STATUSES}
            today_count = daily[-1]['count']
            policy = db.get(Policy, 1)
            menu_total = cnt(MenuItem)
            approvals = cnt(MenuItem, MenuItem.published.is_(True), MenuItem.approved.is_(False))
            active_tables = cnt(Table, Table.active.is_(True))
            media = cnt(Gallery, Gallery.published.is_(True), Gallery.rights_confirmed.is_(True))
            team = cnt(StaffAccount, StaffAccount.active.is_(True))
            latest = db.scalars(select(Audit).order_by(Audit.id.desc()).limit(6)).all()
            return {
                'version': 'V33', 'date': day.isoformat(), 'timezone': 'Asia/Kolkata',
                'range_days': days, 'range_start': start_date.isoformat(),
                'summary': {
                    'reservations_period': sum(d['count'] for d in daily),
                    'reservations_today': today_count,
                    'pending_reservations': status_totals.get('pending', 0),
                    'confirmed_reservations': status_totals.get('confirmed', 0),
                    'new_enquiries': enquiries['new'],
                    'open_enquiries': enquiries['new'] + enquiries['in_progress'],
                    'menu_awaiting_approval': approvals,
                    'published_media': media,
                    'active_tables': active_tables,
                    'active_staff': team,
                },
                'daily': daily, 'status_totals': status_totals,
                'enquiry_statuses': enquiries,
                'next_reservations': [
                    {'id': r.id, 'reference': r.reference,
                     'visit_at': _as_iso(r.start_at), 'party_size': r.party_size,
                     'status': r.status, 'table_id': r.table_id,
                     'guest': r.name} for r in upcoming],
                'activity': [{'id': a.id, 'action': a.action,
                              'at': _as_iso(a.created_at)} for a in latest],
                'configuration': {
                    'booking_enabled': bool(policy and policy.enabled),
                    'booking_owner_verified': bool(policy and policy.owner_verified),
                    'menu_total': menu_total,
                    'menu_awaiting_approval': approvals,
                    'active_tables': active_tables,
                    'published_rights_confirmed_media': media,
                },
                'disclaimer': 'Counts are drawn from recorded operational rows. No revenue, conversion, occupied seats or live guest arrivals are inferred.',
            }

    @app.get('/api/v33/admin/enquiries', tags=['V33 guest inbox'])
    def enquiries(request: Request, status: Literal['all','new','in_progress','replied','archived']='all',
                  q: str=Query('', max_length=100), limit: int=Query(20, ge=1, le=50),
                  offset: int=Query(0, ge=0, le=100000)):
        owner_only(request)
        with Session() as db:
            base = _where_contacts(select(Contact), Contact, status, q)
            count = db.scalar(select(func.count()).select_from(base.subquery())) or 0
            rows = db.scalars(base.order_by(Contact.id.desc()).limit(limit).offset(offset)).all()
            return {'total': count, 'offset': offset, 'limit': limit, 'status': status,
                    'items': [{'id': c.id, 'name': c.name, 'email': c.email,
                               'subject': c.subject, 'message': c.message,
                               'status': c.status, 'received_at': _as_iso(c.received_at)}
                              for c in rows]}

    @app.patch('/api/v33/admin/enquiries/{contact_id}', tags=['V33 guest inbox'])
    def triage(contact_id: int, payload: TriageChange, request: Request):
        owner_only(request, write=True)
        with Session() as db:
            item = db.get(Contact, contact_id)
            if item is None:
                raise HTTPException(404, 'Enquiry not found')
            if item.status != payload.expected_status:
                raise HTTPException(409, 'The enquiry changed. Refresh before trying again.')
            if item.status == payload.status:
                return {'id': item.id, 'status': item.status, 'saved': True}
            # Compare-and-swap in one SQL statement; two simultaneous owners
            # cannot silently overwrite the newer status or double-log it.
            result = db.execute(update(Contact).where(
                Contact.id == contact_id, Contact.status == payload.expected_status
            ).values(status=payload.status))
            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(409, 'The enquiry changed. Refresh before trying again.')
            audit(db, 'v33.enquiry.triage',
                  f'enquiry={contact_id} {payload.expected_status}->{payload.status}')
            db.commit()
            return {'id': contact_id, 'status': payload.status, 'saved': True}

    @app.get('/api/v33/admin/audit', tags=['V33 owner command'])
    def audit_log(request: Request, q: str=Query('', max_length=80),
                  limit: int=Query(25, ge=1, le=100), offset: int=Query(0, ge=0, le=100000)):
        owner_only(request)
        with Session() as db:
            statement = select(Audit)
            if q.strip():
                escaped = q.strip().lower().replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                statement = statement.where(func.lower(Audit.action).like(f'%{escaped}%', escape='\\'))
            total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
            rows = db.scalars(statement.order_by(Audit.id.desc()).limit(limit).offset(offset)).all()
            return {'total': total, 'offset': offset, 'limit': limit,
                    'items': [{'id': row.id, 'action': row.action, 'detail': row.detail,
                               'at': _as_iso(row.created_at)} for row in rows]}

    @app.get('/api/v33/admin/enquiries.csv', tags=['V33 guest inbox'])
    def enquiries_export(request: Request, status: Literal['all','new','in_progress','replied','archived']='all',
                         q: str=Query('', max_length=100)):
        owner_only(request)
        # bounded export; large datasets should use offline database export tools
        with Session() as db:
            rows = db.scalars(_where_contacts(select(Contact), Contact, status, q)
                  .order_by(Contact.id.desc()).limit(5000)).all()
            out = StringIO()
            writer = csv.writer(out, lineterminator='\r\n')
            writer.writerow(['ID', 'Received', 'Status', 'Guest name', 'Email', 'Subject', 'Message'])
            for r in rows:
                writer.writerow([_safe_csv(r.id), _safe_csv(_as_iso(r.received_at)),
                                 _safe_csv(r.status), _safe_csv(r.name), _safe_csv(r.email),
                                 _safe_csv(r.subject), _safe_csv(r.message)])
        # BOM improves opening with Excel while keeping UTF-8 text.
        return Response('\ufeff' + out.getvalue(), media_type='text/csv; charset=utf-8',
                        headers={'Content-Disposition': 'attachment; filename="wongdhen-guest-enquiries.csv"',
                                 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})
