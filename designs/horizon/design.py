#!/usr/bin/env python3
"""Horizon — analog dusk face: night sky fading into a warm horizon behind a mountain silhouette.
   sky (below 12): weather icon + temperature · 3 o'clock: weekday + MM/DD · 9 o'clock: steps
   bottom: battery as a 10-segment golden arc along the edge · cream dauphine hands, coral seconds hand.
Run:  venv/bin/python -I designs/horizon/design.py   -> horizon.bin + preview.png + weather_icons.png"""
import math, os, random, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import facekit as fk

NAME = 'horizon'
TEMPLATE = os.path.join(ROOT, 'samples/from_capture/store_face_373284.bin')   # header only
UB = '/usr/share/fonts/truetype/ubuntu/Ubuntu-'
CJK = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
SS = 4
W = 466; C = W / 2

CREAM = (250, 236, 210); CREAM_DARK = (196, 176, 140); GOLD = (255, 190, 60); GOLD_DIM = (78, 56, 34)
CORAL = (255, 112, 84); MUTED = (170, 160, 185); PLATE = (16, 14, 30); PLATE_EDGE = (70, 60, 95)
CLOUD = (225, 225, 236); BLUE = (110, 185, 255); SUN = (255, 196, 30); WHITE = (245, 245, 245)
SKY_TOP = (8, 10, 32); SKY_MID = (48, 26, 72); SKY_GLOW = (232, 120, 70)
HORIZON_Y = 330

STEPS_C = (116, 233); DATE_C = (350, 233); WX_C = (233, 128)
ARC_R_OUT, ARC_R_IN = 214, 200; ARC_FROM, ARC_TO = 132, 228          # degrees, 0 = 12 o'clock, clockwise

