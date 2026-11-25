# ai-magicavoxel-creative-toolkit

Skills, scripts and tools I use with AI assistants (Claude) for voxel art in
[MagicaVoxel](https://ephtracy.github.io/): reading and writing `.vox` files, "assemble from the sky"
animations with synced 16-bit sound effects, smooth camera paths, and a procedural city kit.

## What's inside

| Path | What it does |
| --- | --- |
| `skills/magicavoxel-vox/` | A Claude skill: the `.vox` rules MagicaVoxel really enforces, and how to check results in the app |
| `voxtools/voxlib.py`, `voxwrite.py`, `scenegraph.py` | Read / write `.vox` files with full scene graphs (groups, transforms, layers, animation, flipbooks) |
| `voxtools/fall.py` | Make any scene fall from the sky and assemble itself, in small cubes or floor by floor |
| `voxtools/landing_sfx.py` | Synthesised SNES-style gravel sounds, one per landing piece, lighter the higher it lands |
| `voxtools/smooth_camera.py` | Turn a few camera keyframes into a smooth per-frame path (MagicaVoxel console commands, CSV or JSON) |
| `voxtools/inspect_vox.py` | Print a file's object tree; compute its world-space voxels |
| `voxtools/isorender.py` | Quick isometric PNG previews of objects, without opening MagicaVoxel |
| `voxtools/city/add_assets.py` | 15 buildings + 16 terrain tiles, as a standalone `.vox` or added into your own scene |
| `voxtools/city/city_generator.py` | Generate a whole zoned city (roads, traffic lights, cars, smoke) from a library of tile models |
| `tests/test_fall.py` | Checks that a fall animation lands voxel-for-voxel on the original |

## Setup

Python 3.9+.

```
pip install -r requirements.txt
```

Every script writes a **new** file and never modifies its input. Run any of them with `--help` for all options.

## Assemble-from-the-sky animation

```
cd voxtools
python fall.py scene.vox scene_fall.vox                                   # everything, 3-voxel cubes, bottom-up
python fall.py scene.vox scene_fall.vox --objects tower bridge            # only some objects
python fall.py city.vox city_fall.vox --pieces floors --order wave --centre 48_city_hall
```

Each object is cut into pieces (cubes, or whole-width floor slices). Every piece becomes its own animated
object that starts 160–320 voxels up and drops into place with a gravity ease-in. Landing times are
randomised so pieces on the same level don't land in lock-step.

- `--order height` (default): everything lands bottom-up across the whole scene.
- `--order wave`: objects land in a wave spreading out from `--centre` (an object name or `x,y`), and each
  object builds up level by level (`--stack` frames apart).
- Tune with `--size`, `--drop`, `--drop-jitter`, `--fall`, `--duration`, `--jitter`, `--start` and `--seed`.
- Objects that are already animated are left alone. Flipbooks (e.g. blinking lights) keep animating and
  fall as one piece.
- MagicaVoxel's timeline defaults to 0–30 frames: extend it to the "last landing frame" the script prints.
- Cubes make a lot of pieces. Use `--pieces floors` or a larger `--size` for very large scenes.

### Sound effects for it

```
python landing_sfx.py scene_fall.vox sfx/ --fps 30
```

Writes one WAV for the whole animation (starting at frame 0), eight single "crunch" one-shots, and a
per-frame landing count. Sounds are synthesised (filtered noise, 32 kHz crush, short echo), so there are no
samples to license.

## Smooth camera paths

```
python smooth_camera.py ../examples/camera_keys.json path.txt --format console --with-time
```

Keyframes go in (frame, x, y, z, zoom, pitch, yaw, roll; see `examples/camera_keys.json`). Out comes one
value per frame on a monotone cubic spline. The path hits every keyframe exactly, speed changes smoothly
through them with no stop-and-go jitter, and zoom moves on a log scale so pull-backs feel even.

- `console`: one MagicaVoxel console line per frame (`cam rx … | cam ry … | … | set a_time N`).
- `csv`: a table of values.
- `segments`: JSON one-frame segments for camera-driver scripts.

## City kit

```
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
entries in the palette to change all terrain materials at once, for example making the water glass. Water
inside the marina, dam, zoo and parks uses the same indices. With `--into`, the tool checks those indices
are free in your scene. If your file has a custom palette order, it also gives the terrain colours their
own two palette rows.

**City generator:**

```
python city_generator.py library.vox city.vox --seed 7 --blocks 25
```

Needs a library `.vox` whose objects follow a naming scheme: `16_res_*`, `32_com_*`, `64_ind_*`,
`16_road`, `48_city_hall` and so on (see `--help`). With 25 blocks per side, the city fills
MagicaVoxel's whole 2048³ scene.

## The Claude skill

`skills/magicavoxel-vox/SKILL.md` is a skill for Claude. It covers the `.vox` rules that aren't in the
official spec but that MagicaVoxel enforces. The most important is node ordering: break it and parts of
your scene silently vanish. It also covers how to verify results in the app with computer use. Add the
folder as a custom skill in Claude, and keep `voxtools/` alongside so the skill can use the scripts.
`skills/magicavoxel-vox/references/` holds the official `.vox` format spec from
[ephtracy/voxel-model](https://github.com/ephtracy/voxel-model) (MIT, licence included). The skill
summarises it and lists where real files differ from it.

## Notes

- Tested with MagicaVoxel 0.99.7.
- MIT licensed (see `LICENSE`). The building designs, palette and props are included under the same licence.
- The `.vox` format is documented at
  [ephtracy/voxel-model](https://github.com/ephtracy/voxel-model). This repo is not affiliated with
  MagicaVoxel.
