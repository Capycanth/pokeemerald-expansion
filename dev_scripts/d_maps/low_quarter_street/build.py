"""Builder for the Low Quarter streets: LAYOUT_LOW_QUARTER_NIGHT (40x40) and its tileset pair
gTileset_D_LowQuarterStreet (primary) + gTileset_D_LowQuarterNight (secondary), plus the day twin
LAYOUT_LOW_QUARTER_DAY, whose tilesets reuse the same tiles and metatiles under day palettes
(gTileset_D_LowQuarterStreetDay + gTileset_D_LowQuarterDay).

Re-runnable: writes both tilesets and the layout from scratch every run.
Run order: extract.py (cut borrowed props from vanilla maps) -> build.py.

Most of the art is drawn here procedurally:
  * Buildings are drawn in *roles* (wall shades, mortar, trim, dark glass, lit glass, roof), so one
    tile serves every colour scheme; the scheme is just the palette slot (brick, stucco, clapboard,
    brownstone, corrugated metal).
  * Ground (asphalt, sidewalk, alley, yard) is drawn in shades and lit by baked lamp pools, as in the
    warehouse: each 8x8 quadrant takes a light stage in 1/4 steps, picks the lit+mid or mid+dark ground
    palette, and Bayer-dithers between the two levels inside it.
  * Props (lamps, trash cans, dumpster, stalls, fences, yard clutter) sit in the top layer with their
    own palettes, lit or dark depending on the light at their base.

Palette slots: 0 ground lit+mid, 1 ground mid+dark, 2 brick, 3 stucco, 4 clapboard, 5 brownstone
(primary); 6 corrugated warehouse, 7 metal props dark, 8 metal props lit, 9 warm props dark,
10 warm props lit, 11 lamp glow, 12 neon (secondary).
A day version only needs new palettes: tiles and metatiles are palette-independent.
"""
import os, sys, math, random, struct, pickle, colorsys, re, json
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'low_quarter_warehouse'))
from tl import ROOT, write_pal, flip

OUT_P = ROOT + '/data/tilesets/primary/d_low_quarter_street'
OUT_S = ROOT + '/data/tilesets/secondary/d_low_quarter_night'
OUT_LY = ROOT + '/data/layouts/LowQuarterNight'
# Day: the same tiles and metatiles under daytime palettes (only palette files are written)
OUT_P_DAY = ROOT + '/data/tilesets/primary/d_low_quarter_street_day'
OUT_S_DAY = ROOT + '/data/tilesets/secondary/d_low_quarter_day'
OUT_LY_DAY = ROOT + '/data/layouts/LowQuarterDay'
W, H = 40, 40
PXW, PXH = W*16, H*16

def q(c): return tuple((max(0, min(255, int(round(v)))) >> 3) << 3 for v in c)

# ====================================================================== city plan (cells)
# Rows: band A (roofs 0-1, facades 2-5) | sidewalk 6-7 | street 8-11 | sidewalk 12 |
#       band B (roofs 13-15, facades 16-19) | sidewalk 20-21 | street 22-25 | sidewalk 26 |
#       band C (roofs 27-29, facades 30-33) | sidewalk 34-35 | street 36-38 | sidewalk 39
# Columns: west blocks 0-24 | sidewalk 25 | avenue 26-29 | sidewalk 30 | east blocks 31-39
STREETS = [(8, 11, 0, 39), (22, 25, 0, 39), (36, 38, 0, 29)]        # rows y0..y1, cols x0..x1
AVENUE = (26, 29)
BANDS = {'A': (0, 1, 2, 5), 'B': (13, 15, 16, 19), 'C': (27, 29, 30, 33)}   # roof r0..r1, facade f0..f1

# Ground-floor codes: w window, b boarded, h shutter (closed shop), s lit shopfront, d door,
# D the MC's door (stoop), r roll-up door, m steel side door, g barred window
def B_(scheme, x0, x1, band, ground, fire=None, seed=0, roof=None, facade=None):
    r0, r1, f0, f1 = BANDS[band]
    if roof: r0, r1 = roof
    if facade: f0, f1 = facade
    assert len(ground) == x1 - x0 + 1, (scheme, x0, ground)
    return dict(scheme=scheme, x0=x0, x1=x1, r0=r0, r1=r1, f0=f0, f1=f1, ground=ground, fire=fire, seed=seed)

BUILDINGS = [
    # band A (top edge)
    B_('brick',  0,  5, 'A', 'bwgdwh', fire=1, seed=1),
    B_('stucco', 7, 12, 'A', 'wwdwgw', seed=2),
    B_('clap',  13, 17, 'A', 'sssdw', seed=3),
    B_('brick', 20, 24, 'A', 'wdhhw', fire=21, seed=4),
    B_('stucco', 31, 35, 'A', 'hhdww', seed=5),
    B_('clap',  36, 39, 'A', 'wbdw', seed=6),
    # band B: the MC's brownstone sits back a row, with a stoop and areaways in front (row 19)
    B_('clap',   0,  4, 'B', 'wwdbw', seed=7),
    B_('brick',  6,  9, 'B', 'ssdw', fire=7, seed=8),
    B_('brown', 10, 14, 'B', 'wwDww', seed=9, roof=(13, 14), facade=(15, 18)),
    B_('brick', 17, 21, 'B', 'wdwhh', seed=10),
    B_('stucco', 22, 24, 'B', 'gdw', seed=11),
    B_('clap',  31, 34, 'B', 'wdbw', seed=12),
    B_('brick', 36, 39, 'B', 'hhdw', seed=13),
    # band C
    B_('stucco', 0,  6, 'C', 'wgwdwbw', seed=14),
    B_('brick',  8, 12, 'C', 'sdssw', seed=15),
    B_('clap',  13, 18, 'C', 'wdwwbd', fire=15, seed=16),
    B_('brown', 20, 24, 'C', 'wwdww', seed=17),
    # the warehouse (Underground Ladder venue): sawtooth roof 27-30, corrugated wall 31-34
    B_('corr',  31, 39, 'C', 'wwrrrrwmw', seed=18, roof=(27, 30), facade=(31, 34)),
]
MC = BUILDINGS[8]
MC_DOOR = (12, 18)
STOOP = {(10, 19): 'well', (11, 19): 'well', (12, 19): 'landing', (13, 19): 'well', (14, 19): 'well', (12, 20): 'stairs'}
MC_ALLEY_FENCE = [(15, 14), (16, 14)]
YARD = (31, 35, 39, 39)                 # x0, y0, x1, y1
YARD_FENCE = [(31, y) for y in (35, 38, 39)]
YARD_GATE = [(31, 36), (31, 37)]
WAREHOUSE_DOOR = (38, 34)               # steel side door; the warp into LowQuarterWarehouse goes here

T = [['S']*W for _ in range(H)]          # S sidewalk, R road, A alley, Y yard, B building, K stoop
for y0, y1, x0, x1 in STREETS:
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1): T[y][x] = 'R'
for y in range(H):
    for x in range(AVENUE[0], AVENUE[1] + 1): T[y][x] = 'R'
BID = {}
for i, b in enumerate(BUILDINGS):
    for y in range(b['r0'], b['f1'] + 1):
        for x in range(b['x0'], b['x1'] + 1): T[y][x] = 'B'; BID[(x, y)] = i
for r0, r1, f0, f1 in BANDS.values():
    for y in range(r0, f1 + 1):
        for x in list(range(0, 25)) + list(range(31, 40)):
            if T[y][x] == 'S': T[y][x] = 'A'
for (x, y) in STOOP: T[y][x] = 'K' if STOOP[(x, y)] != 'stairs' else 'K'
for y in range(YARD[1], YARD[3] + 1):
    for x in range(YARD[0], YARD[2] + 1): T[y][x] = 'Y'

# ====================================================================== lights
# (cell x, cell y of the post's base, kind). Pools are centred just below the base.
LAMPS = [(4, 7), (13, 7), (21, 7), (34, 7),
         (8, 21), (20, 21), (35, 21),
         (5, 35), (17, 35),
         (25, 17), (30, 31), (30, 3)]
POOLS = [((x*16 + 8, y*16 + 12), 2.7*16, 1.9*16) for x, y in LAMPS]
STALLS = [(8, 6), (2, 20), (10, 34)]     # top-left of a 3x2 stall: awning row, counter row
POOLS += [((x*16 + 24, y*16 + 26), 2.1*16, 1.5*16) for x, y in STALLS]     # hanging lantern
POOLS += [((WAREHOUSE_DOOR[0]*16 + 8, WAREHOUSE_DOOR[1]*16 + 22), 2.3*16, 1.7*16)]   # wall-pack light
POOLS += [((MC_DOOR[0]*16 + 8, MC_DOOR[1]*16 + 30), 1.5*16, 1.2*16)]               # porch light

def light(x, y):
    """0 = lit, 1 = mid, 2 = dark (continuous)."""
    best = 2.0
    for (cx, cy), rx, ry in POOLS:
        d = math.hypot((x - cx)/rx, (y - cy)/ry)
        v = min(1, max(0, (d - 0.50)/0.40)) + min(1, max(0, (d - 1.00)/0.45))
        best = min(best, v)
    return best
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
def stage(qx, qy, extra=0.0):
    return min(2.0, round((light(qx*8 + 4, qy*8 + 4) + extra)*4)/4)
def px_level(s, x, y):
    base = int(s) if s < 2 else 2; f = s - base
    return base + (1 if f > 0 and BAYER[y % 4][x % 4] < f*16 else 0)

