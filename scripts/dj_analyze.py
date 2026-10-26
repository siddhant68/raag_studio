#!/usr/bin/env python3
"""Import user-selected audio and make editable rhythm/section candidates. CPU only."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("files", nargs="+", type=Path)
    args = p.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    os.environ["NUMBA_CACHE_DIR"] = str(args.out / "numba_cache")
    import librosa
    import numpy as np
    from app.experiments import remix_lab as lab,dj_lab as dj
    result = {"schema": "raag-dj-sources/1", "sources": [], "models": [],
              "annotation_status": "Measured rhythm candidates. Downbeats, phrases and hooks need listening confirmation."}
    for idx, src in enumerate(args.files):
        started = time.monotonic()
        sid = ["daft", "fisher", "kala", "nashe"][idx] if len(args.files) == 4 else f"source_{idx+1}"
        dest = args.out / f"{sid}{src.suffix.lower()}"
        shutil.copyfile(src, dest)
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(src), "-vn", "-ac", "1", "-ar", "11025", "-f", "f32le", "-"], capture_output=True, check=True).stdout
        y = np.frombuffer(raw, dtype="<f4").copy()
        sr, hop = 11025, 128
        onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop)
        tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=hop, trim=True)
        beats = librosa.frames_to_time(beat_frames, sr=sr, hop_length=hop)
        # Fit only an actual candidate beat tracker, keeping residuals and raw points.
        mask = np.ones(len(beats), dtype=bool)
        for _ in range(4):
            slope, offset = np.polyfit(np.arange(len(beats))[mask], beats[mask], 1)
            residual = beats - (offset + slope*np.arange(len(beats)))
            mask = np.abs(residual) < .07
        bpm = 60/slope
        pulse_candidates=dj.pulse_candidates(y,sr)
        grid=pulse_candidates[0]
        rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=hop)[0]
        chroma = librosa.feature.chroma_stft(y=y, sr=sr, n_fft=2048, hop_length=512)
        chroma_mean = np.mean(chroma, axis=1)
        major = np.array([6.35,2.23,3.48,2.33,4.38,4.09,2.52,5.19,2.39,3.66,2.29,2.88])
        minor = np.array([6.33,2.68,3.52,5.38,2.60,3.53,2.54,4.75,3.98,2.69,3.34,3.17])
        keys = sorted([(float(np.corrcoef(chroma_mean,np.roll(profile,k))[0,1]),k,mode) for mode,profile in [("major",major),("minor",minor)] for k in range(12)], reverse=True)
        note_names = ["C","C#","D","Eb","E","F","F#","G","Ab","A","Bb","B"]
        blocks = []
        for b in range(0,len(beats)-8,8):
            start,end = beats[b],beats[b+8]
            a,z = int(start*sr/hop),int(end*sr/hop)
            c,d = int(start*sr/512),int(end*sr/512)
            blocks.append({"beat_index":b,"start_s":round(float(start),3),"end_s":round(float(end),3),
                "rms_db":round(float(20*np.log10(max(np.mean(rms[a:z]),1e-9))),2),
                "onset_mean":round(float(np.mean(onset[a:z])),3),"chroma":np.mean(chroma[:,c:d],axis=1).round(3).tolist()})
        record = {"id":sid,"name":src.stem,"path":str(dest.resolve()),"original_path":str(src.resolve()),
                  "sha256":lab.sha(src),"duration_s":len(y)/sr,"kind":"stereo_mix",
                  "sharing":"private_user_supplied", "bpm_estimate":float(np.atleast_1d(tempo)[0]),
                  "grid_bpm":grid["bpm"],"grid_offset_s":grid["offset_s"],
                  "grid_candidates":grid,"tempo_candidates":pulse_candidates,
                  "discarded_tracker_index_fit":{"bpm":float(bpm),"offset_s":float(offset),"reason":"Missing beats through breakdowns can invalidate a fit by beat index"},
                  "discarded_tracker_fit_residual_ms_p95":float(np.percentile(np.abs(residual[mask]),95)*1000),
                  "discarded_tracker_fit_fraction":float(np.mean(mask)),"raw_beats_s":beats.tolist(),
                  "key_candidates":[{"key":note_names[k]+" "+mode,"correlation":score} for score,k,mode in keys[:3]],
                  "key_status":"chroma template estimates, not harmonic compatibility approval",
                  "blocks_8beats":blocks,"analysis_wall_s":round(time.monotonic()-started,2)}
        result["sources"].append(record)
        (args.out/"sources.json").write_text(json.dumps(result,indent=2)+"\n")
        print(json.dumps({k:v for k,v in record.items() if k not in ("blocks_8beats","raw_beats_s")}),flush=True)


if __name__ == "__main__":
    main()
