import base64,ipaddress,json,os,pathlib,socket,subprocess,time
os.umask(0o077)
root=pathlib.Path('/root/telegram-egress');root.mkdir(mode=0o700,exist_ok=True)
secret=json.loads(subprocess.check_output(['kubectl','-n','default','get','secret','shared-secrets','-o','json']))
if not base64.b64decode(secret.get('data',{}).get('TELEGRAM_TOKEN','')).strip():
    print('Telegram key absent; no network change');raise SystemExit(0)
file=root/'addresses.json';seen=json.loads(file.read_text()) if file.exists() else {};now=time.time()
for item in socket.getaddrinfo('api.telegram.org',443,family=socket.AF_INET,type=socket.SOCK_STREAM):
    address=item[4][0]
    assert ipaddress.ip_address(address).is_global,'Non-public Telegram DNS answer'
    seen[address]=now
seen={address:stamp for address,stamp in seen.items() if now-stamp<3600}
assert seen,'No verified Telegram IPv4 addresses'
policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'api-telegram-egress','namespace':'default'},'spec':{'podSelector':{'matchLabels':{'app':'api'}},'policyTypes':['Egress'],'egress':[{'to':[{'ipBlock':{'cidr':address+'/32'}} for address in sorted(seen)],'ports':[{'protocol':'TCP','port':443}]}]}}
subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(policy),text=True,check=True)
policy['metadata']['name']='grafana-telegram-relay-egress'
policy['spec']['podSelector']['matchLabels']['app']='grafana-telegram-relay'
subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(policy),text=True,check=True)
file.write_text(json.dumps(seen))
print('Telegram egress refreshed; HTTPS addresses:',len(seen))
