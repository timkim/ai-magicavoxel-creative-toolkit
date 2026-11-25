"""Add beach props to a MagicaVoxel scene: a surfboard stuck in the sand, a scuttling crab, circling seagulls,
a distant island silhouette, a footprint trail pressed into the sand, and looping whitewash run-up on the shore.
All designs are original and generated in code. New colours go into unused palette slots, so existing colours
never change. Everything animated loops over --frames (default 30) to match the waves and palms.

  python beach_props.py beach.vox beach_props.vox --board=-545,-36 --crab=-520,-20,6 \\
      --gulls=20,0,120 --island=460,-20 --footprints=-645,-16:-212,-30 --whitewash=-202,-168

Coordinates are world x,y (MagicaVoxel scene space, z up); props sit on the highest voxel under them.
Use --at-ground-names to limit which objects count as ground (default: everything static).
"""
import argparse, math, sys
import numpy as np
from voxwrite import load_scene
from voxlib import read_chunks
from scenegraph import world_transforms, node_world

def pts(s, n=None):
    v = [float(t) for t in s.split(',')]
    if n and len(v) != n: raise SystemExit(f'expected {n} numbers in {s!r}')
    return v
def vox_of(G):
    nz = np.nonzero(G); return np.column_stack(nz + (G[nz],)).astype(np.uint8)

