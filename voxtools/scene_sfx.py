"""16-bit (SNES-style) beach sound effects for a looping voxel animation: a calm ocean bed, wave crashes,
foam fizz, crab claw clacks and jumps, distant seagull cries and a palm rustle. Everything is synthesised (no
samples), rendered at 32 kHz with BRR-style crushing and the SNES echo, and mixed circularly: sounds that run past
the end wrap round to the start, so the clip loops without a gap or click.

Times are frame numbers at --fps, or seconds with an 's' suffix (0.62s). Every event list is optional.

  python scene_sfx.py beach_sfx.wav --duration 3 --fps 30 \\
      --crash 0.62s,1.62s,2.62s --clack 27,63 --clack-open 24,30,60 --jump 12,84 --land 18,90 \\
      --gull 0.12s --gull-laugh 1.18s --gull-far 2.38s --rustle 0.9s,2.3s --video render.mp4

With --video, also writes <video>_sfx.mp4: the picture copied untouched, this sound as its audio track.
Find event times by stepping through your render (or the .vox timeline); stretched renders multiply frames.
"""
import argparse, os, subprocess
import numpy as np
from scipy.signal import butter, sosfilt, resample_poly
from scipy.io import wavfile
from landing_sfx import snes_echo

SR = 32000

def filt(x, kind, f, order=2): return sosfilt(butter(order, f, btype=kind, fs=SR, output='sos'), x)
def crush(x, bits=8):
    """BRR-ish: sample-and-hold to 16 kHz, quantise, soften."""
    n = len(x); hold = np.repeat(x[::2], 2)[:n]; q = 2 ** (bits - 1)
    return filt(np.round(hold * q) / q, 'low', 7500, 3)
def pulse(freq, n, duty=.25):
    ph = np.cumsum(np.broadcast_to(freq, (n,))) / SR; return np.where((ph % 1) < duty, 1.0, -1.0)
def norm(x): return x / (np.abs(x).max() + 1e-12)

# ---------------------------------------------------------------- sounds
def ocean_bed(n, crashes, dur, seed=42):
    """Dark filtered noise that swells gently just before each crash."""
    r = np.random.default_rng(seed); t = np.arange(n) / SR
    bed = filt(filt(r.standard_normal(n), 'band', [80, 900]), 'low', 700)
    if crashes:
        period = dur / len(crashes); swell = .7 + .3 * np.sin(2 * np.pi * (t - crashes[0] + .27) / period + np.pi / 2)
    else:
        swell = .85 + .15 * np.sin(2 * np.pi * t / dur)
    return crush(norm(bed) * swell)

def crash(seed):
    """Soft wave break: a low whoosh building up, then a darkening roar. Returns (sound, lead-in seconds)."""
    r = np.random.default_rng(seed); n = int(1.3 * SR); tt = np.arange(n) / SR
    noise = r.standard_normal(n); cut = 350 + 1300 * np.exp(-tt / .35); out = np.zeros(n)
    for s in range(0, n, 400): out[s:s + 400] = filt(noise[s:s + 400], 'low', cut[s])
    roar = out * (np.minimum(1, tt / .18) ** 2 * np.exp(-tt / .6))
    thump = np.sin(2 * np.pi * np.cumsum(70 * (1 + 1.5 * np.exp(-tt / .02))) / SR) * np.exp(-tt / .09)
    pre_n = int(.25 * SR); pre = filt(r.standard_normal(pre_n), 'band', [300, 1200]) * np.linspace(0, 1, pre_n) ** 2 * .35
    return crush(norm(np.concatenate([pre * .4, norm(roar) + .15 * thump]))), pre_n / SR

def fizz(seed):
    """Foam running up the sand: soft high hiss."""
    r = np.random.default_rng(seed); n = int(.7 * SR); tt = np.arange(n) / SR
    return crush(norm(filt(r.standard_normal(n), 'band', [1500, 5000]) * np.exp(-tt / .3) * np.minimum(1, tt / .12)))

def clack(seed):
    """Claws snapping shut: woody square-wave knock with a hard double tick."""
    r = np.random.default_rng(seed); n = int(.07 * SR); tt = np.arange(n) / SR
    knock = pulse(950 * (1 + .8 * np.exp(-tt / .006)), n, .5) * np.exp(-tt / .012)
    tick = filt(r.standard_normal(n), 'band', [1800, 6500]) * np.exp(-tt / .004)
    tick2 = np.roll(tick, int(.011 * SR)) * .6; tick2[:int(.011 * SR)] = 0
    return crush(filt(.55 * knock + tick + tick2, 'low', 6500))

def jump():
    """Classic 16-bit jump: square wave sweeping up (~320 -> 1000 Hz)."""
    n = int(.16 * SR); tt = np.arange(n) / SR; u = tt / tt[-1]
    s = pulse(320 * (3.2 ** (u ** .7)), n, .25) * .8 + pulse(640 * (3.2 ** (u ** .7)), n, .5) * .15
    return crush(filt(s * np.minimum(1, tt / .004) * (1 - u) ** 1.5, 'low', 6000))

def land(seed):
    """Small sandy landing: low blip thud plus a puff of sand hiss."""
    r = np.random.default_rng(seed); n = int(.18 * SR); tt = np.arange(n) / SR
    thud = pulse(150 * (1 + 1.2 * np.exp(-tt / .015)), n, .5) * np.exp(-tt / .035)
    sand = filt(r.standard_normal(n), 'band', [1500, 6000]) * np.exp(-tt / .06) * np.minimum(1, tt / .005)
    return crush(norm(filt(.8 * thud, 'low', 900) + .5 * sand))

