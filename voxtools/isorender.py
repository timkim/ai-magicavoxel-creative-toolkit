"""Tiny isometric voxel preview renderer (painter's algorithm, 3 face shades). Good for quick
contact sheets without opening MagicaVoxel; not a substitute for MagicaVoxel's renderer.

  python isorender.py scene.vox out.png                  # every object, side by side
  python isorender.py scene.vox out.png --objects 48_fire --scale 6
"""
import numpy as np
from PIL import Image
def render(voxels, palette, scale=4, bg=(40,40,44), rot=0):
    """voxels: iterable of (x,y,z,i); palette: list of 256 (r,g,b,a) where palette[i-1] is index i."""
    v = np.array([(x,y,z,i) for x,y,z,i in voxels], int)
    if rot:
        for _ in range(rot):
            mx = v[:,1].max(); v[:,[0,1]] = np.stack([mx - v[:,1], v[:,0]],1)
    occ = set(map(tuple, v[:,:3]))
    s = scale
    # iso: screen x = (x - y)*s, screen y = (x + y)*s/2 - z*s
    xs = (v[:,0]-v[:,1])*s; ys = (v[:,0]+v[:,1])*s//2 - v[:,2]*s
    W = int(xs.max()-xs.min()+4*s); H = int(ys.max()-ys.min()+4*s)
    img = Image.new('RGB',(W,H),bg); px = img.load()
    ox = -xs.min()+s; oy = -ys.min()+2*s
    order = np.lexsort((v[:,2], v[:,0]+v[:,1]))  # back to front
    from PIL import ImageDraw
    d = ImageDraw.Draw(img)
    for k in order:
        x,y,z,i = v[k]; c = palette[i-1][:3]
        X = xs[k]+ox; Y = ys[k]+oy
        top = [(X,Y-s//2*0),(X+s,Y+s//2),(X,Y+s),(X-s,Y+s//2)]
        top = [(X,Y),(X+s,Y+s//2),(X,Y+s),(X-s,Y+s//2)]
        left = [(X-s,Y+s//2),(X,Y+s),(X,Y+2*s),(X-s,Y+3*s//2)]
        right= [(X,Y+s),(X+s,Y+s//2),(X+s,Y+3*s//2),(X,Y+2*s)]
        sh = lambda f: tuple(int(a*f) for a in c)
        if (x,y,z+1) not in occ or True: d.polygon(top, fill=sh(1.0))
        d.polygon(left, fill=sh(0.62)); d.polygon(right, fill=sh(0.8))
    return img
def palette_of(path):
    from voxlib import read_chunks
    import struct
    for c in read_chunks(path)[1]:
        if c['id']=='RGBA': return [tuple(c['content'][4*i:4*i+4]) for i in range(256)]


if __name__ == '__main__':
    import argparse, sys
    from voxwrite import load_scene
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('vox'); ap.add_argument('png')
    ap.add_argument('--objects', nargs='+'); ap.add_argument('--scale', type=int, default=3)
    a = ap.parse_args()
    sc = load_scene(a.vox); pal = palette_of(a.vox) or [(128, 128, 128, 255)] * 256
    ims, seen = [], set()
    for nd in sc.nodes:
        if nd['type'] != 'nTRN': continue
        nm = nd['attrs'].get('_name'); ch = sc.nodes[nd['child']]
        if ch['type'] != 'nSHP' or not nm or nm in seen or (a.objects and nm not in a.objects): continue
        seen.add(nm); ims.append(render(sc.models[ch['models'][0][0]][1], pal, scale=a.scale))
    if not ims: sys.exit('no matching objects')
    W = sum(i.width for i in ims); H = max(i.height for i in ims)
    sheet = Image.new('RGB', (W, H), (40, 40, 44)); x = 0
    for i in ims: sheet.paste(i, (x, H - i.height)); x += i.width
    sheet.save(a.png); print('wrote', a.png, len(ims), 'objects')
