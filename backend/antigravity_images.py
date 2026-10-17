"""Subscription image calls through the installed CLI, with a private deny-by-default hook."""
import json
import base64
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

from .antigravity import _executable, _safe_environment, credit_guard, _classify_failure, AntigravityError
from .config import settings
from .images import ImageError, MAX_IMAGE_BYTES, normalize_image

ROOT = Path(__file__).resolve().parents[1]
GUARD_NAME = 'video-pipeline-image-only'


def workspace_config(workspace, prompt):
    name = 'frame_' + uuid.uuid4().hex
    (workspace / 'image-request.json').write_text(json.dumps({'prompt':prompt,'image_name':name}),encoding='utf-8')
    command = [sys.executable,'-I',str(ROOT/'backend/image_guard.py')]
    def hook_command(event):
        parts=[*command,event,str(workspace)]
        if os.name!='nt':
            return shlex.join(parts)
        # Hooks may use PowerShell on Windows; an encoded fixed command preserves paths with spaces.
        script='& '+ ' '.join("'"+part.replace("'","''")+"'" for part in parts)
        return 'powershell.exe -NoProfile -NonInteractive -EncodedCommand '+base64.b64encode(script.encode('utf-16-le')).decode()
    hooks = {GUARD_NAME:{'SessionStart':[{'command':hook_command('session'),'timeout':10}],
        'PreToolUse':[{'matcher':'*','hooks':[{'command':hook_command('tool'),'timeout':10}]}]}}
    folder = workspace / '.agents'
    folder.mkdir()
    (folder / 'hooks.json').write_text(json.dumps(hooks),encoding='utf-8')
    agents=folder/'agents'
    agents.mkdir()
    (agents/'video-pipeline-image.md').write_text('''---
name: video-pipeline-image
description: Generate one illustration with the fixed image tool only.
tools:
  - generate_image
mainAgent: true
subagent: false
model: inherit
commandExecutionPolicy: off
---
You are an image provider. Call generate_image once for the requested illustration.
Do not inspect files, run commands, browse websites or delegate work.
Return the generated image file path using the structured response.
''',encoding='utf-8')
    return name


def invoke(mode, workspace, message=None, timeout=30):
    try:
        return _invoke(mode,workspace,message,timeout)
    finally:
        # Ephemeral CLI responses must not become persistent application logs.
        for filename in ('stdout.jsonl','stderr.txt'):
            for _ in range(4):
                try:
                    path=workspace/filename
                    if path.exists():
                        path.write_bytes(b'')
                    path.unlink(missing_ok=True)
                    break
                except PermissionError:
                    time.sleep(.1)


def _invoke(mode, workspace, message=None, timeout=30):
    from desktop.platforms import process_group
    stdout, stderr = workspace/'stdout.jsonl', workspace/'stderr.txt'
    # CLI model identifiers may require the matching reasoning level.
    request={'mode':mode,'message':message,'model':settings.antigravity_model,'effort':settings.antigravity_effort}
    (workspace/'cli-request.json').write_text(json.dumps(request),encoding='utf-8')
    with process_group() as group:
        process=group.start([sys.executable,'-I',str(ROOT/'backend/image_cli.py'),str(workspace)],cwd=workspace,env=_safe_environment())
        deadline=time.monotonic()+timeout
        while group.poll(process) is None:
            if (workspace/'guard-denied').exists():
                error=ImageError('policy')
                reason=(workspace/'guard-denied').read_text(encoding='utf-8')[:40]
                error.guard_reason=reason if reason in {'artifact_scope','workspace_scope','session_scope','argument_shape','credit_policy','image_call_limit','tool_not_allowed'} else 'unknown'
                if (workspace/'guard-fields.json').exists():
                    try:
                        error.guard_shape=json.loads((workspace/'guard-fields.json').read_text(encoding='utf-8'))
                    except (OSError,ValueError):
                        pass
                raise error
            if mode=='generate' and time.monotonic()>deadline-timeout+20 and not (workspace/'guard-ready.json').exists():
                raise ImageError('policy')
            if time.monotonic()>deadline:
                raise ImageError('timeout')
            if any(path.exists() and path.stat().st_size>limit for path,limit in ((stdout,2*1024*1024),(stderr,65536))):
                raise ImageError('invalid_response')
            time.sleep(.1)
        code=group.poll(process)
    if stdout.stat().st_size>2*1024*1024 or stderr.stat().st_size>65536:
        raise ImageError('invalid_response')
    output=stdout.read_text(encoding='utf-8',errors='replace')
    if code:
        failure=_classify_failure(stderr.read_text(encoding='utf-8',errors='replace')+output)
        raise ImageError({'auth_required':'credentials','quota_or_capacity':'rate_limit','timeout':'timeout'}.get(failure,'unavailable'))
    return output


