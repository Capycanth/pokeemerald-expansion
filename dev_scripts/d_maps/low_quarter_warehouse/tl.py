"""Tileset/map helpers from docs/map-and-tileset-guide.md, plus FRLG-aware pairs and layout crops."""
import struct, os
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
TS = ROOT + '/data/tilesets'

def read_pal(p):
    l = open(p).read().split('\n'); n = int(l[2])
    return [tuple(map(int, x.split())) for x in l[3:3+n]]

def write_pal(p, cols):
    cols = (list(cols) + [(0,0,0)]*16)[:16]
    with open(p, 'w', newline='\r\n') as f:            # CRLF like the originals
        f.write('JASC-PAL\n0100\n16\n' + ''.join('%d %d %d\n' % c for c in cols))

def flip(t, h, v):
    return tuple(t[(7-y if v else y)*8 + (7-x if h else x)] for y in range(8) for x in range(8))

class Tileset:
    def __init__(self, kind, name):
        self.dir = f'{TS}/{kind}/{name}'
        im = Image.open(self.dir + '/tiles.png'); self.png = im; px = im.load(); w, h = im.size
        self.tiles = [tuple(px[tx*8+x, ty*8+y] & 15 for y in range(8) for x in range(8))
                      for ty in range(h//8) for tx in range(w//8)]
        self.pals = [read_pal(f'{self.dir}/palettes/{i:02d}.pal') for i in range(16)]
        d = open(self.dir + '/metatiles.bin', 'rb').read(); v = struct.unpack('<%dH' % (len(d)//2), d)
        self.metatiles = [list(v[i:i+8]) for i in range(0, len(v), 8)]
        d = open(self.dir + '/metatile_attributes.bin', 'rb').read()
        self.attrs = list(struct.unpack('<%dH' % (len(d)//2), d))

    def save(self, ntiles=512):
        rows = (ntiles + 15)//16; im = Image.new('P', (128, rows*8)); im.putpalette(self.png.getpalette()); px = im.load()
        for i, t in enumerate(self.tiles[:rows*16]):
            for j, c in enumerate(t): px[i%16*8 + j%8, i//16*8 + j//8] = c
        im.save(self.dir + '/tiles.png')
        for i, p in enumerate(self.pals): write_pal(f'{self.dir}/palettes/{i:02d}.pal', p)
        open(self.dir + '/metatiles.bin', 'wb').write(b''.join(struct.pack('<8H', *m) for m in self.metatiles))
        open(self.dir + '/metatile_attributes.bin', 'wb').write(struct.pack('<%dH' % len(self.attrs), *self.attrs))

class Pair:                                            # primary + secondary, as the game sees them
    def __init__(self, p, s): self.p, self.s = p, s
    def tile(self, i): ts, i = (self.p, i) if i < 512 else (self.s, i-512); return ts.tiles[i] if i < len(ts.tiles) else (0,)*64
    def pal(self, n): return self.p.pals[n] if n < 6 else self.s.pals[n]
    def meta(self, m): ts, m = (self.p, m) if m < 512 else (self.s, m-512); return ts.metatiles[m] if m < len(ts.metatiles) else [0]*8
    def attr(self, m): return self.p.attrs[m] if m < 512 else self.s.attrs[m-512]
    def render_meta(self, mid, layers=(0, 1)):
        im = Image.new('RGB', (16, 16), self.pal(0)[0]); px = im.load(); m = self.meta(mid)
        for L in layers:
            for q in range(4):
                e = m[L*4+q]; t = flip(self.tile(e & 0x3ff), e & 0x400, e & 0x800); pal = self.pal(e >> 12)
                for j, c in enumerate(t):
                    if c: px[q%2*8 + j%8, q//2*8 + j//8] = pal[c]
        return im
    def render_map(self, blocks, w, h, scale=2):
        im = Image.new('RGB', (w*16, h*16)); cache = {}
        for i, b in enumerate(blocks):
            mid = b & 0x3ff; cache.setdefault(mid, self.render_meta(mid)); im.paste(cache[mid], (i%w*16, i//w*16))
        return im.resize((w*16*scale, h*16*scale), Image.NEAREST)

def read_map(p): d = open(p, 'rb').read(); return list(struct.unpack('<%dH' % (len(d)//2), d))
def write_map(p, b): open(p, 'wb').write(struct.pack('<%dH' % len(b), *b))

# ---- additions: resolve tileset symbols, FRLG-aware pairs ----
import re, json, os
_H = open(ROOT+'/src/data/tilesets/headers.h').read()
_G = open(ROOT+'/src/data/tilesets/graphics.h').read() + open(ROOT+'/src/data/tilesets/metatiles.h').read() + open(ROOT+'/src/graphics.c').read()
def _path(sym):
    m = re.search(r'\b%s\b\[\][^\n]*?"([^"]+)"' % re.escape(sym), _G) or re.search(r'\b%s\b\[\]\[16\]\s*=\s*\{\s*INCGFX_U16\("([^"]+)"' % re.escape(sym), _G)
    return os.path.dirname(m.group(1)).replace('/palettes','')
class TS2(Tileset):
    def __init__(self, sym):
        b = re.search(r'const struct Tileset %s =\s*\{(.*?)\};' % sym, _H, re.S).group(1)
        f = dict(re.findall(r'\.(\w+)\s*=\s*(\w+)', b))
        self.sym = sym
        tdir = ROOT+'/'+_path(f['tiles']); pdir = ROOT+'/'+_path(f['palettes']); mdir = ROOT+'/'+_path(f['metatiles'])
        im = Image.open(tdir + '/tiles.png'); self.png = im; px = im.load(); w, h = im.size
        self.tiles = [tuple(px[tx*8+x, ty*8+y] & 15 for y in range(8) for x in range(8)) for ty in range(h//8) for tx in range(w//8)]
        self.pals = [read_pal(f'{pdir}/palettes/{i:02d}.pal') for i in range(16)]
        d = open(mdir + '/metatiles.bin', 'rb').read(); v = struct.unpack('<%dH' % (len(d)//2), d)
        self.metatiles = [list(v[i:i+8]) for i in range(0, len(v), 8)]
        d = open(mdir + '/metatile_attributes.bin', 'rb').read()
        self.attrs = list(struct.unpack('<%dH' % (len(d)//2), d))
        self.dir = mdir
class PairX(Pair):
    def __init__(self, p, s, frlg=False):
        self.p, self.s = p, s; self.NT = 640 if frlg else 512; self.NP = 7 if frlg else 6
    def tile(self, i): ts, i = (self.p, i) if i < self.NT else (self.s, i-self.NT); return ts.tiles[i] if i < len(ts.tiles) else (0,)*64
    def pal(self, n): return self.p.pals[n] if n < self.NP else self.s.pals[n]
    def meta(self, m): ts, m = (self.p, m) if m < self.NT else (self.s, m-self.NT); return ts.metatiles[m] if m < len(ts.metatiles) else [0]*8
    def attr(self, m): return self.p.attrs[m] if m < self.NT else self.s.attrs[m-self.NT]
    def render_meta(self, mid, layers=(0, 1)):
        im = Image.new('RGB', (16, 16), self.pal(0)[0]); px = im.load(); m = self.meta(mid)
        for L in layers:
            for q in range(4):
                e = m[L*4+q]; t = flip(self.tile(e & 0x3ff), e & 0x400, e & 0x800); pal = self.pal(e >> 12)
                for j, c in enumerate(t):
                    if c: px[q%2*8 + j%8, q//2*8 + j//8] = pal[c]
        return im
LAYOUTS = {l['id']: l for l in json.load(open(ROOT + '/data/layouts/layouts.json'))['layouts'] if 'id' in l}
def layout_pair(lid):
    l = LAYOUTS[lid]; fr = 'Frlg' in l['primary_tileset'] or '_Frlg' in l['primary_tileset']
    return PairX(TS2(l['primary_tileset']), TS2(l['secondary_tileset']), fr), l
def render_layout(lid, scale=2, grid=True):
    P, l = layout_pair(lid); m = read_map(ROOT+'/'+l['blockdata_filepath']); w, h = l['width'], l['height']
    im = P.render_map(m, w, h, scale)
    if grid:
        from PIL import ImageDraw; d = ImageDraw.Draw(im); s = 16*scale
        for x in range(0, w, 5): d.line([(x*s,0),(x*s,h*s)], fill=(255,0,255))
        for y in range(0, h, 5): d.line([(0,y*s),(w*s,y*s)], fill=(255,0,255))
    return im, P, l, m
def dump(lid):
    P, l = layout_pair(lid); m = read_map(ROOT+'/'+l['blockdata_filepath']); w = l['width']
    return '\n'.join('%2d ' % y + ' '.join('%03x' % (m[y*w+x] & 0x3ff) for x in range(w)) for y in range(l['height']))
def region(lid, x, y, w, h):
    P, l = layout_pair(lid); m = read_map(ROOT+'/'+l['blockdata_filepath']); W = l['width']; out=[]
    for yy in range(y, y+h):
        out.append(' '.join('%03x/%d%d%x' % (m[yy*W+xx]&0x3ff, (m[yy*W+xx]>>10)&3, P.attr(m[yy*W+xx]&0x3ff)>>12, P.attr(m[yy*W+xx]&0x3ff)&0xff) for xx in range(x, x+w)))
    return '\n'.join(out)
_RC = {}
def crop(lid, x, y, w, h, s=3):
    from PIL import ImageDraw
    if lid not in _RC: _RC[lid] = render_layout(lid, 1, False)
    im = _RC[lid][0].crop((x*16, y*16, (x+w)*16, (y+h)*16)).resize((w*16*s, h*16*s), Image.NEAREST)
    d = ImageDraw.Draw(im)
    for i in range(w+1): d.line([(i*16*s,0),(i*16*s,h*16*s)], fill=(255,0,255))
    for j in range(h+1): d.line([(0,j*16*s),(w*16*s,j*16*s)], fill=(255,0,255))
    for i in range(w): d.text((i*16*s+2,1), str(x+i), fill=(255,255,0))
    for j in range(h): d.text((1,j*16*s+12), str(y+j), fill=(0,255,255))
    return im
def montage(items, path, maxw=1400):
    from PIL import ImageDraw
    ims = [(t, crop(*a)) for t, a in items]; x=y=rowh=0; pos=[]
    for t, im in ims:
        if x + im.width > maxw: x = 0; y += rowh + 14; rowh = 0
        pos.append((x, y)); x += im.width + 8; rowh = max(rowh, im.height)
    out = Image.new('RGB', (maxw, y + rowh + 14), (30,30,30)); d = ImageDraw.Draw(out)
    for (t, im), (px, py) in zip(ims, pos): out.paste(im, (px, py+12)); d.text((px, py), t, fill=(255,255,255))
    out.save(path); return out.size
