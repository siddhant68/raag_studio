"""Exact audio-driven vertical preview; original music or private user sources."""
from pathlib import Path
import json
import textwrap

from PIL import Image,ImageDraw,ImageFont

from . import remix_lab as lab


def render(folder,output):
    folder,output=Path(folder),Path(output)
    if output.exists():raise FileExistsError(output)
    result=json.loads((folder/"result.json").read_text())
    plan=json.loads((folder/"plan.json").read_text())
    font_path=Path('/System/Library/Fonts/Supplemental/Arial.ttf')
    if not font_path.exists():
        candidates=list(Path('/usr/share/fonts').rglob('DejaVuSans.ttf'))
        if not candidates:raise ValueError('Install Arial or DejaVu Sans for the reel export')
        font_path=candidates[0]
    def font(size):return ImageFont.truetype(str(font_path),size)
    def lines(draw,text,xy,size,color,width):
        words=text.split();line='';yy=xy[1]
        for word in words:
            candidate=(line+' '+word).strip()
            if draw.textlength(candidate,font=font(size))>width and line:
                draw.text((xy[0],yy),line,font=font(size),fill=color);yy+=size+12;line=word
            else:line=candidate
        if line:draw.text((xy[0],yy),line,font=font(size),fill=color)
    for phase in ('setup','reveal'):
        image=Image.new('RGB',(720,1280),'#101211');d=ImageDraw.Draw(image)
        d.ellipse((60,55,112,107),fill='#d5ef78');d.text((70,55),'r.',font=font(37),fill='#101211')
        d.text((129,64),'raag studio / DJ LAB',font=font(22),fill='#f1f1df')
        d.line((60,145,660,145),fill='#343a34',width=2)
        d.text((64,190),'TWO SONGS. ONE MOMENT.',font=font(17),fill='#9da79d')
        lines(d,'Keep the hook.\nMake the entrance.',(60,232),53,'#f1f1df',610)
        color='#72cebb' if phase=='setup' else '#ec9a6b'
        d.rounded_rectangle((60,400,660,552),radius=18,fill='#1d241e',outline=color,width=2)
        d.text((84,421),'THE SETUP' if phase=='setup' else 'THE REVEAL',font=font(17),fill=color)
        source=plan['a' if phase=='setup' else 'b']['name'][:110]
        lines(d,source,(84,459),24,'#f1f1df',550)
        d.text((64,587),'ACTUAL AUDIO / LIVE WAVEFORM',font=font(14),fill='#9da79d')
        d.line((64,845,656,845),fill='#343a34',width=2)
        d.text((64,879),{'loop_drop':'PRESSURE → DROP','echo_reveal':'ECHO & REVEAL','echo_reset':'TEMPO PORTAL','reel_switch':'REEL SWITCH','bass_swap':'VELVET BLEND'}.get(result['preset'],'DJ TRANSITION'),font=font(26),fill='#d5ef78')
        d.text((64,928),f"Handover at {result['reveal_s']:.1f}s",font=font(21),fill='#9da79d')
        d.text((64,1020),'Pick two tracks. Shape the handover.',font=font(23),fill='#f1f1df')
        d.text((64,1057),'Hear both versions. Keep your favorite.',font=font(23),fill='#f1f1df')
        sharing='Original-music demo' if result['sharing']=='original_generated_sources' else 'Private listening experiment'
        d.line((60,1150,660,1150),fill='#343a34',width=2)
        d.text((64,1180),sharing,font=font(16),fill='#9da79d')
        image.save(folder/f'visualizer_{phase}.png')
    reveal=result['reveal_s']
    graph=f"[2:a]asplit=2[a][w];[w]showwaves=s=592x190:mode=cline:colors=0xd5ef78:r=25:scale=sqrt[wave];[0:v][1:v]overlay=enable='gte(t,{reveal:.6f})'[bg];[bg][wave]overlay=64:620,format=yuv420p[v]"
    command=['ffmpeg','-v','error','-n','-loop','1','-framerate','25','-i',folder/'visualizer_setup.png','-loop','1','-framerate','25','-i',folder/'visualizer_reveal.png','-i',folder/'master_listening.wav','-filter_complex',graph,'-map','[v]','-map','[a]','-t',result['duration_s'],'-c:v','libx264','-preset','veryfast','-crf','22','-threads','2','-c:a','aac','-b:a','192k','-movflags','+faststart',output]
    lab.run(command)
    probe=json.loads(lab.run(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,codec_name,width,height','-of','json',output]).stdout)
    if abs(float(probe['format']['duration'])-result['duration_s'])>.1:raise ValueError('Visualizer duration mismatch')
    if not any(s.get('codec_type')=='audio' for s in probe['streams']):raise ValueError('Visualizer has no audio')
    lab.dump(folder/'visualizer_audit.json',{'command':list(map(str,command)),'probe':probe,'sha256':lab.sha(output),'sharing':result['sharing']})
    return {'engine':'deterministic_dj','duration_s':result['duration_s'],'file':str(output)}
