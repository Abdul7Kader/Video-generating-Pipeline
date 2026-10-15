"""Private worker protocol: fixed plan/render actions; no user-supplied commands."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    request, result = map(Path, sys.argv[1:])
    try:
        value = json.loads(request.read_text(encoding='utf-8'))
        payload = value['payload']
        if value['kind'] == 'plan':
            from backend.story import generate_storyboard
            from backend.schemas import JobCreate
            output = generate_storyboard(JobCreate.model_validate(payload['request']), payload['script'])
        elif value['kind'] == 'render':
            from backend.rendering import render_job
            output = render_job(payload['job'], job_dir_override=Path(payload['directory']) if payload['directory'] else None)
        else:
            raise ValueError('Unbekannter Produktionsschritt')
        response = {'value': output}
    except Exception as error:
        # Existing provider errors are already public-safe; no tracebacks or environment.
        response = {'error': str(error)[:2000]}
    temporary = result.with_suffix('.pending')
    temporary.write_text(json.dumps(response, ensure_ascii=False), encoding='utf-8')
    temporary.replace(result)


if __name__ == '__main__':
    main()
