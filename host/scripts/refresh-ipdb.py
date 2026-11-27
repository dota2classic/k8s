import gzip,os,pathlib,urllib.request
target=pathlib.Path('/var/lib/d2c/ipdb')
x4b='https://raw.githubusercontent.com/X4BNet/lists_vpn/main/'
extra_hosting_asns=['AS210644 # AEZA','AS9123 # TimeWeb','AS197695 # REG.RU','AS198610 # Beget','AS44812 # IP Server','AS50340 # Selectel MSK','AS13335 # Cloudflare WARP']
def fetch(url):
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'d2c-ipdb-refresh'}),timeout=120) as r:return r.read()
def lines(data):return [l for l in data.decode().splitlines() if l.strip()]
asn_table=fetch('https://iptoasn.com/data/ip2asn-v4.tsv.gz')
files={
 'ip2asn-v4.tsv.gz':(asn_table,len(gzip.decompress(asn_table).splitlines()),300000),
 'datacenter-ipv4.txt':(datacenter:=fetch(x4b+'output/datacenter/ipv4.txt'),len(lines(datacenter)),10000),
 'vpn-ipv4.txt':(vpn:=fetch(x4b+'output/vpn/ipv4.txt'),len(lines(vpn)),1000),
 'hosting-asn.txt':(hosting:=fetch(x4b+'input/datacenter/ASN.txt')+('\n'+'\n'.join(extra_hosting_asns)+'\n').encode(),len(lines(hosting)),500),
}
for name,(data,count,minimum) in files.items():
    if count<minimum:raise RuntimeError(f'{name}: {count} records, expected at least {minimum}')
target.mkdir(parents=True,exist_ok=True)
for name,(data,count,minimum) in files.items():
    tmp=target/(name+'.tmp');tmp.write_bytes(data);tmp.chmod(0o644);os.replace(tmp,target/name)
    print('ipdb',name,count)