def font(name, size): return ImageFont.truetype(UB + name, size * SS)
def big(w, h): return Image.new('RGBA', (w * SS, h * SS), (0, 0, 0, 0))
def down(im): return im.resize((im.width // SS, im.height // SS), Image.LANCZOS)
def lerp(a, b, t): return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
def polar(r, deg, s=1):  # deg: 0 = up, clockwise
    a = math.radians(deg); return ((C + r * math.sin(a)) * s, (C - r * math.cos(a)) * s)

# ---------------------------------------------------------------- background
def background():
    s = SS
    sky = Image.new('RGBA', (W, W))
    px = sky.load()
    for y in range(W):
        if y < 200: col = lerp(SKY_TOP, SKY_MID, y / 200)
        elif y < HORIZON_Y: col = lerp(SKY_MID, SKY_GLOW, ((y - 200) / (HORIZON_Y - 200)) ** 1.6)
        else: col = SKY_GLOW
        for x in range(W): px[x, y] = col + (255,)
    im = sky.resize((W * s, W * s), Image.BICUBIC)
    d = ImageDraw.Draw(im)
    # stars (fixed seed so every build is identical)
    rnd = random.Random(7)
    for _ in range(70):
        x, y = rnd.uniform(40, 426), rnd.uniform(40, 230)
        if math.hypot(x - C, y - C) > 215: continue
        r = rnd.choice((0.6, 0.8, 1.0, 1.3)); b = rnd.randint(150, 255)
        d.ellipse([(x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s], fill=(b, b, min(255, b + 20)))
    # mountains: far ridge (plum) and near ridge (near black)
    far = [(0, 340), (60, 318), (110, 330), (165, 300), (210, 322), (262, 292), (318, 326), (372, 304), (420, 324), (466, 312), (466, 466), (0, 466)]
    near = [(0, 360), (48, 350), (96, 368), (150, 344), (205, 366), (250, 352), (300, 372), (352, 350), (404, 368), (466, 352), (466, 466), (0, 466)]
    d.polygon([(x * s, y * s) for x, y in far], fill=(46, 24, 52))
    d.polygon([(x * s, y * s) for x, y in near], fill=(14, 10, 20))
    # minute track: small dots, hour markers: tapered cream batons, double baton at 12
    for t in range(60):
        if t % 5 == 0: continue
        x, y = polar(222, t * 6, s); r = 1.4 * s
        d.ellipse([x - r, y - r, x + r, y + r], fill=MUTED)
    for h in range(12):
        deg = h * 30
        if 120 < deg < 240: continue                     # bottom hours are the battery arc
        if h in (3, 9): r1, r2 = 196, 216
        else: r1, r2 = 190, 216
        offs = (-4, 4) if h == 0 else (0,)
        for o in offs:
            a = math.radians(deg); ox, oy = o * math.cos(a), o * math.sin(a)
            p_out = polar(r2, deg); p_in = polar(r1, deg)
            nx, ny = math.cos(a), math.sin(a)                       # perpendicular
            wo, wi = 3.2, 1.6
            poly = [(p_out[0] + ox + nx * wo, p_out[1] + oy + ny * wo), (p_out[0] + ox - nx * wo, p_out[1] + oy - ny * wo),
                    (p_in[0] + ox - nx * wi, p_in[1] + oy - ny * wi), (p_in[0] + ox + nx * wi, p_in[1] + oy + ny * wi)]
            d.polygon([(x * s, y * s) for x, y in poly], fill=CREAM)
    # plates for steps and date
    for (cx, cy), wdt in ((STEPS_C, 104), (DATE_C, 104)):
        d.rounded_rectangle([(cx - wdt / 2) * s, (cy - 30) * s, (cx + wdt / 2) * s, (cy + 30) * s], radius=14 * s,
                            fill=PLATE + (235,), outline=PLATE_EDGE, width=2 * s)
    # steps icon: small trail marker (flag on a hill)
    cx, cy = STEPS_C
    d.polygon([((cx - 13) * s, (cy - 10) * s), ((cx - 3) * s, (cy - 20) * s), ((cx + 6) * s, (cy - 13) * s),
               ((cx + 13) * s, (cy - 10) * s)], fill=GOLD)
    d.line([((cx - 3) * s, (cy - 20) * s), ((cx - 3) * s, (cy - 27) * s)], fill=CREAM, width=int(1.5 * s))
    d.polygon([((cx - 3) * s, (cy - 27) * s), ((cx + 5) * s, (cy - 24.5) * s), ((cx - 3) * s, (cy - 22) * s)], fill=CORAL)
    # battery: small bolt above the arc
    bx, by = C, 412
    bolt = [(bx + 2, by - 9), (bx - 5, by + 1), (bx - 1, by + 1), (bx - 3, by + 9), (bx + 5, by - 1), (bx + 1, by - 1)]
    d.polygon([(x * s, y * s) for x, y in bolt], fill=GOLD)
    return down(im).convert('RGB')

# ---------------------------------------------------------------- battery arc (11 images)
ARC_BOX = (64, 350, 402, 450)       # x0, y0, x1, y1 on screen

def battery_arc(level):
    x0, y0, x1, y1 = ARC_BOX; w, h = x1 - x0, y1 - y0
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    seg = 10; span = (ARC_TO - ARC_FROM) / seg; gap = 2.2
    for k in range(seg):
        a0 = ARC_TO - k * span - gap / 2; a1 = ARC_TO - (k + 1) * span + gap / 2       # fills left -> right
        pts = [polar(ARC_R_OUT, a0 + (a1 - a0) * i / 10) for i in range(11)] + \
              [polar(ARC_R_IN, a1 - (a1 - a0) * i / 10) for i in range(11)]
        col = GOLD if k < level else GOLD_DIM
        d.polygon([((x - x0) * s, (y - y0) * s) for x, y in pts], fill=col)
    return down(im)

# ---------------------------------------------------------------- weather icons (13, Oraimo order)
WEATHER = ['partly-cloudy', 'sunny', 'light-snow', 'rain', 'heavy-snow', 'cloudy', 'fog', 'wind',
           'heavy-rain', 'sleet', 'light-rain', 'thunder', 'unknown']

def weather_icon(kind, w=46, h=38):
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    def cloud(ox=0, oy=0, col=CLOUD, sc=1.0):
        def e(a, b, c, dd): d.ellipse([(ox + a*sc)*s, (oy + b*sc)*s, (ox + c*sc)*s, (oy + dd*sc)*s], fill=col)
        e(6, 12, 22, 28); e(14, 4, 34, 24); e(26, 11, 42, 27)
        d.rectangle([(ox + 14*sc)*s, (oy + 18*sc)*s, (ox + 34*sc)*s, (oy + 28*sc)*s], fill=col)
    def sun(cx, cy, r):
        for k in range(8):
            a = k * math.pi / 4
            d.line([((cx + (r + 3)*math.cos(a))*s, (cy + (r + 3)*math.sin(a))*s),
                    ((cx + (r + 7)*math.cos(a))*s, (cy + (r + 7)*math.sin(a))*s)], fill=SUN, width=2*s)
        d.ellipse([(cx - r)*s, (cy - r)*s, (cx + r)*s, (cy + r)*s], fill=SUN)
    def drops(xs, y0=30):
        for x in xs: d.line([(x*s, y0*s), ((x - 2)*s, (y0 + 6)*s)], fill=BLUE, width=2*s)
    def flakes(xs, y0=33):
        for x in xs:
            for a in (0, 60, 120):
                r = math.radians(a)
                d.line([((x - 3*math.cos(r))*s, (y0 - 3*math.sin(r))*s), ((x + 3*math.cos(r))*s, (y0 + 3*math.sin(r))*s)], fill=WHITE, width=s)
    if kind == 'sunny': sun(23, 19, 9)
    elif kind == 'partly-cloudy': sun(31, 14, 5); cloud(-2, 8, sc=0.85)
    elif kind == 'cloudy': cloud(0, 3)
    elif kind == 'fog':
        for k, y in enumerate((10, 17, 24, 31)): d.line([((6 + 4*(k % 2))*s, y*s), ((40 - 4*(k % 2))*s, y*s)], fill=CLOUD, width=3*s)
    elif kind == 'wind':
        for y, l in ((11, 24), (19, 30), (27, 18)):
            d.line([(6*s, y*s), ((6 + l)*s, y*s)], fill=CLOUD, width=3*s)
            d.arc([((6 + l - 5)*s), ((y - 6)*s), ((6 + l + 5)*s), (y*s)], 270, 90, fill=CLOUD, width=3*s)
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
            d.text((24*s - (bb[2] - bb[0]) / 2 - bb[0], 15*s - (bb[3] - bb[1]) / 2 - bb[1]), '?', font=f, fill=(60, 60, 70))
    return down(im)

# ---------------------------------------------------------------- glyphs
def glyph(ch, w, h, size, colour, fname='M.ttf', fpath=None):
    im = big(w, h); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(fpath, size * SS) if fpath else font(fname, size)
    bb = d.textbbox((0, 0), ch, font=f)
    d.text(((w*SS - (bb[2] - bb[0])) / 2 - bb[0], (h*SS - (bb[3] - bb[1])) / 2 - bb[1]), ch, font=f, fill=colour)
    return down(im)

# ---------------------------------------------------------------- hands
# rotation point inside the picture = (233 - x, 233 - y + 7)   (see README)
HOUR = dict(w=18, h=158, x=224, y=117, length=100)
MINUTE = dict(w=18, h=241, x=224, y=34, length=182)
SECOND = dict(w=36, h=278, x=215, y=12, length=205, tail=40)
def pivot(spec): return (233 - spec['x'], 233 - spec['y'] + 7)

def dauphine(spec):
    w, h = spec['w'], spec['h']; px, py = pivot(spec); L = spec['length']
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    tip = (px, py - L); sl = (px - 7.5, py - L * 0.18); sr = (px + 7.5, py - L * 0.18)
    bl = (px - 3.5, py + 14); br = (px + 3.5, py + 14); bc = (px, py + 14)
    d.polygon([(x * s, y * s) for x, y in (tip, sl, bl, bc)], fill=CREAM)          # lit facet
    d.polygon([(x * s, y * s) for x, y in (tip, sr, br, bc)], fill=CREAM_DARK)     # shaded facet
    d.ellipse([(px - 7) * s, (py - 7) * s, (px + 7) * s, (py + 7) * s], fill=CREAM)
    return down(im)

def seconds_hand(spec):
    w, h = spec['w'], spec['h']; px, py = pivot(spec)
    im = big(w, h); d = ImageDraw.Draw(im); s = SS
    d.rounded_rectangle([(px - 1.3) * s, (py - spec['length']) * s, (px + 1.3) * s, (py + spec['tail']) * s], radius=1.3 * s, fill=CORAL)
    ty = py + spec['tail'] - 6
    d.ellipse([(px - 6) * s, (ty - 6) * s, (px + 6) * s, (ty + 6) * s], fill=CORAL)               # counterweight
    d.ellipse([(px - 6.5) * s, (py - 6.5) * s, (px + 6.5) * s, (py + 6.5) * s], fill=CORAL)       # cap
    d.ellipse([(px - 2.5) * s, (py - 2.5) * s, (px + 2.5) * s, (py + 2.5) * s], fill=(30, 20, 30))
    return down(im)

# ---------------------------------------------------------------- build
def main():
    face = fk.Face(TEMPLATE)
    bg = background(); face.background(bg)
    imgs = {}
    def add(img):
        rid = face.add_image(img); imgs[rid] = img.convert('RGBA'); return rid

    def font_from(glyphs):
        mapping = [(ord(ch), add(im)) for ch, im in glyphs.items()]
        face.fonts.append(mapping); return len(face.fonts) - 1

    DW, DH = 14, 22
    date_font = font_from({**{str(n): glyph(str(n), DW, DH, 19, CREAM) for n in range(10)},
                           '/': glyph('/', DW, DH, 19, GOLD), '-': glyph('-', DW, DH, 19, GOLD)})
    NW, NH = 16, 26
    num_font = font_from({**{str(n): glyph(str(n), NW, NH, 23, CREAM, 'B.ttf') for n in range(10)},
                          '.': glyph('.', NW, NH, 23, CREAM, 'B.ttf'), '_': glyph('-', NW, NH, 23, MUTED, 'B.ttf'),
                          '-': glyph('-', NW, NH, 23, MUTED, 'B.ttf')})
    TW, TH = 14, 22
    temp_font = font_from({**{str(n): glyph(str(n), TW, TH, 20, CREAM, 'B.ttf') for n in range(10)},
                           '/': glyph('-', TW, TH, 20, CREAM, 'B.ttf'), '-': glyph('-', TW, TH, 20, CREAM, 'B.ttf'),
                           'C': glyph('°C', 24, TH, 16, MUTED, 'B.ttf'), 'F': glyph('°F', 24, TH, 16, MUTED, 'B.ttf'),
                           '_': glyph('-', TW, TH, 20, MUTED, 'B.ttf'), '%': glyph('%', TW, TH, 16, MUTED, 'B.ttf'),
                           '.': glyph('.', TW, TH, 20, CREAM, 'B.ttf')})

    # 3 o'clock: weekday (14 imgs CN/EN pairs Mon..Sun) over MM/DD
    cx, cy = DATE_C
    cn = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']; en = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']
    wk = []
    for c, e in zip(cn, en):
        wk.append(add(glyph(c, 60, 20, 15, GOLD, fpath=CJK))); wk.append(add(glyph(e, 60, 20, 15, GOLD, 'B.ttf')))
    face.rec(fk.K_IMGLIST, fk.SRC_WEEKDAY, int(cx - 30), int(cy - 25), params=[wk[0]])
    face.rec(fk.K_TIMEDATE, fk.SRC_MONTHDAY, int(cx - 5 * DW / 2), int(cy - 2), params=[date_font])

    # 9 o'clock: steps (icon is in the background)
    face.rec(fk.K_DATA, fk.SRC_STEPS, STEPS_C[0], STEPS_C[1] - 5, params=[num_font, fk.ALIGN_CENTER])

    # sky: weather + temperature
    wx = [add(weather_icon(k)) for k in WEATHER]
    face.rec(fk.K_WEATHER, fk.SRC_WEATHER, WX_C[0] - 23, WX_C[1] - 38, params=[wx[0]])
    face.rec(fk.K_DATA, fk.SRC_TEMP, WX_C[0], WX_C[1] + 4, params=[temp_font, fk.ALIGN_CENTER])

    # bottom: battery arc
    arcs = [add(battery_arc(k)) for k in range(11)]
    face.rec(fk.K_LEVEL, fk.SRC_BATTERY, ARC_BOX[0], ARC_BOX[1], params=[arcs[0]])

    # hands
    hands = {'hour': dauphine(HOUR), 'minute': dauphine(MINUTE), 'second': seconds_hand(SECOND)}
    for name, spec, src in (('hour', HOUR, fk.SRC_HOUR), ('minute', MINUTE, fk.SRC_MIN), ('second', SECOND, fk.SRC_SEC)):
        face.rec(fk.K_HAND, src, spec['x'], spec['y'], 233, 233, params=[face.add_hand(hands[name])])

    # preview: 10:09:32, Sun 11/08, 6240 steps, partly cloudy 21 °C, battery 80 %
    pv = bg.convert('RGBA')
    def text(fid, s_, x, y, center=False):
        m = dict(face.fonts[fid]); ims = [imgs[m[ord(ch)]] for ch in s_]
        tw = sum(i.width for i in ims); x = x - tw // 2 if center else x
        for i in ims: pv.alpha_composite(i, (int(x), int(y))); x += i.width
    pv.alpha_composite(imgs[wk[13]], (int(cx - 30), int(cy - 25)))
    text(date_font, '11/08', cx - 5 * DW / 2, cy - 2)
    text(num_font, '6240', STEPS_C[0], STEPS_C[1] - 5, True)
    pv.alpha_composite(imgs[wx[0]], (WX_C[0] - 23, WX_C[1] - 38)); text(temp_font, '21C', WX_C[0], WX_C[1] + 4, True)
    pv.alpha_composite(imgs[arcs[8]], (ARC_BOX[0], ARC_BOX[1]))
    for name, spec, ang in (('hour', HOUR, (10 + 9/60) * 30), ('minute', MINUTE, (9 + 32/60) * 6), ('second', SECOND, 32 * 6)):
        layer = Image.new('RGBA', (W, W), (0, 0, 0, 0)); p = pivot(spec)
        layer.alpha_composite(hands[name], (int(C - p[0]), int(C - p[1])))
        pv.alpha_composite(layer.rotate(-ang, resample=Image.BICUBIC, center=(C, C)))
    pv = pv.convert('RGB')
    face.preview(pv); face.recs.insert(1, face.recs.pop())

    out = face.build()
    open(os.path.join(HERE, NAME + '.bin'), 'wb').write(out)
    pv.save(os.path.join(HERE, 'preview.png'))
    sheet = Image.new('RGBA', (13 * 56 + 10, 52), (20, 18, 30, 255))
    for k, rid in enumerate(wx): sheet.alpha_composite(imgs[rid], (10 + k * 56, 7))
    sheet.save(os.path.join(HERE, 'weather_icons.png'))
    print(f'{NAME}.bin', len(out), 'bytes,', len(face.res), 'graphics,', len(face.recs), 'elements')

if __name__ == '__main__':
    main()
