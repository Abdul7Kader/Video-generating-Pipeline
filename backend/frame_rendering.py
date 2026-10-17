"""Held illustrations, one measured speech track, bounded native FFmpeg composition."""
import json
import math
from pathlib import Path
import re

from . import frame, frame_media
from .captions import write_srt
from .failures import failure_stage, PipelineFailure
from .plan import file_sha256
from .quality import find_ffmpeg, find_ffprobe, run_quality_gate

FPS=30
SIZES={'16:9':(1280,720),'9:16':(720,1280),'1:1':(720,720)}


def frame_counts(timeline):
    rate=timeline['rate'];cursor=0;result=[]
    for item in timeline['images']:
        if item['start_sample']!=cursor or item['end_sample']<=cursor:
            raise ValueError('Lückenhafte Audio-Bild-Zeitleiste.')
        start=round(cursor*FPS/rate);cursor=item['end_sample']
        end=round(cursor*FPS/rate)
        if end<=start:
            raise ValueError('Bildabschnitt ist kürzer als ein Videoframe.')
        result.append(end-start)
    if cursor!=timeline['samples']:
        raise ValueError('Bildschluss stimmt nicht mit der gemessenen Tonspur überein.')
    return result


def compose(directory, timeline, manifest, ratio):
    from .rendering import _run
    counts=frame_counts(timeline)
    if len(counts)!=len(manifest['assets']) or [v['id'] for v in timeline['images']]!=[v['scene_id'] for v in manifest['assets']]:
        raise ValueError('Bilder und gemessene Erzählabschnitte stimmen nicht überein.')
    lines=['ffconcat version 1.0']
    for item,count in zip(manifest['assets'],counts):
        # Never interpolate provider/model filenames or arbitrary paths into a concat script.
        name=Path(item['local_file'])
        if not re.fullmatch(r'assets/[a-f0-9]{64}\.png',name.as_posix()) or file_sha256(directory/name)!=item['sha256']:
            raise ValueError('Ungültige oder veränderte Bilddatei.')
        lines += [f"file '{name.as_posix()}'",f'option framerate {FPS}',f'duration {count/FPS:.9f}']
    lines += [f"file '{Path(manifest['assets'][-1]['local_file']).as_posix()}'",f'option framerate {FPS}']
    playlist=directory/'frame-concat.txt';playlist.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    width,height=SIZES[ratio];output=directory/'video.pending.mp4'
    output.unlink(missing_ok=True)
    with failure_stage('render',aspect_ratio=ratio):
        # ffconcat requires safe=0 for the fixed per-image framerate option. Only the
        # app-written relative SHA-256 PNG names above enter this private playlist.
        _run([find_ffmpeg(),'-y','-v','error','-protocol_whitelist','file,pipe','-f','concat','-safe','0',
            '-i',str(playlist),'-i',str(directory/'narration.wav'),'-map','0:v:0','-map','1:a:0',
            '-vf',f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:white,setsar=1,fps={FPS}',
            '-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-threads','2',
            '-c:a','aac','-b:a','160k','-ar','48000','-t',f"{timeline['samples']/timeline['rate']:.9f}",
            '-movflags','+faststart',str(output)],timeout=max(600,math.ceil(timeline['duration']*5)))
    return output


def render(job, directory):
    plan=frame.validate_plan(job.get('frame_plan') or {},job['script'])
    if job['render_script_hash']!=job['script']['content_hash'] or job['approved_script_hash']!=job['script']['content_hash'] or job['render_version']!=job['script']['version']:
        raise ValueError('Frame-Video benötigt die aktuelle, unveränderte Textfreigabe.')
    if not find_ffmpeg() or not find_ffprobe():
        raise PipelineFailure('render','missing_file')
    directory=frame_media.safe_directory(directory)
    # Reuse the primary version's media for additional formats without repeated inference.
    base=directory
    if directory.parent.name=='formats':
        base=directory.parent.parent
        frame_media.safe_directory(base)
    timeline,mode=frame_media.prepare_audio(job,base)
    manifest=frame_media.prepare_images(job,base)
    if directory!=base:
        import shutil
        for folder in ('audio','assets'):
            frame_media.safe_directory(directory/folder)
        for entry in manifest['assets']:
            shutil.copyfile(base/entry['local_file'],directory/entry['local_file'])
        voice=json.loads((base/'voice-manifest.json').read_text(encoding='utf-8'))
        for entry in voice['segments']:
            target=directory/entry['file']
            if not target.exists():
                shutil.copyfile(base/entry['file'],target)
        shutil.copyfile(base/'narration.wav',directory/'narration.wav')
        for name in ('asset-manifest.json','voice-manifest.json','frame-timeline.json'):
            shutil.copyfile(base/name,directory/name)
    text=frame.narration(job['script'])
    captions=[{'narration':text[item['text_start']:item['text_end']],
               'start':item['start_sample']/timeline['rate'],
               'captions':[{'start':0,'duration':(item['end_sample']-item['start_sample'])/timeline['rate'],
                            'text':text[item['text_start']:item['text_end']]}]} for item in timeline['images']]
    write_srt(captions,directory/'subtitles.srt')
    output=compose(directory,timeline,manifest,job['aspect_ratio'])
    with failure_stage('quality'):
        report=run_quality_gate(output_path=output,audio_path=directory/'narration.wav',subtitles_path=directory/'subtitles.srt',
            asset_manifest_path=directory/'asset-manifest.json',voice_manifest_path=directory/'voice-manifest.json',
            expected_duration=timeline['duration'],expected_script_hash=job['render_script_hash'],report_path=directory/'quality-report.json')
        from .rendering import _run
        probe=json.loads(_run([find_ffprobe(),'-v','error','-show_entries','stream=codec_type,duration,width,height:format=duration','-of','json',str(output)],timeout=60).stdout)
        streams=probe['streams'];video=next(v for v in streams if v['codec_type']=='video');audio=next(v for v in streams if v['codec_type']=='audio')
        timing=all(abs(float(item['duration'])-timeline['duration'])<.10 for item in (video,audio,probe['format']))
        dimensions=(video['width'],video['height'])==SIZES[job['aspect_ratio']]
        pixels=all(item['review'].get('passed') is True and item['review'].get('evidence')=='guarded_view_file_pixels' and item['review']['image_sha256']==file_sha256(directory/item['local_file']) for item in manifest['assets'])
        report['checks'] += [{'name':'measured_frame_timing','passed':timing,'details':'Absolute Toleranz < 100 ms, unabhängig von Videolänge.'},
            {'name':'frame_dimensions','passed':dimensions,'details':job['aspect_ratio']},
            {'name':'pixel_reviews','passed':pixels,'details':f"{len(manifest['assets'])} geprüfte Rasterbilder"}]
        report['passed']=all(check['passed'] for check in report['checks'])
        frame_media.atomic_json(directory/'quality-report.json',report)
        if not report['passed']:
            raise PipelineFailure('quality','quality')
    final=directory/'video.mp4'
    output.replace(final)
    return str(final),mode
