"""Make objects in a MagicaVoxel scene fall from the sky and assemble themselves.

Each object is cut into pieces (small cubes, or whole-width floor slices). Every piece becomes
its own animated object that starts high above its spot and drops into place with a gravity
ease-in, so the finished scene looks exactly like the original. Writes a NEW .vox file.

Examples
  # every top-level object, 3-voxel cubes, landing bottom-up across the whole scene
  python fall.py scene.vox scene_fall.vox

  # only two objects
  python fall.py scene.vox scene_fall.vox --objects 48_fire 16_road

  # a city: buildings stack up floor by floor, in a wave spreading out from one object
  python fall.py city.vox city_fall.vox --pieces floors --order wave --centre 48_city_hall

Notes
  * Objects that are already animated are left untouched. Flipbooks (shapes with several
    models, e.g. blinking lights) keep their flipbook and fall as one piece.
  * Cubes make many pieces: a big scene can reach tens of thousands. Use --pieces floors
    or a bigger --size for large scenes.
  * MagicaVoxel's timeline defaults to 0-30 frames: extend it to the "last landing" frame.
"""
import argparse, math, random
import numpy as np
from collections import Counter
from voxwrite import load_scene
from scenegraph import world_transforms, node_world, shape_targets, model_users, parse_t, IDENTITY_R

GRAVITY_KEYS = (0.0, 0.35, 0.55, 0.72, 0.87, 1.0)     # time samples; height = 1 - t^2

