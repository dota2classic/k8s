"""Temporary read-only bridge for already-running sidecars with the grouping bug."""
import base64,json,re,socket,struct,subprocess,time
passwords={}
def read(s,n):
    b=b''
    while len(b)<n:
        x=s.recv(n-len(b))
        if not x:raise OSError('RCON closed')
        b+=x
    return b
def packet(s):
    n=struct.unpack('<i',read(s,4))[0]
    if not 10<=n<=65536:raise OSError('Invalid RCON frame')
    b=read(s,n);return struct.unpack('<ii',b[:8]),b[8:-2].decode(errors='replace')
def send(s,i,t,value):
    b=struct.pack('<ii',i,t)+value+b'\0\0';s.sendall(struct.pack('<i',len(b))+b)
def collect(pod,match,labels,lines):
    # New fixed sidecars push directly; this bridge is only for the affected image.
    sidecar=next(c for c in pod['spec']['containers'] if c['name']=='sidecar')
    if 'e1e04c9d8bc8b45' not in sidecar['image']:return
    game=next(c for c in pod['spec']['containers'] if c['name']=='gameserver')
    port=int(next(e['value'] for e in game['env'] if e['name']=='GAME_PORT'))
    if match not in passwords:
        sec=json.loads(subprocess.check_output(['kubectl','get','secret','gameserver-secrets-'+match,'-n','gameservers','-o','json'],timeout=4))
        passwords[match]=base64.b64decode(sec['data']['RCON_PASSWORD'])
    with socket.create_connection((pod['status']['podIP'],port),timeout=1) as s:
        send(s,1,3,passwords[match])
        for _ in range(3):
            (i,t),_=packet(s)
            if t==2:
                if i!=1:raise OSError('RCON auth failed')
                break
        results={}
        for i,cmd in enumerate(['stats','d2c_frame_stats','status'],2):
            send(s,i,2,cmd.encode());(_,t),text=packet(s);results[cmd]=text
    for row in results['stats'].splitlines():
        fields=row.split()
        if len(fields)>=7:
            try:values=[float(x) for x in fields[:7]]
            except ValueError:continue
            lines.extend(['srcds_metrics_cpu'+labels+' '+str(values[0]),'srcds_metrics_fps'+labels+' '+str(values[5])]);break
    frame=re.search(r'D2C_FRAME frames=(\d+) mean_ms=([\d.]+) p95_ms=([\d.]+) p99_ms=([\d.]+) max_ms=([\d.]+) over_ratio=([\d.]+)',results['d2c_frame_stats'])
    if frame:
        for i,name,scale in [(1,'srcds_frame_window_frames',1),(2,'srcds_frame_interval_mean_seconds',1000),(3,'srcds_frame_interval_p95_seconds',1000),(4,'srcds_frame_interval_p99_seconds',1000),(5,'srcds_frame_interval_max_seconds',1000),(6,'srcds_frame_over_budget_ratio',1)]:
            lines.append(name+labels+' '+str(float(frame[i])/scale))
    for row in results['status'].splitlines():
        if not row.startswith('#') or '"' not in row:continue
        fields=row.rsplit('"',1)[-1].split()
        player=re.match(r'#\s*(\d+)',row)
        if player and len(fields)>=7 and fields[0].startswith('[U:'):
            try:ping,loss=float(fields[2]),float(fields[3])
            except ValueError:continue
            playerlabels=labels[:-1]+',player_slot="'+player[1]+'"}'
            lines.extend(['srcds_metrics_ping'+playerlabels+' '+str(ping),'srcds_metrics_loss'+playerlabels+' '+str(loss)])
    lines.append('d2c_srcds_rcon_collection_timestamp_seconds'+labels+' '+str(time.time()))
