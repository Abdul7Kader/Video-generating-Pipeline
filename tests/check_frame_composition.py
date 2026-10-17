"""Explicit real-media composition proof using an existing reviewed image. No AI calls."""
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import frame, frame_media, frame_rendering
from backend.captions import write_srt
from backend.config import settings
from backend.plan import file_sha256, script_hash
from backend.quality import run_quality_gate, find_ffprobe
from backend.rendering import _run
from backend.schemas import JobCreate, ProductionConfig


def main():
    directory=frame_media.safe_directory(settings.data_dir/'frame-composition-proof')
    source=settings.data_dir/'image-previews/92aff26c56b34f42b23daf238b1334af.png'
    review=json.loads((settings.data_dir/'frame-vision-post-proof.json').read_text(encoding='utf-8'))
    if not review['passed'] or review['image_sha256']!=file_sha256(source):
        raise ValueError('Vorhandenes tatsächlich geprüftes Bild fehlt oder wurde verändert.')
    text='Eine orange Katze tritt aus ihrer Transportbox. Ein kniender Mensch heißt sie willkommen.'
    config=ProductionConfig(profile_id='cloud_stickman',script_provider='antigravity',voice_provider='piper',voice_id='thorsten')
    request=JobCreate(generation_mode='frame',topic='Vorhandenes Katzenbild · reiner Schnittnachweis',input_kind='narration',narration=text,production_config=config,duration_seconds=15)
    script=frame.build_script(request,text);script.update(version=1,content_hash=script_hash(script))
    job={'script':script,'production_config':config.model_dump(),'language':'de',
         'frame_plan':{'text_sha256':frame_media.object_sha256(text),'images':[{'id':'composition-proof','text_start':0,'text_end':len(text)}]}}
    base=frame_media.safe_directory(directory/'16x9/v1')
    timeline,mode=frame_media.prepare_audio(job,base)
    reports=[]
    for ratio in ('16:9','9:16'):
        target=base if ratio=='16:9' else frame_media.safe_directory(base/'formats'/ratio.replace(':','x'))
        assets=frame_media.safe_directory(target/'assets')
        digest=file_sha256(source);image=assets/(digest+'.png');shutil.copyfile(source,image)
        if target!=base:
            frame_media.safe_directory(target/'audio')
            voice=json.loads((base/'voice-manifest.json').read_text(encoding='utf-8'))
            for entry in voice['segments']:
                shutil.copyfile(base/entry['file'],target/entry['file'])
            for filename in ('narration.wav','voice-manifest.json','frame-timeline.json'):
                shutil.copyfile(base/filename,target/filename)
        manifest={'assets':[{'scene_id':'composition-proof','local_file':str(image.relative_to(target)),
                             'sha256':digest,'review':review,'provenance':{'provider':'antigravity','image_model':'not_reported','reused_existing_real_image':True}}]}
        frame_media.atomic_json(target/'asset-manifest.json',manifest)
        write_srt([{'start':0,'captions':[{'text':text,'start':0,'duration':timeline['duration']}]}],target/'subtitles.srt')
        output=frame_rendering.compose(target,timeline,manifest,ratio)
        report=run_quality_gate(output_path=output,audio_path=target/'narration.wav',subtitles_path=target/'subtitles.srt',
            asset_manifest_path=target/'asset-manifest.json',voice_manifest_path=target/'voice-manifest.json',expected_duration=timeline['duration'],
            expected_script_hash=script['content_hash'],report_path=target/'quality-report.json')
        probe=json.loads(_run([find_ffprobe(),'-v','error','-show_entries','stream=codec_type,duration,width,height:format=duration','-of','json',str(output)]).stdout)
        assert all(abs(float(stream['duration'])-timeline['duration'])<.1 for stream in probe['streams'])
        video=next(stream for stream in probe['streams'] if stream['codec_type']=='video')
        assert (video['width'],video['height'])==frame_rendering.SIZES[ratio]
        final=target/'video.mp4';output.replace(final)
        reports.append({'ratio':ratio,'path':str(final),'sha256':file_sha256(final),'duration':timeline['duration'],'quality_passed':report['passed'],'voice':mode})
    result={'passed':True,'proof_kind':'composition_and_local_voice_with_existing_reviewed_google_image',
            'new_image_series_live':False,'external_calls':0,'outputs':reports}
    frame_media.atomic_json(directory/'result.json',result)
    print(json.dumps(result,ensure_ascii=True))


if __name__=='__main__':main()
