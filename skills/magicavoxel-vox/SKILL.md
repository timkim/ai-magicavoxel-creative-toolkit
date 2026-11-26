---
name: magicavoxel-vox
description: Use when reading, generating, patching or animating MagicaVoxel .vox files, or checking them in MagicaVoxel via computer use.
---

# MagicaVoxel .vox: format rules, tools, and in-app verification

The Python tools this skill refers to live in the `voxtools/` folder of this repository
(`voxlib.py` reader, `voxwrite.py` writer, `scenegraph.py`, `fall.py`, `landing_sfx.py`,
`smooth_camera.py`, `inspect_vox.py`, `isorender.py`, `vox_preview.py`, `wave.py`, `texture_sand.py`,
`palm.py`, `beach_props.py`, `scene_sfx.py`, and `city/`). Copy them into the working
directory and import them rather than re-deriving the format.

Never overwrite the user's original files: write new files with a new name, and keep experiments
in a separate test folder.

## Rules MagicaVoxel actually enforces (verified in MagicaVoxel 0.99.7)

1. **Node chunk order must be depth-first from root 0, with ids 0..n-1 matching chunk order.** The same
   content in a different chunk order loads with the subtree silently missing: no error, and the file
   often opens straight into model-edit mode on the first model. Never patch a `child_id` in place and
   append nodes at the end. Load the whole scene, edit it in memory, and re-serialize (`voxwrite.Scene.save`
   renumbers and drops unreachable nodes).
2. **Chunk layout:** `VOX ` + version 200, then `MAIN` holding all `SIZE`/`XYZI` pairs first, then all
   scene nodes, then `LAYR`, `RGBA`, `IMAP` (if any), `MATL`, `rOBJ`, `rCAM`, `NOTE`. Copy the trailing
   chunks verbatim from the source file ("donor").
3. **No orphan nodes.** Drop anything that isn't reachable from root 0.
4. **Node count is not the limit.** 24,000 one-model shapes (48k nodes) render and animate fine.
5. **Animated nTRN:** node attr `_frm_t` = the pose shown in edit view (use the landed pose), and every
   frame dict has `_f` (frame number) plus `_t` (and optionally `_r`). Don't repeat an `_f` value.
   Static nodes have one frame with no `_f`. Keyframes don't have to start at 0. A transform pointing
   at a group can be animated too.
6. **Flipbook nSHP:** node attr `_loop: 1` to loop (optionally `_frm_id`); each model entry has
   `{'_f': n}`. To loop seamlessly, repeat the first model one step after the last.
