import sys, io, struct
from PIL import Image
a=open(sys.argv[1],'rb').read()
i=0
while (i:=a.find(b'BM',i))!=-1:
    size=struct.unpack_from('<I',a,i+2)[0]
    if 1000<size<=len(a)-i:
        try:
            im=Image.open(io.BytesIO(a[i:i+size])); im.load()
            print(hex(i), size, im.size, im.mode); im.save(f"{sys.argv[2]}_{hex(i)}.png")
        except Exception as e: pass
    i+=2
