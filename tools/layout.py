import sys, struct
sys.path.insert(0, '.')
def records(a):
    base = 0x400
    roff, cnt, rsz = struct.unpack_from('<IHH', a, 0x440)
    out = []
    for k in range(cnt):
        o = base + roff + k*rsz + 0x20  # first record at 0x4a0 for roff=0xa0? adjust below
        out.append(o)
    return roff, cnt, rsz
if __name__ == '__main__':
    for f in sys.argv[1:]:
        a = open(f, 'rb').read()
        roff, cnt, rsz = struct.unpack_from('<IHH', a, 0x440)
        print('==', f.split('/')[-1], 'records', cnt)
        for k in range(cnt):
            o = 0x400 + roff + k*rsz
            r = a[o:o+rsz]
            idx, kind, one, src = r[0], r[1], r[2], r[3]
            x, y, w, h = struct.unpack_from('<hhhh', r, 4)
            p = struct.unpack_from('<HHHHHHHHHH', r, 12)
            print(f'  #{idx:2} kind {kind} src {src:3} xy ({x:4},{y:4}) wh ({w:3},{h:3}) params {p}')