def split_model(sc, mid, mode, size, cache, reuse_slot):
    """Cut model `mid` into pieces once. Returns [(model_id, offset(3,), level)], where offset
    places the piece's pivot relative to the original model's pivot and level orders bottom-up."""
    key = (mid, mode, size)
    if key in cache: return cache[key]
    (Sx, Sy, Sz), vox = sc.models[mid]
    groups = {}
    for x, y, z, c in vox:
        k = (x // size, y // size, z // size) if mode == 'cubes' else (0, 0, z // size)
        groups.setdefault(k, []).append((x, y, z, c))
    out = []; first = reuse_slot
    for (gx, gy, gz), vs in sorted(groups.items(), key=lambda kv: (kv[0][2], kv[0][1], kv[0][0])):
        if mode == 'cubes':
            x0 = min(v[0] for v in vs); y0 = min(v[1] for v in vs); z0 = min(v[2] for v in vs)
            sx = max(v[0] for v in vs) - x0 + 1; sy = max(v[1] for v in vs) - y0 + 1; sz = max(v[2] for v in vs) - z0 + 1
        else:   # floors keep the full footprint so x/y never shift
            x0, y0, z0 = 0, 0, gz * size; sx, sy = Sx, Sy; sz = min(size, Sz - z0)
        local = [(x - x0, y - y0, z - z0, c) for x, y, z, c in vs]
        if first: sc.models[mid] = ((sx, sy, sz), local); m = mid; first = False
        else: m = sc.add_model((sx, sy, sz), local)
        off = np.array([x0 + sx // 2 - Sx // 2, y0 + sy // 2 - Sy // 2, z0 + sz // 2 - Sz // 2])
        out.append((m, off, gz))
    cache[key] = out
    return out

def drop_keys(off, up, land, a, rng):
    """Keyframes for one piece: start `h` voxels above its spot (along world up), land on `land`."""
    h = a.drop + rng.uniform(0, a.drop_jitter)
    fall = max(4, round(a.fall * (h / a.drop) ** 0.5))          # longer drops take longer
    start = max(1, land - fall)
    pos = lambda k: ' '.join(str(int(v)) for v in off + np.rint(up * k).astype(int))
    frames = [{'_f': '0', '_t': pos(h)}]; last = 0
    for t in GRAVITY_KEYS:
        f = start + round(t * (land - start))
        if f <= last: continue
        frames.append({'_f': str(f), '_t': pos(h * (1 - t * t))}); last = f
    return frames, pos(0)

def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('src'); p.add_argument('out')
    p.add_argument('--objects', nargs='+', help='object names to animate (default: everything)')
    p.add_argument('--pieces', choices=['cubes', 'floors'], default='cubes')
    p.add_argument('--size', type=int, help='cube edge or floor height in voxels (default 3 / 8)')
    p.add_argument('--order', choices=['height', 'wave'], default='height',
                   help='height: bottom-up across the scene. wave: outward from --centre, each object bottom-up')
    p.add_argument('--centre', help='wave centre: an object name or "x,y" (default: middle of the animated objects)')
    p.add_argument('--start', type=int, default=20, help='frame of the first landings')
    p.add_argument('--duration', type=int, default=None, help='frames from first to last landing wave (default 45 / 110)')
    p.add_argument('--stack', type=int, default=3, help='wave order: frames between consecutive levels of one object')
    p.add_argument('--drop', type=float, default=160, help='minimum drop height (voxels)')
    p.add_argument('--drop-jitter', type=float, default=160, help='extra random drop height (voxels)')
    p.add_argument('--fall', type=int, default=14, help='frames to fall --drop voxels')
    p.add_argument('--jitter', type=int, default=14, help='random landing offset per piece (frames)')
    p.add_argument('--seed', type=int, default=11)
    a = p.parse_args()
    size = a.size or (3 if a.pieces == 'cubes' else 8)
    duration = a.duration if a.duration is not None else (45 if a.order == 'height' else 110)
    rng = random.Random(a.seed)

    sc = load_scene(a.src)
    targets, whole, skipped = shape_targets(sc, a.objects)
    if not targets and not whole: raise SystemExit('nothing to animate')
    wt = world_transforms(sc)
    users = model_users(sc, targets)
    world = {t: node_world(sc, wt, t) for t in targets + whole}

    # plan pieces first (so the scene-wide height range / wave extent is known)
    cache, plan = {}, []
    for t in targets:
        R, tw = world[t]
        mid = sc.nodes[sc.nodes[t]['child']]['models'][0][0]
        pieces = split_model(sc, mid, a.pieces, size, cache, users[mid] == 'targets-only')
        up = R.T @ np.array([0, 0, 1])                 # world up, in this node's local axes
        for m, off, level in pieces:
            wz = float(tw[2] + (R @ off)[2])
            plan.append((t, m, off, level, up, wz))
    for t in whole:                                    # flipbooks: the node itself drops, in its parent's axes
        Rp, tp = wt[t]
        plan.append((t, None, parse_t(sc.nodes[t]['frames'][0].get('_t', '')), 0, Rp.T @ np.array([0, 0, 1]),
                     float(world[t][1][2])))
    zs = [p_[5] for p_ in plan]; zlo, zhi = min(zs), max(zs)

    if a.order == 'wave':
        if a.centre and ',' in a.centre:
            centre = np.array([float(v) for v in a.centre.split(',')])
        elif a.centre:
            hits = [nd['id'] for nd in sc.nodes if nd['type'] == 'nTRN' and nd['attrs'].get('_name') == a.centre]
            if not hits: raise SystemExit(f'no object named {a.centre!r} for --centre')
            centre = node_world(sc, wt, hits[0])[1][:2].astype(float)
        else:
            centre = np.mean([world[t][1][:2] for t in targets + whole], axis=0)
        dist = {t: float(np.hypot(*(world[t][1][:2] - centre))) for t in targets + whole}
        far = max(dist.values()) or 1.0

    kids = {t: [] for t in targets}; last = 0
    for t, m, off, level, up, wz in plan:
        if a.order == 'height':
            land = a.start + int((wz - zlo) / max(1.0, zhi - zlo) * duration)
        else:
            land = a.start + int(dist[t] / far * duration) + level * a.stack
        land += rng.randint(0, a.jitter)
        frames, rest = drop_keys(off, up, land, a, rng)
        last = max(last, land)
        node = sc.nodes[t]
        if m is None:                                  # flipbook node: animate its own transform
            r = node['frames'][0].get('_r')
            if r and r != IDENTITY_R:
                for f in frames: f['_r'] = r
            node['frames'] = frames; node['attrs']['_frm_t'] = rest
            continue
        kids[t].append(sc.trn(sc.shp([(m, {})]), layer=node['layer'], frames=frames, attrs={'_frm_t': rest}))
    for t in targets:
        sc.nodes[t]['child'] = sc.grp(kids[t])

    sc.save(a.out, a.src)
    print(f'{a.out}: {len(targets)} objects -> {len(plan) - len(whole)} falling pieces ({a.pieces}, size {size}); '
          f'{len(whole)} flipbooks fall whole; last landing frame {last}')
    for name, n in Counter(nm for nm, _ in skipped).items():
        print(f'  left as is (already animated): {name}' + (f' x{n}' if n > 1 else ''))

if __name__ == '__main__':
    main()
