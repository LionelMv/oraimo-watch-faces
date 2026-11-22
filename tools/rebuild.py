import sys, struct, glob, hashlib, binascii
sys.path.insert(0,'.')
from att import att_packets
from verify import crc as crc8005
pk=list(att_packets(sys.argv[1]))
bulk=[a[3:] for t,h,s,a in pk if a[0] in (0x52,0x12) and len(a)>3 and struct.unpack_from('<H',a,1)[0]==9]
# Reassemble messages: a message starts with a type byte 01..04 + 12-byte header; payload length in header
files=[]; cur=None; i=0; stream=b''.join(bulk)
msgs=[]; buf=bytearray()
# walk packets: header packets begin new message; length known from header
j=0
while j < len(bulk):
    p=bulk[j]; typ=p[0]
    if typ in (1,4): msgs.append((typ,p,b'')); j+=1; continue
    hdr=p[:12]; ln=struct.unpack_from('<H',hdr,10)[0]
    data=bytearray(p[12:]); j+=1
    while len(data)<ln: data+=bulk[j]; j+=1
    msgs.append((typ,hdr,bytes(data[:ln])))
out=None; n=0; ok=bad=0; algos={}
for typ,hdr,data in msgs:
    if typ==1:
        out=bytearray(); print('START', hdr.hex(' '))
    elif typ==2:
        out+=data; off=0
        print('INFO hdr', hdr.hex(' '), 'len', len(data), 'total size in TOPSTEP hdr', struct.unpack_from('<I',data,0x0c)[0])
    if typ in (2,3):
        c=struct.unpack_from('<H',hdr,8)[0]
        cands={'crc8005':crc8005(data),'hqx0':binascii.crc_hqx(data,0),'hqxffff':binascii.crc_hqx(data,0xffff)}
        for k,v in cands.items():
            if v==c: algos[k]=algos.get(k,0)+1
        if typ==3:
            off=struct.unpack_from('<I',hdr,4)[0]
            assert off==len(out), (hex(off),hex(len(out)))
            out+=data
    elif typ==4:
        n+=1; fn=f'rebuilt_{n}.bin'; open(fn,'wb').write(out)
        h=hashlib.md5(out).hexdigest()
        match=[f for f in glob.glob('oraimo_app/dial/**/*.bin',recursive=True) if hashlib.md5(open(f,'rb').read()).hexdigest()==h]
        print('END ->',fn,len(out),'bytes; TOPSTEP crc ok:', struct.unpack_from('<H',out,0x10)[0]==crc8005(out[0x400:]),'| identical to:',match or 'none (not on phone)')
print('block checksum algorithm matches:',algos, 'of', sum(1 for m in msgs if m[0] in (2,3)),'blocks')