# ====================================================================== palettes
# ground: three shades (0 light, 1 base, 2 dark) of asphalt and concrete per light level, + paint
ASPH = {0: [(124, 112, 98), (102, 92, 84), (80, 72, 68)],
        1: [(74, 72, 82), (60, 59, 70), (46, 46, 58)],
        2: [(42, 44, 60), (33, 35, 49), (25, 27, 39)]}
CONC = {0: [(184, 166, 136), (156, 140, 116), (124, 112, 96)],
        1: [(108, 104, 110), (92, 89, 98), (74, 72, 82)],
        2: [(64, 66, 84), (53, 55, 73), (42, 44, 60)]}
PAINT = {0: (220, 204, 150), 1: (140, 134, 118), 2: (86, 86, 92)}
def ground_pal(levels):
    a, b = levels
    return [(0, 0, 0)] + [q(c) for c in ASPH[a] + ASPH[b] + CONC[a] + CONC[b]] + [q(PAINT[a]), q(PAINT[b])]
PAL_G0, PAL_G1 = ground_pal((0, 1)), ground_pal((1, 2))
def gidx(slot, lv, mat, shade):
    """mat 0 asphalt / 1 concrete, shade 0-2 or 3 = paint."""
    a = 0 if (slot == 0 and lv == 0) or (slot == 1 and lv == 1) else 1
    if shade == 3: return 13 + a
    return 1 + mat*6 + a*3 + shade

# building roles
W0, W1, W2, W3, MO, T0, T1, G0, G1, L0, L1, L2, R0, R1, R2 = range(1, 16)
GLASS = [(58, 74, 104), (32, 40, 62), (252, 236, 172), (232, 180, 92), (160, 104, 60)]
ROOF = [(90, 90, 104), (52, 53, 66), (22, 22, 30)]
SCHEMES = {
    'brick':  dict(slot=2, wall=[(106, 64, 60), (88, 52, 52), (70, 42, 46), (52, 33, 40)], mortar=(46, 42, 52), trim=[(122, 118, 124), (78, 72, 84)]),
    'stucco': dict(slot=3, wall=[(106, 112, 126), (88, 94, 110), (72, 78, 94), (56, 60, 78)], mortar=(46, 50, 66), trim=[(140, 140, 142), (92, 92, 104)]),
    'clap':   dict(slot=4, wall=[(100, 98, 72), (82, 80, 60), (66, 64, 50), (48, 46, 40)], mortar=(38, 36, 34), trim=[(118, 106, 86), (72, 62, 54)]),
    'brown':  dict(slot=5, wall=[(116, 82, 66), (98, 68, 56), (80, 56, 48), (62, 44, 40)], mortar=(50, 40, 40), trim=[(140, 126, 110), (88, 74, 66)]),
    'corr':   dict(slot=6, wall=[(98, 110, 112), (80, 92, 96), (62, 72, 80), (44, 52, 62)], mortar=(104, 66, 48), trim=[(150, 132, 80), (84, 76, 66)],
                   roof=[(96, 102, 112), (60, 64, 76), (26, 28, 36)]),
}
def scheme_pal(s):
    S = SCHEMES[s]
    return [(0, 0, 0)] + [q(c) for c in S['wall'] + [S['mortar']] + S['trim'] + GLASS + S.get('roof', ROOF)]

# ====================================================================== ground drawing
rng = random.Random(1234)
def periodic_noise(seed, p_light, p_dark, period=16):
    r = random.Random(seed); g = [[1]*period for _ in range(period)]
    for y in range(period):
        for x in range(period):
            v = r.random()
            g[y][x] = 0 if v < p_light else 2 if v < p_light + p_dark else 1
    return g
ATEX = periodic_noise(3, 0.07, 0.14)                 # asphalt grain
ALTEX = periodic_noise(4, 0.05, 0.30)                # alley: grimier
CTEX = periodic_noise(5, 0.10, 0.06)                 # sidewalk slabs
for i in range(16): CTEX[15][i] = 2; CTEX[i][15] = 2; CTEX[0][i] = 0 if CTEX[0][i] == 1 else CTEX[0][i]
YTEX = periodic_noise(6, 0.06, 0.12, 32)             # yard concrete, 32 px slabs
for i in range(32): YTEX[31][i] = 2; YTEX[i][31] = 2

GMAT = [[0]*PXW for _ in range(PXH)]; GSH = [[1]*PXW for _ in range(PXH)]; GEXTRA = {}
def cell_t(x, y): return T[y][x] if 0 <= x < W and 0 <= y < H else 'B'
for cy in range(H):
    for cx in range(W):
        t = T[cy][cx]
        for j in range(16):
            for i in range(16):
                x, y = cx*16 + i, cy*16 + j
                if t == 'R':   m, s = 0, ATEX[j][i]
                elif t == 'A': m, s = 0, ALTEX[j][i]
                elif t == 'Y': m, s = 1, YTEX[y % 32][x % 32]
                else:          m, s = 1, CTEX[j][i]
                GMAT[y][x] = m; GSH[y][x] = s
        if t == 'S':           # curbs where the sidewalk meets a road
            if cell_t(cx, cy + 1) == 'R':
                for i in range(16): GMAT[cy*16 + 13][cx*16 + i], GSH[cy*16 + 13][cx*16 + i] = 1, 0
                for i in range(16):
                    for j in (14, 15): GMAT[cy*16 + j][cx*16 + i], GSH[cy*16 + j][cx*16 + i] = 0, 2
            if cell_t(cx, cy - 1) == 'R':
                for i in range(16): GMAT[cy*16][cx*16 + i], GSH[cy*16][cx*16 + i] = 0, 2; GSH[cy*16 + 1][cx*16 + i] = 0
            if cell_t(cx + 1, cy) == 'R':
                for j in range(16): GSH[cy*16 + j][cx*16 + 14] = 0; GMAT[cy*16 + j][cx*16 + 15], GSH[cy*16 + j][cx*16 + 15] = 0, 2
            if cell_t(cx - 1, cy) == 'R':
                for j in range(16): GMAT[cy*16 + j][cx*16], GSH[cy*16 + j][cx*16] = 0, 2; GSH[cy*16 + j][cx*16 + 1] = 0
        if t == 'A':           # alleys sit in the buildings' shadow
            for j in range(16):
                for i in range(16):
                    x, y = cx*16 + i, cy*16 + j
                    e = 0.75
                    if cell_t(cx - 1, cy) == 'B' and i < 4: e = 1.2
                    if cell_t(cx + 1, cy) == 'B' and i > 11: e = 1.2
                    GEXTRA[(x, y)] = e

def paint_px(x, y): GMAT[y][x] = 0; GSH[y][x] = 3
# centre lines: dashed, 8 on / 8 off
for y0, y1, x0, x1 in STREETS:
    if y1 - y0 == 3:
        yy = (y0 + 2)*16 - 1
        for x in range(x0*16, (x1 + 1)*16):
            cx = x // 16
            if AVENUE[0] - 1 <= cx <= AVENUE[1] + 1: continue
            if (x % 16) < 9 and (x % 16) > 0:
                paint_px(x, yy); paint_px(x, yy + 1)
xx = (AVENUE[0] + 2)*16 - 1
for y in range(PXH):
    cy = y // 16
    if any(s[0] - 1 <= cy <= s[1] + 1 for s in STREETS): continue
    if 0 < (y % 16) < 9: paint_px(xx, y); paint_px(xx + 1, y)
# crosswalks across the avenue (vertical bars) and across the streets beside the avenue (horizontal bars)
for y0, y1, x0, x1 in STREETS[:2]:
    for cy in (y0 - 1, y1 + 1):
        for x in range(AVENUE[0]*16 + 2, (AVENUE[1] + 1)*16 - 2):
            if (x % 8) < 4:
                for j in range(2, 14): paint_px(x, cy*16 + j)
    for cx in (AVENUE[0] - 1, AVENUE[1] + 1):
        for y in range(y0*16 + 2, (y1 + 1)*16 - 2):
            if (y % 8) < 4:
                for i in range(2, 14): paint_px(cx*16 + i, y)
for cx in (AVENUE[0] - 1,):              # T-junction with street 3
    for y in range(36*16 + 2, 39*16 - 2):
        if (y % 8) < 4:
            for i in range(2, 14): paint_px(cx*16 + i, y)
# stop lines
def blob(cx, cy, r, mat, shade, seed, ring=None, sx=1.0):
    rr = random.Random(seed)
    for y in range(int(cy - r - 2), int(cy + r + 3)):
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            d = math.hypot((x - cx)*sx, y - cy) + rr.uniform(-1.2, 1.2)
            if d < r:
                GMAT[y][x] = mat; GSH[y][x] = shade
                if ring is not None and d > r - 1.5: GSH[y][x] = ring
def manhole(cx, cy):
    for y in range(cy - 6, cy + 7):
        for x in range(cx - 7, cx + 8):
            d = math.hypot((x - cx)*0.85, y - cy)
            if d < 6.2:
                GMAT[y][x] = 0; GSH[y][x] = 2 if d > 5.0 or (d < 4.2 and (x + y) % 3 == 0) else 0 if d > 4.2 else 1
def drain(cx, cy):          # curb storm drain: dark slots
    for y in range(cy, cy + 3):
        for x in range(cx, cx + 10):
            GMAT[y][x] = 0; GSH[y][x] = 2 if (x - cx) % 3 != 2 else 1
