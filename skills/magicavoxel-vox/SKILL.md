---
name: magicavoxel-vox
description: Use when reading, generating, patching or animating MagicaVoxel .vox files, or checking them in MagicaVoxel via computer use.
---

# MagicaVoxel .vox: format rules, tools, and in-app verification

The Python tools this skill refers to live in the `voxtools/` folder of this repository
(`voxlib.py` reader, `voxwrite.py` writer, `scenegraph.py`, `fall.py`, `landing_sfx.py`,
`smooth_camera.py`, `inspect_vox.py`, `isorender.py`, and `city/`). Copy them into the working
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
4. Verify in MagicaVoxel (below).

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
