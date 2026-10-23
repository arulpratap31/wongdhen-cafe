"""Wongdhen Cafe — functional local/staging application.
Original 16-page menu always available intact. A subset of digital entries is
transcribed from the supplied PDF and is NOT owner-approved for publication.
"""
from __future__ import annotations
import os, re, time, secrets, hmac, hashlib
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Literal
from urllib.parse import urlsplit
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Text, select, func
from sqlalchemy.orm import declarative_base, sessionmaker
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from PIL import Image, UnidentifiedImageError
from io import BytesIO
from seed_menu import SEED
from asset_urls import asset_url, workspace_id

ROOT = Path(__file__).resolve().parent
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///' + str(ROOT / 'data' / 'site.db'))
(ROOT / 'data').mkdir(exist_ok=True)
connect_args = {'check_same_thread': False} if DB_URL.startswith('sqlite:') else {}
engine = create_engine(DB_URL, connect_args=connect_args, pool_pre_ping=True)
Session = sessionmaker(bind=engine, expire_on_commit=False)
Base = declarative_base()

class MenuItem(Base):
    __tablename__ = 'menu_items'
    id = Column(Integer, primary_key=True)
    category = Column(String(120), index=True, nullable=False)
    name = Column(String(240), nullable=False)
    price_display = Column(String(80), nullable=False)
    source_page = Column(Integer, nullable=False)
    approved = Column(Boolean, nullable=False, default=False)
    published = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

class Contact(Base):
    __tablename__ = 'contacts'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(220), nullable=False)
    subject = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    status = Column(String(40), default='new')

class Setting(Base):
    __tablename__ = 'settings'
    key = Column(String(120), primary_key=True)
    value = Column(Text, nullable=False, default='')

class Gallery(Base):
    __tablename__ = 'gallery'
    id = Column(Integer, primary_key=True)
    path = Column(String(300), nullable=False)
    caption = Column(String(250), nullable=False, default='')
    rights_confirmed = Column(Boolean, nullable=False, default=False)
    published = Column(Boolean, nullable=False, default=False)

class Audit(Base):
    __tablename__ = 'audit'
    id = Column(Integer, primary_key=True)
    action = Column(String(120), nullable=False)
    detail = Column(Text, nullable=False, default='')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class StaffAccount(Base):
    __tablename__ = 'v9_staff_accounts'
    id = Column(Integer, primary_key=True)
    username = Column(String(90), nullable=False, unique=True, index=True)
    password_hash = Column(String(180), nullable=False)
    role = Column(String(40), nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    session_version = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))



class OwnerSession(Base):
    """Revocable owner session; no raw cookie is stored in the database."""
    __tablename__ = 'v22_owner_sessions'
    token_hash = Column(String(64), primary_key=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)

def hash_staff_password(password: str) -> str:
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 320000)
    return f'pbkdf2_sha256$320000${salt.hex()}${digest.hex()}'


def verify_staff_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt, expected = encoded.split('$')
        if algorithm != 'pbkdf2_sha256' or int(iterations) > 600000:
            return False
        candidate = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), bytes.fromhex(salt), int(iterations))
        return hmac.compare_digest(candidate, bytes.fromhex(expected))
    except (ValueError, TypeError):
        return False


# Explicit allowlist: staff cannot access any admin route unless granted here.
STAFF_ROUTES = {
    'booking_staff': ('/api/v3/admin/booking/', '/api/v7/admin/occasions', '/api/v8/admin/groups', '/api/v9/admin/booking/calendar'),
    'kitchen_staff': ('/api/v8/admin/orders',),
    'content_editor': ('/api/admin/menu', '/api/admin/media', '/api/v6/admin/', '/api/v8/admin/promo', '/api/v10/admin/photos'),
}
STAFF_ROUTES['manager'] = STAFF_ROUTES['booking_staff'] + STAFF_ROUTES['kitchen_staff'] + STAFF_ROUTES['content_editor'] + (
    '/api/admin/contacts', '/api/v8/admin/overview', '/api/v8/admin/content-health',
    '/api/v8/admin/menu-stock', '/api/v7/admin/queue', '/api/v7/admin/rewards', '/api/v10/admin/photos',
    '/api/v8/admin/ordering/config', '/api/v8/admin/tables', '/api/v9/admin/booking/calendar',
)


def staff_route_allowed(request: Request, role: str) -> bool:
    path = request.url.path
    # Page access is granted per role before the browser receives a management shell.
    # The /admin hub is a login page only, not an exception for management APIs.
    if request.method == 'GET' and path == '/admin':
        return True
    if request.method == 'GET' and path in ROLE_PORTAL_PATHS:
        return role in ROLE_PORTAL_PATHS[path]['roles']
    if path in ('/api/admin/me','/api/admin/logout'):
        return True
    if path == '/api/v38/workspace/summary':
        return True
    if path == '/api/v38/workspace/manager':
        return role == 'manager'
    if path == '/api/v39/manager/checklist' or path.startswith('/api/v39/manager/checklist/'):
        return role == 'manager'
    # Do not permit bulk CSV exports or owner settings through a broad prefix.
    if role == 'booking_staff' and request.method != 'GET' and (path.startswith('/api/v3/admin/booking/tables') or path.startswith('/api/v3/admin/booking/policy')):
        return False
    if '/export/' in path or path.startswith('/api/admin/staff') or path.startswith('/api/admin/settings'):
        return False
    return any(path == prefix.rstrip('/') or path.startswith(prefix.rstrip('/') + '/')
               for prefix in STAFF_ROUTES.get(role, ()))

