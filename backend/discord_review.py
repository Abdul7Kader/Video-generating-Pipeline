"""Discord decisions are bound to channel, actor, message, version and file hash."""
import json
import platform
from pathlib import Path
import re
import tempfile
import threading
import time
from urllib.parse import quote

from .config import settings
from .db import utcnow
from .credentials import credentials
from .discord_http import request, DiscordError
from .integrations import load, lock as configuration_lock
from .operations import operations, OperationCancelled
from .plan import file_sha256
from .reviews import Reviews
from .schemas import VersionAction, VideoApproval
from .story import spoken_story


class DiscordReviewService:
    def __init__(self, db, approve, plan, *, accepting=lambda: True, claim_lock=None):
        self.db, self.reviews, self.approve, self.plan = db, Reviews(db), approve, plan
        self.accepting, self.claim_lock = accepting, claim_lock or threading.Lock()
        self.stop, self.busy = threading.Event(), threading.Event()
        self.status = 'Discord ist noch nicht verbunden.'
        self.socket, self.active_job, self.threads = None, None, []

    def start(self):
        for function, name in [(self.gateway, 'discord-gateway'), (self.worker, 'discord-review-worker')]:
            thread = threading.Thread(target=function, name=name, daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        self.stop.set()
        if self.socket:
            self.socket.close()
        if self.active_job:
            try:
                operations.cancel(self.active_job, self.db)
            except (ValueError, KeyError):
                pass
        for thread in self.threads:
            thread.join(timeout=10)

    def current(self, ticket):
        job = self.db.get_job(ticket['job_id'])
        if not job or not job['script']['integrity_verified']:
            return None
        if ticket['kind'] == 'script':
            return job if job['status'] == 'script_review' and job['script_version'] == ticket['version'] and job['script']['content_hash'] == ticket['fingerprint'] else None
        return job if job['status'] == 'video_review' and job['render_version'] == ticket['version'] and job['output_sha256'] == ticket['fingerprint'] else None

    @staticmethod
    def components(ticket):
        prefix = 'vp:' + ticket['id'] + ':'
        return [{'type':1, 'components':[
            {'type':2,'style':3,'label':'Text freigeben und Video erstellen' if ticket['kind'] == 'script' else 'Video freigeben und weitergeben', 'custom_id':prefix + 'approve'},
            {'type':2,'style':1,'label':'Änderung wünschen','custom_id':prefix + 'change'},
            {'type':2,'style':4,'label':'Ablehnen','custom_id':prefix + 'reject'}]}]

    def send(self, ticket):
        preferences = load()
        if not preferences.discord_enabled or (preferences.discord_guild_id,preferences.discord_channel_id) != (ticket['guild_id'],ticket['channel_id']):
            raise DiscordError('Das Discord-Ziel wurde deaktiviert oder geändert. Einstellungen prüfen und gegebenenfalls neu senden.')
        job = self.current(ticket)
        if not job:
            raise DiscordError('Diese Version ist nicht mehr zur Abnahme bereit. Aktuelle Version neu senden.')
        targets = ', '.join('youtube (' + ticket['options'].get('youtube_privacy','private') + ')' if target == 'youtube' else target for target in ticket['targets']) or 'Nur lokal freigeben · kein Social-Media-Upload'
        payload = {'content':f"**{job['script']['title'][:160]}** · Version {ticket['version']}\n"
            + ('Überarbeiteter Sprechertext. Textfreigabe startet eine neue Videoerstellung.\n' if ticket['kind'] == 'script' else 'Fertiges Video zur Prüfung. Erst die Freigabe startet die gewählten Übertragungen.\n')
            + f"Ziele: {targets}." + (' TikTok: Übergabe als Entwurf; endgültig in TikTok veröffentlichen.' if 'tiktok' in ticket['targets'] else '')
            + ('\nBeschriftung: ' + job['script']['description'][:700] if ticket['kind'] == 'video' else '')
            + f"\nPrüfbindung: `{ticket['fingerprint'][:16]}`", 'allowed_mentions':{'parse':[]}, 'components':self.components(ticket)}
        if ticket['kind'] == 'script':
            with tempfile.TemporaryDirectory(prefix='script-review-') as directory:
                source = Path(directory) / 'sprechertext.txt'
                source.write_text(spoken_story(job['script']), encoding='utf-8')
                response = request('POST', '/channels/' + ticket['channel_id'] + '/messages', payload,
                    file=source,filename='sprechertext.txt',limit=preferences.discord_upload_mb*1024*1024,expected_sha256=file_sha256(source))
        else:
            source = (settings.jobs_dir / job['output_path']).resolve()
            if settings.jobs_dir not in source.parents or not source.is_file() or file_sha256(source) != ticket['fingerprint']:
                raise DiscordError('Die fertige Videodatei fehlt oder hat sich verändert; Übertragung gesperrt.')
            response = request('POST','/channels/' + ticket['channel_id'] + '/messages',payload,
                file=source,filename='video.mp4',limit=preferences.discord_upload_mb*1024*1024,expected_sha256=ticket['fingerprint'])
        identifier = str(response.get('id', ''))
        if not identifier.isdecimal() or str(response.get('channel_id')) != ticket['channel_id']:
            raise DiscordError('Discord hat die Nachrichten-ID nicht bestätigt; vor einer Wiederholung den Kanal prüfen.',uncertain=True)
        self.reviews.transition(ticket['id'], {'sending'}, 'sent', message_id=identifier)
        self.db.record_event(job['id'], 'discord_sent', 'Zur Prüfung an den konfigurierten Discord-Kanal gesendet; noch nicht veröffentlicht.')

    def reply(self, interaction, content=None, *, defer=False, modal=None):
        if modal:
            payload = {'type':9,'data':modal}
        else:
            payload = {'type':5 if defer else 4,'data':{'flags':64,'allowed_mentions':{'parse':[]}}}
            if content:
                payload['data']['content'] = content[:1800]
        request('POST','/interactions/' + quote(str(interaction['id']),safe='') + '/' + quote(str(interaction['token']),safe='') + '/callback',payload)

    def complete_reply(self, interaction, content):
        request('PATCH','/webhooks/' + quote(str(interaction['application_id']),safe='') + '/' + quote(str(interaction['token']),safe='') + '/messages/@original',
                {'content':content[:1800],'allowed_mentions':{'parse':[]}})

    def handle(self, interaction):
        data = interaction.get('data') or {}
        custom = data.get('custom_id', '')
        match = re.fullmatch(r'vp:([0-9a-f]{32}):(approve|change|reject|feedback)(?::([0-9]{15,22}))?',custom)
        if not match:
            return
        ticket = self.reviews.get(match[1])
        preferences = load()
        actor = str(((interaction.get('member') or {}).get('user') or interaction.get('user') or {}).get('id',''))
        allowed = (ticket and preferences.discord_enabled and actor in preferences.discord_approver_ids
            and str(interaction.get('guild_id')) == ticket['guild_id'] == preferences.discord_guild_id
            and str(interaction.get('channel_id')) == ticket['channel_id'] == preferences.discord_channel_id
            and (match[2] == 'feedback' and interaction.get('type') == 5 and match[3] == actor
                 or interaction.get('type') == 3 and str((interaction.get('message') or {}).get('id')) == ticket['message_id']))
        if not allowed:
            self.reply(interaction,'Keine Freigabeberechtigung für diesen Server, Kanal und diese Nachricht.')
            return
        if not self.accepting() or ticket['state'] != 'sent' or not self.current(ticket) or ticket['options'].get('connection_revision') != preferences.connection_revision:
            self.reply(interaction,'Diese Abnahme ist nicht mehr aktuell oder die Anwendung wird beendet. Bitte die aktuelle Version verwenden.')
            return
        if match[2] == 'change':
            self.reply(interaction,modal={'custom_id':f"vp:{ticket['id']}:feedback:{actor}", 'title':'Was soll die KI verbessern?', 'components':[
                {'type':1,'components':[{'type':4,'custom_id':'instructions','label':'Dein Änderungswunsch','style':2,'required':True,'min_length':3,'max_length':2000}]}]})
            return
        instructions = None
        if match[2] == 'feedback':
            instructions = ' '.join(str(item.get('value','')) for row in data.get('components',[]) for item in row.get('components',[]) if item.get('custom_id') == 'instructions').strip()
            if not 3 <= len(instructions) <= 2000:
                self.reply(interaction,'Bitte einen konkreten Änderungswunsch mit 3 bis 2000 Zeichen eingeben.')
                return
        self.reply(interaction,defer=True)
        if not self.reviews.transition(ticket['id'], {'sent'}, 'deciding', actor_id=actor, instructions=instructions):
            self.complete_reply(interaction,'Diese Entscheidung wurde bereits bearbeitet.')
            return
        try:
            if match[2] == 'approve':
                if ticket['kind'] == 'script':
                    self.reviews.transition(ticket['id'], {'deciding'}, 'render_requested')
                    message = 'Text freigegeben. Die neue Videoerstellung ist eingereiht; das Ergebnis kommt erneut hier zur Videoabnahme.'
                else:
                    with configuration_lock:
                        if load().connection_revision != ticket['options'].get('connection_revision'):
                            raise RuntimeError('Kanalkonfiguration geändert.')
                        self.approve(ticket['job_id'],VideoApproval(expected_version=ticket['version'],expected_hash=ticket['fingerprint'],target_platforms=ticket['targets'] or ['download']))
                    self.reviews.transition(ticket['id'], {'deciding'}, 'approved')
                    message = 'Video freigegeben. Eingerichtete gewählte Ziele werden abgearbeitet. Fehlende Zugänge bleiben als Einrichtungsbedarf sichtbar; TikTok benötigt die endgültige Veröffentlichung in der App.'
            elif match[2] == 'reject':
                self.reviews.transition(ticket['id'], {'deciding'}, 'rejected')
                if ticket['kind'] == 'video':
                    with self.db._write_lock,self.db.connect() as conn:
                        conn.execute("UPDATE jobs SET status='video_rejected',updated_at=? WHERE id=? AND status='video_review'",(utcnow(),ticket['job_id']))
                        conn.commit()
                message = 'Abgelehnt. Es wird nichts veröffentlicht; lokale Dateien bleiben erhalten.'
            else:
                self.reviews.transition(ticket['id'], {'deciding'}, 'revision_requested')
                message = 'Änderungswunsch eingereiht. Die KI überarbeitet den Text; du erhältst ihn vor einer neuen Videoerstellung erneut zur Freigabe.'
            self.db.record_event(ticket['job_id'],'discord_decision',message,{'actor_id':actor,'review_id':ticket['id']})
        except Exception:
            self.reviews.transition(ticket['id'], {'deciding'}, 'failed',error='Freigabe nicht bestätigt. Aktuelle Datei, Version und Zielkonfiguration prüfen.')
            message = 'Die Freigabe wurde nicht bestätigt. Aktuelle Datei und Zielkonfiguration in der Anwendung prüfen; keine automatische Wiederholung.'
        self.complete_reply(interaction,message)

    def process(self, ticket):
        if ticket['state'] == 'sending':
            self.send(ticket)
            return
        self.active_job = ticket['job_id']
        try:
            job = self.current(ticket)
            if not job:
                raise RuntimeError('Die angeforderte Version ist nicht mehr aktuell.')
            if ticket['state'] == 'planning':
                self.plan(job['id'],VersionAction(expected_version=ticket['version'],expected_hash=ticket['fingerprint']))
                self.reviews.transition(ticket['id'],{'planning'},'approved')
            else:
                with operations.start(job['id'],self.db) as operation:
                    self.db.begin_planning(job['id'],job['script_version'])
                    values = {name:job[name] for name in ('topic','language','duration_seconds','aspect_ratio','production_config')}
                    values['script_mode'] = 'story'
                    result = operation.run('revise',{'request':values,'script':job['script'],'instructions':ticket['instructions']})
                    with operations.lock:
                        operation.check()
                        self.db.update_script(job['id'],job['script_version'],result)
                self.reviews.transition(ticket['id'],{'revising'},'revised')
                self.reviews.enqueue(job['id'],load(),kind='script')
        finally:
            self.active_job = None

    def worker(self):
        while not self.stop.is_set():
            ticket = None
            try:
                with self.claim_lock:
                    if self.accepting() and load().discord_enabled:
                        ticket = self.reviews.claim()
                        if ticket:
                            self.busy.set()
                if ticket:
                    try:
                        self.process(ticket)
                    except OperationCancelled:
                        self.reviews.transition(ticket['id'],{ticket['state']},'failed',error='Auf Wunsch abgebrochen; keine Veröffentlichung.')
                    except Exception as error:
                        uncertain = isinstance(error,DiscordError) and error.uncertain
                        message = str(error) if isinstance(error,DiscordError) else 'Der Abnahmeschritt wurde nicht abgeschlossen. Lokalen Auftragsstatus prüfen; keine automatische Wiederholung.'
                        self.reviews.transition(ticket['id'],{ticket['state']},'unknown' if uncertain else 'failed',error=message)
                        self.db.planning_failed(ticket['job_id'],message)
                        self.db.record_event(ticket['job_id'],'discord_failed',message)
            except Exception:
                self.status = 'Discord-Abnahme pausiert. Einstellungen und lokalen Auftragsstatus prüfen.'
            finally:
                self.busy.clear()
            self.stop.wait(.5 if ticket else 2)

    def publish_status(self, job_id):
        try:
            preference = load()
            if not preference.discord_enabled:
                return
            ticket,job = self.reviews.latest(job_id),self.db.get_job(job_id)
            if not ticket or ticket['kind'] != 'video' or ticket['state'] != 'approved' or not ticket['message_id']:
                return
            if (ticket['guild_id'],ticket['channel_id']) != (preference.discord_guild_id,preference.discord_channel_id):
                return
            labels = {'published':'Veröffentlicht','publishing':'Wird übertragen','queued':'Wartet',
                'setup_required':'Einrichtung fehlt','failed':'Fehlgeschlagen','unknown':'Externen Status prüfen',
                'ready':'Lokal bereit','awaiting_user':'Entwurf übergeben – in TikTok endgültig veröffentlichen'}
            lines = [f"**{job['script']['title'][:160]}** · Version {ticket['version']} · Freigegeben"]
            lines.append('Beschriftung: ' + job['script']['description'][:600])
            for target in job['publication_targets']:
                lines.append(target['platform'] + ': ' + labels.get(target['status'],target['status']) + (' ' + target['remote_url'] if target['remote_url'] else ''))
            request('PATCH',f"/channels/{ticket['channel_id']}/messages/{ticket['message_id']}",
                {'content':'\n'.join(lines)[:1900],'allowed_mentions':{'parse':[]},'components':[]})
        except Exception:
            self.db.record_event(job_id,'discord_status_failed','Plattformstatus lokal gespeichert; Discord-Statusnachricht konnte nicht aktualisiert werden.')

    def gateway(self):
        from websockets.sync.client import connect
        delay = 5
        while not self.stop.is_set():
            try:
                preference = load()
                if not preference.discord_enabled:
                    self.status = 'Discord ist deaktiviert.'
                    self.stop.wait(2)
                    continue
                token = credentials.get('discord_bot_token')
                if not token:
                    self.status = 'Discord Bot-Token fehlt. Unter Einstellungen speichern.'
                    self.stop.wait(5)
                    continue
                self.status = 'Ausgehende Discord-Verbindung wird hergestellt …'
                with connect('wss://gateway.discord.gg/?v=10&encoding=json',proxy=None,
                             open_timeout=10,close_timeout=3,max_size=1024*1024,compression=None) as socket:
                    self.socket = socket
                    hello = json.loads(socket.recv(timeout=10))
                    interval = float((hello.get('d') or {}).get('heartbeat_interval',0)) / 1000
                    if hello.get('op') != 10 or not .1 <= interval <= 120:
                        raise RuntimeError('Ungültiger Gateway-Start')
                    socket.send(json.dumps({'op':2,'d':{'token':token,'intents':0,
                        'properties':{'os':platform.system(),'browser':'VideoPipeline','device':'VideoPipeline'}}}))
                    sequence, next_heartbeat, acknowledged = None,time.monotonic(),True
                    while not self.stop.is_set():
                        now = time.monotonic()
                        if now >= next_heartbeat:
                            if not acknowledged:
                                raise RuntimeError('Discord-Heartbeat nicht bestätigt')
                            socket.send(json.dumps({'op':1,'d':sequence}))
                            acknowledged = False
                            next_heartbeat = now + interval
                        try:
                            event = json.loads(socket.recv(timeout=min(1,max(.01,next_heartbeat-time.monotonic()))))
                        except TimeoutError:
                            current = load()
                            if not current.discord_enabled or current.connection_revision != preference.connection_revision:
                                break
                            continue
                        if event.get('s') is not None:
                            sequence = event['s']
                        if event.get('op') == 11:
                            acknowledged = True
                        elif event.get('op') == 1:
                            socket.send(json.dumps({'op':1,'d':sequence}))
                        elif event.get('op') in {7,9}:
                            break
                        elif event.get('t') == 'READY':
                            if not (event.get('d',{}).get('user') or {}).get('bot'):
                                raise RuntimeError('Kein regulärer Bot')
                            self.status,delay = 'Discord verbunden · nur erlaubte Freigeber können entscheiden.',5
                        elif event.get('t') == 'INTERACTION_CREATE':
                            try:
                                self.handle(event['d'])
                            except Exception:
                                self.status = 'Eine Discord-Aktion wurde nicht bestätigt. Aktuelle Version und Rechte prüfen.'
            except Exception:
                self.status = 'Discord-Verbindung unterbrochen. Bot-Token, Rechte und Anbieterlimits prüfen; erneuter Verbindungsversuch folgt.'
            finally:
                self.socket = None
            self.stop.wait(delay)
            delay = min(60,delay*2)
