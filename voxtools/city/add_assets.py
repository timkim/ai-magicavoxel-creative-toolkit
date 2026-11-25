"""Generate the city buildings and terrain tiles as MagicaVoxel objects.

  python add_assets.py --list                                  # what's available
  python add_assets.py assets.vox                              # standalone file with everything
  python add_assets.py assets.vox --only 32_church 64_stadium  # just some
  python add_assets.py my_city_plus.vox --into my_city.vox     # append to an existing scene
  python add_assets.py --preview sheet.png                     # quick isometric preview sheet

Palette
  * Building colours live in indices 97-112, terrain colours in 161-176. Terrain tiles use ONLY
    161-176, so you can select those palette entries and change the material of all terrain at once
    (e.g. make the water glass). Water/rock inside buildings (marina, dam, zoo, parks) uses the
    same terrain indices, so it follows along.
  * With --into, the existing objects are copied unchanged. Those palette indices must be unused by
    the scene (the script checks). If the scene has a custom palette order (IMAP chunk), the terrain
    colours are moved into a clean two-row block of their own and the building colours into another.
  * Terrain tiles go on their own layer, named "terrain".
"""
import argparse, os, struct, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..'))
from voxwrite import Scene, load_scene, chunk, rgba_bytes
from voxlib import read_chunks, _dict
from vkit import to_vox, PALETTE
from buildings_civic import BUILDINGS, NEW_COLOURS
from buildings_more import BUILDINGS2, ANIMATED2
from terrain import TILES, TERRAIN_COLOURS

TERRAIN_IDX = sorted(TERRAIN_COLOURS)
BUILD_IDX = sorted(NEW_COLOURS)
FLIP_STEP = 6     # wind turbine: animation frames per 30-degree blade step

def catalog():
    items = {}
    for n, fn in {**BUILDINGS, **BUILDINGS2}.items(): items[n] = ('building', fn)
    for n, fn in ANIMATED2.items(): items[n] = ('animated', fn)
    for n, fn in TILES.items(): items[n] = ('terrain', fn)
    return items

def _dict_bytes(d):
    out = struct.pack('<i', len(d))
    for k, v in d.items():
        for s in (k, v):
            b = s.encode('latin1'); out += struct.pack('<i', len(b)) + b
    return out

