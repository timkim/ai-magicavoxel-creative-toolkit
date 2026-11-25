"""After fall.py, the landed scene must be voxel-for-voxel identical to the original.
  python tests/test_fall.py some_scene.vox"""
import os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); TOOLS = os.path.join(HERE, '..', 'voxtools')
sys.path.insert(0, TOOLS)
from voxwrite import load_scene
from inspect_vox import world_voxels

def check(src, *args):
    out = os.path.join(tempfile.mkdtemp(), 'out.vox')
    subprocess.run([sys.executable, os.path.join(TOOLS, 'fall.py'), src, out, *args], check=True, capture_output=True)
    a = world_voxels(load_scene(src)); b = world_voxels(load_scene(out))
    ok = a == b
    print(('OK  ' if ok else 'FAIL'), ' '.join(args) or '(defaults)', f'{sum(a.values())} voxels')
    return ok

if __name__ == '__main__':
    src = sys.argv[1]
    results = [check(src), check(src, '--pieces', 'floors', '--order', 'wave'), check(src, '--size', '5')]
    sys.exit(0 if all(results) else 1)
