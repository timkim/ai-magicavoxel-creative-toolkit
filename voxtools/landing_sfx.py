"""16-bit-era (SNES-style) gravel landing sounds, synced to every piece landing in a .vox animation
made with fall.py (or any animation whose pieces end on their last keyframe).

Pieces that land higher up sound lighter: higher pitch, less thump, quieter. The sound is synthesised
(no samples): filtered noise bursts, crushed to 32 kHz with a short SNES-style echo.

  python landing_sfx.py scene_fall.vox sfx_out --fps 30
  python landing_sfx.py scene_fall.vox sfx_out --fps 24 30

Writes <name>_landings_<fps>fps.wav (one track for the whole animation, starting at frame 0),
eight single gravel_crunch_N.wav one-shots, and <name>_landings_per_frame.json.
"""
import argparse, os, sys, json
import numpy as np
from scipy.signal import butter, sosfilt, resample_poly
from scipy.io import wavfile
from collections import Counter
from voxlib import read_chunks, parse_node

SR_SNES = 32000      # SNES DSP output rate
SR_OUT = 44100
rng = np.random.default_rng(16)

def bp(x, lo, hi, sr):
    return sosfilt(butter(2, [lo, hi], btype='band', fs=sr, output='sos'), x)

def lp(x, f, sr, order=2):
    return sosfilt(butter(order, f, fs=sr, output='sos'), x)

def make_crunch(seed, dur=0.22):
    """One gravel crunch, rendered at 32 kHz then crushed like a BRR sample."""
    r = np.random.default_rng(seed); sr = SR_SNES; n = int(dur * sr); t = np.arange(n) / sr
    # low thump: fast pitch-dropping sine
    f0 = r.uniform(85, 140); f = f0 * (1 + 1.8 * np.exp(-t / 0.012))
    thump = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.exp(-t / r.uniform(0.035, 0.06))
    # grit: many tiny stone clicks, dense at impact then thinning out
    grit = np.zeros(n)
    for _ in range(r.integers(18, 34)):
        at = int(abs(r.exponential(0.035)) * sr)
        if at >= n - 200: continue
        L = int(r.uniform(0.0015, 0.006) * sr)
        burst = r.standard_normal(L) * np.exp(-np.arange(L) / (L / 3))
        grit[at:at + L] += burst * r.uniform(0.3, 1.0) * np.exp(-at / sr / 0.08)
    grit = bp(grit, r.uniform(1400, 2200), r.uniform(4500, 6500), sr)
    # a bit of sandy hiss under it
    hiss = bp(r.standard_normal(n), 2500, 7000, sr) * np.exp(-t / 0.05) * 0.15
    grit = 1.4 * grit / (np.abs(grit).max() + 1e-9) + hiss
    def crush(x):   # BRR-ish: sample-and-hold to 16 kHz, quantize, SNES gaussian-style softening
        hold = np.repeat(x[::2], 2)[:n]; q = 2 ** 7
        return lp(np.round(hold * q) / q, 7000, sr, order=3)
    m = max(np.abs(0.9 * thump + grit).max(), 1e-9)
    return crush(0.9 * thump / m), crush(grit / m)

def snes_echo(x, sr, delay=0.064, fb=0.32, mix=0.28):
    """The SNES echo unit: a delay line with feedback through a low-pass FIR."""
    d = int(delay * sr); y = x.copy(); buf = np.zeros_like(x)
    for start in range(d, len(x), d):
        seg = slice(start, min(len(x), start + d)); src = slice(start - d, start - d + (seg.stop - seg.start))
        buf[seg] = lp(x[src] + fb * buf[src], 3500, sr, order=1)
    return y + mix * buf

def rot_row2(r):
    r = int(r); i0 = r & 3; i1 = (r >> 2) & 3; i2 = 3 - i0 - i1
    v = [0, 0, 0]; v[i2] = -1 if (r >> 6) & 1 else 1; return v

def landings(path):
    """[(landing frame, world z)] for every animated block, walking the scene graph."""
    _, ch = read_chunks(path)
    nodes = {n['id']: n for n in (parse_node(c) for c in ch if c['id'] in ('nTRN', 'nGRP', 'nSHP'))}
    out = []
    def walk(i, z0, up):
        n = nodes[i]
        if n['type'] == 'nTRN':
            f0 = n['frames'][0]
            if len(n['frames']) > 1:   # an animated block: landing = last key, height = landed pose
                tz = sum(a * b for a, b in zip(up, map(int, n['attrs']['_frm_t'].split())))
                out.append((int(n['frames'][-1]['_f']), z0 + tz)); return
            t = list(map(int, f0.get('_t', '0 0 0').split()))
            z = z0 + sum(a * b for a, b in zip(up, t))
            r2 = rot_row2(f0['_r']) if '_r' in f0 else [0, 0, 1]
            # compose: world z of a local vector v = up . (R v) = (R^T up) . v
            R = [[0] * 3 for _ in range(3)]
            rr = int(f0.get('_r', 4)); i0 = rr & 3; i1 = (rr >> 2) & 3; i2 = 3 - i0 - i1
            for row, (idx, bit) in enumerate(((i0, 4), (i1, 5), (i2, 6))): R[row][idx] = -1 if (rr >> bit) & 1 else 1
            nup = [sum(up[k] * R[k][j] for k in range(3)) for j in range(3)]
            walk(n['child'], z, nup)
        elif n['type'] == 'nGRP':
            for c in n['children']: walk(c, z0, up)
    walk(0, 0, [0, 0, 1])
    return out

