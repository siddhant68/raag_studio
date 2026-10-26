"""Long overlapping deck blends, keeping existing outgoing exit buses."""
import copy,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from app.experiments import dj_lab as dj,remix_lab as lab
from scipy import signal

def main():
    root=ROOT/'runs/_dj_lab/club_session_20261026_v1'
    out=ROOT/'runs/_dj_lab/kala_nashe_overlap_20261026_v1';out.mkdir(exist_ok=False)
    cases=[('03_bollywood_pressure_drop',16),('03_bollywood_pressure_drop',32)]
    summary=[]
    for index,(name,lead) in enumerate(cases,1):
        old=root/name;p=json.loads((old/'plan.json').read_text());r=json.loads((old/'result.json').read_text())
        folder=out/f'{index:02d}_{name}_lead{lead}';folder.mkdir()
        beat=60/p['target_bpm'];at=round(r['reveal_s']*lab.SR);n=round(lead*beat*lab.SR)
        s=copy.deepcopy(p['b']);s['cue_s']-=8*60/s['bpm'];s['beats']+=8
        if s['cue_s']<0:raise ValueError('Not enough real pre-roll')
        joint=dj._prepare(s,p['target_bpm'],folder/'incoming_continuous')
        old_gain=json.loads((old/'deck_b/transform.json').read_text())['gain_db']
        new_gain=json.loads((folder/'incoming_continuous/transform.json').read_text())['gain_db']
        joint*=10**((old_gain-new_gain)/20)*r['master_gain']
        low,high=lab.split_bands(joint)
        t=np.arange(len(joint))/lab.SR/beat
        # Audibly establish both decks well before the outgoing loop/exit.
        # Bass enters across the final eight beats as the existing exit removes A bass.
        gain=np.interp(t,[0,lead*.125,lead*.5,lead*.75,lead,lead+4],[0,.35,.65,.80,.95,1])
        bass=np.sin(np.clip((t-(lead-8))/8,0,1)*np.pi/2)**2
        shaped=(high+low*bass[:,None])*gain[:,None]
        original=lab.decode(old/'master.wav');a=lab.decode(old/'bus_a.wav');fx=lab.decode(old/'bus_fx.wav')
        raw=a+fx
        start=at-n;length=min(len(shaped),len(raw)-start)
        raw[start:start+length]+=shaped[:length]
        raw=raw[:start+length]
        original=original[:len(raw)]
        raw=dj.edge_ramp(raw,.012,.8)
        # Compare exact outgoing bus, not a normalized combined waveform.
        lab.write(folder/'outgoing_unchanged.wav',a)
        assert np.array_equal(a,lab.decode(folder/'outgoing_unchanged.wav'))
        lab.write(folder/'incoming_bus.wav',shaped)
        lab.write(folder/'master.wav',raw);lab.write(folder/'previous.wav',original)
        stats=[lab.loudness(folder/f'{arm}.wav') for arm in ['master','previous']]
        target=min(-16,*[v['input_i']-2-v['input_tp'] for v in stats])
        levels={}
        for arm in ['master','previous']:
            levels[arm]=lab.listening_copy(folder/f'{arm}.wav',folder/f'{arm}_listening.wav',target)
            lab.run(['ffmpeg','-v','error','-n','-i',folder/f'{arm}_listening.wav','-c:a','libmp3lame','-b:a','256k',folder/f'{arm}.mp3'])
            levels[arm]['mp3']=lab.loudness(folder/f'{arm}.mp3')
            checks=lab.waveform_checks(lab.decode(folder/f'{arm}.mp3'),len(raw))
            assert not checks['failures'],checks
            assert levels[arm]['mp3']['input_tp']<=-1
        assert abs(levels['master']['mp3']['input_i']-levels['previous']['mp3']['input_i'])<.15
        revision={'previous_plan':p,'previous_master_sha256':lab.sha(old/'master.wav'),'incoming_lead_beats':lead,'incoming_start_s':start/lab.SR,'focus_time_s':at/lab.SR,'bass_release_beats':8,'gain_at_focus':.95,'source_start_s':s['cue_s'],'source_note':'Real earliest aligned passage, no fabricated pre-roll; focus cue differs from original to support long overlap','outgoing_bus_sample_identical':True,'levels':levels,'models':[],'review':'Awaiting listening; automated checks do not establish smoothness'}
        lab.dump(folder/'revision.json',revision)
        dest=out/f'{index:02d}_Kala_to_Nashe_overlap_{lead//4}bars.mp3'
        dest.write_bytes((folder/'master.mp3').read_bytes())
        summary.append({'file':dest.name,'lead_s':round(n/lab.SR,2),'focus_s':at/lab.SR,'revision':str(folder.relative_to(out))})
        lab.dump(out/'summary.json',summary);print(summary[-1],flush=True)

if __name__=='__main__':main()
