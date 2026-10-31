"""Builder for the Low Quarter Warehouse: gTileset_D_LowQuarterWarehouse + LAYOUT_LOW_QUARTER_WAREHOUSE.

Re-runnable: writes the secondary tileset and the layout from scratch every run.
Run order: extract.py (cut props from vanilla maps) -> recolor.py (shared palettes) -> build_wh.py.
Lighting is baked: floor/wall pixels pick a light level (lit / mid / dark) from an elliptical
spotlight field, with ordered dithering at the band edges. Props use a mid or dark palette.
"""
import os, sys, struct, pickle, random, math
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tl import ROOT, write_pal, layout_pair, read_map, flip

OUT_TS = ROOT + '/data/tilesets/secondary/d_low_quarter_warehouse'
OUT_LY = ROOT + '/data/layouts/LowQuarterWarehouse'
HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 21, 16                 # map size in cells
WALL_ROWS = 3                 # rows 0..2 are the back wall
CX, CY = 10.5*16, 9.5*16      # spotlight centre (px): centre of cell (10, 9)
RX, RY = 5.6*16, 5.4*16       # spotlight radii (px)

# ------------------------------------------------------------------ palettes
def q(c): return tuple((max(0, min(255, int(v))) >> 3) << 3 for v in c)
LIT  = [q(c) for c in [(184,176,152), (160,152,132), (136,128,112), (104, 98, 88)]]
MID  = [q(c) for c in [(112,108,100), ( 96, 92, 86), ( 82, 79, 75), ( 62, 60, 58)]]
DARK = [q(c) for c in [( 64, 63, 68), ( 54, 53, 59), ( 45, 45, 51), ( 33, 33, 39)]]
PAINT = {0: q((228,224,206)), 1: q((140,137,128))}     # faded white line paint
RED   = {0: q((170, 92, 70)), 1: q((108, 66, 56))}     # faded red centre paint
PAL_FLOOR_LM = [(0,0,0)] + LIT + MID + [PAINT[0], PAINT[1], RED[0], RED[1]]       # slot 6
PAL_FLOOR_MD = [(0,0,0)] + MID + DARK                                             # slot 7
# floor palette lookups: (pal slot, level, shade) -> colour index
def fidx(slot, level, shade):
    return (1 + shade + (0 if level == 0 else 4)) if slot == 6 else (1 + shade + (0 if level == 1 else 4))

