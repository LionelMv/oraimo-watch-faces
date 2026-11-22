"""facekit — build oraimo Watch 5R Pro (OSW-830) watch-face .bin files from scratch.

Format summary (see README §6):
  0x000  TOPSTEP header (copied from a template, size/CRC patched)
  0x400  TBUI header (copied from template, size patched)
  0x440  layout header: records @+0xa0 (32 B each), resources @+0xd20 (12 B each),
         fonts @+0x1920 (0x180 B each), data @+0x4920   (all offsets relative to 0x400)
"""
import struct
from PIL import Image

REL = 0x400
REC_OFF, RES_OFF, FONT_OFF, DATA_OFF = 0xa0, 0xd20, 0x1920, 0x4920
FONT_STRIDE = 0x180

# element kinds / data sources (decoded from Oraimo faces)
K_BG, K_HAND, K_TIMEDATE, K_DATA, K_IMGLIST, K_LEVEL, K_PREVIEW = 0, 1, 2, 3, 4, 5, 6
SRC_TIME, SRC_DAY, SRC_MONTHDAY = 0, 1, 13
SRC_STEPS, SRC_DISTANCE, SRC_KCAL, SRC_HEART = 0, 6, 7, 8
SRC_WEEKDAY, SRC_AMPM, SRC_BATTERY = 0, 6, 0
SRC_HOUR, SRC_MIN, SRC_SEC = 6, 7, 8
ALIGN_LEFT, ALIGN_CENTER = 0, 1


def rgb565(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)


def crc16_umts(d):          # file checksum (TOPSTEP 0x10)
    c = 0
    for b in d:
        c ^= b << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x8005) & 0xffff if c & 0x8000 else (c << 1) & 0xffff
    return c


def encode_pa(img, alpha=True):
    """Encode a PIL image as a 'PA' block: per-row, run tokens only (0x80|n).
    alpha=True -> format 0x20e (3-byte pixels), False -> 0x10e (2-byte pixels, opaque)."""
    img = img.convert('RGBA'); w, h = img.size; px = img.load()
    rows = []
    for y in range(h):
        out = bytearray(); x = 0
        while x < w:
            def key(xx):
                r, g, b, a = px[xx, y]
                if not alpha: return (255, rgb565(r, g, b))
                return (a, rgb565(r, g, b) if a else 0)
            k = key(x); n = 1
            while x + n < w and n < 63 and key(x + n) == k: n += 1
            if alpha:
                out += bytes([0x80 | n, k[0]]) + struct.pack('<H', k[1]); x += n
            elif n >= 2:            # opaque: runs only for n>=2 (Oraimo never writes 0x81 in opaque images)
                out += bytes([0x80 | n]) + struct.pack('<H', k[1]); x += n
            else:                   # opaque single pixels -> literal group 0xC0|m + m colours
                lits = []
                while x < w and len(lits) < 63:
                    k = key(x)
                    if x + 1 < w and key(x + 1) == k: break     # a run starts here
                    lits.append(k[1]); x += 1
                out += bytes([0xC0 | len(lits)]) + b''.join(struct.pack('<H', c) for c in lits)
        rows.append(bytes(out))
    starts = [0]
    for r in rows: starts.append(starts[-1] + len(r))
    avg = starts[-1] // h
    deltas = [s - i * avg for i, s in enumerate(starts)]
    es = 1 if all(-128 <= d <= 127 for d in deltas) else 2
    tbl = b''.join(struct.pack('<b' if es == 1 else '<h', d) for d in deltas)
    hdr = b'PA' + bytes([0, 1 if alpha else 0]) + struct.pack('<HH', w, h) + bytes([0, es]) + struct.pack('<H', avg) + bytes(4)
    return hdr + tbl + b''.join(rows)


