import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ordax_dev_agent.assets.blender_modeling import validate
from ordax_dev_agent.blender_live import BlenderLiveActions, BlenderLive
from ordax_dev_agent.models import ActionResult


class ModelingTests(unittest.TestCase):
    def test_supported_operations(self):
        validate('create', {'name': 'Body', 'primitive': 'cube', 'size': 2})
        validate('create', {'name': 'Round', 'primitive': 'sphere', 'segments': 32})
        validate('transform', {'object': 'Body', 'rotation_degrees': [0, 45, 0]})
        validate('modifier', {'object': 'Body', 'name': 'Edges', 'type': 'BEVEL', 'segments': 3})

    def test_unknown_missing_and_inapplicable_parameters_fail(self):
        for action, args in [('delete', {}), ('create', {'name': 'Body'}),
            ('create', {'name': 'Body', 'primitive': 'cube', 'radius': 3}),
            ('modifier', {'object': 'Body', 'name': 'M', 'type': 'MIRROR', 'width': 1}),
            ('transform', {'object': 'Body'}), ('transform', {'object': 'Body', 'code': 'anything'})]:
            with self.subTest(action=action, args=args), self.assertRaises(ValueError):
                validate(action, args)

    def test_numeric_limits_reject_nan_boolean_and_excess(self):
        for scale in ([float('nan'), 1, 1], [0, 1, 1], [True, 1, 1], [1001, 1, 1]):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                validate('transform', {'object': 'Body', 'scale': scale})
        with self.assertRaises(ValueError):
            validate('modifier', {'object': 'Body', 'name': 'Sub', 'type': 'SUBSURF', 'levels': 3})

    def test_utf8_names_not_silently_truncated(self):
        with self.assertRaises(ValueError):
            validate('create', {'name': 'é' * 40, 'primitive': 'cube'})

    def agent(self, enabled):
        agent = BlenderLiveActions()
        agent._project = lambda payload: SimpleNamespace(blender={'allow_modeling': enabled}, slug='model')
        return agent

    def test_local_permission_is_required_before_ipc(self):
        with patch.object(BlenderLive, 'request') as request:
            for value in (False, None, 'true', 1):
                with self.assertRaises(ValueError):
                    self.agent(value).blender_model_create({'name': 'Body', 'primitive': 'cube'})
            request.assert_not_called()

    def test_validated_operation_uses_live_transport(self):
        with patch.object(BlenderLive, '__init__', return_value=None), \
             patch.object(BlenderLive, 'request', return_value=ActionResult(True, 'done')) as request:
            result = self.agent(True).blender_model_transform({'project': 'model', 'object': 'Body', 'scale': [1, 2, 1]})
        self.assertTrue(result.ok)
        self.assertEqual(request.call_args.args[0], 'model')
        self.assertNotIn('project', request.call_args.args[1]['arguments'])

    def test_schemas_discoverable_without_enabling_mutations(self):
        result = self.agent(False).blender_modeling_tools({})
        self.assertFalse(result.data['enabled_locally'])
        self.assertIn('blender.model_create', result.data['tools'])
