"""Minimal MagicaVoxel .vox reader/writer (scene graph aware)."""
import struct

def _dict(b, o):
    n = struct.unpack_from('<i', b, o)[0]; o += 4
    d = {}
    for _ in range(n):
        kl = struct.unpack_from('<i', b, o)[0]; o += 4
        k = b[o:o+kl].decode('latin1'); o += kl
        vl = struct.unpack_from('<i', b, o)[0]; o += 4
        v = b[o:o+vl].decode('latin1'); o += vl
        d[k] = v
    return d, o

def read_chunks(path):
    b = open(path, 'rb').read()
    assert b[:4] == b'VOX ', 'not a vox file'
    ver = struct.unpack_from('<i', b, 4)[0]
    assert b[8:12] == b'MAIN'
    n, m = struct.unpack_from('<ii', b, 12)
    o = 20 + n
    end = o + m
    chunks = []
    while o < end:
        cid = b[o:o+4].decode('latin1')
        n, m = struct.unpack_from('<ii', b, o + 4)
        content = b[o+12:o+12+n]
        chunks.append({'id': cid, 'offset': o, 'content': content, 'children_len': m})
        o += 12 + n + m
    return ver, chunks

def parse_node(c):
    b = c['content']; cid = c['id']
    nid = struct.unpack_from('<i', b, 0)[0]
    attrs, o = _dict(b, 4)
    node = {'type': cid, 'id': nid, 'attrs': attrs}
    if cid == 'nTRN':
        child, reserved, layer, nframes = struct.unpack_from('<iiii', b, o); o += 16
        frames = []
        for _ in range(nframes):
            f, o = _dict(b, o); frames.append(f)
        node.update(child=child, reserved=reserved, layer=layer, frames=frames)
    elif cid == 'nGRP':
        n = struct.unpack_from('<i', b, o)[0]; o += 4
        node['children'] = list(struct.unpack_from('<%di' % n, b, o))
    elif cid == 'nSHP':
        n = struct.unpack_from('<i', b, o)[0]; o += 4
        models = []
        for _ in range(n):
            mid = struct.unpack_from('<i', b, o)[0]; o += 4
            md, o = _dict(b, o); models.append((mid, md))
        node['models'] = models
    return node

def summarize(path):
    ver, chunks = read_chunks(path)
    from collections import Counter
    cnt = Counter(c['id'] for c in chunks)
    nodes = {}
    layers = []
    for c in chunks:
        if c['id'] in ('nTRN', 'nGRP', 'nSHP'):
            nd = parse_node(c); nodes[nd['id']] = nd
        elif c['id'] == 'LAYR':
            lid = struct.unpack_from('<i', c['content'], 0)[0]
            d, _ = _dict(c['content'], 4)
            layers.append((lid, d))
    return ver, cnt, nodes, layers, chunks

def tree(nodes, nid=0, depth=0, out=None, maxdepth=99):
    out = out if out is not None else []
    n = nodes[nid]; pad = '  ' * depth
    if n['type'] == 'nTRN':
        name = n['attrs'].get('_name', '')
        hid = n['attrs'].get('_hidden', '')
        fr = n['frames']
        desc = f"{pad}nTRN {nid} name={name!r} layer={n['layer']} frames={len(fr)}"
        if hid: desc += f" hidden={hid}"
        if fr: desc += f" f0={fr[0]}"
        if len(fr) > 1: desc += f" ... last={fr[-1]}"
        out.append(desc)
        if depth < maxdepth: tree(nodes, n['child'], depth + 1, out, maxdepth)
    elif n['type'] == 'nGRP':
        out.append(f"{pad}nGRP {nid} children={len(n['children'])} attrs={n['attrs']}")
        if depth < maxdepth:
            for ch in n['children']: tree(nodes, ch, depth + 1, out, maxdepth)
    else:
        ms = n['models']
        desc = f"{pad}nSHP {nid} models={len(ms)} first={ms[0] if ms else None}"
        if n['attrs']: desc += f" attrs={n['attrs']}"
        out.append(desc)
    return out
