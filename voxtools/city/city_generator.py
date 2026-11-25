"""Generate a whole city from a library .vox of tile models.

  python city_generator.py library.vox city.vox --seed 7 --blocks 25
  python city_generator.py library.vox city.vox --static      # no cars / smoke / traffic lights

The city is a grid of 4x4-tile blocks (16 voxels per tile) separated by roads; 25 blocks per side
fills MagicaVoxel's whole 2048-voxel scene. Zoning: a downtown core with a few satellite centres
(tall commercial), mixed rings, residential suburbs (height-capped) and industry at the edges with
power plants. Civic buildings are spread on a coarse lattice; nearby repeats of the same design are
avoided. Cars drive the roads, traffic lights cycle and chimneys smoke (unless --static).

The library is a .vox whose top-level objects are named by footprint and category:
  16_road                         straight road tile (runs along x)
  16_road_int_green/_yellow/_red  intersection tile in each traffic-light state
  16_res_*, 32_res_*, 64_res_*    residential lots (1x1, 2x2, 4x4 tiles)
  16_com_*, 32_com_*, 64_com_*    commercial lots
  16_ind_*, 32_ind_*, 64_ind_*    industrial lots
  16_const_*, 32_const_*          construction sites (sprinkled in at random)
  48_city_hall, 32_mayors_house, 48_fire, 48_police, 48_hospital, 32_library, 32_water_tower,
  64_power_nuclear, 64_power_solar, 16_park, 16_statue
  x_tree_*                        trees for the city edge
  x_*_car                         cars (only needed without --static)
  anim_cloud_0                    smoke flipbook (only needed without --static)
"""
import argparse, math, os, random, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from collections import Counter, defaultdict
from voxwrite import Scene, load_scene
from scenegraph import rot_matrix

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('library'); ap.add_argument('out')
ap.add_argument('--seed', type=int, default=7)
ap.add_argument('--blocks', type=int, default=25, help='blocks per side (25 fills the 2048 scene)')
ap.add_argument('--static', action='store_true', help='no cars, smoke or traffic-light animation')
args = ap.parse_args()
if args.blocks < 3: ap.error('--blocks must be at least 3')

SRC = args.library
T = 16
RE = 5                                   # road every 5 tiles -> 4x4-tile blocks
NB = args.blocks
N = NB * RE + 1                          # 126 tiles -> 2016 voxels
ANIM = 120
STATIC = args.static
ROT = ['4', '17', '52', '33']
out_path = args.out
rng = random.Random(args.seed)

src = load_scene(SRC)
lib, flip = {}, {}
for k in src.nodes[src.nodes[0]['child']]['children']:
    t = src.nodes[k]; s = src.nodes[t['child']]; name = t['attrs'].get('_name')
    if name and name not in lib:
        lib[name] = (s['models'][0][0], src.models[s['models'][0][0]][0], t['layer'])
        if len(s['models']) > 1: flip[name] = (dict(s['attrs']), list(s['models']))
names = lambda p: sorted(n for n in lib if n.startswith(p))
REQUIRED = ['16_road', '16_road_int_green', '16_road_int_yellow', '16_road_int_red', '48_city_hall', '32_mayors_house',
            '48_fire', '48_police', '48_hospital', '32_library', '32_water_tower', '64_power_nuclear', '64_power_solar',
            '16_park', '16_statue'] + ([] if STATIC else ['anim_cloud_0'])
missing = [n for n in REQUIRED if n not in lib]
for p in ['16_res_', '16_com_', '16_ind_', 'x_tree_']:
    if not names(p): missing.append(p + '*')
if missing: sys.exit('library is missing: ' + ', '.join(missing) + '  (see --help for the naming scheme)')

sc = Scene(); remap = {}
def mid(n):
    m = lib[n][0] if isinstance(n, str) else n
    if m not in remap: remap[m] = sc.add_model(*src.models[m])
    return remap[m]
