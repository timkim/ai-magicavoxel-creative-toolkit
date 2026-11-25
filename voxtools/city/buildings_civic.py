"""Civic buildings, batch 1: church, school, stadium, military base.
Conventions: 16 voxels per tile (footprints 32/48/64), a 1-voxel lot layer at z=0 with a coloured
border ring, 1-voxel window detail, and the small props in props.json (trees, flag, cars)."""
import math, random
import numpy as np
from vkit import *

# ---- palette indices used by the base palette (palette.json) ----
ASPH, ASPH2, PAVE, PAVE_L = 9, 11, 255, 254       # asphalt, road grey, light pavement
GREY_D, GREY, GREY_L, WHITE = 129, 12, 14, 216
LAWN, LAWN_D, HEDGE = 208, 96, 81
WIN, WIN2, WIN_D, BLACK = 190, 189, 192, 136
RED, YELLOW, GOLD, BROWN, BROWN_D = 24, 252, 250, 72, 126
ORANGE = 251

# ---- new building colours (free slots 97-112) ----
NEW_COLOURS = {
    97: (0xd9, 0xc7, 0x9e),  # church stone
    98: (0xb2, 0x9c, 0x72),  # stone shadow / trim
    99: (0x4b, 0x52, 0x6b),  # slate roof
    100: (0x3d, 0x6f, 0xd1), # stained glass blue
    101: (0xb0, 0x3a, 0x8c), # stained glass magenta
    102: (0xe0, 0xa8, 0x48), # school brick (warm yellow)
    103: (0x5b, 0x6b, 0x2e), # olive drab
    105: (0xb9, 0xa5, 0x6b), # khaki ground
    106: (0x3f, 0x4a, 0x22), # dark olive
    107: (0xb5, 0x45, 0x2f), # running-track red
    108: (0x77, 0xcc, 0x4a), # pitch stripe light
    109: (0x2a, 0x5b, 0xb8), # stadium seats blue
    110: (0xc4, 0xbd, 0xae), # warm concrete
    111: (0x8a, 0x97, 0x9c), # hangar metal
    112: (0x2c, 0x3e, 0x50), # dark glass
}
STONE, STONE_D, SLATE, GLASS_B, GLASS_M = 97, 98, 99, 100, 101
SCHOOL_BRICK, OLIVE, KHAKI, OLIVE_D, TRACK = 102, 103, 105, 106, 107
PITCH_L, SEAT, CONCRETE, METAL, GLASS_D = 108, 109, 110, 111, 112


def trees(G, spots, z=1, rng=None):
    rng = rng or random.Random(1)
    for x, y in spots:
        stamp(G, rng.choice(['x_tree_0', 'x_tree_1', 'x_tree_2', 'x_tree_3']), x, y, z)

def cars(G, spots, z=1, rng=None, rot=0):
    rng = rng or random.Random(2)
    for x, y in spots:
        stamp(G, rng.choice(['x_red_car', 'x_blue_car', 'x_white_car', 'x_green_car', 'x_yellow_car', 'x_teal_car']), x, y, z, rot)


