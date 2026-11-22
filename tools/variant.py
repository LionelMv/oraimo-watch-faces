"""Rebuild an existing face with edits: keep only some element records and/or swap resources from another file.
usage: variant.py in.bin out.bin --keep 0,1,7,8,9  [--res 0=template.bin:44 ...]"""
import sys, struct, argparse
sys.path.insert(0, '.')
import facekit as fk
ap = argparse.ArgumentParser(); ap.add_argument('src'); ap.add_argument('out')
ap.add_argument('--keep'); ap.add_argument('--res', nargs='*', default=[])
ap.add_argument('--nofonts', action='store_true'); ap.add_argument('--maxres', type=int)
A = ap.parse_args()
src = open(A.src, 'rb').read()
f = fk.Face(A.src)
cnt = struct.unpack_from('<H', src, 0x44c)[0]
swap = {}
for s in A.res:
    rid, rest = s.split('='); fn, orid = rest.split(':'); swap[int(rid)] = fk.copy_resource(open(fn, 'rb').read(), int(orid))
if A.maxres: cnt = A.maxres
for rid in range(cnt): f.add_raw(*(swap.get(rid) or fk.copy_resource(src, rid)))
roff, rc, rs = struct.unpack_from('<IHH', src, 0x440)
keep = set(map(int, A.keep.split(','))) if A.keep else set(range(rc))
for k in range(rc):
    if k not in keep: continue
    r = src[0x400 + roff + 32 * k: 0x400 + roff + 32 * (k + 1)]
    f.recs.append((r[1], r[3], *struct.unpack_from('<hhhh', r, 4), list(struct.unpack_from('<10H', r, 12))))
fc = struct.unpack_from('<H', src, 0x454)[0]
if A.nofonts: fc = 0
for k in range(fc):
    o = 0x400 + 0x1920 + 0x180 * k; n = struct.unpack_from('<H', src, o)[0]
    f.fonts.append([struct.unpack_from('<HH', src, o + 4 + 4 * j) for j in range(n)])
f.preview_id = struct.unpack_from('<I', src, 0x460)[0]
open(A.out, 'wb').write(f.build()); print('wrote', A.out, 'records', sorted(keep))
