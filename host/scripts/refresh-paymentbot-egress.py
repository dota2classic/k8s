import ipaddress,json,os,pathlib,socket,subprocess,time
os.umask(0o077)
root=pathlib.Path('/root/d2c-paymentbot');root.mkdir(mode=0o700,exist_ok=True)
file=root/'telegram-addresses.json';seen=json.loads(file.read_text()) if file.exists() else {};now=time.time()
for item in socket.getaddrinfo('api.telegram.org',443,family=socket.AF_INET,type=socket.SOCK_STREAM):
    address=item[4][0]
    assert ipaddress.ip_address(address).is_global,'Non-public Telegram DNS answer'
    seen[address]=now
seen={address:stamp for address,stamp in seen.items() if now-stamp<3600}
assert seen,'No Telegram addresses; previous policy retained'
policy={'apiVersion':'networking.k8s.io/v1','kind':'NetworkPolicy','metadata':{'name':'paymentbot-telegram-egress','namespace':'default'},'spec':{'podSelector':{'matchLabels':{'app':'paymentbot'}},'policyTypes':['Egress'],'egress':[{'to':[{'ipBlock':{'cidr':address+'/32'}} for address in sorted(seen)],'ports':[{'protocol':'TCP','port':443}]}]}}
subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(policy),text=True,check=True)
file.write_text(json.dumps(seen))
print('Payment bot Telegram HTTPS egress refreshed')
