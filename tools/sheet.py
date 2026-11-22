import sys; sys.path.insert(0,'.')
from PIL import Image
import tbui3
from tbui import entries
f=sys.argv[1]; out=sys.argv[2]; ids=set(range(int(sys.argv[3]),int(sys.argv[4])+1)); scale=int(sys.argv[5]) if len(sys.argv)>5 else 3
a=open(f,'rb').read(); ims=[]
for i,fmt,w,h,off in entries(a):
    if i in ids and a[off:off+2]==b'PA':
        try: ims.append(tbui3.decode_pa(a,off))
        except Exception as e: pass
W=sum(im.width+4 for im in ims); H=max(im.height for im in ims)
sheet=Image.new('RGBA',(W,H),(40,40,40,255)); x=0
for im in ims: sheet.alpha_composite(im,(x,0)); x+=im.width+4
sheet=sheet.resize((sheet.width*scale,sheet.height*scale),Image.NEAREST); sheet.save(out); print(out, sheet.size, len(ims))