# =====================================================================================================
def church():
    """32x32: stone nave with slate gable roof, stained-glass lancets, front bell tower and spire,
    lawn with a little churchyard of headstones."""
    G = grid(32, 32, 48)
    lot(G, LAWN, WHITE)
    box(G, 13, 22, 0, 19, 31, 1, PAVE_L)                 # front path to the street
    box(G, 1, 1, 0, 31, 3, 1, PAVE_L)                    # back footpath
    # nave: x 9..23, y 5..20, walls to z 12, roof ridge along y
    shell(G, 9, 5, 1, 23, 20, 12, STONE, floor=STONE_D)
    box(G, 9, 5, 1, 23, 20, 2, STONE_D)                  # plinth course
    for y in range(7, 19, 3):                            # tall lancet windows on both long walls
        for x in (9, 22):
            G[x, y, 4:9] = GLASS_B if (y // 3) % 2 else GLASS_M
            G[x, y, 9] = STONE_D
    gable(G, 8, 4, 24, 21, 12, SLATE, axis='y', gable_c=STONE)
    # apse at the back
    cylinder(G, 16, 5, 5, 1, 10, STONE); cylinder(G, 16, 5, 5, 10, 11, STONE_D)
    cone(G, 16, 5, 5.5, 11, 5, SLATE)
    G[:, :5, 0][G[:, :5, 0] == 0] = LAWN
    # bell tower at the front (y 19..25), centred on the nave
    box(G, 13, 19, 1, 20, 26, 24, STONE)
    box(G, 13, 19, 23, 20, 26, 24, STONE_D)              # cornice
    box(G, 12, 18, 24, 21, 27, 25, STONE_D)
    for z0 in (18,):                                     # belfry openings with a bell inside
        for x in (15, 16, 17, 18):
            G[x, 19, z0:z0 + 4] = 0; G[x, 25, z0:z0 + 4] = 0
        for y in (21, 22, 23):
            G[13, y, z0:z0 + 4] = 0; G[19, y, z0:z0 + 4] = 0
        box(G, 14, 20, z0, 19, 25, z0 + 4, 0)
        box(G, 16, 22, z0 + 1, 17, 23, z0 + 3, GOLD)
    cone(G, 16.5, 22.5, 4.5, 25, 12, SLATE)
    box(G, 16, 22, 37, 17, 23, 42, GOLD); box(G, 15, 22, 40, 18, 23, 41, GOLD)   # cross
    # front door and rose window on the tower face (y = 25)
    box(G, 15, 25, 1, 18, 26, 5, BROWN); G[16, 25, 5] = BROWN
    for dx, dz in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)]:
        G[16 + dx, 25, 11 + dz] = GLASS_M if (dx, dz) == (0, 0) else GLASS_B
    G[13, 22:24, 8:12] = GLASS_B; G[19, 22:24, 8:12] = GLASS_B
    # churchyard headstones and trees
    rng = random.Random(7)
    for x in range(3, 8, 2):
        for y in range(6, 20, 3):
            G[x, y, 1:3] = GREY if rng.random() < .7 else GREY_L
    trees(G, [(24, 6), (26, 12), (24, 18), (26, 24), (2, 24), (6, 26)], rng=rng)
    box(G, 23, 26, 1, 30, 27, 2, HEDGE)
    return trim(G)