# Separate, canonical portal URLs. All privileged data remains behind API authorization.
ROLE_PORTAL_PATHS = {
    '/owner': ('admin', 'owner-desk'),
    '/owner/finance': ('admin', 'owner-finance'),
    '/owner/growth': ('admin', 'owner-growth'),
    '/owner/customers': ('admin', 'owner-customers'),
    '/owner/team': ('admin', 'staff'),
    '/owner/editorial': ('admin', 'owner-editorial'),
    '/owner/reservations': ('admin', 'bookings'),
    '/owner/menu': ('admin', 'menu'),
    '/owner/audit': ('admin', 'audit'),
    '/manager': ('manager', 'manager-desk'),
    '/manager/daily': ('manager', 'manager-standards'),
    '/manager/reservations': ('manager', 'bookings'),
    '/manager/calendar': ('manager', 'calendar'),
    '/manager/kitchen': ('manager', 'kitchen'),
    '/manager/menu': ('manager', 'menu'),
    '/manager/inbox': ('manager', 'inbox'),
    '/manager/queue': ('manager', 'walkins'),
    '/staff': (('booking_staff','kitchen_staff','content_editor'), 'staff-desk'),
    '/staff/reservations': ('booking_staff', 'staff-desk'),
    '/staff/reservations/bookings': ('booking_staff', 'bookings'),
    '/staff/reservations/calendar': ('booking_staff', 'calendar'),
    '/staff/reservations/waitlist': ('booking_staff', 'waitlist'),
    '/staff/reservations/queue': ('booking_staff', 'walkins'),
    '/staff/kitchen': ('kitchen_staff', 'staff-desk'),
    '/staff/kitchen/orders': ('kitchen_staff', 'kitchen'),
    '/staff/content': ('content_editor', 'staff-desk'),
    '/staff/content/menu': ('content_editor', 'menu'),
    '/staff/content/photos': ('content_editor', 'v10-media'),
    '/staff/content/upload': ('content_editor', 'media'),
}
ROLE_PORTAL_PATHS = {path:{'roles':(roles,) if isinstance(roles,str) else roles,'tab':tab} for path,(roles,tab) in ROLE_PORTAL_PATHS.items()}
ROLE_HOME = {'admin':'/owner','manager':'/manager','booking_staff':'/staff/reservations',
             'kitchen_staff':'/staff/kitchen','content_editor':'/staff/content'}

Base.metadata.create_all(engine)
with Session() as db:
    if not db.scalar(select(func.count(MenuItem.id))):
        for cat, name, price, page in SEED:
            db.add(MenuItem(category=cat,name=name,price_display=price,source_page=page,approved=False,published=True))
        db.commit()
    for k,v in {'address':'','hours':'','phone':'+91 81301 33279','instagram':'https://www.instagram.com/wongdhencafe/','ordering_url':'','bookings_enabled':'false','menu_version_confirmed':'false','v19_site_theme':'burgundy','v19_allow_visitor_switch':'true'}.items():
        if db.get(Setting,k) is None: db.add(Setting(key=k,value=v))
    db.commit()

app = FastAPI(title='Wongdhen Café — V40 Dedicated Role Portals', docs_url=None, redoc_url=None)
# Compress text assets and HTML; browsers receive the exact same content.
app.add_middleware(GZipMiddleware, minimum_size=1100)
@app.middleware('http')
async def v8_security_headers(request:Request, call_next):
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='strict-origin-when-cross-origin'
    response.headers['X-Frame-Options']='DENY'
    response.headers['Permissions-Policy']='camera=(), microphone=(), geolocation=()'
    response.headers['Cross-Origin-Resource-Policy']='same-origin'
    response.headers['X-Permitted-Cross-Domain-Policies']='none'
    if os.environ.get('ENVIRONMENT')=='production' and request.url.scheme=='https':
        response.headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
    if request.url.path == '/admin' or request.url.path in ROLE_PORTAL_PATHS or request.url.path.startswith('/api/v33/admin/') or request.url.path.startswith('/api/v32/admin/') or request.url.path.startswith('/api/v28/public/readiness') or request.url.path.startswith('/api/v38/admin/') or request.url.path.startswith('/api/v39/owner/') or request.url.path.startswith('/api/v39/manager/') or request.url.path.startswith('/api/v38/notes') or request.url.path.startswith('/api/v24') or request.url.path.startswith('/account') or request.url.path.startswith('/api/admin') or '/admin/' in request.url.path or request.url.path.startswith('/api/v8/ordering/track'):
        response.headers['Cache-Control']='no-store'
    if request.url.path.startswith('/static/') and request.method=='GET' and response.status_code==200:
        # Code must revalidate, including dependencies of the owner dashboard.
        # Images can retain their normal browser cache.
        if request.url.path.endswith(('.js', '.css')):
            response.headers['Cache-Control']='no-cache, must-revalidate'
        else:
            response.headers.setdefault('Cache-Control','public, max-age=3600')
    return response

app.mount('/static', StaticFiles(directory=str(ROOT / 'static')), name='static')
templates = Jinja2Templates(directory=str(ROOT / 'templates'))
templates.env.globals['asset'] = asset_url
SESSION_KEY = os.environ.get('SESSION_SECRET') or secrets.token_hex(32)
serializer = URLSafeTimedSerializer(SESSION_KEY, salt='wongdhen-admin-session')
PRODUCTION = os.environ.get('ENVIRONMENT') == 'production'
# Owner development permission is already granted. Production requires security secrets,
# but is not blocked by a separate owner-approval environment flag.
if PRODUCTION:
    if not os.environ.get('SESSION_SECRET') or not os.environ.get('ADMIN_PASSWORD'):
        raise RuntimeError('Production requires SESSION_SECRET and ADMIN_PASSWORD')

# Single-instance minimal traffic throttle; use Redis or a gateway when deploying multiple instances.
seen = defaultdict(deque)
def throttle(request: Request, bucket: str, n: int = 12, seconds: int = 60):
    ip = request.client.host if request.client else 'local'
    key = (bucket, ip)
    now = time.monotonic()
    q = seen[key]
    while q and q[0] < now-seconds: q.popleft()
    if len(q) >= n: raise HTTPException(429, 'Too many requests. Please retry later.')
    q.append(now)

def check_origin(request: Request):
    origin = request.headers.get('origin')
    if origin:
        parsed = urlsplit(origin)
        if parsed.scheme not in ('https', 'http') or parsed.username or parsed.password or not parsed.hostname:
            raise HTTPException(403, 'Cross-site request blocked')
        # Compare effective host and port; disallow spoofed host/userinfo origin.
        supplied_host = request.headers.get('host', '')
        if parsed.netloc.lower() != supplied_host.lower():
            raise HTTPException(403, 'Cross-site request blocked')


def authenticated(request: Request):
    token = request.cookies.get('wc_session','')
    if not token:raise HTTPException(401,'Admin sign-in required')
    try: body = serializer.loads(token, max_age=60*60*8)
    except (BadSignature,SignatureExpired):raise HTTPException(401,'Session expired')
    if body.get('role') == 'admin':
        sid=body.get('sid','')
        if not isinstance(sid,str) or len(sid)!=64:raise HTTPException(401,'Owner session expired')
        with Session() as db:
            record=db.get(OwnerSession,hashlib.sha256(sid.encode()).hexdigest())
            if record is None or record.expires_at.replace(tzinfo=timezone.utc)<datetime.now(timezone.utc):
                raise HTTPException(401,'Owner session expired or revoked')
        return body
    if body.get('role') not in STAFF_ROUTES or not body.get('staff_id'):
        raise HTTPException(403,'Insufficient permissions')
    with Session() as db:
        user = db.get(StaffAccount, body['staff_id'])
        if (user is None or not user.active or user.role != body.get('role') or
                not hmac.compare_digest(user.session_version, body.get('session_version',''))):
            raise HTTPException(401,'Staff session expired or account disabled')
    if not staff_route_allowed(request, body['role']):
        raise HTTPException(403,'Staff role does not permit this operation')
    return body

