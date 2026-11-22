import sys, struct
from itertools import groupby
sys.path.insert(0, '.')
from tbui import entries
a = open(sys.argv[1], 'rb').read()
rows = [(i, fmt, w, h) for i, fmt, w, h, off in entries(a)]
for k, g in groupby(rows, key=lambda r: (r[1], r[2], r[3])):
    g = list(g); print(f"ids {g[0][0]:3}-{g[-1][0]:3}  count {len(g):3}  fmt {hex(k[0])}  {k[1]}x{k[2]}")