# =====================================================================================================
def school():
    """48x48: L-shaped two-storey brick school, flat roofs with vents, playground with a basketball
    court, sandpit, flagpole, school buses in the drop-off loop."""
    G = grid(48, 48, 40)
    lot(G, PAVE, ORANGE)
    box(G, 1, 1, 0, 47, 47, 1, LAWN)
    # main wing (along x) and side wing (along y)
    def wing(x0, y0, x1, y1, h):
        shell(G, x0, y0, 1, x1, y1, h, SCHOOL_BRICK, floor=GREY)
        box(G, x0, y0, h, x1, y1, h + 1, GREY_L)                  # roof slab
        shell(G, x0, y0, h + 1, x1, y1, h + 2, WHITE)             # parapet
        for z in (3, 4, 8, 9):
            windows(G, x0, y0, x1, y1, [z], WIN, step=3)
        box(G, x0, y0, 6, x1, y1, 7, WHITE)                       # white band between storeys
        G[x0 + 1:x1 - 1, y0 + 1:y1 - 1, 6] = 0
    wing(4, 4, 40, 15, 12)
    wing(4, 15, 15, 40, 12)
    # entrance block with a clock and a canopy
    box(G, 18, 15, 1, 27, 19, 14, SCHOOL_BRICK); box(G, 18, 15, 14, 27, 19, 15, WHITE)
    box(G, 20, 18, 1, 25, 19, 5, GLASS_D)
    box(G, 17, 18, 5, 28, 21, 6, WHITE)
    for p in ((17, 20), (27, 20)): G[p[0], p[1], 1:5] = WHITE
    G[22, 18, 10] = WHITE; G[21:24, 18, 11] = WHITE; G[22, 18, 12] = WHITE; G[22, 18, 11] = BLACK  # clock
    # rooftop units
    for x0 in (8, 28): box(G, x0, 7, 14, x0 + 4, 11, 16, GREY); G[x0 + 1, 8, 16] = GREY_D
    # playground: basketball court
    box(G, 20, 24, 0, 44, 38, 1, ASPH)
    for x in range(20, 44): G[x, 24, 0] = G[x, 37, 0] = WHITE
    for y in range(24, 38): G[20, y, 0] = G[32, y, 0] = G[43, y, 0] = WHITE
    for x, y in ((21, 30), (42, 30)):
        G[x, y, 1:6] = GREY_L; G[x, y - 1:y + 2, 6] = WHITE; G[x + (1 if x < 30 else -1), y, 5] = ORANGE
    # sandpit + climbing frame
    box(G, 36, 40, 0, 44, 45, 1, 232)
    for x in (37, 42):
        for y in (41, 44): G[x, y, 1:5] = RED
    box(G, 37, 41, 5, 43, 45, 6, YELLOW)
    # drop-off loop and buses in front of the side wing
    box(G, 1, 41, 0, 30, 46, 1, ASPH2)
    for x0 in (4, 16):
        box(G, x0, 42, 1, x0 + 10, 45, 4, YELLOW); box(G, x0, 42, 4, x0 + 10, 45, 5, YELLOW)
        for x in range(x0 + 1, x0 + 9, 2): G[x, 44, 3] = BLACK; G[x, 42, 3] = BLACK
        G[x0 + 9, 42:45, 2:4] = BLACK
        G[x0 + 1, 42, 1] = G[x0 + 1, 44, 1] = G[x0 + 8, 42, 1] = G[x0 + 8, 44, 1] = BLACK
    stamp(G, 'x_flag', 34, 18, 1)
    trees(G, [(41, 5), (43, 10), (40, 18), (2, 4), (2, 30), (44, 20)], rng=random.Random(3))
    return trim(G)


