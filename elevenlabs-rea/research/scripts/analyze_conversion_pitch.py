import pathlib,subprocess,json,time
import numpy as np
import librosa
from scipy.signal import correlate,correlation_lags
root=pathlib.Path(__file__).resolve().parents[2]; sr=22050;hop=256;t=time.time();datas=[]
for fn in ['E18-source-30-45.wav','E18-roger-converted.mp3']:
 p=root/'audio'/fn
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-ac','1','-ar',str(sr),'pipe:1'])
 y=np.frombuffer(raw,dtype='<f4').astype('float64')
 f0,voiced,prob=librosa.pyin(y,fmin=65,fmax=1000,sr=sr,frame_length=2048,hop_length=hop)
 rms=librosa.feature.rms(y=y,frame_length=2048,hop_length=hop)[0]
 onset=librosa.onset.onset_strength(y=y,sr=sr,hop_length=hop)
 datas.append((fn,y,f0,voiced,prob,rms,onset))
a,b=datas;n=min(len(a[2]),len(b[2]));mask=np.isfinite(a[2][:n])&np.isfinite(b[2][:n]);x=a[2][:n][mask];z=b[2][:n][mask]
cents=1200*np.log2(z/x);corr=float(np.corrcoef(np.log2(x),np.log2(z))[0,1]) if len(x)>2 else None
rows=[]
for fn,y,f0,voiced,prob,rms,onset in datas:
 rows.append({'file':fn,'decoded_duration_s':len(y)/sr,'frame_count':len(f0),'pyin_voiced_fraction':float(np.mean(np.isfinite(f0))),'pyin_median_estimated_hz':float(np.nanmedian(f0)),'median_voiced_probability':float(np.median(prob[np.isfinite(f0)]))})
def envelope_corr(i):
 x=a[i];z=b[i];m=min(len(x),len(z));x=x[:m];z=z[:m];cc=correlate(z-z.mean(),x-x.mean());lags=correlation_lags(len(z),len(x));lim=np.abs(lags)<=round(.3*sr/hop);lag=int(lags[lim][np.argmax(cc[lim])]);return {'zero_lag_correlation':float(np.corrcoef(x,z)[0,1]),'best_lag_ms_within_300ms':1000*lag*hop/sr}
r={'method':'librosa pYIN65–1000Hz, mono22.05kHz,2048frame/256hop; source is full mix; no vocal separation','librosa_version':librosa.__version__,'elapsed_s':time.time()-t,'files':rows,'paired_estimates':{'paired_finite_frame_count':int(mask.sum()),'all_compared_frames':n,'log_f0_correlation_at_zero_lag':corr,'median_signed_cents_difference':float(np.median(cents)),'median_absolute_cents_difference':float(np.median(np.abs(cents))),'within_100_cents_fraction':float(np.mean(np.abs(cents)<=100))},'rms_envelope':envelope_corr(5),'onset_envelope':envelope_corr(6),'interpretation':'Pitch comparison rejected as unreliable: medians near65Hz lower bound and median voiced probabilities about0.01. Do not use correlation/cents as evidence of preserved or changed melody. Gross duration measured only.','limitations':['Source is a mixed generated song, so dominant instrumental pitches may drive pYIN.','No reliable source-vocal F0 reference; octave errors and voiced-mask mismatches possible.','Frame estimates are not musical note alignment or singer identity evidence.','No singing, diction or perceptual quality success is established.']}
(root/'experiments/E18/pitch_timing_analysis.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
