"""Explicit native two-still boundary fixture. No AI or voice generation."""
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend import frame_media as media, frame_rendering as render
from backend.config import settings
from backend.plan import file_sha256
from backend.quality import find_ffmpeg


def png(color):
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',128,128,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(color)*128)*128))+chunk(b'IEND',b'')


def main():
    directory=media.safe_directory(settings.data_dir/'frame-boundary-proof');media.safe_directory(directory/'assets')
    source=settings.data_dir/'frame-composition-proof/16x9/v1/narration.wav'
    shutil.copyfile(source,directory/'narration.wav')
    total=media.pcm_info(source);boundary=125123
    timeline={'rate':media.RATE,'samples':total,'duration':total/media.RATE,'images':[
        {'id':'red','start_sample':0,'end_sample':boundary},{'id':'blue','start_sample':boundary,'end_sample':total}]}
    assets=[]
    for identifier,color in [('red',(255,0,0)),('blue',(0,0,255))]:
        data=png(color);key=media.object_sha256(list(color));path=directory/'assets'/(key+'.png');path.write_bytes(data)
        assets.append({'scene_id':identifier,'local_file':str(path.relative_to(directory)),'sha256':file_sha256(path)})
    output=render.compose(directory,timeline,{'assets':assets},'16:9')
    switch=render.frame_counts(timeline)[0]
    decoded=subprocess.run([find_ffmpeg(),'-v','error','-i',str(output),'-vf',f'select=eq(n\\,{switch-1})+eq(n\\,{switch})',
        '-fps_mode','vfr','-frames:v','2','-f','rawvideo','-pix_fmt','rgb24','pipe:1'],capture_output=True,check=True,timeout=30).stdout
    size=1280*720*3;center=(360*1280+640)*3
    assert len(decoded)==2*size
    first=decoded[center:center+3];second=decoded[size+center:size+center+3]
    assert first[0]>240 and first[2]<20 and second[2]>240 and second[0]<20,(list(first),list(second))
    result={'passed':True,'proof_kind':'synthetic_two_color_native_boundary','switch_frame':switch,
            'measured_boundary_sample':boundary,'boundary_error_seconds':abs(switch/render.FPS-boundary/media.RATE)}
    assert result['boundary_error_seconds']<1/render.FPS
    media.atomic_json(directory/'result.json',result);print(json.dumps(result))


if __name__=='__main__':main()
