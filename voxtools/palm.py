"""Generate a voxel palm tree: a curved, ringed trunk, arching fronds with drooping leaflets, and a
cluster of coconuts. Writes a standalone .vox, or plants the tree on the ground of a copy of a scene.

  python palm.py palm.vox                                   # standalone
  python palm.py beach_palm.vox --into beach.vox --at=-300,80   # plant at world x,y on the ground there
  (write --at=X,Y with '=' when X is negative)
  python palm.py palm.vox --height 60 --lean 14 --fronds 10 --seed 4
  python palm.py palm.vox --sway 1.5 --frames 30                # gentle looping sway in the wind
"""
import argparse, math, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voxwrite import Scene, load_scene
from voxlib import read_chunks
from scenegraph import world_transforms, node_world

COLOURS = {
    'bark': (0x8b, 0x6b, 0x4a), 'bark_ring': (0x6f, 0x53, 0x38), 'bark_light': (0xa3, 0x82, 0x5c),
    'leaf_dark': (0x2f, 0x7a, 0x34), 'leaf': (0x3f, 0x9a, 0x3c), 'leaf_light': (0x6c, 0xbb, 0x4a),
    'leaf_tip': (0xb5, 0xc4, 0x5a), 'rachis': (0x8f, 0xa8, 0x4a), 'coconut': (0x6b, 0x4a, 0x2a),
    'coconut_green': (0x7a, 0x8a, 0x34),
}