def render(lands, fps, variants, tail=1.2):
    by_frame = {}
    for f, z in lands: by_frame.setdefault(f, []).append(z)
    zs = np.array([z for _, z in lands]); zlo, zhi = np.percentile(zs, 1), np.percentile(zs, 99.5)
    last = max(by_frame); total = int((last / fps + tail) * SR_SNES)
    L = np.zeros(total); R = np.zeros(total)
    for frame, heights in sorted(by_frame.items()):
        c = len(heights)
        # audible voices per frame grows slowly with the crowd; loudness ~ log of blocks landing
        voices = int(min(c, 3 + 3 * np.log2(1 + c)))
        gain = 0.25 + 0.75 * np.log1p(c) / np.log1p(1600)
        for _ in range(voices):
            th, gr = variants[rng.integers(len(variants))]
            h = float(np.clip((heights[rng.integers(c)] - zlo) / (zhi - zlo), 0, 1))   # 0 = ground, 1 = top
            # lighter up high: less thump, quieter, thinner, higher pitched
            v = (1 - 0.85 * h) * th + (1 - 0.35 * h) * gr
            if h > 0.3: v = v - (h - 0.3) * lp(v, 900, SR_SNES)          # strip low body
            rate = rng.uniform(0.88, 1.12) * (0.85 + 1.05 * h)           # ground ~0.85x, top ~1.9x pitch
            idx = np.arange(0, len(v) - 1, rate)
            s = np.interp(idx, np.arange(len(v)), v)
            at = int((frame + rng.uniform(0, 1)) / fps * SR_SNES)   # spread inside the frame
            end = min(total, at + len(s)); s = s[:end - at]
            pan = rng.uniform(-0.7, 0.7); amp = gain * rng.uniform(0.5, 1.0) * (1 - 0.4 * h) / np.sqrt(voices)
            L[at:end] += s * amp * (1 - pan) / 2 * 2 ** 0.5
            R[at:end] += s * amp * (1 + pan) / 2 * 2 ** 0.5
    out = np.stack([snes_echo(L, SR_SNES), snes_echo(R, SR_SNES)], 1)
    out = np.tanh(1.6 * out / (np.abs(out).max() + 1e-9)) / np.tanh(1.6)   # gentle limiter
    out = resample_poly(out, SR_OUT // 100, SR_SNES // 100, axis=0)
    return (np.clip(out * 0.89, -1, 1) * 32767).astype(np.int16)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('vox'); ap.add_argument('outdir')
    ap.add_argument('--fps', type=int, nargs='+', default=[30], help='frame rate(s) of your render')
    a = ap.parse_args(); vox, outdir, fpss = a.vox, a.outdir, a.fps
    os.makedirs(outdir, exist_ok=True)
    variants = [make_crunch(s) for s in range(8)]
    for i, (th, gr) in enumerate(variants):
        one = resample_poly(snes_echo(th + gr, SR_SNES, mix=0.2), SR_OUT // 100, SR_SNES // 100)
        wavfile.write(f'{outdir}/gravel_crunch_{i + 1}.wav', SR_OUT, (one / np.abs(one).max() * 0.89 * 32767).astype(np.int16))
    lands = landings(vox); counts = Counter(f for f, _ in lands); base = os.path.splitext(os.path.basename(vox))[0]
    zs = [z for _, z in lands]; print('blocks', len(lands), 'landing height range', min(zs), max(zs))
    for fps in fpss:
        wav = render(lands, fps, variants)
        wavfile.write(f'{outdir}/{base}_landings_{fps}fps.wav', SR_OUT, wav)
        print(f'{base}_landings_{fps}fps.wav', f'{len(wav) / SR_OUT:.2f}s', 'first hit', f'{min(counts) / fps:.2f}s', 'last hit', f'{max(counts) / fps:.2f}s')
    json.dump(dict(sorted(counts.items())), open(f'{outdir}/{base}_landings_per_frame.json', 'w'))
