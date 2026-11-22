import sys, itertools
sys.path.insert(0, '.')
from tbui import entries
from pa_generic import tokens, render
a = open(sys.argv[1], 'rb').read()
E = {e[0]: e for e in entries(a)}
i, fmt, w, h, off = E[int(sys.argv[2])]
m, toks, end = tokens(a, off)
print('tokens', len(toks), 'idx', sum(t[0]=='idx' for t in toks), 'parsed end ok?', end)
def rough(pix):
    s = 0; n = 0
    for y in range(0, h, 3):
        row = pix[y*w:(y+1)*w]
        for x in range(1, w):
            c1, c2 = row[x-1][1], row[x][1]
            s += abs((c1>>11)-(c2>>11)) + abs(((c1>>5)&63)-((c2>>5)&63))/2 + abs((c1&31)-(c2&31)); n += 1
    return s/n
cands = {'zero-cache(baseline)': lambda c: 127, 'ring': 'ring', 'low7': lambda c: c & 127,
         'mod127': lambda c: c % 127, 'xorfold': lambda c: (c ^ (c >> 7) ^ (c >> 14)) & 127,
         'hi7': lambda c: c >> 9}
for A, B, C in itertools.product((1,3,5,7,11,13), repeat=3):
    cands[f'rgb {A},{B},{C}'] = (lambda c, A=A, B=B, C=C: ((c>>11)*A + ((c>>5)&63)*B + (c&31)*C) & 127)
    cands[f'rgb8 {A},{B},{C},a11'] = (lambda c, A=A, B=B, C=C: (((c>>11)<<3)*A + (((c>>5)&63)<<2)*B + ((c&31)<<3)*C + 255*11) & 127)
for A, B in itertools.product(range(1, 16), repeat=2):
    cands[f'bytes {A},{B}'] = (lambda c, A=A, B=B: ((c & 255)*A + (c >> 8)*B) & 127)
res = sorted((rough(render(m, toks, f)), k) for k, f in cands.items())
for r, k in res[:8]: print(f'{r:7.3f}  {k}')
print('baseline', [r for r, k in res if k.startswith('zero')])
from pa_generic import render_delta
for lay in ((2,3,2),(3,2,2),(2,2,3)):
    print('delta', lay, round(rough(render_delta(m, toks, lay)),3))