def admin_write(request: Request):
    check_origin(request)
    body = authenticated(request)
    token = request.headers.get('x-csrf-token','')
    if not token or not hmac.compare_digest(token,body.get('csrf','')):
        raise HTTPException(403,'Invalid anti-forgery token')
    return body

def item_dict(x):
    return {'id':x.id,'category':x.category,'name':x.name,'price_display':x.price_display,
            'source_page':x.source_page,'approved':x.approved,'published':x.published}

def audit(db,action,detail=''):
    db.add(Audit(action=action,detail=detail[:1000]))

@app.get('/api/status')
def status():
    # Source-of-truth is the V3 policy rather than a hard-coded availability claim.
    with Session() as db:
        model = booking_models['Policy']
        tables = booking_models['Table']
        p = db.get(model, 1)
        inventory = db.scalar(select(func.count(tables.id)).where(tables.active.is_(True)))
        booking_live = bool(p and p.enabled and p.owner_verified and p.opening and p.closing
                            and p.opening < p.closing and inventory)
    return {'status':'staging','menu_pdf_pages':16,'menu_current_prices_confirmed':False,
            'online_reservations_enabled':booking_live,'booking_v3_config_endpoint':'/api/v3/booking/config',
            'commercial_release_approved':False}

@app.get('/api/menu')
def menu(q: str='', category: str='', limit: int=2000):
    if len(q) > 80 or len(category) > 120:
        raise HTTPException(422, 'Menu search values are too long')
    with Session() as db:
        stmt=select(MenuItem).where(MenuItem.published.is_(True)).order_by(MenuItem.category,MenuItem.name)
        if category: stmt=stmt.where(MenuItem.category==category)
        if q:
            safe_q=q.replace('\\','\\\\').replace('%','\\%').replace('_','\\_')
            stmt=stmt.where(MenuItem.name.ilike('%'+safe_q+'%',escape='\\'))
        rows=db.scalars(stmt.limit(min(max(limit,1),5000))).all()
        categories=db.scalars(select(MenuItem.category).where(MenuItem.published.is_(True)).distinct().order_by(MenuItem.category)).all()
        summaries=visual_details['summary_map'](db,rows)
    return {'items':[dict(item_dict(x),**summaries.get(x.id,{'has_approved_photo':False,'thumbnail_url':None,'dietary_class':'unconfirmed'})) for x in rows],'categories':categories,'prices_status':'From uploaded PDF; not yet confirmed as current by the owner','complete':False}

@app.get('/api/settings')
def public_settings():
    with Session() as db:
        vals={x.key:x.value for x in db.scalars(select(Setting)).all()}
    return {k:vals.get(k,'') for k in ('address','hours','phone','instagram','ordering_url','bookings_enabled','menu_version_confirmed')}

class ContactIn(BaseModel):
    name: str = Field(min_length=2,max_length=120)
    email: str = Field(min_length=5,max_length=220)
    subject: str = Field(min_length=3,max_length=200)
    message: str = Field(min_length=10,max_length=3000)
    website: str = ''

# V21 — fourteen carefully art-directed themes. V19 endpoint remains backwards compatible.
V21_THEMES = ('burgundy', 'emerald', 'ivory', 'terracotta', 'jewel', 'francisca', 'orchid', 'biblical', 'garden', 'machine', 'vanilla', 'navy', 'fig', 'oldmoney')

@app.get('/api/v21/appearance')
def v21_public_appearance():
    with Session() as db:
        default = db.get(Setting, 'v21_site_theme')
        allow = db.get(Setting, 'v21_allow_visitor_switch')
        previous = db.get(Setting, 'v19_site_theme')
        previous_allow = db.get(Setting, 'v19_allow_visitor_switch')
    chosen = default.value if default and default.value in V21_THEMES else (previous.value if previous and previous.value in V21_THEMES else 'burgundy')
    return {'default_theme':chosen,
            'allow_visitor_switch':(allow.value if allow else (previous_allow.value if previous_allow else 'true'))=='true',
            'themes':list(V21_THEMES)}

class V21AppearanceIn(BaseModel):
    default_theme: Literal['burgundy', 'emerald', 'ivory', 'terracotta', 'jewel', 'francisca', 'orchid', 'biblical', 'garden', 'machine', 'vanilla', 'navy', 'fig', 'oldmoney']
    allow_visitor_switch: bool = True

@app.patch('/api/admin/v21/appearance')
def v21_save_appearance(payload: V21AppearanceIn, request: Request):
    admin_write(request)
    with Session() as db:
        for key,value in [('v21_site_theme',payload.default_theme),
                          ('v21_allow_visitor_switch','true' if payload.allow_visitor_switch else 'false')]:
            item=db.get(Setting,key)
            if item is None:db.add(Setting(key=key,value=value))
            else:item.value=value
        audit(db,'appearance.v21.update',payload.default_theme+' visitor_switch='+str(payload.allow_visitor_switch))
        db.commit()
    return {'saved':True,'default_theme':payload.default_theme,'allow_visitor_switch':payload.allow_visitor_switch}

# V19 — owner-controlled global appearance, persisted in existing Settings model.
V19_THEMES = ('burgundy', 'emerald', 'ivory', 'terracotta')

@app.get('/api/v19/appearance')
def v19_public_appearance():
    with Session() as db:
        selected = db.get(Setting, 'v19_site_theme')
        allow = db.get(Setting, 'v19_allow_visitor_switch')
    selected_name = selected.value if selected and selected.value in V19_THEMES else 'burgundy'
    return {'default_theme': selected_name, 'allow_visitor_switch': bool(allow and allow.value == 'true'),
            'themes': list(V19_THEMES)}

class V19AppearanceIn(BaseModel):
    default_theme: Literal['burgundy', 'emerald', 'ivory', 'terracotta']
    allow_visitor_switch: bool = True

