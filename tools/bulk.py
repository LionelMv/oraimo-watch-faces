import sys, struct
sys.path.insert(0,'.')
from att import att_packets
pk=list(att_packets(sys.argv[1])); t0=pk[0][0]
seq=[]
for t,h,s,a in pk:
    if a[0] in (0x52,0x12,0x1b) and len(a)>=3:
        ah=struct.unpack_from('<H',a,1)[0]
        if ah in (9,11): seq.append(((t-t0)/1e6, ah, a[3:]))
# print first 40 events, then summary of non-250 bulk packets
for i,(ts,ah,v) in enumerate(seq[:45]):
    print(f"{ts:7.2f} {'BULK' if ah==9 else 'ACK '} len {len(v):3} {v[:16].hex(' ')}")
print("--- bulk packets whose first byte is 01/02/03/04 and len != 250, or ACKs with type!=83:")
for ts,ah,v in seq:
    if (ah==9 and len(v)!=250) or (ah==11 and v[0]!=0x83):
        print(f"{ts:7.2f} {'BULK' if ah==9 else 'ACK '} len {len(v):3} {v[:32].hex(' ')}")