def place_all(sc, parent_children, names, x0, y0, terrain_layer, gap=16):
    """Lay buildings out in columns of ~4 and terrain tiles in a grid to their right."""
    cat = catalog(); x, y, col_w, count = x0, y0, 0, 0
    def add_obj(name, models, sx, sy, sz, px, py, layer, flip=False):
        if flip:
            keys = [(m, {'_f': str(i * FLIP_STEP)}) for i, m in enumerate(models)] + [(models[0], {'_f': str(len(models) * FLIP_STEP)})]
            shp = sc.shp(keys, attrs={'_loop': '1'})
        else:
            shp = sc.shp([(models[0], {})])
        parent_children.append(sc.trn(shp, layer=layer, frames=[{'_t': f'{px + sx // 2} {py + sy // 2} {sz // 2}'}],
                                      attrs={'_name': name}))
    buildings = [n for n in names if cat[n][0] != 'terrain']; tiles = [n for n in names if cat[n][0] == 'terrain']
    for name in buildings:
        kind, fn = cat[name]
        grids = fn() if kind == 'animated' else [fn()]
        sx, sy, sz = grids[0].shape
        mids = [sc.add_model((sx, sy, sz), to_vox(G)) for G in grids]
        add_obj(name, mids, sx, sy, sz, x, y, 0, flip=kind == 'animated')
        col_w = max(col_w, sx); y += sy + gap; count += 1
        if count % 4 == 0: x += col_w + gap; y = y0; col_w = 0
    if buildings and count % 4: x += col_w + gap
    for k, name in enumerate(tiles):
        G = cat[name][1](); sx, sy, sz = G.shape
        add_obj(name, [sc.add_model((sx, sy, sz), to_vox(G))], sx, sy, sz,
                x + (k % 4) * (16 + 8), y0 + (k // 4) * (16 + 8), terrain_layer)

def scene_extent(sc):
    from scenegraph import world_transforms, node_world
    wt = world_transforms(sc); xs = []
    for i, nd in enumerate(sc.nodes):
        if nd['type'] == 'nTRN' and sc.nodes[nd['child']]['type'] == 'nSHP':
            R, t = node_world(sc, wt, i); size = np.array(sc.models[sc.nodes[nd['child']]['models'][0][0]][0])
            ext = np.abs(R) @ size
            xs.append((t[0] + ext[0] // 2 + 1, t[1] - ext[1] // 2))
    return (max(x for x, _ in xs), min(y for _, y in xs)) if xs else (0, 0)

def used_indices(sc):
    return {v[3] for _, vox in sc.models for v in vox}

def write_standalone(out, names):
    sc = Scene(); sc.trn(layer=-1); g = sc.grp(); sc.nodes[0]['child'] = g
    place_all(sc, sc.nodes[g]['children'], names, -200, -200, terrain_layer=3)
    sc.build_tree_ids()
    from voxwrite import size_xyzi
    body = b''.join(size_xyzi(s, v) for s, v in sc.models) + b''.join(sc.node_bytes(nd) for nd in sc.nodes)
    for lid in range(16):
        nm = {0: 'buildings', 3: 'terrain'}.get(lid)
        body += chunk('LAYR', struct.pack('<i', lid) + _dict_bytes({'_name': nm} if nm else {}) + struct.pack('<i', -1))
    body += chunk('RGBA', rgba_bytes(PALETTE))
    open(out, 'wb').write(b'VOX ' + struct.pack('<i', 200) + b'MAIN' + struct.pack('<ii', 0, len(body)) + body)

def pick_blocks(order, free_idx, n_blocks):
    """Choose 8-aligned, 16-slot display blocks whose slots all show free palette indices.
    Returns blocks sorted by distance from the slots showing used colours (closest first)."""
    used_slots = [s for s, idx in enumerate(order) if idx not in free_idx and idx != 0]
    cands = []
    for start in range(0, 256 - 16 + 1, 8):
        slots = range(start, start + 16)
        if all(order[s] in free_idx for s in slots):
            d = min((abs(s - u) for s in slots for u in used_slots), default=0)
            cands.append((d, start))
    if len(cands) < n_blocks: return None
    cands.sort(); chosen = []
    for d, s in cands:   # non-overlapping
        if all(abs(s - c) >= 16 for c in chosen): chosen.append(s)
    return chosen

def write_into(src, out, names):
    sc = load_scene(src)
    clash = used_indices(sc) & set(TERRAIN_IDX + BUILD_IDX)
    if clash:
        raise SystemExit(f'the scene already uses palette indices {sorted(clash)}; those are reserved for the new '
                         'assets. Move those colours first (or generate a standalone file and merge by hand).')
    root = sc.nodes[sc.nodes[0]['child']]
    layers_used = {nd['layer'] for nd in sc.nodes if nd['type'] == 'nTRN'}
    terrain_layer = next(l for l in range(16) if l not in layers_used)
    xmax, ymin = scene_extent(sc)
    place_all(sc, root['children'], names, int(xmax) + 32, int(ymin), terrain_layer)

    replace = {}; ch = read_chunks(src)[1]
    rgba = [c for c in ch if c['id'] == 'RGBA']
    pal = bytearray(rgba[0]['content'] if rgba else rgba_bytes(PALETTE))
    for i, rgb in {**NEW_COLOURS, **TERRAIN_COLOURS}.items(): pal[4 * (i - 1):4 * i] = bytes(rgb) + b'\xff'
    replace['RGBA'] = bytes(pal)
    imap = [c for c in ch if c['id'] == 'IMAP']
    if imap:
        order = list(imap[0]['content']); free = set(range(1, 256)) - used_indices(sc) | set(TERRAIN_IDX + BUILD_IDX)
        blocks = pick_blocks(order, free, 2)
        if blocks:
            for idxs, start in ((BUILD_IDX, blocks[0]), (TERRAIN_IDX, blocks[-1])):   # buildings near, terrain far
                for k, idx in enumerate(idxs):
                    cur = order.index(idx); order[cur], order[start + k] = order[start + k], order[cur]
            replace['IMAP'] = bytes(order)
    layr = {}
    for c in ch:
        if c['id'] == 'LAYR':
            lid = struct.unpack_from('<i', c['content'], 0)[0]
            if lid == terrain_layer:
                d, o = _dict(c['content'], 4); d['_name'] = 'terrain'
                layr[c['offset']] = struct.pack('<i', lid) + _dict_bytes(d) + c['content'][o:]
    # write: like Scene.save, with per-chunk replacements
    sc.build_tree_ids()
    from voxwrite import size_xyzi
    body = b''.join(size_xyzi(s, v) for s, v in sc.models) + b''.join(sc.node_bytes(nd) for nd in sc.nodes)
    for c in ch:
        if c['id'] in ('LAYR', 'RGBA', 'IMAP', 'MATL', 'rOBJ', 'rCAM', 'NOTE'):
            body += chunk(c['id'], layr.get(c['offset'], replace.get(c['id'], c['content'])))
    if not rgba: body += chunk('RGBA', replace['RGBA'])
    open(out, 'wb').write(b'VOX ' + struct.pack('<i', 200) + b'MAIN' + struct.pack('<ii', 0, len(body)) + body)
    return terrain_layer

def preview(path, names):
    from isorender import render
    from PIL import Image
    cat = catalog(); ims = []
    for n in names:
        kind, fn = cat[n]; G = fn()[0] if kind == 'animated' else fn()
        ims.append(render(to_vox(G), [tuple(c) + (255,) for c in PALETTE], scale=3))
    per = 6; rows = [ims[i:i + per] for i in range(0, len(ims), per)]
    W = max(sum(i.width for i in r) for r in rows); H = sum(max(i.height for i in r) for r in rows)
    sheet = Image.new('RGB', (W, H), (40, 40, 44)); y = 0
    for r in rows:
        x = 0; h = max(i.height for i in r)
        for i in r: sheet.paste(i, (x, y + h - i.height)); x += i.width
        y += h
    sheet.save(path)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out', nargs='?')
    ap.add_argument('--into', help='existing .vox to append to (it is not modified; OUT is a new file)')
    ap.add_argument('--only', nargs='+', help='asset names (default: all)')
    ap.add_argument('--list', action='store_true')
    ap.add_argument('--preview', help='write an isometric preview sheet PNG')
    a = ap.parse_args()
    cat = catalog()
    if a.list:
        for n, (kind, _) in cat.items(): print(f'{n:28s} {kind}')
        return
    names = a.only or list(cat)
    bad = [n for n in names if n not in cat]
    if bad: raise SystemExit(f'unknown asset(s): {bad} (see --list)')
    if a.preview: preview(a.preview, names); print('wrote', a.preview)
    if not a.out:
        if not a.preview: ap.error('give an output .vox (or --list / --preview)')
        return
    if a.into:
        layer = write_into(a.into, a.out, names); print(f'wrote {a.out}: {len(names)} assets added (terrain on layer {layer})')
    else:
        write_standalone(a.out, names); print(f'wrote {a.out}: {len(names)} assets')

if __name__ == '__main__':
    main()
