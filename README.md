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
| `voxtools/wave.py` | Generate a looping ocean wave that curls over and crashes (barrel, foam, spray) as a flipbook |
| `voxtools/texture_sand.py` | Texture flat sand: colour patches, grain, wind ripples, pebbles and shells |
| `voxtools/palm.py` | Generate a palm tree (ringed leaning trunk, drooping fronds, coconuts) and plant it on a scene's ground |
| `voxtools/beach_props.py` | Add beach props to a scene: surfboard, scuttling crab, circling seagulls, distant island, footprint trail, whitewash run-up |
| `voxtools/scene_sfx.py` | Synthesised 16-bit beach soundtrack (ocean, crashes, foam, crab clacks and jumps, gulls) timed to your render, loop-safe |
| `voxtools/inspect_vox.py` | Print a file's object tree; compute its world-space voxels |
| `voxtools/isorender.py` | Quick isometric PNG previews of objects, without opening MagicaVoxel |
| `voxtools/vox_preview.py` | Quick perspective preview from a camera position at any frame, to check composition |
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

## Ocean waves

```
python wave.py wave.vox                                   # 24-frame loop, 256 long, 150 high
python wave.py wave.vox --frames 32 --length 768 --height 170
python wave.py wave.vox --peel                            # the break travels along the wave instead
python wave.py wave.vox --length 512 --segment 24         # 512 long, built from 24-long blocks
python wave.py wave.vox --length 512 --segment 24 --width 24 --zsize 48 --height 26 --thickness 2 --margin 3
                                                          # a small wave whose whole break fits 24x24x48 blocks
python wave.py set.vox --set 3 --length 512 --segment 24 --width 24 --zsize 48 --height 26 --thickness 2 \
    --margin 3 --frames 30 --step 1 --sea-width 144 --travel 96 --beach 24 --ocean 256
                                                          # three waves rolling in and crashing on a beach,
                                                          # with 256 of open ocean behind them
python wave.py scene_plus_wave.vox --into scene.vox       # add a wave to a copy of a scene
```

Builds a sheet of water from a cross-section and runs it through a real plunging break over the loop:
the swell rises, the crest curls, the lip shoots out and lands in front of the face (the barrel), the
impact explodes into foam and spray, and the next swell builds. The loop is seamless. If the break is wider than `--width`, it is squeezed horizontally to fit (same amount on every frame).
With `--set N`, N waves travel toward a sand beach, evenly staggered over the loop: each rises out of the
flat sea at the back, breaks as it comes in and crashes near the shore while the next one builds behind it.
`--ocean` adds open water behind the waves with gentle swells rolling toward the shore (`--ocean-swell`,
`--swell-length`); they taper off where they meet the breaking zone and loop with the waves.
The sea is tiled into blocks of `--width` x `--segment` x `--zsize`. Spray is scattered in 3D as clumps of 1-4 voxel cubes. As the lip throws, it splits into irregular fingers that
reach out and curl down by different amounts (`--fingers`, `--finger-width`), so the leading edge is scalloped. Colours (`--water`, `--shade`, `--foam`), thickness, spray, frame count
and timing (`--step`) are all options. Lengths over 256 are split into aligned 256-long segments, since
that's MagicaVoxel's model size limit.

## Sand texture

```
python texture_sand.py beach.vox beach_textured.vox             # texture every voxel of colour index 4
python texture_sand.py beach.vox out.vox --sand 12 --ripple 9 --ripple-angle 30 --no-pebbles
```

Recolours the chosen sand colour with patchy light/dark tones and fine grain, raises wavy wind ripples
in patches on the surface, and scatters a few pebbles and shell bits. Everything is based on world
position, so the texture lines up across objects and stays identical in every animation frame. New sand
shades go into free palette slots; the original file is not modified.

## Palm trees

```
python palm.py palm.vox                                         # standalone tree
python palm.py beach_palm.vox --into beach.vox --at=-300,80     # plant on the ground at world x,y
python palm.py palm.vox --height 60 --lean 22 --lean-dir 90 --fronds 10 --seed 9
python palm.py big_palm.vox --scale 2 --lean 26 --lean-dir 90   # twice the size, leaning to the side
python palm.py palm.vox --sway 1.5 --frames 30 --flip-y         # mirrored, swaying gently in a 30-frame loop
python palm.py beach2.vox --into beach.vox --replace --at=-330,40 --sway 1.5   # swap out an existing palm_tree
```

Builds a curved, ringed trunk that leans and curves back upright, a crown with coconuts, and fronds that
arch out and droop with leaflets on both sides. With `--into`, it finds the ground height at that spot and
plants the tree there in a copy of the scene; colours go into free palette slots. Change `--seed` for a
different tree. `--sway` animates it as a looping flipbook: the trunk rocks with the wind and every frond
bobs on its own timing (`--wind-dir`, `--frames`, `--step`).

## Beach props

```
python beach_props.py beach.vox beach_props.vox --board=-545,-36 --crab=-520,-20,6 --gulls=20,0,120 \
    --island=460,-20 --footprints=-645,-16:-212,-30 --whitewash=-202,-168 --water-index 1 --foam-index 3
```

Each option adds one prop, standing on the ground under it (coordinates are world x,y; negative values need
`--opt=` with an equals sign):

- `--board`: an original surfboard (rails, stringer, coloured nose, fin), tail buried in the sand and leaning.
- `--crab=X,Y0,Y1`: a crab that scuttles sideways from Y0 to Y1, pauses, and scuttles back, legs and claws
  moving only while it walks.
- `--gulls=X,Y,Z`: a small flock that flaps and circles, one lap per loop (`--gull-count`).
- `--island`: a hazy dusk-coloured island silhouette with tiny palms. Put it just past the far edge of the
  ocean; it reaches below the waterline so it never looks like it floats.
- `--footprints=X0,Y0:X1,Y1`: a winding trail of alternating prints pressed two voxels into the sand.
- `--whitewash=XA,XB`: foam running up the shore and drawing back, three surges per loop (one per wave of a 3-wave set),
  using your own water and foam palette indices.

Ground includes static objects and the parts of flipbooks that don't move (e.g. sand inside wave blocks).
Animated props loop over `--frames` (default 30) to match `wave.py` and `palm.py --sway`.

## Previews

```
python vox_preview.py scene.vox look.png --eye=-675,-15,40 --yaw 0 --fov 45 --frame 15
```

A rough perspective splat of the whole scene (flipbooks and animated transforms at `--frame`). Fast enough to
check placement before opening MagicaVoxel. `--yaw` is the look direction around z (0 = +x).

## Soundtrack for a beach render

```
python scene_sfx.py beach.wav --duration 3 --fps 30 --crash 0.62s,1.62s,2.62s \
    --clack 27,63 --clack-open 24,30,60 --jump 12,84 --land 18,90 \
    --gull 0.12s --gull-laugh 1.18s --gull-far 2.38s --rustle 0.9s,2.3s --video render.mp4
```

Synthesised SNES-style sound (no samples) for a looping clip: a calm ocean bed that swells before each
break, soft wave crashes with foam hiss, crab claw clacks (open ticks and snaps shut), 16-bit jump "boings"
and sandy landings, nasal gull cries pushed far away with echo, and palm rustles. Times are frames at
`--fps` or seconds with an `s` suffix; sounds that run past the end wrap to the start, so the loop is
seamless. `--ocean`, `--gulls` and `--crab` scale each part. With `--video`, it also writes
`<video>_sfx.mp4` with the picture copied untouched (needs ffmpeg).

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
