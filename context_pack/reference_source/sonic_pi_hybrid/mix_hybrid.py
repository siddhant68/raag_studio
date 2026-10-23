"""Keep the real Sonic Pi backing and combine it with an isolated generated vocal."""
import json,subprocess
from pathlib import Path
import numpy as np,soundfile as sf,pyloudnorm as pyln
from scipy import signal

root=Path(__file__).resolve().parent
sr=48000;bpm=76;beat=60/bpm;bar=4*beat
duration=16*bar+2.7;n=round(duration*sr)
meter=pyln.Meter(sr)
def level(y,target):
    return y*10**((target-meter.integrated_loudness(y))/20)
def fade(y,attack,release):
    y=y.copy();a=min(len(y),round(attack*sr));b=min(len(y),round(release*sr))
    if a:y[:a]*=np.sin(np.linspace(0,np.pi/2,a))[:,None]**2
    if b:y[-b:]*=np.cos(np.linspace(0,np.pi/2,b))[:,None]**2
    return y
back,bsr=sf.read(root/'Sonic_Pi_Backing_Native.wav',dtype='float32',always_2d=True)
assert bsr==sr
energy=np.sqrt(np.mean(back*back,axis=1))
onset=int(np.where(energy>.002)[0][0])-round(.007*sr)
back=back[max(0,onset):]
back=np.pad(back,((0,max(0,n-len(back))),(0,0)))[:n]
back=level(fade(back,.008,2.3),-23)
sf.write(root/'Sonic_Pi_Backing.wav',level(back,-15),sr,subtype='PCM_24')
v,vsr=sf.read(root/'Vocal_Isolated.wav',dtype='float32',always_2d=True)
assert vsr==sr
# Keep the vocal center and preserve its words; no pitch conversion or resinging.
v=np.repeat(v.mean(axis=1)[:,None],2,axis=1)
v=signal.sosfiltfilt(signal.butter(2,75,fs=sr,btype='highpass',output='sos'),v,axis=0)
v=level(fade(v,.025,1.0),-18.5)
placed=np.zeros((n,2),np.float64)
entry=round(2*bar*sr);count=min(len(v),n-entry)
placed[entry:entry+count]=v[:count]
# A restrained two-decibel duck leaves the words space while retaining dynamics.
env=np.sqrt(signal.lfilter(np.ones(2400)/2400,[1],np.mean(placed**2,axis=1))+1e-12)
activity=np.clip((env-.005)/.04,0,1)
duck=10**((-2.0*activity)/20)
mix=fade(back*duck[:,None]+placed,.02,2.0)
sf.write(root/'Hybrid_Premaster.wav',mix,sr,subtype='FLOAT')
ffmpeg='/opt/homebrew/bin/ffmpeg'
def run(args):return subprocess.run([ffmpeg,'-hide_banner','-y',*map(str,args)],check=True,capture_output=True,text=True)
def parse(log):return json.JSONDecoder().raw_decode(log[log.rfind('{'):])[0]
m=parse(run(['-i',root/'Hybrid_Premaster.wav','-af','loudnorm=I=-15:TP=-1.5:LRA=14:print_format=json','-f','null','-']).stderr)
f=('loudnorm=I=-15:TP=-1.5:LRA=14:linear=true:print_format=json'
   f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}"
   f":measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
out=root/'Thodi_Der_Aur_Sonic_Pi_Test.wav'
master=run(['-i',root/'Hybrid_Premaster.wav','-af',f,'-ar','48000','-c:a','pcm_s24le',out])
for source,dest,title in [(out,'Thodi_Der_Aur_Sonic_Pi_Test.mp3','Thodi Der Aur - Sonic Pi Test'),
    (root/'Sonic_Pi_Backing.wav','Sonic_Pi_Backing.mp3','Thodi Der Aur - Sonic Pi Backing')]:
    run(['-i',source,'-c:a','libmp3lame','-b:a','320k','-metadata','title='+title,root/dest])
y,_=sf.read(out,dtype='float32',always_2d=True)
assert np.isfinite(y).all() and abs(y).max()<1
report={'duration_seconds':len(y)/sr,'bpm':bpm,'key_requested':'D major',
    'backing_source':'Actual Sonic Pi engine recording; no AI reorchestration.',
    'recording_lead_removed_seconds':onset/sr,'vocal_entry_seconds':entry/sr,
    'vocal_source':'ACE-Step vocal_01, then local HDemucs separation.',
    'vocal_target_lufs':-18.5,'backing_target_lufs':-23,'standalone_backing_lufs':-15,'duck_db':2,
    'clipped_samples':int(np.sum(abs(y)>=1)),'peak_dbfs':float(20*np.log10(abs(y).max())),
    'normalization':parse(master.stderr),
    'limit':'Mixing and separation do not correct wrong consonants or regenerate individual syllables.'}
(root/'mix_report.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
