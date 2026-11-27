"""Export read-only cgroup v2 counters for each SRCDS container to node-exporter."""
import json,os,pathlib,subprocess,time
import game_rcon_metrics
root=pathlib.Path('/var/lib/node_exporter/textfile_collector')
root.mkdir(parents=True,exist_ok=True,mode=0o755)
def esc(v):return str(v).replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
def collect():
    pods=json.loads(subprocess.check_output(['kubectl','get','pods','-n','gameservers','-o','json'],timeout=8))['items']
    lines=['# SRCDS cgroup counters; no player identities or secrets.']
    for p in pods:
        match=p['metadata'].get('labels',{}).get('ru.dotaclassic/matchId')
        if not match:continue
        for s in p['status'].get('containerStatuses',[]):
            if s['name']!='gameserver' or not s.get('state',{}).get('running'):continue
            try:
                cid=s['containerID'].split('://')[-1]
                pid=json.loads(subprocess.check_output(['crictl','inspect',cid],timeout=5))['info']['pid']
                group=next(l.split('::',1)[1] for l in pathlib.Path(f'/proc/{pid}/cgroup').read_text().splitlines() if l.startswith('0::'))
                cg=pathlib.Path('/sys/fs/cgroup')/group.lstrip('/')
                values={k:int(v) for k,v in (l.split() for l in (cg/'cpu.stat').read_text().splitlines())}
                labels='{match_id="'+esc(match)+'",pod_name="'+esc(p['metadata']['name'])+'"}'
                for key,suffix,scale in [('usage_usec','cpu_usage_seconds_total',1e6),('user_usec','cpu_user_seconds_total',1e6),('system_usec','cpu_system_seconds_total',1e6),('throttled_usec','cpu_throttled_seconds_total',1e6),('nr_throttled','cpu_throttled_periods_total',1),('nr_periods','cpu_periods_total',1)]:
                    lines.append('d2c_srcds_'+suffix+labels+' '+str(values.get(key,0)/scale))
                for row in (cg/'cpu.pressure').read_text().splitlines():
                    fields=row.split();total=next(int(x.split('=')[1]) for x in fields if x.startswith('total='))
                    lines.append('d2c_srcds_cpu_pressure_'+fields[0]+'_seconds_total'+labels+' '+str(total/1e6))
                lines.append('d2c_srcds_memory_bytes'+labels+' '+(cg/'memory.current').read_text().strip())
                try:game_rcon_metrics.collect(p,match,labels,lines)
                except (OSError,KeyError,subprocess.SubprocessError,StopIteration):pass
            except (OSError,KeyError,subprocess.SubprocessError,StopIteration):continue
    lines.append('d2c_srcds_cgroup_collection_timestamp_seconds '+str(time.time()))
    tmp=root/'gameserver.prom.tmp';tmp.write_text('\n'.join(lines)+'\n');tmp.chmod(0o644);tmp.replace(root/'gameserver.prom')
if __name__=='__main__':
    while True:
        started=time.monotonic()
        try:collect()
        except Exception as e:print('Cgroup collection failed: '+type(e).__name__,flush=True)
        time.sleep(max(1,5-(time.monotonic()-started)))
