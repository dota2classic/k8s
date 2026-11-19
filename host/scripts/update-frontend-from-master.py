"""Deploy only a successfully built master image; no GitHub/Kubernetes remote credentials."""
import argparse, datetime, fcntl, hashlib, json, pathlib, re, subprocess, urllib.request

ROOT=pathlib.Path('/root/d2c-site')
REPO='dota2classic/frontend'
ROOT.mkdir(mode=0o700,exist_ok=True)
lock=(ROOT/'updater.lock').open('w')
try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
except BlockingIOError:raise SystemExit(0)
parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()

def request(url,headers=None):
    req=urllib.request.Request(url,headers={'User-Agent':'DotaLegacy-frontend-recovery','Accept':'application/vnd.github+json',**(headers or {})})
    with urllib.request.urlopen(req,timeout=30) as response:
        return response.read(), response.headers
def getjson(url,headers=None):return json.loads(request(url,headers)[0])
def kubectl(*argv,**kw):
    return subprocess.check_output(['kubectl','-n','default',*argv],stderr=subprocess.PIPE,timeout=240,**kw).decode()
def save(report):
    report['checkedAt']=datetime.datetime.now(datetime.timezone.utc).isoformat()
    tmp=ROOT/'update-report.tmp';tmp.write_text(json.dumps(report,indent=2));tmp.replace(ROOT/'update-report.json')
    print(json.dumps(report),flush=True)

def smoke(image):
    pods=json.loads(kubectl('get','pods','-l','app=frontend','-o','json'))['items']
    matching=[p for p in pods if not p['metadata'].get('deletionTimestamp') and
              p['spec']['containers'][0]['image']==image and
              any(c['type']=='Ready' and c['status']=='True' for c in p['status'].get('conditions',[]))]
    assert len(matching)==1, 'Expected one Ready frontend pod for the selected image'
    script="""(async()=>{let pages=[];for(const path of ['/','/download','/players','/matches']){
      const r=await fetch('http://127.0.0.1:3000'+path,{signal:AbortSignal.timeout(30000)});
      const html=await r.text();if(r.status!==200||html.length<500)throw new Error('Page check failed: '+path+' '+r.status);
      pages.push({path,status:r.status,bytes:html.length});}
      console.log(JSON.stringify({versions:Object.fromEntries(['next','react','react-dom'].map(n=>[n,require(n+'/package.json').version])),pages}));
      })().catch(e=>{console.error(e.message);process.exit(1)})"""
    return json.loads(kubectl('exec','-i',matching[0]['metadata']['name'],'--','node','-',input=script.encode()))

try:
    commit=getjson(f'https://api.github.com/repos/{REPO}/commits/master')
    sha=commit['sha'];assert re.fullmatch('[0-9a-f]{40}',sha)
    runs=getjson(f'https://api.github.com/repos/{REPO}/actions/workflows/ci.yml/runs?branch=master&event=push&head_sha={sha}&per_page=10')['workflow_runs']
    runs=[r for r in runs if r['head_sha']==sha and r['head_branch']=='master' and r['event']=='push']
    latest=max(runs,key=lambda r:r['id']) if runs else None
    if not latest or latest['status']!='completed' or latest['conclusion']!='success':
        save({'status':'waiting-for-master-build','masterSha':sha,'changed':False});raise SystemExit(0)
    # The Build workflow publishes this immutable commit tag only after its production build passes.
    token=getjson(f'https://auth.docker.io/token?service=registry.docker.io&scope=repository:{REPO}:pull')['token']
    tag='k8s-'+sha[:7]
    manifest,headers=request(f'https://registry-1.docker.io/v2/{REPO}/manifests/{tag}',
        {'Authorization':'Bearer '+token,'Accept':'application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json, application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'})
    digest=headers['Docker-Content-Digest'];assert re.fullmatch('sha256:[0-9a-f]{64}',digest)
    assert digest=='sha256:'+hashlib.sha256(manifest).hexdigest(), 'Registry manifest digest mismatch'
    image=REPO+'@'+digest
    deployment=json.loads(kubectl('get','deployment','frontend','-o','json'))
    containers=deployment['spec']['template']['spec']['containers']
    assert len(containers)==1 and containers[0]['name']=='frontend'
    previous=containers[0]['image']
    report={'masterSha':sha,'buildRun':latest['html_url'],'tag':tag,'image':image,'previousImage':previous,'changed':False}
    if not args.apply:
        save({**report,'status':'candidate-verified'});raise SystemExit(0)
    failed=ROOT/'failed-master-sha'
    if failed.exists() and failed.read_text().strip()==sha:
        save({**report,'status':'previously-failed-requires-review'});raise SystemExit(1)
    if previous==image:
        save({**report,'status':'already-current'});raise SystemExit(0)
    assert deployment['status'].get('observedGeneration',0)>=deployment['metadata']['generation'], 'Existing deployment change not observed'
    assert deployment['status'].get('updatedReplicas',0)==1 and deployment['status'].get('availableReplicas',0)==1, 'Existing frontend rollout is not healthy'
    (ROOT/'previous-image.txt').write_text(previous+'\n')
    kubectl('set','image','deployment/frontend','frontend='+image)
    try:
        kubectl('rollout','status','deployment/frontend','--timeout=180s')
        checks=smoke(image)
        kubectl('annotate','deployment','frontend','d2c.dotaclassic/master-sha='+sha,'--overwrite')
        save({**report,'status':'deployed','changed':True,'checks':checks})
    except Exception:
        failed.write_text(sha+'\n')
        kubectl('set','image','deployment/frontend','frontend='+previous)
        kubectl('rollout','status','deployment/frontend','--timeout=180s')
        save({**report,'status':'rolled-back','changed':True,'requiresReview':True})
        raise
except Exception as error:
    # No API headers, credentials, environment, or raw process output in journals.
    (ROOT/'update-error.json').write_text(json.dumps({'errorType':type(error).__name__,'message':str(error)},indent=2))
    print(json.dumps({'status':'error','errorType':type(error).__name__}),flush=True)
    raise SystemExit(1)