def gull(kind, seed, pitch=1.0):
    """Gull cry: nasal, raspy pulse voice. 'long' = drawn-out kee-OW, 'kyow' = short laugh note."""
    r = np.random.default_rng(seed); L = .46 if kind == 'long' else .13
    n = int(L * SR); tt = np.arange(n) / SR; u = tt / L
    f = (np.interp(u, [0, .08, .22, .35, 1], [620, 1180, 1250, 1120, 560]) if kind == 'long'
         else np.interp(u, [0, .2, .45, 1], [700, 1150, 1080, 640]))
    f = f * pitch * (1 + .012 * r.standard_normal(n).cumsum() / np.sqrt(np.arange(1, n + 1)))
    voice = pulse(f, n, .14) * (1 + .45 * pulse(np.full(n, 68.0), n, .5)) + .25 * filt(r.standard_normal(n), 'band', [1500, 4000])
    voice = filt(voice, 'band', [600, 4200]) + 1.2 * filt(voice, 'band', [2000, 3200])
    e = np.minimum(1, tt / .012) * np.minimum(1, (L - tt) / (.12 if kind == 'long' else .05))
    if kind == 'long': e *= np.interp(u, [0, .3, 1], [1, .9, .55])
    return crush(norm(voice * e))

def rustle(seed, length=.9):
    r = np.random.default_rng(seed); n = int(length * SR)
    return crush(filt(r.standard_normal(n), 'band', [3000, 8000]) * np.sin(np.pi * np.linspace(0, 1, n)))

# ---------------------------------------------------------------- mixing
def times(s, fps):
    if not s: return []
    return [float(v[:-1]) if v.endswith('s') else float(v) / fps for v in s.split(',') if v]

def render(a):
    N = int(SR * a.duration)
    def place(track, snd, at, gain=1.0):
        idx = (int(round(at * SR)) + np.arange(len(snd))) % N; np.add.at(track, idx, snd * gain)
    T = lambda s: times(s, a.fps)
    crashes = T(a.crash)
    waves, foam, crab, birds, leaves = (np.zeros(N) for _ in range(5))
    for k, at in enumerate(crashes):
        s, pre = crash(10 + k); place(waves, s, at - pre, 1.0 - .08 * (k % 3))
        place(foam, fizz(20 + k), at + a.fizz_delay, .55)
    for k, at in enumerate(T(a.clack)): place(crab, clack(50 + k), at - .005, 1.7)
    for k, at in enumerate(T(a.clack_open)): place(crab, filt(clack(60 + k), 'high', 2500), at - .005, .7)
    for at in T(a.jump): place(crab, jump(), at, .55)
    for k, at in enumerate(T(a.land)): place(crab, land(70 + k), at - .01, .6)
    for k, at in enumerate(T(a.gull)): place(birds, gull('long', 1 + k), at)
    for k, at in enumerate(T(a.gull_laugh)):
        for j in range(4): place(birds, gull('kyow', 10 + 4 * k + j, 1 - .03 * j), at + j * .14, .9 - .1 * j)
    for k, at in enumerate(T(a.gull_far)): place(birds, gull('long', 30 + k, 1.12), at, .55)
    for k, at in enumerate(T(a.rustle)): place(leaves, rustle(31 + k), at)

    bed = ocean_bed(N, crashes, a.duration)
    ambient = .30 * bed + .28 * waves + .12 * foam + .08 * leaves
    ambient = a.ocean * .63 * ambient / (np.abs(ambient).max() + 1e-12)
    far = filt(filt(birds, 'low', 1800), 'high', 700)          # distance: highs gone, mostly echo
    gulls = norm(far) * .12 * a.gulls if birds.any() else 0 * far
    wet = np.zeros(N); place(wet, snes_echo(gulls, SR, delay=.19, fb=.4, mix=1.0) - gulls, 0)
    mix = ambient + .7 * gulls + .6 * wet + a.crab * 1.7 * crab / max(1.0, np.abs(crab).max())
    mix = filt(mix, 'high', 35); ax = np.abs(mix)
    mix = np.where(ax > .8, np.sign(mix) * (.8 + .18 * np.tanh((ax - .8) / .18)), mix)   # soft-limit transients only
    return resample_poly(mix, 441, 320)[:int(a.duration * 44100)]

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', help='output .wav')
    ap.add_argument('--duration', type=float, required=True, help='clip length in seconds (the loop)')
    ap.add_argument('--fps', type=float, default=30)
    ap.add_argument('--crash', help='wave break moments'); ap.add_argument('--fizz-delay', type=float, default=.28, help='seconds from break to foam hiss')
    ap.add_argument('--clack', help='claws snap shut'); ap.add_argument('--clack-open', help='claws open (light tick)')
    ap.add_argument('--jump', help='take-offs'); ap.add_argument('--land', help='landings')
    ap.add_argument('--gull', help='long gull cries'); ap.add_argument('--gull-laugh', help='start of a 4-note gull laugh')
    ap.add_argument('--gull-far', help='fainter, further gull cries'); ap.add_argument('--rustle', help='palm leaf rustles')
    ap.add_argument('--ocean', type=float, default=1.0, help='ocean level (1 = default calm level)')
    ap.add_argument('--gulls', type=float, default=1.0, help='gull level'); ap.add_argument('--crab', type=float, default=1.0, help='crab level')
    ap.add_argument('--video', help='also mux into this video -> <name>_sfx.mp4 (needs ffmpeg)')
    a = ap.parse_args(argv)
    out = render(a)
    wavfile.write(a.out, 44100, (np.clip(out, -1, 1) * 32767).astype(np.int16)); print('saved', a.out)
    if a.video:
        mp4 = os.path.splitext(a.video)[0] + '_sfx.mp4'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-i', a.out, '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', mp4], check=True)
        print('saved', mp4)

if __name__ == '__main__':
    main()
