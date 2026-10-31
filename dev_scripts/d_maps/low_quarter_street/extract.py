"""Cut the borrowed props for the Low Quarter streets out of vanilla maps (RGBA, source ground removed).

Reuses the warehouse cutter. Everything else on the street map is drawn procedurally in build.py.
"""
import os, sys, pickle
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'low_quarter_warehouse'))
import extract as WX                      # warehouse cutter: cut(), top_layer(), OBJS
from tl import *

SP = 'LAYOUT_SLATEPORT_CITY'; RB = 'LAYOUT_RUSTBORO_CITY'; BF = 'LAYOUT_BATTLE_FRONTIER_BATTLE_FACTORY_LOBBY'
SP_BG = [0x210, 0x211, 0x227, 0x22f, 0x285]
OBJS = {
    # market stall: Slateport tent and goods
    'tent':        (SP, 2, 41, 5, 3, 'warm', SP_BG),
    'bowl_teal':   (SP, 7, 43, 1, 1, 'warm', SP_BG),
    'bowl_orange': (SP, 7, 41, 1, 1, 'warm', SP_BG),
    'bowl_red':    (SP, 7, 45, 1, 1, 'warm', SP_BG),
    'flowers':     (SP, 8, 41, 1, 1, 'warm', SP_BG),
    'crate_lbl':   (SP, 7, 42, 1, 1, 'warm', SP_BG),
    'crate_slat':  (SP, 7, 46, 1, 1, 'warm', SP_BG),
    'pot':         (SP, 8, 47, 1, 1, 'warm', SP_BG),
    # street furniture
    'lamp':        (RB, 19, 15, 1, 2, 'metal', [0x2bb, 0x2c3]),
    'trash':       WX.OBJS['trash'],
    # yard clutter for the warehouse lot (same cuts as the warehouse interior)
    **{k: WX.OBJS[k] for k in ('crate3', 'crate2', 'crate_stack', 'pallet', 'box', 'box_open', 'debris', 'debris2', 'rubble', 'lumber')},
}
TOPS = {k: WX.TOPS[k] for k in ('drum', 'drum_stack')}

if __name__ == '__main__':
    out = {n: (WX.top_layer(n, TOPS[n]) if n in TOPS else WX.cut(n, s)) for n, s in list(OBJS.items()) + list(TOPS.items())}
    pickle.dump({n: (o.tobytes(), o.size, c, f) for n, (o, c, f) in out.items()}, open(os.path.join(HERE, 'objs.pkl'), 'wb'))
    from PIL import ImageDraw
    S = 3; x = y = rowh = 0; pos = {}
    for n, (o, c, f) in out.items():
        ww, hh = o.size[0]*S, o.size[1]*S
        if x + ww > 1300: x = 0; y += rowh + 16; rowh = 0
        pos[n] = (x, y); x += ww + 12; rowh = max(rowh, hh)
    cat = Image.new('RGB', (1300, y + rowh + 16), (40, 40, 40)); d = ImageDraw.Draw(cat)
    for n, (o, c, f) in out.items():
        px0, py0 = pos[n]; bgc = Image.new('RGBA', o.size, (255, 0, 255, 255)); bgc.alpha_composite(o)
        cat.paste(bgc.convert('RGB').resize((o.size[0]*S, o.size[1]*S), Image.NEAREST), (px0, py0+12)); d.text((px0, py0), n, fill=(255, 255, 255))
    cat.save(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'catalog.png')); print(cat.size)
