"""Turn a handful of camera keyframes into one smooth, per-frame camera path.

Interpolation is a monotone cubic Hermite spline (Fritsch-Carlson) per channel:
  * passes exactly through every keyframe,
  * speed changes smoothly through each keyframe (no stop-and-go "jitter" at segment boundaries),
  * never overshoots a keyframe value,
  * eases in at the first keyframe and out at the last.
Zoom is interpolated in log space, so a big pull-back (e.g. 260 -> 1900) feels steady instead of
accelerating at the far end.

Input (JSON):
  {"frames": 165,
   "keyframes": [{"frame": 0,   "x": 0, "y": 0, "z": 30, "zoom": 260,  "pitch": -18, "yaw": 35, "roll": 0},
                 {"frame": 164, "x": 0, "y": 0, "z": 0,  "zoom": 1600, "pitch": -52, "yaw": 135}]}
  Missing channels on a keyframe repeat the previous keyframe's value.

Output formats (--format):
  console   one MagicaVoxel console line per frame:
              cam rx <pitch> | cam ry <yaw> | cam rz <roll> | cam zoom <zoom> | cam x <x> | cam y <y> | cam z <z>
            (add --with-time to append "| set a_time <frame>" so the scene animation follows along)
  csv       frame,x,y,z,zoom,pitch,yaw,roll
  segments  {"keyframes": [{"frames": 1, "animationDelay": 0, "camera": {"x": {"start": ..}, ...}}, ...]}
            -- one 1-frame segment per frame, for camera-driver scripts that play start/end segments.

  python smooth_camera.py examples/camera_keys.json path.txt --format console --with-time
"""
import argparse, csv, json
import numpy as np

CHANNELS = ['x', 'y', 'z', 'zoom', 'pitch', 'yaw', 'roll']

def monotone_hermite(t, y, tq, end_slopes=(0.0, 0.0)):
    t = np.asarray(t, float); y = np.asarray(y, float)
    if len(t) == 1: return np.full(len(tq), y[0])
    h = np.diff(t); d = np.diff(y) / h
    m = np.zeros_like(y)
    for k in range(1, len(y) - 1):
        if d[k - 1] * d[k] <= 0: m[k] = 0
        else:
            w1 = 2 * h[k] + h[k - 1]; w2 = h[k] + 2 * h[k - 1]
            m[k] = (w1 + w2) / (w1 / d[k - 1] + w2 / d[k])     # weighted harmonic mean
    m[0], m[-1] = end_slopes
    out = []
    for q in tq:
        q = min(max(q, t[0]), t[-1])
        k = min(np.searchsorted(t, q, side='right') - 1, len(h) - 1)
        s = (q - t[k]) / h[k]
        h00 = 2*s**3 - 3*s**2 + 1; h10 = s**3 - 2*s**2 + s; h01 = -2*s**3 + 3*s**2; h11 = s**3 - s**2
        out.append(h00 * y[k] + h10 * h[k] * m[k] + h01 * y[k + 1] + h11 * h[k] * m[k + 1])
    return np.array(out)

def build(spec):
    keys = sorted(spec['keyframes'], key=lambda k: k['frame'])
    frames = int(spec.get('frames', keys[-1]['frame'] + 1))
    filled, prev = [], {c: 0.0 for c in CHANNELS}
    for k in keys:
        prev = {c: float(k.get(c, prev[c])) for c in CHANNELS}; filled.append(prev)
    t = [k['frame'] for k in keys]; tq = np.arange(frames)
    curves = {}
    for c in CHANNELS:
        vals = [f[c] for f in filled]
        if c == 'zoom' and min(vals) > 0: curves[c] = np.exp(monotone_hermite(t, np.log(vals), tq))
        else: curves[c] = monotone_hermite(t, vals, tq)
    return frames, curves

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('keys'); ap.add_argument('out')
    ap.add_argument('--format', choices=['console', 'csv', 'segments'], default='console')
    ap.add_argument('--with-time', action='store_true', help='console: also set the animation frame')
    a = ap.parse_args()
    frames, c = build(json.load(open(a.keys)))
    r = lambda ch, f, n=3: round(float(c[ch][f]), n)
    if a.format == 'console':
        with open(a.out, 'w') as fh:
            for f in range(frames):
                line = (f'cam rx {r("pitch", f)} | cam ry {r("yaw", f)} | cam rz {r("roll", f)} | cam zoom {r("zoom", f)} | '
                        f'cam x {r("x", f)} | cam y {r("y", f)} | cam z {r("z", f)}')
                fh.write(line + (f' | set a_time {f}' if a.with_time else '') + '\n')
    elif a.format == 'csv':
        with open(a.out, 'w', newline='') as fh:
            w = csv.writer(fh); w.writerow(['frame'] + CHANNELS)
            for f in range(frames): w.writerow([f] + [r(ch, f, 4) for ch in CHANNELS])
    else:
        segs = [{'frames': 1, 'animationDelay': 0,
                 'camera': {ch: {'start': r(ch, f, 4)} for ch in CHANNELS}} for f in range(frames)]
        json.dump({'keyframes': segs}, open(a.out, 'w'), indent=1)
    print(f'wrote {a.out}: {frames} frames ({a.format})')

if __name__ == '__main__':
    main()
