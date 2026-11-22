import sys, struct
sys.path.insert(0,'.')
from att import att_packets
pk=list(att_packets(sys.argv[1])); t0=pk[0][0]
bulk=0; lastbulk=None
def hx(b,n=48): return b[:n].hex(' ')+(' …' if len(b)>n else '')
for t,h,s,a in pk:
    op=a[0]
    if op not in (0x12,0x52,0x1b): continue
    ah=struct.unpack_from('<H',a,1)[0]; v=a[3:]; ts=(t-t0)/1e6
    if ah==9:
        bulk+=1
        if bulk<=4 or bulk%1000==0: print(f"{ts:8.2f} BULK#{bulk} len {len(v)}: {hx(v,32)}")
        lastbulk=(ts,v); continue
    tag={6:'CMD >',3:'RSP <',11:'ACK <'}.get(ah,str(ah))
    print(f"{ts:8.2f} {tag} [{len(v):3}] {hx(v)}")
print("total bulk packets", bulk, "last", lastbulk[0] if lastbulk else None, hx(lastbulk[1],32) if lastbulk else '')