sc.trn(layer=-1); world = sc.grp(); sc.nodes[0]['child'] = world; kids = sc.nodes[world]['children']
HALF = N * T // 2
placed = []
owner = {}                               # tile -> design name (spatial hash for the no-repeat rule)
uses = Counter()

def place(name, tx, ty, rot='4'):
    m, (sx, sy, sz), lay = lib[name]
    cx = tx * T + sx // 2 - HALF; cy = ty * T + sy // 2 - HALF
    f0 = {'_t': f'{cx} {cy} {sz // 2}'}
    if rot != '4': f0['_r'] = rot
    placed.append((name, cx, cy, rot))
    kids.append(sc.trn(sc.shp([(mid(name), {})]), layer=lay, frames=[f0], attrs={'_name': name}))
    st = max(1, sx // T)
    for a in range(st):
        for b in range(st): owner[(tx + a, ty + b)] = name
    uses[name] += 1

# ---------------- roads + traffic lights ----------------
is_road = lambda i: i % RE == 0
lights = [mid('16_road_int_green'), mid('16_road_int_yellow'), mid('16_road_int_red')]
for x in range(N):
    for y in range(N):
        if is_road(x) and is_road(y):
            ph = 0 if (x // RE + y // RE) % 2 == 0 else 30
            seq = sorted({(f + ph) % 60: m for m, f in [(lights[0], 0), (lights[1], 24), (lights[2], 30), (lights[0], 60)]}.items())
            models = [(m, {'_f': str(f)}) for f, m in seq]
            s = sc.shp([(lights[0], {})]) if STATIC else sc.shp(models, attrs={'_loop': '1', '_frm_id': str(models[0][0])})
            kids.append(sc.trn(s, layer=0, frames=[{'_t': f'{x * T + 8 - HALF} {y * T + 8 - HALF} 8'}], attrs={'_name': 'intersection'}))
        elif is_road(y): place('16_road', x, y)
        elif is_road(x): place('16_road', x, y, '17')

# ---------------- zoning ----------------
def far_points(k, min_d, pool, existing=()):
    pts = list(existing)
    if not pool: return []
    for _ in range(2000):
        if len(pts) >= k + len(existing): break
        p = rng.choice(pool)
        if all(math.dist(p, q) >= min_d for q in pts): pts.append(p)
    return pts[len(existing):]

blocks = [(bx, by) for bx in range(NB) for by in range(NB)]
mainc = (NB // 2, NB // 2)
cores = [mainc] + far_points(4, 7, [b for b in blocks if 3 <= b[0] < NB - 3 and 3 <= b[1] < NB - 3], [mainc])
edge = [b for b in blocks if min(b[0], b[1], NB - 1 - b[0], NB - 1 - b[1]) <= 2]
indc = far_points(3, 10, [b for b in edge if all(math.dist(b, c) > 6 for c in cores)])

def zone(b):
    dc = min(math.dist(b, c) - (1.2 if c == mainc else 0) for c in cores)
    di = min((math.dist(b, c) for c in indc), default=math.inf)
    if di <= 1.6: return 'industrial'
    if dc <= 1.5: return 'commercial'
    if dc <= 3.0: return 'mixed'
    return 'residential'

# civic buildings: city hall downtown, plants in each industrial zone (alternating types),
# and a rotating set of district services spread on a coarse lattice
special = {mainc: '48_city_hall'}
for i, c in enumerate(indc): special[c] = ['64_power_nuclear', '64_power_solar', '64_power_nuclear'][i]
services = ['48_fire', '48_police', '48_hospital', '32_library', '32_water_tower', '48_fire', '48_police', '32_library']
k = 0
for gx in range(2, NB, 6):
    for gy in range(2, NB, 6):
        b = (min(NB - 1, gx + rng.randint(-1, 1)), min(NB - 1, gy + rng.randint(-1, 1)))
        if b in special or any(math.dist(b, c) < 1.5 for c in cores): continue
        special[b] = services[k % len(services)]; k += 1
_m = far_points(1, 6, [b for b in blocks if zone(b) == 'residential'], list(special)) or \
     far_points(1, 2, [b for b in blocks if zone(b) != 'industrial' and b not in special], list(special))
if _m: special[_m[0]] = '32_mayors_house'

pools = {
    'residential': {1: names('16_res_'), 2: names('32_res_'), 4: names('64_res_')},
    'commercial': {1: names('16_com_'), 2: names('32_com_'), 4: names('64_com_')},
    'industrial': {1: names('16_ind_'), 2: names('32_ind_'), 4: names('64_ind_')},
}
const = {1: names('16_const_'), 2: names('32_const_')}
AVOID = {1: 3, 2: 5, 4: 10}

def nearby(tx, ty, size, R):
    out = set()
    for x in range(tx - R + 1, tx + size + R - 1):
        for y in range(ty - R + 1, ty + size + R - 1):
            n = owner.get((x, y))
            if n: out.add(n)
    return out

def choose(pool, tx, ty, size):
    near = nearby(tx, ty, size, AVOID[size])
    cands = [n for n in pool if n not in near] or pool
    return rng.choices(cands, weights=[1 / (1 + uses[n]) ** 2 for n in cands])[0]

_hcache = {}
def real_h(n):
    if n not in _hcache: _hcache[n] = max(p[2] for p in src.models[lib[n][0]][1]) + 1
    return _hcache[n]
CAP = {'residential': 45, 'mixed': 55, 'commercial': 999, 'industrial': 999}   # max building height by zone
def pick(z, size, tx, ty):
    cap = CAP[z]
    if z == 'mixed': z = rng.choice(['residential', 'commercial'])
    if rng.random() < 0.05 and size <= 2: return choose(const[size], tx, ty, size)
    pool = [n for n in pools[z][size] if real_h(n) <= cap]
    if size > 1:   # big lot: only if a design fits the height cap and has not been used nearby
        near = nearby(tx, ty, size, AVOID[size])
        pool = [n for n in pool if n not in near]
        if not pool: return None
    return choose(pool or pools[z][size], tx, ty, size)

def fill_block(x0, y0, z, sp=None):
    used = [[False] * 4 for _ in range(4)]
    def put(name, i, j, s):
        place(name, x0 + i, y0 + j, rng.choice(ROT))
        for a in range(s):
            for b in range(s): used[i + a][j + b] = True
    if sp:
        s = lib[sp][1][0] // T
        if s == 4: place(sp, x0, y0); return
        put(sp, 0, 0, s)
    big = {'commercial': 0.55, 'industrial': 0.3, 'residential': 0.0, 'mixed': 0.12}[z]
    if not sp and rng.random() < big:
        n4 = pick(z, 4, x0, y0)
        if n4: put(n4, 0, 0, 4); return
    p2 = {'industrial': 0.9, 'commercial': 0.6}.get(z, 0.5)
    for i in (0, 2):
        for j in (0, 2):
            if not any(used[i + a][j + b] for a in (0, 1) for b in (0, 1)) and rng.random() < p2:
                n2 = pick(z, 2, x0 + i, y0 + j)
                if n2: put(n2, i, j, 2)
    for i in range(4):
        for j in range(4):
            if used[i][j]: continue
            r = rng.random(); spot = nearby(x0 + i, y0 + j, 1, 4)
            if z == 'residential' and r < 0.07 and '16_park' not in spot: put('16_park', i, j, 1)
            elif r < 0.02 and '16_statue' not in nearby(x0 + i, y0 + j, 1, 8): put('16_statue', i, j, 1)
            else: put(pick(z, 1, x0 + i, y0 + j), i, j, 1)

for b in blocks:
    fill_block(b[0] * RE + 1, b[1] * RE + 1, zone(b), special.get(b))

# ---------------- trees around the edge ----------------
trees = names('x_tree_')
for i in range(0, N * T, 7):
    for side in range(4):
        if rng.random() < 0.6:
            n = rng.choice(trees); sz = lib[n][1][2]; off = -6 - rng.randrange(10)
            x, y = [(i, off), (i, N * T - off), (off, i), (N * T - off, i)][side]
            kids.append(sc.trn(sc.shp([(mid(n), {})]), layer=0, frames=[{'_t': f'{x - HALF} {y - HALF} {sz // 2}'}], attrs={'_name': n}))

# ---------------- cars: each drives ~240 voxels per loop; the jump back lands on the loop restart ----------------
cars = [n for n in names('x_') if n.endswith('_car')]
L = N * T; SPEED = 2.0
ncars = 0
for k in range(0 if STATIC else NB + 1):
    lane = k * RE
    for axis in ('x', 'y'):
        for direction in (+1, -1):
            for _ in range(5):
                n = rng.choice(cars)
                base = lane * T + 8 + (4 if (direction > 0) == (axis == 'y') else -4) - HALF
                p0 = rng.uniform(0, L - SPEED * ANIM)
                def pos(f):
                    a = p0 + SPEED * f
                    a = (a if direction > 0 else L - a) - HALF
                    return f'{a:.0f} {base} 1' if axis == 'x' else f'{base} {a:.0f} 1'
                r = {('x', 1): '17', ('x', -1): '33', ('y', 1): '4', ('y', -1): '52'}[(axis, direction)]
                frames = []
                for f in (0, ANIM):
                    fr = {'_f': str(f), '_t': pos(f)}
                    if r != '4': fr['_r'] = r
                    frames.append(fr)
                kids.append(sc.trn(sc.shp([(mid(n), {})]), layer=0, frames=frames, attrs={'_name': n, '_frm_t': frames[0]['_t']}))
                ncars += 1

# ---------------- smoke on chimneys / cooling towers ----------------
def chimneys(name):
    (S, v) = src.models[lib[name][0]]
    top = defaultdict(int)
    for x, y, z, c in v: top[(x, y)] = max(top[(x, y)], z)
    zmax = max(top.values()); hi = {p for p, z in top.items() if z >= zmax - 3}
    seen = set(); out = []
    for p in hi:
        if p in seen: continue
        st = [p]; comp = []
        while st:
            q = st.pop()
            if q in seen or q not in hi: continue
            seen.add(q); comp.append(q); st += [(q[0] + a, q[1] + b) for a in (-1, 0, 1) for b in (-1, 0, 1)]
        if len(comp) <= 12 or name == '64_power_nuclear':
            out.append((sum(a for a, _ in comp) / len(comp), sum(b for _, b in comp) / len(comp), max(top[q] for q in comp)))
    return S, out[:4]
chim = {}
pmodels = [mid(m) for m, _ in flip['anim_cloud_0'][1]] if not STATIC else []
puffs = 0
for name, cx, cy, rot in ([] if STATIC else placed):
    if not ('_ind_' in name or name == '64_power_nuclear'): continue
    if name not in chim: chim[name] = chimneys(name)
    S, stacks = chim[name]; R = rot_matrix(rot)
    for px, py, pz in stacks:
        ox, oy = px - S[0] // 2, py - S[1] // 2
        wx = cx + R[0][0] * ox + R[0][1] * oy; wy = cy + R[1][0] * ox + R[1][1] * oy
        for j in range(2):
            k = rng.randrange(len(pmodels)); seq = pmodels[k:] + pmodels[:k]
            s = sc.shp([(m, {'_f': str(2 * i)}) for i, m in enumerate(seq)], attrs={'_loop': '1', '_frm_id': str(seq[0])})
            jx, jy = (0, 0) if j == 0 else (rng.randint(-3, 3), rng.randint(-3, 3))
            kids.append(sc.trn(s, layer=1, frames=[{'_t': f'{wx + jx:.0f} {wy + jy:.0f} {pz + 8 + 3 * j}'}], attrs={'_name': 'smoke'}))
            puffs += 1

sc.save(out_path, SRC)
print(f'{out_path}: {N}x{N} tiles = {L}x{L} voxels | objects {len(kids)} | nodes {len(sc.nodes)} | models {len(sc.models)} | cars {ncars} | smoke {puffs}')
print('cores', cores, '| industrial', indc)
print('civic', sorted(Counter(special.values()).items()))