class Ctx:
    def __init__(self, path, frames):
        self.sc = load_scene(path); self.frames = frames
        ch = read_chunks(path)[1]
        self.pal = bytearray([c for c in ch if c['id'] == 'RGBA'][0]['content'])
        used = {int(v[3]) for _, vox in self.sc.models for v in vox}
        self.free = [i for i in range(255, 0, -1) if i not in used]
        self.root = self.sc.nodes[self.sc.nodes[0]['child']]
        self.wt = world_transforms(self.sc)
    def colour(self, rgb):
        if not self.free: raise SystemExit('palette full: no unused colour slots left')
        i = self.free.pop(0); self.pal[4 * (i - 1):4 * i] = bytes(rgb) + b'\xff'; return i
    def static_shapes(self, names=None):
        """(trn id, model id, R, t, size, V, W) for every non-animated single-model shape."""
        for i, nd in enumerate(self.sc.nodes):
            if nd['type'] != 'nTRN' or i not in self.wt or len(nd['frames']) > 1: continue
            shp = self.sc.nodes[nd['child']]
            if shp['type'] != 'nSHP' or len(shp['models']) != 1: continue
            if names and nd['attrs'].get('_name', '') not in names: continue
            R, t = node_world(self.sc, self.wt, i); m = shp['models'][0][0]; s, v = self.sc.models[m]
            V = np.asarray(v, np.int64)
            if len(V): yield i, m, R, t, s, V, (V[:, :3] - np.array(s) // 2) @ R.T + t
    def build_ground(self, names=None):
        Ws = [W for *_, V, W in self.static_shapes(names)]
        # flipbooks (e.g. animated wave blocks): voxels that stay put across the loop count as ground too
        for i, nd in enumerate(self.sc.nodes):
            if nd['type'] != 'nTRN' or i not in self.wt or len(nd['frames']) > 1: continue
            shp = self.sc.nodes[nd['child']]
            if shp['type'] != 'nSHP' or len(shp['models']) < 2: continue
            if names and nd['attrs'].get('_name', '') not in names: continue
            ms = [m for m, _ in shp['models']]; (s, v0), (_, v1) = self.sc.models[ms[0]], self.sc.models[ms[len(ms) // 2]]
            a0, a1 = np.asarray(v0, np.int64), np.asarray(v1, np.int64)
            if not len(a0) or not len(a1): continue
            k = lambda a: (a[:, 0] * 4096 + a[:, 1]) * 4096 + a[:, 2]
            V = a0[np.isin(k(a0), k(a1))]
            if not len(V): continue
            R, t = node_world(self.sc, self.wt, i); Ws.append((V[:, :3] - np.array(s) // 2) @ R.T + t)
        A = np.concatenate(Ws); key = A[:, 0] * 1_000_003 + A[:, 1]
        o = np.lexsort((A[:, 2], key)); last = np.r_[key[o][1:] != key[o][:-1], True]
        top = A[o][last]
        self.ground_cols = {(int(x), int(y)): int(z) for x, y, z in top}
    def ground(self, x, y, r=0):
        best = -1
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                best = max(best, self.ground_cols.get((int(round(x)) + dx, int(round(y)) + dy), -1))
        return best
    def add(self, models, frames, name, loop=True):
        """models: list of model ids (flipbook if >1); frames: list of (frame, x, y, z[, rot]) for the transform."""
        if len(models) > 1:
            keys = [(m, {'_f': str(f)}) for f, m in enumerate(models)] + [(models[0], {'_f': str(len(models))})]
            shp = self.sc.shp(keys, attrs={'_loop': '1'} if loop else {})
        else:
            shp = self.sc.shp([(models[0], {})])
        if len(frames) == 1:
            _, x, y, z, *r = frames[0]; fr = [{'_t': f'{x} {y} {z}', **({'_r': r[0]} if r else {})}]
            attrs = {'_name': name}
        else:
            fr = [{'_f': str(f), '_t': f'{x} {y} {z}', **({'_r': r[0]} if r else {})} for f, x, y, z, *r in frames]
            attrs = {'_name': name, '_frm_t': fr[0]['_t']}
        self.root['children'].append(self.sc.trn(shp, frames=fr, attrs=attrs))

# ---------------------------------------------------------------- surfboard
def surfboard(cx, x, y, length=36, width=10, buried=7, tilt=.22):
    B = {'deck': cx.colour((0xf5, 0xf1, 0xe6)), 'rail': cx.colour((0x2f, 0xb3, 0xa8)),
         'stringer': cx.colour((0x9a, 0x6a, 0x42)), 'nose': cx.colour((0xff, 0x7a, 0x5c)), 'fin': cx.colour((0x35, 0x3b, 0x48))}
    G = np.zeros((width + 12, 4, length + 2), np.uint8)
    for z in range(length):
        u = z / (length - 1)
        half = max(.6, (width / 2) * (0.78 + 0.22 * math.sin(math.pi * min(u * 1.25, 1))) * (1 - max(0, (u - .78) / .22) ** 1.8))
        c = 6 + width / 2 + tilt * z
        for gx in range(G.shape[0]):
            d = gx + .5 - c
            if abs(d) <= half:
                col = B['rail'] if abs(d) > half - 1.1 else B['deck']
                if gx == int(c): col = B['stringer']
                if u > .86: col = B['nose']
                G[gx, 1, z] = G[gx, 2, z] = col
        if 4 <= z <= 7: G[int(round(c)), 0, z] = B['fin']
    G = np.transpose(G, (1, 0, 2)).copy()           # deck faces -x
    sx, sy, sz = G.shape; gz = cx.ground(x, y, 2)
    m = cx.sc.add_model(G.shape, vox_of(G))
    cx.add([m], [(0, int(x) - 2 + sx // 2, int(y) - int(6 + width / 2) + sy // 2, gz + 1 - buried + sz // 2)], 'surfboard')

# ---------------------------------------------------------------- crab
def crab(cx, x, y0, y1):
    K = {'shell': cx.colour((0xe0, 0x4b, 0x2b)), 'dark': cx.colour((0x9c, 0x2c, 0x1c)),
         'claw': cx.colour((0xf3, 0x8a, 0x5a)), 'tip': cx.colour((0xf6, 0xd9, 0xb8)), 'eye': cx.colour((0x16, 0x16, 0x18))}
    def pose(ph, moving):
        G = np.zeros((11, 21, 8), np.uint8); px, py = 6, 10
        for gx in range(11):
            for gy in range(21):
                e = ((gx - px) / 3.3) ** 2 + ((gy - py) / 5.0) ** 2
                if e <= 1:
                    for z in (2, 3): G[gx, gy, z] = K['dark'] if (z == 2 or e > .7) else K['shell']
                if ((gx - px) / 2.4) ** 2 + ((gy - py) / 3.8) ** 2 <= 1: G[gx, gy, 4] = K['shell']
        G[px - 1, py - 2, 5] = G[px - 1, py + 2, 5] = K['shell']
        for s in (-1, 1): G[3, py + s, 4] = G[3, py + s, 5] = K['dark']; G[3, py + s, 6] = K['eye']
        for k, bx in enumerate((5, 7, 9)):
            for s in (-1, 1):
                up = moving and ((k + (s > 0) + ph) % 2 == 0); reach = 1 if (moving and (k + ph) % 2) else 0
                for gx, gy, z in [(bx, py + s * 5, 2), (bx, py + s * 6, 3), (bx + (k - 1) * reach, py + s * 7, 3 if up else 2),
                                  (bx + (k - 1) * reach, py + s * 8, 2 if up else 1), (bx + (k - 1) * reach, py + s * 8, 1 if up else 0)]:
                    G[gx, gy, z] = K['dark']
        open_ = 1 if (moving and ph % 2) else 0
        for s in (-1, 1):
            yc = py + s * 3; G[3, yc, 3] = G[2, yc, 3] = K['claw']
            for gx in (0, 1):
                for z in (2, 3, 4): G[gx, yc + s, z] = K['claw']
            G[0, yc + s, 5] = K['tip']; G[0, yc, 4 + open_] = K['tip']
        return G
    F = cx.frames; a, b = int(F * .3), int(F * .5); c = int(F * .8)
    def ypos(f):                                    # dart, pause, dart back, pause
        sm = lambda u: u * u * (3 - 2 * u)
        if f < a: return y0 + (y1 - y0) * sm(f / a)
        if f < b: return y1
        if f < c: return y1 - (y1 - y0) * sm((f - b) / (c - b))
        return y0
    cache, mids = {}, []
    for f in range(F):
        k = (f % 2, f < a or b <= f < c)
        if k not in cache: cache[k] = cx.sc.add_model((11, 21, 8), vox_of(pose(*k)))
        mids.append(cache[k])
    frames = []
    for f in list(range(F)) + [F]:
        yy = ypos(f % F); gz = max(cx.ground(x + dx, yy + dy) for dx in (-3, 0, 3) for dy in (-6, 0, 6))
        frames.append((f, int(x) - 1, int(round(yy)), gz + 5))
    cx.add(mids, frames, 'crab')

# ---------------------------------------------------------------- seagulls
ROT = {0: '4', 1: '17', 2: '52', 3: '33'}          # facing +x, +y, -x, -y
def gulls(cx, x, y, z, count=5, scale=2, seed=5):
    C = {'body': cx.colour((0xf7, 0xf7, 0xf4)), 'wing': cx.colour((0xc9, 0xcf, 0xd6)),
         'tip': cx.colour((0x2b, 0x2d, 0x33)), 'beak': cx.colour((0xf2, 0xb2, 0x2e))}
    def pose(lift):
        G = np.zeros((9, 19, 9), np.uint8); cz = 4
        for gx in range(2, 8): G[gx, 9, cz] = C['body']
        G[8, 9, cz] = C['beak']; G[7, 9, cz + 1] = G[1, 9, cz + 1] = C['body']
        for s in (-1, 1):
            for k in range(1, 10):
                gz = cz + int(round(lift * ((k / 9) ** 1.3)))
                for gx in (4, 5):
                    if not (k >= 7 and gx == 4): G[gx, 9 + s * k, max(0, min(8, gz))] = C['tip'] if k >= 8 else C['wing']
        return np.kron(G, np.ones((scale,) * 3, np.uint8))
    poses = [cx.sc.add_model(p.shape, vox_of(p)) for p in (pose(l) for l in (3, 1, -2, 1))]
    rng = np.random.default_rng(seed); F = cx.frames; flap = max(2, F // 3)
    for g in range(count):
        gx, gy, gz = x + rng.uniform(-80, 80), y + rng.uniform(-110, 110), z + rng.uniform(-25, 30)
        rad, ph = rng.uniform(20, 34), rng.uniform(0, 1)
        mids = [poses[(g + k * 4 // flap) % 4] for k in range(flap)]
        frames = []
        for f in range(0, F + 1, 3):
            ang = 2 * math.pi * (f / F + ph)
            q = int(round(((ang + math.pi / 2) % (2 * math.pi)) / (math.pi / 2))) % 4
            frames.append((f, int(round(gx + rad * math.cos(ang))), int(round(gy + .7 * rad * math.sin(ang))),
                           int(round(gz + 3 * math.sin(2 * ang))), ROT[q]))
        cx.add(mids, frames, f'seagull_{g + 1}')

# ---------------------------------------------------------------- island silhouette
def island(cx, x, y, colours=((0x8a, 0x6b, 0x86), (0x74, 0x58, 0x77), (0x63, 0x4c, 0x6c)), below=14):
    far, near, top = (cx.colour(c) for c in colours)
    SX, SY, SZ = 48, 230, 96; G = np.zeros((SX, SY, SZ), np.uint8)
    hump = lambda v, c, w, h: h * math.exp(-((v - c) / w) ** 2)
    for gy in range(SY):
        hy = (hump(gy, 82, 42, 50) + hump(gy, 150, 30, 30) + hump(gy, 115, 70, 10) + hump(gy, 40, 26, 9)) \
            * (1 + .06 * math.sin(gy * .45) + .04 * math.sin(gy * 1.3))
        for gx in range(SX):
            dx = (gx - SX / 2) / (SX / 2)
            h = hy * max(0, 1 - dx * dx) + (3 if abs(dx) < .9 and 15 < gy < SY - 15 else 0)
            for z in range(min(SZ - 1, below + int(h))):
                G[gx, gy, z] = top if z > below + h - 3 else (near if gx < SX / 2 else far)
    for py, lean in ((70, 1), (92, -1), (156, 1)):  # tiny palm silhouettes
        z0 = np.nonzero(G[SX // 2, py])[0].max() + 1
        for k in range(9): G[SX // 2, py + (k * lean) // 4, z0 + k] = top
        zt, yt = z0 + 9, py + (9 * lean) // 4
        for a in range(-5, 6): G[SX // 2, yt + a, zt + (0 if abs(a) < 3 else -1 if abs(a) < 5 else -2)] = top
        G[SX // 2, yt, zt + 1] = top
    m = cx.sc.add_model(G.shape, vox_of(G))
    cx.add([m], [(0, int(x), int(y), SZ // 2 - below)], 'island')

# ---------------------------------------------------------------- footprints
def footprints(cx, a, b, stride=7.5, names=None):
    (x0, y0), (x1, y1) = a, b
    def path(u):
        return x0 + u * (x1 - x0), y0 + u * (y1 - y0) + 9 * math.sin(u * 7.0) + 4 * math.sin(u * 17.0)
    P = [path(k / 2000) for k in range(2001)]; prints = []; acc = 0; side = 1
    for k in range(2000):
        acc += math.dist(P[k], P[k + 1])
        if acc >= stride:
            acc = 0; (ax, ay), (bx, by) = P[k], P[k + 1]; n = math.hypot(bx - ax, by - ay); dx, dy = (bx - ax) / n, (by - ay) / n
            prints.append((ax - dy * 2.2 * side, ay + dx * 2.2 * side, dx, dy)); side = -side
    press = set()
    for px, py, dx, dy in prints:
        for i in range(-3, 4):
            for j in range(-2, 3):
                if (i / 3.2) ** 2 + (j / 1.7) ** 2 <= 1: press.add((int(round(px + dx * i - dy * j)), int(round(py + dy * i + dx * j))))
    floor = {}
    for tid, m, R, t, s, V, W in list(cx.static_shapes(names)):
        keep = np.ones(len(V), bool); tops = {}
        for idx, (x, y, z) in enumerate(W.tolist()):
            if (x, y) in press and z > tops.get((x, y), (-10**9, 0))[0]: tops[(x, y)] = (z, idx)
        if not tops: continue
        lookup = {tuple(w): i for i, w in enumerate(W.tolist())}
        for (x, y), (z, idx) in tops.items():
            keep[idx] = False
            b1 = lookup.get((x, y, z - 1))
            if b1 is not None:
                keep[b1] = False; b2 = lookup.get((x, y, z - 2))
                if b2 is not None:
                    c = int(V[b2, 3])
                    if c not in floor:
                        rgb = cx.pal[4 * (c - 1):4 * c - 1]; floor[c] = cx.colour(tuple(int(v * .82) for v in rgb))
                    V[b2, 3] = floor[c]
        cx.sc.models[m] = (s, V[keep].astype(np.uint8))
    for xy in press:
        if xy in cx.ground_cols: cx.ground_cols[xy] -= 2
    print(f'footprints: {len(prints)} prints')

# ---------------------------------------------------------------- whitewash
def whitewash(cx, xa, xb, water, foam, waves=3, block=24, seed=3):
    """Foam run-up and backwash over the ground between x=xa (inland) and x=xb (sea side), 'waves' surges per loop."""
    from texture_sand import value_noise, hash3
    ys = [y for (x, y) in cx.ground_cols if xa <= x < xb]
    if not ys: raise SystemExit('whitewash: no ground between those x values')
    Y0, Y1 = min(ys), max(ys) + 1; F = cx.frames; L = xb - xa
    def run(tau):
        if tau < .35: u = tau / .35; return u * u * (3 - 2 * u)
        u = (tau - .35) / .65; return 1 - u * u * (3 - 2 * u)
    noise = lambda y, s, sd: float(value_noise(np.array([float(y)]), np.array([0.0]), s, sd)[0])
    per = {}
    for f in range(F):
        for y in range(Y0, Y1):
            tau = ((f / F - .11 + .06 * (noise(y, 37, seed) - .5)) * waves) % 1.0
            front = xb - 8 - (L - 8) * run(tau) * (.65 + .35 * noise(y, 23, seed + 1))
            for x in range(xa, xb):
                g = cx.ground_cols.get((x, y), -1)
                if x < front or g < 0: continue
                h = hash3(x, y, f, 17)
                c = foam if (x < front + 2.2 or h < .22 + .3 * (1 - tau)) else water if h < .9 else 0
                if c: per.setdefault((y - Y0) // block, {}).setdefault(f, []).append((x - xa, (y - Y0) % block, g + 1, c))
    zmax = max(z for b in per.values() for v in b.values() for _, _, z, _ in v) + 1
    for bj, frames in sorted(per.items()):
        mids = [cx.sc.add_model((L, block, zmax), np.array(frames.get(f, []), np.uint8).reshape(-1, 4)) for f in range(F)]
        cx.add(mids, [(0, xa + L // 2, Y0 + bj * block + block // 2, zmax // 2)], f'whitewash_{bj}')
    print(f'whitewash: {len(per)} blocks')

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--frames', type=int, default=30, help='loop length (match your waves/palms)')
    ap.add_argument('--board', help='X,Y surfboard stuck in the sand')
    ap.add_argument('--crab', help='X,Y0,Y1 crab scuttling sideways between Y0 and Y1')
    ap.add_argument('--gulls', help='X,Y,Z centre of the circling seagull flock')
    ap.add_argument('--gull-count', type=int, default=5)
    ap.add_argument('--island', help='X,Y distant island silhouette (put it just past the far edge of the ocean)')
    ap.add_argument('--footprints', help='X0,Y0:X1,Y1 trail start and end')
    ap.add_argument('--whitewash', help='XA,XB shore strip for the foam run-up (inland x, sea-side x)')
    ap.add_argument('--water-index', type=int, default=1, help='palette index of your water (whitewash)')
    ap.add_argument('--foam-index', type=int, default=3, help='palette index of your foam (whitewash)')
    ap.add_argument('--ground-names', help='comma list of object names that count as ground (default: all static)')
    a = ap.parse_args(argv)
    cx = Ctx(a.src, a.frames); names = set(a.ground_names.split(',')) if a.ground_names else None
    cx.build_ground(names)
    if a.footprints:
        s, e = a.footprints.split(':'); footprints(cx, pts(s, 2), pts(e, 2), names=names)
    if a.board: surfboard(cx, *pts(a.board, 2))
    if a.crab: crab(cx, *pts(a.crab, 3))
    if a.gulls: gulls(cx, *pts(a.gulls, 3), count=a.gull_count)
    if a.island: island(cx, *pts(a.island, 2))
    if a.whitewash: whitewash(cx, *map(int, pts(a.whitewash, 2)), a.water_index, a.foam_index)
    cx.sc.save(a.out, a.src, replace={'RGBA': bytes(cx.pal)})
    print('saved', a.out, '|', len(cx.free), 'palette slots still free')

if __name__ == '__main__':
    main()
