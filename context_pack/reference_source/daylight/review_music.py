"""Local, fallible acoustic descriptions plus technical checks, not taste scores."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from earshot import api

root = Path(__file__).resolve().parent
report = {'takes': {}, 'limits': 'Model tags are fallible and do not establish beauty, exact notes or listener preference.'}
for result_path in sorted((root / 'takes').glob('*/result.json')):
    result = json.loads(result_path.read_text())
    if not result.get('success'):
        continue
    path = result['audios'][0]['path']
    y, sr = sf.read(path, dtype='float32', always_2d=True)
    checks = {'finite': bool(np.isfinite(y).all()), 'duration': len(y)/sr,
              'peak_dbfs': float(20*np.log10(abs(y).max()+1e-12)),
              'clipped_samples': int((abs(y)>=1).sum()), 'channels': y.shape[1]}
    assert checks['finite'] and checks['clipped_samples'] == 0
    item = {'path': path, 'checks': checks, 'descriptions': {}}
    for label, start, end in [('opening', 5, 15), ('middle', 42, 52), ('late', 98, 108)]:
        print(f'{result_path.parent.name}: {label}', flush=True)
        description = api.describe(path, start=start, end=end, top=5)
        item['descriptions'][label] = description
        print(description.get('summary'), flush=True)
    report['takes'][result_path.parent.name] = item
    (root / 'review.json').write_text(json.dumps(report, indent=2, default=str))
print('Review complete', flush=True)
