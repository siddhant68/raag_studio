import subprocess,pathlib,json,hashlib,numpy as np
from scipy.signal import correlate,correlation_lags,resample_poly
root=pathlib.Path(__file__).resolve().parents[2]
all_data={};metrics=[]
for p in sorted((root/'audio').glob('E*.mp3')):
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(p),'-f','f32le','-ac','1','-ar','44100','pipe:1'])
 a=np.frombuffer(raw,dtype='<f4');all_data[p.name]=a
 rms=float(np.sqrt(np.mean(a*a)));peak=float(np.max(np.abs(a)))
 metrics.append({'file':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'decoded_mono_sample_rate':44100,'decoded_samples':len(a),'decoded_duration_s':len(a)/44100,'mono_peak_linear':peak,'mono_peak_dbfs':20*np.log10(max(peak,1e-12)),'mono_rms_dbfs':20*np.log10(max(rms,1e-12)),'limits':'Downmixed decoded peaks/RMS only; not stereo true peak, perceptual quality, singing or lyric fidelity.'})
(root/'research/audio_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
if 'E01-original.mp3' in all_data and 'E05-chorus-edit.mp3' in all_data:
 a=all_data['E01-original.mp3'];b=all_data['E05-chorus-edit.mp3'];rows=[]
 for start,end,label in [(5,25,'verse_interior'),(32,52,'selected_chorus_interior'),(65,85,'final_chorus_interior')]:
  x=a[int(start*44100):int(end*44100)].astype('float64');y=b[int(start*44100):int(end*44100)].astype('float64');xd=resample_poly(x,1,4);yd=resample_poly(y,1,4)
  c=correlate(yd,xd,mode='full',method='fft');lags=correlation_lags(len(yd),len(xd));m=np.abs(lags)<=round(0.1*11025);lag=int(lags[m][np.argmax(c[m])]);rows.append({'span_s':[start,end],'label':label,'best_lag_ms_within_100ms':1000*lag/11025,'zero_offset_correlation':float(np.corrcoef(x,y)[0,1]),'equal_samples_fraction':float(np.mean(x==y)),'normalized_residual_rms':float(np.sqrt(np.mean((x-y)**2)/np.mean(x*x)))})
 (root/'experiments/E05/alignment_check.json').write_text(json.dumps({'method':'MP3 decoded to mono 44.1 kHz; lag estimated on polyphase 11.025kHz resample via FFT correlation, bounded ±100ms; interior spans avoid edit boundary','comparisons':rows,'limitations':['No sample identity established.','High correlation supports strong similarity, not every part unchanged.','MP3 encoding differences may produce residuals outside edit.','No seam or artistic quality audition performed.']},indent=2)+'\n')
print(json.dumps(metrics,indent=2));print(json.dumps(rows,indent=2))
