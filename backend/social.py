"""Official streamed Meta Reels uploads and TikTok inbox handoff, no browser automation."""
import hashlib
import http.client
import json
from pathlib import Path
import time
from urllib.parse import urlsplit, urlencode

from .credentials import credentials
from .integrations import load
from .publishing import PublicationError, PendingPublication

GRAPH_VERSION = 'v25.0'
API_HOSTS = {'graph.facebook.com','graph.instagram.com','open.tiktokapis.com'}


def json_request(host, method, path, token='', payload=None, *, form=False, timeout=60):
    if host not in API_HOSTS or not path.startswith('/') or any(value in path for value in '\r\n'):
        raise PublicationError('Unzulässiges Anbieterziel.')
    body = urlencode(payload).encode() if form and payload is not None else json.dumps(payload).encode() if payload is not None else None
    headers = {'Content-Type':'application/x-www-form-urlencoded' if form else 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
    connection = http.client.HTTPSConnection(host,timeout=timeout)
    attempted = False
    try:
        attempted = True
        connection.request(method,path,body,headers)
        response = connection.getresponse()
        raw = response.read(2*1024*1024+1)
        if not 200 <= response.status < 300:
            raise PublicationError(f'{host} antwortet mit HTTP {response.status}. Anmeldung, API-Rechte und Anbieterlimits prüfen.',uncertain=response.status >= 500 and method != 'GET')
        if len(raw) > 2*1024*1024:
            raise PublicationError('Die Anbieterantwort ist zu groß.',uncertain=method != 'GET')
        value = json.loads(raw) if raw else {}
        error = value.get('error')
        if error and not (isinstance(error,dict) and error.get('code') == 'ok'):
            raise PublicationError('Der Anbieter hat die Aktion abgelehnt. Anmeldung, Berechtigungen und Kontingent prüfen.')
        return value
    except PublicationError:
        raise
    except Exception:
        raise PublicationError('Anbieterantwort nicht bestätigt. Externen Zustand vor einer Wiederholung prüfen.',uncertain=attempted and method != 'GET') from None
    finally:
        connection.close()


def upload_url(value, allowed_host, prefix):
    if not isinstance(value,str) or any(character in value for character in '\r\n\0'):
        raise PublicationError('Ungültige Anbieteradresse.')
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        raise PublicationError('Ungültige Anbieteradresse.') from None
    if (parsed.scheme != 'https' or parsed.hostname != allowed_host or parsed.username or parsed.password
            or port not in {None,443} or parsed.fragment or not parsed.path.startswith(prefix)):
        raise PublicationError('Der Anbieter hat eine unzulässige Upload-Adresse geliefert; Datei und Zugang werden nicht gesendet.')
    return parsed


def upload_file(url, file, *, host, prefix, token='', start=0, length=None, digest=None, total=None, method='POST'):
    parsed = upload_url(url,host,prefix)
    length = file.stat().st_size if length is None else length
    headers = {'Content-Type':'application/octet-stream' if method == 'POST' else 'video/mp4','Content-Length':str(length)}
    if method == 'POST':
        headers.update(Authorization='OAuth ' + token,offset=str(start),file_size=str(file.stat().st_size))
    else:
        headers['Content-Range'] = f'bytes {start}-{start+length-1}/{total}'
    connection = http.client.HTTPSConnection(host,timeout=180)
    try:
        connection.putrequest(method,parsed.path + ('?' + parsed.query if parsed.query else ''))
        for name,value in headers.items(): connection.putheader(name,value)
        connection.endheaders()
        remaining = length
        with file.open('rb') as stream:
            stream.seek(start)
            while remaining:
                chunk = stream.read(min(64*1024,remaining))
                if not chunk:
                    raise PublicationError('Die Datei wurde während der Übertragung verändert.',uncertain=True)
                if digest is not None: digest.update(chunk)
                connection.send(chunk)
                remaining -= len(chunk)
        response = connection.getresponse()
        response.read(1024*1024)
        if not 200 <= response.status < 300:
            raise PublicationError(f'Videoübertragung mit HTTP {response.status} nicht bestätigt.',uncertain=response.status >= 500)
    except PublicationError:
        raise
    except Exception:
        raise PublicationError('Videoübertragung unterbrochen; externen Status vor einer Wiederholung prüfen.',uncertain=True) from None
    finally:
        connection.close()


def numeric_id(value):
    value = str(value)
    if not value.isdecimal() or len(value) > 40:
        raise PublicationError('Ungültige Anbieter-ID.')
    return value


def poll_status(read, complete, failed, *, remote_id):
    for attempt in range(20):
        value = read()
        if complete(value): return value
        if failed(value): raise PublicationError('Der Anbieter konnte das Video nicht verarbeiten.',remote_id=remote_id)
        if attempt < 19: time.sleep(15)
    raise PublicationError('Die Verarbeitung wurde noch nicht bestätigt; vor einer Wiederholung beim Anbieter prüfen.',uncertain=True,remote_id=remote_id)


def publish_facebook(job, video):
    preference = load()
    token, page = credentials.get('facebook_token'), numeric_id(preference.facebook_page_id)
    if not preference.facebook_enabled or not token:
        raise PublicationError('Facebook-Seite und Zugriffstoken unter Einstellungen einrichten.')
    route = f'/{GRAPH_VERSION}/{page}/video_reels'
    started = json_request('graph.facebook.com','POST',route,token,{'upload_phase':'start'},form=True)
    identifier = numeric_id(started.get('video_id',''))
    digest = hashlib.sha256()
    upload_file(started.get('upload_url',''),video,host='rupload.facebook.com',prefix='/video-upload/',token=token,digest=digest)
    if digest.hexdigest() != job['publication_target']['approved_output_sha256']:
        raise PublicationError('Die gesendete Datei entspricht nicht mehr der Freigabe; Veröffentlichung gestoppt.')
    try:
        published = json_request('graph.facebook.com','POST',route,token,{'upload_phase':'finish','video_id':identifier,
            'video_state':'PUBLISHED','title':job['script']['title'][:255],'description':job['script']['description'][:5000]},form=True)
    except PublicationError as error:
        error.remote_id = identifier
        raise
    if published.get('success') is not True:
        raise PublicationError('Facebook hat die Veröffentlichung nicht bestätigt.',uncertain=True,remote_id=identifier)
    try:
        poll_status(lambda:json_request('graph.facebook.com','GET',f'/{GRAPH_VERSION}/{identifier}?fields=status',token),
            lambda value:(value.get('status',{}).get('publishing_phase') or {}).get('status') == 'complete',
            lambda value:value.get('status',{}).get('video_status') in {'error','expired'},remote_id=identifier)
    except PublicationError as error:
        error.uncertain, error.remote_id = True,identifier
        raise
    return identifier,'https://www.facebook.com/reel/' + identifier


def publish_instagram(job, video):
    preference = load()
    token, account = credentials.get('instagram_token'), numeric_id(preference.instagram_account_id)
    if not preference.instagram_enabled or not token:
        raise PublicationError('Professionelles Instagram-Konto und Zugriffstoken unter Einstellungen einrichten.')
    host = 'graph.instagram.com' if preference.instagram_login == 'instagram' else 'graph.facebook.com'
    started = json_request(host,'POST',f'/{GRAPH_VERSION}/{account}/media',token,
        {'media_type':'REELS','upload_type':'resumable','caption':(job['script']['title'] + '\n\n' + job['script']['description'])[:2200]},form=True)
    identifier = numeric_id(started.get('id',''))
    digest = hashlib.sha256()
    upload_file(started.get('uri') or started.get('upload_uri',''),video,host='rupload.facebook.com',prefix='/ig-api-upload/',token=token,digest=digest)
    if digest.hexdigest() != job['publication_target']['approved_output_sha256']:
        raise PublicationError('Die gesendete Datei entspricht nicht mehr der Freigabe; Veröffentlichung gestoppt.')
    poll_status(lambda:json_request(host,'GET',f'/{GRAPH_VERSION}/{identifier}?fields=status_code',token),
        lambda value:value.get('status_code') == 'FINISHED',lambda value:value.get('status_code') in {'ERROR','EXPIRED'},remote_id=identifier)
    try:
        published = json_request(host,'POST',f'/{GRAPH_VERSION}/{account}/media_publish',token,{'creation_id':identifier},form=True)
    except PublicationError as error:
        error.remote_id = identifier
        raise
    try:
        remote = numeric_id(published.get('id',''))
    except PublicationError:
        raise PublicationError('Instagram-Veröffentlichung nicht eindeutig bestätigt; externen Status prüfen.',uncertain=True,remote_id=identifier) from None
    try:
        details = json_request(host,'GET',f'/{GRAPH_VERSION}/{remote}?fields=permalink',token)
    except PublicationError:
        details = {}  # Publication was confirmed; an optional link failure must not retry it.
    url = details.get('permalink')
    parsed = urlsplit(url or '')
    if parsed.scheme != 'https' or parsed.hostname not in {'www.instagram.com','instagram.com'}:
        url = None
    return remote,url


def tiktok_token(preference):
    refresh = credentials.get('tiktok_refresh_token')
    if refresh and preference.tiktok_client_id and credentials.get('tiktok_client_secret'):
        value = json_request('open.tiktokapis.com','POST','/v2/oauth/token/',payload={'client_key':preference.tiktok_client_id,
            'client_secret':credentials.get('tiktok_client_secret'),'grant_type':'refresh_token','refresh_token':refresh},form=True)
        if not value.get('access_token'):
            raise PublicationError('TikTok-Anmeldung muss erneuert werden.')
        credentials.set('tiktok_refresh_token',value.get('refresh_token') or refresh)
        credentials.set('tiktok_access_token',value['access_token'])
    token = credentials.get('tiktok_access_token')
    if not token: raise PublicationError('TikTok-Zugang mit video.upload-Berechtigung fehlt.')
    return token


def upload_tiktok_draft(job, video):
    preference = load()
    if not preference.tiktok_enabled:
        raise PublicationError('TikTok-Übergabe ist deaktiviert.')
    token = tiktok_token(preference)
    size = video.stat().st_size
    chunk_size = min(size,32*1024*1024)
    if not chunk_size: raise PublicationError('Die Videodatei ist leer.')
    count = max(1,size // chunk_size)
    started = json_request('open.tiktokapis.com','POST','/v2/post/publish/inbox/video/init/',token,
        {'source_info':{'source':'FILE_UPLOAD','video_size':size,'chunk_size':chunk_size,'total_chunk_count':count}}).get('data',{})
    identifier = str(started.get('publish_id',''))
    if not identifier or len(identifier) > 100:
        raise PublicationError('TikTok hat die Übergabe-ID nicht bestätigt.',uncertain=True)
    digest = hashlib.sha256()
    for index in range(count):
        start = index * chunk_size
        length = chunk_size if index < count-1 else size-start
        upload_file(started.get('upload_url',''),video,host='open-upload.tiktokapis.com',prefix=('/video/','/upload/'),
            start=start,length=length,total=size,digest=digest,method='PUT')
    if digest.hexdigest() != job['publication_target']['approved_output_sha256']:
        raise PublicationError('Die TikTok-Übertragung passt nicht mehr zur Freigabe. Entwurf vor Veröffentlichung prüfen.',uncertain=True,remote_id=identifier)
    try:
        status = poll_status(lambda:json_request('open.tiktokapis.com','POST','/v2/post/publish/status/fetch/',token,{'publish_id':identifier}).get('data',{}),
            lambda value:value.get('status') in {'SEND_TO_USER_INBOX','PUBLISH_COMPLETE'},lambda value:value.get('status') == 'FAILED',remote_id=identifier)
    except PublicationError as error:
        error.remote_id = identifier
        error.uncertain = True
        raise
    if status.get('status') == 'PUBLISH_COMPLETE':
        return identifier,None
    return PendingPublication(identifier,None,'An TikTok als Entwurf übergeben. Benachrichtigung in TikTok öffnen und selbst endgültig veröffentlichen; noch nicht öffentlich gepostet.')


def check_pending(db, job_id=None):
    target = db.pending_confirmation(job_id)
    if not target or not load().tiktok_enabled:
        return None
    db.confirm_tiktok(target['job_id'],target['remote_id'])
    token = credentials.get('tiktok_access_token')
    if not token:
        raise PublicationError('TikTok-Zugang fehlt. Unter Einstellungen neu verbinden.')
    value = json_request('open.tiktokapis.com','POST','/v2/post/publish/status/fetch/',token,
        {'publish_id':target['remote_id']},timeout=10).get('data',{})
    db.confirm_tiktok(target['job_id'],target['remote_id'],complete=value.get('status') == 'PUBLISH_COMPLETE',failed=value.get('status') == 'FAILED')
    return {'job_id':target['job_id'],'status':value.get('status','Unbekannt')}
