import socket,ipaddress,json,pathlib,time,subprocess
state=pathlib.Path('/root/steam-egress-addresses.json')
now=time.time();seen=json.loads(state.read_text()) if state.exists() else {}
for host in ['api.steampowered.com','steamcommunity.com']:
    for result in socket.getaddrinfo(host,443,family=socket.AF_INET,type=socket.SOCK_STREAM):
        ip=result[4][0]
        if not ipaddress.ip_address(ip).is_global:raise RuntimeError('Non-public Steam DNS answer')
        seen[ip]=now
seen={ip:timestamp for ip,timestamp in seen.items() if now-timestamp<3600}
state.write_text(json.dumps(seen))
policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'api-external-integrations','namespace':'default'},'spec':{'podSelector':{'matchLabels':{'app':'api'}},'policyTypes':['Egress'],'egress':[{'to':[{'ipBlock':{'cidr':ip+'/32'}} for ip in sorted(set(seen)|{'141.105.71.200'})],'ports':[{'protocol':'TCP','port':443}]},{'to':[{'ipBlock':{'cidr':'141.105.71.200/32'}}],'ports':[{'protocol':'TCP','port':9090}]}]}}
subprocess.run(['k3s','kubectl','apply','-f','-'],input=json.dumps(policy),text=True,check=True)
print('Steam egress addresses:',len(seen))
