import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.blender_live_bridge import (
    blender_companion_bundle_fingerprint,
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
            ],
            manifest["files"],
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
