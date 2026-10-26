"""Apply coordinated deck volume automation to the user-approved rhythmic tease."""
import json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.experiments import dj_lab as dj,remix_lab as lab

def main():
    previous=ROOT/'runs/_dj_lab/kala_nashe_rhythmic_entrance_20261026_v2/01_03_bollywood_pressure_drop_lead16'
    original=ROOT/'runs/_dj_lab/club_session_20261026_v1/03_bollywood_pressure_drop'
    out=ROOT/'runs/_dj_lab/kala_nashe_volume_handover_20261026_v1';out.mkdir(exist_ok=False)
    revision=json.loads((previous/'revision.json').read_text())
    beat=60/revision['previous_plan']['target_bpm'];lead=16
    start=round(revision['incoming_start_s']*lab.SR);focus=round(revision['focus_time_s']*lab.SR)
    b=lab.decode(previous/'incoming_bus.wav');a=lab.decode(previous/'outgoing_unchanged.wav');fx=lab.decode(original/'bus_fx.wav')
    t=np.arange(len(b))/lab.SR/beat
    old_gain=np.interp(t,[0,2,8,12,16,20],[0,.35,.65,.80,.95,1])
    # Smooth continuous incoming rise; retain all repeat edits and bass automation.
    progress=np.clip(t/lead,0,1)
    new_gain=np.sin(progress*np.pi/2)**1.25
    ratio=np.divide(new_gain,old_gain,out=np.zeros_like(new_gain),where=old_gain>1e-9)
    b*=ratio[:,None]
    timeline=np.arange(len(a))
    phase=np.clip((timeline-start)/(focus-start),0,1)
    outgoing_gain=np.cos(phase*np.pi/2)
    outgoing_gain[timeline>=focus]=0
    assert np.all(np.diff(outgoing_gain)<=1e-10)
    assert np.all(np.diff(new_gain)>=-1e-10)
    assert np.array_equal(a[:start],(a*outgoing_gain[:,None])[:start])
    a*=outgoing_gain[:,None];fx*=outgoing_gain[:,None]
    reference=lab.decode(previous/'master.wav')
    raw=a+fx;length=min(len(b),len(raw)-start);raw[start:start+length]+=b[:length]
    raw=dj.edge_ramp(raw[:len(reference)],.012,.8)
    for name,x in [('master',raw),('previous',reference),('outgoing_bus',a),('incoming_bus',b)]:lab.write(out/f'{name}.wav',x)
    stats=[lab.loudness(out/f'{name}.wav') for name in ['master','previous']]
    target=min(-16,*[v['input_i']-2-v['input_tp'] for v in stats]);levels={}
    for name in ['master','previous']:
        levels[name]=lab.listening_copy(out/f'{name}.wav',out/f'{name}_listening.wav',target)
        dest=out/('Kala_to_Nashe_tease_gradual_handover.mp3' if name=='master' else 'Previous_tease_comparison.mp3')
        lab.run(['ffmpeg','-v','error','-n','-i',out/f'{name}_listening.wav','-c:a','libmp3lame','-b:a','256k',dest])
        checks=lab.waveform_checks(lab.decode(dest),len(raw));assert not checks['failures'],checks
        levels[name]['mp3']=lab.loudness(dest);assert levels[name]['mp3']['input_tp']<=-1
    assert abs(levels['master']['mp3']['input_i']-levels['previous']['mp3']['input_i'])<.15
    lab.dump(out/'revision.json',{'approved_tease_source':str(previous),'previous_sha256':lab.sha(previous/'master.wav'),'overlap_start_s':start/lab.SR,'handover_s':focus/lab.SR,'incoming_curve':'sin(pi/2 * progress)^1.25 replaces prior gain','outgoing_curve':'cos(pi/2 * progress)','repeat_schedule':revision['repeat_schedule'],'levels':levels,'review':'Pending listening; rhythmic edits retained, deck volumes changed'})
    print(out/'Kala_to_Nashe_tease_gradual_handover.mp3',flush=True)

if __name__=='__main__':main()
