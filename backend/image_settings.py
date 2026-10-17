"""Local image setup and a cancellable probe, separate from film production."""
import threading
import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from . import images, setup
from .config import settings
from .credentials import CredentialError
from .operations import Operation, OperationCancelled

router=APIRouter(prefix='/api/settings/images')
operation=None
thread=None
task={'status':'idle','message':'Noch kein Testbild erzeugt.'}


def preview_path(identifier):
    if not isinstance(identifier,str) or len(identifier)!=32 or any(c not in '0123456789abcdef' for c in identifier):
        raise HTTPException(404,'Testbild nicht gefunden.')
    root=settings.data_dir/'image-previews'
    target=root/(identifier+'.png')
    if root.is_symlink() or root.resolve().parent != settings.data_dir.resolve() or target.is_symlink() or target.resolve().parent != root.resolve():
        raise HTTPException(409,'Der Testbildordner darf keine fremde Pfadverknüpfung sein.')
    return target


@router.get('')
def read(request: Request):
    setup.require_local(request)
    return images.status()


@router.put('')
async def update(request: Request):
    setup.require_local(request)
    try:
        value=await request.json()
        if not isinstance(value,dict) or set(value)-{'preferences','token','clear_token'}:
            raise ValueError()
        preferences=images.Preferences.model_validate(value['preferences'])
        token=value.get('token')
        clear=value.get('clear_token',False)
        if not isinstance(clear,bool) or token is not None and (not isinstance(token,str) or len(token)>1200 or any(c in token for c in '\r\n\0') or not token.isascii()):
            raise ValueError()
        token='' if clear else token.strip() if token and token.strip() else None
    except (ValueError,KeyError,TypeError):
        raise HTTPException(422,'Bildanbieter, Account-ID und Token prüfen. Keine URLs oder Befehle eintragen.') from None
    with setup.manager.lock:
        setup.manager.require_idle()
        try:
            images.save(preferences,token)
            return images.status()
        except CredentialError as error:
            raise HTTPException(409,str(error)) from None
        except (OSError,images.ImageError):
            raise HTTPException(409,'Bildkonfiguration konnte nicht sicher gespeichert werden. Kontotresor und Ordnerrechte prüfen.') from None


@router.get('/preview')
def preview_status(request: Request):
    setup.require_local(request)
    with setup.manager.lock:
        return dict(task)


@router.post('/preview')
async def start_preview(request: Request):
    global operation,thread,task
    setup.require_local(request)
    try:
        value=await request.json()
        if not isinstance(value,dict) or set(value)!={'prompt'} or not isinstance(value['prompt'],str) or not 10<=len(value['prompt'].strip())<=1400 or '\0' in value['prompt']:
            raise ValueError()
    except (ValueError,TypeError):
        raise HTTPException(422,'Ein Bildmotiv mit 10 bis 1400 Zeichen beschreiben.') from None
    with setup.manager.lock:
        setup.manager.require_idle()
        preferences=images.load()
        if preferences.provider=='cloudflare' and not (preferences.cloudflare_account_id and preferences.cloudflare_free_confirmed):
            raise HTTPException(409,str(images.ImageError('not_configured')))
        identifier=uuid.uuid4().hex
        preview_path(identifier)
        operation=Operation()
        task={'status':'running','action':'image_preview','message':'Ein Testbild wird erzeugt. Restzeit noch nicht messbar.',
              'started_at':time.time(),'percent':None,'remaining_seconds':None,'provider':preferences.provider,'id':identifier}
        setup.manager.task=dict(task)
        thread=threading.Thread(target=perform,args=(operation,identifier,value['prompt'].strip(),preferences),daemon=True)
        thread.start()
        return dict(task)


def perform(current,identifier,prompt,preferences):
    global operation,task
    try:
        result=current.run('image_preview',{'id':identifier,'prompt':prompt,'preferences':preferences.model_dump()},timeout=660)
        current.check()
        with setup.manager.lock:
            current.check()
            task={**task,'status':'completed','message':'Testbild erzeugt. Inhalt und Stil bitte ansehen; noch keine automatische Inhaltsfreigabe.',
                  'percent':100,'remaining_seconds':0,'image_url':'/api/settings/images/files/'+identifier, 'result':result}
    except OperationCancelled:
        with setup.manager.lock:
            task={**task,'status':'cancelled','message':'Testbildlauf abgebrochen. Bereits verbrauchtes Anbieterkontingent wird dadurch nicht zurückgebucht.'}
    except Exception as error:
        from .main import remember_failure
        failure=remember_failure(error,'image')
        with setup.manager.lock:
            task={**task,'status':'failed','message':str(failure),'failure':failure.public()}
    finally:
        with setup.manager.lock:
            setup.manager.task=dict(task)
            operation=None


@router.post('/cancel')
def cancel_preview(request: Request):
    setup.require_local(request)
    with setup.manager.lock:
        if operation:
            operation.cancel.set()
            task['message']='Abbruch läuft; eigene Bildprozesse werden beendet …'
        return dict(task)


@router.get('/files/{identifier}')
def image_file(identifier: str, request: Request):
    setup.require_local(request)
    target=preview_path(identifier)
    if not target.is_file():
        raise HTTPException(404,'Testbild nicht gefunden.')
    return FileResponse(target,media_type='image/png',headers={'Cache-Control':'no-store'})


def close():
    if operation:
        operation.cancel.set()
    if thread and thread.is_alive():
        thread.join(timeout=10)