PROP_PAL, IDX, META = pickle.load(open(HERE + '/props.pkl', 'rb'))
def mid_of(c):  return q(tuple(v*0.86 for v in c))
def dark_of(c): return q(tuple(v*0.50 + t for v, t in zip(c, (6, 6, 16))))
PAL_WARM_M  = [(0,0,0)] + [mid_of(c) for c in PROP_PAL['warm']]
PAL_WARM_D  = [(0,0,0)] + [dark_of(c) for c in PROP_PAL['warm']]
PAL_METAL_M = [(0,0,0)] + [mid_of(c) for c in PROP_PAL['metal']]
PAL_METAL_D = [(0,0,0)] + [dark_of(c) for c in PROP_PAL['metal']]
# rubber exit mat, drawn in the warm palette (dark rubber, worn brown rim)
_wp = PROP_PAL['warm']; _lum = sorted(range(len(_wp)), key=lambda i: sum(_wp[i]))
_d0, _d1, _rim = _lum[0] + 1, _lum[1] + 1, _lum[4] + 1
IDX['mat'] = [[0 if (i in (0, 15) or j in (0, 15)) else _rim if (i in (1, 14) or j in (1, 14)) else (_d1 if ((i - 2)//3 + (j - 2)//3) % 2 else _d0)
               for i in range(16)] for j in range(16)]
META['mat'] = ([[0]], 'warm')
# rows at the top of a free-standing prop the player can walk behind (drawn over the player)
WALK_BEHIND = {'crate3': 1, 'crate2': 1, 'crate3b': 1, 'crate_stack': 1, 'drum': 1, 'drum_stack': 1,
               'lumber': 1, 'lumber_tall': 1, 'trash': 1}
def prop_blocks(name, cy):
    if name == 'mat': return False
    return cy >= WALK_BEHIND.get(name, 0)
PROP_SLOT = {('warm', 1): 8, ('warm', 2): 9, ('metal', 1): 10, ('metal', 2): 11}

# ------------------------------------------------------------------ light field
BAYER = [[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]
def light(x, y):
    """0 = lit, 1 = mid, 2 = dark (continuous)."""
    d = math.hypot((x - CX) / RX, (y - CY) / RY)
    def ramp(a, b): return min(1, max(0, (d - a) / (b - a)))
    return ramp(0.86, 1.12) + ramp(1.32, 1.78)
def stage(qx, qy):           # light stage of an 8x8 quadrant, in steps of 1/4
    return round(light(qx*8 + 4, qy*8 + 4) * 4) / 4
def px_level(s, x, y):
    base = int(s) if s < 2 else 2; f = s - base
    return base + (1 if f > 0 and BAYER[y % 4][x % 4] < f*16 else 0)

# ------------------------------------------------------------------ concrete texture (32x32 period)
rng = random.Random(7)
TEX = [[1]*32 for _ in range(32)]
for y in range(16):
    for x in range(16):
        r = rng.random()
        if r < 0.10: TEX[y][x] = 0
        elif r < 0.22: TEX[y][x] = 2
for i in range(16):                      # slab joints every cell, light bevel above/left
    TEX[15][i] = 3; TEX[i][15] = 3; TEX[0][i] = 0 if TEX[0][i] != 2 else 1; TEX[i][0] = 0 if TEX[i][0] != 2 else 1
TEX[15][15] = 3
for y in range(32):
    for x in range(32): TEX[y][x] = TEX[y % 16][x % 16]

# decals: shade overrides in map pixel space (oil stains, cracks)
DECAL = {}
def stain(cx, cy, r, seed):
    rr = random.Random(seed)
    for y in range(int(cy - r - 2), int(cy + r + 3)):
        for x in range(int(cx - r - 2), int(cx + r + 3)):
            dd = math.hypot((x - cx) * 0.8, y - cy) + rr.uniform(-1.6, 1.6)
            if dd < r: DECAL[(x, y)] = 3 if dd < r*0.7 else 2
def crack(x, y, n, seed, dx=1):
    rr = random.Random(seed)
    for _ in range(n):
        DECAL[(x, y)] = 3
        x += dx; y += rr.choice((-1, 0, 0, 1))
stain(4*16+6, 9*16+10, 9, 1)       # oil under the left aisle
stain(16*16+2, 10*16+6, 7, 2)      # oil by the generator side
stain(12*16+10, 4*16+6, 5, 3)
crack(7*16+2, 13*16+12, 22, 4)
crack(13*16, 6*16+3, 18, 5)

# ring paint (pixel masks)
PAINT_MASK = set(); RED_MASK = set()
RX0, RY0, RX1, RY1 = 6*16 + 3, 5*16 + 3, 15*16 - 4, 14*16 - 4     # ring rectangle (inclusive px)
for x in range(RX0, RX1 + 1):
    for t in (0, 1): PAINT_MASK |= {(x, RY0 + t), (x, RY1 - t)}
for y in range(RY0, RY1 + 1):
    for t in (0, 1): PAINT_MASK |= {(RX0 + t, y), (RX1 - t, y)}
MIDY = 9*16 + 8
for x in range(RX0, RX1 + 1): PAINT_MASK |= {(x, MIDY), (x, MIDY + 1)}
ccx = 10*16 + 8
for y in range(MIDY - 22, MIDY + 23):
    for x in range(ccx - 22, ccx + 23):
        dd = math.hypot(x - ccx, y - MIDY)
        if 19.0 <= dd < 21.5: PAINT_MASK.add((x, y))
        if 7.5 <= dd < 10.0: RED_MASK.add((x, y))
for (sy) in (RY0 + 22, RY1 - 22):   # starting marks for the two trainers
    for x in range(ccx - 6, ccx + 7): PAINT_MASK.add((x, sy))
chip = random.Random(11); CHIP = [[chip.random() for _ in range(16)] for _ in range(16)]
PAINT_MASK = {p for p in PAINT_MASK if CHIP[p[1] % 16][p[0] % 16] > 0.10}
RED_MASK = {p for p in RED_MASK if CHIP[p[1] % 16][p[0] % 16] > 0.25}

# exit mat (rubber, floor colours) at (10, 15)
MAT = (10, 15)

SHADOW = {}
def cast_shadow(x0, y0, w, h, strength=0.9, reach=7):
    """Shadow of a prop's base footprint, pushed away from the spotlight."""
    bx0, bx1, by0, by1 = x0*16 + 2, (x0 + w)*16 - 2, (y0 + h - 1)*16 + 4, (y0 + h)*16
    mx, my = (bx0 + bx1)/2 - CX, (by0 + by1)/2 - CY; n = math.hypot(mx, my) or 1; dx, dy = mx/n, my/n
    for k in range(1, reach + 1):
        for y in range(by0, by1):
            for x in range(bx0, bx1):
                p = (int(round(x + dx*k)), int(round(y + dy*k)))
                SHADOW[p] = max(SHADOW.get(p, 0), strength * (1 - (k - 1)/(reach*1.4)))

def floor_quadrant(qx, qy):
    """Return (pal_slot, 64 colour indices) for the floor quadrant at quadrant coords."""
    s = stage(qx, qy)
    slot = 6 if s <= 1 else 7
    out = []
    for j in range(8):
        for i in range(8):
            x, y = qx*8 + i, qy*8 + j
            lv = px_level(min(2, round((s + SHADOW.get((x, y), 0))*4)/4), x, y) if (x, y) in SHADOW else px_level(s, x, y)
            if slot == 6: lv = min(lv, 1)
            else: lv = max(lv, 1)
            shade = DECAL.get((x, y), TEX[y % 32][x % 32])
            cx_, cy_ = x // 16, y // 16
            if slot == 6 and (x, y) in RED_MASK: out.append(11 + lv); continue
            if slot == 6 and (x, y) in PAINT_MASK: out.append(9 + lv); continue
            out.append(fidx(slot, lv, shade))
    return slot, out

# ------------------------------------------------------------------ wall (Power Plant girder wall, own palette)
def build_wall():
    P, l = layout_pair('LAYOUT_POWER_PLANT'); m = read_map(ROOT + '/' + l['blockdata_filepath']); w = l['width']
    cells = {}
    for cx in range(1, 10):
        for cy in range(3):
            cells[(cx, cy)] = P.render_meta(m[cy*w + cx] & 0x3ff)
    # recolour into the shared metal palette, so the wall can switch mid/dark by palette alone
    from recolor import grade, nearest
    pal = PROP_PAL['metal']; cache = {}; idx = {}
    for k, im in cells.items():
        a = []
        for j in range(16):
            row = []
            for i in range(16):
                g = grade(im.getpixel((i, j)), 'metal')
                if g not in cache: cache[g] = nearest(g, pal) + 1
                row.append(cache[g])
            a.append(row)
        idx[k] = a
    return idx
WALL_IDX = build_wall()
# wall column pattern: pillar, brace L (2), plain (5), brace R (2), pillar, ...
def wall_src_col(x):
    k = x % 10
    return {0: 1, 1: 2, 2: 3, 8: 7, 9: 8}.get(k, 4)

# ------------------------------------------------------------------ banks
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
        i, h, v = self.tile(t); return (512 + i) | (h << 10) | (v << 11) | (pal << 12)
    def meta(self, entries, attr):
        key = (tuple(entries), attr)
        if key not in self.mlut:
            self.mlut[key] = 512 + len(self.metas); self.metas.append(list(entries)); self.attrs.append(attr)
        return self.mlut[key]
B = Bank()
BLANK = 512   # secondary tile 0, all transparent

def quads(arr, cx, cy):
    """Four 8x8 tiles (TL,TR,BL,BR) of a cell from a 2-D index array."""
    out = []
    for qy in (0, 1):
        for qx in (0, 1):
            out.append([arr[cy*16 + qy*8 + j][cx*16 + qx*8 + i] for j in range(8) for i in range(8)])
    return out

def floor_entries(x, y):
    return [B.entry(*reversed(floor_quadrant(x*2 + qx, y*2 + qy))) for qy in (0, 1) for qx in (0, 1)]

def wall_entries(x, y):
    src = WALL_IDX[(wall_src_col(x), y)]
    slot = 10 if light((x + 0.5)*16, (y + 0.5)*16) < 1.62 else 11
    return [B.entry([src[qy*8 + j][qx*8 + i] for j in range(8) for i in range(8)], slot) for qy in (0, 1) for qx in (0, 1)]

# ------------------------------------------------------------------ layout
WALKABLE, BLOCKED = 0x3000, 0x0400
LAYER_NORMAL, LAYER_COVERED = 0, 1
# (prop, x, y) top-left cell
PLACE = [
    # back wall fittings
    ('lockers', 2, 1), ('terminal', 4, 1), ('hook', 7, 1), ('hook', 13, 1), ('panels', 14, 1), ('shelf', 18, 1),
    # left side: crates and drums
    ('crate3', 1, 3), ('crate_stack', 1, 6), ('drum_stack', 3, 6), ('drum', 4, 3), ('lumber_tall', 1, 10),
    ('rubble', 2, 9), ('debris2', 3, 11),
    # ring posts
    ('girder', 5, 4), ('girder', 15, 4), ('girder', 5, 11), ('girder', 15, 11),
    # right side: machinery
    ('engine', 17, 3), ('trash', 16, 7), ('generator', 17, 11),
    # back aisle clutter
    ('box', 9, 3), ('box_open', 11, 3),
    # front: pallet, boxes, bench for the crowd
    ('pallet', 2, 13), ('box', 4, 14), ('box_open2', 1, 14), ('debris', 7, 15), ('bench', 12, 14),
    ('rubble', 6, 14), ('mat', 10, 15),
]

for name, x, y in PLACE:
    a = IDX[name]; col, fam = META[name]; h, w = len(a)//16, len(a[0])//16
    if y >= WALL_ROWS and name != 'mat': cast_shadow(x, y, w, h)
for x in range(-4, W*16 + 4):                 # soft shadow along the foot of the back wall
    for k in range(7): SHADOW[(x, WALL_ROWS*16 + k)] = max(SHADOW.get((x, WALL_ROWS*16 + k), 0), 0.8*(1 - k/7))
grid = {}            # (x,y) -> (bottom entries, top entries, collision, layer)
for y in range(H):
    for x in range(W):
        if y < WALL_ROWS: grid[(x, y)] = [wall_entries(x, y), [BLANK]*4, BLOCKED, LAYER_COVERED]
        else:             grid[(x, y)] = [floor_entries(x, y), [BLANK]*4, WALKABLE, LAYER_NORMAL]

def prop_level(name, x, y):
    a = IDX[name]; h, w = len(a)//16, len(a[0])//16
    return 1 if light((x + w/2)*16, (y + h - 0.5)*16) < 1.45 else 2

placed_cells = set()
for name, x, y in PLACE:
    a = IDX[name]; col, fam = META[name]; h, w = len(a)//16, len(a[0])//16
    slot = PROP_SLOT[(fam, prop_level(name, x, y))]
    for cy in range(h):
        for cx in range(w):
            tq = quads(a, cx, cy)
            if not any(any(t) for t in tq): continue
            g = grid[(x + cx, y + cy)]
            g[1] = [B.entry(t, slot) if any(t) else BLANK for t in tq]
            on_wall = y + cy < WALL_ROWS
            blocked = on_wall or prop_blocks(name, cy)
            g[2] = BLOCKED if blocked else WALKABLE
            g[3] = LAYER_COVERED if blocked else LAYER_NORMAL
            placed_cells.add((x + cx, y + cy))

# ------------------------------------------------------------------ metatile order
# Porymap shows 8 metatiles per row. Map-only metatiles (floor, walls, placed props on lit floor)
# come first; then a prop pool packed so every prop assembles in the 8-wide picker,
# first on dark floor, then on mid floor. Padding slots repeat the plain floor.
MB_SOUTH_ARROW_WARP = 0x65
map_keys = []
for y in range(H):
    for x in range(W):
        bot, top, col, layer = grid[(x, y)]
        beh = MB_SOUTH_ARROW_WARP if (x, y) == MAT else 0
        map_keys.append((tuple(bot + top), beh | (layer << 12), col))

def pack(lv):
    floor = floor_entries(*{2: (0, 3), 1: (8, 3)}[lv])     # a dark cell / a mid-lit cell of the real floor
    pad = (tuple(floor + [BLANK]*4), 0)
    order = sorted([n for n in IDX if n != 'mat'], key=lambda n: (-len(IDX[n]), -len(IDX[n][0]), n))
    shelves = []                                          # each: [height, used_cols, rows-of-slots]
    for name in order:
        a = IDX[name]; col, fam = META[name]; h, w = len(a)//16, len(a[0])//16
        cells = [[None]*w for _ in range(h)]
        for cy in range(h):
            for cx in range(w):
                tq = quads(a, cx, cy)
                if any(any(t) for t in tq):
                    cells[cy][cx] = (tuple(floor + [B.entry(t, PROP_SLOT[(fam, lv)]) if any(t) else BLANK for t in tq]),
                                     LAYER_COVERED << 12 if prop_blocks(name, cy) else 0)
        sh = next((s_ for s_ in shelves if s_[0] >= h and s_[1] + w <= 8), None)
        if sh is None: sh = [h, 0, [[None]*8 for _ in range(h)]]; shelves.append(sh)
        for cy in range(h):
            for cx in range(w): sh[2][cy][sh[1] + cx] = cells[cy][cx]
        sh[1] += w
    slots = []
    for sh in shelves:
        for row in sh[2]: slots += [c or pad for c in row]
    return slots

pool = pack(2) + pack(1)
pool_first = {}
for i, k in enumerate(pool): pool_first.setdefault(k, i)
head = []; head_ix = {}
for key, beh, col in map_keys:
    k = (key, beh)
    if k not in pool_first and k not in head_ix: head_ix[k] = len(head); head.append(k)
pad_n = (-len(head)) % 8                                  # start the pool on a fresh picker row
head += [head[0]]*pad_n
B.metas = [list(k[0]) for k in head] + [list(k[0]) for k in pool]
B.attrs = [k[1] for k in head] + [k[1] for k in pool]
def mid_of_key(k): return 512 + (head_ix[k] if k in head_ix else len(head) + pool_first[k])
blocks = [mid_of_key((key, beh)) | col for key, beh, col in map_keys]
n_map_metas = len(head)

# ------------------------------------------------------------------ write
def save():
    assert len(B.tiles) <= 512, ('too many tiles', len(B.tiles))
    assert len(B.metas) <= 512, ('too many metatiles', len(B.metas))
    os.makedirs(OUT_TS + '/palettes', exist_ok=True); os.makedirs(OUT_LY, exist_ok=True)
    pals = [[(0, 0, 0)]*16 for _ in range(16)]
    for slot, p in ((6, PAL_FLOOR_LM), (7, PAL_FLOOR_MD), (8, PAL_WARM_M), (9, PAL_WARM_D),
                    (10, PAL_METAL_M), (11, PAL_METAL_D)):
        assert len(p) <= 16, (slot, len(p)); pals[slot] = (list(p) + [(0, 0, 0)]*16)[:16]
    for i, p in enumerate(pals): write_pal(f'{OUT_TS}/palettes/{i:02d}.pal', p)
    n = len(B.tiles); rows = (n + 15) // 16
    im = Image.new('P', (128, rows*8)); im.putpalette([c for col in pals[6] for c in col] + [0]*(768 - 48)); px = im.load()
    for i, t in enumerate(B.tiles):
        for j, c in enumerate(t): px[i % 16*8 + j % 8, i//16*8 + j//8] = c
    im.save(OUT_TS + '/tiles.png')
    open(OUT_TS + '/metatiles.bin', 'wb').write(b''.join(struct.pack('<8H', *m) for m in B.metas))
    open(OUT_TS + '/metatile_attributes.bin', 'wb').write(struct.pack('<%dH' % len(B.attrs), *B.attrs))
    open(OUT_LY + '/map.bin', 'wb').write(struct.pack('<%dH' % len(blocks), *blocks))
    import re
    gp = ROOT + '/src/data/tilesets/graphics.h'; g = open(gp).read()
    g = re.sub(r'(d_low_quarter_warehouse/tiles.png", ".4bpp.fastSmol", "-num_tiles )\w+', lambda m: m.group(1) + str(n), g)
    open(gp, 'w').write(g)
    open(OUT_LY + '/border.bin', 'wb').write(struct.pack('<4H', 1, 1, 1, 1))
    return pals

def render(pals, scale=2):
    """Render the map exactly from the written banks (no game code)."""
    im = Image.new('RGB', (W*16, H*16)); p = im.load()
    for b_i, b in enumerate(blocks):
        m = B.metas[(b & 0x3ff) - 512]; bx, by = b_i % W*16, b_i//W*16
        for L in (0, 1):
            for qd in range(4):
                e = m[L*4 + qd]; t = B.tiles[(e & 0x3ff) - 512]; t = flip(t, e & 0x400, e & 0x800); pal = pals[e >> 12]
                for j, c in enumerate(t):
                    if c: p[bx + qd % 2*8 + j % 8, by + qd//2*8 + j//8] = pal[c]
    big = im.resize((W*16*scale, H*16*scale), Image.NEAREST)
    colim = big.copy(); d = ImageDraw.Draw(colim, 'RGBA')
    for i, b in enumerate(blocks):
        if (b >> 10) & 3:
            x, y = i % W*16*scale, i//W*16*scale; d.rectangle([x, y, x + 16*scale - 1, y + 16*scale - 1], fill=(255, 0, 0, 90))
    return im, big, colim

if __name__ == '__main__':
    pals = save()
    im, big, colim = render(pals)
    big.save(HERE + '/preview_map.png'); colim.save(HERE + '/preview_collision.png')
    print('tiles', len(B.tiles), 'metatiles', len(B.metas), '(map uses', n_map_metas, ')')