class Face:
    def __init__(self, template_path):
        self.t = open(template_path, 'rb').read()
        assert self.t[:7] == b'TOPSTEP'
        self.res = []      # (fmt, w, h, blob)
        self.recs = []     # (kind, src, x, y, w, h, params[10])
        self.fonts = []    # list of [(char, res_id)]
        self.preview_id = None

    # ---- resources
    def add_image(self, img, alpha=True):
        rid = len(self.res)
        self.res.append((0x20e if alpha else 0x10e, img.width, img.height, encode_pa(img, alpha)))
        return rid

    def add_raw(self, fmt, w, h, blob):
        rid = len(self.res); self.res.append((fmt, w, h, blob)); return rid

    def add_font(self, glyphs):
        """glyphs: dict char -> PIL image. Returns font index."""
        mapping = [(ord(ch), self.add_image(im)) for ch, im in glyphs.items()]
        self.fonts.append(mapping); return len(self.fonts) - 1

    # ---- layout records
    def rec(self, kind, src, x=0, y=0, w=0, h=0, params=()):
        p = list(params) + [0] * (10 - len(params))
        self.recs.append((kind, src, x, y, w, h, p))

    def background(self, img):
        self.rec(K_BG, 0, params=[self.add_image(img.convert('RGB'), alpha=False)])

    def preview(self, img):
        rid = self.add_image(img.convert('RGB').resize((312, 312), Image.LANCZOS), alpha=False)
        self.preview_id = rid; self.rec(K_PREVIEW, 1, params=[rid])

    # ---- build
    def build(self):
        out = bytearray(self.t[:REL + 0xa0])                       # TOPSTEP + TBUI + layout hdr + misc
        out += bytes(REL + DATA_OFF - len(out))
        # records
        for k, (kind, src, x, y, w, h, p) in enumerate(self.recs):
            r = bytes([k, kind, 1, src]) + struct.pack('<hhhh', x, y, w, h) + struct.pack('<10H', *p)
            out[REL + REC_OFF + 32 * k: REL + REC_OFF + 32 * (k + 1)] = r
        assert REL + REC_OFF + 32 * len(self.recs) <= REL + RES_OFF
        # fonts
        for k, m in enumerate(self.fonts):
            e = struct.pack('<HH', len(m), 0) + b''.join(struct.pack('<HH', c, r) for c, r in m)
            assert len(e) <= FONT_STRIDE
            out[REL + FONT_OFF + FONT_STRIDE * k: REL + FONT_OFF + FONT_STRIDE * k + len(e)] = e
        # resources + data
        data = bytearray(); table = bytearray()
        for rid, (fmt, w, h, blob) in enumerate(self.res):
            off = DATA_OFF + len(data)
            table += struct.pack('<HHHHI', rid, fmt, w, h, off)
            data += blob + bytes((-len(blob)) % 4)
        assert REL + RES_OFF + len(table) <= REL + FONT_OFF
        out[REL + RES_OFF: REL + RES_OFF + len(table)] = table
        out += data
        out += b'TBUI'                     # end marker: every Oraimo face ends with 'TBUI' (required)
        # layout header
        struct.pack_into('<IHHIHHIHHII', out, 0x440, REC_OFF, len(self.recs), 0x20, RES_OFF, len(self.res), 12,
                         FONT_OFF, len(self.fonts), 0x60, 4, DATA_OFF)
        struct.pack_into('<I', out, 0x460, self.preview_id or 0)
        # sizes + checksum
        struct.pack_into('<I', out, 0x40c, len(out) - 0x404)
        struct.pack_into('<I', out, 0x0c, len(out))
        struct.pack_into('<I', out, 0x28, len(out) - REL)
        struct.pack_into('<H', out, 0x10, crc16_umts(out[REL:]))
        return bytes(out)


def copy_resource(template_bytes, rid):
    """Return (fmt, w, h, blob) of a resource in an existing face, blob = bytes up to next resource."""
    a = template_bytes; ents = []
    o = REL + RES_OFF
    cnt = struct.unpack_from('<H', a, 0x44c)[0]
    for k in range(cnt):
        i, fmt, w, h, off = struct.unpack_from('<HHHHI', a, o + 12 * k); ents.append((i, fmt, w, h, off + REL))
    ents.sort(key=lambda e: e[4])
    for k, (i, fmt, w, h, off) in enumerate(ents):
        if i == rid:
            end = ents[k + 1][4] if k + 1 < len(ents) else len(a)
            blob = a[off:end]
            if k + 1 == len(ents) and blob.endswith(b'TBUI'): blob = blob[:-4]   # drop file end marker
            return fmt, w, h, blob
    raise KeyError(rid)


