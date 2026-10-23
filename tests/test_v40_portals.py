"""V40 multi-portal routing, session protection, and role-specific destinations."""
import os
import secrets
os.environ.setdefault('ENVIRONMENT','development')
os.environ.setdefault('DATABASE_URL','sqlite:////mnt/data/v40_isolated_test.db')
os.environ.setdefault('SESSION_SECRET','v40-test-session-secret-with-strong-unique-entropy-2026')
os.environ.setdefault('ADMIN_USERNAME','v40owner')
os.environ.setdefault('ADMIN_PASSWORD','v40-unique-strong-owner-test-password')
from fastapi.testclient import TestClient
from app import app, ROLE_PORTAL_PATHS, ROLE_HOME


def login(client, username, password):
    res=client.post('/api/admin/login',json={'username':username,'password':password})
    assert res.status_code==200, res.text
    return {'x-csrf-token':res.json()['csrf']}


def test_portal_anonymous_separate_pages_and_assets():
    with TestClient(app) as c:
        assert c.get('/api/v40/local-status').json()['release']=='V40'
        assert c.get('/admin').status_code==200
        for url, details in ROLE_PORTAL_PATHS.items():
            r=c.get(url)
            assert r.status_code==200,(url,r.status_code,r.text[:250])
            assert 'data-page="admin"' in r.text
            assert f'data-portal-route="{url}"' in r.text
            assert 'no-store' in r.headers.get('cache-control','')
            assert 'noindex' in r.text
            assert 'v40-portals.js' in r.text
            assert 'v40-portals.css' in r.text
        for url in ['/staff/payroll','/manager/revenue','/owner/secret']:
            assert c.get(url).status_code==404
        for asset in ['/static/js/v40-portals.js','/static/css/v40-portals.css']:
            assert c.get(asset).status_code==200


def test_owner_manager_and_staff_isolation():
    usernames={}
    with TestClient(app) as owner,TestClient(app) as mgr,TestClient(app) as reception,TestClient(app) as kitchen,TestClient(app) as content:
        csrf=login(owner,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD'])
        role_accounts=[('manager',mgr),('booking_staff',reception),('kitchen_staff',kitchen),('content_editor',content)]
        for role, client in role_accounts:
            user='v40'+secrets.token_hex(4)
            result=owner.post('/api/admin/staff',json={'username':user,'password':'v40-long-unique-test-password-2026','role':role},headers=csrf)
            assert result.status_code==201,result.text
            usernames[role]=(user,result.json()['id'])
            login(client,user,'v40-long-unique-test-password-2026')
        assert owner.get('/owner/finance').status_code==200
        assert owner.get('/api/v38/workspace/owner').status_code==200
        assert owner.get('/manager').status_code==403
        for role,client in role_accounts:
            assert client.get(ROLE_HOME[role]).status_code==200,role
            for uri in ['/owner','/owner/finance','/api/v38/workspace/owner','/api/v38/workspace/customers']:
                assert client.get(uri).status_code==403,(role,uri)
            assert client.get('/api/v38/workspace/summary').json()['role']==role
        assert mgr.get('/manager/daily').status_code==200
        assert mgr.get('/staff/reservations').status_code==403
        assert mgr.get('/staff/kitchen').status_code==403
        assert reception.get('/staff/reservations/calendar').status_code==200
        assert reception.get('/staff/content').status_code==403
        assert reception.get('/staff/kitchen').status_code==403
        assert kitchen.get('/staff/kitchen/orders').status_code==200
        assert kitchen.get('/staff/reservations').status_code==403
        assert content.get('/staff/content/photos').status_code==200
        assert content.get('/manager').status_code==403
        assert kitchen.get('/api/v8/admin/orders').status_code==200
        assert kitchen.get('/api/admin/staff').status_code==403
        # A role change invalidates the previous session, including its HTML page access.
        username,staff_id=usernames['kitchen_staff']
        upd=owner.patch(f'/api/admin/staff/{staff_id}',json={'active':False},headers=csrf)
        assert upd.status_code==200,upd.text
        assert kitchen.get('/api/v38/workspace/summary').status_code==401
        # Revoked cookies cannot retrieve data; the page only displays a login prompt.
        assert kitchen.get('/staff/kitchen').status_code==200
