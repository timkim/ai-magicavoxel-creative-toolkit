"""Give flat sand texture: patchy colour variation, fine grain, wind ripples raised on the surface,
and a sprinkling of pebbles and shell bits. Works on every voxel of the chosen colour index anywhere in
the scene (including inside animated flipbooks). The texture is computed in world space, so it lines up
across separate objects and stays identical from frame to frame. Writes a NEW file.

  python texture_sand.py beach.vox beach_textured.vox                # sand = colour index 4
  python texture_sand.py beach.vox out.vox --sand 12 --ripple 6 --no-pebbles
"""
import argparse, os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voxwrite import load_scene
from voxlib import read_chunks
from scenegraph import world_transforms, node_world

SHADES = {  # role: rgb (relative to a light beach sand)
    'light': (0xef, 0xdf, 0xb4), 'mid': (0xdc, 0xc7, 0x95), 'dark': (0xcf, 0xb9, 0x84),
    'grain_dark': (0xb9, 0xa2, 0x72), 'grain_light': (0xf6, 0xea, 0xd0),
    'crest': (0xf1, 0xe2, 0xb8), 'trough': (0xd0, 0xba, 0x88), 'pebble': (0x9a, 0x94, 0x8a), 'shell': (0xf2, 0xe4, 0xd8),
}

def hash3(x, y, z, seed):
    h = (x * 73856093) ^ (y * 19349663) ^ (z * 83492791) ^ (seed * 2654435761)
    h = (h ^ (h >> 13)) * 1274126177
    return ((h ^ (h >> 16)) & 0xFFFFFF) / float(0xFFFFFF)

def value_noise(x, y, scale, seed):
    """Smooth 2D noise in [0, 1] at world positions (arrays)."""
    fx, fy = x / scale, y / scale
    x0, y0 = np.floor(fx).astype(np.int64), np.floor(fy).astype(np.int64)
    tx, ty = fx - x0, fy - y0
    tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
    def h(a, b): return hash3(a, b, np.zeros_like(a), seed)
    return (h(x0, y0) * (1 - tx) * (1 - ty) + h(x0 + 1, y0) * tx * (1 - ty) +
            h(x0, y0 + 1) * (1 - tx) * ty + h(x0 + 1, y0 + 1) * tx * ty)

