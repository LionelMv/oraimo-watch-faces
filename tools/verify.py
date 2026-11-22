import sys, struct
t=[]
for i in range(256):
    c=i<<8
    for _ in range(8): c=((c<<1)^0x8005)&0xffff if c&0x8000 else (c<<1)&0xffff
    t.append(c)
def crc(d):
    c=0
    for b in d: c=((c<<8)&0xffff)^t[((c>>8)^b)&0xff]
    return c
for f in sys.argv[1:]:
    a=open(f,'rb').read()
    st=struct.unpack_from('<H',a,0x10)[0]; calc=crc(a[0x400:])
    print(f.split('/')[-1], 'stored',hex(st),'calc',hex(calc),'OK' if st==calc else 'MISMATCH',
          '| size field', struct.unpack_from('<I',a,0x0c)[0]==len(a), '| body len', struct.unpack_from('<I',a,0x28)[0]==len(a)-0x400)
