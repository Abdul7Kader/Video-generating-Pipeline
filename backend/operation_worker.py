"""Private worker protocol: fixed plan/render actions; no user-supplied commands."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    request, result = map(Path, sys.argv[1:])
    from backend import failures
    failures.progress_path = result.with_name('progress.json')
    try:
        value = json.loads(request.read_text(encoding='utf-8'))
        payload = value['payload']
        if value['kind'] == 'plan':
            from backend.story import generate_storyboard
            from backend.schemas import JobCreate
            with failures.failure_stage('planning'):
                output = generate_storyboard(JobCreate.model_validate(payload['request']), payload['script'])
        elif value['kind'] == 'render':
            from backend.rendering import render_job
            output = render_job(payload['job'], job_dir_override=Path(payload['directory']) if payload['directory'] else None)
        elif value['kind'] == 'revise':
            from backend.story import generate_story
            from backend.schemas import JobCreate
            with failures.failure_stage('script'):
                output = generate_story(JobCreate.model_validate(payload['request']), previous=payload['script'], instructions=payload['instructions'])
        else:
            raise failures.PipelineFailure('request','unsupported_action')
        response = {'value': output}
    except Exception as error:
        failure = failures.describe(error,{'plan':'planning','render':'render','revise':'script'}.get(value.get('kind'),'request') if isinstance(locals().get('value'),dict) else 'request')
        response = {'error':str(failure),'failure':failure.wire()}
    temporary = result.with_suffix('.pending')
    temporary.write_text(json.dumps(response, ensure_ascii=False), encoding='utf-8')
    temporary.replace(result)


if __name__ == '__main__':
    main()
