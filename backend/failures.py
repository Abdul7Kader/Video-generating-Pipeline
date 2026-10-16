"""Bounded public diagnostics. Exception bodies and provider URLs never cross this boundary."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import errno
import json
from pathlib import Path
import re
import subprocess
import traceback
import uuid

progress_path = None  # Set only by the private worker to its own operation directory.
_stage_context = ContextVar('pipeline_stage',default=('',{}))

STAGES = {'script':'Skript erstellen oder überarbeiten','planning':'Zeichenplan vorbereiten',
    'image':'Bilder vorbereiten','voice':'Erzählerstimme erzeugen','render':'Video zusammensetzen',
    'quality':'Videoqualität prüfen','storage':'Dateien speichern','discord':'Discord-Abnahme',
    'publish':'Veröffentlichung','request':'Anfrage verarbeiten'}
CODES = {
    'voice_missing':('Die ausgewählte Stimme ist nicht eingerichtet; stumme Ersatzvideos sind deaktiviert.','Die gewählte lokale Stimme unter Einstellungen vollständig einrichten.',False),
    'provider_mismatch':('Die erzeugte Stimme entspricht nicht dem ausgewählten Anbieter.','Die gewählte Stimme und ihre Einrichtung prüfen; es wird keine Ersatzstimme übernommen.',False),
    'timeout':('Das Zeitlimit dieses Schritts wurde überschritten.','Zugang und Auslastung prüfen; den betroffenen Schritt bei Bedarf erneut starten.',True),
    'credentials':('Der Anbieterzugang fehlt oder wurde abgelehnt.','Den gewählten Zugang unter Einstellungen prüfen und erneut anmelden.',False),
    'rate_limit':('Der Anbieter hat sein aktuelles Nutzungslimit gemeldet.','Das angegebene Anbieterlimit abwarten. Gespeicherte Ergebnisse bleiben erhalten.',False),
    'disk_full':('Der Datenträger hat nicht genügend freien Speicher.','Am gewählten Speicherort Platz schaffen und diesen Schritt erneut starten.',True),
    'file_conflict':('Am Zielort liegt bereits eine andere Datei. Sie wird nicht überschrieben.','Zielordner und bestehende Datei prüfen; vorhandene Endvideos bleiben erhalten.',False),
    'permission':('Eine benötigte Datei oder ein Ordner ist nicht zugänglich.','Ordnerrechte und den ausgewählten lokalen Speicherort prüfen.',False),
    'missing_file':('Eine benötigte Datei oder Laufzeit fehlt.','Speicherort und Einrichtung prüfen; entfernte Arbeitsdateien müssen neu erzeugt werden.',False),
    'invalid_response':('Die Antwort oder das Ergebnis dieses Schritts ist ungültig.','Eingaben und Qualitätsangaben prüfen; anschließend gezielt erneut versuchen.',True),
    'process_failed':('Ein eigener Verarbeitungsprozess wurde unerwartet beendet.','Einrichtung und freien Arbeitsspeicher prüfen; gespeicherte Ergebnisse bleiben erhalten.',True),
    'quality':('Das erzeugte Ergebnis hat die Qualitätsprüfung nicht bestanden.','Den gespeicherten Qualitätsbericht und den betroffenen Inhalt prüfen.',True),
    'not_ready':('Frame ist noch nicht zur Produktion freigegeben.','Zuerst den vorgesehenen KI-Bildweg einrichten und abnehmen. Die bestehende Animation bleibt nutzbar.',False),
    'unexpected':('Dieser Schritt konnte nicht abgeschlossen werden.','Fehlerdetails kopieren und mit der Fehler-ID melden. Gespeicherte Dateien bleiben erhalten.',False),
    'unsupported_action':('Unbekannter Produktionsschritt.','Nur die festgelegten Produktionsaktionen sind erlaubt.',False),
}


class PipelineFailure(RuntimeError):
    def __init__(self, stage, code='unexpected', *, identifier=None, context=None, diagnostics=None):
        self.stage = stage if isinstance(stage,str) and stage in STAGES else 'request'
        self.code = code if isinstance(code,str) and code in CODES else 'unexpected'
        self.identifier = identifier if isinstance(identifier,str) and re.fullmatch(r'[0-9a-f]{16}',identifier) else uuid.uuid4().hex[:16]
        self.context = {key:value for key,value in (context if isinstance(context,dict) else {}).items()
            if key in {'scene_id','image_index','image_total','aspect_ratio','platform'}
            and isinstance(value,(str,int)) and re.fullmatch(r'[a-zA-Z0-9_:.\-]{1,64}',str(value))}
        self.diagnostics = diagnostics or {}
        super().__init__(STAGES[self.stage] + ': ' + CODES[self.code][0] + ' Fehler-ID: ' + self.identifier)

    def public(self, job_id=None):
        message,action,retryable = CODES[self.code]
        # Publication retries require checking the provider even after an apparently local error.
        if self.stage == 'publish':
            retryable = False
            action = 'Externen Zielstatus prüfen. Ein unbestätigter Upload wird nicht automatisch wiederholt.'
        last = (self.diagnostics.get('locations') or [{}])[-1]
        technical = {'error_type':self.diagnostics.get('exception_type'),'component':last.get('file'),'line':last.get('line')}
        return {'id':self.identifier,'job_id':job_id,'stage':self.stage,'stage_label':STAGES[self.stage],
            'code':self.code,'message':message,'next_action':action,'retryable':retryable,'context':self.context,'technical':technical}

    def wire(self):
        return {'stage':self.stage,'code':self.code,'id':self.identifier,'context':self.context,'diagnostics':self.diagnostics}

    @classmethod
    def from_wire(cls,value):
        # Rebuild all public wording locally; never trust messages coming back from a worker.
        result = cls(value.get('stage'),value.get('code'),identifier=value.get('id'),context=value.get('context'))
        diagnostic = value.get('diagnostics') or {}
        if isinstance(diagnostic,dict):
            kind = str(diagnostic.get('exception_type',''))
            if re.fullmatch(r'[a-zA-Z0-9_]{1,80}',kind):
                result.diagnostics['exception_type'] = kind
            result.diagnostics['locations'] = [
                {'function':item['function'],'line':item['line'],
                 'file':item.get('file') if re.fullmatch(r'[a-zA-Z0-9_.-]{1,120}',str(item.get('file',''))) else None}
                for item in (diagnostic.get('locations') or [])[:8]
                if isinstance(item,dict) and re.fullmatch(r'[a-zA-Z0-9_<>]{1,80}',str(item.get('function','')))
                and type(item.get('line')) is int and 0 < item['line'] < 1000000]
        return result


def describe(error, stage='request', **context):
    if isinstance(error,PipelineFailure):
        return error
    chain=[];cause=error
    while cause and all(cause is not item for item in chain) and len(chain)<4:
        chain.append(cause);cause=cause.__cause__ or cause.__context__
    text = ' '.join(str(item)[:2048].lower() for item in chain)  # Classification only, never persisted or returned.
    if 'stumme ersatzvideos sind deaktiviert' in text: code = 'voice_missing'
    elif 'ausgewählten anbieter' in text or 'ersatzstimme' in text: code = 'provider_mismatch'
    elif any(isinstance(item,(TimeoutError,subprocess.TimeoutExpired)) for item in chain) or any(word in text for word in ('timeout','zeitlimit','timed out','time limit')):
        code = 'timeout'
    elif any(isinstance(item,OSError) and (item.errno == errno.ENOSPC or getattr(item,'winerror',None) == 112) for item in chain):
        code = 'disk_full'
    elif any(isinstance(item,PermissionError) for item in chain): code = 'permission'
    elif any(isinstance(item,FileNotFoundError) for item in chain): code = 'missing_file'
    elif 'nicht überschrieben' in text or 'geänderte texte' in text: code = 'file_conflict'
    elif any(word in text for word in ('429','rate limit','rate_limit','quota','kontingent','nutzungslimit')): code = 'rate_limit'
    elif any(word in text for word in ('401','403','anmeldung','credential','unauthorized','nicht angemeldet','api-key','api key')): code = 'credentials'
    elif stage == 'quality' or 'qualitäts' in text or 'quality gate' in text: code = 'quality'
    elif isinstance(error,subprocess.CalledProcessError): code = 'process_failed'
    elif isinstance(error,(ValueError,TypeError,KeyError)): code = 'invalid_response'
    else: code = 'unexpected'
    frames = traceback.extract_tb(error.__traceback__)[-8:]
    diagnostic = {'exception_type':type(error).__name__,
        'locations':[{'function':frame.name,'line':frame.lineno,'file':Path(frame.filename).name} for frame in frames]}
    return PipelineFailure(stage,code,context=context,diagnostics=diagnostic)


@contextmanager
def failure_stage(stage, **context):
    parent_stage,parent_context = _stage_context.get()
    context = PipelineFailure(stage,context={**(parent_context if parent_stage == stage else {}),**context}).context
    token = _stage_context.set((stage,context))
    if progress_path:
        try:
            report = PipelineFailure(stage,context=context).public()
            temporary = progress_path.with_suffix('.pending')
            temporary.write_text(json.dumps({'stage':report['stage'],'context':report['context']}),encoding='utf-8')
            temporary.replace(progress_path)
        except OSError:
            pass  # Progress reporting must not mask a real disk/processing failure.
    try:
        yield
    except PipelineFailure as error:
        if error.stage == stage:
            error.context = {**PipelineFailure(stage,context=context).context,**error.context}
        raise
    except Exception as error:
        # Cancellation remains a deliberate state, not a production error.
        from .operations import OperationCancelled
        if isinstance(error,OperationCancelled):
            raise
        raise describe(error,stage,**context) from None
    finally:
        _stage_context.reset(token)


def at_stage(stage):
    def decorate(function):
        @wraps(function)
        def guarded(*args,**kwargs):
            with failure_stage(stage):
                return function(*args,**kwargs)
        return guarded
    return decorate
