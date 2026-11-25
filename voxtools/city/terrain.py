"""16x16 terrain tiles. Every voxel uses ONLY the reserved terrain palette row 161-176, so the whole
terrain set can be selected in the palette and re-materialed (e.g. water -> glass) in one go."""
import math, random
import numpy as np
from vkit import grid, to_vox, trim

TERRAIN_COLOURS = {
    161: (0x5f, 0xa8, 0x3a),  # grass
    162: (0x4c, 0x8f, 0x2e),  # grass dark (speckle)
    163: (0x8a, 0x6a, 0x44),  # soil
    164: (0x6b, 0x4f, 0x32),  # soil dark (strata)
    165: (0xe3, 0xd2, 0x9a),  # sand
    166: (0x9a, 0x95, 0x8c),  # rock
    167: (0x6e, 0x6a, 0x63),  # rock dark
    168: (0x3f, 0xa7, 0xd6),  # water shallow
    169: (0x1f, 0x6f, 0xb0),  # water deep
    170: (0xd8, 0xf0, 0xf7),  # surf / foam
    171: (0x2f, 0x7a, 0x2a),  # forest canopy
    172: (0x23, 0x60, 0x1f),  # forest canopy dark
    173: (0x5a, 0x3b, 0x22),  # tree trunk
    174: (0x8c, 0x83, 0x78),  # rubble
    175: (0x4b, 0x46, 0x40),  # bedrock
    176: (0xf4, 0xf6, 0xf8),  # snow (mountain caps)
}
GRASS, GRASS_D, SOIL, SOIL_D, SAND, ROCK, ROCK_D, WATER, WATER_D, FOAM, LEAF, LEAF_D, TRUNK, RUBBLE, BEDROCK, SNOW = range(161, 177)
T, LEVEL = 16, 8          # tile size; one terrain height step = half a tile

def speckle(c, alt, p, rng):
    return alt if rng.random() < p else c

def column_fill(G, x, y, h, top, rng, rocky=False):
    """Fill one column up to height h (top voxel at h-1) with strata underneath."""
    for z in range(h - 1):
        if z == 0: c = BEDROCK if h > 2 else SOIL
        elif rocky and z < h - 3: c = ROCK if (z + x // 3) % 3 else ROCK_D
        else: c = SOIL_D if z % 4 == 2 else SOIL
        G[x, y, z] = c
    G[x, y, h - 1] = top

def flat(top, alt=None, p=0.0, seed=0):
    rng = random.Random(seed); G = grid(T, T, 1)
    for x in range(T):
        for y in range(T): G[x, y, 0] = speckle(top, alt, p, rng) if alt else top
    return G

def heightfield(fn, seed=0, snow=False):
    """fn(x, y) -> height in voxels (>=1). Grass on top, soil/rock strata below."""
    rng = random.Random(seed); G = grid(T, T, 2 * LEVEL + 2)
    for x in range(T):
        for y in range(T):
            h = max(1, int(round(fn(x + .5, y + .5))))
            top = speckle(GRASS, GRASS_D, .15, rng)
            if snow and h >= 2 * LEVEL: top = SNOW
            column_fill(G, x, y, h, top, rng, rocky=h > LEVEL + 2)
    return trim(G)

ramp = lambda t: 1 + LEVEL * min(max(t, 0), 1)          # t in 0..1 across the tile

def shore(kind, seed=0):
    """Water on the low-y side (edge), low-x/low-y quadrant (outer corner) or everywhere but one corner (inner)."""
    rng = random.Random(seed); G = grid(T, T, 1)
    for x in range(T):
        for y in range(T):
            if kind == 'edge': d = y
            elif kind == 'outer': d = T - math.hypot(T - x, T - y)   # land only in the far corner
            else: d = math.hypot(x, y)                                # water only in the near corner
            if d < 5: c = WATER_D if d < 2.5 else WATER
            elif d < 6: c = FOAM
            elif d < 9: c = speckle(SAND, FOAM, .05, rng)
            else: c = speckle(GRASS, GRASS_D, .15, rng)
            G[x, y, 0] = c
    return G

def forest(seed=0):
    rng = random.Random(seed); G = grid(T, T, 12)
    for x in range(T):
        for y in range(T): G[x, y, 0] = speckle(GRASS_D, GRASS, .3, rng)
    spots = [(3, 3), (10, 2), (6, 8), (13, 9), (2, 12), (9, 13)]
    for cx, cy in spots:
        cx += rng.randint(-1, 1); cy += rng.randint(-1, 1); h = rng.randint(6, 9); r = rng.uniform(2, 2.8)
        G[cx, cy, 1:4] = TRUNK
        for z in range(3, h + 1):
            rr = r * (1 - (z - 3) / (h - 1)) + .6
            for x in range(cx - 3, cx + 4):
                for y in range(cy - 3, cy + 4):
                    if 0 <= x < T and 0 <= y < T and math.hypot(x - cx, y - cy) <= rr:
                        G[x, y, z] = LEAF_D if (z + x + y) % 3 == 0 else LEAF
    return trim(G)

def rubble(seed=0):
    rng = random.Random(seed); G = grid(T, T, 4)
    for x in range(T):
        for y in range(T): G[x, y, 0] = speckle(SOIL, RUBBLE, .4, rng)
    for _ in range(40):
        x, y = rng.randrange(T), rng.randrange(T); h = rng.choice([1, 1, 2, 3])
        G[x, y, 1:1 + h] = rng.choice([RUBBLE, ROCK, ROCK_D])
    return trim(G)

def rocks(seed=0):
    rng = random.Random(seed); G = grid(T, T, 7)
    for x in range(T):
        for y in range(T): G[x, y, 0] = speckle(ROCK, ROCK_D, .3, rng)
    for cx, cy, r in ((4, 5, 2.6), (11, 10, 3.2), (12, 3, 1.6)):
        for x in range(T):
            for y in range(T):
                d = math.hypot(x - cx, y - cy)
                if d < r:
                    h = int((1 - d / r) * 4) + 1
                    G[x, y, 1:1 + h] = ROCK; G[x, y, h] = ROCK_D if (x + y) % 2 else ROCK
    return trim(G)

TILES = {
    '16_terrain_grass':        lambda: flat(GRASS, GRASS_D, .15, 1),
    '16_terrain_dirt':         lambda: flat(SOIL, SOIL_D, .25, 2),
    '16_terrain_sand':         lambda: flat(SAND, FOAM, .04, 3),
    '16_terrain_rock':         lambda: rocks(4),
    '16_terrain_water':        lambda: flat(WATER, FOAM, .02, 5),
    '16_terrain_water_deep':   lambda: flat(WATER_D, WATER, .05, 6),
    '16_terrain_shore_edge':   lambda: shore('edge', 7),
    '16_terrain_shore_outer':  lambda: shore('outer', 8),
    '16_terrain_shore_inner':  lambda: shore('inner', 9),
    '16_terrain_forest':       lambda: forest(10),
    '16_terrain_rubble':       lambda: rubble(11),
    '16_terrain_hill':         lambda: heightfield(lambda x, y: 1 + LEVEL, 12),
    '16_terrain_slope':        lambda: heightfield(lambda x, y: ramp(y / T), 13),
    '16_terrain_slope_outer':  lambda: heightfield(lambda x, y: ramp(min(x, y) / T), 14),
    '16_terrain_slope_inner':  lambda: heightfield(lambda x, y: ramp(max(x, y) / T), 15),
    '16_terrain_hill_2':       lambda: heightfield(lambda x, y: 1 + 2 * LEVEL, 16, snow=True),
}
