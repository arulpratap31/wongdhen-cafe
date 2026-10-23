"""Focused V39 regression tests on a disposable database; no real sales or customers."""
import os,secrets
os.environ.setdefault('ENVIRONMENT','development')
os.environ.setdefault('SESSION_SECRET','v39-isolated-long-test-session-secret-1111111111111111111')
os.environ.setdefault('ADMIN_USERNAME','v39testowner')
os.environ.setdefault('ADMIN_PASSWORD','v39-unique-test-password-long-and-strong')
os.environ.setdefault('DATABASE_URL','sqlite:////mnt/data/v39_test_isolated.db')
from fastapi.testclient import TestClient
from app import app


def sign(client,user,pw):
    resp=client.post('/api/admin/login',json={'username':user,'password':pw})
    assert resp.status_code==200,resp.text
    return {'x-csrf-token':resp.json()['csrf']}


def test_v39_public_guide_and_campaign_ownership():
    with TestClient(app) as owner, TestClient(app) as guest:
        assert guest.get('/experience-guide').status_code==200
        assert guest.get('/static/css/v39-hospitality.css').status_code==200
        assert guest.get('/api/v39/public/campaigns').status_code==200
        assert guest.get('/api/v39/owner/insights').status_code==401
        token=sign(owner,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD'])
        stats=owner.get('/api/v39/owner/insights').json()
        assert stats['enquiries']['current']==0
        assert stats['reservation_requests']['current']==0
        slug='v39-audit-'+secrets.token_hex(3)
        payload={'slug':slug,'title':'An evening at Wongdhen','description':'Explore genuine café atmosphere with original photography.','cta':'PLAN YOUR VISIT','destination':'/visit','picture':'house','published':False}
        assert guest.post('/api/v39/owner/campaigns',json=payload).status_code==401
        assert owner.post('/api/v39/owner/campaigns',json=payload).status_code==403
        assert owner.post('/api/v39/owner/campaigns',json={**payload,'picture':'bad'},headers=token).status_code==422
        resp=owner.post('/api/v39/owner/campaigns',json=payload,headers=token)
        assert resp.status_code==201,resp.text
        campaign=resp.json()['campaign']
        assert not any(x['slug']==slug for x in guest.get('/api/v39/public/campaigns').json()['items'])
        assert owner.post('/api/v39/owner/campaigns',json=payload,headers=token).status_code==409
        assert owner.patch('/api/v39/owner/campaigns/'+str(campaign['id']),json={'published':True}).status_code==403
        assert owner.patch('/api/v39/owner/campaigns/'+str(campaign['id']),json={'published':True},headers=token).status_code==200
        assert any(x['slug']==slug for x in guest.get('/api/v39/public/campaigns').json()['items'])
        assert owner.patch('/api/v39/owner/campaigns/'+str(campaign['id']),json={'published':False},headers=token).status_code==200


def test_v39_manager_tasks_and_owner_separation():
    with TestClient(app) as owner,TestClient(app) as manager,TestClient(app) as staff:
        owner_csrf=sign(owner,os.environ['ADMIN_USERNAME'],os.environ['ADMIN_PASSWORD'])
        manager_name='v39mgr'+secrets.token_hex(3)
        staff_name='v39kit'+secrets.token_hex(3)
        for name,role in [(manager_name,'manager'),(staff_name,'kitchen_staff')]:
            r=owner.post('/api/admin/staff',json={'username':name,'password':'long-test-password-v39-2026','role':role},headers=owner_csrf)
            assert r.status_code==201,r.text
        m_token=sign(manager,manager_name,'long-test-password-v39-2026')
        sign(staff,staff_name,'long-test-password-v39-2026')
        assert manager.get('/api/v39/owner/campaigns').status_code==403
        assert manager.get('/api/v39/owner/insights').status_code==403
        assert staff.get('/api/v39/manager/checklist').status_code==403
        assert staff.put('/api/v39/manager/checklist/arrival',json={'done':True},headers=m_token).status_code==403
        assert manager.get('/api/v39/manager/checklist').status_code==200
        assert owner.get('/api/v39/manager/checklist').status_code==200
        assert manager.put('/api/v39/manager/checklist/arrival',json={'done':True}).status_code==403
        assert manager.put('/api/v39/manager/checklist/missing',json={'done':True},headers=m_token).status_code==404
        assert manager.put('/api/v39/manager/checklist/arrival',json={'done':True},headers=m_token).status_code==200
        today=manager.get('/api/v39/manager/checklist').json()
        assert today['items'][0]['done'] is True
        assert manager.put('/api/v39/manager/checklist/arrival',json={'done':False},headers=m_token).status_code==200
        assert manager.get('/api/v39/manager/checklist').json()['items'][0]['done'] is False
