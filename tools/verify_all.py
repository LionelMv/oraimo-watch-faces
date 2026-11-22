import sys, struct
sys.path.insert(0,'.')
from att import att_packets
def arc(d,init=0):
    c=init
    for b in d:
        c^=b
        for _ in range(8): c=(c>>1)^0xA001 if c&1 else c>>1
    return c
pk=list(att_packets(sys.argv[1]))
bulk=[a[3:] for t,h,s,a in pk if a[0] in (0x52,0x12) and len(a)>3 and struct.unpack_from('<H',a,1)[0]==9]
j=0; ok=n=0
while j<len(bulk):
    p=bulk[j]
    if p[0] in (1,4): j+=1; continue
    hdr=p[:12]; ln=struct.unpack_from('<H',hdr,10)[0]; data=bytearray(p[12:]); j+=1
    while len(data)<ln: data+=bulk[j]; j+=1
    n+=1; ok+= arc(bytes(data[:ln]))==struct.unpack_from('<H',hdr,8)[0]
print(f"bulk blocks: {ok}/{n} CRC-16/ARC ok")
# command channel L1 header: ab flags len(be16) crc(be16) seq(be16) + payload
ok=n=0; tried={}
for t,h,s,a in pk:
    if a[0] not in (0x12,0x52,0x1b) or len(a)<4: continue
    ah=struct.unpack_from('<H',a,1)[0]; v=a[3:]
    if ah not in (6,3) or len(v)<8 or v[0]!=0xab: continue
    ln=struct.unpack_from('>H',v,2)[0]
    if ln==0 or len(v)<8+ln: continue
    pl=v[8:8+ln]; c=struct.unpack_from('>H',v,4)[0]; n+=1
    ok+= arc(pl)==c
print(f"command frames: {ok}/{n} header CRC-16/ARC (big-endian) ok")
