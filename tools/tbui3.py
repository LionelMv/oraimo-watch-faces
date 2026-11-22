import struct, collections
from PIL import Image
from tbui import entries
low=collections.Counter(); c0=collections.Counter()
def col(c):
    return (((c>>11)&31)*255//31, ((c>>5)&63)*255//63, (c&31)*255//31)
def decode_pa(a, off):
    w,h=struct.unpack_from('<HH',a,off+4); es=a[off+9]; avg=struct.unpack_from('<H',a,off+10)[0]
    t0=off+16; f='<b' if es==1 else '<h'
    tbl=[struct.unpack_from(f,a,t0+k*es)[0] for k in range(h+1)]
    d0=t0+(h+1)*es
    img=Image.new('RGBA',(w,h)); P=img.load()
    for y in range(h):
        p=d0+y*avg+tbl[y]; end=d0+(y+1)*avg+tbl[y+1]; x=0; last=(255,255,255)
        while x<w:
            b=a[p]; p+=1; n=b&0x3f
            if b&0xC0==0x80:
                al=a[p]; c=col(a[p+1]|(a[p+2]<<8)); p+=3; last=c
                for _ in range(n): P[x,y]=c+(al,); x+=1
            elif b&0xC0==0xC0:
                for _ in range(n):
                    c0[(a[p],a[p+1])]+=1; P[x,y]=last+(a[p],); p+=2; x+=1
            else:
                low[b]+=1; P[x,y]=(0,0,0,0); x+=1
        if not (x==w and p==end): raise ValueError(f"row {y}: x={x}/{w} p-end={p-end}")
    return img
