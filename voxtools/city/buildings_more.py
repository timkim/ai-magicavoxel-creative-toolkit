"""Buildings, batch 2: college, prison, zoo, marina, airport, museum, coal/gas/wind/hydro power, large parks.
Same conventions as buildings_civic.py. Water and rock use the terrain palette indices, so they change
material together with the terrain tiles."""
import math, random
import numpy as np
from vkit import *
from buildings_civic import *            # palette names + NEW_COLOURS, trees(), cars()
from terrain import WATER, WATER_D, FOAM, ROCK, ROCK_D, SAND as T_SAND

BRICK, BRICK_D, RUST, MARBLE = 113, 119, 117, 253
SKY_B, TEAL, PURPLE, SAND = 245, 238, 243, 232
POWER_RING, UTIL_RING, PARK_RING = BLACK, 250, LAWN_D

def lawn_lot(S, ring, ground=LAWN):
    G = grid(S, S, 80); lot(G, ground, ring); return G

def path(G, x0, y0, x1, y1, c=PAVE_L):
    box(G, x0, y0, 0, x1, y1, 1, c)

def columns(G, xs, y, z0, z1, c=WHITE):
    for x in xs: G[x, y, z0:z1] = c

def flag(G, x, y): stamp(G, 'x_flag', x, y, 1)

# =====================================================================================================
def college():
    """48x48 campus: brick main hall with a white portico and clock tower, two side halls, quad."""
    G = lawn_lot(48, 235)
    path(G, 22, 20, 26, 47); path(G, 4, 30, 44, 33); path(G, 10, 20, 38, 22)
    # main hall (back, along x)
    box(G, 8, 4, 1, 40, 16, 12, BRICK); box(G, 8, 4, 1, 40, 16, 2, BRICK_D)
    windows(G, 8, 4, 40, 16, [4, 5, 8, 9], WIN, step=2)
    gable(G, 7, 3, 41, 17, 12, SLATE, axis='x', gable_c=BRICK)
    # portico with columns and pediment on the front (y=16)
    box(G, 18, 16, 1, 30, 20, 2, WHITE)
    columns(G, range(19, 30, 2), 19, 2, 10)
    box(G, 18, 16, 10, 30, 20, 11, WHITE)
    for k in range(4): box(G, 18 + k * 2, 19, 11 + k, 30 - k * 2, 20, 12 + k, WHITE)
    box(G, 22, 15, 1, 26, 16, 6, BROWN)
    # clock tower behind the portico
    box(G, 21, 7, 12, 27, 13, 26, BRICK); box(G, 20, 6, 26, 28, 14, 27, WHITE)
    for f in ((21, 9), (26, 9)): pass
    G[24, 12, 20] = BLACK; G[23:26, 12, 19:22][G[23:26, 12, 19:22] == BRICK] = WHITE; G[24, 12, 20] = BLACK
    cone(G, 24, 10, 4.5, 27, 7, SLATE); G[24, 9, 34:37] = GOLD
    # side halls along y
    for x0 in (2, 36):
        box(G, x0, 22, 1, x0 + 10, 44, 9, BRICK); box(G, x0, 22, 1, x0 + 10, 44, 2, BRICK_D)
        windows(G, x0, 22, x0 + 10, 44, [4, 5, 7], WIN, step=2)
        gable(G, x0 - 1, 22, x0 + 11, 44, 9, SLATE, axis='y', gable_c=BRICK)
    trees(G, [(14, 36), (30, 36), (14, 24), (30, 24), (18, 42), (28, 42)], rng=random.Random(21))
    flag(G, 33, 21)
    return trim(G)

