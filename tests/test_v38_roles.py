"""Security checks: backend permission separation, revocation, and owner financial provenance."""
import os
os.environ.setdefault('ENVIRONMENT','development')
os.environ.setdefault('SESSION_SECRET','v38-isolated-long-test-session-secret-1111111111111111111')
os.environ.setdefault('ADMIN_USERNAME','v38testowner')
os.environ.setdefault('ADMIN_PASSWORD','v38-unique-test-password-long-and-strong')
os.environ.setdefault('DATABASE_URL','sqlite:////mnt/data/v38_regression_tests.db')
from fastapi.testclient import TestClient
from app import app, Session, v8_models
import secrets

def signin(client,username,password):
    r=client.post('/api/admin/login',json={'username':username,'password':password})
    assert r.status_code==200,r.text
    return {'x-csrf-token':r.json()['csrf']}

def test_owner_private_financial_ledger():
    with TestClient(app) as c:
        assert c.get('/api/v38/workspace/owner').status_code==401
        assert c.get('/api/v38/workspace/customers').status_code==401
        assert c.get('/api/v38/workspace/summary').status_code==401
        token=signin(c,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD'])
        assert c.get('/api/v38/workspace/owner').status_code==200
        assert c.get('/api/v38/workspace/customers').status_code==200
        payload={'kind':'revenue','amount_inr':'217.50','category':'dine_in','description':'Verified reconciliation','reference':'ROLETEST-1'}
        assert c.post('/api/v38/workspace/finance',json=payload).status_code==403
        assert c.post('/api/v38/workspace/finance',json={**payload,'category':'rent'},headers=token).status_code==422
        r=c.post('/api/v38/workspace/finance',json=payload,headers=token)
        assert r.status_code==201,r.text
        entry=r.json()['entry']
        assert entry['amount_inr']=='217.5'
        assert c.get('/api/v38/workspace/owner').json()['finance']['record_count']>=1
        assert c.delete('/api/v38/workspace/finance/'+str(entry['id'])).status_code==403
        assert c.delete('/api/v38/workspace/finance/'+str(entry['id']),headers=token).status_code==200

def test_manager_and_staff_permissions_and_revocation():
    with TestClient(app) as owner,TestClient(app) as manager,TestClient(app) as kitchen,TestClient(app) as editor:
        h=signin(owner,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD'])
        creds=[('v38manager','manager'),('v38kitchen','kitchen_staff'),('v38content','content_editor')]
        ids={}
        for username,role in creds:
            r=owner.post('/api/admin/staff',json={'username':username,'password':'long-test-pass-role-2026','role':role},headers=h)
            if r.status_code==409:
                users=owner.get('/api/admin/staff').json()['staff'];ids[username]=next(x['id'] for x in users if x['username']==username)
                owner.patch(f"/api/admin/staff/{ids[username]}",json={'role':role,'active':True,'new_password':'long-test-pass-role-2026'},headers=h)
            else:
                assert r.status_code==201,r.text
                ids[username]=r.json()['id']
        for client,user,role in ((manager,'v38manager','manager'),(kitchen,'v38kitchen','kitchen_staff'),(editor,'v38content','content_editor')):
            signin(client,user,'long-test-pass-role-2026')
            data=client.get('/api/v38/workspace/summary')
            assert data.status_code==200,data.text
            assert data.json()['role']==role
            assert data.json()['capabilities']['can_see_finance'] is False
            for route in ['/api/v38/workspace/owner','/api/v38/workspace/finance','/api/v38/workspace/customers','/api/admin/staff','/api/v38/admin/insights']:
                assert client.get(route).status_code==403,(user,route,client.get(route).status_code)
        assert manager.get('/api/v38/workspace/manager').status_code==200
        assert kitchen.get('/api/v38/workspace/manager').status_code==403
        assert editor.get('/api/v38/workspace/manager').status_code==403
        # Insert a harmless order record in the isolated test DB and verify sensitive
        # monetary/contact information cannot leak into manager/kitchen responses.
        with Session() as db:
            order=v8_models['Order'](reference='ROLETEST-'+secrets.token_hex(6),token_hash=secrets.token_hex(32),
               idempotency_key=secrets.token_hex(16),name='Test guest',contact='private-test@example.com',
               notes='Personal note',status='placed',mode='pickup',total_paise=17500,
               items_json='[{"id":1,"name":"Sample test item","quantity":1,"unit_paise":17500,"subtotal_paise":17500}]')
            db.add(order);db.commit()
        for c in (manager,kitchen):
            resp=c.get('/api/v8/admin/orders')
            assert resp.status_code==200
            item=next(x for x in resp.json()['orders'] if x['reference']==order.reference)
            assert 'contact' not in item and 'total_paise' not in item and 'notes' not in item
            assert all('unit_paise' not in line and 'subtotal_paise' not in line for line in item['items'])
        assert 'name' not in next(x for x in kitchen.get('/api/v8/admin/orders').json()['orders'] if x['reference']==order.reference)
        assert kitchen.get('/api/admin/contacts').status_code==403
        assert editor.get('/api/v8/admin/orders').status_code==403
        assert owner.patch(f"/api/admin/staff/{ids['v38kitchen']}",json={'active':False},headers=h).status_code==200
        assert kitchen.get('/api/v38/workspace/summary').status_code==401
        owner.patch(f"/api/admin/staff/{ids['v38kitchen']}",json={'active':True},headers=h)
