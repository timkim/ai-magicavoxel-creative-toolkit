"""Small voxel modelling kit: numpy grid G[x, y, z] of palette indices (0 = empty)."""
import json, math, os
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
# small props (trees, flag, cars) used to dress the lots: {name: ((sx, sy, sz), [(x, y, z, colour), ...])}
PROPS = {n: (tuple(d['size']), [tuple(v) for v in d['voxels']])
         for n, d in json.load(open(os.path.join(_HERE, 'props.json'))).items()}
PALETTE = [tuple(c) for c in json.load(open(os.path.join(_HERE, 'palette.json')))]   # PALETTE[i-1] = colour i

def grid(sx, sy, sz):
    return np.zeros((sx, sy, sz), np.uint8)

def box(G, x0, y0, z0, x1, y1, z1, c):
    """Fill [x0,x1) x [y0,y1) x [z0,z1)."""
    G[max(x0, 0):x1, max(y0, 0):y1, max(z0, 0):z1] = c

def shell(G, x0, y0, z0, x1, y1, z1, c, floor=None):
    """Hollow walls (no roof)."""
    box(G, x0, y0, z0, x1, y1, z1, c)
    G[x0 + 1:x1 - 1, y0 + 1:y1 - 1, z0:z1] = 0
    if floor is not None: G[x0 + 1:x1 - 1, y0 + 1:y1 - 1, z0] = floor

def windows(G, x0, y0, x1, y1, zs, c, step=2, frame=None, faces='xy'):
    """Punch windows into the outer walls of the rectangle [x0,x1)x[y0,y1) at heights zs, every `step`."""
    for z in zs:
        if 'x' in faces:
            for x in range(x0 + 1, x1 - 1):
                if (x - x0) % step == 1:
                    for y in (y0, y1 - 1):
                        if G[x, y, z]: G[x, y, z] = c
        if 'y' in faces:
            for y in range(y0 + 1, y1 - 1):
                if (y - y0) % step == 1:
                    for x in (x0, x1 - 1):
                        if G[x, y, z]: G[x, y, z] = c

def gable(G, x0, y0, x1, y1, z0, c, axis='x', gable_c=None, overhang=0):
    """Pitched roof with the ridge along `axis`, starting at height z0. End triangles in gable_c."""
    if axis == 'x':
        w = y1 - y0
        for k in range((w + 1) // 2):
            z = z0 + k
            box(G, x0 - overhang, y0 + k, z, x1 + overhang, y1 - k, z + 1, c)
            if gable_c:
                G[x0, y0 + k + 1:y1 - k - 1, z] = gable_c; G[x1 - 1, y0 + k + 1:y1 - k - 1, z] = gable_c
    else:
        w = x1 - x0
        for k in range((w + 1) // 2):
            z = z0 + k
            box(G, x0 + k, y0 - overhang, z, x1 - k, y1 + overhang, z + 1, c)
            if gable_c:
                G[x0 + k + 1:x1 - k - 1, y0, z] = gable_c; G[x0 + k + 1:x1 - k - 1, y1 - 1, z] = gable_c

def cylinder(G, cx, cy, r, z0, z1, c, hollow=False):
    for x in range(int(cx - r - 1), int(cx + r + 2)):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            d = math.hypot(x + .5 - cx, y + .5 - cy)
            if d <= r and (not hollow or d > r - 1.2):
                if 0 <= x < G.shape[0] and 0 <= y < G.shape[1]: G[x, y, z0:z1] = c

def cone(G, cx, cy, r, z0, h, c):
    for k in range(h):
        rr = r * (1 - k / h)
        if rr < .5: rr = .5
        cylinder(G, cx, cy, rr, z0 + k, z0 + k + 1, c)

def disc(G, cx, cy, r, z, c):
    cylinder(G, cx, cy, r, z, z + 1, c)

def stamp(G, name, x, y, z, rot=0):
    (sx, sy, sz), vox = PROPS[name]
    for vx, vy, vz, c in vox:
        w, h = sx, sy
        for _ in range(rot):                 # 90-degree turns about z
            vx, vy = h - 1 - vy, vx
            w, h = h, w
        X, Y, Z = x + vx, y + vy, z + vz
        if 0 <= X < G.shape[0] and 0 <= Y < G.shape[1] and 0 <= Z < G.shape[2]: G[X, Y, Z] = c

def lot(G, ground, ring):
    """Lot convention: single ground layer at z=0 with a 1-voxel coloured border ring."""
    G[:, :, 0] = ground
    G[0, :, 0] = G[-1, :, 0] = ring; G[:, 0, 0] = G[:, -1, 0] = ring

def trim(G):
    """Crop empty z above the model (models keep their x/y footprint)."""
    zs = np.nonzero(G.any(axis=(0, 1)))[0]
    return G[:, :, :zs.max() + 1]

def to_vox(G):
    xs, ys, zs = np.nonzero(G)
    return [(int(x), int(y), int(z), int(G[x, y, z])) for x, y, z in zip(xs, ys, zs)]
