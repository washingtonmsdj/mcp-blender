import base64
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ordax_dev_agent.actions import ActionRegistry
from ordax_dev_agent.config import AgentConfig
from ordax_dev_agent.models import ActionResult
from ordax_dev_agent.mcp_server import artifact_image


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.project = self.root / 'project'
        (self.project / 'references').mkdir(parents=True)
        self.png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1cAAAAASUVORK5CYII=')
        (self.project / 'references/front.png').write_bytes(self.png)
        self.manifest = {'version': 1, 'assets': {'bottle': {
            'requirements': ['Preserve silhouette'], 'dimensions_world_m': {'z': .2},
            'references': [{'id': 'front', 'path': 'references/front.png',
                            'view': 'front', 'projection': 'orthographic'}]}}}
        self.save()
        self.registry = ActionRegistry(AgentConfig('test', None, None, 5, self.root / 'state',
            self.root, self.root, self.root, projects={'model': {'path': str(self.project), 'apps': ['blender']}},
            default_project='model'))

    def save(self):
        (self.project / 'references/manifest.json').write_text(json.dumps(self.manifest), encoding='utf-8')

    def execute(self, action='project.reference_images', **payload):
        return self.registry.execute(action, {'asset': 'bottle', **payload})

    def test_catalog_does_not_copy_images(self):
        result = self.registry.execute('project.references', {})
        self.assertTrue(result.ok)
        self.assertEqual(result.data['assets'], [{'asset': 'bottle', 'reference_count': 1}])
        self.assertFalse((self.root / 'state/artifacts').exists())

    def test_image_is_readable_as_actual_mcp_pixels(self):
        result = self.execute()
        self.assertTrue(result.ok)
        ref = result.data['references'][0]
        self.assertEqual(ref['sha256'], hashlib.sha256(self.png).hexdigest())
        with patch('ordax_dev_agent.mcp_server.registry', return_value=self.registry):
            content = artifact_image('model', ref['artifact'])
        self.assertEqual(base64.b64decode(content[1].data), self.png)

    def test_path_escape_and_absolute_path_rejected(self):
        (self.root / 'outside.png').write_bytes(self.png)
        for name in ('../outside.png', str(self.root / 'outside.png')):
            self.manifest['assets']['bottle']['references'][0]['path'] = name
            self.save()
            self.assertFalse(self.execute().ok)

    def test_changed_manifest_or_pinned_image_rejected(self):
        self.assertFalse(self.execute(manifest_sha256='old').ok)
        self.manifest['assets']['bottle']['references'][0]['sha256'] = 'old'
        self.save()
        self.assertFalse(self.execute().ok)

    def test_invalid_images_and_unknown_ids_rejected(self):
        self.assertFalse(self.execute(reference_ids=['missing']).ok)
        (self.project / 'references/front.png').write_bytes(b'not an image')
        self.assertFalse(self.execute().ok)

    def test_invalid_dimensions_and_duplicate_ids_rejected(self):
        self.manifest['assets']['bottle']['dimensions_world_m']['z'] = float('nan')
        self.save()
        self.assertFalse(self.execute().ok)
        self.manifest['assets']['bottle']['dimensions_world_m'] = {}
        refs = self.manifest['assets']['bottle']['references']
        refs.append(dict(refs[0]))
        self.save()
        self.assertFalse(self.execute().ok)

    def test_review_pairs_evidence_without_claiming_visual_success(self):
        capture = ActionResult(True, 'capture', {'views': [{'view': 'front', 'artifact': 'model.png'}],
            'bounds_world': {'min': [0, 0, 0], 'max': [10, 10, 20]}, 'unit_scale_m': .01})
        with patch.object(self.registry, 'blender_live_capture', return_value=capture) as call:
            result = self.execute('blender.reference_review', objects=['Body'])
        self.assertTrue(result.ok)
        self.assertEqual(call.call_args.args[0]['views'], ['front'])
        self.assertTrue(result.data['dimension_checks'][0]['within_tolerance'])
        self.assertFalse(result.data['pairs'][0]['pixel_alignment_verified'])
        self.assertIn('pending', result.data['visual_assessment'])

    def test_unknown_units_do_not_invent_meter_measurements(self):
        capture = ActionResult(True, 'capture', {'views': [],
            'bounds_world': {'min': [0, 0, 0], 'max': [1, 1, 1]}, 'unit_scale_m': None})
        with patch.object(self.registry, 'blender_live_capture', return_value=capture):
            result = self.execute('blender.reference_review', objects=['Body'])
        self.assertEqual(result.data['dimension_checks'][0]['status'], 'unknown')

    def test_failed_capture_keeps_reference_evidence_and_unknown_outcome(self):
        capture = ActionResult(False, 'timeout', {'outcome_unknown': True, 'command_id': 'test'})
        with patch.object(self.registry, 'blender_live_capture', return_value=capture):
            result = self.execute('blender.reference_review', objects=['Body'])
        self.assertFalse(result.ok)
        self.assertTrue(result.data['capture']['outcome_unknown'])
        self.assertEqual(len(result.data['artifacts']), 1)

    def test_review_requires_explicit_objects(self):
        self.assertFalse(self.execute('blender.reference_review').ok)

    def test_detail_reference_does_not_get_a_false_matching_view(self):
        self.manifest['assets']['bottle']['references'][0]['view'] = 'detail'
        self.save()
        capture = ActionResult(True, 'capture', {'views': [{'view': 'front'}],
            'bounds_world': {'min': [0, 0, 0], 'max': [1, 1, 1]}, 'unit_scale_m': 1})
        with patch.object(self.registry, 'blender_live_capture', return_value=capture) as call:
            result = self.execute('blender.reference_review', objects=['Body'])
        self.assertIsNone(result.data['pairs'][0]['model'])
        self.assertEqual(len(call.call_args.args[0]['views']), 4)
        self.assertFalse(result.data['dimension_checks'][0]['within_tolerance'])
