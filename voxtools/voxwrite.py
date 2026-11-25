"""Write MagicaVoxel .vox files the way MagicaVoxel itself saves them:
all SIZE/XYZI first, then scene nodes with ids 0..n-1 in depth-first chunk order,
then LAYR / RGBA / IMAP / MATL / rOBJ / rCAM / NOTE.

Those trailing chunks (palette, materials, layers, render settings) are copied from a
"donor" .vox (usually the file you started from). Without a donor, pass `palette`
(a list of up to 255 (r, g, b) tuples, palette[i-1] = colour index i) and MagicaVoxel's
defaults are used for everything else.

IMPORTANT: MagicaVoxel silently drops subtrees whose node ids are not 0..n-1 in
depth-first chunk order, so save() always renumbers (and drops unreachable nodes)."""
import struct
from voxlib import read_chunks, parse_node

def _s(s):
    b = s.encode('latin1'); return struct.pack('<i', len(b)) + b

def _d(d):
    out = struct.pack('<i', len(d))
    for k, v in d.items(): out += _s(k) + _s(str(v))
    return out

def chunk(cid, content):
    return cid.encode('latin1') + struct.pack('<ii', len(content), 0) + content

def size_xyzi(size, voxels):
    sx, sy, sz = size
    c = chunk('SIZE', struct.pack('<iii', sx, sy, sz))
    body = struct.pack('<i', len(voxels)) + b''.join(struct.pack('<BBBB', *v) for v in voxels)
    return c + chunk('XYZI', body)

def rgba_bytes(palette):
    """256 RGBA entries; palette[i-1] is colour index i. Missing entries are filled with grey."""
    out = bytearray()
    for i in range(256):
        r, g, b = (tuple(palette[i])[:3] if i < len(palette) and palette[i] else (128, 128, 128))
        out += bytes((r, g, b, 255))
    return bytes(out)

class Scene:
    def __init__(self):
        self.models = []       # (size, voxels)
        self.nodes = []        # dicts; index == id
    def add_model(self, size, voxels):
        self.models.append((size, voxels)); return len(self.models) - 1
    def _new(self, nd):
        nd['id'] = len(self.nodes); self.nodes.append(nd); return nd['id']
    def trn(self, child=None, layer=0, frames=None, attrs=None):
        return self._new({'type': 'nTRN', 'attrs': attrs or {}, 'child': child, 'layer': layer,
                          'frames': frames or [{}]})
    def grp(self, children=None, attrs=None):
        return self._new({'type': 'nGRP', 'attrs': attrs or {}, 'children': children or []})
    def shp(self, models, attrs=None):
        return self._new({'type': 'nSHP', 'attrs': attrs or {}, 'models': models})

    def node_bytes(self, nd):
        b = struct.pack('<i', nd['id']) + _d(nd['attrs'])
        if nd['type'] == 'nTRN':
            b += struct.pack('<iiii', nd['child'], -1, nd['layer'], len(nd['frames']))
            for f in nd['frames']: b += _d(f)
        elif nd['type'] == 'nGRP':
            b += struct.pack('<i', len(nd['children'])) + b''.join(struct.pack('<i', c) for c in nd['children'])
        else:
            b += struct.pack('<i', len(nd['models']))
            for mid, md in nd['models']: b += struct.pack('<i', mid) + _d(md)
        return chunk(nd['type'], b)

    def build_tree_ids(self):
        """Renumber nodes depth-first from root 0 (MagicaVoxel's own order)."""
        order = []
        def visit(i):
            order.append(i); nd = self.nodes[i]
            if nd['type'] == 'nTRN': visit(nd['child'])
            elif nd['type'] == 'nGRP':
                for c in nd['children']: visit(c)
        visit(0)
        remap = {old: new for new, old in enumerate(order)}
        new = []
        for old in order:
            nd = dict(self.nodes[old]); nd['id'] = remap[old]
            if nd['type'] == 'nTRN': nd['child'] = remap[nd['child']]
            if nd['type'] == 'nGRP': nd['children'] = [remap[c] for c in nd['children']]
            new.append(nd)
        self.nodes = new

    def save(self, path, donor=None, node_order=None, renumber=True, palette=None, replace=None):
        """donor: .vox to copy palette/materials/layers/render settings from.
        palette: used when there is no donor. replace: {chunk_id: new_content} overrides donor chunks."""
        if renumber: self.build_tree_ids()
        body = b''.join(size_xyzi(s, v) for s, v in self.models)
        nodes = self.nodes if node_order is None else [self.nodes[i] for i in node_order]
        body += b''.join(self.node_bytes(nd) for nd in nodes)
        replace = replace or {}
        if donor:
            _, dch = read_chunks(donor)
            for c in dch:
                if c['id'] in ('LAYR', 'RGBA', 'IMAP', 'MATL', 'rOBJ', 'rCAM', 'NOTE'):
                    body += chunk(c['id'], replace.get(c['id'], c['content']))
        elif palette:
            body += chunk('RGBA', rgba_bytes(palette))
        data = b'VOX ' + struct.pack('<i', 200) + b'MAIN' + struct.pack('<ii', 0, len(body)) + body
        open(path, 'wb').write(data)
        return len(data)

def load_scene(path):
    """Load an existing file into a Scene (models + nodes), keeping ids."""
    _, ch = read_chunks(path)
    sc = Scene(); size = None
    for c in ch:
        if c['id'] == 'SIZE': size = struct.unpack('<iii', c['content'])
        elif c['id'] == 'XYZI':
            n = struct.unpack_from('<i', c['content'], 0)[0]
            vox = [tuple(c['content'][4+4*i:8+4*i]) for i in range(n)]
            sc.models.append((size, vox))
        elif c['id'] in ('nTRN', 'nGRP', 'nSHP'):
            nd = parse_node(c); nd.pop('reserved', None)
            sc.nodes.append(nd)
    sc.nodes.sort(key=lambda n: n['id'])
    assert [n['id'] for n in sc.nodes] == list(range(len(sc.nodes)))
    return sc