7. **Pivot:** a model is centred at `floor(size/2)` per axis. When splitting a model into pieces, give
   each piece `_t = piece_min + piece_size//2 - parent_size//2` (relative to the parent's transform) to
   keep voxels in place. Verify by rebuilding world positions and comparing sets
   (`inspect_vox.world_voxels`).
8. **Interpolation between keys is linear**, so approximate easing with extra keys (e.g. gravity:
   height fractions 1, .75, .4375, 0 at t = 0, .5, .75, 1).
9. **Palette:** index i in XYZI maps to `RGBA[i-1]`. Check the file's palette before picking test
   colours; unused slots are often all one colour. An `IMAP` chunk only changes the *display order* in
   the palette panel (display slot -> index); it does not change which colour a voxel uses.
10. **Rotation byte `_r`:** bits 0-1 = column of the non-zero entry in row 0, bits 2-3 = row 1, bits
    4/5/6 = sign of rows 0/1/2. z rotations: 4 = 0°, 17 = 90°, 52 = 180°, 33 = 270°.
11. **Hidden layers:** `LAYR` chunks carry `_hidden`. Copying another file's `LAYR` can put your new
    nodes on a hidden layer (they vanish in the editor and the render). Check which layer you assign.

## File format reference

The official spec is in `references/` (copied from
[ephtracy/voxel-model](https://github.com/ephtracy/voxel-model), MIT licence):
`MagicaVoxel-file-format-vox.txt` covers the container, models and palette, and
`MagicaVoxel-file-format-vox-extension.txt` covers the scene graph, materials, layers, camera and
palette chunks. Read them for exact byte layouts. Quick summary (all integers little-endian):

- **Container:** `VOX ` + int32 version, then the `MAIN` chunk holding every other chunk. Each chunk
  is a 4-char id, int32 content size N, int32 children size M, then the content and the children.
- **Models:** `SIZE` (int32 x, y, z; z is up) followed by `XYZI` (int32 count, then 1 byte each
  of x, y, z, colour index per voxel). A model's id is its position among the SIZE/XYZI pairs.
- **Palette:** `RGBA` has 256 entries of R, G, B, A bytes; entry k (0-254) is colour index k+1.
- **Building blocks:** STRING = int32 length + bytes (no terminating zero). DICT = int32 count +
  that many STRING key/value pairs. Every value is text: numbers as decimal strings, vectors as
  `"x y z"`.
- **Rotation byte `_r`:** bits 0-1 give the column of the non-zero entry in row 0, bits 2-3 the
  column in row 1 (row 2 takes the remaining column), and bits 4/5/6 are the signs of rows 0/1/2
  (1 = negative).
- **Scene graph:** transform `nTRN` (id, DICT `_name`/`_hidden`, child id, reserved -1, layer id,
  frame count >= 1, one DICT per frame with `_r`/`_t`/`_f`), group `nGRP` (id, DICT, child ids),
  and shape `nSHP` (id, DICT, at least one model id each with a DICT holding `_f`). The root is
  transform 0 -> group 1.
- **Other chunks:**
  - `MATL`: one per palette index (id = index); properties such as `_type` (`_diffuse`,
    `_metal`, `_glass`, `_emit`), `_weight`, `_rough`, `_spec`, `_ior`, `_att`, `_flux`.
  - `LAYR`: id, DICT `_name`/`_hidden`, reserved -1.
  - `rOBJ`: render settings, one DICT each.
  - `rCAM`: id, then DICT `_mode`, `_focus`, `_angle`, `_radius`, `_frustum`, `_fov`.
  - `NOTE`: palette row names.
  - `IMAP`: palette display order.
- **Deprecated:** `PACK` (pre-0.98 animation) and `MATT` (replaced by `MATL`).

**Where real files differ from the spec text (MagicaVoxel 0.99.7):**
- **Version:** files are written with version **200**, not 150.
- **IMAP:** stored as **256 single bytes** (display slot -> palette index), not 256 int32.
- **Undocumented keys:** `nTRN` `_frm_t` (pose shown in the editor for animated nodes), and
  `nSHP` `_loop` / `_frm_id` (flipbook looping and the model shown in the editor). The root
  transform uses layer **-1**.
- **MATL:** a missing `_type` means diffuse. Files also carry extra undocumented keys (e.g.
  `_ri`, `_g`), so copy `MATL` chunks byte for byte rather than rebuilding them.
- **Count of other chunks:** MagicaVoxel writes 16 `LAYR`, 256 `MATL`, several `rOBJ` and several
  `rCAM` chunks. Copy them all from the source file.
- **No default palette needed:** files always include `RGBA`, so the spec's default palette only
  matters for very old files.
- **Spec omits node order:** it doesn't mention the depth-first node-order rule (rule 1 above), so
  follow rule 1 regardless.

## Sanity check for any writer change

`load_scene(x).save(y, x)` on an untouched MagicaVoxel file must be byte-identical.

## Workflow

1. Parse the source `.vox` and print the tree (`python inspect_vox.py file.vox`): names, sizes, layers,
   keyframe counts, flipbooks.
2. Edit the scene in memory. To replace a named object with animated pieces: split its model into
   pieces, add a new `nGRP` of `nTRN`->`nSHP` per piece, point the object's `nTRN.child` at the group,
   and reuse the original model slot for the first piece (only if nothing else uses it).
3. Save with renumbering. Check that ids are sequential, that depth-first order equals chunk order, and
   that landed voxel positions are identical to the original (`tests/test_fall.py` does this).
4. Check composition before opening MagicaVoxel: `python vox_preview.py scene.vox look.png --eye=X,Y,Z
   --yaw D --frame N` (MagicaVoxel's camera is a 45° vertical FOV). Looking along +x, screen-right is -y.
5. Verify in MagicaVoxel (below).

### Adding things to an existing scene

- New colours go into **unused palette slots** (scan every model's indices first); never recolour an
  existing slot. `palm.py`, `texture_sand.py` and `beach_props.py` all do this.
- **Ground height** = highest voxel per column across static objects, plus the voxels of flipbooks that
  stay put across the loop (sand inside animated wave blocks). Skip props, birds and the thing you're
  replacing.
- Match loops: animated props use the same frame count as the waves/palms (30), with a repeat of the
  first model at the end of every flipbook so the loop is seamless.
- Negative coordinates on the command line need `--opt=-300,80` (with `=`), or argparse reads them as
  options.
- Big scenes: keep separate models per block (e.g. 24-wide flipbook strips) instead of one huge model;
  MagicaVoxel models are capped at 256 per axis.

### Sound for a render (`scene_sfx.py`)

- Time sounds to **the render the user made**, not to your animation file: they may have re-animated
  things or stretched the clip (a 3x stretch shows each frame 3 times). Measure on-screen motion
  per frame (frame differences in a region, crops of key frames), and take the user's frame numbers as
  final when they give them.
- Put clacks on the frames where claws *close*, landings where things touch down, and keep separate
  events from overlapping (e.g. gull cries away from crab clacks).
- Alternating two pitches quickly reads as a distracting trill; use one pitch for repeated ticks.
  Gulls need a buzzy, nasal, raspy cry (jump up then a long slide down, plus short "kyow" laugh notes),
  not a smooth glide, and sound distant when quiet, low-passed and mostly echo.
- Don't peak-normalise the final mix when the user asks to lower one part (normalising turns it straight
  back up); keep a fixed reference level and soft-limit only transients. Mix circularly so tails wrap
  and the loop is seamless.

### Cameras: file vs. panel vs. console (verified in MagicaVoxel 0.99.7)

The ten `rCAM` chunks (ids 0-9) are the ten camera slots in the Render tab's Camera panel (bottom right).
Only slots someone stored hold real values; unused slots are `pers` with focus, angle and radius all 0.
Slots only reach the file when the user saves (Ctrl+S), so the live session can differ from the file:
read the file again after they save, or ask for a screenshot of the panel.

| Camera panel / console command | Stored in `rCAM` |
|---|---|
| X, Y, Z (`cam x`, `cam y`, `cam z`) | `_focus` x y z |
| Pitch (`cam rx`) | `_angle` first value (same sign) |
| Yaw (`cam ry`) | `_angle` second value **with the sign flipped** (file `8.5` = panel `-8.5`) |
| Roll (`cam rz`) | `_angle` third value |
| Zoom (`cam zoom`), orthographic | **2 x `_frustum`** (file `104.578` = panel `209.2`); `_radius` is just a fixed far distance |
| Fov | `_fov` |
| Pers / Orth | `_mode` |

- Console yaw wraps into -180..180 (`cam ry 270` shows -90), so a 360 spin can interpolate yaw from
  its start to start +/- 360.
- In the panel, a digit 0-9 only *selects* a slot; **L** loads the selected slot into the view and **S**
  stores the current view into it.
- Camera files for MagicaVoxel-Animation-Script are in panel units (zoom = 2 x frustum, yaw negated).
  Most robust: have the user load the start slot with **L**, and send only the properties that change
  (e.g. just yaw and zoom), so everything else stays exactly as the slot set it.
- Not yet verified: perspective-mode zoom (probably `_radius`) and the roll sign.
- If MagicaVoxel is already open, `open_application` starts a second, empty instance. Screenshot first
  and use the existing window; close an accidental empty one without saving.

## Verifying in MagicaVoxel with computer use

- **Open a file:** Ctrl+O. If you get "Model unsaved, save changes to file?", click **No** (never
  save over test or original files). In the dialog, click the File name field, Ctrl+A, type the full
  path, press Enter. Large files (~6 MB) take several seconds to load.
- **Model vs Render:** the tabs at the top-left. Tab toggles model-edit and scene view in Model mode. A
  file that opens directly into edit mode on one model, with the rest missing, means the scene graph
  was rejected (usually rule 1).
- **Timeline:** the small ▼ at the top-left of the viewport toggles it. The default range is 0–30, so
  extend the end marker for longer animations. `,` / `.` step one frame.
- At frame 0 with nothing played, edit view shows the `_frm_t` pose.
- **Big scenes render partially** unless Sample → Geometry → **Sparse** is on (an app setting, not
  saved in the .vox).
- **Console:** F1 toggles it (Escape does not close it). Useful commands: `cam rx/ry/rz/zoom/x/y/z <v>`
  (render camera), `set a_time <frame>`, `set pt_auto 0|1` (pause/resume progressive render), `snap
  scene` (save a render; opens a save dialog). Chain commands with ` | `.
- Use high-contrast colours and pieces of at least 3 voxels in test files; UI text and 1-voxel objects
  are tiny on high-DPI screens, so zoom into regions to read.
- Release the computer-use lock when done.
