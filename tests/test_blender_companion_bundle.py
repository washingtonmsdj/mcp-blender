import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.blender_live_bridge import (
    blender_companion_bundle_fingerprint,
)
from ordax_dev_agent.assets.blender_modeling_contracts import (
    evaluate_modifier_runtime_budget,
    modeling_schemas,
    normalize_transform_fields,
    normalize_transform_request,
    plan_modeling_operation,
)


def load_spatial_math():
    root = Path(__file__).resolve().parents[1]
    path = root / "ordax_dev_agent" / "assets" / "blender_spatial_math.py"
    spec = importlib.util.spec_from_file_location(
        "_test_ordax_blender_spatial_math",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Blender spatial math helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_quality_rules():
    root = Path(__file__).resolve().parents[1]
    path = root / "ordax_dev_agent" / "assets" / "blender_quality_rules.py"
    spec = importlib.util.spec_from_file_location(
        "_test_ordax_blender_quality_rules",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Blender quality rules helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_uv_math():
    root = Path(__file__).resolve().parents[1]
    path = root / "ordax_dev_agent" / "assets" / "blender_uv_math.py"
    spec = importlib.util.spec_from_file_location("_test_ordax_blender_uv_math", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load Blender UV math helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BlenderCompanionBundleTests(unittest.TestCase):
    def test_bundle_fingerprint_changes_when_helper_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "blender_live_companion.py").write_text(
                "print('companion')\n",
                encoding="utf-8",
            )
            helper = root / "blender_uv_math.py"
            helper.write_text("VALUE = 1\n", encoding="utf-8")
            (root / "blender_companion_bundle.json").write_text(
                json.dumps(
                    {
                        "version": 1,
                        "files": [
                            "blender_live_companion.py",
                            "blender_uv_math.py",
                        ],
                    }
                ),
                encoding="utf-8",
            )

            before = blender_companion_bundle_fingerprint(root)
            helper.write_text("VALUE = 2\n", encoding="utf-8")
            after = blender_companion_bundle_fingerprint(root)

        self.assertNotEqual(before, after)

    def test_bundle_fingerprint_is_independent_of_manifest_file_order(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.py").write_text("A = 1\n", encoding="utf-8")
            (root / "b.py").write_text("B = 2\n", encoding="utf-8")
            manifest = root / "blender_companion_bundle.json"
            manifest.write_text(
                json.dumps({"version": 1, "files": ["a.py", "b.py"]}),
                encoding="utf-8",
            )
            first = blender_companion_bundle_fingerprint(root)
            manifest.write_text(
                json.dumps({"version": 1, "files": ["b.py", "a.py"]}),
                encoding="utf-8",
            )
            second = blender_companion_bundle_fingerprint(root)

        self.assertEqual(first, second)

    def test_bundle_rejects_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            outside = root.parent / "outside-companion-helper.py"
            outside.write_text("VALUE = 1\n", encoding="utf-8")
            self.addCleanup(outside.unlink, missing_ok=True)
            (root / "blender_companion_bundle.json").write_text(
                json.dumps({"version": 1, "files": ["../outside-companion-helper.py"]}),
                encoding="utf-8",
            )

            with self.assertRaises(ValueError):
                blender_companion_bundle_fingerprint(root)

    def test_repository_bundle_fingerprint_is_valid(self) -> None:
        root = (
            Path(__file__).resolve().parents[1]
            / "ordax_dev_agent"
            / "assets"
        )
        digest = blender_companion_bundle_fingerprint(root)
        self.assertEqual(64, len(digest))
        manifest = json.loads(
            (root / "blender_companion_bundle.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            [
                "blender_live_companion.py",
                "blender_uv_math.py",
                "blender_spatial_math.py",
                "blender_quality_rules.py",
                "blender_modeling_contracts.py",
            ],
            manifest["files"],
        )


class BlenderModelingContractTests(unittest.TestCase):
    def test_create_primitive_plan_applies_typed_defaults(self) -> None:
        plan = plan_modeling_operation(
            "create_primitive",
            {"name": "Body", "primitive": "sphere"},
        )
        self.assertFalse(plan["executable"])
        self.assertEqual("pending_blender_smoke", plan["status"])
        self.assertEqual(
            {
                "name": "Body",
                "primitive": "sphere",
                "location": [0.0, 0.0, 0.0],
                "radius": 1.0,
                "segments": 32,
            },
            plan["arguments"],
        )

    def test_create_plan_rejects_primitive_specific_mismatch(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported field.*cube"):
            plan_modeling_operation(
                "create_primitive",
                {
                    "name": "Body",
                    "primitive": "cube",
                    "radius": 1.0,
                },
            )

    def test_modifier_plan_applies_type_specific_defaults(self) -> None:
        plan = plan_modeling_operation(
            "add_modifier",
            {
                "object_name": "Body",
                "name": "SoftEdges",
                "type": "bevel",
            },
        )
        self.assertFalse(plan["executable"])
        self.assertEqual(
            {
                "object_name": "Body",
                "name": "SoftEdges",
                "type": "BEVEL",
                "width": 0.05,
                "segments": 2,
            },
            plan["arguments"],
        )

    def test_transform_plan_is_executable_and_closed_to_unknown_fields(self) -> None:
        plan = plan_modeling_operation(
            "object_transform",
            {
                "ordax_object_id": "hull.main",
                "location": [1, 2, 3],
            },
        )
        self.assertTrue(plan["executable"])
        self.assertEqual("blender.live_object_transform", plan["action"])
        self.assertEqual(
            {
                "ordax_object_id": "hull.main",
                "location": [1.0, 2.0, 3.0],
            },
            plan["arguments"],
        )
        with self.assertRaisesRegex(ValueError, "unsupported field"):
            plan_modeling_operation(
                "object_transform",
                {
                    "object_name": "Body",
                    "location": [0, 0, 0],
                    "anything": True,
                },
            )

    def test_selector_rejects_non_string_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "object_name must be a string"):
            plan_modeling_operation(
                "object_transform",
                {
                    "object_name": 123,
                    "location": [0, 0, 0],
                },
            )

    def test_modifier_plan_exposes_runtime_guard_limits(self) -> None:
        plan = plan_modeling_operation(
            "add_modifier",
            {
                "object_name": "Body",
                "name": "Subsurf",
                "type": "SUBSURF",
                "levels": 2,
            },
        )
        self.assertEqual(
            {
                "max_modifier_stack": 8,
                "max_evaluated_faces": 200000,
                "max_projected_subsurf_faces": 500000,
            },
            plan["runtime_guards"],
        )

    def test_create_plan_exposes_runtime_and_failure_contracts(self) -> None:
        plan = plan_modeling_operation(
            "create_primitive",
            {"name": "Body", "primitive": "cube"},
        )
        self.assertEqual(
            ["object_mode", "no_render_job", "unique_object_name"],
            plan["runtime_requirements"],
        )
        self.assertEqual(
            [
                "remove_partial_object_on_failure",
                "remove_partial_mesh_on_failure",
            ],
            plan["failure_policy"],
        )

    def test_modifier_plan_exposes_runtime_and_failure_contracts(self) -> None:
        plan = plan_modeling_operation(
            "add_modifier",
            {
                "object_name": "Body",
                "name": "Edges",
                "type": "BEVEL",
            },
        )
        self.assertIn(
            "local_nonlinked_mesh_target",
            plan["runtime_requirements"],
        )
        self.assertIn(
            "unique_modifier_name",
            plan["runtime_requirements"],
        )
        self.assertIn(
            "animated_or_constrained_target_requires_dedicated_workflow",
            plan["runtime_requirements"],
        )
        self.assertEqual(
            [
                "remove_new_modifier_on_failure",
                "preserve_existing_modifier_stack",
            ],
            plan["failure_policy"],
        )

    def test_transform_plan_does_not_inherit_legacy_mesh_only_runtime_guards(self) -> None:
        plan = plan_modeling_operation(
            "object_transform",
            {
                "object_name": "Camera",
                "location": [1, 2, 3],
            },
        )
        self.assertTrue(plan["executable"])
        self.assertNotIn("runtime_requirements", plan)
        self.assertNotIn("failure_policy", plan)

    def test_modifier_budget_rejects_full_stack(self) -> None:
        result = evaluate_modifier_runtime_budget(
            modifier_type="BEVEL",
            modifier_count=8,
            evaluated_faces=1000,
        )
        self.assertFalse(result["allowed"])
        self.assertIn("modifier stack limit reached", result["reasons"])

    def test_modifier_budget_rejects_mesh_above_evaluated_face_limit(self) -> None:
        result = evaluate_modifier_runtime_budget(
            modifier_type="SOLIDIFY",
            modifier_count=2,
            evaluated_faces=200001,
        )
        self.assertFalse(result["allowed"])
        self.assertIn(
            "evaluated mesh exceeds interactive face budget",
            result["reasons"],
        )

    def test_subsurf_budget_uses_projected_face_count(self) -> None:
        accepted = evaluate_modifier_runtime_budget(
            modifier_type="SUBSURF",
            modifier_count=2,
            evaluated_faces=31250,
            levels=2,
        )
        self.assertTrue(accepted["allowed"])
        self.assertEqual(500000, accepted["projected_faces"])

        rejected = evaluate_modifier_runtime_budget(
            modifier_type="SUBSURF",
            modifier_count=2,
            evaluated_faces=31251,
            levels=2,
        )
        self.assertFalse(rejected["allowed"])
        self.assertEqual(500016, rejected["projected_faces"])
        self.assertIn(
            "projected SUBSURF mesh exceeds interactive face budget",
            rejected["reasons"],
        )

    def test_modifier_budget_rejects_boolean_or_invalid_metrics(self) -> None:
        with self.assertRaises(ValueError):
            evaluate_modifier_runtime_budget(
                modifier_type="BEVEL",
                modifier_count=True,
                evaluated_faces=100,
            )
        with self.assertRaises(ValueError):
            evaluate_modifier_runtime_budget(
                modifier_type="SUBSURF",
                modifier_count=1,
                evaluated_faces=100,
                levels=3,
            )

    def test_schema_keeps_unverified_mutations_disabled(self) -> None:
        schemas = modeling_schemas()
        self.assertEqual("available", schemas["object_transform"]["status"])
        self.assertEqual(
            "pending_blender_smoke",
            schemas["create_primitive"]["status"],
        )
        self.assertEqual(
            "pending_blender_smoke",
            schemas["add_modifier"]["status"],
        )

    def test_schema_copy_cannot_mutate_global_contract(self) -> None:
        first = modeling_schemas()
        first["object_transform"]["status"] = "changed"
        self.assertEqual(
            "available",
            modeling_schemas()["object_transform"]["status"],
        )

    def test_transform_contract_rejects_nonfinite_and_boolean_values(self) -> None:
        for payload in (
            {"location": [0, float("nan"), 0]},
            {"rotation_euler": [0, True, 0]},
            {"scale": [1, float("inf"), 1]},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                normalize_transform_fields(payload)

    def test_transform_contract_enforces_positive_scale_and_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            normalize_transform_fields({"scale": [1, 0, 1]})
        with self.assertRaises(ValueError):
            normalize_transform_fields({"dimensions": [1, -1, 1]})

    def test_transform_contract_normalizes_valid_values(self) -> None:
        self.assertEqual(
            {
                "location": [1.0, 2.5, -3.0],
                "rotation_euler": [0.0, 1.25, 0.0],
                "scale": [1.0, 2.0, 1.0],
            },
            normalize_transform_fields(
                {
                    "location": [1, 2.5, -3],
                    "rotation_euler": [0, 1.25, 0],
                    "scale": [1, 2, 1],
                }
            ),
        )

    def test_companion_transform_validation_accepts_only_transport_metadata(self) -> None:
        normalized = normalize_transform_request(
            {
                "id": "command-1",
                "operation": "object_transform",
                "object_name": "Hull",
                "location": [1, 2, 3],
                "scale": [1, 1.5, 1],
            },
            transport_fields={"id", "operation"},
        )
        self.assertEqual(
            {
                "object_name": "Hull",
                "location": [1.0, 2.0, 3.0],
                "scale": [1.0, 1.5, 1.0],
            },
            normalized,
        )

        with self.assertRaisesRegex(ValueError, "unsupported field"):
            normalize_transform_request(
                {
                    "id": "command-1",
                    "operation": "object_transform",
                    "project": "model",
                    "object_name": "Hull",
                    "location": [0, 0, 0],
                },
                transport_fields={"id", "operation"},
            )

    def test_companion_transform_validation_rejects_boolean_and_zero_scale(self) -> None:
        with self.assertRaises(ValueError):
            normalize_transform_request(
                {
                    "id": "command-1",
                    "operation": "object_transform",
                    "object_name": "Hull",
                    "rotation_euler": [0, True, 0],
                },
                transport_fields={"id", "operation"},
            )
        with self.assertRaises(ValueError):
            normalize_transform_request(
                {
                    "id": "command-1",
                    "operation": "object_transform",
                    "object_name": "Hull",
                    "scale": [1, 0, 1],
                },
                transport_fields={"id", "operation"},
            )


class BlenderSpatialMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spatial = load_spatial_math()

    def test_aabb_overlap_accepts_touching_faces(self) -> None:
        left = {"aabb_min": [0, 0, 0], "aabb_max": [1, 1, 1]}
        right = {"aabb_min": [1, 0, 0], "aabb_max": [2, 1, 1]}
        self.assertTrue(self.spatial.aabb_overlap(left, right))

    def test_aabb_overlap_rejects_separated_boxes(self) -> None:
        left = {"aabb_min": [0, 0, 0], "aabb_max": [1, 1, 1]}
        right = {"aabb_min": [1.01, 0, 0], "aabb_max": [2, 1, 1]}
        self.assertFalse(self.spatial.aabb_overlap(left, right))

    def test_aabb_contains_respects_tolerance(self) -> None:
        outer = {"aabb_min": [0, 0, 0], "aabb_max": [1, 1, 1]}
        inner = {
            "aabb_min": [-5e-7, 0.1, 0.1],
            "aabb_max": [1.0000005, 0.9, 0.9],
        }
        self.assertTrue(self.spatial.aabb_contains(outer, inner, 1e-6))
        self.assertFalse(self.spatial.aabb_contains(outer, inner, 1e-8))

    def test_aabb_helpers_reject_missing_bounds(self) -> None:
        complete = {"aabb_min": [0, 0, 0], "aabb_max": [1, 1, 1]}
        self.assertFalse(self.spatial.aabb_overlap({}, complete))
        self.assertFalse(self.spatial.aabb_contains(complete, {}))


class BlenderQualityRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.rules = load_quality_rules()

    def test_quality_axis_normalizes_case_and_whitespace(self) -> None:
        self.assertEqual(("x", 0), self.rules.quality_axis(" X ", "axis"))
        self.assertEqual(("z", 2), self.rules.quality_axis("z", "axis"))

    def test_quality_axis_rejects_unknown_axis(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be one of x, y, z"):
            self.rules.quality_axis("w", "axis")

    def test_quality_tolerance_uses_default(self) -> None:
        self.assertEqual(0.02, self.rules.quality_tolerance({}, default=0.02))

    def test_quality_tolerance_accepts_numeric_strings(self) -> None:
        self.assertEqual(
            0.125,
            self.rules.quality_tolerance({"tolerance": "0.125"}),
        )

    def test_quality_tolerance_rejects_invalid_or_out_of_range_values(self) -> None:
        with self.assertRaisesRegex(ValueError, "must be a number"):
            self.rules.quality_tolerance({"tolerance": "bad"})
        with self.assertRaisesRegex(ValueError, "between 0 and 1000000"):
            self.rules.quality_tolerance({"tolerance": -0.1})
        with self.assertRaisesRegex(ValueError, "between 0 and 1000000"):
            self.rules.quality_tolerance({"tolerance": 1000000.1})


class BlenderUvMathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.uv = load_uv_math()

    def test_triangle_area(self) -> None:
        self.assertEqual(
            0.5,
            self.uv.triangle_area_2d([(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]),
        )

    def test_overlap_area_matches_identical_triangle(self) -> None:
        triangle = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        self.assertAlmostEqual(
            0.5,
            self.uv.triangle_overlap_area_2d(triangle, triangle),
            places=12,
        )

    def test_overlap_area_is_zero_for_disjoint_triangles(self) -> None:
        first = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        second = [(2.0, 2.0), (3.0, 2.0), (2.0, 3.0)]
        self.assertAlmostEqual(
            0.0,
            self.uv.triangle_overlap_area_2d(first, second),
            places=12,
        )

    def test_overlap_is_orientation_independent(self) -> None:
        subject = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        clip_clockwise = [(0.0, 1.0), (1.0, 0.0), (0.0, 0.0)]
        self.assertAlmostEqual(
            0.5,
            self.uv.triangle_overlap_area_2d(subject, clip_clockwise),
            places=12,
        )


    def test_shape_distortion_is_zero_for_uniform_uv_scale(self) -> None:
        geometry = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)]
        uv = [(0.0, 0.0), (5.0, 0.0), (0.0, 5.0)]
        self.assertAlmostEqual(
            0.0,
            self.uv.triangle_shape_distortion(geometry, uv, 1e-12),
            places=12,
        )

    def test_shape_distortion_detects_changed_edge_proportions(self) -> None:
        geometry = [(0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.0, 2.0, 0.0)]
        uv = [(0.0, 0.0), (4.0, 0.0), (0.0, 1.0)]
        distortion = self.uv.triangle_shape_distortion(
            geometry,
            uv,
            1e-12,
        )
        self.assertIsNotNone(distortion)
        self.assertGreater(distortion, 0.1)

    def test_shape_distortion_returns_none_for_degenerate_triangle(self) -> None:
        geometry = [(0.0, 0.0, 0.0)] * 3
        uv = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0)]
        self.assertIsNone(
            self.uv.triangle_shape_distortion(geometry, uv, 1e-12)
        )


if __name__ == "__main__":
    unittest.main()
