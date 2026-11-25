"""Generate a looping, curling ocean wave as a MagicaVoxel flipbook.

The wave is a sheet of water whose cross-section (the profile, in x/z) is extruded along y. Over the
loop the whole wave goes through a real plunging break: the swell rises and steepens, the crest curls
over, the lip shoots out and falls onto the water in front (enclosing the barrel), the impact explodes
into foam and spray, and the whitewash rolls out while the next swell builds. The last frame leads
seamlessly back into the first. Small timing differences along the wave (--variation) keep it from
looking like a perfect extrusion. --peel instead makes the break travel along the wave.

  python wave.py wave.vox                                  # 24-frame loop, 256 long, 150 high
  python wave.py wave.vox --frames 32 --length 768 --height 170
  python wave.py wave.vox --peel                            # the break travels along the wave instead
  python wave.py wave.vox --water 85d5ec --foam ffffff --shade 5fb3d6
  python wave.py scene_plus_wave.vox --into scene.vox       # add to a copy of an existing scene

Notes
  * MagicaVoxel models are limited to 256 voxels per side, so --length beyond 256 is split into
    256-long segments that line up (one object each, grouped as "wave").
  * Each frame is shown for --step animation frames (default 2), so a 24-frame wave loops every 48.
  * Big waves are heavy: a 256 x 256 x 200 frame is ~0.3-0.7 M voxels. Use --thickness and --frames
    to keep file size in check.
"""
import argparse, math, os, struct, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from voxwrite import Scene, load_scene
from voxlib import read_chunks

# breaking cycle: (stage 0..1, curl angle at the crest, height factor, lip-jet progress, lip foam, impact)
# 0-.30 swell rises and steepens | .30-.50 crest curls over | .50-.67 the lip shoots out as a jet and
# falls onto the water in front, enclosing the barrel | .67-.84 impact: the curl collapses into an
# explosion of foam and spray | .84-1 whitewash rolls out and the next swell builds (1 == 0: seamless)
STAGES = [(0.00, 40, 0.42, 0.00, 0.00, 0.00), (0.18, 62, 0.70, 0.00, 0.00, 0.00), (0.30, 100, 0.95, 0.00, 0.05, 0.00),
          (0.42, 160, 1.00, 0.00, 0.15, 0.00), (0.50, 190, 1.00, 0.15, 0.30, 0.00), (0.59, 190, 1.00, 0.60, 0.45, 0.00),
          (0.67, 190, 0.97, 1.00, 0.60, 0.30), (0.75, 175, 0.62, 1.00, 0.90, 1.00), (0.84, 120, 0.42, 0.40, 0.80, 0.70),
          (0.93, 60, 0.40, 0.00, 0.30, 0.25), (1.00, 40, 0.42, 0.00, 0.00, 0.00)]

def stage_params(s):
    s = s % 1.0
    for (a, *pa), (b, *pb) in zip(STAGES, STAGES[1:]):
        if a <= s <= b:
            t = (s - a) / (b - a); t = t * t * (3 - 2 * t)              # smoothstep between keys
            return [p + (q - p) * t for p, q in zip(pa, pb)]
    return list(STAGES[-1][1:])

def centerline(end_deg, height, start_deg=22, n=400):
    """Points along the curl, from the base (u=0) to the lip (u=1), scaled to the given height."""
    u = np.linspace(0, 1, n)
    th = np.radians(start_deg + (end_deg - start_deg) * u ** 2.2)
    dx, dz = np.cos(th), np.sin(th)
    x = np.concatenate([[0], np.cumsum(dx[1:] + dx[:-1]) / 2]) / n
    z = np.concatenate([[0], np.cumsum(dz[1:] + dz[:-1]) / 2]) / n
    k = height / max(z.max(), 1e-6)
    return u, x * k, z * k

