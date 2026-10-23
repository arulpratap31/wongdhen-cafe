"""V24 customer accounts: Google OpenID Connect, revocable sessions and owned data.

No Google password or access token is persisted. Google credentials must be provided
by the café's Google Cloud administrator before enabling live sign-in.
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlsplit

import httpx
import jwt
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, delete, select
from sqlalchemy.orm import relationship

THEMES = frozenset('burgundy emerald ivory terracotta jewel francisca orchid biblical garden machine vanilla navy fig oldmoney'.split())
GOOGLE_AUTHORIZE = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN = 'https://oauth2.googleapis.com/token'
GOOGLE_JWKS = 'https://www.googleapis.com/oauth2/v3/certs'


class PreferencePatch(BaseModel):
    theme: str | None = Field(default=None, max_length=30)
    menu_category: str | None = Field(default=None, max_length=120)
    menu_page: int | None = Field(default=None, ge=0, le=2000)
    photo_page: int | None = Field(default=None, ge=0, le=2000)

class PhotoInput(BaseModel):
    photo_id: str = Field(min_length=1, max_length=60, pattern=r'^P\d{4}$')

class ClaimInput(BaseModel):
    manage_token: str = Field(min_length=20, max_length=200)



def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def sha256(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def next_path(value: str) -> str:
    """Permit only non-protocol, safe, local absolute paths."""
    if not value or len(value) > 300 or not value.startswith('/') or value.startswith('//') or '\\' in value or any(ord(c)<32 for c in value):
        return '/account'
    parts=urlsplit(value)
    if parts.scheme or parts.netloc or parts.fragment or parts.path.startswith('//'):
        return '/account'
    return value


def install_customer_accounts(app, Base, engine, Session, MenuItem, booking_models, check_origin, throttle):
    class Customer(Base):
        __tablename__ = 'v24_customers'
        id = Column(Integer, primary_key=True)
        google_sub = Column(String(255), unique=True, index=True, nullable=False)
        email = Column(String(254), nullable=False)
        name = Column(String(120), nullable=False)
        picture = Column(String(700), nullable=False, default='')
        created_at = Column(DateTime, default=utcnow, nullable=False)
        signed_in_at = Column(DateTime, default=utcnow, nullable=False)

    class CustomerSession(Base):
        __tablename__ = 'v24_customer_sessions'
        token_hash = Column(String(64), primary_key=True)
        customer_id = Column(Integer, ForeignKey('v24_customers.id'), nullable=False, index=True)
        csrf_token = Column(String(64), nullable=False)
        expires_at = Column(DateTime, nullable=False)

    class OAuthAttempt(Base):
        __tablename__ = 'v24_oauth_attempts'
        state_hash = Column(String(64), primary_key=True)
        browser_hash = Column(String(64), nullable=False)
        verifier = Column(String(128), nullable=False)
        nonce = Column(String(128), nullable=False)
        next_url = Column(String(300), nullable=False)
        expires_at = Column(DateTime, nullable=False)

    class Preference(Base):
        __tablename__ = 'v24_customer_preferences'
        customer_id = Column(Integer, ForeignKey('v24_customers.id'), primary_key=True)
        theme = Column(String(30), nullable=False, default='')
        menu_category = Column(String(120), nullable=False, default='')
        menu_page = Column(Integer, nullable=False, default=0)
        photo_page = Column(Integer, nullable=False, default=0)
        updated_at = Column(DateTime, nullable=False, default=utcnow)

    class Favorite(Base):
        __tablename__ = 'v24_customer_favorites'
        customer_id = Column(Integer, ForeignKey('v24_customers.id'), primary_key=True)
        menu_item_id = Column(Integer, ForeignKey('menu_items.id'), primary_key=True)
        created_at = Column(DateTime, nullable=False, default=utcnow)

    class PhotoBookmark(Base):
        __tablename__ = 'v24_photo_bookmarks'
        customer_id = Column(Integer, ForeignKey('v24_customers.id'), primary_key=True)
        photo_id = Column(String(60), primary_key=True)
        created_at = Column(DateTime, nullable=False, default=utcnow)

    class ReservationClaim(Base):
        __tablename__ = 'v24_reservation_claims'
        reservation_id = Column(Integer, ForeignKey('v3_reservations.id'), primary_key=True)
        customer_id = Column(Integer, ForeignKey('v24_customers.id'), nullable=False, index=True)
        linked_at = Column(DateTime, nullable=False, default=utcnow)

    Base.metadata.create_all(engine)
    router = APIRouter(prefix='/api/v24', tags=['V24 customer accounts'])
    google_id = os.getenv('GOOGLE_CLIENT_ID', '').strip()
    google_secret = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
    redirect_uri = os.getenv('GOOGLE_REDIRECT_URI', '').strip() or ('http://127.0.0.1:8765/api/v24/auth/google/callback' if os.getenv('ENVIRONMENT') != 'production' else '')
    production = os.getenv('ENVIRONMENT') == 'production'
    configured = bool(google_id and google_secret and redirect_uri)
    if configured:
        uri = urlsplit(redirect_uri)
        if (uri.scheme != 'https' and not (not production and uri.scheme == 'http' and uri.hostname in ('localhost', '127.0.0.1'))) or uri.path != '/api/v24/auth/google/callback' or uri.query or uri.fragment or uri.username or uri.password:
            raise RuntimeError('GOOGLE_REDIRECT_URI must point to the HTTPS callback (local HTTP loopback permitted in development)')

    def set_cookie(response, name, value, age):
        response.set_cookie(name, value, httponly=True, secure=production, samesite='lax', max_age=age, path='/')

    def clear_cookie(response, name):
        response.delete_cookie(name, secure=production, httponly=True, samesite='lax', path='/')

    def session_and_user(db, request):
        token = request.cookies.get('wc_customer', '')
        if len(token) < 40 or len(token) > 200:
            raise HTTPException(401, 'Customer sign-in required')
        session = db.get(CustomerSession, sha256(token))
        if session is None or session.expires_at <= utcnow():
            raise HTTPException(401, 'Customer session expired')
        user = db.get(Customer, session.customer_id)
        if user is None:
            raise HTTPException(401, 'Customer session invalid')
        return session, user

    def require_write(db, request):
        check_origin(request)
        session, user = session_and_user(db, request)
        csrf = request.headers.get('x-csrf-token', '')
        if not csrf or not hmac.compare_digest(csrf, session.csrf_token):
            raise HTTPException(403, 'Invalid customer anti-forgery token')
        return user

    def public_preferences(db, customer_id):
        prefs = db.get(Preference, customer_id)
        if prefs is None:
            prefs = Preference(customer_id=customer_id)
            db.add(prefs)
            db.flush()
        return prefs

    def preferences_dict(prefs):
        return {'theme': prefs.theme, 'menu_category': prefs.menu_category,
                'menu_page': prefs.menu_page, 'photo_page': prefs.photo_page,
                'updated_at': prefs.updated_at.isoformat() if prefs.updated_at else None}

    def favorite_dict(db, customer_id):
        rows = db.scalars(select(MenuItem).join(Favorite, Favorite.menu_item_id == MenuItem.id).where(
            Favorite.customer_id == customer_id, MenuItem.published.is_(True)).order_by(MenuItem.category, MenuItem.name)).all()
        return [{'id': x.id, 'name': x.name, 'category': x.category, 'price_display': x.price_display,
                 'source_page': x.source_page, 'approved': x.approved} for x in rows]

    def claim_dict(reservation):
        return {'reference': reservation.reference, 'visit_date': reservation.start_at.date().isoformat(),
                'visit_time': reservation.start_at.strftime('%H:%M'), 'party_size': reservation.party_size,
                'status': reservation.status}

    @router.get('/auth/config')
    def auth_config():
        return {'google_enabled': configured, 'saved_progress_requires_sign_in': True}

    @router.get('/auth/google/start')
    def google_start(request: Request, next: str = '/account'):
        if not configured:
            raise HTTPException(503, 'Google sign-in is not configured by the café administrator')
        throttle(request, 'customer-google-start', 12, 60)
        state = secrets.token_urlsafe(32)
        browser = secrets.token_urlsafe(32)
        verifier = secrets.token_urlsafe(48)
        nonce = secrets.token_urlsafe(32)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with Session() as db:
            db.add(OAuthAttempt(state_hash=sha256(state), browser_hash=sha256(browser), verifier=verifier,
                                nonce=nonce, next_url=next_path(next), expires_at=utcnow()+timedelta(minutes=10)))
            db.commit()
        args = {'client_id': google_id, 'redirect_uri': redirect_uri, 'response_type': 'code',
                'scope': 'openid email profile', 'state': state, 'nonce': nonce,
                'code_challenge': challenge, 'code_challenge_method': 'S256', 'prompt': 'select_account'}
        response = RedirectResponse(GOOGLE_AUTHORIZE+'?'+urlencode(args), status_code=303)
        response.headers['Cache-Control'] = 'no-store'
        set_cookie(response, 'wc_oauth_flow', browser, 600)
        return response

    @router.get('/auth/google/callback')
    def google_callback(request: Request, state: str = '', code: str = '', error: str = ''):
        if error:
            raise HTTPException(400, 'Google sign-in cancelled or declined')
        if not configured or not code or not state or len(state) > 200 or len(code) > 4096:
            raise HTTPException(400, 'Invalid Google sign-in callback')
        browser = request.cookies.get('wc_oauth_flow', '')
        if len(browser) < 40 or len(browser) > 200:
            raise HTTPException(403, 'Google sign-in browser verification failed')
        # Consume the state in the database before contacting Google to block replay.
        with Session.begin() as db:
            attempt = db.get(OAuthAttempt, sha256(state))
            if (attempt is None or attempt.expires_at <= utcnow() or
                    not hmac.compare_digest(attempt.browser_hash, sha256(browser))):
                raise HTTPException(403, 'Google sign-in state expired or invalid')
            verifier, nonce, destination = attempt.verifier, attempt.nonce, attempt.next_url
            db.delete(attempt)
        try:
            with httpx.Client(timeout=12.0, follow_redirects=False) as client:
                token_response = client.post(GOOGLE_TOKEN, data={
                    'client_id': google_id, 'client_secret': google_secret, 'grant_type': 'authorization_code',
                    'code': code, 'code_verifier': verifier, 'redirect_uri': redirect_uri})
                token_response.raise_for_status()
                token = token_response.json().get('id_token')
            if not isinstance(token, str):
                raise ValueError('Missing ID token')
            signing_key = jwt.PyJWKClient(GOOGLE_JWKS, timeout=8).get_signing_key_from_jwt(token)
            claims = jwt.decode(token, signing_key.key, algorithms=['RS256'], audience=google_id,
                                issuer=['https://accounts.google.com', 'accounts.google.com'], options={'require': ['exp', 'iat', 'iss', 'aud', 'sub']})
            if not isinstance(claims.get('sub'), str) or not claims['sub'] or not hmac.compare_digest(str(claims.get('nonce', '')), nonce):
                raise ValueError('Invalid identity or nonce')
            if claims.get('email_verified') is not True or not isinstance(claims.get('email'), str) or '@' not in claims['email']:
                raise ValueError('Verified email unavailable')
        except (httpx.HTTPError, jwt.PyJWTError, ValueError, KeyError, TypeError) as exc:
            # The upstream response and tokens must never be reflected to clients or logs.
            raise HTTPException(401, 'Google sign-in verification failed') from None
        # Google 'sub', never a matching email address, is the identity key.
        sub = claims['sub'][:255]
        with Session.begin() as db:
            user = db.scalar(select(Customer).where(Customer.google_sub == sub))
            if user is None:
                user = Customer(google_sub=sub, email=claims['email'][:254], name=str(claims.get('name') or 'Guest')[:120],
                                picture=str(claims.get('picture') or '')[:700])
                db.add(user)
                db.flush()
            else:
                user.email, user.name = claims['email'][:254], str(claims.get('name') or 'Guest')[:120]
                user.signed_in_at = utcnow()
                user.picture = str(claims.get('picture') or '')[:700]
            raw_session = secrets.token_urlsafe(48)
            csrf = secrets.token_hex(32)
            db.add(CustomerSession(token_hash=sha256(raw_session), customer_id=user.id,
                                   csrf_token=csrf, expires_at=utcnow()+timedelta(days=14)))
        response = RedirectResponse(next_path(destination), status_code=303)
        response.headers['Cache-Control'] = 'no-store'
        set_cookie(response, 'wc_customer', raw_session, 14*86400)
        clear_cookie(response, 'wc_oauth_flow')
        return response

    @router.get('/me')
    def me(request: Request):
        with Session() as db:
            session, user = session_and_user(db, request)
            p = public_preferences(db, user.id)
            response = {'id': user.id, 'name': user.name, 'email': user.email,
                        'picture': user.picture if user.picture.startswith('https://') else '',
                        'csrf': session.csrf_token, 'preferences': preferences_dict(p),
                        'favorites': favorite_dict(db, user.id),
                        'photos': [b.photo_id for b in db.scalars(select(PhotoBookmark).where(PhotoBookmark.customer_id == user.id)).all()]}
            response['reservations'] = [claim_dict(x) for x in db.scalars(
                select(booking_models['Reservation']).join(ReservationClaim, ReservationClaim.reservation_id == booking_models['Reservation'].id)
                .where(ReservationClaim.customer_id == user.id).order_by(booking_models['Reservation'].start_at.desc())).all()]
            db.commit()
            return response

    @router.patch('/preferences')
    def save_preferences(payload: PreferencePatch, request: Request):
        if payload.theme is not None and payload.theme not in THEMES and payload.theme != '':
            raise HTTPException(422, 'Unknown theme')
        with Session.begin() as db:
            user = require_write(db, request)
            p = public_preferences(db, user.id)
            for field, value in payload.model_dump(exclude_unset=True).items():
                if value is not None:
                    setattr(p, field, value)
            p.updated_at = utcnow()
            return {'saved': True, 'preferences': preferences_dict(p)}

    @router.post('/favorites/{item_id}', status_code=201)
    def add_favorite(item_id: int, request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            item = db.get(MenuItem, item_id)
            if item is None or not item.published:
                raise HTTPException(404, 'Dish unavailable')
            if db.get(Favorite, (user.id, item_id)) is None:
                db.add(Favorite(customer_id=user.id, menu_item_id=item_id))
            return {'saved': True, 'item_id': item_id}

    @router.delete('/favorites/{item_id}')
    def remove_favorite(item_id: int, request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            db.execute(delete(Favorite).where(Favorite.customer_id == user.id, Favorite.menu_item_id == item_id))
            return {'saved': False, 'item_id': item_id}

    @router.post('/photo-bookmarks')
    def add_photo(payload: PhotoInput, request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            # Only allow published photographs from the original photo catalog.
            photo_table = Base.metadata.tables['v10_photo_catalog']
            if not db.execute(select(photo_table.c.id).where(photo_table.c.id == payload.photo_id, photo_table.c.published.is_(True))).first():
                raise HTTPException(404, 'Photo not found')
            if db.get(PhotoBookmark, (user.id, payload.photo_id)) is None:
                db.add(PhotoBookmark(customer_id=user.id, photo_id=payload.photo_id))
            return {'saved': True, 'photo_id': payload.photo_id}

    @router.delete('/photo-bookmarks/{photo_id}')
    def remove_photo(photo_id: str, request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            db.execute(delete(PhotoBookmark).where(PhotoBookmark.customer_id == user.id, PhotoBookmark.photo_id == photo_id))
            return {'saved': False}

    @router.post('/reservations/claim')
    def claim_reservation(payload: ClaimInput, request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            reservation = db.scalar(select(booking_models['Reservation']).where(
                booking_models['Reservation'].token_hash == sha256(payload.manage_token)))
            if reservation is None:
                raise HTTPException(404, 'Reservation token invalid')
            existing = db.get(ReservationClaim, reservation.id)
            if existing is not None and existing.customer_id != user.id:
                raise HTTPException(409, 'Reservation already associated with an account')
            if existing is None:
                db.add(ReservationClaim(reservation_id=reservation.id, customer_id=user.id))
            return {'linked': True, 'reservation': claim_dict(reservation)}

    @router.get('/export')
    def export_customer_data(request: Request):
        with Session() as db:
            session, user = session_and_user(db, request)
            p = public_preferences(db, user.id)
            return {'account': {'name': user.name, 'email': user.email, 'created_at': user.created_at.isoformat()},
                    'preferences': preferences_dict(p), 'favorites': favorite_dict(db, user.id),
                    'photo_bookmarks': [x.photo_id for x in db.scalars(select(PhotoBookmark).where(PhotoBookmark.customer_id == user.id)).all()],
                    'linked_reservations': [x.reservation_id for x in db.scalars(select(ReservationClaim).where(ReservationClaim.customer_id == user.id)).all()]}

    @router.post('/logout')
    def customer_logout(request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            raw = request.cookies.get('wc_customer', '')
            db.execute(delete(CustomerSession).where(CustomerSession.token_hash == sha256(raw), CustomerSession.customer_id == user.id))
        response = RedirectResponse('/account', status_code=303)
        clear_cookie(response, 'wc_customer')
        response.headers['Cache-Control'] = 'no-store'
        return response

    @router.delete('/account')
    def delete_account(request: Request):
        with Session.begin() as db:
            user = require_write(db, request)
            for model in (Favorite, Preference, PhotoBookmark, ReservationClaim, CustomerSession):
                db.execute(delete(model).where(model.customer_id == user.id))
            db.delete(user)
        from fastapi.responses import JSONResponse
        response = JSONResponse({'deleted': True, 'note': 'Past reservation records are retained separately under the café booking retention rules.'})
        clear_cookie(response, 'wc_customer')
        response.headers['Cache-Control'] = 'no-store'
        return response

    app.include_router(router)
    return {'Customer': Customer, 'CustomerSession': CustomerSession, 'OAuthAttempt': OAuthAttempt}
