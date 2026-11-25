"""Scene-graph helpers: MagicaVoxel rotations and world transforms of transform (nTRN) nodes."""
import numpy as np

IDENTITY_R = '4'      # MagicaVoxel's packed rotation byte for "no rotation"

def rot_matrix(r):
    """Decode MagicaVoxel's packed rotation byte into a 3x3 matrix (world = R @ local)."""
    r = int(r); i0 = r & 3; i1 = (r >> 2) & 3; i2 = 3 - i0 - i1
    M = np.zeros((3, 3), int)
    for row, (idx, bit) in enumerate(((i0, 4), (i1, 5), (i2, 6))):
        M[row, idx] = -1 if (r >> bit) & 1 else 1
    return M

def parse_t(s):
    return np.array([int(v) for v in s.split()], int) if s else np.zeros(3, int)

def frame0(trn):
    """The transform shown at frame 0 (first keyframe)."""
    return trn['frames'][0] if trn['frames'] else {}

def world_transforms(sc):
    """{trn_id: (R_parent, t_parent)} -- the world transform of each nTRN's *parent*, so that
    world(p) = t_parent + R_parent @ (t_local + R_local @ p) for a point p inside the node."""
    out = {}
    def walk(i, R, t):
        nd = sc.nodes[i]
        if nd['type'] == 'nTRN':
            out[i] = (R, t)
            f = frame0(nd)
            Rl = rot_matrix(f.get('_r', IDENTITY_R)); tl = parse_t(f.get('_t', ''))
            walk(nd['child'], R @ Rl, t + R @ tl)
        elif nd['type'] == 'nGRP':
            for c in nd['children']: walk(c, R, t)
    walk(0, np.eye(3, dtype=int), np.zeros(3, int))
    return out

def node_world(sc, wt, trn_id):
    """World rotation and translation of the node itself (including its own transform)."""
    R, t = wt[trn_id]; f = frame0(sc.nodes[trn_id])
    return R @ rot_matrix(f.get('_r', IDENTITY_R)), t + R @ parse_t(f.get('_t', ''))

def shape_targets(sc, names=None):
    """nTRN ids whose child is a single-model, unanimated nSHP -- the things we can break apart.
    names=None: every such node under the root's top level (descending into groups).
    Returns (targets, whole, skipped): `whole` are flipbooks (several models) that can only move as
    one piece; `skipped` lists (name, reason) for nodes that are already animated."""
    root = sc.nodes[sc.nodes[0]['child']]
    targets, whole, skipped = [], [], []
    def consider(tid, label):
        t = sc.nodes[tid]; ch = sc.nodes[t['child']]
        if ch['type'] == 'nGRP':
            for k in ch['children']:
                if sc.nodes[k]['type'] == 'nTRN': consider(k, label)
            return
        if len(t['frames']) > 1: skipped.append((label, 'already animated')); return
        if len(ch['models']) > 1: whole.append(tid); return
        targets.append(tid)
    if names is None:
        for k in root['children']: consider(k, sc.nodes[k]['attrs'].get('_name', f'node {k}'))
    else:
        want = set(names); found = set()
        for nd in sc.nodes:
            nm = nd['attrs'].get('_name') if nd['type'] == 'nTRN' else None
            if nm in want: consider(nd['id'], nm); found.add(nm)
        missing = want - found
        if missing: raise SystemExit(f'no object named: {", ".join(sorted(missing))}')
    return targets, whole, skipped

def model_users(sc, target_trns):
    """For each model id: 'targets-only' if only the given targets use it (its slot may be reused)."""
    shps = {sc.nodes[t]['child'] for t in target_trns}; users = {}
    for nd in sc.nodes:
        if nd['type'] == 'nSHP':
            for mid, _ in nd['models']:
                users[mid] = users.get(mid, 'targets-only') if nd['id'] in shps else 'other'
    return users