# =====================================================================================================
def prison():
    """48x48: tall perimeter wall with guard towers, X-shaped cell blocks, exercise yard."""
    G = lawn_lot(48, BLACK, ground=GREY)
    box(G, 1, 1, 0, 47, 47, 1, 129)
    shell(G, 2, 2, 1, 46, 46, 10, CONCRETE)             # wall
    shell(G, 2, 2, 10, 46, 46, 11, GREY)
    for i in range(3, 45, 2):                            # razor wire
        for x, y in ((i, 2), (i, 45), (2, i), (45, i)): G[x, y, 11] = GREY_L
    for tx, ty in ((1, 1), (42, 1), (1, 42), (42, 42)):  # guard towers
        box(G, tx, ty, 1, tx + 5, ty + 5, 16, CONCRETE)
        box(G, tx, ty, 13, tx + 5, ty + 5, 15, GLASS_D); box(G, tx - 1, ty - 1, 16, tx + 6, ty + 6, 17, GREY)
        G[tx + 2, ty + 2, 17:19] = GREY_L; G[tx + 2, ty + 2, 19] = YELLOW
    # gate
    box(G, 21, 45, 1, 27, 47, 8, GREY_D); box(G, 20, 44, 8, 28, 47, 10, CONCRETE)
    # cell blocks: a cross of two long wings
    for (x0, y0, x1, y1) in ((8, 18, 40, 26), (20, 6, 28, 30)):
        box(G, x0, y0, 1, x1, y1, 14, CONCRETE); box(G, x0, y0, 14, x1, y1, 15, GREY)
        for z in (3, 6, 9, 12):
            windows(G, x0, y0, x1, y1, [z], BLACK, step=2)
    box(G, 18, 16, 1, 30, 28, 18, GREY_L); box(G, 18, 16, 18, 30, 28, 19, GREY)   # central hub
    G[19:29, 16, 15:17] = GLASS_D; G[29, 17:27, 15:17] = GLASS_D
    # yard with a court and a fence
    box(G, 30, 30, 0, 44, 44, 1, ASPH)
    for x in range(30, 44): G[x, 30, 1:4] = GREY_L if x % 2 else 0
    for y in range(30, 44): G[30, y, 1:4] = GREY_L if y % 2 else 0
    for x in range(32, 43): G[x, 37, 0] = WHITE
    G[37, 31:44, 0][::2] = WHITE
    # parking strip by the gate is outside the wall
    return trim(G)

# =====================================================================================================
def animal(G, kind, x, y, z=1, rot=0):
    if kind == 'elephant':
        box(G, x, y, z + 1, x + 4, y + 2, z + 4, GREY); box(G, x - 1, y, z + 2, x, y + 2, z + 4, GREY)
        G[x - 2, y, z + 1:z + 3] = GREY
        for dx in (0, 3):
            for dy in (0, 1): G[x + dx, y + dy, z] = GREY
    elif kind == 'giraffe':
        box(G, x, y, z + 2, x + 3, y + 1, z + 4, YELLOW); G[x + 1, y, z + 3] = BROWN
        G[x, y, z:z + 2] = G[x + 2, y, z:z + 2] = YELLOW
        G[x + 2, y, z + 4:z + 8] = YELLOW; G[x + 3, y, z + 7] = YELLOW; G[x + 2, y, z + 5] = BROWN
    elif kind == 'lion':
        box(G, x, y, z, x + 3, y + 1, z + 2, RUST); box(G, x + 3, y, z + 1, x + 4, y + 1, z + 3, BROWN)
    elif kind == 'penguin':
        G[x, y, z] = WHITE; G[x, y, z + 1] = BLACK