@app.patch('/api/admin/appearance')
def v19_save_appearance(payload: V19AppearanceIn, request: Request):
    admin_write(request)  # Staff roles have no appearance-setting permission.
    with Session() as db:
        for key,value in [('v19_site_theme', payload.default_theme),
                          ('v19_allow_visitor_switch', 'true' if payload.allow_visitor_switch else 'false')]:
            row = db.get(Setting, key)
            if row is None: db.add(Setting(key=key, value=value))
            else: row.value = value
        audit(db, 'appearance.update', payload.default_theme + ' switching=' + str(payload.allow_visitor_switch))
        db.commit()
    return {'saved': True, 'default_theme': payload.default_theme,
            'allow_visitor_switch': payload.allow_visitor_switch}

@app.post('/api/contact')
def contact(payload:ContactIn,request:Request):
    throttle(request,'contact',4,300);check_origin(request)
    if payload.website: return {'received':True}
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',payload.email):raise HTTPException(422,'Enter a valid email address')
    with Session() as db:
        entry=Contact(name=payload.name.strip(),email=payload.email.strip(),subject=payload.subject.strip(),message=payload.message.strip())
        db.add(entry); db.commit()
        return {'received':True,'reference':entry.id,'note':'Message saved to the website inbox; email forwarding is not configured.'}

class LoginIn(BaseModel):
    username:str
    password:str

@app.post('/api/admin/login')
def login(payload:LoginIn,request:Request):
    throttle(request,'admin_login',20,300);check_origin(request)
    username=os.environ.get('ADMIN_USERNAME','owner')
    password=os.environ.get('ADMIN_PASSWORD','')
    is_owner=bool(password and hmac.compare_digest(payload.username,username) and hmac.compare_digest(payload.password,password))
    csrf=secrets.token_urlsafe(32)
    if is_owner:
        sid=secrets.token_hex(32)
        with Session() as db:
            db.add(OwnerSession(token_hash=hashlib.sha256(sid.encode()).hexdigest(),expires_at=datetime.now(timezone.utc)+timedelta(hours=8)))
            db.commit()
        body={'role':'admin','csrf':csrf,'sid':sid}
    else:
        with Session() as db:
            staff=db.scalar(select(StaffAccount).where(StaffAccount.username==payload.username))
            # Evaluate a dummy strong hash to make unknown-user behavior similar.
            if staff is None or not staff.active or not verify_staff_password(payload.password,staff.password_hash):
                raise HTTPException(401,'Invalid credentials')
            body={'role':staff.role,'staff_id':staff.id,'session_version':staff.session_version,'csrf':csrf}
    response=JSONResponse({'signed_in':True,'csrf':csrf,'role':body['role']})
    response.set_cookie('wc_session',serializer.dumps(body),httponly=True,
                        secure=PRODUCTION,samesite='strict',max_age=60*60*8,path='/')
    return response

@app.get('/api/admin/me')
def admin_me(request:Request):
    data=authenticated(request)
    return {'authenticated':True,'csrf':data['csrf'],'role':data['role']}

@app.post('/api/admin/logout')
def logout(request:Request):
    body=admin_write(request)
    if body.get('role')=='admin' and body.get('sid'):
        with Session() as db:
            session=db.get(OwnerSession,hashlib.sha256(body['sid'].encode()).hexdigest())
            if session is not None:db.delete(session);db.commit()
    resp=JSONResponse({'signed_out':True});resp.delete_cookie('wc_session',path='/');return resp

class StaffCreate(BaseModel):
    username: str = Field(min_length=3, max_length=90, pattern=r'^[A-Za-z0-9_.-]+$')
    password: str = Field(min_length=14, max_length=128)
    role: Literal['manager','booking_staff','kitchen_staff','content_editor']


class StaffChange(BaseModel):
    role: Literal['manager','booking_staff','kitchen_staff','content_editor'] | None = None
    active: bool | None = None
    new_password: str | None = Field(default=None, min_length=14, max_length=128)


def owner_only(request: Request, write: bool=False):
    identity=admin_write(request) if write else authenticated(request)
    if identity['role'] != 'admin':
        raise HTTPException(403,'Only the owner can manage staff accounts')


@app.get('/api/admin/staff')
def staff_list(request: Request):
    owner_only(request)
    with Session() as db:
        rows=db.scalars(select(StaffAccount).order_by(StaffAccount.username)).all()
        return {'staff':[{'id':x.id,'username':x.username,'role':x.role,'active':x.active,
                          'created_at':x.created_at.isoformat() if x.created_at else ''} for x in rows]}


@app.post('/api/admin/staff',status_code=201)
def staff_create(payload: StaffCreate,request: Request):
    owner_only(request,write=True)
    if payload.username.lower() == os.environ.get('ADMIN_USERNAME','owner').lower():
        raise HTTPException(409,'This username is reserved for the owner')
    with Session() as db:
        if db.scalar(select(StaffAccount).where(func.lower(StaffAccount.username)==payload.username.lower())):
            raise HTTPException(409,'Username already exists')
        row=StaffAccount(username=payload.username,password_hash=hash_staff_password(payload.password),
                         role=payload.role,active=True,session_version=secrets.token_hex(24))
        db.add(row);db.flush();audit(db,'staff.create',f'{row.id}:{row.role}');db.commit()
        return {'id':row.id,'username':row.username,'role':row.role,'active':row.active}


@app.patch('/api/admin/staff/{staff_id}')
def staff_change(staff_id: int,payload: StaffChange,request: Request):
    owner_only(request,write=True)
    if payload.role is None and payload.active is None and payload.new_password is None:
        raise HTTPException(422,'No changes supplied')
    with Session() as db:
        row=db.get(StaffAccount,staff_id)
        if row is None:raise HTTPException(404,'Staff account not found')
        if payload.role is not None:row.role=payload.role
        if payload.active is not None:row.active=payload.active
        if payload.new_password is not None:row.password_hash=hash_staff_password(payload.new_password)
        row.session_version=secrets.token_hex(24)  # Immediately revoke existing sessions.
        audit(db,'staff.update',f'{row.id}:{row.role} active={row.active}')
        db.commit()
        return {'id':row.id,'username':row.username,'role':row.role,'active':row.active,'sessions_revoked':True}

@app.get('/api/admin/menu')
def admin_menu(request:Request):
    authenticated(request)
    with Session() as db:
        rows=db.scalars(select(MenuItem).order_by(MenuItem.category,MenuItem.name)).all()
        summaries=visual_details['summary_map'](db,rows)
        return {'items':[dict(item_dict(x),**summaries.get(x.id,{'has_approved_photo':False,'thumbnail_url':None,'dietary_class':'unconfirmed'})) for x in rows]}