def generate(prompt, destination):
    try:
        _executable()
        credit_guard()
        own_root=settings.data_dir/'image-operations'
        if own_root.is_symlink() or own_root.resolve().parent != settings.data_dir.resolve():
            raise ImageError('policy')
        own_root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='google-',dir=own_root,ignore_cleanup_errors=True) as name:
            workspace=Path(name)
            workspace.chmod(0o700)
            image_name=workspace_config(workspace,prompt)
            # /hooks is a documented local inspection command, not a model prompt.
            inspected=invoke('inspect',workspace)
            if GUARD_NAME not in inspected:
                raise ImageError('policy')
            instruction='Call generate_image exactly once. Do not call any other tool. ImageName: '+image_name+'\nPrompt:\n'+prompt+'\nThen finish with a short confirmation.'
            output=invoke('generate',workspace,json.dumps({'event':'user','message':{'content':instruction}})+'\n',timeout=615)
            if (workspace/'guard-denied').exists() or not (workspace/'image-called').exists():
                raise ImageError('policy')
            artifact=Path(json.loads((workspace/'guard-ready.json').read_text())['artifact'])
            result=None
            for line in output.splitlines():
                event=json.loads(line)
                if event.get('event')=='step_update':
                    step=event.get('step_update',{})
                    if step.get('step_type')=='tool' and step.get('tool_name') not in {'generate_image','finish'}:
                        raise ImageError('policy')
                if event.get('event')=='result':
                    result=event['result']
            if not isinstance(result,dict) or result.get('status')!='SUCCESS':
                raise ImageError('unavailable')
            # Image-only CLI agents may omit structured_output. The app owns the name
            # and session directory, so select only that namespace, never a free-text path.
            structured=result.get('structured_output')
            if isinstance(structured,dict) and isinstance(structured.get('image_path'),str):
                source=Path(structured['image_path'])
            else:
                candidates=[path for path in artifact.glob(image_name+'*') if path.suffix.lower() in {'.png','.jpg','.jpeg'}]
                if len(candidates)!=1:
                    raise ImageError('invalid_response')
                source=candidates[0]
            if not source.is_absolute() or source.is_symlink() or source.resolve().parent != artifact.resolve() or not source.name.startswith(image_name) or source.suffix.lower() not in {'.png','.jpg','.jpeg'}:
                raise ImageError('policy')
            if not source.is_file() or source.stat().st_size>MAX_IMAGE_BYTES:
                raise ImageError('invalid_response')
            return {'provider':'antigravity','bridge_model':settings.antigravity_model,'image_model':'not_reported',
                    'billing_policy':'baseline-only',**normalize_image(source.read_bytes(),destination)}
    except AntigravityError as error:
        raise ImageError({'auth_required':'credentials','credits_enabled':'policy','billing_unknown':'policy','quota_or_capacity':'rate_limit','timeout':'timeout'}.get(error.code,'unavailable')) from None
    except (ValueError,KeyError,TypeError):
        raise ImageError('invalid_response') from None