def crack(x, y, n, seed, dx=1, dy=0):
    rr = random.Random(seed)
    for _ in range(n):
        GSH[y][x] = 2
        if dx: x += dx; y += rr.choice((-1, 0, 0, 1))
        else: y += dy; x += rr.choice((-1, 0, 0, 1))
def puddle(cx, cy, r, seed):       # dark sky reflected in water: concrete shades on asphalt
    blob(cx, cy, r, 1, 1, seed, ring=2, sx=0.55)
    rr = random.Random(seed + 9)
    for _ in range(3):
        x, y = cx + rr.randint(-int(r*1.2), int(r*1.2)), cy + rr.randint(-1, 1)
        if GMAT[y][x] == 1: GSH[y][x] = 0
def litter(x, y, seed):            # crumpled paper
    rr = random.Random(seed)
    for j in range(3):
        for i in range(4):
            if rr.random() < 0.8: GMAT[y + j][x + i] = 1; GSH[y + j][x + i] = 0 if (i + j) % 3 else 3
    for i in range(4): GSH[y + 3][x + i] = 2

for cx, cy in [(6*16 + 8, 9*16 + 8), (28*16 + 8, 17*16 + 8), (15*16 + 8, 23*16 + 8), (34*16, 10*16 + 8), (11*16, 37*16 + 8)]:
    manhole(cx, cy)
for cx, cy in [(2*16 + 3, 8*16), (17*16 + 3, 22*16), (32*16 + 3, 22*16), (20*16 + 3, 36*16), (9*16 + 3, 11*16 + 13), (23*16 + 3, 25*16 + 13)]:
    drain(cx, cy)
for args in [(3*16, 10*16 + 3, 26, 1), (18*16, 23*16 + 6, 30, 2), (33*16, 24*16 + 4, 20, 3), (6*16, 37*16 + 2, 22, 4), (36*16, 9*16 + 5, 18, 5),
             (9*16, 7*16 + 5, 12, 6), (31*16 + 5, 21*16 + 2, 14, 7)]:
    crack(*args)
crack(27*16 + 4, 2*16, 24, 8, dx=0, dy=1); crack(28*16 + 9, 30*16, 20, 9, dx=0, dy=1)
for cx, cy, r, s in [(11*16, 10*16 + 4, 7, 1), (22*16 + 6, 24*16 + 2, 9, 2), (36*16, 24*16 + 8, 6, 3), (27*16 + 6, 33*16, 6, 4),
                     (15*16 + 9, 18*16 + 6, 5, 5), (4*16, 37*16 + 7, 8, 6)]:
    puddle(cx, cy, r, s)
for i, (x, y) in enumerate([(9*16 + 3, 21*16 + 4), (15*16 + 2, 19*16 + 8), (23*16 + 9, 6*16 + 6), (2*16 + 5, 35*16 + 8), (19*16 + 4, 30*16 + 2),
                            (6*16 + 6, 15*16 + 3), (34*16 + 4, 37*16 + 6), (37*16 + 2, 36*16 + 9), (14*16 + 8, 12*16 + 6), (30*16 + 5, 26*16 + 6)]):
    litter(x, y, i)
# oil in the warehouse yard
for cx, cy, r, s in [(34*16, 37*16, 9, 11), (37*16 + 6, 38*16 + 4, 6, 12)]:
    rr = random.Random(s)
    for y in range(cy - r - 2, cy + r + 3):
        for x in range(cx - r - 3, cx + r + 4):
            d = math.hypot((x - cx)*0.75, y - cy) + rr.uniform(-1.5, 1.5)
            if d < r: GSH[y][x] = 2

# ====================================================================== building drawing (roles)
BR = {}                 # (x, y) px -> role
BSLOT = {}              # (cx, cy) cell -> palette slot
def put(x, y, r): BR[(x, y)] = r

def wall_role(pattern, x, y):
    i, j = x % 16, y % 16
    if pattern == 'brick':
        course = j // 4
        if j % 4 == 3: return MO
        if (i + (4 if course % 2 else 0)) % 8 == 7: return MO
        bid = ((i + (4 if course % 2 else 0)) // 8, course)
        return W2 if (bid[0]*3 + bid[1]*5) % 7 == 0 else W0 if (bid[0] + bid[1]*3) % 9 == 4 else W1
    if pattern == 'clap':
        k = j % 4
        return W0 if k == 0 else W3 if k == 3 else W1 if (i + j*7) % 11 else W2
    if pattern == 'corr':
        return (W0, W1, W2, W3)[i % 4] if j != 15 else W3
    # stucco / brownstone: speckled render with faint coursing
    h = (i*7 + j*13 + (i*j) % 5) % 23
    if pattern == 'brown' and j in (7, 15): return MO
    return W0 if h == 0 else W2 if h in (5, 11) else W3 if h == 17 else W1
PATTERN = {'brick': 'brick', 'stucco': 'stucco', 'clap': 'clap', 'brown': 'brown', 'corr': 'corr'}

def rect_role(x0, y0, x1, y1, r):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1): put(x, y, r)

def draw_window(ox, oy, state, barred=False):
    """Window in the cell whose top-left pixel is (ox, oy)."""
    rect_role(ox + 2, oy + 1, ox + 13, oy + 1, T1)               # lintel
    rect_role(ox + 3, oy + 2, ox + 12, oy + 11, R2)              # frame outline
    rect_role(ox + 4, oy + 3, ox + 11, oy + 10, T0)              # frame
    gx0, gy0, gx1, gy1 = ox + 5, oy + 4, ox + 10, oy + 10
    for y in range(gy0, gy1 + 1):
        for x in range(gx0, gx1 + 1):
            i, j = x - gx0, y - gy0
            if state == 'lit':
                r = L0 if 1 <= i <= 4 and 1 <= j <= 4 else L1
                if i in (0, 5): r = L2
            elif state == 'blind':
                r = L2 if j % 2 else L1
            elif state == 'board':
                r = T1 if j % 3 == 2 else T0 if (i + j) % 5 else R2
            elif state == 'broken':
                r = G1
                if (i, j) in ((1, 1), (2, 2), (3, 2), (4, 3), (2, 4), (1, 5), (4, 5)): r = G0
                if (i, j) in ((3, 3), (2, 3)): r = R2
            else:                                                   # dark
                r = G0 if i + j in (2, 3) or i + j == 7 else G1
            if state not in ('board',) and x == gx0 + 3 and state != 'broken': r = T0 if state != 'lit' else L2   # mullion
            put(x, y, r)
    rect_role(ox + 2, oy + 11, ox + 13, oy + 12, T0)             # sill
    rect_role(ox + 3, oy + 13, ox + 12, oy + 13, R2)             # sill shadow
    if barred:
        for x in range(gx0, gx1 + 1, 2): rect_role(x, gy0 - 1, x, gy1, R2)
    if state == 'ac':
        rect_role(ox + 4, oy + 7, ox + 11, oy + 12, T0); rect_role(ox + 4, oy + 12, ox + 11, oy + 13, R2)
        for x in range(ox + 5, ox + 11, 2): rect_role(x, oy + 8, x, oy + 11, T1)
    if state in ('dark', 'broken', 'board'):                      # grime streak under the sill
        put(ox + 5, oy + 14, W3); put(ox + 9, oy + 14, W3); put(ox + 9, oy + 15, W3)

def draw_door(ox, oy, wide=False):
    rect_role(ox + 2, oy + 0, ox + 13, oy + 0, T1)
    rect_role(ox + 3, oy + 1, ox + 12, oy + 15, R2)
    rect_role(ox + 4, oy + 2, ox + 11, oy + 15, T1)
    rect_role(ox + 5, oy + 3, ox + 10, oy + 7, T0 if not wide else L1)
    rect_role(ox + 5, oy + 9, ox + 10, oy + 14, T0)
    rect_role(ox + 6, oy + 4, ox + 9, oy + 6, T1 if not wide else L0)
    rect_role(ox + 6, oy + 10, ox + 9, oy + 13, T1)
    put(ox + 10, oy + 9, L1)                                      # knob

def draw_shop(ox, oy, k):
    rect_role(ox, oy, ox + 15, oy + 1, T1)
    rect_role(ox, oy + 2, ox + 15, oy + 12, R2)
    for y in range(oy + 3, oy + 12):
        for x in range(ox + 1, ox + 15):
            i, j = x - ox, y - oy
            put(x, y, L0 if j < 6 and 3 < (i + k*5) % 16 < 12 else L1)
    for x in range(ox + 2, ox + 14, 4):                         # goods on shelves
        rect_role(x, oy + 8, x + 1, oy + 11, L2)
    rect_role(ox, oy + 12, ox + 15, oy + 13, T0); rect_role(ox, oy + 14, ox + 15, oy + 15, T1)

def draw_shutter(ox, oy):
    rect_role(ox, oy, ox + 15, oy + 1, T1)
    for y in range(oy + 2, oy + 16):
        for x in range(ox, ox + 16): put(x, y, T0 if (y - oy) % 3 == 0 else T1)
    rect_role(ox, oy + 15, ox + 15, oy + 15, R2)

def draw_rollup(ox, oy, part):
    for y in range(oy, oy + 16):
        for x in range(ox, ox + 16):
            put(x, y, T1 if (y % 4) == 3 else T0 if (y % 4) == 0 else W2)
    if part in ('L', 'S'): rect_role(ox, oy, ox + 1, oy + 15, R2)
    if part in ('R', 'S'): rect_role(ox + 14, oy, ox + 15, oy + 15, R2)