# ---------------------------------------------------------------- hands (format 0x40e)
# Hands are upright images split into 31x31 tiles (row-major tile order, row-major pixels in a tile),
# one index-table entry per tile (+1 end entry); header byte 8 = 0x1e. The watch rotates them itself.
K_WEATHER, SRC_WEATHER = 6, 2          # weather icon list (13 images, order: see README)
SRC_TEMP = 11                          # temperature number (font chars '0'-'9', '/', 'C', 'F', '_')
TILE = 31


def hand_grid(w, h, rows=None):
    # tile rows = ceil((h + 7) / 31): matches all Oraimo hands (158->6, 241->8, 278->10); see pivot +7 rule
    return -(-w // TILE), rows if rows else -(-(h + 7) // TILE)


def encode_hand(img, rows=None):
    img = img.convert('RGBA'); w, h = img.size; px = img.load()
    cols, rws = hand_grid(w, h, rows)
    def P(x, y):
        if x >= w or y >= h: return (0, 0)
        r, g, b, a = px[x, y]; return (a, rgb565(r, g, b) if a else 0)
    tiles = []
    for ty in range(rws):
        for tx in range(cols):
            out = bytearray()
            for yy in range(TILE):
                x = 0
                while x < TILE:
                    k = P(tx*TILE + x, ty*TILE + yy); n = 1
                    while x + n < TILE and P(tx*TILE + x + n, ty*TILE + yy) == k: n += 1
                    out += bytes([0x80 | n, k[0]]) + struct.pack('<H', k[1]); x += n
            tiles.append(bytes(out))
    starts = [0]
    for t in tiles: starts.append(starts[-1] + len(t))
    avg = starts[-1] // len(tiles)
    tbl = b''.join(struct.pack('<h', s - i * avg) for i, s in enumerate(starts))
    hdr = b'PA\x00\x01' + struct.pack('<HH', w, h) + bytes([0x1e, 2]) + struct.pack('<H', avg) + bytes(4)
    return hdr + tbl + b''.join(tiles)


def decode_hand(blob, rows=None):
    """Decode a 0x40e hand blob to a PIL image of size (w,h). Supports run/literal/delta tokens."""
    w, h = struct.unpack_from('<HH', blob, 4); avg = struct.unpack_from('<H', blob, 10)[0]
    cols, rws = hand_grid(w, h, rows)
    n = cols * rws + 1
    tbl = [struct.unpack_from('<h', blob, 16 + 2*k)[0] for k in range(n)]; d0 = 16 + 2*n
    end = d0 + (n - 1) * avg + tbl[-1]
    p = d0; pix = []; al = 0; prev = 0
    while p < end:
        b = blob[p]; p += 1; c = b & 0x3f
        if b & 0xC0 == 0x80:
            al, prev = blob[p], blob[p+1] | blob[p+2] << 8; p += 3; pix += [(al, prev)] * c
        elif b & 0xC0 == 0xC0:
            for _ in range(c): prev = blob[p] | blob[p+1] << 8; p += 2; pix.append((al, prev))
        else:
            dr = (b >> 5) - 2; dg = ((b >> 2) & 7) - 4; db = (b & 3) - 2
            prev = ((((prev >> 11) + dr) & 31) << 11) | (((((prev >> 5) & 63) + dg) & 63) << 5) | (((prev & 31) + db) & 31)
            pix.append((al, prev))
    canvas = Image.new('RGBA', (cols*TILE, rws*TILE), (0, 0, 0, 0)); C = canvas.load()
    for t in range(cols * rws):
        tx, ty = t % cols, t // cols
        for k in range(TILE*TILE):
            a, c = pix[t*TILE*TILE + k]
            C[tx*TILE + k % TILE, ty*TILE + k // TILE] = (((c >> 11) & 31) * 255 // 31, ((c >> 5) & 63) * 255 // 63, (c & 31) * 255 // 31, a)
    return canvas


def add_hand(face, img, rows=None):
    return face.add_raw(0x40e, img.width, img.height, encode_hand(img, rows))
Face.add_hand = add_hand
