import sys, struct, collections
def records(path):
    d=open(path,'rb').read(); o=16
    while o+24<=len(d):
        ol,il,fl,dr,ts=struct.unpack_from('>IIIIq',d,o); o+=24
        yield fl, ts, d[o:o+il]; o+=il
def att_packets(path):
    # reassemble L2CAP over ACL
    buf={}; 
    for fl,ts,p in records(path):
        if not p or p[0]!=2: continue
        sent = (fl & 1)==0   # bit0: 0 = host->controller (phone sends)
        h,ln=struct.unpack_from('<HH',p,1); handle=h&0xfff; pb=(h>>12)&3; data=p[5:5+ln]
        key=(handle,sent)
        if pb in (0,2):
            if len(data)<4: continue
            l2len,cid=struct.unpack_from('<HH',data,0)
            buf[key]=[l2len,cid,bytearray(data[4:]),ts]
        elif pb==1 and key in buf:
            buf[key][2]+=data
        else: continue
        l2len,cid,pl,t0=buf[key]
        if len(pl)>=l2len:
            del buf[key]
            if cid==4: yield t0, handle, sent, bytes(pl[:l2len])
if __name__=='__main__':
    path=sys.argv[1]
    names={0x12:'WriteReq',0x52:'WriteCmd',0x1b:'Notify',0x13:'WriteRsp',0x1d:'Indicate',0x0a:'ReadReq',0x0b:'ReadRsp',0x08:'ReadByType',0x09:'ReadByTypeRsp',0x10:'ReadByGroup',0x11:'ReadByGroupRsp',0x04:'FindInfo',0x05:'FindInfoRsp',0x02:'MTUReq',0x03:'MTURsp',0x01:'Error'}
    cnt=collections.Counter(); first={}
    pk=list(att_packets(path))
    for t,h,s,a in pk:
        op=a[0]; ah=struct.unpack_from('<H',a,1)[0] if len(a)>=3 and op in (0x12,0x52,0x1b,0x1d,0x0a) else None
        k=(h,'phone>' if s else 'watch>',names.get(op,hex(op)),ah); cnt[k]+=1
        first.setdefault(k,[]).append(len(a))
    for k,v in sorted(cnt.items(), key=lambda x:-x[1]):
        L=first[k]; print(k, v, 'len min/max', min(L), max(L))