def profile(s, a, rng, hscale=1.0, finger=0.0):
    """2D cross-section for breaking stage s: int8 array P[x, z] with 0 empty, 1 water, 2 shade, 3 foam."""
    X, Z = a.width, a.zsize
    end_deg, hfac, jet, foam, splash = stage_params(s)
    if end_deg > 120:                                   # fingers curl over further, gaps less
        end_deg += a.fingers * 35 * finger * min(1.0, (end_deg - 120) / 60)
    u, cx, cz = centerline(end_deg, a.height * hfac * hscale)
    # the lip leaves the crest as a jet: forward (-x) and falling under gravity onto the water in front
    reach = a.height * hscale * .5
    if jet > 0:
        tx, tz = cx[-1], cz[-1]
        jet = min(1.0, jet * (1 + a.fingers * .35 * finger))
        tau = np.linspace(0, jet, 200)[1:]
        if splash > .5: tau = tau[: max(1, int(len(tau) * (1 - (splash - .5) * 2)))]   # jet breaks up
        u = np.concatenate([u * .75, .75 + .25 * tau / max(jet, 1e-6)])
        r_f = reach * (1 + a.fingers * .45 * finger)           # fingers shoot further out
        cx = np.concatenate([cx, tx - r_f * tau]); cz = np.concatenate([cz, tz * (1 - tau ** 2)])
    cx = (cx - cx.min()) * a.xscale + a.margin
    if splash > .5:                                    # collapsing: the crest sinks into the foam
        cz = cz * (1 - .3 * (splash - .5) * 2)
    P = np.zeros((X, Z), np.int8)
    gx, gz = np.mgrid[0:X, 0:Z]
    th_base, th_lip = a.thickness, max(2.0, a.thickness * .45)
    step = max(1, len(u) // 400)
    for i in range(0, len(u), step):
        r = th_base + (th_lip - th_base) * min(1.0, u[i] / .75)
        x0, z0 = cx[i], cz[i]
        lo_x, hi_x = int(max(0, x0 - r - 1)), int(min(X, x0 + r + 2))
        lo_z, hi_z = int(max(0, z0 - r - 1)), int(min(Z, z0 + r + 2))
        if lo_x >= hi_x or lo_z >= hi_z: continue
        sub = (gx[lo_x:hi_x, lo_z:hi_z] + .5 - x0) ** 2 + (gz[lo_x:hi_x, lo_z:hi_z] + .5 - z0) ** 2 <= r * r
        region = P[lo_x:hi_x, lo_z:hi_z]
        foam_from = (1 - .004 * (1 + 2 * foam)) if jet > 0 else (1 - .03 * (.5 + 2 * foam))
        col = 3 if (u[i] > foam_from and foam > .1) else (2 if u[i] < .35 and a.shade else 1)
        region[sub & (region == 0)] = col
        region[sub & (col == 3)] = 3
    # flat water in front of and behind the wave so it sits on the sea
    P[:, 0:2][P[:, 0:2] == 0] = 1
    info = dict(tipx=float(cx[-1]), tipz=float(cz[-1]), foam=foam, splash=splash, jet=jet,
                land_x=float(cx[-1] if jet > .9 else cx.min() + reach * .2 * a.xscale), xmin=float(cx.min()), xmax=float(cx.max()),
                hs=hscale)
    return P, info

def spray_clumps(info, a, y, rng, out):
    """Append (x, y, z, size) cubes for one row of the wave: spray off the lip, the impact explosion,
    and whitewash on the surface. Spray is grouped in clumps of small cubes (1-4 voxels)."""
    H = a.height * info['hs']; foam, splash, jet = info['foam'], info['splash'], info['jet']
    k = H / 150.0                                            # spray scales with the wave size
    xs_ = a.xscale
    sizes, weights = [1, 2, 3, 4], [.4, .3, .2, .1]
    def clump(x, z, spread, n):
        for _ in range(n):
            out.append((x + rng.normal(0, spread), y + rng.normal(0, spread), z + rng.normal(0, spread * .8),
                        rng.choice(sizes, p=weights)))
    if foam > .1 and splash < .6:                            # broken foam along the lip edge
        for _ in range(rng.poisson(foam * .6)):
            clump(info['tipx'], info['tipz'], max(.6, 1.2 * k), rng.integers(1, 4))
    if foam > .1 and splash < .6 and jet < .9:              # lip spray while it throws
        for _ in range(rng.poisson(foam * .5 * a.spray / 220)):
            ang = rng.uniform(0, 2 * math.pi); d = abs(rng.normal(0, (3 + 6 * foam) * k))
            clump(info['tipx'] + math.cos(ang) * d * xs_, info['tipz'] + abs(math.sin(ang)) * d * .7, max(.6, 1.5 * k), rng.integers(1, 4))
    if splash > 0:                                           # impact: big churning clumps + thrown spray
        for _ in range(rng.poisson(splash * 1.2 * a.spray / 220)):
            clump(info['land_x'] + rng.normal(0, H * .12 * (.5 + splash)) * xs_,
                  abs(rng.normal(H * .12 * splash, H * .18 * splash)), max(.8, (2 + 3 * splash) * k), rng.integers(3, 9))
        for _ in range(rng.poisson(splash * 1.5 * a.spray / 220)):
            ang = rng.uniform(math.radians(20), math.radians(160)); d = abs(rng.normal(0, H * .45 * splash))
            clump(info['land_x'] + math.cos(ang) * d * 1.2 * xs_, math.sin(ang) * d, max(.6, 1.2 * k), rng.integers(1, 4))
    if foam > .25 and splash > .2:                           # whitewash spreading on the surface
        spread = H * (.3 + .9 * (1 - splash))
        for _ in range(rng.poisson(foam * .8)):
            clump(rng.uniform(info['xmin'] - spread * .8 * xs_, info['xmax'] + spread * .3 * xs_), rng.uniform(1, 3), max(.8, 2 * k), rng.integers(2, 6))

def fit_xscale(a):
    """Largest horizontal extent of the breaking motion (all stages, tallest variation) -> scale to fit --width."""
    a.xscale = 1.0
    hmax = 1 + a.height_variation
    ext = 0.0
    for b in range(64):
        end_deg, hfac, jet, foam, splash = stage_params(b / 64)
        u, cx, cz = centerline(end_deg, a.height * hfac * hmax)
        lo, hi = cx.min(), cx.max()
        if jet > 0: lo = min(lo, cx[-1] - a.height * hmax * .5 * (1 + a.fingers * .45) * min(1, jet * (1 + a.fingers * .35)))
        ext = max(ext, hi - lo + a.thickness * 2)
    room = a.width - a.margin - 1
    return min(1.0, room / ext)

def build_frames(a, colours):
    """Return frames[f][segment] = (N, 4) uint8 voxel arrays."""
    rng = np.random.default_rng(a.seed)
    seg = max(1, min(256, a.segment))
    nseg = math.ceil(a.length / seg)
    seg_len = [min(seg, a.length - seg * k) for k in range(nseg)]
    seg_start = [seg * k for k in range(nseg)]
    cache = {}
    BINS, HBINS = 96, 9
    FBINS = 7
    def prof(s, hs, fg=0.0):
        fb = int(round((fg + 1) / 2 * (FBINS - 1))) if a.fingers else (FBINS - 1) // 2
        fval = fb / (FBINS - 1) * 2 - 1
        b = int((s % 1.0) * BINS) % BINS
        hb = int(round((hs - (1 - a.height_variation)) / max(2 * a.height_variation, 1e-6) * (HBINS - 1))) if a.height_variation else 0
        hb = min(max(hb, 0), HBINS - 1)
        key = (b, hb, fb)
        if key not in cache:
            hval = (1 - a.height_variation) + 2 * a.height_variation * hb / (HBINS - 1) if a.height_variation else 1.0
            cache[key] = profile(b / BINS, a, np.random.default_rng(a.seed + b * 31 + hb * 7 + fb), hval, fval)  # (P, info)
        return cache[key]
    # smooth random curves along the wave: timing offset and height, so it breaks unevenly
    nrng = np.random.default_rng(a.seed + 1000)
    waves = [(nrng.uniform(.006, .03), nrng.uniform(0, 2 * math.pi), nrng.uniform(.4, 1)) for _ in range(4)]
    hwaves = [(nrng.uniform(.008, .025), nrng.uniform(0, 2 * math.pi), nrng.uniform(.4, 1)) for _ in range(3)]
    def smooth(gy, comps):
        v = sum(w * math.sin(f * gy + ph) for f, ph, w in comps); return v / sum(w for _, _, w in comps)
    # finger pattern: tongues roughly --finger-width apart, irregular, sharpened so they read as fingers
    fw = a.finger_width
    fcomps = [(2 * math.pi / (fw * m), nrng.uniform(0, 2 * math.pi), w)
              for m, w in ((nrng.uniform(.85, 1.2), 1), (nrng.uniform(1.6, 2.4), .7), (nrng.uniform(.5, .7), .35), (nrng.uniform(3, 5), .6))]
    def finger(gy):
        v = smooth(gy, fcomps); return math.copysign(abs(v) ** .6, v)
    frames = []
    for f in range(a.frames):
        t = f / a.frames
        frng = np.random.default_rng(a.seed * 7919 + f)
        segs = []
        for k in range(nseg):
            Y = seg_len[k]
            G = np.zeros((a.width, Y, a.zsize), np.uint8)
            cubes = []
            for y in range(Y):
                gy = seg_start[k] + y
                if a.peel: s = ((gy / a.peel_length) - t) % 1.0
                else: s = (t + a.variation * smooth(gy, waves)) % 1.0
                P, info = prof(s, 1 + a.height_variation * smooth(gy, hwaves), finger(gy))
                G[:, y, :] = np.array([0] + colours, np.uint8)[P]
                spray_clumps(info, a, y, frng, cubes)
            foam_c = colours[2]
            for x, y, z, n in cubes:
                x, y, z = int(round(x)), int(round(y)), int(round(z))
                x0, y0, z0 = max(0, x), max(0, y), max(0, z)
                x1, y1, z1 = min(a.width, x + n), min(Y, y + n), min(a.zsize, z + n)
                if x0 < x1 and y0 < y1 and z0 < z1: G[x0:x1, y0:y1, z0:z1] = foam_c
            xs, ys, zs = np.nonzero(G)
            arr = np.empty((len(xs), 4), np.uint8)
            arr[:, 0] = xs; arr[:, 1] = ys; arr[:, 2] = zs; arr[:, 3] = G[xs, ys, zs]
            segs.append(arr)
        frames.append(segs)
    return frames, seg_len

def build_set(a, colours):
    """A set of a.set waves travelling toward a beach at low x, staggered evenly over the loop.
    Returns frames[f] = uint8 grid (sea_width, length, zsize) of colour indices."""
    rng_cache = {}
    BINS, HBINS, FBINS = 96, 9, 7
    def prof(s, hs, fg):
        fb = int(round((fg + 1) / 2 * (FBINS - 1))) if a.fingers else (FBINS - 1) // 2
        b = int((s % 1.0) * BINS) % BINS
        hb = min(max(int(round((hs - .2) / 1.2 * (HBINS - 1))), 0), HBINS - 1)
        key = (b, hb, fb)
        if key not in rng_cache:
            rng_cache[key] = profile(b / BINS, a, np.random.default_rng(a.seed + b * 31 + hb * 7 + fb),
                                     .2 + 1.2 * hb / (HBINS - 1), fb / (FBINS - 1) * 2 - 1)
        return rng_cache[key]
    nrng = np.random.default_rng(a.seed + 1000)
    def comps(n, lo, hi): return [(nrng.uniform(lo, hi), nrng.uniform(0, 2 * math.pi), nrng.uniform(.4, 1)) for _ in range(n)]
    def smooth(gy, cs): return sum(w * math.sin(f * gy + ph) for f, ph, w in cs) / sum(w for _, _, w in cs)
    fw = a.finger_width
    fcomps = [(2 * math.pi / (fw * m), nrng.uniform(0, 2 * math.pi), w)
              for m, w in ((nrng.uniform(.85, 1.2), 1), (nrng.uniform(1.6, 2.4), .7), (nrng.uniform(.5, .7), .35), (nrng.uniform(3, 5), .6))]
    def finger(gy):
        v = smooth(gy, fcomps); return math.copysign(abs(v) ** .6, v)
    per_wave = [(comps(4, .006, .03), comps(3, .008, .025)) for _ in range(a.set)]   # each wave its own unevenness
    W0 = a.sea_width; W, Y, Z = a.sea_width + a.ocean, a.length, a.zsize
    WATER, SHADE, FOAM, SAND, WET = colours
    pal = np.array([0, WATER, SHADE, FOAM], np.uint8)
    beach = a.beach
    # static sea floor + beach
    base = np.zeros((W, Y, Z), np.uint8)
    base[beach:, :, 0:2] = WATER
    for x in range(beach):
        h = 2 + int((beach - x) / max(beach, 1) * a.beach_height)
        base[x, :, 0:h] = SAND
        base[x, :, h - 1] = WET if x > beach - 6 else SAND
    # open ocean behind the breaking zone: gentle swells rolling toward the shore, looping with the waves
    ox = np.arange(W0, W)[:, None].astype(float); oy = np.arange(Y)[None, :].astype(float)
    taper = np.clip((ox - W0) / 40.0, 0, 1)                              # flat where it meets the waves
    yvar = .5 + .5 * np.sin(oy * .023 + 1.3) * np.sin(oy * .061)        # swells vary along the coast
    frames = []
    for f in range(a.frames):
        t = f / a.frames
        frng = np.random.default_rng(a.seed * 7919 + f)
        G = base.copy(); cubes = []
        if a.ocean and a.ocean_swell > 0:
            ph = 2 * math.pi * ((ox / a.swell_length) + t * a.swells_per_loop) + .6 * np.sin(oy * .031)
            h = 2 + np.rint(a.ocean_swell * taper * (.55 + .45 * yvar) * (.5 + .5 * np.sin(ph))).astype(int)
            for dz in range(int(h.max())):
                G[W0:W, :, dz][h > dz] = SHADE if dz >= 2 and dz < int(h.max()) - 1 else WATER
        for i in range(a.set):
            tw, hw = per_wave[i]
            for y in range(Y):
                ti = (t + i / a.set + a.variation * smooth(y, tw)) % 1.0
                rise = min(1.0, ti / .15); rise = rise * rise * (3 - 2 * rise)       # swell rises out of the flat sea
                hs = rise * (1 + a.height_variation * smooth(y, hw))
                if hs < .25: continue
                P, info = prof(ti, hs, finger(y + 37 * i))
                x0 = int(beach + a.shore_gap + (1 - ti) * a.travel) - a.margin   # profile x=margin is the wave base
                xs, zs = np.nonzero(P[:, 2:]); zs = zs + 2                      # skip the profile's own floor rows
                X = xs + x0; ok = (X >= 0) & (X < W)
                G[X[ok], y, zs[ok]] = pal[P[xs[ok], zs[ok]]]
                sub = []; spray_clumps(info, a, y, frng, sub)
                cubes += [(cx + x0, cy, cz, n) for cx, cy, cz, n in sub]
        for x, y, z, n in cubes:
            x, y, z = int(round(x)), int(round(y)), int(round(z))
            xa, ya, za = max(0, x), max(0, y), max(0, z)
            xb, yb, zb = min(W, x + n), min(Y, y + n), min(Z, z + n)
            if xa < xb and ya < yb and za < zb: G[xa:xb, ya:yb, za:zb] = FOAM
        frames.append(G)
    return frames

def hexrgb(s):
    s = s.lstrip('#'); return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out')
    ap.add_argument('--into', help='add the wave to a copy of this scene (the scene file is not modified)')
    ap.add_argument('--frames', type=int, default=24, help='frames in the loop')
    ap.add_argument('--step', type=int, default=2, help='animation frames each wave frame is shown')
    ap.add_argument('--length', type=int, default=256, help='length of the wave along y (voxels)')
    ap.add_argument('--segment', type=int, default=256, help='length of each wave block along y (max 256); the wave is split into blocks this long')
    ap.add_argument('--height', type=float, default=150, help='peak height (voxels)')
    ap.add_argument('--thickness', type=float, default=7, help='water sheet thickness at the base (voxels)')
    ap.add_argument('--width', type=int, default=256, help='model size across the wave (x)')
    ap.add_argument('--margin', type=int, default=40, help='space in front of the wave base (x)')
    ap.add_argument('--zsize', type=int, default=0, help='model height (z); default fits the wave')
    ap.add_argument('--peel', action='store_true', help='peel: the break travels along the wave instead of the whole wave crashing at once')
    ap.add_argument('--peel-length', type=float, default=256, help='with --peel: distance along y of one full break cycle')
    ap.add_argument('--variation', type=float, default=.1, help='timing differences along the wave (fraction of the loop), so sections break at different moments')
    ap.add_argument('--height-variation', type=float, default=.12, help='height differences along the wave (fraction of --height)')
    ap.add_argument('--fingers', type=float, default=.8, help='how strongly the lip splits into fingers that reach out and curl down (0 = straight lip)')
    ap.add_argument('--finger-width', type=float, default=6, help='typical spacing of the fingers along the wave (voxels)')
    ap.add_argument('--spray', type=int, default=220, help='amount of spray (clumps of 1-4 voxel cubes)')
    ap.add_argument('--water', default='85d5ec'); ap.add_argument('--foam', default='ffffff')
    ap.add_argument('--shade', default='6cc3e0', help='lower-face shade colour ("" for none)')
    ap.add_argument('--set', type=int, default=1, help='number of waves travelling toward a beach (1 = a single standing wave)')
    ap.add_argument('--sea-width', type=int, default=144, help='with --set: size of the sea across the waves (x)')
    ap.add_argument('--travel', type=float, default=96, help='with --set: distance each wave travels over its cycle')
    ap.add_argument('--beach', type=int, default=24, help='with --set: width of the sand beach at the front (x)')
    ap.add_argument('--beach-height', type=float, default=5, help='with --set: how high the beach rises')
    ap.add_argument('--shore-gap', type=int, default=4, help='with --set: distance from the beach where the travel ends')
    ap.add_argument('--ocean', type=int, default=0, help='with --set: open ocean behind the waves (x), e.g. 256')
    ap.add_argument('--ocean-swell', type=float, default=3, help='height of the rolling swells on the open ocean (0 = flat)')
    ap.add_argument('--swell-length', type=float, default=32, help='distance between ocean swells (x)')
    ap.add_argument('--swells-per-loop', type=int, default=1, help='how many swell lengths the ocean moves per loop')
    ap.add_argument('--sand', default='e6d3a3'); ap.add_argument('--wet-sand', default='c8b384')
    ap.add_argument('--seed', type=int, default=3)
    a = ap.parse_args()
    a.zsize = a.zsize or min(256, int(a.height * (1 + a.height_variation) * 1.08) + 12)

    rgbs = [hexrgb(a.water), hexrgb(a.shade) if a.shade else hexrgb(a.water), hexrgb(a.foam)]
    if a.set > 1: rgbs += [hexrgb(a.sand), hexrgb(a.wet_sand)]
    if a.into:
        src = load_scene(a.into); used = {v[3] for _, vox in src.models for v in vox}
        pal = bytearray([c for c in read_chunks(a.into)[1] if c['id'] == 'RGBA'][0]['content'])
        # reuse an identical existing colour, else take a free slot
        existing = {tuple(pal[4 * i:4 * i + 3]): i + 1 for i in range(255) if (i + 1) in used}
        free = [i for i in range(255, 0, -1) if i not in used]
        idx = []
        for rgb in rgbs:
            if rgb in existing: idx.append(existing[rgb])
            else:
                i = free.pop(0); pal[4 * (i - 1):4 * i] = bytes(rgb) + b'\xff'; existing[rgb] = i; idx.append(i)
        sc = src; replace = {'RGBA': bytes(pal)}
        root = sc.nodes[sc.nodes[0]['child']]
    else:
        idx = list(range(1, len(rgbs) + 1)); sc = Scene(); sc.trn(layer=-1); g = sc.grp(); sc.nodes[0]['child'] = g
        root = sc.nodes[g]; replace = None

    a.xscale = fit_xscale(a)
    if a.xscale < 1: print(f'squeezing the wave horizontally x{a.xscale:.2f} so the whole break fits {a.width} wide')
    wave_kids = []
    if a.set > 1:
        grids = build_set(a, idx)
        BX, BY, BZ = a.width, max(1, min(256, a.segment)), a.zsize            # block size
        nvox = 0; empty = None
        WT = a.sea_width + a.ocean
        for i in range(math.ceil(WT / BX)):
            for j in range(math.ceil(a.length / BY)):
                mids, prev = [], None
                for G in grids:
                    sub = G[i * BX:(i + 1) * BX, j * BY:(j + 1) * BY, :]
                    xs, ys, zs = np.nonzero(sub)
                    arr = np.column_stack([xs, ys, zs, sub[xs, ys, zs]]).astype(np.uint8)
                    nvox += len(arr)
                    b = arr.tobytes()
                    if prev is not None and b == prev: mids.append(mids[-1]); continue
                    if len(arr) == 0:
                        if empty is None: empty = sc.add_model((BX, BY, BZ), np.zeros((0, 4), np.uint8))
                        mids.append(empty)
                    else: mids.append(sc.add_model((BX, BY, BZ), arr))
                    prev = b
                if all(m == empty for m in mids): continue
                if len(set(mids)) == 1: shp = sc.shp([(mids[0], {})])
                else:
                    keys = [(m, {'_f': str(f * a.step)}) for f, m in enumerate(mids)] + [(mids[0], {'_f': str(a.frames * a.step)})]
                    shp = sc.shp(keys, attrs={'_loop': '1'})
                t = (i * BX + BX // 2 - WT // 2, j * BY + BY // 2 - a.length // 2, BZ // 2)
                wave_kids.append(sc.trn(shp, frames=[{'_t': f'{t[0]} {t[1]} {t[2]}'}], attrs={'_name': f'sea_{i}_{j}'}))
        root['children'].append(sc.trn(sc.grp(wave_kids), attrs={'_name': 'waves'}))
        if a.into: sc.save(a.out, a.into, replace=replace)
        else: sc.save(a.out, palette=rgbs)
        print(f'{a.out}: {a.set} waves, {a.frames}-frame loop ({a.frames * a.step} animation frames), '
              f'{len(wave_kids)} blocks of {BX}x{BY}x{BZ}, {len(sc.models)} models, {nvox / 1e6:.1f} M voxels')
        return
    frames, seg_len = build_frames(a, idx)
    for k, Y in enumerate(seg_len):
        size = (a.width, Y, a.zsize)
        mids = [sc.add_model(size, frames[f][k]) for f in range(a.frames)]
        keys = [(m, {'_f': str(f * a.step)}) for f, m in enumerate(mids)] + [(mids[0], {'_f': str(a.frames * a.step)})]
        shp = sc.shp(keys, attrs={'_loop': '1'})
        y0 = sum(seg_len[:k]) - a.length // 2
        wave_kids.append(sc.trn(shp, frames=[{'_t': f'0 {y0 + Y // 2} {a.zsize // 2}'}], attrs={'_name': f'wave_{k}'}))
    root['children'].append(sc.trn(sc.grp(wave_kids), attrs={'_name': 'wave'}))

    if a.into: sc.save(a.out, a.into, replace=replace)
    else: sc.save(a.out, palette=rgbs)
    nvox = sum(len(s) for fr in frames for s in fr)
    print(f'{a.out}: {a.frames}-frame loop ({a.frames * a.step} animation frames), {len(seg_len)} segment(s), '
          f'{nvox / 1e6:.1f} M voxels total, colours at palette {idx}')

if __name__ == '__main__':
    main()
