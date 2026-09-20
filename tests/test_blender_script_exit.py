import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from mcp_blender_unity.server import blender_run_python

class BlenderScriptExitTests(unittest.TestCase):
    def test_script_failure_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as directory:
            script=Path(directory)/'failure.py'
            script.write_text("raise RuntimeError('intentional')",encoding='utf-8')
            def simulate(command,**kwargs):
                # Blender's documented CLI behavior: Python errors default to exit 0.
                fails='--python-exit-code' in command and command.index('--python-exit-code')<command.index('--python')
                return {'ok':not fails,'returncode':1 if fails else 0}
            with patch('mcp_blender_unity.server._required_file',return_value=Path('blender')),patch('mcp_blender_unity.server.find_blender'),patch('mcp_blender_unity.server.run_process',side_effect=simulate):
                self.assertFalse(blender_run_python(str(script))['ok'])
