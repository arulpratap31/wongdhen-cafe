"""V40 canonical Windows/development launcher. Run from the project directory."""
from pathlib import Path
import json
import os
import socket
import sys
import time
from urllib.request import urlopen
from dotenv import load_dotenv
from asset_urls import workspace_id

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT / '.env')
HOST='127.0.0.1'
PORT=8765
CANONICAL=f'http://{HOST}:{PORT}'
CALLBACK=CANONICAL+'/api/v24/auth/google/callback'


def check_configuration():
    if os.getenv('ENVIRONMENT','development').lower()=='production':
        raise SystemExit('The local V40 launcher is for development only. Use a secured ASGI deployment for production.')
    if not os.getenv('ADMIN_USERNAME','').strip() or not os.getenv('ADMIN_PASSWORD','').strip():
        raise SystemExit('Set ADMIN_USERNAME and a strong ADMIN_PASSWORD in .env before starting.')
    secret=os.getenv('SESSION_SECRET','')
    if len(secret)<40 or secret.startswith('replace-'):
        raise SystemExit('Set a random SESSION_SECRET of at least 40 characters in .env before starting.')
    google_id=os.getenv('GOOGLE_CLIENT_ID','').strip()
    google_secret=os.getenv('GOOGLE_CLIENT_SECRET','').strip()
    redirect=os.getenv('GOOGLE_REDIRECT_URI','').strip()
    if redirect and redirect!=CALLBACK:
        raise SystemExit('For local use the Google redirect URI must be: '+CALLBACK)
    if google_id and google_secret:
        os.environ['GOOGLE_REDIRECT_URI']=CALLBACK
        print('Google OAuth configured. Redirect URI registered in Google Cloud must be:',CALLBACK,flush=True)
    else:
        print('Google Sign-In is inactive; set BOTH Google Cloud OAuth values in .env.',flush=True)


def project_running():
    try:
        with urlopen(CANONICAL+'/api/v40/local-status',timeout=.75) as response:
            data=json.load(response)
            return (response.status==200 and data.get('release')=='V40'
                    and data.get('workspace_id')==workspace_id()
                    and data.get('owner_layout')=='role-separated')
    except Exception:
        return False


def port_taken():
    try:
        with socket.create_connection((HOST,PORT),timeout=.8):return True
    except OSError:return False


def ready(existing=False):
    print('\n'+'='*63)
    print('WONGDHEN CAFÉ V40 / DEDICATED ROLE PORTALS')
    print('Your local website is ready.')
    print('WEBSITE:',CANONICAL+'/')
    print('LOGIN:  ',CANONICAL+'/admin')
    print('OWNER:  ',CANONICAL+'/owner')
    print('MANAGER:',CANONICAL+'/manager')
    print('STAFF:  ',CANONICAL+'/staff')
    print('ACCOUNT:',CANONICAL+'/account')
    if existing: print('This exact V40 workspace is already running in another window.')
    print('Keep the server window open; Ctrl+C to exit.')
    print('='*63+'\n',flush=True)


def main():
    check_configuration()
    if project_running():
        ready(existing=True)
        try:
            while project_running(): time.sleep(2)
        except KeyboardInterrupt: pass
        return 0
    if port_taken():
        print('Port 8765 is occupied by a different site. Stop the other website before starting V40.',file=sys.stderr)
        return 1
    import uvicorn
    class Server(uvicorn.Server):
        async def startup(self,sockets=None):
            await super().startup(sockets=sockets)
            if self.started: ready()
    server=Server(uvicorn.Config('app:app',host=HOST,port=PORT,reload=False,log_level='info'))
    server.run()
    return 0 if server.started else 1

if __name__=='__main__':
    raise SystemExit(main())
