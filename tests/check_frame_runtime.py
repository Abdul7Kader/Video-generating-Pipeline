"""Explicit necessary live acceptance. Not part of unit discovery; no posting or settings mutation.

Run: python tests/check_frame_runtime.py
Reuses the fixed acceptance project's validated files when run again after a repair.
"""
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from backend import frame, images, frame_media
from backend.config import settings
from backend.db import Database
from backend.plan import file_sha256
from backend.rendering import render_job
from backend.schemas import JobCreate, ProductionConfig


def main():
    directory=frame_media.safe_directory(settings.data_dir/'frame-acceptance')
    database=Database(directory/'acceptance.sqlite3');database.initialize()
    config=ProductionConfig(profile_id='cloud_stickman',script_provider='antigravity',voice_provider='piper',voice_id='thorsten',voice_speed=1)
    request=JobCreate(generation_mode='frame',topic='Eine Katze findet ein Zuhause',input_kind='narration',
        narration='Eine orange Katze tritt vorsichtig aus ihrer Transportbox. Eine junge Frau kniet daneben und begrüßt sie mit offener Hand. Dann sitzt dieselbe Katze entspannt auf dem Schoß der Frau. In ihrem neuen Zuhause fühlt sie sich sicher.',
        duration_seconds=15,aspect_ratios=['16:9','9:16'],production_config=config)
    job_id='b6763816-3b0e-4d2b-b1db-d00d5f044707'
    existing=database.get_job(job_id)
    if not existing:
        database.create_job(request.model_dump(),frame.draft(request),job_id=job_id)
    job=database.get_job(job_id)
    if not job.get('frame_plan'):
        database.approve_script(job_id,job['script_version'],job['script']['content_hash'])
        database.begin_planning(job_id,job['script_version'])
        print('Real semantic plan',flush=True)
        plan=frame.plan_images(request,job['script'])
        job=database.save_frame_plan(job_id,job['script_version'],job['script']['content_hash'],plan)
    print('Images',len(job['frame_plan']['images']),flush=True)
    database.queue_render(job_id,job['script_version'],job['script']['content_hash'])
    job=database.claim_render()
    base=directory/'jobs'/job_id/'v1';outputs={}
    try:
        # Explicit test-only selection of the already authorized Google subscription.
        # The user's saved provider and Cloudflare credentials remain untouched.
        generate=images.generate
        def checked_generate(*args,**kwargs):
            try:return generate(*args,**kwargs)
            except Exception as error:
                print('Image adapter diagnosis',type(error).__name__,getattr(error,'code',''),getattr(error,'adapter_phase',''),getattr(error,'adapter_error_type',''),getattr(error,'guard_reason',''),getattr(error,'guard_tool',''),getattr(error,'guard_shape',{}),flush=True)
                print('Own image export',getattr(error,'candidate_count',''),getattr(error,'artifact_session',''),getattr(error,'artifact_entries',[]),flush=True)
                raise
        with patch.object(images,'load',return_value=images.Preferences(provider='antigravity')),patch.object(images,'generate',side_effect=checked_generate):
            frame_media.production_readiness(job)
            for ratio in job['aspect_ratios']:
                target=base if ratio==job['aspect_ratio'] else base/'formats'/ratio.replace(':','x')
                print('Real render',ratio,flush=True)
                output,mode=render_job(job|{'aspect_ratio':ratio},job_dir_override=target)
                outputs[ratio]={'path':str(Path(output).relative_to(directory/'jobs')),'sha256':file_sha256(Path(output))}
        database.finish_render_variants(job_id,1,outputs,mode)
        report={'passed':True,'job_id':job_id,'billing_policy':'baseline-only','posted':False,
                'outputs':outputs,'duration':json.loads((base/'frame-timeline.json').read_text())['duration'],
                'images':len(job['frame_plan']['images']),'limits':['Lange reale Filme und Nutzerbewertung bleiben ausstehend.','Cloudflare ohne Zugangsdaten nicht live geprüft.']}
        frame_media.atomic_json(directory/'result.json',report)
        print(json.dumps(report,ensure_ascii=True),flush=True)
    except Exception as error:
        database.fail_render(job_id,str(error))
        raise


if __name__=='__main__':main()
