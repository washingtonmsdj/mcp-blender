import json
import tempfile
import unittest
import uuid
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from ordax_dev_agent.assets.blender_checkpoints import identifier, listing, create, restore
from ordax_dev_agent.blender_live import BlenderLive, BlenderLiveActions


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.state = {'project': self.root, 'allow_checkpoints': True, 'allow_restore': True}
        self.fake_bpy = SimpleNamespace(context=SimpleNamespace(mode='OBJECT'),
            app=SimpleNamespace(is_job_running=lambda job: False), data=SimpleNamespace(images=[]), ops=Mock())

    def test_ids_cannot_escape_storage(self):
        for value in (None, '../outside', 'x', 5):
            with self.assertRaises(ValueError):
                identifier(value)

    def test_list_skips_incomplete_and_malformed_records(self):
        root = self.root / '.ordax/blender/checkpoints'
        for index, created in enumerate((1, 2, 'invalid')):
            checkpoint_id = uuid.uuid4().hex
            folder = root / checkpoint_id
            folder.mkdir(parents=True)
            (folder / 'checkpoint.json').write_text(json.dumps({'checkpoint_id': checkpoint_id, 'created_at': created}))
        (root / uuid.uuid4().hex).mkdir()
        result = listing(self.root, limit=1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['checkpoints'][0]['created_at'], 2)

    def test_dirty_images_block_creation(self):
        self.fake_bpy.data.images = [SimpleNamespace(is_dirty=True, type='IMAGE')]
        with patch.dict('sys.modules', {'bpy': self.fake_bpy}), self.assertRaises(ValueError):
            create(self.state)
        self.fake_bpy.ops.wm.save_as_mainfile.assert_not_called()

    def test_low_disk_space_blocks_save(self):
        with patch.dict('sys.modules', {'bpy': self.fake_bpy}), \
             patch('ordax_dev_agent.assets.blender_checkpoints.shutil.disk_usage', return_value=SimpleNamespace(free=0)), \
             self.assertRaises(ValueError):
            create(self.state)
        self.fake_bpy.ops.wm.save_as_mainfile.assert_not_called()

    def test_restore_confirmation_and_permission_required(self):
        with patch.dict('sys.modules', {'bpy': self.fake_bpy}):
            with self.assertRaises(ValueError):
                restore(self.state, {}, uuid.uuid4().hex)
            with self.assertRaises(ValueError):
                restore({**self.state, 'allow_restore': False}, {'confirm_replace_scene': True}, uuid.uuid4().hex)
        self.fake_bpy.ops.wm.open_mainfile.assert_not_called()

    def test_integrity_failure_never_opens_scene(self):
        checkpoint_id = uuid.uuid4().hex
        folder = self.root / '.ordax/blender/checkpoints' / checkpoint_id
        folder.mkdir(parents=True)
        (folder / 'checkpoint.blend').write_bytes(b'tampered')
        (folder / 'checkpoint.json').write_text(json.dumps({'checkpoint_id': checkpoint_id, 'sha256': '0' * 64}))
        with patch.dict('sys.modules', {'bpy': self.fake_bpy}), self.assertRaises(ValueError):
            restore(self.state, {'checkpoint_id': checkpoint_id, 'expected_sha256': '0' * 64,
                                'confirm_replace_scene': True}, uuid.uuid4().hex)
        self.fake_bpy.ops.wm.open_mainfile.assert_not_called()

    def test_host_denies_restore_before_transport(self):
        agent = BlenderLiveActions()
        agent._project = lambda payload: SimpleNamespace(blender={})
        with patch.object(BlenderLive, 'request') as request, self.assertRaises(ValueError):
            agent.blender_checkpoint_restore({})
        request.assert_not_called()

    def test_automatic_protection_requires_checkpoint_permission(self):
        agent = BlenderLiveActions()
        agent._project = lambda payload: SimpleNamespace(blender={'allow_modeling': True, 'checkpoint_before_modeling': True})
        with patch.object(BlenderLive, 'request') as request, self.assertRaises(ValueError):
            agent.blender_model_create({'name': 'Body', 'primitive': 'cube'})
        request.assert_not_called()
