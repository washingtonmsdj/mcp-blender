"""Opt-in integration smoke: real Blender rendering in a temporary isolated project.

Run with the repository Python: python scripts/verify_visual_agent.py
Does not open or modify the user's scenes or running agent.
"""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp_blender_unity.config import find_blender
from mcp_blender_unity.process import run_process
from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig


def main():
    blender = find_blender()
    if not blender:
        raise SystemExit("Blender not installed")
    with tempfile.TemporaryDirectory(prefix="ordax-visual-test-") as directory:
        root = Path(directory)
        scene = root / "scene.blend"
        # Blender factory startup includes a cube, light and camera.
        create = run_process([str(blender), "--background", "--factory-startup", "--python-exit-code", "1",
                              "--python-expr", f"import bpy; bpy.ops.wm.save_as_mainfile(filepath={str(scene)!r})"],
                             timeout_seconds=120)
        if not create['ok']:
            raise RuntimeError(create)
        config = AgentConfig('smoke', None, None, 5, root / 'state', root, root, root,
                             projects={'cube': {'path': str(root), 'apps': ['blender'],
                                                'blender': {'blend_file': 'scene.blend'}}}, default_project='cube')
        agent = ActionRegistry(config)
        before = scene.read_bytes()
        result = agent.execute('observation.capture', {'app': 'blender', 'frames': 2,
                                                     'width': 320, 'height': 180, 'samples': 4})
        if not result.ok:
            raise RuntimeError(json.dumps(result.data, indent=2))
        observations = result.data['observations']
        assert len(observations) == 2
        assert observations[0]['artifact'] != observations[1]['artifact']
        for observation in observations:
            assert Path(observation['artifact']).read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
            assert observation['snapshot']['object_count'] == 3
        assert scene.read_bytes() == before, 'Observation modified the original .blend file'
        print(json.dumps({'ok': True, 'frames': len(observations), 'objects': 3,
                          'source_unchanged': True, 'durations': [o['duration_seconds'] for o in observations]}, indent=2))


if __name__ == '__main__':
    main()
