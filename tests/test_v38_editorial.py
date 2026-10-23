"""V38 targeted endpoint and security regression tests with an isolated database."""
import os
os.environ.setdefault('ENVIRONMENT','development')
os.environ.setdefault('SESSION_SECRET','v38-isolated-long-test-session-secret-1111111111111111111')
os.environ.setdefault('ADMIN_USERNAME','v38testowner')
os.environ.setdefault('ADMIN_PASSWORD','v38-unique-test-password-long-and-strong')
os.environ.setdefault('DATABASE_URL','sqlite:////mnt/data/v38_regression_tests.db')
from fastapi.testclient import TestClient
from app import app

def test_v38_public_routes_and_assets():
 with TestClient(app) as c:
  for path in ('/','/atelier','/guestbook','/food-theatre','/static/js/v38-atelier.js','/static/css/v38-atelier.css','/api/v38/editorial','/api/v38/photos','/api/v38/notes'):
   resp=c.get(path);assert resp.status_code==200,(path,resp.text[:300])
  data=c.get('/api/v38/editorial').json()
  assert data['release']=='V38' and data['approved_photo_count']>10
  assert data['spotlight']['photo_url'].startswith('/static/')
  assert c.get('/api/v38/photos?category=not_real').status_code==422

def test_v38_owner_auth_csrf_validation():
 with TestClient(app) as c:
  content={'headline':'An authentic little house','subtitle':'Original café photographs for guests to explore.','photo_id':c.get('/api/v38/editorial').json()['spotlight']['photo_id'],'cta_text':'EXPLORE THE CAFÉ','cta_path':'/food-theatre'}
  assert c.put('/api/v38/admin/editorial',json=content).status_code==401
  assert c.get('/api/v38/admin/notes').status_code==401
  assert c.get('/api/v38/admin/insights').status_code==401
  login=c.post('/api/admin/login',json={'username':os.environ['ADMIN_USERNAME'],'password':os.environ['ADMIN_PASSWORD']})
  assert login.status_code==200,login.text
  csrf=login.json()['csrf'];h={'x-csrf-token':csrf}
  assert c.put('/api/v38/admin/editorial',json=content).status_code==403
  assert c.put('/api/v38/admin/editorial',json={**content,'photo_id':'../../etc/passwd'},headers=h).status_code==422
  assert c.put('/api/v38/admin/editorial',json=content,headers=h).status_code==200
  assert c.get('/api/v38/editorial').json()['spotlight']['headline']==content['headline']
  assert c.get('/api/v38/admin/insights').status_code==200

def test_v38_moderation_consent_and_metrics():
 with TestClient(app) as owner,TestClient(app) as guest:
  note={'first_name':'Jamie','message':'I enjoyed the relaxed atmosphere and photographs.','consent':False}
  assert guest.post('/api/v38/notes',json=note).status_code==422
  note['consent']=True
  assert guest.post('/api/v38/notes',json={**note,'message':'Email me at example@test.com please'}).status_code==422
  assert guest.post('/api/v38/notes',json=note).status_code==202
  assert not any(n.get('message')==note['message'] for n in guest.get('/api/v38/notes').json()['items'])
  assert guest.post('/api/v38/events',json={'event':'atelier_save','consent':False}).status_code==422
  assert guest.post('/api/v38/events',json={'event':'atelier_save','consent':True}).status_code==202
  login=owner.post('/api/admin/login',json={'username':os.environ['ADMIN_USERNAME'],'password':os.environ['ADMIN_PASSWORD']})
  assert login.status_code==200;h={'x-csrf-token':login.json()['csrf']}
  pending=owner.get('/api/v38/admin/notes').json()['items'];item=next(n for n in pending if n['message']==note['message'])
  assert owner.patch(f"/api/v38/admin/notes/{item['id']}",json={'status':'published'}).status_code==403
  assert owner.patch(f"/api/v38/admin/notes/{item['id']}",json={'status':'published'},headers=h).status_code==200
  assert any(n['id']==item['id'] for n in guest.get('/api/v38/notes').json()['items'])
  assert owner.delete(f"/api/v38/admin/notes/{item['id']}",headers=h).status_code==200
  assert not any(n['id']==item['id'] for n in guest.get('/api/v38/notes').json()['items'])
  stats=owner.get('/api/v38/admin/insights').json()
  assert any(r['event']=='atelier_save' for r in stats['counts'])
