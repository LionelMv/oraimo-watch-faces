import struct, io
from PIL import Image
def entries(a):
    """resource table: (id, fmt, w, h, abs_offset)"""
    o=0x1120; out=[]
    while o+12<=len(a):
        i,fmt,w,h,off=struct.unpack_from('<HHHHI',a,o)
        if (i==0 and o>0x1120) or off==0 or off+0x400>len(a): break
        out.append((i,fmt,w,h,off+0x400)); o+=12
    return out
def px(p):  # 3 bytes: alpha, rgb565 LE
    a=p[0]; c=p[1]|(p[2]<<8)
    return (((c>>11)&31)*255//31, ((c>>5)&63)*255//63, (c&31)*255//31, a)
def decode_pa(a, off):
    assert a[off:off+2]==b'PA', a[off:off+4]
    w,h=struct.unpack_from('<HH',a,off+4); es=a[off+9]; avg=struct.unpack_from('<H',a,off+10)[0]
    t0=off+16; fmt='<b' if es==1 else '<h'
    tbl=[struct.unpack_from(fmt,a,t0+k*es)[0] for k in range(h+1)]
    d0=t0+(h+1)*es
    img=Image.new('RGBA',(w,h)); P=img.load()
    for y in range(h):
        p=d0+y*avg+tbl[y]; end=d0+(y+1)*avg+tbl[y+1]; x=0
        while x<w:
            b=a[p]; p+=1; n=b&0x7f
            if b&0x80:
                c=px(a[p:p+3]); p+=3
                for _ in range(n): P[x,y]=c; x+=1
            else:
                for _ in range(n): P[x,y]=px(a[p:p+3]); p+=3; x+=1
        assert x==w and p==end, (y,x,w,hex(p),hex(end))
    return img, d0+h*avg+tbl[h]-off
