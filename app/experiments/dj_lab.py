"""Real, reproducible stereo DJ edits. No models, invented stems or taste scores.

The API invokes this module in the configured audio Python, keeping numerical
dependencies out of the web server. Source cues and grids are editable estimates.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import time

import numpy as np
from scipy import signal, optimize

from . import remix_lab as lab

SR = 48000
PRESETS = {
    "tease_blend": {"name": "Tease & handover", "description": "A four-bar overlap, tightening incoming repeats and a gradual volume handover.", "use_case": "Club · Bollywood · rhythmic entrances"},
    "bass_swap": {"name": "Velvet blend", "description": "An eight-beat blend with one bass owner.", "use_case": "Warm-up · lounge · continuous mixes"},
    "loop_drop": {"name": "Pressure → drop", "description": "A four-beat fragment tightens before the next entrance.", "use_case": "Club · dance floor · reveal"},
    "echo_reveal": {"name": "Echo & reveal", "description": "The outgoing phrase echoes into the next track.", "use_case": "Parties · hook changes"},
    "echo_reset": {"name": "Tempo portal", "description": "An echo exit connects two tracks at their own tempos.", "use_case": "Bollywood ↔ dance · genre changes"},
    "reel_switch": {"name": "Reel switch", "description": "A short setup, a brief breath, then a recognizable entrance.", "use_case": "Reels · outfit changes · before/after"},
}


def validate_plan(p):
    if p.get("schema") != "raag-dj-plan/1" or p.get("preset") not in PRESETS:
        raise ValueError("Unknown DJ plan or technique")
    if not lab.finite_number(p.get("target_bpm")) or not 60 <= p["target_bpm"] <= 180:
        raise ValueError("Target tempo must be between 60 and 180 BPM")
    for role in ("a", "b"):
        s = p.get(role, {})
        for key in ("bpm", "cue_s", "beats"):
            if not lab.finite_number(s.get(key)):
                raise ValueError(f"{role}: invalid {key}")
        if not 60 <= s["bpm"] <= 180 or s["cue_s"] < 0:
            raise ValueError(f"{role}: invalid source tempo or cue")
        if type(s["beats"]) is not int or s["beats"] not in (8, 16, 24, 32, 48, 64):
            raise ValueError("Source length must be 8, 16, 24, 32, 48 or 64 beats")
        path = Path(s.get("path", ""))
        if not path.is_file() or lab.sha(path) != s.get("sha256"):
            raise ValueError(f"{role}: source missing or hash changed")
        duration = float(json.loads(lab.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path]).stdout)["format"]["duration"])
        if s["cue_s"] + s["beats"] * 60 / s["bpm"] > duration - .005:
            raise ValueError(f"{role}: selected passage extends past the source. Choose an earlier cue or fewer beats.")
        if p["preset"] not in ("echo_reset", "reel_switch") and abs(p["target_bpm"] / s["bpm"] - 1) > .15:
            raise ValueError("More than 15% tempo change: use Tempo portal to keep both original tempos")
    if p["preset"] == "tease_blend" and min(p[r]["beats"] for r in ("a", "b")) < 24:
        raise ValueError("Tease & handover needs at least 24 beats on each deck")
    return p


def edge_ramp(x, fade_in=.003, fade_out=.02):
    y = x.copy()
    for count, at_start in ((round(fade_in*SR), True), (round(fade_out*SR), False)):
        count = min(count, len(y)//2)
        if count:
            ramp = np.sin(np.linspace(0, np.pi/2, count))**2
            if at_start:
                y[:count] *= ramp[:,None]
            else:
                y[-count:] *= ramp[::-1,None]
    return y


def tease_blend(b, beat_s):
    """Approved 16-beat overlap: B tease, bass rise and continuous groove release.

    The cue is the audible overlap start, not the later release point.
    """
    beat=beat_s*SR;release=round(16*beat)
    if len(b)<round(24*beat):
        raise ValueError("Tease & handover needs at least 24 incoming beats")
    joint=b.copy();template=b[release:round(20*beat)].copy()
    schedule=[];cursor=0.0
    for span,unit in ((4,2),(2,1),(2,.5)):
        for _ in range(round(span/unit)):
            begin,end=round((8+cursor)*beat),round((8+cursor+unit)*beat)
            joint[begin:end]=edge_ramp(template[:end-begin],.004,.006)
            schedule.append({"at_beat":8+cursor,"repeat_beats":unit})
            cursor+=unit
    count=round(.004*SR)
    joint[release:release+count]*=np.sin(np.linspace(0,np.pi/2,count))[:,None]**2
    low,high=lab.split_bands(joint)
    t=np.arange(len(joint))/beat
    phase=np.clip(t/16,0,1)
    gain=np.sin(phase*np.pi/2)**1.25
    bass=np.sin(np.clip((t-8)/8,0,1)*np.pi/2)**2
    return (high+low*bass[:,None])*gain[:,None], np.cos(phase*np.pi/2), gain, schedule


def add_bus(master, bus, start):
    if start < 0 or start+len(bus) > len(master):
        raise ValueError("Bus outside the output timeline")
    master[start:start+len(bus)] += bus


def beat_echo(x, beat_s, repeats=5, feedback=.36):
    if not .0 <= feedback <= .65 or not 1 <= repeats <= 8:
        raise ValueError("Echo feedback/repeats out of bounds")
    delay = round(beat_s * .75 * SR)  # dotted-eighth, expressed in quarter-note beats
    filtered = signal.sosfiltfilt(signal.butter(2,[450,5000],btype="bandpass",fs=SR,output="sos"),x,axis=0)
    out = np.zeros((len(x)+delay*repeats,2),dtype=np.float32)
    for i in range(1,repeats+1):
        add_bus(out,filtered*feedback**i,delay*i)
    return out


def roll(x, beat_s):
    """Eight-beat build. Identical source slice, no random cuts or new noise."""
    beat = SR*beat_s
    if len(x) < round(4*beat):
        raise ValueError("Need a full four-beat loop")
    template = x[:round(4*beat)]
    total = round(8*beat)
    out = np.zeros((total,2),dtype=np.float32)
    schedule = []
    cursor = 0.0
    for span, length in ((4,4),(2,1),(1,.5),(1,.25)):
        for _ in range(round(span/length)):
            begin,end = round(cursor*beat),round((cursor+length)*beat)
            piece = edge_ramp(template[:end-begin],.002,.003)
            out[begin:end] = piece
            schedule.append({"at_beat":cursor,"loop_beats":length,"sample":begin})
            cursor += length
    if round(cursor*beat) != total:
        raise ValueError("Roll timeline rounding")
    # The final eighth beat is withdrawn so the incoming attack has space.
    gap = round(.125*beat)
    out[-gap:] *= np.linspace(1,0,gap)[:,None]
    return out,schedule


def pulse_candidates(y, sr=11025):
    """Low-band transient periodicity. It can select metrical alternatives."""
    hop=128
    low = signal.sosfiltfilt(signal.butter(3,[40,160],fs=sr,btype="bandpass",output="sos"),y)
    count=len(low)//hop
    rms=np.sqrt(np.mean(low[:count*hop].reshape(count,hop)**2,axis=1))
    onset=np.maximum(0,np.diff(np.log(rms+.003),prepend=0))
    times=(np.arange(count)+.5)*hop/sr
    nfft=2**max(18,math.ceil(math.log2(count))+3)
    spec=np.abs(np.fft.rfft(onset-np.mean(onset),n=nfft))
    bpms=np.fft.rfftfreq(nfft,d=hop/sr)*60
    peaks,_=signal.find_peaks(spec)
    peaks=sorted([i for i in peaks if 60<bpms[i]<180],key=lambda i:spec[i],reverse=True)[:6]
    candidates=[]
    for i in peaks:
        center=float(bpms[i])
        fit=optimize.minimize_scalar(lambda b:-abs(np.sum(onset*np.exp(2j*np.pi*times*b/60))),bounds=(center-.12,center+.12),method="bounded")
        z=np.sum(onset*np.exp(2j*np.pi*times*fit.x/60))
        candidates.append({"bpm":float(fit.x),"offset_s":float((np.angle(z)%(2*np.pi))/(2*np.pi)*60/fit.x),
                           "periodicity":float(abs(z)/max(onset.sum(),1e-9))})
    return candidates


def analyze(path):
    raw=lab.run(["ffmpeg","-v","error","-i",path,"-vn","-ac","1","-ar","11025","-f","f32le","-"]).stdout
    y=np.frombuffer(raw,dtype="<f4").copy()
    if len(y)<11025*5 or len(y)>11025*900 or not np.isfinite(y).all() or np.max(np.abs(y))<1e-5:
        raise ValueError("Choose audible music between 5 seconds and 15 minutes")
    candidates=pulse_candidates(y)
    chunks=np.array_split(np.abs(y),600)
    waveform=[round(float(np.max(v)),5) for v in chunks]
    return {"duration_s":len(y)/11025,"sha256":lab.sha(path),"waveform":waveform,
            "bpm":round(candidates[0]["bpm"],3),"grid_offset_s":round(candidates[0]["offset_s"],4),
            "tempo_candidates":candidates,"annotation_status":"Estimated pulse; correct tempo and cue by listening. This is not a downbeat or hook detector.",
            "models":[],"engine":"deterministic_dj"}


def _prepare(s,target_bpm,folder):
    folder.mkdir()
    duration=s["beats"]*60/s["bpm"]
    raw=lab.run(["ffmpeg","-v","error","-ss",s["cue_s"],"-i",s["path"],"-t",f"{duration:.9f}","-vn","-ar",SR,"-ac",2,"-f","f32le","-"]).stdout
    x=np.frombuffer(raw,dtype="<f4").reshape(-1,2).copy()
    expected=round(duration*SR)
    if abs(len(x)-expected)>2:
        raise ValueError("Decoded source passage is unexpectedly short")
    input_path=folder/"input.wav"
    lab.write(input_path,x)
    output=folder/"prepared.wav"
    command=["rubberband","-3","--centre-focus","-F","-q","-D",s["beats"]*60/target_bpm,input_path,output]
    if abs(target_bpm-s["bpm"])<.001:
        lab.write(output,x)
        command=None
    else:
        result=lab.run(command)
        (folder/"transform.log").write_bytes(result.stderr)
    prepared=lab.decode(output)
    target_n=round(s["beats"]*60/target_bpm*SR)
    difference=len(prepared)-target_n
    if abs(difference)>round(.02*SR):
        raise ValueError("Time-stretch output length failed tolerance")
    prepared=np.pad(prepared[:target_n],((0,max(0,-difference)),(0,0)))
    stats=lab.loudness(output)
    gain_db=min(-18-stats["input_i"],-2-stats["input_tp"])
    if not math.isfinite(gain_db):
        raise ValueError("Source selection is silent")
    prepared*=10**(gain_db/20)
    lab.dump(folder/"transform.json",{"command":list(map(str,command)) if command else None,"input_bpm":s["bpm"],"output_bpm":target_bpm,"pitch_semitones":0,"duration_adjustment_samples":difference,"input_loudness":stats,"gain_db":gain_db})
    return edge_ramp(prepared)


def render(p,out):
    started=time.monotonic()
    validate_plan(p)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    lab.dump(out/"plan.json",p)
    changing=p["preset"] in ("echo_reset","reel_switch")
    bpm_a=p["a"]["bpm"] if changing else p["target_bpm"]
    bpm_b=p["b"]["bpm"] if changing else p["target_bpm"]
    a=_prepare(p["a"],bpm_a,out/"deck_a")
    b=_prepare(p["b"],bpm_b,out/"deck_b")
    beat_a,beat_b=60/bpm_a,60/bpm_b
    reveal=len(a)
    overlap=round((16 if p["preset"]=="tease_blend" else 8)*beat_a*SR) if p["preset"] in ("bass_swap","tease_blend") else 0
    b_start=reveal-overlap
    total=b_start+len(b)
    buses={k:np.zeros((total,2),dtype=np.float32) for k in ("a","b","fx")}
    control=np.zeros((total,2),dtype=np.float32)
    add_bus(control,a,0)
    add_bus(control,b,b_start)
    events=[]
    def event(at,label):events.append({"time_s":round(at/SR,4),"label":label})
    event(0,"Outgoing passage")
    if p["preset"]=="bass_swap":
        lo_a,hi_a=lab.split_bands(a)
        lo_b,hi_b=lab.split_bands(b)
        t=np.linspace(0,1,overlap)
        gain_a=np.ones(len(a));gain_a[-overlap:]=np.cos(t*np.pi/2)
        gain_b=np.ones(len(b));gain_b[:overlap]=np.sin(t*np.pi/2)
        low_a=np.ones(len(a));low_b=np.ones(len(b));switch=overlap//2
        width=round(.08*SR)
        low_a[-overlap+switch-width:]=0
        low_a[-overlap+switch-width:-overlap+switch]=np.linspace(1,0,width)
        low_b[:switch]=0;low_b[switch:switch+width]=np.linspace(0,1,width)
        add_bus(buses["a"],(lo_a*low_a[:,None]+hi_a)*gain_a[:,None],0)
        add_bus(buses["b"],(lo_b*low_b[:,None]+hi_b)*gain_b[:,None],b_start)
        event(b_start,"Incoming texture enters")
        event(b_start+switch,"Bass handover")
    elif p["preset"] in ("loop_drop", "tease_blend"):
        build=round(8*beat_a*SR);loop_start=reveal-build
        source_loop=a[loop_start:loop_start+round(4*beat_a*SR)]
        rolled,schedule=roll(source_loop,beat_a)
        low,high=lab.split_bands(rolled)
        rolled=high+low*np.linspace(1,.04,len(rolled))[:,None]
        a[loop_start:]=rolled
        gap=round(.125*beat_a*SR)
        a[-gap:]=0
        add_bus(buses["a"],a,0);add_bus(buses["b"],b,b_start)
        if p["preset"] == "tease_blend":
            # The selected B cue starts the overlap; its beat 17 is the release.
            incoming, _, _, repeats = tease_blend(b, beat_a)
            phase=np.clip((np.arange(len(a))-b_start)/overlap,0,1)
            a_gain=np.cos(phase*np.pi/2)
            buses["a"][:len(a)]=a*a_gain[:,None]
            buses["b"][:]=0
            add_bus(buses["b"],incoming,b_start)
            lab.dump(out/"incoming_repeat_schedule.json",repeats)
            lab.dump(out/"volume_automation.json",{"incoming":"sin(pi/2 * overlap_progress)^1.25", "outgoing":"cos(pi/2 * overlap_progress)", "overlap_beats":16})
            event(b_start,"Incoming overlap begins; gradual volume handover")
            event(b_start+round(8*beat_a*SR),"Incoming two-beat tease begins")
            event(b_start+round(12*beat_a*SR),"Incoming one-beat repeats")
            event(b_start+round(14*beat_a*SR),"Incoming half-beat repeats")
            event(reveal,"Tease releases; incoming groove at full volume")
        lab.dump(out/"loop_events.json",schedule)
        event(loop_start,"Four-beat loop begins")
        for beat,label in ((4,"One-beat repeats"),(6,"Half-beat repeats"),(7,"Quarter-beat repeats")):
            event(loop_start+round(beat*beat_a*SR),label)
        event(reveal-gap,"Brief withdrawal")
    else:
        capture=round(beat_a*SR)
        tail=beat_echo(edge_ramp(a[-capture:],.006,.01),beat_a)
        # Send only the final beat into the echo; the dry hook remains intact.
        echo_start=reveal-capture
        available=min(len(tail),total-echo_start)
        add_bus(buses["fx"],tail[:available]*.9,echo_start)
        a[-round(.04*SR):]*=np.linspace(1,0,round(.04*SR))[:,None]
        if p["preset"]=="reel_switch":
            breath=round(.25*beat_a*SR)
            a[-breath:]*=np.linspace(1,0,breath)[:,None]
            event(reveal-breath,"Quarter-beat breath")
        add_bus(buses["a"],a,0);add_bus(buses["b"],b,b_start)
        event(echo_start,"Dotted-eighth echo send")
    event(b_start,"Incoming track takes focus" if overlap==0 else "Incoming passage starts")
    event(reveal,"Outgoing track ends")
    master=sum(buses.values())
    peak=max(float(np.max(np.abs(master))),float(np.max(np.abs(control))))
    common_gain=min(1,.8/max(peak,1e-9))
    master=edge_ramp(master*common_gain,.012,.8)
    control=edge_ramp(control*common_gain,.012,.8)
    lab.write(out/"master.wav",master)
    lab.write(out/"control.wav",control)
    # Keep actual buses available for inspection; never label them instrument stems.
    for name,bus in buses.items():lab.write(out/f"bus_{name}.wav",bus*common_gain)
    measured={name:lab.loudness(out/f"{name}.wav") for name in ("master","control")}
    target=min(-16,*[v["input_i"]-1.8-v["input_tp"] for v in measured.values()])
    levels={}
    for name in ("master","control"):
        levels[name]=lab.listening_copy(out/f"{name}.wav",out/f"{name}_listening.wav",target)
        lab.run(["ffmpeg","-v","error","-n","-i",out/f"{name}_listening.wav","-map_metadata","-1","-c:a","libmp3lame","-b:a","256k",out/f"{name}.mp3"])
        lab.run(["ffmpeg","-v","error","-xerror","-i",out/f"{name}.mp3","-f","null","-"])
        levels[name]["mp3"]=lab.loudness(out/f"{name}.mp3")
    # Validate decoded lossy exports, not just the pre-encode master.
    checks={name:lab.waveform_checks(lab.decode(out/f"{name}.mp3"),total) for name in ("master","control")}
    for name,c in checks.items():
        if c["failures"]:raise ValueError(f"{name} export failed: {c['failures']}")
        if levels[name]["mp3"]["input_tp"]> -1.0:raise ValueError("MP3 true peak exceeds -1 dBTP")
    retention={}
    # Source-sample identity checks cover only declared untouched statement regions.
    for role,ref,start,stop in (("a",lab.decode(out/"deck_a/prepared.wav"),0,max(0,b_start if p["preset"]=="tease_blend" else reveal-round(9*beat_a*SR))),):
        # Gain invariance handles the preparation gain and final headroom adjustment.
        if stop>SR:retention[role]=lab.retention(ref[round(.1*SR):stop],master[round(.1*SR):stop])
    peak_bins=[round(float(np.max(np.abs(v))),5) for v in np.array_split(master,600)]
    result={"schema":"raag-dj-render/1","engine":"deterministic_dj","preset":p["preset"],
            "title":p.get("title",PRESETS[p["preset"]]["name"]),"duration_s":total/SR,"reveal_s":(reveal if p["preset"]=="tease_blend" else b_start)/SR,"overlap_start_s":b_start/SR,
            "target_bpm":p["target_bpm"],"tempo_a":bpm_a,"tempo_b":bpm_b,"events":events,"waveform":peak_bins,
            "checks":checks,"levels":levels,"statement_sample_retention":retention,"master_gain":common_gain,
            "wall_s":round(time.monotonic()-started,2),"sharing":p.get("sharing","private_user_supplied"),
            "models":[],"seed":None,"checkpoint":None,"prompt":None,"lyrics":"Unchanged source recordings",
            "musical_review":"Awaiting listening; waveform checks do not certify a good transition",
            "source_hashes":{"a":p["a"]["sha256"],"b":p["b"]["sha256"]},
            "files":{name:lab.sha(out/name) for name in ("master.wav","control.wav","master.mp3","control.mp3","plan.json")}}
    lab.dump(out/"result.json",result)
    return result
