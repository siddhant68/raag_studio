"""Verify this handoff baseline without loading music models or generating audio."""
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
manifest_path = root/'context_pack/inventory/FILE_MANIFEST.json'
manifest = json.loads(manifest_path.read_text())
errors = []
for item in manifest['files']:
    path = root/item['path']
    if not path.is_file():
        errors.append({'path':item['path'],'error':'missing'})
    elif hashlib.sha256(path.read_bytes()).hexdigest() != item['sha256']:
        errors.append({'path':item['path'],'error':'changed since handoff baseline'})
catalogue = json.loads((root/'context_pack/examples/AUDIO_CATALOGUE.json').read_text())
for item in catalogue:
    path = root/'context_pack'/item['file']
    if not path.exists():
        errors.append({'path':item['file'],'error':'audio missing'})
skills = list((root/'context_pack/third_party/vendor').rglob('SKILL.md'))
if len(skills) != 159:
    errors.append({'vendor_skills':len(skills),'expected':159})
status = {'baseline_files_checked':len(manifest['files']),'audio_examples':len(catalogue),
          'vendor_skill_files':len(skills),'errors':errors,
          'note':'A modified baseline can reflect intentional implementation work; review differences, never restore blindly.'}
print(json.dumps(status,indent=2))
raise SystemExit(1 if errors else 0)
