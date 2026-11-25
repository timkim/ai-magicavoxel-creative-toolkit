# ai-magicavoxel-creative-toolkit

Skills, scripts and tools I use with AI assistants (Claude) for voxel art in
[MagicaVoxel](https://ephtracy.github.io/). They read and write `.vox` files, build "assemble from the
sky" animations with synced 16-bit sound effects, generate smooth camera paths, build beach scenes
(waves, sand, palm trees) and generate cities from a procedural kit.

## What's inside

| Path | What it does |
| --- | --- |
| **Core** | |
| `voxtools/voxlib.py`, `voxwrite.py`, `scenegraph.py` | Read and write `.vox` files with full scene graphs (groups, transforms, layers, animation, flipbooks) |
| `voxtools/inspect_vox.py` | Print a file's object tree and compute its world-space voxels |
| `voxtools/isorender.py` | Quick isometric PNG previews of objects, without opening MagicaVoxel |
| **Animation** | |
| `voxtools/fall.py` | Make any scene fall from the sky and assemble itself, in small cubes or floor by floor |
| `voxtools/landing_sfx.py` | Synthesised SNES-style gravel sounds, one per landing piece, lighter the higher it lands |
| `voxtools/smooth_camera.py` | Turn a few camera keyframes into a smooth per-frame path (console commands, CSV or JSON) |
| **Beach scenes** | |
| `voxtools/wave.py` | A looping ocean wave that curls over and crashes (barrel, foam, spray), as a flipbook |
| `voxtools/texture_sand.py` | Texture flat sand: colour patches, grain, wind ripples, pebbles and shells |
| `voxtools/palm.py` | A palm tree (ringed leaning trunk, drooping fronds, coconuts), planted on a scene's ground |
| **City kit** | |
| `voxtools/city/add_assets.py` | 15 buildings and 16 terrain tiles, as a standalone `.vox` or added into your own scene |
| `voxtools/city/city_generator.py` | A whole zoned city (roads, traffic lights, cars, smoke) from a library of tile models |
| **Other** | |
| `skills/magicavoxel-vox/` | A Claude skill: the `.vox` rules MagicaVoxel really enforces, and how to check results in the app |
| `tests/test_fall.py` | Checks that a fall animation lands voxel-for-voxel on the original |

## Setup

Requires Python 3.9 or newer.

```sh
pip install -r requirements.txt
```

The examples below run from `voxtools/` (the city kit runs from `voxtools/city/`). Every script writes a
**new** file and never modifies its input. Run any script with `--help` to see all its options.

## Assemble-from-the-sky animation

```sh
cd voxtools
python fall.py scene.vox scene_fall.vox                                   # everything, 3-voxel cubes, bottom-up
python fall.py scene.vox scene_fall.vox --objects tower bridge            # only some objects
python fall.py city.vox city_fall.vox --pieces floors --order wave --centre 48_city_hall
```

Each object is cut into pieces: cubes, or whole-width floor slices. Every piece becomes its own animated
object that starts 160–320 voxels up and drops into place with a gravity ease-in. Landing times are
randomised so pieces on the same level don't land in lock-step.

- **`--order height`** (default): everything lands bottom-up across the whole scene.
- **`--order wave`**: objects land in a wave spreading out from `--centre` (an object name or `x,y`).
  Each object builds up level by level, `--stack` frames apart.
- **Tuning:** `--size`, `--drop`, `--drop-jitter`, `--fall`, `--duration`, `--jitter`, `--start` and `--seed`.
- **Existing animation:** objects that are already animated are left alone. Flipbooks (blinking lights,
  for example) keep animating and fall as one piece.
- **Timeline:** MagicaVoxel's timeline defaults to 0–30 frames. Extend it to the "last landing frame"
  the script prints.
- **Large scenes:** cubes make a lot of pieces. Use `--pieces floors` or a larger `--size`.

### Sound effects

```sh
python landing_sfx.py scene_fall.vox sfx/ --fps 30
```

Writes one WAV for the whole animation (starting at frame 0), eight single "crunch" one-shots, and a
per-frame landing count. The sounds are synthesised (filtered noise, 32 kHz crush, short echo), so there
are no samples to license.

## Smooth camera paths

```sh
python smooth_camera.py ../examples/camera_keys.json path.txt --format console --with-time
```

The input is a list of keyframes (frame, x, y, z, zoom, pitch, yaw, roll; see `examples/camera_keys.json`).
The output is one value per frame on a monotone cubic spline. The path hits every keyframe exactly, speed
changes smoothly through them with no stop-and-go jitter, and zoom moves on a log scale so pull-backs
feel even.

Output formats (`--format`):

- `console`: one MagicaVoxel console line per frame (`cam rx … | cam ry … | … | set a_time N`).
- `csv`: a table of values.
- `segments`: JSON one-frame segments for camera-driver scripts.

## Beach scenes

### Ocean waves

```sh
python wave.py wave.vox                                    # 24-frame loop, 256 long, 150 high
python wave.py wave.vox --frames 32 --length 768 --height 170
python wave.py wave.vox --peel                             # the break travels along the wave
python wave.py scene_plus_wave.vox --into scene.vox        # add a wave to a copy of a scene
```

The wave is a sheet of water built from a cross-section. Over the loop it goes through a plunging break:
the swell rises, the crest curls, the lip shoots out and lands in front of the face (the barrel), the
impact explodes into foam and spray, and the next swell builds. The loop is seamless.

- **Lip:** as it throws, the lip splits into irregular fingers that reach out and curl down by different
  amounts, so the leading edge is scalloped (`--fingers`, `--finger-width`). Spray is scattered in 3D as
  clumps of 1–4 voxel cubes (`--spray`).
- **Look and timing:** colours (`--water`, `--shade`, `--foam`), `--thickness`, `--frames` and `--step`
  (animation frames per wave frame, default 2).
- **Blocks:** the sea is tiled into blocks of `--width` × `--segment` × `--zsize`. If the break is wider
  than `--width`, it is squeezed horizontally to fit, by the same amount on every frame.
- **Size limit:** MagicaVoxel models are at most 256 voxels per side, so lengths over 256 are split into
  aligned segments. Big waves are heavy (a 256 × 256 × 200 frame is 0.3–0.7 million voxels), so keep
  `--thickness` and `--frames` in check.

**Waves rolling onto a beach.** With `--set N`, N waves travel toward a sand beach, evenly staggered over
the loop. Each rises out of the flat sea at the back, breaks as it comes in and crashes near the shore
while the next one builds behind it. `--ocean` adds open water behind the waves, with gentle swells
rolling toward the shore (`--ocean-swell`, `--swell-length`). The swells taper off where they meet the
breaking zone and loop with the waves.

```sh
# A small wave whose whole break fits in 24 × 24 × 48 blocks
python wave.py wave.vox --length 512 --segment 24 --width 24 --zsize 48 --height 26 --thickness 2 --margin 3

# Three waves crashing on a beach, with 256 voxels of open ocean behind them
python wave.py set.vox --set 3 --length 512 --segment 24 --width 24 --zsize 48 --height 26 --thickness 2 \
    --margin 3 --frames 30 --step 1 --sea-width 144 --travel 96 --beach 24 --ocean 256
```

### Sand texture

```sh
python texture_sand.py beach.vox beach_textured.vox             # texture every voxel of colour index 4
python texture_sand.py beach.vox out.vox --sand 12 --ripple 9 --ripple-angle 30 --no-pebbles
```

Recolours the chosen sand colour with patchy light and dark tones and fine grain. It also raises wavy
wind ripples in patches on the surface and scatters a few pebbles and shell bits. The texture is based on
world position, so it lines up across objects and stays identical in every animation frame. New sand
shades go into free palette slots.

### Palm trees

```sh
python palm.py palm.vox                                          # standalone tree
python palm.py beach_palm.vox --into beach.vox --at=-300,80      # plant on the ground at world x,y
python palm.py palm.vox --height 60 --lean 22 --lean-dir 90 --fronds 10 --seed 9
python palm.py big_palm.vox --scale 2 --lean 26 --lean-dir 90    # twice the size, leaning to the side
python palm.py palm.vox --sway 1.5 --frames 30 --flip-y          # mirrored, swaying in a 30-frame loop
python palm.py beach2.vox --into beach.vox --replace --at=-330,40 --sway 1.5   # swap out an existing palm_tree
```

Builds a curved, ringed trunk that leans and curves back upright, a crown with coconuts, and fronds that
arch out and droop with leaflets on both sides. Change `--seed` for a different tree.

- **`--into`:** finds the ground height at `--at` and plants the tree there in a copy of the scene.
  Colours go into free palette slots. Write `--at=X,Y` with `=` when X is negative.
- **`--sway`:** animates the tree as a looping flipbook. The trunk rocks with the wind and every frond
  bobs on its own timing (`--wind-dir`, `--frames`, `--step`).

## City kit

```sh
cd voxtools/city
python add_assets.py --list
python add_assets.py assets.vox                          # all 32 assets in one file
python add_assets.py my_city_plus.vox --into my_city.vox # add them to your scene
python add_assets.py --preview sheet.png
```

The kit has 15 buildings and 16 terrain tiles:

- **Civic:** church, school, college, museum, prison.
- **Big sites:** stadium, military base, zoo, marina, airport.
- **Power:** coal, gas, hydro dam, and an animated wind farm.
- **Parks:** two large parks.
- **Terrain:** grass, dirt, sand, rock, water, shoreline pieces, forest, rubble, slopes and hills.

Tiles are 16 voxels and building footprints are 32, 48 or 64.

**Palette:** terrain uses only indices 161–176, and building colours sit in 97–112. Select the terrain
entries in the palette to change all terrain materials at once, for example to make the water glass.
Water inside the marina, dam, zoo and parks uses the same indices. With `--into`, the tool checks that
those indices are free in your scene. If your file has a custom palette order, it also gives the terrain
colours their own two palette rows.

### City generator

```sh
python city_generator.py library.vox city.vox --seed 7 --blocks 25
```

Needs a library `.vox` whose objects follow a naming scheme: `16_res_*`, `32_com_*`, `64_ind_*`,
`16_road`, `48_city_hall` and so on (see `--help`). With 25 blocks per side, the city fills
MagicaVoxel's whole 2048³ scene.

## The Claude skill

`skills/magicavoxel-vox/SKILL.md` is a skill for Claude. It covers the `.vox` rules that MagicaVoxel
enforces but the official spec doesn't mention. The most important is node ordering: break it and parts
of your scene silently vanish. It also covers how to verify results in the app with computer use.

To use it, add the folder as a custom skill in Claude and keep `voxtools/` alongside it so the skill can
run the scripts.

`skills/magicavoxel-vox/references/` holds the official `.vox` format spec from
[ephtracy/voxel-model](https://github.com/ephtracy/voxel-model) (MIT, licence included). The skill
summarises it and lists where real files differ from it.

## Notes

- Tested with MagicaVoxel 0.99.7.
- MIT licensed (see `LICENSE`). The building designs, palette and props are included under the same licence.
- This repo is not affiliated with MagicaVoxel.
