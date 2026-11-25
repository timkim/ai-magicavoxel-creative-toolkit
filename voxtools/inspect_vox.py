"""Inspect a .vox: print the object tree, or compute the world-space voxels of the scene.
  python inspect_vox.py scene.vox            # object tree with sizes, layers and animation info
"""
import sys
from collections import Counter
import numpy as np
from voxwrite import load_scene
from scenegraph import rot_matrix, parse_t, IDENTITY_R

def world_voxels(sc, pose='rest'):
    """Counter of (x, y, z, colour) in world space. pose='rest' uses each animated node's _frm_t
    (its landed / edit-view pose); pose='first' uses frame 0."""
    out = Counter()
    def walk(i, R, t):
        nd = sc.nodes[i]
        if nd['type'] == 'nTRN':
            f = nd['frames'][0] if nd['frames'] else {}
            tl = parse_t(nd['attrs']['_frm_t']) if pose == 'rest' and '_frm_t' in nd['attrs'] else parse_t(f.get('_t', ''))
            walk(nd['child'], R @ rot_matrix(f.get('_r', IDENTITY_R)), t + R @ tl)
        elif nd['type'] == 'nGRP':
            for c in nd['children']: walk(c, R, t)
        else:
            m = nd['models'][0][0]; size, vox = sc.models[m]
            half = np.array(size) // 2
            for x, y, z, c in vox:
                w = t + R @ (np.array((x, y, z)) - half)
                out[(int(w[0]), int(w[1]), int(w[2]), c)] += 1
    walk(0, np.eye(3, dtype=int), np.zeros(3, int))
    return out

def tree(sc):
    def walk(i, depth):
        nd = sc.nodes[i]
        if nd['type'] == 'nTRN':
            name = nd['attrs'].get('_name', ''); anim = f' {len(nd["frames"])} keys' if len(nd['frames']) > 1 else ''
            ch = sc.nodes[nd['child']]
            if ch['type'] == 'nSHP':
                sz = sc.models[ch['models'][0][0]][0]
                fb = f' flipbook x{len(ch["models"])}' if len(ch['models']) > 1 else ''
                print('  ' * depth + f'{name or "(unnamed)"}  {sz[0]}x{sz[1]}x{sz[2]}  layer {nd["layer"]}{anim}{fb}')
            else:
                print('  ' * depth + f'{name or "(group)"}  layer {nd["layer"]}{anim}')
                walk(nd['child'], depth + 1)
        elif nd['type'] == 'nGRP':
            for c in nd['children']: walk(c, depth)
    walk(0, 0)

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Print the object tree of a .vox (names, sizes, layers, animation).')
    ap.add_argument('vox'); a = ap.parse_args()
    tree(load_scene(a.vox))