def draw_roof(b):
    X0, X1, Y0, Y1 = b['x0']*16, (b['x1'] + 1)*16 - 1, b['r0']*16, (b['r1'] + 1)*16 - 1
    rr = random.Random(b['seed']*31)
    if b['scheme'] == 'corr':         # sawtooth: lit slope, dark north-light face with glazing, 16 px period
        for y in range(Y0, Y1 + 1):
            for x in range(X0, X1 + 1):
                j = (y - Y0) % 16
                r = R0 if j < 4 else R1 if j < 9 else (G1 if j < 13 and (x % 8) < 6 else R2)
                if j == 9: r = R2
                if j in (10, 11) and (x % 8) < 6: r = G0 if (x % 8) < 2 else G1
                put(x, y, r)
        rect_role(X0, Y0, X0, Y1, R2); rect_role(X1, Y0, X1, Y1, R2); rect_role(X0, Y0, X1, Y0, R2)
        return
    for y in range(Y0, Y1 + 1):
        for x in range(X0, X1 + 1):
            h = ((x % 16)*5 + (y % 16)*11 + ((x % 16)*(y % 16)) % 7) % 29
            put(x, y, R0 if h == 3 else R2 if h in (8, 21) else R1)
    # parapet: outline, 2 px coping, inner shadow
    for x in range(X0, X1 + 1):
        put(x, Y0, R2); put(x, Y0 + 1, R0); put(x, Y0 + 2, R0); put(x, Y0 + 3, R2)
    for y in range(Y0, Y1 + 1):
        put(X0, y, R2); put(X0 + 1, y, R0); put(X0 + 2, y, R0); put(X0 + 3, y, R2) if y > Y0 + 2 else None
        put(X1, y, R2); put(X1 - 1, y, R0); put(X1 - 2, y, R0)
    # roof fixtures, snapped to cells so they dedupe
    cells = [(cx, cy) for cx in range(b['x0'] + 1, b['x1']) for cy in range(b['r0'], b['r1'] + 1)]
    rr.shuffle(cells)
    for k, (cx, cy) in enumerate(cells[:max(1, (b['x1'] - b['x0'])//2)]):
        ox, oy = cx*16, cy*16
        kind = rr.choice(['ac', 'vent', 'hatch', 'ac', 'chimney'])
        if kind == 'ac':
            rect_role(ox + 2, oy + 4, ox + 13, oy + 13, R2); rect_role(ox + 3, oy + 4, ox + 12, oy + 7, T0); rect_role(ox + 3, oy + 8, ox + 12, oy + 12, T1)
            for x in range(ox + 4, ox + 12, 2): rect_role(x, oy + 9, x, oy + 11, R2)
        elif kind == 'vent':
            for y in range(oy + 3, oy + 13):
                for x in range(ox + 3, ox + 13):
                    d = math.hypot(x - ox - 7.5, y - oy - 7.5)
                    if d < 5: put(x, y, R2 if d > 4 else T0 if y < oy + 7 else T1)
            rect_role(ox + 5, oy + 13, ox + 10, oy + 14, R2)
        elif kind == 'hatch':
            rect_role(ox + 3, oy + 3, ox + 12, oy + 12, R2); rect_role(ox + 4, oy + 4, ox + 11, oy + 10, T1); rect_role(ox + 4, oy + 4, ox + 11, oy + 5, T0)
        else:
            rect_role(ox + 4, oy + 2, ox + 11, oy + 13, R2)
            for y in range(oy + 3, oy + 13):
                for x in range(ox + 5, ox + 11): put(x, y, wall_role('brick', x, y))
            rect_role(ox + 4, oy + 2, ox + 11, oy + 3, T0)

def draw_fire_escape(b, fx):
    """Two cells wide, upper floors only: landings with railings and alternating diagonal stairs."""
    X0, X1 = fx*16, fx*16 + 31
    floors = list(range(b['f0'], b['f1']))
    for n, cy in enumerate(floors):
        y = cy*16
        for x in range(X0, X1 + 1):
            put(x, y + 13, R2); put(x, y + 14, T1); put(x, y + 15, R2)       # landing deck
            put(x, y + 7, R2)                                                 # top rail
            if (x - X0) % 5 == 0:
                for yy in range(y + 7, y + 13): put(x, yy, R2)               # balusters
        rect_role(X0, y + 7, X0, y + 15, R2); rect_role(X1, y + 7, X1, y + 15, R2)
        if n + 1 < len(floors) or True:                                      # stair up to the next landing
            yb, yt = y + 13, y - 3
            if n == 0: continue
            for k in range(0, 17):
                t = k/16; xa = X0 + 4 + int((22 if n % 2 else 0) + t*(-22 if n % 2 else 22)); ya = int(yb + (yt - yb)*t)
                put(xa, ya, R2); put(xa + 3, ya, R2)
                if k % 3 == 0: put(xa + 1, ya, T1); put(xa + 2, ya, T1)
    # drop ladder above the ground floor
    ly = b['f1']*16
    for yy in range(ly - 3, ly + 6):
        put(X0 + 24, yy, R2); put(X0 + 28, yy, R2)
        if yy % 3 == 0:
            for x in range(X0 + 25, X0 + 28): put(x, yy, T1)

WSTATE = ['dark']*10 + ['lit']*4 + ['board']*2 + ['ac']*2
def draw_building(b):
    S = SCHEMES[b['scheme']]; pat = PATTERN[b['scheme']]
    for cy in range(b['r0'], b['f1'] + 1):
        for cx in range(b['x0'], b['x1'] + 1): BSLOT[(cx, cy)] = S['slot']
    draw_roof(b)
    X0, X1 = b['x0']*16, (b['x1'] + 1)*16 - 1
    rr = random.Random(b['seed'])
    for cy in range(b['f0'], b['f1'] + 1):
        for cx in range(b['x0'], b['x1'] + 1):
            ox, oy = cx*16, cy*16
            for j in range(16):
                for i in range(16): put(ox + i, oy + j, wall_role(pat, ox + i, oy + j))
            if cy < b['f1']:
                if b['scheme'] == 'corr':
                    if cy == b['f0']:                         # clerestory strip
                        rect_role(ox, oy + 5, ox + 15, oy + 5, R2); rect_role(ox, oy + 6, ox + 15, oy + 10, G1 if cx % 3 else L1)
                        for x in range(ox, ox + 16, 4): rect_role(x, oy + 6, x, oy + 10, R2)
                        rect_role(ox, oy + 11, ox + 15, oy + 11, T0)
                    continue
                st = rr.choice(WSTATE)
                if b['fire'] is not None and b['fire'] <= cx <= b['fire'] + 1: st = 'dark'   # behind the fire escape
                if cx in (b['x0'], b['x1']) and st in ('ac', 'board'): st = 'dark'
                draw_window(ox, oy, st)
            else:
                g = b['ground'][cx - b['x0']]
                if g in 'wg': draw_window(ox, oy, rr.choice(['dark', 'dark', 'lit', 'board']), barred=(g == 'g'))
                elif g == 'b': draw_window(ox, oy, 'board')
                elif g == 's': draw_shop(ox, oy, cx)
                elif g == 'h': draw_shutter(ox, oy)
                elif g in 'dm': draw_door(ox, oy)
                elif g == 'D': draw_door(ox, oy, wide=True)
                elif g == 'r':
                    left = cx == b['x0'] or b['ground'][cx - b['x0'] - 1] != 'r'
                    right = cx == b['x1'] or b['ground'][cx - b['x0'] + 1] != 'r'
                    draw_rollup(ox, oy, 'S' if left and right else 'L' if left else 'R' if right else 'M')
                if cy == b['f1']:
                    rect_role(ox, oy + 15, ox + 15, oy + 15, R2)     # plinth line
    # rollup door spans two floors on the warehouse
    if b['scheme'] == 'corr':
        for cx in range(b['x0'], b['x1'] + 1):
            if b['ground'][cx - b['x0']] == 'r':
                g = b['ground']; left = g[cx - b['x0'] - 1] != 'r'; right = g[cx - b['x0'] + 1] != 'r'
                draw_rollup(cx*16, (b['f1'] - 1)*16, 'S' if left and right else 'L' if left else 'R' if right else 'M')
                rect_role(cx*16, (b['f1'] - 1)*16, cx*16 + 15, (b['f1'] - 1)*16 + 2, R2)
        # hazard stripes on the dock edge in front of the roll-up door
    # cornice at the top of the facade
    for x in range(X0, X1 + 1):
        Y = b['f0']*16
        put(x, Y, T1); put(x, Y + 1, T0); put(x, Y + 2, R2)
    if b['fire'] is not None: draw_fire_escape(b, b['fire'])
    for y in range(b['r0']*16, (b['f1'] + 1)*16): put(X0, y, R2); put(X1, y, R2)

for b in BUILDINGS: draw_building(b)

# ---- the MC's stoop: landing in front of the door, sunken areaways with basement windows, stairs
def draw_stoop():
    S = 'brown'
    for (cx, cy), kind in STOOP.items():
        BSLOT[(cx, cy)] = SCHEMES[S]['slot']; ox, oy = cx*16, cy*16
        if kind == 'landing':
            for y in range(oy, oy + 16):
                for x in range(ox, ox + 16): put(x, y, W1 if (x + y) % 9 else W0)
            rect_role(ox, oy, ox + 15, oy + 1, R2)                      # door shadow
            rect_role(ox, oy + 11, ox + 15, oy + 12, T0)               # landing nosing
            rect_role(ox, oy + 13, ox + 15, oy + 15, W3)               # landing riser
            for y in range(oy, oy + 12):                                # iron side railings
                put(ox, y, R2); put(ox + 15, y, R2)
            rect_role(ox, oy + 2, ox, oy + 10, R2); put(ox + 1, oy + 2, R2); put(ox + 14, oy + 2, R2)
        elif kind == 'stairs':
            for y in range(oy, oy + 16):
                for x in range(ox, ox + 16):
                    j = (y - oy) % 4
                    put(x, y, T0 if j == 0 else W1 if j < 3 else W3)
            for y in range(oy, oy + 16):                                # cheek walls + handrails
                for x in (ox, ox + 1, ox + 14, ox + 15): put(x, y, W2 if x in (ox + 1, ox + 14) else R2)
            rect_role(ox, oy + 14, ox + 15, oy + 15, MO)                # bottom step shadow on the sidewalk side
        else:                                                           # areaway: dark well, basement window, railing
            for y in range(oy, oy + 16):
                for x in range(ox, ox + 16): put(x, y, R2 if y < oy + 3 else W3 if (x + y) % 7 else MO)
            lit = cx == 11
            rect_role(ox + 3, oy + 1, ox + 12, oy + 7, T1)
            rect_role(ox + 4, oy + 2, ox + 11, oy + 6, L1 if lit else G1)
            if lit: rect_role(ox + 5, oy + 3, ox + 8, oy + 4, L0)
            else: put(ox + 5, oy + 3, G0); put(ox + 6, oy + 4, G0)
            for x in range(ox + 4, ox + 12, 2): rect_role(x, oy + 2, x, oy + 6, R2)       # bars
            rect_role(ox, oy + 9, ox + 15, oy + 9, R2)                  # railing top rail
            for x in range(ox, ox + 16, 3): rect_role(x, oy + 9, x, oy + 15, R2)
            rect_role(ox, oy + 15, ox + 15, oy + 15, T0)                # curb of the well
draw_stoop()

# ====================================================================== props (top layer)
OBJ = {}
D = pickle.load(open(os.path.join(HERE, 'objs.pkl'), 'rb'))
for n, (b_, sz, c, f) in D.items(): OBJ[n] = Image.frombytes('RGBA', sz, b_)
# the Battle Factory can is clean white: dirty it down to galvanised grey


def canvas(w, h): return Image.new('RGBA', (w*16, h*16), (0, 0, 0, 0))
def dumpster():
    im = canvas(2, 2); d = ImageDraw.Draw(im)
    body, dark, lid, rim = (64, 112, 82), (40, 72, 56), (48, 86, 64), (88, 140, 104)
    d.rectangle([1, 9, 30, 29], fill=body, outline=(24, 36, 30))
    d.rectangle([0, 5, 31, 10], fill=lid, outline=(24, 36, 30)); d.line([1, 6, 30, 6], fill=rim)
    for x in (6, 15, 24): d.line([x, 11, x, 28], fill=dark)
    d.rectangle([3, 13, 11, 17], fill=dark)                      # label plate
    d.line([2, 28, 29, 28], fill=dark)
    for x in (4, 25): d.rectangle([x, 29, x + 3, 31], fill=(30, 30, 34))
    for p in [(20, 20), (21, 21), (9, 24), (27, 14), (26, 15)]: d.point(p, fill=(120, 72, 48))   # rust
    d.polygon([(4, 4), (12, 1), (14, 4)], fill=(36, 36, 40))        # bag poking out
    return im
def bags():
    im = canvas(1, 1); d = ImageDraw.Draw(im)
    for (x, y, r) in [(5, 10, 5), (11, 11, 4), (8, 6, 4)]:
        d.ellipse([x - r, y - r, x + r, y + r], fill=(38, 40, 46), outline=(18, 18, 22))
        d.point((x - 1, y - r + 2), fill=(96, 100, 110)); d.point((x, y - r + 2), fill=(70, 74, 84))
    d.line([8, 2, 9, 3], fill=(18, 18, 22))
    return im
def hydrant():
    im = canvas(1, 1); d = ImageDraw.Draw(im)
    red, dk, hi = (176, 52, 44), (110, 30, 30), (220, 110, 90)
    d.rectangle([5, 6, 10, 14], fill=red, outline=dk); d.rectangle([4, 4, 11, 6], fill=red, outline=dk)
    d.rectangle([6, 2, 9, 4], fill=dk); d.rectangle([2, 8, 4, 10], fill=dk); d.rectangle([11, 8, 13, 10], fill=dk)
    d.line([6, 7, 6, 12], fill=hi); d.rectangle([4, 14, 11, 15], fill=(60, 30, 30))
    return im
def fence_h(post=True):
    im = canvas(1, 1); d = ImageDraw.Draw(im); wire, post_c, dk = (120, 124, 132), (150, 154, 160), (60, 62, 70)
    for x in range(0, 16):
        for y in range(4, 15):
            if (x + y) % 4 == 0 or (x - y) % 4 == 0: d.point((x, y), fill=wire)
    d.line([0, 3, 15, 3], fill=post_c); d.line([0, 4, 15, 4], fill=dk)
    if post: d.rectangle([0, 1, 1, 15], fill=post_c); d.line([1, 2, 1, 15], fill=dk)
    return im
def fence_v():
    im = canvas(1, 1); d = ImageDraw.Draw(im); wire, post_c, dk = (120, 124, 132), (150, 154, 160), (60, 62, 70)
    for y in range(0, 16): d.point((7, y), fill=wire if y % 2 else dk); d.point((8, y), fill=wire if y % 2 == 0 else dk)
    d.rectangle([6, 0, 9, 3], fill=post_c); d.line([9, 1, 9, 3], fill=dk)
    return im
def gate_post():
    im = canvas(1, 1); d = ImageDraw.Draw(im)
    d.rectangle([6, 0, 9, 14], fill=(150, 154, 160)); d.line([9, 1, 9, 14], fill=(60, 62, 70)); d.rectangle([5, 0, 10, 2], fill=(170, 174, 180))
    return im
def awning(w=3):
    im = canvas(w, 1); d = ImageDraw.Draw(im)
    a, b_, dk = (178, 64, 56), (210, 196, 170), (90, 36, 36)
    for x in range(w*16):
        for y in range(0, 11):
            d.point((x, y), fill=a if (x // 4) % 2 == 0 else b_)
        if (x % 8) < 6: d.point((x, 11), fill=a if (x // 4) % 2 == 0 else b_)
    d.line([0, 0, w*16 - 1, 0], fill=dk); d.line([0, 9, w*16 - 1, 9], fill=dk)
    for x in (1, w*16 - 2): d.line([x, 10, x, 15], fill=(80, 60, 44))
    # hanging lantern
    cx = w*16//2; d.line([cx, 10, cx, 11], fill=(40, 40, 40)); d.rectangle([cx - 2, 12, cx + 2, 15], fill=(255, 220, 140))
    return im
def counter(goods):
    w = len(goods); im = canvas(w, 1); d = ImageDraw.Draw(im)
    wood, wd, top = (132, 92, 58), (84, 58, 40), (164, 120, 80)
    d.rectangle([0, 6, w*16 - 1, 15], fill=wood, outline=wd); d.line([1, 6, w*16 - 2, 6], fill=top)
    for x in range(4, w*16, 8): d.line([x, 8, x, 14], fill=wd)
    for k, g in enumerate(goods):
        if g:
            gi = OBJ[g].resize((12, 12), Image.NEAREST)
            im.alpha_composite(gi, (k*16 + 2, -1))
    return im
def trash_can():
    """Galvanised can, 10 px wide, with a rounded base and its own contact shadow so it sits on any ground."""
    im = canvas(1, 2); px = im.load()
    out, dk, mid, lt, hi, rust, shad = (40, 42, 50), (78, 82, 92), (108, 114, 124), (138, 144, 152), (172, 178, 184), (112, 80, 58), (22, 22, 28)
    cx = 7.5
    for y in range(28, 32):                                   # contact shadow
        for x in range(1, 15):
            if ((x - cx)/6.5)**2 + ((y - 29.6)/2.0)**2 <= 1: px[x, y] = shad + (255,)
    for y in range(15, 30):                                   # body: shaded cylinder with two ribs
        for x in range(3, 13):
            if y >= 28 and ((x - cx)/5.0)**2 + ((y - 27.5)/1.6)**2 > 1: continue
            u = (x - 3)/9.0
            c = hi if u < 0.18 else lt if u < 0.40 else mid if u < 0.72 else dk
            if y in (19, 24): c = dk if u > 0.2 else mid
            if x in (3, 12) or y == 29 or (y == 28 and x in (4, 11)): c = out
            px[x, y] = c + (255,)
    for x, y in ((10, 21), (9, 22), (10, 26), (5, 27)): px[x, y] = rust + (255,)
    for y in range(11, 17):                                   # lid: flat ellipse with a rim and handle
        for x in range(2, 14):
            e = ((x - cx)/6.0)**2 + ((y - 14.0)/2.6)**2
            if e <= 1: px[x, y] = (out if e > 0.72 else hi if y < 14 else lt) + (255,)
    for x in range(6, 10): px[x, 10] = out + (255,)
    px[6, 11] = px[9, 11] = out + (255,)
    return im

def boxes():
    im = canvas(1, 1); im.alpha_composite(OBJ['box'], (0, 0)); return im

PROPS = {
    'dumpster': (dumpster(), 'metal', 1), 'bags': (bags(), 'metal', 0), 'trash': (trash_can(), 'metal', 1),
    'hydrant': (hydrant(), 'warm', 0), 'fence_h': (fence_h(), 'metal', 0), 'fence_v': (fence_v(), 'metal', 0),
    'gate_post': (gate_post(), 'metal', 0),
    'awning': (awning(), 'warm', 9), 'counter_a': (counter(['bowl_orange', 'bowl_teal', 'bowl_red']), 'warm', 0),
    'counter_b': (counter(['flowers', 'pot', 'crate_lbl']), 'warm', 0), 'counter_c': (counter(['crate_slat', 'bowl_teal', 'flowers']), 'warm', 0),
    'box': (OBJ['box'], 'warm', 0), 'box_open': (OBJ['box_open'], 'warm', 0), 'crate_lbl': (OBJ['crate_lbl'], 'warm', 0),
    'crate3': (OBJ['crate3'], 'warm', 1), 'crate2': (OBJ['crate2'], 'warm', 1), 'crate_stack': (OBJ['crate_stack'], 'warm', 1),
    'pallet': (OBJ['pallet'], 'warm', 0), 'drum': (OBJ['drum'], 'warm', 1), 'drum_stack': (OBJ['drum_stack'], 'warm', 1),
    'rubble': (OBJ['rubble'], 'warm', 0), 'debris': (OBJ['debris'], 'warm', 0), 'lumber': (OBJ['lumber'], 'warm', 1),
}
# walk-behind rows (drawn over the player, walkable): third field. 9 = whole prop walkable (awning)

def grade(c, fam):
    r, g, b = [v/255 for v in c]; h, s, v = colorsys.rgb_to_hsv(r, g, b)
    s *= 0.70 if fam == 'warm' else 0.55
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return tuple(int(x*255) for x in (r, g, b))
def palette_for(fam, n=15):
    px = []
    for name, (im, f, wb) in PROPS.items():
        if f != fam: continue
        px += [grade(p[:3], fam) for p in im.get_flattened_data() if p[3]]
    strip = Image.new('RGB', (len(px), 1)); strip.putdata(px)
    qz = strip.quantize(colors=n, method=Image.Quantize.MEDIANCUT, kmeans=3); pal = qz.getpalette()[:n*3]
    return [tuple(pal[i*3 + k] for k in range(3)) for i in range(n)]
def nearest(c, pal):
    return min(range(len(pal)), key=lambda i: sum((a - b)**2*w for a, b, w in zip(c, pal[i], (3, 4, 2))))
FAMPAL = {f: palette_for(f) for f in ('warm', 'metal')}
def night_dark(c): return q((c[0]*0.46 + 6, c[1]*0.48 + 8, c[2]*0.56 + 18))
def night_lit(c):  return q((c[0]*0.86 + 8, c[1]*0.80 + 6, c[2]*0.68 + 4))
PAL_METAL_D = [(0, 0, 0)] + [night_dark(c) for c in FAMPAL['metal']]
PAL_METAL_L = [(0, 0, 0)] + [night_lit(c) for c in FAMPAL['metal']]
PAL_WARM_D = [(0, 0, 0)] + [night_dark(c) for c in FAMPAL['warm']]
PAL_WARM_L = [(0, 0, 0)] + [night_lit(c) for c in FAMPAL['warm']]
SLOT = {('metal', 2): 7, ('metal', 0): 8, ('warm', 2): 9, ('warm', 0): 10}
PIDX = {}
for name, (im, fam, wb) in PROPS.items():
    cache = {}; w_, h_ = im.size; px = im.load(); a = [[0]*w_ for _ in range(h_)]
    for y in range(h_):
        for x in range(w_):
            p = px[x, y]
            if p[3]:
                g = grade(p[:3], fam)
                if g not in cache: cache[g] = nearest(g, FAMPAL[fam]) + 1
                a[y][x] = cache[g]
    PIDX[name] = a
# the awning's lantern is a light source: force it into the lit palette's brightest entry
# lamp: its own palette (11) with glowing glass
LAMP_DAY = [(0, 0, 0)]
def lamp_pal_and_idx():
    im = OBJ['lamp']; px = im.load(); w_, h_ = im.size
    cols = sorted({px[x, y][:3] for y in range(h_) for x in range(w_) if px[x, y][3]}, key=lambda c: sum(c))
    pal = [(0, 0, 0)]; idx = [[0]*w_ for _ in range(h_)]; m = {}
    for c in cols:
        r, g, b = c; lum = (r*3 + g*4 + b*2)/9
        is_glass = (b > r + 20 and lum > 120) or lum > 200
        nc = q((255, 238, 180)) if is_glass and lum > 190 else q((240, 200, 120)) if is_glass else q((c[0]*0.45 + 8, c[1]*0.45 + 8, c[2]*0.52 + 16))
        if nc not in pal:
            pal.append(nc)
            LAMP_DAY.append(q((206, 216, 224)) if is_glass and lum > 190 else q((166, 180, 194)) if is_glass else q(c))
        m[c] = pal.index(nc)
    for y in range(h_):
        for x in range(w_):
            if px[x, y][3]: idx[y][x] = m[px[x, y][:3]]
    # lantern / wall-pack glow colours appended
    for c, dc in [((255, 248, 210), (222, 216, 200)), ((230, 170, 90), (176, 166, 150))]:     # unlit by day
        pal.append(q(c)); LAMP_DAY.append(q(dc))
    assert len(pal) <= 16, len(pal)
    return pal, idx
PAL_GLOW, LAMP_IDX = lamp_pal_and_idx()
GLOW_HOT, GLOW_WARM = len(PAL_GLOW) - 2, len(PAL_GLOW) - 1

# neon / graffiti palette (12)
PAL_NEON = [(0, 0, 0)] + [q(c) for c in [(255, 120, 220), (200, 56, 160), (110, 30, 90), (120, 240, 255), (40, 160, 200), (24, 70, 100),
                                         (255, 210, 90), (60, 180, 90), (230, 230, 240), (36, 32, 44)]]
FONT = {'P': ['111', '101', '111', '100', '100'], 'A': ['010', '101', '111', '101', '101'], 'W': ['10001', '10001', '10101', '10101', '01010'],
        'N': ['1001', '1101', '1011', '1001', '1001'], 'B': ['110', '101', '110', '101', '110'], 'R': ['110', '101', '110', '101', '101'],
        'O': ['010', '101', '101', '101', '010'], 'E': ['111', '100', '110', '100', '111'], 'L': ['100', '100', '100', '100', '111'],
        'I': ['1', '1', '1', '1', '1'], 'Q': ['010', '101', '101', '110', '011'], 'U': ['101', '101', '101', '101', '111'], 'S': ['011', '100', '010', '001', '110'],
        'D': ['110', '101', '101', '101', '110'], 'G': ['011', '100', '101', '101', '011'], 'C': ['011', '100', '100', '100', '011'], 'K': ['101', '101', '110', '101', '101'],
        ' ': ['0', '0', '0', '0', '0']}
def neon_sign(text, w, main=1, glow=2):
    """Neon tube lettering on a dark backing board, w cells wide, one cell tall."""
    a = [[0]*(w*16) for _ in range(16)]
    tw = sum(len(FONT[c][0]) + 1 for c in text) - 1; x = (w*16 - tw)//2
    for yy in range(3, 13):
        for xx in range(max(0, x - 3), min(w*16, x + tw + 3)): a[yy][xx] = 11
    for c in text:
        g = FONT[c]
        for j, row in enumerate(g):
            for i, bit in enumerate(row):
                if bit == '1':
                    a[5 + j][x + i] = main
        x += len(g[0]) + 1
    for yy in range(3, 13):
        for xx in range(16*w):
            if a[yy][xx] == 11 and any(a[y2][x2] == main for y2 in (yy - 1, yy, yy + 1) for x2 in (xx - 1, xx, xx + 1) if 0 <= y2 < 16 and 0 <= x2 < 16*w):
                a[yy][xx] = glow
    for xx in range(16*w):
        if a[3][xx] == 11 or a[3][xx] == glow: a[3][xx] = 3
    return a
def graffiti(seed, w=2):
    rr = random.Random(seed); a = [[0]*(w*16) for _ in range(16)]
    cols = rr.sample([1, 4, 7, 8], 2)
    x, y = 3, 8
    for k in range(w*16 - 8):
        x = 3 + k; y = int(8 + 3.5*math.sin(k*0.7 + seed)) + rr.choice((0, 0, 1))
        for dy in (-1, 0, 1):
            if 1 <= y + dy < 15: a[y + dy][x] = cols[0]
        if k % 5 == 0:
            for dy in range(-3, 4):
                if 1 <= y + dy < 15: a[y + dy][x] = cols[1]
    for k in range(4):                                  # drips
        dx = rr.randint(4, w*16 - 4)
        for dy in range(11, 15): a[dy][dx] = cols[0] if a[dy][dx] == 0 else a[dy][dx]
    return a
NEON = [  # (index array, cell x, cell y)
    (neon_sign('PAWN', 2, 4, 5), 14, 4),          # over the clapboard shopfronts (band A)
    (neon_sign('BAR', 2, 1, 2), 8, 31),           # over the lit shop in band C
    (neon_sign('OPEN', 2, 7, 6), 6, 18),           # corner store in band B
]
GRAFF = []                                       # graffiti tags removed (read as glitches)

# ---- placement: (prop, cell x, cell y) top-left
PLACE = [
    # MC's alley (x 15-16): fenced dead end with a dumpster, bags and a can
    ('dumpster', 15, 15), ('bags', 16, 17), ('trash', 15, 17),
    # other alleys
    ('bags', 6, 3), ('trash', 6, 4), ('dumpster', 18, 1), ('trash', 19, 4), ('box', 18, 4),
    ('trash', 5, 14), ('bags', 5, 18), ('box_open', 35, 14), ('trash', 35, 17),
    ('trash', 7, 30), ('bags', 19, 32), ('crate_lbl', 19, 28), ('box', 7, 33),
    # curbside
    ('trash', 23, 6), ('trash', 24, 34), ('trash', 37, 6), ('bags', 1, 34),
    ('hydrant', 17, 21), ('hydrant', 24, 7), ('hydrant', 13, 35),
    # warehouse yard
    ('drum_stack', 39, 35), ('drum', 32, 35), ('crate3', 34, 37), ('crate2', 37, 37), ('pallet', 32, 38), ('rubble', 36, 36), ('lumber', 39, 37),
]
for x, y in STALLS:
    PLACE += [('awning', x, y), (['counter_a', 'counter_b', 'counter_c'][STALLS.index((x, y))], x, y + 1)]
for x, y in MC_ALLEY_FENCE: PLACE.append(('fence_h', x, y))
for x, y in YARD_FENCE: PLACE.append(('fence_v', x, y))
for x, y in YARD_GATE[:1]: PLACE.append(('gate_post', x, y - 0))
# (the yard runs off the bottom edge; no fence there)

TOP = {}            # (cx, cy) -> [4 (indices or None)], slot
COLL = {}           # (cx, cy) -> blocked?
WALKBEHIND = set()
def stamp(arr, cx0, cy0, slot, rows_walk=0, block=True):
    h_, w_ = len(arr)//16, len(arr[0])//16
    for cy in range(h_):
        for cx in range(w_):
            qs = []
            for qy in (0, 1):
                for qx in (0, 1):
                    t = tuple(arr[cy*16 + qy*8 + j][cx*16 + qx*8 + i] for j in range(8) for i in range(8))
                    qs.append(t if any(t) else None)
            if not any(qs): continue
            key = (cx0 + cx, cy0 + cy)
            if key in TOP:   # merge with what is already there (same slot only)
                old, oslot = TOP[key]
                assert oslot == slot, ('slot clash', key)
                qs = [n if n else o for n, o in zip(qs, old)]
            TOP[key] = (qs, slot)
            walk = rows_walk == 9 or cy < rows_walk
            if walk: WALKBEHIND.add(key)
            elif block: COLL[key] = True

def prop_light(name, x, y):
    a = PIDX[name]; h_, w_ = len(a)//16, len(a[0])//16
    return 0 if light((x + w_/2)*16, (y + h_ - 0.4)*16) < 1.2 else 2
for name, x, y in PLACE:
    im, fam, wb = PROPS[name]
    lv = prop_light(name, x, y)
    stamp(PIDX[name], x, y, SLOT[(fam, lv)], wb)
for (x, y) in LAMPS:
    stamp(LAMP_IDX, x, y - 1, 11, 1)
# glow spots: the awning lanterns and the warehouse wall-pack light
for x, y in STALLS:
    cx = x*16 + 24
    for yy in range(12, 16):
        for xx in range(cx - 2, cx + 3):
            k = (xx // 16, y)
for name, x, y in [(n, x, y) for (n, x, y) in PLACE if n == 'awning']:
    # move the lantern pixels into the glow palette: done by a separate overlay cell would clash; keep them warm-lit
    pass
wp = [[0]*16 for _ in range(16)]
for yy in range(1, 5):
    for xx in range(5, 11): wp[yy][xx] = GLOW_HOT if 1 < yy < 4 and 6 < xx < 10 else GLOW_WARM
for xx in range(4, 12): wp[5][xx] = 1
stamp(wp, WAREHOUSE_DOOR[0], WAREHOUSE_DOOR[1] - 1, 11, 0, block=False)
# porch light above the MC's door
pl = [[0]*16 for _ in range(16)]
for yy in range(10, 14):
    for xx in range(6, 10): pl[yy][xx] = GLOW_HOT if 11 <= yy <= 12 and 7 <= xx <= 8 else GLOW_WARM
stamp(pl, MC_DOOR[0], MC_DOOR[1] - 1, 11, 0, block=False)
for a, x, y in NEON: stamp(a, x, y, 12, 0, block=False)

# ====================================================================== tile + metatile banks
class Bank:
    def __init__(self):
        self.tiles = [(0,)*64]; self.lut = {(0,)*64: (0, 0, 0)}
        self.metas = []; self.attrs = []; self.mlut = {}
    def tile(self, t):
        t = tuple(t)
        if t in self.lut: return self.lut[t]
        for h in (0, 1):
            for v in (0, 1):
                f = flip(t, h, v)
                if f in self.lut and self.lut[f][1:] == (0, 0):
                    i = self.lut[f][0]; self.lut[t] = (i, h, v); return self.lut[t]
        i = len(self.tiles); self.tiles.append(t); self.lut[t] = (i, 0, 0); return self.lut[t]
    def entry(self, t, pal):
        if t is None: return 0
        i, h, v = self.tile(t); return i | (h << 10) | (v << 11) | (pal << 12)
    def meta(self, entries, attr):
        key = (tuple(entries), attr)
        if key not in self.mlut:
            self.mlut[key] = len(self.metas); self.metas.append(list(entries)); self.attrs.append(attr)
        return self.mlut[key]
BK = Bank()

def ground_quadrant(qx, qy):
    extra = GEXTRA.get((qx*8 + 4, qy*8 + 4), 0)
    s = stage(qx, qy, extra)
    slot = 0 if s <= 1 else 1
    out = []
    for j in range(8):
        for i in range(8):
            x, y = qx*8 + i, qy*8 + j
            lv = px_level(s, x, y)
            lv = min(lv, 1) if slot == 0 else max(lv, 1)
            out.append(gidx(slot, lv, GMAT[y][x], GSH[y][x]))
    return slot, out

def building_quadrant(cx, cy, qx, qy):
    out = []
    for j in range(8):
        for i in range(8):
            out.append(BR.get((cx*16 + qx*8 + i, cy*16 + qy*8 + j), R2))
    return out

WALKABLE, BLOCKED = 0x3000, 0x0400
LAYER_NORMAL, LAYER_COVERED = 0, 1
MB_NORMAL = 0x00
blocks = []
for cy in range(H):
    for cx in range(W):
        t = T[cy][cx]
        if t in 'BK':
            slot = BSLOT[(cx, cy)]
            bot = [BK.entry(building_quadrant(cx, cy, qx, qy), slot) for qy in (0, 1) for qx in (0, 1)]
            blocked = t == 'B' or STOOP.get((cx, cy)) == 'well'
        else:
            bot = []
            for qy in (0, 1):
                for qx in (0, 1):
                    slot, tl_ = ground_quadrant(cx*2 + qx, cy*2 + qy); bot.append(BK.entry(tl_, slot))
            blocked = False
        top = [0]*4; layer = LAYER_COVERED
        if (cx, cy) in TOP:
            qs, slot = TOP[(cx, cy)]
            top = [BK.entry(t_, slot) for t_ in qs]
            if (cx, cy) in WALKBEHIND: layer = LAYER_NORMAL
            if COLL.get((cx, cy)): blocked = True
        if (cx, cy) in BID:                       # door cells stay walkable so warps can be added
            bb = BUILDINGS[BID[(cx, cy)]]
            if cy == bb['f1'] and bb['ground'][cx - bb['x0']] in 'dDm': blocked = False
        mid = BK.meta(bot + top, MB_NORMAL | (layer << 12))
        blocks.append([mid, BLOCKED if blocked else WALKABLE])
# doors on the other buildings stay blocked until they get warps; open any door cell later in Porymap.

# ====================================================================== split primary / secondary
# Metatiles drawn only with primary palettes (0-5: ground and buildings) go in the primary; anything
# using a secondary palette (props, warehouse, lights, neon) goes in the secondary, at ids 512+.
PRIM = [i for i, m in enumerate(BK.metas) if all((e >> 12) < 6 for e in m)]
SEC = [i for i, m in enumerate(BK.metas) if not all((e >> 12) < 6 for e in m)]
assert len(PRIM) <= 512 and len(SEC) <= 512, (len(PRIM), len(SEC))
GID = {old: k for k, old in enumerate(PRIM)}; GID.update({old: 512 + k for k, old in enumerate(SEC)})

# ====================================================================== write
PALS = [[(0, 0, 0)]*16 for _ in range(16)]
for slot, p in [(0, PAL_G0), (1, PAL_G1), (2, scheme_pal('brick')), (3, scheme_pal('stucco')), (4, scheme_pal('clap')), (5, scheme_pal('brown')),
                (6, scheme_pal('corr')), (7, PAL_METAL_D), (8, PAL_METAL_L), (9, PAL_WARM_D), (10, PAL_WARM_L), (11, PAL_GLOW), (12, PAL_NEON)]:
    assert len(p) <= 16, (slot, len(p)); PALS[slot] = (list(p) + [(0, 0, 0)]*16)[:16]

# ---------------------------------------------------------------------- day palettes
# Same index layout as the night palettes. The ground's two light levels get the same colours,
# so the baked lamp pools vanish; lit windows read as glass with curtains, lamps and neon are off.
DAY_ASPH = [(116, 116, 122), (98, 98, 106), (80, 80, 90)]
DAY_CONC = [(186, 182, 172), (164, 160, 152), (134, 130, 124)]
DAY_PAINT = (222, 214, 184)
PAL_G_DAY = [(0, 0, 0)] + [q(c) for c in DAY_ASPH*2 + DAY_CONC*2] + [q(DAY_PAINT)]*2
DAY_GLASS = [(152, 186, 210), (86, 114, 150), (208, 226, 236), (122, 154, 186), (198, 178, 142)]
DAY_ROOF = [(150, 150, 158), (112, 113, 122), (56, 56, 66)]
DAY_SCHEMES = {
    'brick':  dict(wall=[(176, 98, 82), (150, 80, 68), (124, 64, 58), (96, 50, 50)], mortar=(150, 140, 130), trim=[(202, 198, 188), (140, 132, 126)]),
    'stucco': dict(wall=[(192, 186, 168), (170, 164, 148), (146, 140, 126), (118, 112, 102)], mortar=(122, 116, 106), trim=[(224, 222, 214), (152, 148, 142)]),
    'clap':   dict(wall=[(150, 160, 124), (128, 138, 106), (106, 114, 88), (82, 88, 70)], mortar=(66, 68, 58), trim=[(198, 186, 154), (128, 114, 92)]),
    'brown':  dict(wall=[(170, 120, 90), (148, 102, 78), (124, 84, 66), (98, 66, 54)], mortar=(92, 72, 62), trim=[(206, 192, 172), (142, 124, 108)]),
    'corr':   dict(wall=[(152, 168, 168), (128, 144, 146), (104, 118, 124), (78, 90, 98)], mortar=(158, 100, 68), trim=[(214, 188, 98), (130, 118, 98)],
                   roof=[(162, 168, 176), (118, 124, 136), (58, 62, 72)]),
}
def day_scheme_pal(s):
    S = DAY_SCHEMES[s]
    return [(0, 0, 0)] + [q(c) for c in S['wall'] + [S['mortar']] + S['trim'] + DAY_GLASS + S.get('roof', DAY_ROOF)]
def day_prop(c): return q((c[0]*1.04 + 4, c[1]*1.04 + 4, c[2]*1.02 + 4))
PAL_METAL_DAY = [(0, 0, 0)] + [day_prop(c) for c in FAMPAL['metal']]
PAL_WARM_DAY = [(0, 0, 0)] + [day_prop(c) for c in FAMPAL['warm']]
# neon off: pale tubes, halos and the backing board in board greys (index 11 is the board)
_BOARD, _EDGE = (58, 56, 66), (92, 90, 100)
PAL_NEON_DAY = [(0, 0, 0)] + [q(c) for c in [(214, 186, 206), _BOARD, _EDGE, (186, 214, 222), _BOARD, _BOARD,
                                             (220, 206, 158), (132, 168, 134), (220, 220, 226), (40, 38, 46), _BOARD]]
PALS_DAY = [[(0, 0, 0)]*16 for _ in range(16)]
for slot, p in [(0, PAL_G_DAY), (1, PAL_G_DAY), (2, day_scheme_pal('brick')), (3, day_scheme_pal('stucco')), (4, day_scheme_pal('clap')),
                (5, day_scheme_pal('brown')), (6, day_scheme_pal('corr')), (7, PAL_METAL_DAY), (8, PAL_METAL_DAY), (9, PAL_WARM_DAY),
                (10, PAL_WARM_DAY), (11, LAMP_DAY), (12, PAL_NEON_DAY)]:
    assert len(p) <= 16, (slot, len(p)); PALS_DAY[slot] = (list(p) + [(0, 0, 0)]*16)[:16]

def save():
    nt, nm = len(BK.tiles), len(BK.metas)
    assert nt <= 1024, ('too many tiles', nt); assert nm <= 1024, ('too many metatiles', nm)
    # tiles: first 512 primary, the rest secondary (tile index i >= 512 -> secondary slot i - 512)
    # metatiles: the bank's first 512 are primary ids 0..511, the rest are secondary ids 512+
    for d in (OUT_P, OUT_S):
        os.makedirs(d + '/palettes', exist_ok=True)
    os.makedirs(OUT_LY, exist_ok=True)
    for i in range(16):
        write_pal(f'{OUT_P}/palettes/{i:02d}.pal', PALS[i] if i < 6 else [(0, 0, 0)]*16)
        write_pal(f'{OUT_S}/palettes/{i:02d}.pal', PALS[i] if 6 <= i < 13 else [(0, 0, 0)]*16)
    def write_tiles(path, tiles):
        rows = max(1, (len(tiles) + 15)//16)
        im = Image.new('P', (128, rows*8)); im.putpalette([c for col in PALS[0] for c in col] + [0]*(768 - 48)); px = im.load()
        for i, t in enumerate(tiles):
            for j, c in enumerate(t): px[i % 16*8 + j % 8, i//16*8 + j//8] = c
        im.save(path)
    write_tiles(OUT_P + '/tiles.png', BK.tiles[:512]); write_tiles(OUT_S + '/tiles.png', BK.tiles[512:])
    pm, sm = [BK.metas[i] for i in PRIM], [BK.metas[i] for i in SEC]
    pa, sa = [BK.attrs[i] for i in PRIM], [BK.attrs[i] for i in SEC]
    open(OUT_P + '/metatiles.bin', 'wb').write(b''.join(struct.pack('<8H', *m) for m in pm))
    open(OUT_P + '/metatile_attributes.bin', 'wb').write(struct.pack('<%dH' % len(pa), *pa))
    open(OUT_S + '/metatiles.bin', 'wb').write(b''.join(struct.pack('<8H', *m) for m in sm))
    open(OUT_S + '/metatile_attributes.bin', 'wb').write(struct.pack('<%dH' % len(sa), *sa))
    gp = ROOT + '/src/data/tilesets/graphics.h'; g = open(gp).read()
    for d_, n_ in (('primary/d_low_quarter_street', min(512, nt)), ('secondary/d_low_quarter_night', max(1, nt - 512))):
        g = re.sub(r'(%s/tiles.png", "[^"]+", "-num_tiles )\d+' % re.escape(d_), lambda m: m.group(1) + str(n_), g)
    open(gp, 'w').write(g)
    gid = lambda m: GID[m]
    data = [gid(m) | c for m, c in blocks]
    open(OUT_LY + '/map.bin', 'wb').write(struct.pack('<%dH' % len(data), *data))
    roof_id = blocks[0*W + 2][0]                   # brick roof cell at (2, 0)
    open(OUT_LY + '/border.bin', 'wb').write(struct.pack('<4H', *[GID[roof_id]]*4))
    for d in (OUT_P_DAY, OUT_S_DAY): os.makedirs(d + '/palettes', exist_ok=True)
    os.makedirs(OUT_LY_DAY, exist_ok=True)
    for i in range(16):
        write_pal(f'{OUT_P_DAY}/palettes/{i:02d}.pal', PALS_DAY[i] if i < 6 else [(0, 0, 0)]*16)
        write_pal(f'{OUT_S_DAY}/palettes/{i:02d}.pal', PALS_DAY[i] if 6 <= i < 13 else [(0, 0, 0)]*16)
    open(OUT_LY_DAY + '/map.bin', 'wb').write(struct.pack('<%dH' % len(data), *data))
    open(OUT_LY_DAY + '/border.bin', 'wb').write(struct.pack('<4H', *[GID[roof_id]]*4))
    return nt, nm

def render(scale=2, pals=None):
    pals = pals or PALS
    im = Image.new('RGB', (PXW, PXH)); p = im.load()
    def tile_of(i): return BK.tiles[i]
    for b_i, (mid, col) in enumerate(blocks):
        m = BK.metas[mid]; bx, by = b_i % W*16, b_i//W*16
        for L in (0, 1):
            for qd in range(4):
                e = m[L*4 + qd]; t = flip(tile_of(e & 0x3ff), e & 0x400, e & 0x800); pal = pals[e >> 12]
                for j, c in enumerate(t):
                    if c: p[bx + qd % 2*8 + j % 8, by + qd//2*8 + j//8] = pal[c]
    big = im.resize((PXW*scale, PXH*scale), Image.NEAREST)
    colim = big.copy(); d = ImageDraw.Draw(colim, 'RGBA')
    for i, (mid, col) in enumerate(blocks):
        x, y = i % W*16*scale, i//W*16*scale
        if col & 0x0c00: d.rectangle([x, y, x + 16*scale - 1, y + 16*scale - 1], fill=(255, 0, 0, 80))
        if BK.attrs[mid] >> 12 == LAYER_NORMAL and any(BK.metas[mid][4:]): d.rectangle([x + 2, y + 2, x + 16*scale - 3, y + 16*scale - 3], outline=(0, 255, 255, 160))
    return im, big, colim

if __name__ == '__main__':
    nt, nm = save()
    im, big, colim = render(1)
    out = sys.argv[1] if len(sys.argv) > 1 else HERE
    im.save(out + '/night_map.png'); colim.save(out + '/night_collision.png')
    im.resize((PXW*2, PXH*2), Image.NEAREST).save(out + '/night_map_2x.png')
    dim, dbig, dcol = render(1, PALS_DAY)
    dim.save(out + '/day_map.png'); dim.resize((PXW*2, PXH*2), Image.NEAREST).save(out + '/day_map_2x.png')
    print('tiles', nt, 'metatiles', nm, '(primary', len(PRIM), 'secondary', len(SEC), ')')