def zoo():
    """64x64: entrance gate, sand paths, elephant/giraffe/lion paddocks, penguin pool, aviary dome."""
    S = 64; G = lawn_lot(S, 231)
    rng = random.Random(31)
    path(G, 29, 30, 35, 63, SAND); path(G, 4, 29, 60, 35, SAND); path(G, 29, 4, 35, 30, SAND)
    def paddock(x0, y0, x1, y1, ground):
        box(G, x0, y0, 0, x1, y1, 1, ground)
        for x in range(x0, x1):
            for y in (y0, y1 - 1): G[x, y, 1:3] = BROWN if x % 3 else BROWN_D
        for y in range(y0, y1):
            for x in (x0, x1 - 1): G[x, y, 1:3] = BROWN if y % 3 else BROWN_D
    paddock(3, 3, 27, 27, SAND)                          # elephants
    disc(G, 9, 9, 3.5, 0, WATER)
    for p in ((14, 15), (19, 8)): animal(G, 'elephant', *p)
    trees(G, [(20, 20), (5, 20)], rng=rng)
    paddock(37, 3, 61, 27, LAWN)                         # giraffes
    for p in ((42, 10), (50, 18), (54, 8)): animal(G, 'giraffe', *p)
    trees(G, [(56, 21), (40, 21)], rng=rng)
    paddock(3, 37, 27, 61, 232)                          # lions with rocks
    for cx, cy in ((10, 44), (18, 52)):
        for x in range(cx - 3, cx + 4):
            for y in range(cy - 3, cy + 4):
                d = math.hypot(x - cx, y - cy)
                if d < 3.2: G[x, y, 1:1 + int(4 - d)] = ROCK
    for p in ((14, 41), (21, 46), (8, 55)): animal(G, 'lion', *p)
    # penguin pool
    box(G, 37, 37, 0, 61, 49, 1, WHITE); box(G, 39, 39, 0, 59, 47, 1, WATER_D)
    for x in range(37, 61): G[x, 37, 1:3] = GLASS_D
    for p in ((38, 38), (40, 38), (58, 38), (60, 40), (37, 44), (38, 47)): animal(G, 'penguin', *p)
    # aviary dome
    cx, cy, r = 49, 55, 6.5
    for x in range(int(cx - r - 1), int(cx + r + 2)):
        for y in range(int(cy - r - 1), int(cy + r + 2)):
            for z in range(1, 9):
                d = math.sqrt((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 + ((z - 1) * 1.0) ** 2)
                if r - 1 < d <= r and ((x + y + z) % 2 == 0): G[x, y, z] = GREY_L
    trees(G, [(47, 53), (50, 56)], rng=rng)
    # entrance gate and ticket booths
    box(G, 27, 58, 1, 29, 61, 10, BROWN_D); box(G, 35, 58, 1, 37, 61, 10, BROWN_D)
    box(G, 26, 58, 10, 38, 61, 12, LAWN_D); G[29:35, 59, 10] = YELLOW
    box(G, 22, 57, 1, 26, 61, 5, YELLOW); box(G, 38, 57, 1, 42, 61, 5, YELLOW)
    box(G, 21, 56, 5, 27, 62, 6, RED); box(G, 37, 56, 5, 43, 62, 6, RED)
    trees(G, [(5, 31), (59, 31), (31, 6)], rng=rng)
    return trim(G)

# =====================================================================================================
def boat(G, x, y, length=7, sail=True, c=WHITE):
    """Small boat pointing +x: dark hull line, white deck, either a mast + thin sail or a cabin."""
    box(G, x + 1, y, 0, x + length - 1, y + 3, 1, BLACK)
    box(G, x, y, 1, x + length, y + 3, 2, c); G[x, y, 1] = G[x, y + 2, 1] = 0
    G[x + length - 1, y + 1, 1] = c
    if sail:
        G[x + 2, y + 1, 2:9] = GREY_L
        for z in range(2, 8):
            G[x + 3:x + 3 + max(1, (8 - z) // 2), y + 1, z] = WHITE
    else:
        box(G, x + 2, y, 2, x + 5, y + 3, 3, c); G[x + 2:x + 5, y + 1, 3] = GLASS_D; G[x + 4, y + 1, 2] = GLASS_D

def marina():
    """48x48: harbour water with piers and moored boats, a clubhouse and car park on land."""
    S = 48; G = lawn_lot(S, SKY_B, ground=PAVE)
    box(G, 1, 1, 0, 47, 26, 1, WATER)                    # water half
    for x in range(1, 47):
        G[x, 25, 0] = FOAM
        if x % 7 == 3: G[x, 1:24, 0][::5] = WATER_D
    box(G, 1, 26, 0, 47, 28, 1, ROCK)                    # sea wall
    G[:, 26:28, 1][G[:, 26:28, 0] == ROCK] = ROCK_D
    rngb = random.Random(43)
    for px in (12, 32):                                  # two piers with finger berths
        box(G, px, 6, 1, px + 3, 26, 2, 70)
        for y in range(6, 26, 3): G[px, y, 0] = G[px + 2, y, 0] = BROWN_D
        for y in (8, 16):
            box(G, px + 3, y, 1, px + 9, y + 1, 2, 70); box(G, px - 6, y, 1, px, y + 1, 2, 70)
            if rngb.random() < .8: boat(G, px + 3, y + 2, 7, sail=rngb.random() < .5)
            if rngb.random() < .8: boat(G, px - 7, y - 4, 6, sail=rngb.random() < .5, c=rngb.choice([WHITE, WHITE, 220]))
    boat(G, 40, 8, 6, sail=True)
    # clubhouse
    box(G, 4, 30, 1, 20, 42, 8, WHITE); windows(G, 4, 30, 20, 42, [3, 4, 5], WIN, step=2)
    box(G, 3, 29, 8, 21, 43, 9, SKY_B); box(G, 6, 32, 9, 18, 40, 11, WHITE); box(G, 5, 31, 11, 19, 41, 12, SKY_B)
    box(G, 4, 28, 1, 20, 30, 2, 70)                      # deck
    flag(G, 22, 30)
    # car park
    for x in range(25, 46, 4): G[x, 31:36, 0] = WHITE; G[x, 39:44, 0] = WHITE
    cars(G, [(x + 1, 32) for x in range(25, 44, 4)] + [(x + 1, 40) for x in range(25, 40, 4)], rng=random.Random(41))
    trees(G, [(22, 44), (4, 44), (13, 44)], rng=random.Random(42))
    return trim(np.ascontiguousarray(G[:, ::-1, :]))      # water side toward the default view

# =====================================================================================================
def plane(G, x, y, z=1, length=16, livery=SKY_B):
    """Airliner pointing +x."""
    box(G, x, y, z + 1, x + length, y + 3, z + 4, WHITE)
    box(G, x + 1, y, z + 2, x + length - 1, y + 3, z + 3, livery)
    G[x + length - 1, y + 1, z + 2:z + 4] = GLASS_D
    box(G, x + 5, y - 7, z + 2, x + 9, y + 10, z + 3, WHITE)          # wings
    box(G, x + 6, y - 4, z + 1, x + 8, y - 3, z + 2, GREY); box(G, x + 6, y + 6, z + 1, x + 8, y + 7, z + 2, GREY)
    box(G, x, y + 1, z + 4, x + 3, y + 2, z + 9, livery)             # tail fin
    box(G, x, y - 2, z + 3, x + 3, y + 5, z + 4, WHITE)
    for dx in (3, 7, 12): G[x + dx, y + 1, z] = BLACK

def airport():
    """64x64 regional airport: runway with markings, taxiway, glass terminal, control tower,
    hangar and two parked airliners."""
    S = 64; G = lawn_lot(S, SKY_B)
    box(G, 1, 4, 0, 63, 14, 1, 135)                      # runway
    for x in range(4, 60, 6): G[x:x + 3, 9, 0] = WHITE
    for x in (2, 3, 60, 61):
        for y in range(5, 14, 2): G[x, y, 0] = WHITE
    for y in (4, 13): G[1:63, y, 0] = YELLOW
    box(G, 1, 14, 0, 63, 18, 1, LAWN_D)
    box(G, 8, 18, 0, 56, 22, 1, ASPH); box(G, 8, 14, 0, 12, 18, 1, ASPH); box(G, 52, 14, 0, 56, 18, 1, ASPH)
    G[8:56, 20, 0] = YELLOW
    box(G, 4, 22, 0, 60, 40, 1, GREY)                    # apron
    plane(G, 10, 29); plane(G, 34, 29, livery=RED)
    # terminal
    box(G, 4, 42, 1, 46, 54, 9, GLASS_D); box(G, 4, 42, 1, 46, 54, 2, CONCRETE)
    for x in range(4, 46, 4): G[x, 42, 2:9] = WHITE; G[x, 53, 2:9] = WHITE
    box(G, 3, 41, 9, 47, 55, 10, WHITE)
    for x0 in (12, 30):                                  # jet bridges
        box(G, x0, 37, 4, x0 + 2, 42, 6, GREY_L)
    box(G, 4, 55, 0, 46, 63, 1, ASPH2)                   # forecourt road
    cars(G, [(x, 57) for x in range(8, 44, 5)], rng=random.Random(51), rot=0)
    # control tower
    box(G, 52, 44, 1, 56, 48, 22, CONCRETE)
    box(G, 50, 42, 22, 58, 50, 26, GLASS_D); box(G, 49, 41, 26, 59, 51, 27, WHITE)
    G[54, 46, 27:31] = GREY_L; G[54, 46, 31] = RED
    # small hangar
    box(G, 48, 22, 1, 62, 34, 10, METAL); gable(G, 48, 21, 62, 35, 10, GREY, axis='x')
    box(G, 50, 21, 1, 60, 22, 8, GREY_D)
    return trim(np.ascontiguousarray(G[:, ::-1, :]))      # runway toward the default view

# =====================================================================================================
def museum():
    """48x48: classical museum with a broad stair, colonnade, pediment, banners and a skylit roof."""
    S = 48; G = lawn_lot(S, PURPLE, ground=PAVE_L)
    box(G, 1, 1, 0, 47, 12, 1, LAWN)
    box(G, 6, 8, 1, 42, 34, 14, MARBLE); box(G, 6, 8, 1, 42, 34, 2, STONE_D)
    box(G, 6, 8, 14, 42, 34, 15, STONE)
    for z in (5, 6, 7, 8, 9):
        windows(G, 6, 8, 42, 34, [z], STONE_D, step=4, faces='y')
    box(G, 14, 14, 15, 34, 28, 17, GLASS_B)              # skylight
    for x in range(14, 34, 3): G[x, 14:28, 16] = WHITE
    # stairs + colonnade + pediment on the front (y=34)
    for k in range(4): box(G, 12, 34 + k, 1, 36, 35 + k, 4 - k, MARBLE)
    box(G, 12, 34, 4, 36, 38, 5, MARBLE)
    columns(G, range(13, 36, 2), 37, 5, 15, WHITE)
    box(G, 12, 34, 15, 36, 38, 16, WHITE)
    for k in range(6): box(G, 12 + 2 * k, 37, 16 + k, 36 - 2 * k, 38, 17 + k, WHITE)
    box(G, 12 + 2, 34, 16, 36 - 2, 37, 19, STONE)
    box(G, 21, 33, 5, 27, 34, 11, BROWN)
    for bx, c in ((9, RED), (39, GLASS_M)):              # banners
        G[bx, 34, 6:13] = c; G[bx, 34, 13] = GOLD
    # sculpture garden
    stamp(G, 'x_tree_3', 4, 3, 1); stamp(G, 'x_tree_3', 40, 3, 1)
    for x in (14, 24, 34):
        box(G, x, 4, 1, x + 2, 6, 3, MARBLE); G[x, 4, 3:6] = GREY_D
    path(G, 20, 38, 28, 47)
    return trim(G)

# =====================================================================================================
def chimney(G, cx, cy, r, h, z0=1):
    for z in range(z0, z0 + h):
        band = ((z - z0) // 4) % 2 == 0
        cylinder(G, cx, cy, r, z, z + 1, RED if band else WHITE, hollow=True)
    cylinder(G, cx, cy, r + .6, z0 + h, z0 + h + 1, GREY_D, hollow=True)

def power_coal():
    """64x64: boiler house, turbine hall, two banded chimneys, coal piles and a conveyor."""
    S = 64; G = grid(S, S, 80); lot(G, GREY_D, POWER_RING)
    box(G, 1, 1, 0, 63, 63, 1, 129)
    rng = random.Random(61)
    for cx, cy in ((12, 48), (26, 54)):                  # coal piles
        for x in range(cx - 9, cx + 10):
            for y in range(cy - 8, cy + 9):
                d = math.hypot((x - cx) / 1.1, y - cy)
                h = int(7 - d)
                if h > 0 and 0 < x < 63 and 0 < y < 63:
                    G[x, y, 1:1 + h] = BLACK; G[x, y, h] = 128 if rng.random() < .3 else BLACK
    for k in range(18):                                   # conveyor to the boiler house
        z = 4 + k // 2
        box(G, 18 + k, 38 - k // 2, z, 20 + k, 40 - k // 2, z + 1, GREY)
        if k % 4 == 0: G[19 + k, 39 - k // 2, 1:z] = GREY_L
    box(G, 30, 10, 1, 52, 32, 26, GREY)                  # boiler house
    box(G, 30, 10, 26, 52, 32, 27, GREY_D)
    windows(G, 30, 10, 52, 32, list(range(4, 24, 3)), WIN_D, step=3)
    box(G, 8, 10, 1, 30, 26, 14, CONCRETE); gable(G, 8, 10, 30, 26, 14, METAL, axis='x')   # turbine hall
    windows(G, 8, 10, 30, 26, [5, 6, 9, 10], WIN, step=2)
    chimney(G, 56, 14, 3.5, 54); chimney(G, 56, 26, 3.5, 54)
    box(G, 52, 12, 6, 55, 28, 9, GREY)                   # flue duct
    # transformer yard
    for x in range(8, 26, 4):
        for y in (32, 36):
            box(G, x, y, 1, x + 2, y + 2, 4, GREY_L); G[x, y, 4:8] = GREY
    return trim(G)

def power_gas():
    """48x48: turbine hall, two spherical gas tanks, cooling fans and a short exhaust stack."""
    S = 48; G = grid(S, S, 60); lot(G, GREY_D, POWER_RING)
    box(G, 1, 1, 0, 47, 47, 1, 129)
    for cx, cy in ((12, 12), (12, 30)):                  # spherical tanks on legs
        r = 6.5
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            for y in range(int(cy - r - 1), int(cy + r + 2)):
                for z in range(0, 20):
                    d = math.sqrt((x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 + (z + .5 - 12) ** 2)
                    if d <= r: G[x, y, z] = WHITE if z > 9 else GREY_L
        for dx, dy in ((-4, -4), (4, -4), (-4, 4), (4, 4)): G[cx + dx, cy + dy, 1:8] = GREY
        G[cx, cy - 7, 1:18] = GREY                       # ladder
    box(G, 24, 6, 1, 44, 24, 14, CONCRETE); box(G, 24, 6, 14, 44, 24, 15, SKY_B)
    windows(G, 24, 6, 44, 24, [4, 5, 9, 10], WIN, step=2)
    box(G, 24, 28, 1, 44, 40, 5, GREY)                   # air-cooled condenser with fans
    for x in range(26, 43, 5):
        for y in (31, 36): disc(G, x, y, 1.8, 5, BLACK)
    cylinder(G, 40, 15, 2.5, 15, 34, GREY_L, hollow=True); cylinder(G, 40, 15, 3, 34, 35, GREY_D, hollow=True)
    box(G, 20, 18, 3, 24, 20, 4, YELLOW)                 # gas pipes
    box(G, 18, 12, 3, 20, 31, 4, YELLOW)
    return trim(G)

def wind_turbine_frames(n_frames=4):
    """32x32 lot with three turbines. Returns a list of grids, one per animation frame (blades rotate
    30 degrees per frame; 3-blade symmetry makes 4 frames a seamless loop)."""
    S = 32; frames = []
    for f in range(n_frames):
        G = grid(S, S, 48); lot(G, LAWN, UTIL_RING)
        box(G, 1, 1, 0, 31, 31, 1, LAWN)
        rng = random.Random(71)
        for x in range(1, 31):
            for y in range(1, 31):
                if rng.random() < .15: G[x, y, 0] = LAWN_D
        for i, (tx, ty, h) in enumerate(((7, 8, 30), (22, 13, 34), (12, 24, 28))):
            box(G, tx, ty, 1, tx + 2, ty + 2, 3, CONCRETE)
            G[tx, ty, 3:h] = WHITE; G[tx + 1, ty, 3:h - 6] = WHITE
            box(G, tx - 1, ty, h, tx + 2, ty + 3, h + 2, WHITE)          # nacelle, rotor faces +y
            hub = (tx, ty + 3, h + 1)
            G[hub] = GREY
            phase = math.radians(30 * f + i * 17)
            for b in range(3):
                a = phase + b * 2 * math.pi / 3
                for k in range(1, 11):
                    x = int(round(hub[0] + math.cos(a) * k)); z = int(round(hub[2] + math.sin(a) * k))
                    if 0 <= x < S and 1 <= z < 48: G[x, hub[1], z] = WHITE if k < 10 else RED
        frames.append(G)
    return frames

def power_hydro():
    """64x64: river with a curved concrete dam, reservoir behind it, spillway foam and a power house."""
    S = 64; G = grid(S, S, 40); lot(G, LAWN, UTIL_RING)
    rng = random.Random(81)
    for x in range(1, 63):                               # river valley along y
        w = 9 + int(3 * math.sin(x / 9))
        for y in range(1, 63):
            if abs(y - 32) < w: G[x, y, 0] = WATER if abs(y - 32) < w - 2 else T_SAND
    # reservoir (raised water behind the dam, x < 24)
    for x in range(1, 24):
        for y in range(1, 63):
            G[x, y, 0:14] = 0
            if abs(y - 32) < 22:
                G[x, y, 0:13] = ROCK_D; G[x, y, 13] = WATER_D if abs(y - 32) < 20 else ROCK
            else:
                G[x, y, 0:14] = ROCK if (x + y) % 5 else ROCK_D; G[x, y, 14] = LAWN
    # dam wall, slightly curved
    for y in range(8, 57):
        xo = 24 + int(round(2 * math.cos((y - 32) / 24 * math.pi / 2) - 2))
        box(G, xo, y, 0, xo + 4, y + 1, 16, CONCRETE)
        G[xo:xo + 4, y, 16] = GREY_L
        if 26 <= y <= 38 and y % 3 != 0: G[xo + 3, y, 2:14] = FOAM   # spillway
    for y in range(26, 39): G[28:33, y, 0] = FOAM
    box(G, 32, 42, 1, 46, 52, 10, CONCRETE); gable(G, 32, 42, 46, 52, 10, METAL, axis='x')   # power house
    windows(G, 32, 42, 46, 52, [4, 5, 7], WIN, step=2)
    for x in range(48, 60, 4): G[x, 47, 1:12] = GREY; G[x - 1:x + 2, 47, 11] = GREY   # pylons
    trees(G, [(50, 5), (56, 10), (44, 56), (55, 56), (40, 5)], rng=rng)
    return trim(G)

# =====================================================================================================
def park_large(S=48):
    """Large park: pond (terrain water), looping paths, fountain plaza, gazebo, benches, lots of trees."""
    G = grid(S, S, 30); lot(G, LAWN, PARK_RING)
    rng = random.Random(91 + S)
    c = S / 2
    for x in range(1, S - 1):
        for y in range(1, S - 1):
            d = math.hypot(x + .5 - c, y + .5 - c)
            if abs(d - S * .33) < 1.2: G[x, y, 0] = SAND          # ring path
            if rng.random() < .08 and G[x, y, 0] == LAWN: G[x, y, 0] = LAWN_D
    path(G, int(c) - 1, 1, int(c) + 1, S - 1, SAND); path(G, 1, int(c) - 1, S - 1, int(c) + 1, SAND)
    # pond in one quadrant
    px, py = S * .7, S * .3
    for x in range(S):
        for y in range(S):
            d = math.hypot((x + .5 - px) / 1.3, y + .5 - py)
            if d < S * .12: G[x, y, 0] = WATER
            elif d < S * .12 + 1 and G[x, y, 0] == LAWN: G[x, y, 0] = T_SAND
    # fountain plaza in the centre
    disc(G, c, c, S * .1, 0, PAVE_L); cylinder(G, c, c, S * .07, 1, 2, WHITE, hollow=True)
    disc(G, c, c, S * .07 - 1, 1, WATER); G[int(c), int(c), 1:5] = WHITE; G[int(c), int(c), 5] = FOAM
    # gazebo
    gx, gy = int(S * .25), int(S * .72)
    disc(G, gx, gy, 4, 1, WHITE)
    for a in range(0, 360, 60):
        G[int(gx + 3 * math.cos(math.radians(a))), int(gy + 3 * math.sin(math.radians(a))), 2:6] = WHITE
    cone(G, gx, gy, 4.5, 6, 4, RED)
    # benches
    for k in range(8):
        a = k * math.pi / 4 + .3; r = S * .33 + 2
        x, y = int(c + r * math.cos(a)), int(c + r * math.sin(a))
        if 1 < x < S - 3 and 1 < y < S - 3 and G[x, y, 0] in (LAWN, LAWN_D): G[x:x + 2, y, 1] = BROWN
    spots = []
    for _ in range(int(S * S / 70)):
        x, y = rng.randrange(2, S - 6), rng.randrange(2, S - 6)
        if all(G[x + dx, y + dy, 0] in (LAWN, LAWN_D) for dx in range(5) for dy in range(5)) and \
           all(abs(x - a) > 4 or abs(y - b) > 4 for a, b in spots):
            spots.append((x, y))
    trees(G, spots, rng=rng)
    return trim(G)


BUILDINGS2 = {
    '48_college': college, '48_prison': prison, '64_zoo': zoo, '48_marina': marina,
    '64_airport': airport, '48_museum': museum, '64_power_coal': power_coal, '48_power_gas': power_gas,
    '64_power_hydro': power_hydro, '32_park_large': lambda: park_large(32), '48_park_large': lambda: park_large(48),
}
ANIMATED2 = {'32_power_wind': wind_turbine_frames}
