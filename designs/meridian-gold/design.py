#!/usr/bin/env python3
"""Meridian Gold — black analog face with white baton markers and four sub-dials:
   top: date (MM/DD) + weekday · left: steps · right: weather + temperature · bottom: golden battery ring.
v2 (2026-11-08): outlined "pill" hour/minute hands, shorter hour markers, weather instead of heart rate.
(v1 backup removed 2026-11-08 at user request; v2 confirmed on the watch.)
Run from anywhere:  ../../venv/bin/python -I design.py   -> meridian-gold.bin + preview.png"""
import math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from PIL import Image, ImageDraw, ImageFont
import facekit as fk

TEMPLATE = os.path.join(ROOT, 'samples/from_capture/store_face_373284.bin')   # analog template (hands, header)
UB = '/usr/share/fonts/truetype/ubuntu/Ubuntu-'
CJK = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
SS = 4                     # supersampling for smooth edges
W = 466; C = W / 2

GOLD = (245, 184, 0); GOLD_DIM = (70, 58, 22)
WHITE = (245, 245, 245); GREY = (120, 120, 126); DIAL = (26, 26, 29); RING = (52, 52, 58)
GREEN = (120, 230, 40); RED = (240, 50, 60)
CLOUD = (215, 220, 228); BLUE = (80, 170, 255); SUN = (255, 196, 30)

SUB_R = 58
SUBS = {'top': (C, C - 108), 'left': (C - 108, C), 'right': (C + 108, C), 'bottom': (C, C + 108)}

def font(name, size): return ImageFont.truetype(UB + name, size * SS)

def big(w, h): return Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
def down(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)

# ---------------------------------------------------------------- background
def background():
    im = Image.new('RGBA', (W * SS, W * SS), (0, 0, 0, 255)); d = ImageDraw.Draw(im)
    s = SS
    # minute track
    for t in range(60):
        if t % 5 == 0: continue
        a = t * math.pi / 30; r1, r2 = 219, 229
        d.line([(C*s + r1*s*math.sin(a), C*s - r1*s*math.cos(a)), (C*s + r2*s*math.sin(a), C*s - r2*s*math.cos(a))],
               fill=GREY, width=2 * s)
    # hour batons
    for t in range(12):
        a = t * math.pi / 6; r1, r2 = 182, 214      # v2: shorter batons (was 172)
        p1 = (C*s + r1*s*math.sin(a), C*s - r1*s*math.cos(a)); p2 = (C*s + r2*s*math.sin(a), C*s - r2*s*math.cos(a))
        d.line([p1, p2], fill=WHITE, width=9 * s)
        for p in (p1, p2): d.ellipse([p[0] - 4.5*s, p[1] - 4.5*s, p[0] + 4.5*s, p[1] + 4.5*s], fill=WHITE)
    # sub-dials
    for (x, y) in SUBS.values():
        d.ellipse([(x - SUB_R)*s, (y - SUB_R)*s, (x + SUB_R)*s, (y + SUB_R)*s], fill=DIAL, outline=RING, width=2 * s)
    # left: footprints icon + label
    x, y = SUBS['left']
    for dx, dy, rot in ((-7, -36, -12), (6, -42, 12)):
        foot = big(14, 22); fd = ImageDraw.Draw(foot)
        fd.ellipse([2*s, 0, 12*s, 14*s], fill=GREEN); fd.ellipse([3*s, 15*s, 11*s, 22*s], fill=GREEN)
        foot = foot.rotate(rot, resample=Image.BICUBIC, expand=True)
        im.alpha_composite(foot, (int((x + dx - 7) * s), int((y + dy - 11) * s)))
    label(d, 'STEPS', x, y + 26)
    # bottom: lightning bolt in the battery ring
    x, y = SUBS['bottom']
    bolt = [(x + 3, y - 15), (x - 8, y + 2), (x - 1, y + 2), (x - 4, y + 15), (x + 8, y - 3), (x + 1, y - 3)]
    d.polygon([(px * s, py * s) for px, py in bolt], fill=GOLD)
    return down(im).convert('RGB')

def label(d, text, cx, cy):
    f = font('M.ttf', 11); bb = d.textbbox((0, 0), text, font=f)
    d.text((cx*SS - (bb[2] - bb[0]) / 2 - bb[0], cy*SS - (bb[3] - bb[1]) / 2 - bb[1]), text, font=f, fill=GREY)

