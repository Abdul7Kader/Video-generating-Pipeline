"""Private Antigravity pre-execution hook. No model-supplied command is executed."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile


def atomic_write(path, text):
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
        temporary=Path(stream.name)
        stream.write(text)
    try:
        os.replace(temporary,path)
    finally:
        temporary.unlink(missing_ok=True)


def handle(event, value, workspace):
    workspace = Path(workspace).resolve()
    config = json.loads((workspace / 'image-request.json').read_text(encoding='utf-8'))
    deny = {'decision':'deny','reason':'Video Pipeline: only the fixed image request is permitted.'}
    reason='artifact_scope'
    try:
        artifact = Path(value['artifactDirectoryPath'])
        brain = Path.home() / '.gemini/antigravity-cli/brain'
        if not re.fullmatch(r'[a-f0-9-]{36}', artifact.name) or artifact.parent.resolve() != brain.resolve() or artifact.resolve() != brain.resolve() / artifact.name:
            raise ValueError()
        paths = value.get('workspacePaths',[])
        reason='workspace_scope'
        if not paths or any(Path(path).resolve() != workspace for path in paths):
            raise ValueError()
        if event == 'session':
            atomic_write(workspace/'guard-ready.json',json.dumps({'artifact':str(artifact)}))
            return {}
        saved = json.loads((workspace / 'guard-ready.json').read_text(encoding='utf-8'))
        reason='session_scope'
        if saved['artifact'] != str(artifact):
            raise ValueError()
        call = value['toolCall']
        if call['name'] == 'finish':
            return {'decision':'allow'}
        if call['name'] == 'generate_image':
            reason='argument_shape'
            args = call['args']
            # CLI versions serialize args either as an object or as a JSON string.
            if isinstance(args,str) and len(args)<=65536:
                args=json.loads(args)
            aliases={'Prompt':('Prompt','prompt'),'ImageName':('ImageName','imageName','image_name'),
                     'ImagePaths':('ImagePaths','imagePaths','image_paths')}
            allowed={name for names in aliases.values() for name in names}
            # CLI hooks add these UI metadata fields to the otherwise unchanged tool arguments.
            metadata={'toolAction','toolSummary'}
            if not isinstance(args,dict) or set(args)-allowed-metadata or any(sum(name in args for name in names)>1 for names in aliases.values()) or any(args.get(name) for name in aliases['ImagePaths']) or any(not isinstance(args[key],str) or len(args[key])>2000 for key in metadata & set(args)):
                raise ValueError()
            # Recheck the manufacturer's baseline-only switch at the actual tool call.
            billing = Path.home() / '.gemini/antigravity-cli/settings.json'
            reason='credit_policy'
            if billing.exists():
                if billing.stat().st_size > 65536 or json.loads(billing.read_text(encoding='utf-8-sig')).get('useG1Credits',False) is not False:
                    raise ValueError()
            reason='image_call_limit'
            with (workspace / 'image-called').open('x'):
                pass
            fixed={'Prompt':config['prompt'],'ImageName':config['image_name'],'ImagePaths':[]}
            overwrite={next((name for name in aliases[key] if name in args),key):item for key,item in fixed.items()}
            overwrite.update({key:'Generate one Frame illustration' for key in metadata & set(args)})
            return {'decision':'auto_approve','overwrite':overwrite}
        reason='tool_not_allowed'
    except (OSError,ValueError,KeyError,TypeError,AttributeError):
        pass
    atomic_write(workspace/'guard-denied',reason)
    return deny


def main():
    try:
        workspace=Path(sys.argv[2]).resolve()
        (workspace/('guard-invoked-'+sys.argv[1])).touch()
        raw = sys.stdin.buffer.read(65537)
        if len(raw)>65536:
            raise ValueError()
        value=json.loads(raw)
        call=value.get('toolCall',{})
        shape={'fields':sorted(value.keys()),'tool_fields':sorted(call.keys()) if isinstance(call,dict) else [],
               'args_type':type(call.get('args')).__name__ if isinstance(call,dict) else '',
               'args_fields':sorted(key for key in call.get('args',{}) if re.fullmatch(r'[A-Za-z_]{1,48}',key))[:16] if isinstance(call,dict) and isinstance(call.get('args'),dict) else []}
        atomic_write(workspace/'guard-fields.json',json.dumps(shape))
        result=handle(sys.argv[1],value,workspace)
    except Exception:
        result={'decision':'deny','reason':'Video Pipeline image guard could not validate the request.'}
    print(json.dumps(result))


if __name__ == '__main__':
    main()
