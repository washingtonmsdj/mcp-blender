import tempfile
import unittest
from pathlib import Path

from ordax_dev_agent.unity_assets import asset_inventory


class UnityAssetInventoryTests(unittest.TestCase):
    def test_inventory_finds_imported_asset_paths(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            (root/"Assets"/"Pure Nature 2"/"Islands"/"Prefabs").mkdir(parents=True)
            (root/"Assets"/"Pure Nature 2"/"Islands"/"Prefabs"/"Palm.prefab").write_text("x",encoding="utf-8")
            (root/"Assets"/"Other.mat").write_text("x",encoding="utf-8")
            report=asset_inventory(root,terms=["pure nature","islands"])
            self.assertEqual(1,report["matched_files"])
            self.assertEqual("prefab",report["matches"][0]["kind"])
            self.assertIn("Pure Nature 2",report["matches"][0]["path"])

    def test_inventory_ignores_meta_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            (root/"Assets").mkdir()
            (root/"Assets"/"Tree.prefab").write_text("x",encoding="utf-8")
            (root/"Assets"/"Tree.prefab.meta").write_text("m",encoding="utf-8")
            report=asset_inventory(root)
            self.assertEqual(1,report["total_files"])


if __name__=="__main__":
    unittest.main()