def texture_voxels(V, size, R, t, base, C, a):
    """Texture one model's voxels (int array N x 4) whose colour == base, placed in the world by R, t.
    C maps roles (see SHADES) to palette indices. Returns (new voxels, number of added voxels, sand count)."""
    ang = np.radians(a.ripple_angle); ca, sa = np.cos(ang), np.sin(ang)
    half = np.array(size) // 2
    W = (V[:, :3] - half) @ R.T + t           # world positions
    wx, wy, wz = W[:, 0], W[:, 1], W[:, 2]
    out = V.copy()
    sand = V[:, 3] == base
    # colour patches + grain
    p = value_noise(wx.astype(float), wy.astype(float), a.patch, a.seed)
    p2 = value_noise(wx.astype(float) + 500, wy.astype(float) - 300, a.patch * .4, a.seed + 1)
    mix = .65 * p + .35 * p2
    col = np.where(mix < .38, C['dark'], np.where(mix < .5, C['mid'], np.where(mix < .62, base, C['light'])))
    g = hash3(wx, wy, wz, a.seed + 2)
    col = np.where(g < .05, C['grain_dark'], np.where(g > .965, C['grain_light'], col))
    out[sand, 3] = col[sand]
    # surface: the top sand voxel of each column in this model
    occ = {}
    for idx in np.nonzero(sand)[0]:
        xy = (V[idx, 0], V[idx, 1])
        if V[idx, 2] > occ.get(xy, (-1, -1))[0]: occ[xy] = (V[idx, 2], idx)
    allpos = set(map(tuple, V[:, :3]))
    extra = []
    if a.ripple > 0 or a.pebbles:
        for (lx, ly), (lz, idx) in occ.items():
            if (lx, ly, lz + 1) in allpos: continue          # covered by water / something else
            X, Y = float(wx[idx]), float(wy[idx])
            if a.ripple > 0:
                u = X * ca - Y * sa
                wob = value_noise(np.array([X]), np.array([Y]), 23, a.seed + 3)[0] - .5
                wob2 = value_noise(np.array([X]), np.array([Y]), 9, a.seed + 5)[0] - .5
                r = np.sin(2 * np.pi * (u / a.ripple) + wob * 9 + wob2 * 2.5)
                # ripples only show in wind-blown patches, and fade in and out at their edges
                mask = value_noise(np.array([X]), np.array([Y]), 31, a.seed + 6)[0]
                if mask > .45:
                    if r > .8 - .4 * (mask - .45) and lz + 1 < size[2] and hash3(int(X), int(Y), 7, a.seed) > .12:
                        extra.append((lx, ly, lz + 1, C['crest']))
                    elif r < -.75:
                        out[idx, 3] = C['trough']
            if a.pebbles and lz + 1 < size[2]:
                h = hash3(int(X), int(Y), 991, a.seed + 4)
                if h < .0035: extra.append((lx, ly, lz + 1, C['pebble']))
                elif h < .0055: extra.append((lx, ly, lz + 1, C['shell']))
    if extra:
        out = np.vstack([out, np.array(extra, np.int64)])
    return out, len(extra), int(sand.sum())

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--sand', type=int, default=4, help='palette index of the sand to texture')
    ap.add_argument('--patch', type=float, default=14, help='size of the colour patches (voxels)')
    ap.add_argument('--ripple', type=float, default=7, help='spacing of the wind ripples (voxels, 0 = none)')
    ap.add_argument('--ripple-angle', type=float, default=12, help='direction of the ripple crests in degrees (0 = along y)')
    ap.add_argument('--no-pebbles', dest='pebbles', action='store_false')
    ap.add_argument('--seed', type=int, default=7)
    a = ap.parse_args()

    sc = load_scene(a.src)
    ch = read_chunks(a.src)[1]
    used = {v[3] for _, vox in sc.models for v in vox}
    pal = bytearray([c for c in ch if c['id'] == 'RGBA'][0]['content'])
    free = [i for i in range(1, 256) if i not in used]
    if len(free) < len(SHADES): sys.exit('not enough free palette slots for the sand shades')
    C = {}
    for role, rgb in SHADES.items():
        i = free.pop(0); C[role] = i; pal[4 * (i - 1):4 * i] = bytes(rgb) + b'\xff'
    base = a.sand

    # which nodes show which models, and where
    wt = world_transforms(sc)
    users = {}
    for i, nd in enumerate(sc.nodes):
        if nd['type'] == 'nTRN' and sc.nodes[nd['child']]['type'] == 'nSHP':
            for k, (m, _) in enumerate(sc.nodes[nd['child']]['models']):
                users.setdefault(m, []).append((i, nd['child'], k))
    done, touched, added = {}, 0, 0
    for m, refs in users.items():
        size, vox = sc.models[m]
        if not vox: continue
        V = np.asarray(vox, np.int64)
        if not (V[:, 3] == base).any(): continue
        for n, (trn, shp, k) in enumerate(refs):
            R, t = node_world(sc, wt, trn)
            key = (m, tuple(R.flatten()), tuple(t))
            if key in done:                          # same model at the same place: reuse the textured copy
                sc.nodes[shp]['models'][k] = (done[key], sc.nodes[shp]['models'][k][1]); continue
            out, n_extra, n_sand = texture_voxels(V, size, R, t, base, C, a)
            added += n_extra; sand = V[:, 3] == base
            new_vox = out.astype(np.uint8)
            if n == 0:
                sc.models[m] = (size, new_vox); done[key] = m
            else:
                nm = sc.add_model(size, new_vox); done[key] = nm
                sc.nodes[shp]['models'][k] = (nm, sc.nodes[shp]['models'][k][1])
            touched += int(sand.sum())
    sc.save(a.out, a.src, replace={'RGBA': bytes(pal)})
    print(f'{a.out}: textured {touched / 1e6:.2f} M sand voxels, added {added} ripple/pebble voxels; '
          f'new shades at palette {sorted(C.values())}')

if __name__ == '__main__':
    main()
