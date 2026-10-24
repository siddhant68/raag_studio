"""Read-only audio inspection; write research indices, never mutate original audio."""
import pathlib,subprocess,json,hashlib,csv,importlib.metadata
root=pathlib.Path(__file__).resolve().parents[2]
model=root.parent/'tools/whisper-small-mlx'
model_sha=hashlib.sha256((model/'weights.npz').read_bytes()).hexdigest()
rows=[];asrrows=[]
probe_dir=root/'research/audio_probes';probe_dir.mkdir(exist_ok=True)
for p in sorted((root/'audio').iterdir()):
 if p.suffix.lower() not in ['.mp3','.wav','.flac','.m4a']:continue
 eid=p.name.split('-')[0]
 probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
 (probe_dir/(p.stem+'.json')).write_text(json.dumps(probe,ensure_ascii=False,indent=2)+'\n')
 streams=[s for s in probe['streams'] if s.get('codec_type')=='audio'];s=streams[0];f=probe['format']
 row={'experiment_id':eid,'file':str(p.relative_to(root)),'role':('reference_crop' if 'reference-0-30' in p.name else 'source_crop' if '-source-' in p.name else 'converted_download' if 'roger-converted' in p.name else 'generated_original_download'),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size,'duration_s':f.get('duration'),'codec':s.get('codec_name'),'sample_rate':s.get('sample_rate'),'channels':s.get('channels'),'bit_rate':s.get('bit_rate',f.get('bit_rate'))}
 rows.append(row)
 for transcript in sorted((root/'experiments'/eid).glob('asr_hi_*.json')):
  j=json.loads(transcript.read_text());segs=j.get('segments',[])
  declared=j.get('analysis_metadata',{}).get('audio_file')
  if declared and pathlib.Path(declared).resolve()!=p.resolve():continue
  if not declared and row['role'] not in ('generated_original_download','converted_download'):continue
  asrrows.append({'experiment_id':eid,'audio_file':row['file'],'audio_sha256':row['sha256'],'transcript_file':str(transcript.relative_to(root)),'transcript_sha256':hashlib.sha256(transcript.read_bytes()).hexdigest(),'model_path':str(model),'model_weights_sha256':model_sha,'mlx_whisper_version':importlib.metadata.version('mlx-whisper'),'language':'hi','initial_prompt':'None; no lyric fixture supplied','previous_text_conditioning':False,'decode_mode':'default_temperature_fallback' if 'fallback' in transcript.name else 'temperature_0_word_timestamps','segment_count':len(segs),'high_compression_segment_count':sum(float(s.get('compression_ratio',0))>2.4 for s in segs),'low_logprob_segment_count':sum(float(s.get('avg_logprob',0))< -1 for s in segs),'listener_status':'pending_listening'})
for name,data in [('audio_asset_index',rows),('asr_index',asrrows)]:
 (root/'research'/f'{name}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 with (root/'research'/f'{name}.csv').open('w',newline='') as out:
  w=csv.DictWriter(out,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
print(json.dumps({'audio_assets':len(rows),'asr_records':len(asrrows),'model_weights_sha256':model_sha}))
