import pathlib,subprocess,json
source=pathlib.Path('/root/warm-user-profiles.js').read_bytes()
result=subprocess.run(['kubectl','exec','-i','deployment/user','--','node','-','--apply','--ensure'],input=source,capture_output=True,timeout=240)
if result.returncode:raise SystemExit('User profile cache warmup failed; inspect the service pod and database')
report=json.loads(result.stdout)
root=pathlib.Path('/root/d2c-site');root.mkdir(mode=0o700,exist_ok=True)
(root/'profile-cache.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