class MenuIn(BaseModel):
    category:str=Field(min_length=2,max_length=120)
    name:str=Field(min_length=2,max_length=240)
    price_display:str=Field(min_length=1,max_length=80)
    source_page:int=Field(ge=1,le=16)
    approved:bool=False
    published:bool=False

@app.post('/api/admin/menu')
def admin_add_menu(payload:MenuIn,request:Request):
    admin_write(request)
    with Session() as db:
        item=MenuItem(**payload.model_dump());db.add(item);audit(db,'menu.create',payload.name)
        db.commit();return item_dict(item)

@app.patch('/api/admin/menu/{item_id}')
def admin_edit_menu(item_id:int,payload:MenuIn,request:Request):
    admin_write(request)
    with Session() as db:
        item=db.get(MenuItem,item_id)
        if item is None:raise HTTPException(404,'Menu item not found')
        for k,v in payload.model_dump().items():setattr(item,k,v)
        item.updated_at=datetime.now(timezone.utc)
        audit(db,'menu.update',f'{item_id} {payload.name}');db.commit();return item_dict(item)

@app.get('/api/admin/contacts')
def admin_contacts(request:Request):
    authenticated(request)
    with Session() as db:
        rows=db.scalars(select(Contact).order_by(Contact.id.desc()).limit(300)).all()
        return {'contacts':[{'id':x.id,'name':x.name,'email':x.email,'subject':x.subject,
             'message':x.message,'received_at':x.received_at.isoformat() if x.received_at else '', 'status':x.status} for x in rows]}

class SettingsIn(BaseModel):
    address:str=Field(max_length=300)
    hours:str=Field(max_length=250)
    phone:str=Field(max_length=60)
    instagram:str=Field(max_length=300)
    ordering_url:str=Field(max_length=300)

@app.patch('/api/admin/settings')
def edit_settings(payload:SettingsIn,request:Request):
    admin_write(request)
    with Session() as db:
        for k,v in payload.model_dump().items():db.get(Setting,k).value=v.strip()
        audit(db,'settings.update');db.commit()
    return {'saved':True}

@app.post('/api/admin/media')
async def upload_media(request:Request,file:UploadFile=File(...),caption:str=Form(''),rights_confirmed:bool=Form(False)):
    admin_write(request)
    if not rights_confirmed:raise HTTPException(422,'Commercial rights must be confirmed before uploading')
    data=await file.read(8_000_001)
    if len(data)>8_000_000:raise HTTPException(413,'Maximum file size 8 MB')
    try:
        im=Image.open(BytesIO(data));im.verify()
        im=Image.open(BytesIO(data))
        if im.width*im.height>30_000_000:raise HTTPException(422,'Image too large')
        im=im.convert('RGB')
    except (UnidentifiedImageError,ValueError,OSError):raise HTTPException(422,'Invalid image')
    name=secrets.token_hex(12)+'.webp'
    im.thumbnail((2200,2200));im.save(ROOT/'static/images'/name,'WEBP',quality=86)
    with Session() as db:
        x=Gallery(path='/static/images/'+name,caption=caption[:250],rights_confirmed=True,published=True)
        db.add(x);audit(db,'media.upload',name);db.commit()
        return {'saved':True,'url':x.path}

@app.get('/api/gallery')
def gallery():
    builtins=[
        {'path':'/static/images/hero-night.webp','caption':'Wongdhen Cafe · Evening interior'},
        {'path':'/static/images/interior-day.webp','caption':'Wongdhen Cafe · Dining space'},
        {'path':'/static/images/bakery.webp','caption':'Wongdhen Cafe · Bakery counter'},
        {'path':'/static/images/coffee-dessert.webp','caption':'Wongdhen Cafe · Coffee and cake'},
        {'path':'/static/images/drinks.webp','caption':'Wongdhen Cafe · Drinks'},
        {'path':'/static/images/interior-side.webp','caption':'Wongdhen Cafe · Seating area'},
    ]
    with Session() as db:
        builtins.extend({'path':x.path,'caption':x.caption} for x in db.scalars(select(Gallery).where(Gallery.published.is_(True), Gallery.rights_confirmed.is_(True))).all())
    return {'images':builtins}

from visual_menu import install_visual_menu
visual_details = install_visual_menu(app, Base, engine, Session, MenuItem, authenticated, admin_write, audit, ROOT)

from reservations import install_reservations
booking_models = install_reservations(app, Base, engine, Session, authenticated, admin_write, throttle, check_origin, audit)

from v7 import install_v7
v7_models = install_v7(app, Base, engine, Session, MenuItem, booking_models, authenticated, admin_write, check_origin, throttle, audit, ROOT)

from v8 import install_v8
v8_models = install_v8(app, Base, engine, Session, MenuItem, booking_models, visual_details, authenticated, admin_write, throttle, audit, SESSION_KEY)

@app.get('/api/v9/admin/booking/calendar')
def v9_booking_calendar(request: Request, start: date, end: date):
    """Date-scoped restaurant-local reservation calendar; no synthetic capacity."""
    authenticated(request)
    if end < start or (end - start).days > 62:
        raise HTTPException(422, 'Choose a chronological range of at most 63 days')
    Reservation = booking_models['Reservation']
    from sqlalchemy import and_
    with Session() as db:
        rows = db.scalars(select(Reservation).where(and_(
            Reservation.start_at >= datetime.combine(start, datetime.min.time()),
            Reservation.start_at < datetime.combine(end + timedelta(days=1), datetime.min.time())
        )).order_by(Reservation.start_at)).all()
    days = {}
    for item in rows:
        key=item.start_at.date().isoformat()
        block=days.setdefault(key, {'date':key,'total':0,'statuses':{},'guests':0})
        block['total']+=1
        block['statuses'][item.status]=block['statuses'].get(item.status,0)+1
        if item.status not in ('cancelled','declined','no_show'):
            block['guests']+=item.party_size
    return {'timezone':'Asia/Kolkata','start':start.isoformat(),'end':end.isoformat(),
            'days':list(days.values()),
            'reservations':[{'id':x.id,'reference':x.reference,'date':x.start_at.date().isoformat(),
              'time':x.start_at.strftime('%H:%M'),'status':x.status,'party_size':x.party_size,
              'name':x.name,'table_id':x.table_id} for x in rows]}


# V22 House Edition: privileged operations and guest planning. These endpoints
# derive real states from stored records; they never invent live seat availability.
from pydantic import ConfigDict

