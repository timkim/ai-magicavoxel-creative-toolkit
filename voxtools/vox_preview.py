"""Quick perspective preview of a .vox scene from a camera position, without opening MagicaVoxel.
Splats every voxel as a square (painter's algorithm, no lighting), so it is rough, but good enough to check
composition: is the new prop in frame, is it too big, does it hide something.

  python vox_preview.py scene.vox preview.png --eye=-675,-15,40 --yaw 0 --pitch 0 --fov 45 --size 540x960
  python vox_preview.py scene.vox preview.png --eye=... --frame 12      # flipbooks and animated transforms at frame 12

--yaw is the look direction in degrees around z (0 = +x, 90 = +y); --pitch tilts up (+) or down (-);
--fov is the vertical field of view in degrees (MagicaVoxel's default camera uses 45).
"""
import argparse, math
import numpy as np
from PIL import Image
from voxwrite import load_scene
from voxlib import read_chunks
from scenegraph import world_transforms, node_world

def rot_matrix(r):
    r = int(r); i0 = r & 3; i1 = (r >> 2) & 3; i2 = 3 - i0 - i1; M = np.zeros((3, 3), int)
    M[0, i0] = -1 if (r >> 4) & 1 else 1; M[1, i1] = -1 if (r >> 5) & 1 else 1; M[2, i2] = -1 if (r >> 6) & 1 else 1
    return M

def gather(path, frame):
    sc = load_scene(path); wt = world_transforms(sc); pts, cols = [], []
    for i, nd in enumerate(sc.nodes):
        if nd['type'] != 'nTRN' or i not in wt: continue
        shp = sc.nodes[nd['child']]
        if shp['type'] != 'nSHP': continue
        ms = shp['models']; m = ms[0][0]
        if len(ms) > 1:                                    # flipbook: last key at or before the frame (looping)
            keys = sorted((int(d.get('_f', 0)), mm) for mm, d in ms); last = keys[-1][0] or 1
            loop = shp['attrs'].get('_loop') == '1'; f = frame % last if loop else min(frame, last)
            m = [mm for k, mm in keys if k <= f][-1]
        R, t = node_world(sc, wt, i)
        fr = nd['frames']
        if len(fr) > 1:                                    # animated transform: nearest key at or before the frame
            keys = sorted(fr, key=lambda d: int(d.get('_f', 0)))
            k = [d for d in keys if int(d.get('_f', 0)) <= frame] or keys[:1]; k = k[-1]
            if '_t' in k: t = np.array([int(v) for v in k['_t'].split()]) + (t - np.array([int(v) for v in (nd['frames'][0].get('_t') or '0 0 0').split()]))
            if '_r' in k: R = rot_matrix(k['_r'])
        s, v = sc.models[m]; V = np.asarray(v, np.int64)
        if not len(V): continue
        pts.append((V[:, :3] - np.array(s) // 2) @ np.asarray(R).T + t); cols.append(V[:, 3])
    pal = np.frombuffer([c for c in read_chunks(path)[1] if c['id'] == 'RGBA'][0]['content'], np.uint8).reshape(256, 4)[:, :3]
    return np.concatenate(pts).astype(float), np.concatenate(cols), pal

def render(W, C, pal, eye, yaw, pitch, fov, size, sky=(250, 190, 150)):
    w, h = size; f = (h / 2) / math.tan(math.radians(fov) / 2)
    cy, sy, cp, sp = math.cos(math.radians(yaw)), math.sin(math.radians(yaw)), math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    fwd = np.array([cy * cp, sy * cp, sp]); right = np.array([sy, -cy, 0.]); up = np.cross(right, fwd)
    d = W - np.asarray(eye, float); z = d @ fwd; keep = z > 1
    d, z, C = d[keep], z[keep], C[keep]
    u = (w / 2 + f * (d @ right) / z).astype(int); v = (h / 2 - f * (d @ up) / z).astype(int)
    ok = (u > -12) & (u < w) & (v > -12) & (v < h); u, v, z, C = u[ok], v[ok], z[ok], C[ok]
    o = np.argsort(-z); img = np.zeros((h, w, 3), np.uint8); img[:] = sky
    r = np.clip((f / z[o] * .9).astype(int), 1, 16)
    for uu, vv, cc, rr in zip(u[o], v[o], C[o], r):
        if uu + rr > 0 and vv + rr > 0: img[max(vv, 0):vv + rr, max(uu, 0):uu + rr] = pal[cc - 1]
    return img

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('vox'); ap.add_argument('png')
    ap.add_argument('--eye', required=True, help='X,Y,Z camera position (world)')
    ap.add_argument('--yaw', type=float, default=0); ap.add_argument('--pitch', type=float, default=0)
    ap.add_argument('--fov', type=float, default=45); ap.add_argument('--size', default='540x960')
    ap.add_argument('--frame', type=int, default=0)
    a = ap.parse_args(argv)
    W, C, pal = gather(a.vox, a.frame)
    img = render(W, C, pal, [float(v) for v in a.eye.split(',')], a.yaw, a.pitch, a.fov, tuple(int(v) for v in a.size.split('x')))
    Image.fromarray(img).save(a.png); print('saved', a.png, f'({len(W)} voxels)')

if __name__ == '__main__':
    main()
