#!/usr/bin/env python3
"""Build a test watch face from a known-good DIY face file:
new background + preview, new big time digits (all 5 colour sets), same layout & offsets."""
import sys, struct, io, math
sys.path.insert(0, '.')
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from tbui import entries
import tbui3

SRC, OUT = sys.argv[1], sys.argv[2]
a = bytearray(open(SRC, 'rb').read())
E = entries(a)
FONT = '/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf'

def rgb565(r, g, b): return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

# ---------- PA encoder (run tokens only: 0x80|n + alpha + rgb565 LE) ----------
def encode_pa(img, hdr2_3=b'\x00\x01'):
    img = img.convert('RGBA'); w, h = img.size; P = img.load()
    rows = []
    for y in range(h):
        out = bytearray(); x = 0
        while x < w:
            r, g, b, al = P[x, y]
            key = (al, rgb565(r, g, b) if al else 0)
            n = 1
            while x + n < w and n < 63:
                r2, g2, b2, a2 = P[x + n, y]
                if (a2, rgb565(r2, g2, b2) if a2 else 0) != key: break
                n += 1
            out += bytes([0x80 | n, key[0]]) + struct.pack('<H', key[1]); x += n
        rows.append(bytes(out))
    starts = [0]
    for r in rows: starts.append(starts[-1] + len(r))
    total = starts[-1]; avg = total // h
    deltas = [starts[i] - i * avg for i in range(h + 1)]
    es = 1 if all(-128 <= d <= 127 for d in deltas) else 2
    tbl = b''.join(struct.pack('<b' if es == 1 else '<h', d) for d in deltas)
    hdr = b'PA' + hdr2_3 + struct.pack('<HH', w, h) + bytes([0, es]) + struct.pack('<H', avg) + bytes(4)
    return hdr + tbl + b''.join(rows)

def replace_pa(rid, img):
    k = next(k for k, e in enumerate(E) if e[0] == rid)
    i, fmt, w, h, off = E[k]
    assert img.size == (w, h), (rid, img.size, (w, h))
    slot = (E[k + 1][4] if k + 1 < len(E) else len(a)) - off
    enc = encode_pa(img, bytes(a[off + 2:off + 4]))
    if len(enc) > slot: raise SystemExit(f'id {rid}: encoded {len(enc)} > slot {slot}')
    a[off:off + slot] = enc + bytes(slot - len(enc))
    back = tbui3.decode_pa(bytes(a), off)                      # round-trip check
    def sig(im):
        im = im.convert('RGBA'); return [(al, rgb565(r, g, b) if al else 0) for r, g, b, al in im.getdata()]
    assert sig(back) == sig(img), f'round-trip mismatch id {rid}'
    return len(enc), slot

def quantize(img):  # hard alpha, keeps runs long
    img = img.convert('RGBA'); px = img.load()
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, al = px[x, y]; px[x, y] = (r, g, b, 255 if al >= 110 else 0)
    return img

def grad(y, h):  # orange -> hot pink, per row (free in run encoding)
    t = y / max(1, h - 1)
    return (int(255), int(150 - 110 * t), int(20 + 120 * t))

def glyph(ch, w, h, size):
    font = ImageFont.truetype(FONT, size)
    m = Image.new('L', (w, h), 0); d = ImageDraw.Draw(m)
    bb = d.textbbox((0, 0), ch, font=font)
    d.text(((w - (bb[2] - bb[0])) / 2 - bb[0], (h - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=font, fill=255)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); P = img.load(); M = m.load()
    for y in range(h):
        c = grad(y, h)
        for x in range(w):
            if M[x, y] >= 110: P[x, y] = c + (255,)
    return img

# ---------- 1. big time digits + colon for all 5 colour sets ----------
report = []
for base in (10, 31, 52, 73, 94):            # 10 digits (48x74) then colon (18x74)
    for dgt in range(10):
        report.append(replace_pa(base + dgt, glyph(str(dgt), 48, 74, 78)))
    report.append(replace_pa(base + 10, glyph(':', 18, 74, 70)))
print('digits: max used/slot', max(r[0] / r[1] for r in report))

# ---------- 2. background 466x466 ----------
W = 466
bg = Image.new('RGB', (W, W)); P = bg.load()
for y in range(W):
    for x in range(W):
        dx, dy = x - W / 2, y - W / 2; r = math.hypot(dx, dy) / (W / 2)
        P[x, y] = (int(10 + 30 * r), int(12 + 20 * (1 - r)), int(40 + 70 * (1 - r)))
d = ImageDraw.Draw(bg)
for k, rad in enumerate(range(60, 240, 30)):
    d.ellipse((W/2-rad, W/2-rad, W/2+rad, W/2+rad), outline=(40+20*k, 60, 140+15*k), width=2)
for t in range(60):
    ang = t * math.pi / 30; r1 = 222 if t % 5 else 205
    d.line((W/2 + r1*math.sin(ang), W/2 - r1*math.cos(ang), W/2 + 230*math.sin(ang), W/2 - 230*math.cos(ang)),
           fill=(255, 140, 60) if t % 5 == 0 else (120, 130, 200), width=3 if t % 5 == 0 else 1)
f = ImageFont.truetype(FONT, 22)
txt = 'BUILT ON LAPTOP'; bb = d.textbbox((0, 0), txt, font=f)
d.text(((W - (bb[2]-bb[0])) / 2, 330), txt, font=f, fill=(255, 170, 90))

def put_bmp(rid, img):
    k = next(k for k, e in enumerate(E) if e[0] == rid); off = E[k][4]
    assert a[off:off+2] == b'BM'
    pix_off = struct.unpack_from('<I', a, off + 10)[0]; w, h = struct.unpack_from('<ii', a, off + 18)
    assert img.size == (w, abs(h))
    rows = []
    src = img.convert('RGB').load()
    order = range(abs(h) - 1, -1, -1) if h > 0 else range(abs(h))   # bottom-up when h>0
    buf = bytearray()
    for y in order:
        for x in range(w):
            r, g, b = src[x, y]; buf += struct.pack('<H', rgb565(r, g, b))
        buf += bytes((-len(buf)) % 4) if (w * 2) % 4 else b''
    a[off + pix_off: off + pix_off + len(buf)] = buf
put_bmp(180, bg)

# ---------- 3. preview 312x312: bg + time "10:08" at the DIY position (approx) ----------
prev = bg.convert('RGBA')
x = 70
for ch in '10:08':
    g = glyph(ch, 18 if ch == ':' else 48, 74, 70 if ch == ':' else 78); prev.alpha_composite(g, (x, 150)); x += g.width
put_bmp(181, prev.convert('RGB').resize((312, 312), Image.LANCZOS))

# ---------- 4. checksum ----------
def crc(d):
    c=0
    for b in d:
        c^=b<<8
        for _ in range(8): c=((c<<1)^0x8005)&0xffff if c&0x8000 else (c<<1)&0xffff
    return c
struct.pack_into('<H', a, 0x10, crc(bytes(a[0x400:])))
open(OUT, 'wb').write(a)
prev.convert('RGB').save(OUT.replace('.bin', '_preview.png'))
print('wrote', OUT, len(a), 'bytes, crc', hex(crc(bytes(a[0x400:]))))