class V22EnquiryState(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: Literal['new','in_progress','replied','archived']

@app.get('/api/v22/admin/operations')
def v22_operations(request: Request):
    owner_only(request)
    with Session() as db:
        from sqlalchemy import case
        counts = {k:db.scalar(select(func.count(Contact.id)).where(Contact.status==k)) or 0
                  for k in ('new','in_progress','replied','archived')}
        latest = db.scalars(select(Audit).order_by(Audit.id.desc()).limit(15)).all()
        menu_total = db.scalar(select(func.count(MenuItem.id))) or 0
        menu_approved = db.scalar(select(func.count(MenuItem.id)).where(MenuItem.approved.is_(True))) or 0
        photos = db.scalar(select(func.count(Gallery.id)).where(Gallery.published.is_(True))) or 0
    return {'enquiries':counts, 'menu':{'total':menu_total,'approved':menu_approved},
            'owner_uploaded_photos':photos,
            'audit':[{'id':a.id,'action':a.action,'when':a.created_at.isoformat() if a.created_at else ''}
                     for a in latest],
            'note':'Internal recorded activity only; no invented booking or revenue totals.'}

@app.patch('/api/v22/admin/contacts/{contact_id}/status')
def v22_update_enquiry(contact_id:int,payload:V22EnquiryState,request:Request):
    owner_only(request,write=True)
    with Session() as db:
        item=db.get(Contact,contact_id)
        if item is None:raise HTTPException(404,'Enquiry not found')
        before=item.status
        item.status=payload.status
        audit(db,'contact.triage',f'enquiry={contact_id} {before}->{payload.status}')
        db.commit()
        return {'saved':True,'id':contact_id,'status':payload.status}

@app.get('/api/v22/guest-guide')
def v22_guest_guide():
    with Session() as db:
        facts={k:(db.get(Setting,k).value if db.get(Setting,k) else '')
               for k in ('address','hours','phone','instagram')}
        approved_count=db.scalar(select(func.count(MenuItem.id)).where(MenuItem.approved.is_(True),MenuItem.published.is_(True))) or 0
    booking=status()['online_reservations_enabled']
    return {'location':'Majnu Ka Tila, New Delhi',
            'business':facts,
            'menu_items_approved':approved_count,
            'booking_state':'configured_live' if booking else 'not_live',
            'booking_note':'Contact the café directly when online booking is not live.',
            'paths':{'menu':'/menu','photos':'/gallery','visit':'/visit','enquiry':'/contact'}}

@app.get('/robots.txt')
def robots():
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse('User-agent: *\nDisallow: /admin\nDisallow: /api/\n' +
       ('Disallow: /\n' if os.environ.get('ENVIRONMENT')!='production' else 'Allow: /\n'))

@app.get('/sitemap.xml')
def sitemap(request:Request):
    from fastapi.responses import Response
    if os.environ.get('ENVIRONMENT')!='production':
        raise HTTPException(404,'Sitemap is available only on production')
    # Use the configured domain; never trust arbitrary incoming Host headers for SEO metadata.
    canonical=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
    if not canonical.startswith('https://'):raise HTTPException(503,'PUBLIC_BASE_URL must be an HTTPS URL')
    paths=['','experience-guide','atelier','guestbook','living-house','food-theatre','about','menu','gallery','photo-book','journal','discover','tour','reels','visit','reservations','contact','compare','group-events']
    import xml.sax.saxutils as xs
    content='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+xs.escape(canonical+'/'+p)+'</loc></url>' for p in paths)+'</urlset>'
    return Response(content,media_type='application/xml')

@app.get('/menu-pdf')
def menu_pdf():return FileResponse(ROOT/'static/menu/wongdhen-original-16-pages.pdf',media_type='application/pdf',filename='Wongdhen-Cafe-Complete-Menu.pdf')


# Photography catalog stays isolated from original booking, menu and commerce systems.
from v10_photos import install_v10
v10_photo_model = install_v10(app, Base, engine, Session, Gallery, authenticated, admin_write, audit, ROOT)
from premium_discovery import install_grand_maison
install_grand_maison(app, Session, MenuItem, v10_photo_model, Contact, booking_models, ROOT, owner_only)
from v11_photos import install_v11
install_v11(app, Session, v10_photo_model, ROOT)
from v13_photos import install_v13
install_v13(app, Session, v10_photo_model, ROOT)

# Customer sessions use separate cookies, identities and authorization from the owner system.
from customer_accounts import install_customer_accounts
customer_models = install_customer_accounts(app, Base, engine, Session, MenuItem, booking_models, check_origin, throttle)

@app.get('/api/v32/admin/pulse', tags=['V32 owner operations'])
def v32_owner_pulse(request: Request):
    """A privacy-aware, owner-only view of *recorded* operations, never projections."""
    from zoneinfo import ZoneInfo
    owner_only(request)
    Reservation = booking_models['Reservation']
    Table = booking_models['Table']
    today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
    start = datetime.combine(today, datetime.min.time())
    stop = start + timedelta(days=1)
    window_start = start - timedelta(days=6)
    with Session() as db:
        seven = {str(day)[:10]:count for day,count in db.execute(
            select(func.date(Reservation.start_at), func.count(Reservation.id))
            .where(Reservation.start_at >= window_start, Reservation.start_at < stop)
            .group_by(func.date(Reservation.start_at))).all()}
        statuses = dict(db.execute(select(Reservation.status, func.count(Reservation.id))
                       .where(Reservation.start_at >= start, Reservation.start_at < stop)
                       .group_by(Reservation.status)).all())
        recent = db.scalars(select(Audit).order_by(Audit.id.desc()).limit(8)).all()
        return {
            'release':'V32', 'day':today.isoformat(), 'timezone':'Asia/Kolkata',
            'today_reservations':sum(statuses.values()),
            'status_counts':statuses,
            'seven_day_reservations':[
                {'date':(today-timedelta(days=6-offset)).isoformat(),
                 'count':seven.get((today-timedelta(days=6-offset)).isoformat(),0)}
                for offset in range(7)],
            'unreviewed_enquiries':db.scalar(select(func.count(Contact.id)).where(Contact.status == 'new')) or 0,
            'pending_menu_approvals':db.scalar(select(func.count(MenuItem.id)).where(
                MenuItem.published.is_(True),MenuItem.approved.is_(False))) or 0,
            'active_tables':db.scalar(select(func.count(Table.id)).where(Table.active.is_(True))) or 0,
            'recent_activity':[{'action':row.action, 'at':row.created_at.isoformat() if row.created_at else ''}
                               for row in recent],
            'notice':'Recorded operational data only: reservations do not imply arrivals, earnings or availability.'
        }

# V33 House Command: owner-only operational intelligence and active guest inbox.
from house_command_v33 import install_v33
install_v33(app, Session, owner_only, audit, {
    'Contact': Contact, 'MenuItem': MenuItem, 'Gallery': Gallery,
    'Audit': Audit, 'StaffAccount': StaffAccount, 'Setting': Setting
}, booking_models)

@app.get('/api/v31/local-status', tags=['V31 single-origin setup'])
def v31_local_status(request: Request):
    # Report only nonsecret public runtime capabilities; never return credentials.
    if PRODUCTION:
        raise HTTPException(404, 'Not found')
    return {'release': 'V31', 'canonical_origin': 'http://127.0.0.1:8765',
            'running_origin': f'{request.url.scheme}://{request.url.netloc}',
            'correct_port': request.url.port == 8765 and request.url.hostname == '127.0.0.1',
            'customer_account_path': '/account', 'staff_portal_path': '/admin',
            'google_configured': bool(os.getenv('GOOGLE_CLIENT_ID', '').strip() and
                                      os.getenv('GOOGLE_CLIENT_SECRET', '').strip()),
            'note': 'Google login needs the callback registered in Google Cloud and a complete live flow test.'}

# V37: owner-managed public visual defaults. Never store credentials or user profiles here.
class V37ExperienceIn(BaseModel):
    lighting: Literal['day','evening'] = 'evening'
    motion: Literal['auto','subtle','reduced'] = 'auto'


@app.get('/api/v37/experience', tags=['V37 living house'])
def v37_experience():
    with Session() as db:
        light=db.get(Setting,'v37_lighting')
        motion=db.get(Setting,'v37_motion')
        return {'release':'V37',
                'lighting':light.value if light and light.value in ('day','evening') else 'evening',
                'motion':motion.value if motion and motion.value in ('auto','subtle','reduced') else 'auto'}


@app.patch('/api/v37/admin/experience', tags=['V37 living house'])
def v37_set_experience(payload: V37ExperienceIn, request: Request):
    owner_only(request,write=True)
    with Session() as db:
        for key,value in [('v37_lighting',payload.lighting),('v37_motion',payload.motion)]:
            row=db.get(Setting,key)
            if row is None:db.add(Setting(key=key,value=value))
            else:row.value=value
        audit(db,'v37.experience.update',f'lighting={payload.lighting} motion={payload.motion}')
        db.commit()
    return {'saved':True,'lighting':payload.lighting,'motion':payload.motion}


@app.get('/api/v38/local-status', tags=['V38 local workspace verification'])
def v38_local_status(request: Request):
    if PRODUCTION:raise HTTPException(404,'Not found')
    return {'release':'V38','workspace_id':workspace_id(),'owner_layout':'role-separated',
            'owner_financial_reporting':'manual ledger; no simulated POS payments',
            'manager_workspace':True,'staff_limited_access':True,
            'customer_directory':'owner-only','editorial_pages':['/atelier','/guestbook'],
            'google_configured':bool(os.getenv('GOOGLE_CLIENT_ID','').strip() and os.getenv('GOOGLE_CLIENT_SECRET','').strip())}

@app.get('/api/v37/local-status', tags=['V37 living house'])
def v37_local_status(request: Request):
    if PRODUCTION:
        raise HTTPException(404, 'Not found')
    return {'release':'V37','workspace_id':workspace_id(),'owner_layout':'canonical-workspace',
            'experience_pages':['/living-house','/food-theatre','/moments','/plan-your-moment'],
            'google_configured':bool(os.getenv('GOOGLE_CLIENT_ID','').strip() and os.getenv('GOOGLE_CLIENT_SECRET','').strip()),
            'photo_experience':'authentic photographic interpretation; not a real 360 scan',
            'note':'Google OAuth must be configured and live-tested separately.'}

@app.get('/api/v36/local-status', tags=['V36 single-origin setup'])
def v36_local_status(request: Request):
    if PRODUCTION:
        raise HTTPException(404, 'Not found')
    return {'release':'V36','canonical_origin':'http://127.0.0.1:8765',
            'workspace_id':workspace_id(),'owner_layout':'canonical-workspace',
            'google_configured':bool(os.getenv('GOOGLE_CLIENT_ID','').strip() and os.getenv('GOOGLE_CLIENT_SECRET','').strip()),
            'notice':'Google sign-in requires Google Cloud credentials and live OAuth verification.'}

@app.get('/api/v35/local-status', tags=['V35 single-origin setup'])
def v35_local_status(request: Request):
    """Expose a non-secret build marker so operators can detect an old local server."""
    if PRODUCTION:
        raise HTTPException(404, 'Not found')
    return {
        'release': 'V35',
        'canonical_origin': 'http://127.0.0.1:8765',
        'running_origin': f'{request.url.scheme}://{request.url.netloc}',
        'correct_port': request.url.port == 8765 and request.url.hostname == '127.0.0.1',
        'owner_path': '/admin',
        'workspace_id': workspace_id(),
        'owner_layout': 'canonical-workspace',
        'note': 'The launcher must match this project before reusing a running server.'
    }


from imperial_v26 import install_imperial
v26_models = install_imperial(app, Base, engine, Session, MenuItem, booking_models, owner_only, audit, ROOT, SESSION_KEY, check_origin, throttle)

from quality_v27 import install_quality
install_quality(app, Session, MenuItem, v10_photo_model, Setting, booking_models, v26_models, owner_only)

from signature_v28 import install_signature_v28
install_signature_v28(app, Session, MenuItem, Setting, booking_models, owner_only, v10_photo_model)

from taste_studio_v29 import install_taste_studio_v29
install_taste_studio_v29(app, Session, MenuItem, Setting)

# V38: original-media editorial, moderated guest notes, optional aggregate insights.
from v38_editorial import install_v38
v38_models = install_v38(app, Base, engine, Session, Setting, owner_only, admin_write, throttle, check_origin, audit, ROOT)

# Dedicated and server-authorized owner, manager, and staff dashboards.
from v38_role_portals import install_role_portals
v38_roles = install_role_portals(app, Base, engine, Session, authenticated, owner_only, admin_write, audit,
                                 StaffAccount, Contact, MenuItem, booking_models, v8_models, customer_models)

@app.get('/api/v40/local-status')
def v40_status():
    return {'release':'V40','mode':'local development','status':'ok','portal_count':len(ROLE_PORTAL_PATHS),
            'roles':list(ROLE_HOME),'owner':'/owner','manager':'/manager','staff':'/staff'}

@app.get('/api/v39/local-status')
def v39_local_status():
    return {'release':'V39','mode':'local development','status':'ok','workspace_id':workspace_id(),'owner_layout':'role-separated'}

# V39: owner growth studio and daily manager standards; backend roles are authoritative.
from v39_growth import install_v39
v39_models = install_v39(app, Base, engine, Session, owner_only, admin_write, authenticated,
                         audit, Contact, booking_models['Reservation'], ROOT)

@app.get('/{page:path}',response_class=HTMLResponse)
def pages(request:Request,page:str=''):
    portal_path = '/'+page
    portal = ROLE_PORTAL_PATHS.get(portal_path)
    if portal:
        # Anonymous requests receive a role-specific sign-in screen, never private data.
        # A valid session for another role is forbidden at the server boundary.
        try:
            identity=authenticated(request)
        except HTTPException as e:
            if e.status_code != 401:
                raise
        else:
            if identity['role'] not in portal['roles']:
                raise HTTPException(403,'This workspace belongs to another role')
    accepted={'','experience-guide','atelier','guestbook','living-house','food-theatre','moments','plan-your-moment','taste-studio','about','menu','gallery','experience','visit','photo-book','journal','lookbook','contact','admin','reservations','manage-booking','discover','tour','reels','rewards','queue','privacy','terms','compare','order','group-events','checkin','concierge','account'}
    if page == 'menu/original':return RedirectResponse('/menu',status_code=307)
    if page not in accepted and portal is None:raise HTTPException(404,'Page not found')
    # Structured data is deliberately limited to recorded café facts; no fake reviews or hours.
    import json
    facts={}
    with Session() as db:
        for key in ('address','hours','phone'):
            setting=db.get(Setting,key)
            if setting and setting.value.strip():facts[key]=setting.value.strip()
    structured={'@context':'https://schema.org','@type':'CafeOrCoffeeShop','name':'Wongdhen Cafe'}
    if facts.get('phone'):structured['telephone']=facts['phone']
    if facts.get('address'):structured['address']={'@type':'PostalAddress','streetAddress':facts['address']}
    base_url=os.environ.get('PUBLIC_BASE_URL','').rstrip('/')
    if base_url.startswith('https://'):
        structured['url']=base_url+'/'
        structured['hasMenu']=base_url+'/menu'
    structured_json=json.dumps(structured,ensure_ascii=False).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    descriptions={
        'experience-guide':('Plan Your Café Visit — Wongdhen Café','Browse genuine café imagery, explore the menu, and find a clear next step for visiting Wongdhen Café.'),
        'atelier':('The Living Atelier — Wongdhen Café','Explore real café photography, curate dishes from the published menu, make a postcard and experience Wongdhen in a new way.'),
        'guestbook':('Guestbook — Wongdhen Café','Read moderated guest-submitted notes and share a small memory with consent.'),
        'home':('Wongdhen Café — Food, Coffee & Moments in Majnu Ka Tila','Discover Wongdhen Café through original photographs of its food, café ambience and welcoming spaces.'),
        'lookbook':('The Wongdhen Atelier — Editorial Photographic Spreads','Explore original Wongdhen Café photography reimagined as curated editorial spreads.'),
        'gallery':('Wongdhen Café — 100-Photo Editorial Gallery','Explore 100 original Wongdhen Café photographs of people, ambience, food and café moments.'),
        'menu':('Wongdhen Café — Interactive Menu Book','Open our interactive digital menu book to explore actual Wongdhen Café menu entries, coffee and desserts.'),
        'about':('About Wongdhen Café — Our Photographic Story','Get to know Wongdhen Café through 50 genuine photographs and editorial chapters.'),
        'visit':('Visit Wongdhen Café — Delhi Location & Visual Tour','Plan a visit to Wongdhen Café in Majnu Ka Tila, New Delhi, and explore 75 original photographs.'),
        'photo-book':('Wongdhen Café — Interactive 75-Photo Book','Explore 75 original Wongdhen Café photographs in an interactive editorial photo book.'),
        'journal':('Wongdhen Café — 100-Photo Visual Journal','Read Wongdhen Café’s visual journal through 100 original photographs in five editorial chapters.'),
        'concierge':('Wongdhen Café — The House Guide','Choose your café experience with a curated guide to the genuine menu, photos and location.'),
        'taste-studio':('Taste & Visit Studio — Explore Wongdhen Café', 'Explore published Wongdhen Café dishes, build a personal dining shortlist, and plan your visit with real café information.'),
        'account':('My Wongdhen — Saved Menu, Themes & Reservations','Secure customer account, saved menu favorites and visits with Wongdhen Café.'),
        'living-house':('The Living House — Immersive Café Photography','Explore Wongdhen Café through atmospheric three-dimensional arrangements of authentic café photographs.'),
        'food-theatre':('Food Theatre — Wongdhen Café Menu Discovery','Search published menu items and build a shareable dining shortlist, using verified dish photos where available.'),
        'moments':('Create Your Café Moodboard — Wongdhen Café','Choose original Wongdhen café images and create a personal photo moodboard.'),
        'plan-your-moment':('Plan Your Moment — Visit Wongdhen Café','Plan a café outing, find published visiting details and explore actual reservation options.'),
    }
    title,description=descriptions.get(page or 'home',('Wongdhen Café — Majnu Ka Tila, New Delhi','Discover Wongdhen Café, its original menu, ambience, photo gallery and café experience.'))
    if portal:
        label = ('Owner' if portal['roles']==('admin',) else 'Manager' if portal['roles']==('manager',) else 'Team')
        title=f'{label} Workspace — Wongdhen Café'
        description=f'Private {label.lower()} portal. Access is controlled by assigned staff permissions.'
    elif page == 'admin':
        title='Team Sign-in — Wongdhen Café'
        description='Secure access for owner, management and authorized team members.'
    with Session() as theme_db:
        site_appearance = theme_db.get(Setting, 'v21_site_theme') or theme_db.get(Setting, 'v19_site_theme')
        site_theme_default = site_appearance.value if site_appearance and site_appearance.value in V21_THEMES else 'burgundy'
    return templates.TemplateResponse(request,'site.html',{'page':'admin' if portal else page or 'home','portal_route':portal_path if portal else ('/admin' if page=='admin' else ''),'portal_tab':portal['tab'] if portal else '', 'portal_roles':','.join(portal['roles']) if portal else '', 'staging':not PRODUCTION,'site_theme_default':site_theme_default,
                       'structured_json':structured_json,'page_title':title,'page_description':description})
