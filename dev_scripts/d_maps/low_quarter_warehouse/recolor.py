"""Grade all props into two shared 'dingy' palettes (warm, metal) and count unique 8x8 tiles."""
import pickle, os, colorsys
HERE = os.path.dirname(os.path.abspath(__file__))
from PIL import Image
D = pickle.load(open(os.path.join(HERE, 'objs.pkl'), 'rb'))
DROP = {'rw_machine', 'lab_machine', 'tank', 'pp_panel'}
OBJ = {n: (Image.frombytes('RGBA', sz, b), c, f) for n, (b, sz, c, f) in D.items() if n not in DROP}

def grade(c, fam):
    r, g, b = [v/255 for v in c]; h, s, v = colorsys.rgb_to_hsv(r, g, b)
    if fam == 'warm':
        s *= 0.62; v = v*0.80 + 0.02
        # pull yellows/oranges toward a brown-ochre hue
        if 0.04 < h < 0.20: h = h*0.75 + 0.075*0.25
    else:
        s *= 0.40; v = v*0.76 + 0.02
        if 0.45 < h < 0.75: h = h*0.6 + 0.58*0.4     # blues/purples -> steel blue-grey
        if h < 0.06 or h > 0.92: s = min(1, s*1.6)   # keep rust reads as rust
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return tuple(int(round(x*255)) for x in (r, g, b))

def palette_for(fam, n=15):
    px = []
    for name, (im, c, f) in OBJ.items():
        if f != fam: continue
        px += [grade(p[:3], fam) for p in im.get_flattened_data() if p[3]]
    strip = Image.new('RGB', (len(px), 1)); strip.putdata(px)
    q = strip.quantize(colors=n, method=Image.Quantize.MEDIANCUT, kmeans=3)
    pal = q.getpalette()[:n*3]
    return [tuple((pal[i*3+k] >> 3) << 3 for k in range(3)) for i in range(n)]

def nearest(c, pal):
    return min(range(len(pal)), key=lambda i: sum((a-b)**2 * w for a, b, w in zip(c, pal[i], (3, 4, 2))))

def index_obj(name, pal):
    im, c, fam = OBJ[name]; W, H = im.size; px = im.load(); cache = {}
    out = [[0]*W for _ in range(H)]
    for y in range(H):
        for x in range(W):
            p = px[x, y]
            if p[3]:
                g = grade(p[:3], fam)
                if g not in cache: cache[g] = nearest(g, pal) + 1
                out[y][x] = cache[g]
    return out

if __name__ == '__main__':
    PAL = {f: palette_for(f) for f in ('warm', 'metal')}
    IDX = {n: index_obj(n, PAL[OBJ[n][2]]) for n in OBJ}
    pickle.dump((PAL, IDX, {n: (OBJ[n][1], OBJ[n][2]) for n in OBJ}), open(os.path.join(HERE, 'props.pkl'), 'wb'))
    def tiles(n):
        a = IDX[n]; H, W = len(a), len(a[0]); ts = []
        for ty in range(0, H, 8):
            for tx in range(0, W, 8):
                t = tuple(a[ty+j][tx+i] for j in range(8) for i in range(8))
                if any(t): ts.append(t)
        return ts
    def canon(t):
        f = lambda t, h, v: tuple(t[(7-y if v else y)*8 + (7-x if h else x)] for y in range(8) for x in range(8))
        return min(f(t, h, v) for h in (0, 1) for v in (0, 1))
    allt = set(); per = {}
    for n in IDX:
        ts = {canon(t) for t in tiles(n)}; per[n] = len(ts - allt); allt |= ts
    print('unique prop tiles', len(allt)); print(sorted(per.items(), key=lambda x: -x[1]))
    for f, p in PAL.items(): print(f, p)