# ---------------------------------------------------------------- glyph helpers
def glyph(ch, w, h, size, colour, fname='M.ttf', fpath=None):
    im = big(w, h); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(fpath, size * SS) if fpath else font(fname, size)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text(((w*SS - (bb[2] - bb[0])) / 2 - bb[0], (h*SS - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=colour)
    return down(im)

def battery_ring(level, size=112):
    im = big(size, size); d = ImageDraw.Draw(im); s = SS
    r_out, r_in = (size / 2 - 3) * s, (size / 2 - 13) * s; cx = cy = size / 2 * s
    seg = 10; gap = 6     # degrees
    for k in range(seg):                       # clockwise from the bottom-left, leaving the bottom open
        a0 = 140 + k * (260 / seg) + gap / 2; a1 = 140 + (k + 1) * (260 / seg) - gap / 2
        col = GOLD if k < level else GOLD_DIM
        pts = []
        for a in [a0 + (a1 - a0) * i / 12 for i in range(13)]:
            pts.append((cx + r_out * math.cos(math.radians(a)), cy + r_out * math.sin(math.radians(a))))
        for a in [a1 - (a1 - a0) * i / 12 for i in range(13)]:
            pts.append((cx + r_in * math.cos(math.radians(a)), cy + r_in * math.sin(math.radians(a))))
        d.polygon(pts, fill=col)
    return down(im)


# ---------------------------------------------------------------- weather icons (13, Oraimo order)
WEATHER = ['partly-cloudy', 'sunny', 'light-snow', 'rain', 'heavy-snow', 'cloudy', 'fog', 'wind',
           'heavy-rain', 'sleet', 'light-rain', 'thunder', 'unknown']

def weather_icon(kind, w=46, h=38):
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    def cloud(ox=0, oy=0, col=CLOUD, sc=1.0):
        def e(x0, y0, x1, y1): d.ellipse([(ox + x0*sc)*s, (oy + y0*sc)*s, (ox + x1*sc)*s, (oy + y1*sc)*s], fill=col)
        e(6, 12, 22, 28); e(14, 4, 34, 24); e(26, 11, 42, 27); d.rectangle([(ox + 14*sc)*s, (oy + 18*sc)*s, (ox + 34*sc)*s, (oy + 28*sc)*s], fill=col)
    def sun(cx, cy, r, rays=True):
        if rays:
            for k in range(8):
                a = k * math.pi / 4
                d.line([((cx + (r + 3)*math.cos(a))*s, (cy + (r + 3)*math.sin(a))*s), ((cx + (r + 7)*math.cos(a))*s, (cy + (r + 7)*math.sin(a))*s)], fill=SUN, width=2*s)
        d.ellipse([(cx - r)*s, (cy - r)*s, (cx + r)*s, (cy + r)*s], fill=SUN)
    def drops(xs, y0=30):
        for x in xs: d.line([(x*s, y0*s), ((x - 2)*s, (y0 + 6)*s)], fill=BLUE, width=2*s)
    def flakes(xs, y0=33):
        for x in xs:
            for a in (0, 60, 120):
                r = math.radians(a); d.line([((x - 3*math.cos(r))*s, (y0 - 3*math.sin(r))*s), ((x + 3*math.cos(r))*s, (y0 + 3*math.sin(r))*s)], fill=WHITE, width=s)
    if kind == 'sunny': sun(23, 19, 9)
    elif kind == 'partly-cloudy': sun(31, 14, 5); cloud(-2, 8, sc=0.85)
    elif kind == 'cloudy': cloud(0, 3)
    elif kind == 'fog':
        for k, y in enumerate((10, 17, 24, 31)): d.line([((6 + 4*(k % 2))*s, y*s), ((40 - 4*(k % 2))*s, y*s)], fill=CLOUD, width=3*s)
    elif kind == 'wind':
        for y, l in ((11, 24), (19, 30), (27, 18)):
            d.line([(6*s, y*s), ((6 + l)*s, y*s)], fill=CLOUD, width=3*s)
            d.arc([((6 + l - 5)*s), ((y - 6)*s), ((6 + l + 5)*s), ((y + 0)*s)], 270, 90, fill=CLOUD, width=3*s)
    else:
        cloud(0, -2)
        if kind == 'light-rain': drops([23])
        elif kind == 'rain': drops([15, 23, 31])
        elif kind == 'heavy-rain': drops([12, 19, 26, 33]); drops([16, 30], 33)
        elif kind == 'light-snow': flakes([23])
        elif kind == 'heavy-snow': flakes([14, 23, 32])
        elif kind == 'sleet': drops([16]); flakes([29])
        elif kind == 'thunder':
            d.polygon([(25*s, 25*s), (18*s, 33*s), (23*s, 33*s), (20*s, 39*s), (29*s, 30*s), (24*s, 30*s)], fill=SUN)
        elif kind == 'unknown':
            f = font('B.ttf', 16); bb = d.textbbox((0, 0), '?', font=f)
            d.text((24*s - (bb[2] - bb[0]) / 2 - bb[0], 15*s - (bb[3] - bb[1]) / 2 - bb[1]), '?', font=f, fill=(60, 60, 66))
    return down(im)

# ---------------------------------------------------------------- hands (reference style: stem + outlined pill)
# Pivot positions inside the hand pictures (measured from Oraimo's own hands, see README):
HOUR = dict(w=18, h=158, pivot=(9, 123), x=224, y=117, length=100)
MINUTE = dict(w=18, h=241, pivot=(9, 206), x=224, y=34, length=188)

def pill_hand(spec, stem=26, width=14, outline=3):
    w, h = spec['w'], spec['h']; px, py = spec['pivot']; L = spec['length']
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    # thin stem from the pivot
    d.rounded_rectangle([(px - 2)*s, (py - stem - 4)*s, (px + 2)*s, py*s], radius=2*s, fill=WHITE)
    # outlined pill
    top, bot = py - L, py - stem
    d.rounded_rectangle([(px - width/2)*s, top*s, (px + width/2)*s, bot*s], radius=width/2*s, fill=WHITE)
    d.rounded_rectangle([(px - width/2 + outline)*s, (top + outline)*s, (px + width/2 - outline)*s, (bot - outline)*s],
                        radius=(width/2 - outline)*s, fill=(0, 0, 0, 255))
    # centre disc (part of the hour hand; rotates invisibly)
    d.ellipse([(px - 6)*s, (py - 6)*s, (px + 6)*s, (py + 6)*s], fill=WHITE)
    return down(im)

# ---------------------------------------------------------------- build
def main():
    t = open(TEMPLATE, 'rb').read()
    face = fk.Face(TEMPLATE)
    bg = background()
    face.background(bg)

    # fonts
    DW, DH = 15, 24                                   # date digits
    date_font = face.add_font({**{str(n): glyph(str(n), DW, DH, 21, WHITE) for n in range(10)},
                               '/': glyph('/', DW, DH, 21, GOLD), '-': glyph('-', DW, DH, 21, GOLD)})
    NW, NH = 17, 28                                   # steps / heart-rate digits
    num_font = face.add_font({**{str(n): glyph(str(n), NW, NH, 25, WHITE, 'B.ttf') for n in range(10)},
                              '.': glyph('.', NW, NH, 25, WHITE, 'B.ttf'), '_': glyph('-', NW, NH, 25, GREY, 'B.ttf'),
                              '-': glyph('-', NW, NH, 25, GREY, 'B.ttf')})

    TW, TH = 15, 24                                   # temperature digits ('/' = minus, 'C' = °C, 'F' = °F)
    temp_font = face.add_font({**{str(n): glyph(str(n), TW, TH, 22, WHITE, 'B.ttf') for n in range(10)},
                               '/': glyph('-', TW, TH, 22, WHITE, 'B.ttf'), '-': glyph('-', TW, TH, 22, WHITE, 'B.ttf'),
                               'C': glyph('°C', 26, TH, 18, GREY, 'B.ttf'), 'F': glyph('°F', 26, TH, 18, GREY, 'B.ttf'),
                               '_': glyph('-', TW, TH, 22, GREY, 'B.ttf'), '%': glyph('%', TW, TH, 18, GREY, 'B.ttf'),
                               '.': glyph('.', TW, TH, 22, WHITE, 'B.ttf')})

    # top: month/day + weekday (14 images: CN, EN pairs Mon..Sun, same order as Oraimo)
    x, y = SUBS['top']
    face.rec(fk.K_TIMEDATE, fk.SRC_MONTHDAY, int(x - 5 * DW / 2), int(y - 30), params=[date_font])
    cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']; en = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    first = None
    for c, e in zip(cn, en):
        r1 = face.add_image(glyph(c, 64, 22, 17, GOLD, fpath=CJK)); r2 = face.add_image(glyph(e, 64, 22, 17, GOLD, 'B.ttf'))
        first = r1 if first is None else first
    face.rec(fk.K_IMGLIST, fk.SRC_WEEKDAY, int(x - 32), int(y + 4), params=[first])
    global WEEKDAY_SAT; WEEKDAY_SAT = first + 11          # EN 'SAT' (pairs CN/EN, Mon..Sun)

    # left: steps, right: heart rate (centred numbers)
    x, y = SUBS['left'];  face.rec(fk.K_DATA, fk.SRC_STEPS, int(x), int(y - 14), params=[num_font, fk.ALIGN_CENTER])
    # right: weather icon (13 images) + temperature
    x, y = SUBS['right']
    wids = [face.add_image(weather_icon(k)) for k in WEATHER]
    face.rec(fk.K_WEATHER, fk.SRC_WEATHER, int(x - 23), int(y - 44), params=[wids[0]])
    face.rec(fk.K_DATA, fk.SRC_TEMP, int(x), int(y + 2), params=[temp_font, fk.ALIGN_CENTER])
    global WEATHER_SUNNY; WEATHER_SUNNY = wids[1]

    # bottom: battery level ring (11 images: 0..10 segments)
    x, y = SUBS['bottom']
    ids = [face.add_image(battery_ring(k)) for k in range(11)]
    face.rec(fk.K_LEVEL, fk.SRC_BATTERY, int(x - 56), int(y - 56), params=[ids[0]])

    # hands: own hour/minute hands (tile format 0x40e), template seconds hand
    global HAND_IMGS
    HAND_IMGS = {'hour': pill_hand(HOUR), 'minute': pill_hand(MINUTE)}
    face.rec(fk.K_HAND, fk.SRC_HOUR, HOUR['x'], HOUR['y'], 233, 233, params=[face.add_hand(HAND_IMGS['hour'])])
    face.rec(fk.K_HAND, fk.SRC_MIN, MINUTE['x'], MINUTE['y'], 233, 233, params=[face.add_hand(HAND_IMGS['minute'])])
    sec = fk.copy_resource(t, 48)
    face.rec(fk.K_HAND, fk.SRC_SEC, 215, 12, 233, 233, params=[face.add_raw(*sec)])
    HAND_IMGS['second'] = fk.decode_hand(sec[3], rows=10)

    # preview (simulated: 10:08:36, Sun 11/08, 8520 steps, sunny 24°C, battery 70%)
    pv = render_preview(bg, face, date_font, num_font, temp_font)
    face.preview(pv)
    # the preview record must come right after the background, like Oraimo files
    face.recs.insert(1, face.recs.pop())

    out = face.build()
    open(os.path.join(HERE, 'meridian-gold.bin'), 'wb').write(out)
    pv.save(os.path.join(HERE, 'preview.png'))
    print('meridian-gold.bin', len(out), 'bytes,', len(face.res), 'graphics,', len(face.recs), 'elements')

def render_preview(bg, face, date_font, num_font, temp_font):
    im = bg.convert('RGBA')
    def text(fid, s_, x, y, center=False):
        m = dict(face.fonts[fid]); ims = [face_img[m[ord(ch)]] for ch in s_]
        tw = sum(i.width for i in ims); x = x - tw // 2 if center else x
        for i in ims: im.alpha_composite(i, (x, y)); x += i.width
    x, y = SUBS['top'];   text(date_font, '11/08', int(x - 5 * 15 / 2), int(y - 30))
    im.alpha_composite(face_img[WEEKDAY_SAT + 2], (int(x - 32), int(y + 4)))          # SUN
    x, y = SUBS['left'];  text(num_font, '8520', int(x), int(y - 14), True)
    x, y = SUBS['right']; im.alpha_composite(face_img[WEATHER_SUNNY], (int(x - 23), int(y - 44)))
    text(temp_font, '24C', int(x), int(y + 2), True)
    x, y = SUBS['bottom']; im.alpha_composite(battery_ring(7), (int(x - 56), int(y - 56)))
    # hands rotated about their pivots exactly as the watch does
    for name, angle, pivot in (('hour', (10 + 8/60) * 30, HOUR['pivot']), ('minute', (8 + 36/60) * 6, MINUTE['pivot']),
                               ('second', 36 * 6, (18, 228))):
        layer = Image.new('RGBA', (W, W), (0, 0, 0, 0))
        layer.alpha_composite(HAND_IMGS[name], (int(C - pivot[0]), int(C - pivot[1])))
        im.alpha_composite(layer.rotate(-angle, resample=Image.BICUBIC, center=(C, C)))
    return im.convert('RGB')

face_img = {}; WEEKDAY_SAT = None; WEATHER_SUNNY = None; HAND_IMGS = {}
_orig_add = fk.Face.add_image
def _track(self, img, alpha=True):
    rid = _orig_add(self, img, alpha); face_img[rid] = img.convert('RGBA'); return rid
fk.Face.add_image = _track

if __name__ == '__main__':
    main()
