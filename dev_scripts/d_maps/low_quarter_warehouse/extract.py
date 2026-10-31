"""Cut warehouse props out of vanilla maps as RGBA images with the source floor removed."""
from tl import *
from PIL import ImageDraw
import pickle, os
HERE = os.path.dirname(os.path.abspath(__file__))

PP = 'LAYOUT_POWER_PLANT'; MV = 'LAYOUT_NEW_MAUVILLE_INSIDE'; SY = 'LAYOUT_SLATEPORT_CITY_STERNS_SHIPYARD_1F'
TD = 'LAYOUT_SS_TIDAL_LOWER_DECK'; RW = 'LAYOUT_FIVE_ISLAND_ROCKET_WAREHOUSE'; BF = 'LAYOUT_BATTLE_FRONTIER_BATTLE_FACTORY_LOBBY'
AQ = 'LAYOUT_AQUA_HIDEOUT_B1F'

# name: (layout, x, y, w, h, family, background metatile ids to strip)
OBJS = {
    # ---- warm family: wood, cardboard, drums, junk          (bg = source floor/wall metatiles to strip)
    'crate3':        (TD, 4, 5, 3, 3, 'warm', [0x20d, 0x21d, 0x2ee, 0x2e7, 0x2f6]),
    'crate2':        (TD, 8, 5, 2, 3, 'warm', [0x20d, 0x21d, 0x2ee, 0x2e7, 0x2f6]),
    'crate3b':       (TD, 11, 5, 3, 3, 'warm', [0x20d, 0x21d, 0x2ee, 0x2e7, 0x2f6]),
    'crate_stack':   (AQ, 21, 1, 2, 3, 'warm', [0x221, 0x229, 0x228, 0x22a, 0x2e0]),
    'pallet':        (RW, 2, 4, 2, 2, 'warm', [0x281, 0x282, 0x283, 0x284, 0x285, 0x286]),
    'box':           (MV, 1, 19, 1, 1, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'box_open':      (MV, 1, 18, 1, 1, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'box_open2':     (MV, 2, 17, 1, 1, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'debris':        (MV, 2, 19, 1, 1, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'debris2':       (MV, 3, 20, 1, 1, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'bench':         (MV, 4, 18, 2, 2, 'warm', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'lumber':        (SY, 18, 11, 1, 3, 'warm', [0x229, 0x228, 0x22a]),
    'lumber_tall':   (SY, 20, 10, 1, 4, 'warm', [0x229, 0x228, 0x22a]),
    'drum':          (PP, 24, 21, 1, 2, 'warm', [0x29f, 0x29d, 0x295]),
    'drum_stack':    (PP, 39, 3, 1, 4, 'warm', [0x29f, 0x29d]),
    'rubble':        (PP, 23, 22, 1, 1, 'warm', [0x29f, 0x29d]),
    # ---- metal family: steel, machines, rust
    'girder':        (SY, 7, 4, 1, 3, 'metal', [0x229, 0x228, 0x22a]),
    'girder_tall':   (SY, 10, 9, 1, 4, 'metal', [0x229, 0x228, 0x22a]),
    'hook':          (SY, 17, 0, 1, 2, 'metal', [0x219, 0x221]),
    'panels':        (SY, 8, 1, 3, 2, 'metal', [0x221, 0x229]),
    'engine':        (SY, 11, 4, 4, 6, 'metal', [0x229, 0x228, 0x22a]),
    'lab_machine':   (SY, 9, 4, 2, 4, 'metal', [0x229, 0x228, 0x22a]),
    'generator':     (MV, 32, 1, 4, 4, 'metal', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'lockers':       (MV, 12, 1, 2, 2, 'metal', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'terminal':      (MV, 14, 1, 1, 2, 'metal', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'shelf':         (MV, 27, 1, 2, 2, 'metal', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'tank':          (MV, 29, 1, 2, 3, 'metal', [0x210, 0x227, 0x22f, 0x237, 0x275, 0x27d, 0x27e, 0x27f, 0x21f, 0x22f]),
    'trash':         (BF, 15, 10, 1, 2, 'metal', [0x201, 0x202, 0x203, 0x204]),
    'pp_panel':      (PP, 27, 35, 1, 2, 'metal', [0x28d, 0x29f, 0x2a2]),
    'rw_machine':    (RW, 1, 0, 3, 3, 'metal', [0x289, 0x28a, 0x28b, 0x291, 0x292, 0x293, 0x282]),
}

def full_render(lid):
    P, l = layout_pair(lid); m = read_map(ROOT+'/'+l['blockdata_filepath']); w, h = l['width'], l['height']
    return P.render_map(m, w, h, 1).convert('RGB'), P, l, m

_cache = {}
def src(lid):
    if lid not in _cache: _cache[lid] = full_render(lid)
    return _cache[lid]

def cut(name, spec):
    lid, x, y, w, h, fam, bgs = spec
    im, P, l, m = src(lid)
    obj = im.crop((x*16, y*16, (x+w)*16, (y+h)*16)).convert('RGBA'); px = obj.load()
    W, H = w*16, h*16
    bgpx = [P.render_meta(mid).load() for mid in bgs]
    isbg = lambda i, j: any(px[i, j][:3] == b[i % 16, j % 16] for b in bgpx)
    if bgs:
        seen = set(); stack = [(i, j) for i in range(W) for j in (0, H-1)] + [(i, j) for j in range(H) for i in (0, W-1)]
        while stack:
            i, j = stack.pop()
            if (i, j) in seen or not (0 <= i < W and 0 <= j < H): continue
            seen.add((i, j))
            if isbg(i, j):
                px[i, j] = (0, 0, 0, 0); stack += [(i+1, j), (i-1, j), (i, j+1), (i, j-1)]
    if name in ('lockers', 'terminal', 'shelf'):   # wall-base row: drop floor-check pixels left under the object
        fl = P.render_meta(0x210).load(); y0 = (h-1)*16
        for i in range(W):
            for j in range(y0+3, H):
                if True: px[i, j] = (0, 0, 0, 0); continue
                if px[i, j][3] and px[i, j][:3] == fl[i % 16, j % 16]: px[i, j] = (0, 0, 0, 0)
    # per-cell source collision (1 = blocked)
    col = [[(m[(y+j)*l['width'] + x+i] >> 10) & 3 for i in range(w)] for j in range(h)]
    return obj, col, fam

# Props whose art sits wholly in the source metatiles' top layer: build them from that layer
# instead of cutting them off the floor (the floor shares colours with the lids).
# Power Plant drums: 2d1 = top of the lid, 2d8 = drum + next drum's lid, 2d9 = last drum.
TOPS = {
    'drum':       (PP, [[0x2d1], [0x2d9]], 'warm'),
    'drum_stack': (PP, [[0x2d1], [0x2d8], [0x2d8], [0x2d9]], 'warm'),
}

def top_layer(name, spec):
    lid, rows, fam = spec
    P, l = layout_pair(lid); h, w = len(rows), len(rows[0])
    im = Image.new('RGBA', (w*16, h*16), (0, 0, 0, 0)); px = im.load()
    for cy, row in enumerate(rows):
        for cx, mid in enumerate(row):
            m = P.meta(mid)
            for qd in range(4):
                e = m[4 + qd]; t = flip(P.tile(e & 0x3ff), e & 0x400, e & 0x800); pal = P.pal(e >> 12)
                for j, c in enumerate(t):
                    if c: px[cx*16 + qd % 2*8 + j % 8, cy*16 + qd//2*8 + j//8] = pal[c] + (255,)
    col = [[0 if cy == 0 else 1 for _ in range(w)] for cy in range(h)]
    return im, col, fam

if __name__ == '__main__':
    out = {n: (top_layer(n, TOPS[n]) if n in TOPS else cut(n, s)) for n, s in OBJS.items()}
    pickle.dump({n: (o.tobytes(), o.size, c, f) for n, (o, c, f) in out.items()}, open(os.path.join(HERE, 'objs.pkl'), 'wb'))
    # catalog image on a magenta checker so cut-outs are visible
    S = 3; x = y = rowh = 0; pos = {}
    for n, (o, c, f) in out.items():
        ww, hh = o.size[0]*S, o.size[1]*S
        if x + ww > 1300: x = 0; y += rowh + 16; rowh = 0
        pos[n] = (x, y); x += ww + 12; rowh = max(rowh, hh)
    cat = Image.new('RGB', (1300, y + rowh + 16), (40, 40, 40)); d = ImageDraw.Draw(cat)
    for n, (o, c, f) in out.items():
        px0, py0 = pos[n]; bgc = Image.new('RGBA', o.size, (255, 0, 255, 255))
        bgc.alpha_composite(o); cat.paste(bgc.convert('RGB').resize((o.size[0]*S, o.size[1]*S), Image.NEAREST), (px0, py0+12))
        d.text((px0, py0), n, fill=(255, 255, 255))
    cat.save(os.path.join(HERE, 'catalog_raw.png')); print(cat.size)
