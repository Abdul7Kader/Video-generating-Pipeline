"""Fixed CLI stdio helper inside the app's native process group."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    from backend.antigravity import _executable, credit_guard
    from backend.process_control import owned_command
    workspace=Path(sys.argv[1]).resolve()
    if workspace != Path.cwd().resolve():
        return 1
    value=json.loads((workspace/'cli-request.json').read_text(encoding='utf-8'))
    credit_guard()
    command=[_executable()]
    if value['mode']=='inspect':
        command += ['--print','/hooks','--output-format','json']
    elif value['mode'] in {'generate','review'} and re.fullmatch(r'gemini-[a-z0-9.-]{1,80}',value['model']) and value['effort'] in {'low','medium','high','xhigh','max'}:
        command += ['--input-format','stream-json','--output-format','stream-json',
            '--agent','video-pipeline-image','--model',value['model'],'--effort',value['effort'],'--mode','accept-edits','--disable-slash-commands','--sandbox','--print-timeout','600s']
    else:
        return 1
    command += ['--log-file',os.devnull]
    with (workspace/'stdout.jsonl').open('wb') as output,(workspace/'stderr.txt').open('wb') as diagnostic:
        process=subprocess.Popen(owned_command(command),cwd=workspace,stdin=subprocess.PIPE,stdout=output,stderr=diagnostic,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        process.communicate((value.get('message') or '').encode('utf-8'),timeout=610)
        return process.returncode


if __name__=='__main__':
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(1)
