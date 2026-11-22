import struct
def parse(a, off):
    alpha = a[off+3] == 1
    w, h = struct.unpack_from('<HH', a, off+4); step = a[off+8] or 1; es = a[off+9]
    avg = struct.unpack_from('<H', a, off+10)[0]
    n = -(-h // step) + 1
    f = '<b' if es == 1 else '<h'
    tbl = [struct.unpack_from(f, a, off+16+k*es)[0] for k in range(n)]
    d0 = off + 16 + n*es
    return dict(alpha=alpha, w=w, h=h, step=step, avg=avg, tbl=tbl, d0=d0)

def tokens(a, off):
    """yield ('run',n,alpha,color) / ('lit',alpha_or_None,color) / ('idx',b) in pixel order"""
    m = parse(a, off); w, h = m['w'], m['h']; pb = 3 if m['alpha'] else 2
    p = m['d0']; total = w*h; x = 0; out = []
    while x < total:
        b = a[p]; p += 1; n = b & 0x3f
        if b & 0xC0 == 0x80:
            if pb == 3: al, c = a[p], a[p+1] | a[p+2] << 8
            else: al, c = 255, a[p] | a[p+1] << 8
            p += pb; out.append(('run', n, al, c)); x += n
        elif b & 0xC0 == 0xC0:
            for _ in range(n): out.append(('lit', a[p] | a[p+1] << 8)); p += 2; x += 1
        else:
            out.append(('idx', b)); x += 1
    return m, out, p

def render(m, toks, h7):
    """h7: hash function color->0..127, or 'ring'. returns list of (alpha,color)"""
    cache = [0]*128; ring = 0; al = 0; pix = []
    def put(c):
        nonlocal ring
        if h7 == 'ring': cache[ring % 128] = c; ring += 1
        else: cache[h7(c)] = c
    for t in toks:
        if t[0] == 'run':
            al = t[2]; pix += [(al, t[3])]*t[1]; put(t[3])
        elif t[0] == 'lit':
            pix.append((al, t[1])); put(t[1])
        else:
            pix.append((al, cache[t[1]]))
    return pix

def render_delta(m, toks, layout=(2,3,2)):
    rb, gb, bb = layout
    al = 0; prev = 0; pix = []
    for t in toks:
        if t[0] == 'run':
            al, prev = t[2], t[3]; pix += [(al, prev)]*t[1]
        elif t[0] == 'lit':
            prev = t[1]; pix.append((al, prev))
        else:
            b = t[1]
            dr = (b >> (gb+bb)) - (1 << (rb-1)); dg = ((b >> bb) & ((1<<gb)-1)) - (1 << (gb-1)); db = (b & ((1<<bb)-1)) - (1 << (bb-1))
            r = ((prev >> 11) + dr) & 31; g = (((prev >> 5) & 63) + dg) & 63; bl = ((prev & 31) + db) & 31
            prev = (r << 11) | (g << 5) | bl; pix.append((al, prev))
    return pix

def to_image(a, off):
    from PIL import Image
    m, toks, _ = tokens(a, off)
    pix = render_delta(m, toks)
    img = Image.new('RGBA', (m['w'], m['h']))
    img.putdata([(((c>>11)&31)*255//31, ((c>>5)&63)*255//63, (c&31)*255//31, al) for al, c in pix[:m['w']*m['h']]])
    return img