def build(a, C, phase=0.0, crop=True):
    rng = np.random.default_rng(a.seed)
    wind = np.array([math.cos(math.radians(a.wind_dir)), math.sin(math.radians(a.wind_dir)), 0.0])
    sway = math.sin(2 * math.pi * phase)
    k = a.scale
    H = a.height * k; TR = a.trunk * k; FL = a.frond_length * k
    S = (int(H * 1.6), int(H * 1.6), int(H * 1.25))
    G = np.zeros(S, np.uint8); cx0, cy0 = S[0] // 2, S[1] // 2
    def put(p, c, over=True):
        x, y, z = (int(round(v)) for v in p)
        if 0 <= x < S[0] and 0 <= y < S[1] and 0 <= z < S[2] and (over or not G[x, y, z]): G[x, y, z] = c
    th = max(1, int(round(k)))                       # leaflet / rachis thickness grows with the scale
    def blob(p, c, over=True):
        for dx in range(th):
            for dy in range(th):
                for dz in range(th): put((p[0] + dx - th // 2, p[1] + dy - th // 2, p[2] + dz - th // 2), c, over)
    def ball(p, r, c, over=True):
        R = int(math.ceil(r))
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                for dz in range(-R, R + 1):
                    if dx * dx + dy * dy + dz * dz <= r * r: put((p[0] + dx, p[1] + dy, p[2] + dz), c, over)
    # trunk: leans toward +x (the sea) and curves back up near the top
    lean = math.radians(a.lean); dirxy = np.array([math.cos(math.radians(a.lean_dir)), math.sin(math.radians(a.lean_dir))])
    n = int(H * 3); top = None
    for i in range(n + 1):
        t = i / n
        off = math.sin(lean) * H * (t * 1.2 - .45 * t * t)          # lean out, then curve upright
        sw = a.sway * k * sway * t * t                               # trunk bends with the wind
        p = (cx0 + dirxy[0] * off + wind[0] * sw, cy0 + dirxy[1] * off + wind[1] * sw, t * H * .92)
        r = TR * (1 - .35 * t) + (.6 * k if t < .06 else 0)          # flared base, tapering trunk
        ring = int(p[2]) % int(3 * k) < max(1, int(k))
        col = C['bark_ring'] if ring else C['bark']
        R = int(math.ceil(r))
        for dx in range(-R, R + 1):
            for dy in range(-R, R + 1):
                if dx * dx + dy * dy <= r * r:
                    shade = C['bark_light'] if (dx + dy) < -r * .4 and not ring else col
                    put((p[0] + dx, p[1] + dy, p[2]), shade)
        top = p
    top = np.array(top)
    # crown and coconuts
    ball(top + (0, 0, k), TR * .9, C['leaf_dark'])
    for n in range(a.coconuts):
        ang = 2 * math.pi * n / a.coconuts + rng.uniform(-.3, .3)
        ball(top + (math.cos(ang) * TR * .9, math.sin(ang) * TR * .9, (-1.5 - rng.uniform(0, 1.5)) * k), 1.4 * k,
             C['coconut'] if n % 3 else C['coconut_green'])
    # fronds: arch up and out, then droop; leaflets hang off both sides
    for n in range(a.fronds):
        ang = 2 * math.pi * n / a.fronds + rng.uniform(-.25, .25)
        L = FL * rng.uniform(.8, 1.1)
        rise = rng.uniform(.3, .6)                                   # how high it arches before drooping
        fph = rng.uniform(0, 2 * math.pi)                            # this frond's own sway timing
        d = np.array([math.cos(ang), math.sin(ang), 0.0])
        side = np.array([-math.sin(ang), math.cos(ang), 0.0])
        m = int(L * 3)
        for i in range(m + 1):
            t = i / m
            p = top + (0, 0, 1.5 * k) + d * L * t + np.array([0, 0, L * (rise * t - (rise + .55) * t * t)])
            if a.sway:
                fs = math.sin(2 * math.pi * phase + fph)
                p = p + wind * (a.sway * 1.6 * k * (.6 * sway + .4 * fs) * t ** 1.5) + np.array([0, 0, a.sway * .9 * k * fs * t * t])
            blob(p, C['rachis'])
            if t < .08: continue
            leaf_len = L * .24 * math.sin(math.pi * min(1.0, t * 1.05)) + .5   # leaflets longest mid-frond
            if i % max(3, int(5 * k)) == 0:
                for sgn in (-1, 1):
                    for jj in range(1, int(leaf_len / k * 1.5) + 1):
                        j = jj * k / 1.5; u = j / max(leaf_len, 1)
                        q = p + side * sgn * j * .75 + d * j * .45 + np.array([0, 0, -(.25 + u * .75) * j])
                        col = C['leaf_tip'] if (u > .85 and t > .7) else (C['leaf_light'] if sgn > 0 else (C['leaf'] if u < .6 else C['leaf_dark']))
                        blob(q, col, over=False)
    if not crop: return G, np.array([cx0, cy0])
    xs, ys, zs = np.nonzero(G)
    lo = np.array([xs.min(), ys.min(), 0]); hi = np.array([xs.max(), ys.max(), zs.max()])
    G = G[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, :hi[2] + 1]
    base_xy = np.array([cx0, cy0]) - lo[:2]                            # trunk base position inside the model
    return G, base_xy

def build_frames(a, C):
    """All animation frames, cropped to their common bounds; optionally mirrored across y."""
    n = max(1, a.frames)
    grids = []
    for f in range(n):
        G, base = build(a, C, f / n if a.sway else 0.0, crop=False)
        grids.append(G)
    occ = np.any(np.stack([g > 0 for g in grids]), axis=0)
    xs, ys, zs = np.nonzero(occ)
    lo = np.array([xs.min(), ys.min(), 0]); hi = np.array([xs.max(), ys.max(), zs.max()])
    grids = [g[lo[0]:hi[0] + 1, lo[1]:hi[1] + 1, :hi[2] + 1] for g in grids]
    base = base - lo[:2]
    if a.flip_y:
        grids = [g[:, ::-1, :] for g in grids]; base = np.array([base[0], grids[0].shape[1] - 1 - base[1]])
    return grids, base

def ground_height(sc, x, y):
    """Highest occupied world z at column (x, y) across the scene's static models (frame 0)."""
    wt = world_transforms(sc); best = None
    for i, nd in enumerate(sc.nodes):
        if nd['type'] != 'nTRN' or i not in wt or sc.nodes[nd['child']]['type'] != 'nSHP': continue
        R, t = node_world(sc, wt, i); m = sc.nodes[nd['child']]['models'][0][0]; size, vox = sc.models[m]
        if not len(vox): continue
        V = np.asarray(vox, np.int64); W = (V[:, :3] - np.array(size) // 2) @ R.T + t
        hit = W[(W[:, 0] == x) & (W[:, 1] == y)]
        if len(hit): best = max(best if best is not None else -10 ** 9, int(hit[:, 2].max()))
    return best

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('--into'); ap.add_argument('--at', help='world x,y to plant at (with --into)')
    ap.add_argument('--height', type=float, default=52); ap.add_argument('--trunk', type=float, default=2.2, help='trunk radius at the base')
    ap.add_argument('--lean', type=float, default=16, help='lean in degrees'); ap.add_argument('--lean-dir', type=float, default=0, help='lean direction in degrees (0 = +x)')
    ap.add_argument('--fronds', type=int, default=8); ap.add_argument('--frond-length', type=float, default=26)
    ap.add_argument('--coconuts', type=int, default=4); ap.add_argument('--seed', type=int, default=5)
    ap.add_argument('--scale', type=float, default=1.0, help='scale the whole tree (2 = twice the size, with thicker leaves)')
    ap.add_argument('--flip-y', action='store_true', help='mirror the tree across the y axis')
    ap.add_argument('--sway', type=float, default=0, help='sway in the wind: about how many voxels the crown moves (0 = still)')
    ap.add_argument('--wind-dir', type=float, default=180, help='direction the wind blows toward, degrees (180 = -x)')
    ap.add_argument('--frames', type=int, default=30, help='frames in the sway loop (with --sway)')
    ap.add_argument('--step', type=int, default=1, help='animation frames per sway frame')
    ap.add_argument('--replace', action='store_true', help='with --into: remove an existing object with the same --name first')
    ap.add_argument('--name', default='palm_tree')
    a = ap.parse_args()
    if not a.sway: a.frames = 1
    roles = list(COLOURS)
    if a.into:
        sc = load_scene(a.into); ch = read_chunks(a.into)[1]
        used = {v[3] for _, vox in sc.models for v in vox}
        pal = bytearray([c for c in ch if c['id'] == 'RGBA'][0]['content'])
        free = [i for i in range(1, 256) if i not in used]
        C = {}
        for r in roles:
            i = free.pop(0); C[r] = i; pal[4 * (i - 1):4 * i] = bytes(COLOURS[r]) + b'\xff'
    else:
        sc = Scene(); sc.trn(layer=-1); g = sc.grp(); sc.nodes[0]['child'] = g
        C = {r: k + 1 for k, r in enumerate(roles)}
    grids, base = build_frames(a, C)
    mids = [sc.add_model(g.shape, np.column_stack(np.nonzero(g) + (g[np.nonzero(g)],)).astype(np.uint8)) for g in grids]
    if len(mids) > 1:
        shp_args = ([(m_, {'_f': str(f * a.step)}) for f, m_ in enumerate(mids)] + [(mids[0], {'_f': str(len(mids) * a.step)})], {'_loop': '1'})
    else:
        shp_args = ([(mids[0], {})], {})
    G = grids[0]; vox = G[G > 0]
    sx, sy, sz = G.shape
    if a.into:
        x, y = (int(v) for v in a.at.split(','))
        if a.replace:
            r_ = sc.nodes[sc.nodes[0]['child']]
            r_['children'] = [c for c in r_['children'] if sc.nodes[c]['attrs'].get('_name') != a.name]
        gz = ground_height(sc, x, y)
        if gz is None: sys.exit(f'nothing to stand on at {x},{y}')
        # place so the trunk base sits on the ground at (x, y)
        t = (x - int(base[0]) + sx // 2, y - int(base[1]) + sy // 2, gz + 1 + sz // 2)
        root = sc.nodes[sc.nodes[0]['child']]
        root['children'].append(sc.trn(sc.shp(shp_args[0], attrs=shp_args[1]), frames=[{'_t': f'{t[0]} {t[1]} {t[2]}'}], attrs={'_name': a.name}))
        sc.save(a.out, a.into, replace={'RGBA': bytes(pal)})
        print(f'{a.out}: planted {a.name} ({sx}x{sy}x{sz}, {len(vox)} voxels, {len(mids)} frame(s)) at {x},{y} on ground z={gz}; colours at {sorted(C.values())}')
    else:
        sc.nodes[sc.nodes[0]['child']]['children'].append(sc.trn(sc.shp(shp_args[0], attrs=shp_args[1]), frames=[{'_t': f'0 0 {sz // 2}'}], attrs={'_name': a.name}))
        sc.save(a.out, palette=[COLOURS[r] for r in roles])
        print(f'{a.out}: {sx}x{sy}x{sz}, {len(vox)} voxels')

if __name__ == '__main__':
    main()