# =====================================================================================================
def stadium():
    """64x64: oval stadium. Striped pitch, red running track, raked blue seating with aisles, a concrete
    outer wall, roof canopies on the long sides, four floodlight towers and a car park."""
    S = 64
    G = grid(S, S, 48)
    lot(G, ASPH, RED)
    rng = random.Random(11)
    for x in range(3, S - 3, 4):                          # car park bay lines + cars
        for y in (2, S - 6):
            if not (y > 32 and 25 <= x <= 36): G[x, y:y + 4, 0] = WHITE
    cars(G, [(x + 1, 2) for x in range(3, S - 4, 4) if rng.random() < .7], rng=rng)
    cars(G, [(x + 1, S - 6) for x in range(3, S - 4, 4) if rng.random() < .7 and not 25 <= x <= 36], rng=rng)
    cx, cy = S / 2, S / 2
    A, B = 28.5, 22.5                                      # outer ellipse radii (x, y)
    for x in range(S):
        for y in range(S):
            u, v = (x + .5 - cx), (y + .5 - cy)
            e = (u / A) ** 2 + (v / B) ** 2                   # 1 at outer wall
            if e > 1: continue
            # inner shapes in "ellipse units"
            r = math.sqrt(e)
            if abs(u) < 17 and abs(v) < 10:                   # pitch
                G[x, y, 1] = PITCH_L if (x // 3) % 2 else LAWN
                if abs(u) in (16.5,) or abs(v) == 9.5 or abs(u) < 0.6 or abs(math.hypot(u, v) - 4) < .5:
                    G[x, y, 1] = WHITE
            elif r < .78:                                     # running track
                G[x, y, 1] = TRACK
                if abs(r - .7) < .012 * 2 or abs(r - .74) < .02: G[x, y, 1] = WHITE
            else:                                             # raked seating: rises outward
                t = (r - .78) / .19
                tier = min(int(t * 7), 6)                       # 7 stepped tiers, 2 voxels each
                h = 2 + tier * 2
                G[x, y, 1:h] = CONCRETE
                ang = math.degrees(math.atan2(v, u)) % 360
                aisle = int(ang) % 30 < 3
                G[x, y, h] = GREY_L if aisle else (SEAT if tier % 2 == 0 else 235)
                if r > .965:                                   # outer wall with window slits
                    G[x, y, 1:h + 3] = CONCRETE
                    G[x, y, h + 2] = WHITE
                    if int(ang) % 6 < 2:
                        G[x, y, 6:8] = GLASS_D; G[x, y, 12:14] = GLASS_D
    # canopies over the two long stands
    for y0, y1 in ((10, 15),):                           # canopy over the main (far) stand only
        box(G, 14, y0, 21, 50, y1, 22, WHITE)
        for x in range(14, 51, 6):
            G[x, y0 if y0 < 32 else y1 - 1, 15:21] = GREY_L
    # scoreboard
    box(G, 29, 9, 20, 35, 10, 25, BLACK); G[30:34, 9, 21:24] = YELLOW
    # floodlights
    for fx, fy in ((6, 10), (57, 10), (6, 53), (57, 53)):
        box(G, fx, fy, 1, fx + 1, fy + 1, 36, GREY_L)
        box(G, fx - 2, fy - 1, 36, fx + 3, fy + 2, 39, GREY)
        box(G, fx - 2, fy + (1 if fy < 32 else -1), 37, fx + 3, fy + (2 if fy < 32 else 0), 39, 220)
    # entrance plaza
    box(G, 28, S - 10, 0, 36, S - 1, 1, PAVE_L)
    return trim(G)


# =====================================================================================================
def military_base():
    """64x64: fenced base with a curved-roof hangar, two barracks, a control tower, helipad with a
    helicopter, parked vehicles, watchtowers and a gatehouse."""
    S = 64
    G = grid(S, S, 40)
    lot(G, KHAKI, OLIVE_D)
    rng = random.Random(5)
    for x in range(1, S - 1):                              # patchy ground
        for y in range(1, S - 1):
            if rng.random() < .12: G[x, y, 0] = 232
    box(G, 2, 40, 0, 62, 50, 1, ASPH)                     # apron / taxiway
    for x in range(4, 60, 4): G[x:x + 2, 45, 0] = YELLOW
    box(G, 28, 50, 0, 34, 63, 1, ASPH2)                   # access road to gate
    # perimeter fence with posts
    for i in range(1, S - 1):
        for x, y in ((i, 1), (i, S - 2), (1, i), (S - 2, i)):
            if 27 <= x <= 34 and y == S - 2: continue    # gate gap
            G[x, y, 1:4] = GREY if i % 4 == 0 else 0
            if i % 4: G[x, y, 3] = GREY_L; G[x, y, 1] = GREY_L
    # gatehouse with barrier
    box(G, 35, 56, 1, 40, 61, 6, CONCRETE); box(G, 34, 55, 6, 41, 62, 7, OLIVE_D)
    G[35, 58:60, 3:5] = WIN; G[37:39, 56, 3:5] = WIN
    box(G, 28, 58, 3, 35, 59, 4, RED); G[29, 58, 3] = G[31, 58, 3] = G[33, 58, 3] = WHITE
    # hangar: half-cylinder roof along y
    hx0, hx1, hy0, hy1 = 5, 25, 8, 38
    hc, hr = (hx0 + hx1) / 2, (hx1 - hx0) / 2
    for x in range(hx0, hx1):
        u = x + .5 - hc
        top = int(math.sqrt(max(hr * hr - u * u, 0)) * 1.0) + 1
        for y in range(hy0, hy1):
            G[x, y, 1:top + 1] = 0
            G[x, y, top] = METAL if (x % 3) else GREY
            if y in (hy0, hy1 - 1): G[x, y, 1:top] = METAL
    box(G, hx0 + 3, hy1 - 1, 1, hx1 - 3, hy1, 9, GREY_D)   # big door (closed, dark)
    for x in range(hx0 + 3, hx1 - 3, 3): G[x, hy1 - 1, 1:9] = GREY
    # barracks x2: long low blocks with pitched roofs
    for y0 in (8, 20):
        box(G, 30, y0, 1, 56, y0 + 8, 6, OLIVE)
        box(G, 30, y0, 1, 56, y0 + 8, 2, OLIVE_D)
        windows(G, 30, y0, 56, y0 + 8, [3, 4], WIN_D, step=3)
        gable(G, 30, y0, 56, y0 + 8, 6, OLIVE_D, axis='x', gable_c=OLIVE)
        G[42:44, y0 + 7, 1:4] = BROWN
    # control tower
    box(G, 52, 30, 1, 57, 35, 16, CONCRETE)
    box(G, 50, 28, 16, 59, 37, 20, GLASS_D); box(G, 50, 28, 16, 59, 37, 17, CONCRETE)
    box(G, 50, 28, 20, 59, 37, 21, OLIVE_D)
    G[54, 32, 21:26] = GREY_L; G[54, 32, 26] = RED
    # helipad with helicopter
    disc(G, 44, 56, 5, 0, ASPH)
    for z in range(1):
        for dy in range(-2, 3): G[42, 56 + dy, 0] = WHITE; G[46, 56 + dy, 0] = WHITE
        G[43:46, 56, 0] = WHITE
    box(G, 42, 55, 1, 48, 58, 4, OLIVE); box(G, 47, 55, 2, 48, 58, 4, GLASS_D)
    box(G, 38, 56, 2, 42, 57, 3, OLIVE); G[38, 56, 3:5] = OLIVE
    box(G, 39, 56, 4, 51, 57, 5, BLACK); box(G, 44, 50, 4, 46, 62, 5, BLACK)
    G[43, 55, 1] = G[47, 55, 1] = G[43, 57, 1] = G[47, 57, 1] = GREY
    # vehicles on the apron: tanks and trucks
    for x0 in (6, 16, 26):
        box(G, x0, 41, 1, x0 + 7, 44, 2, BLACK); box(G, x0, 41, 2, x0 + 7, 44, 3, OLIVE)
        box(G, x0 + 2, 41, 3, x0 + 5, 44, 4, OLIVE_D); box(G, x0 + 5, 42, 3, x0 + 9, 43, 4, OLIVE_D)
    for x0 in (40, 49):
        box(G, x0, 41, 1, x0 + 7, 44, 4, OLIVE); box(G, x0 + 5, 41, 2, x0 + 7, 44, 4, OLIVE_D)
        G[x0 + 6, 41:44, 3] = GLASS_D
        box(G, x0, 41, 4, x0 + 5, 44, 5, KHAKI)
    # watchtowers in two corners
    for wx, wy in ((3, 3), (58, 3)):
        for dx in (0, 2):
            for dy in (0, 2): G[wx + dx, wy + dy, 1:10] = BROWN_D
        box(G, wx - 1, wy - 1, 10, wx + 4, wy + 4, 11, BROWN); box(G, wx - 1, wy - 1, 13, wx + 4, wy + 4, 14, OLIVE_D)
        for dx in (-1, 3):
            for dy in (-1, 3): G[wx + dx, wy + dy, 11:13] = BROWN_D
    stamp(G, 'x_flag', 26, 52, 1)
    trees(G, [(3, 52), (8, 56), (58, 52)], rng=rng)
    return trim(G)


BUILDINGS = {'32_church': church, '48_school': school, '64_stadium': stadium, '64_military_base': military_base}
