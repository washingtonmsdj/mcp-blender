import unittest
from pathlib import Path


class CloudflareDeployScriptTests(unittest.TestCase):
    def test_first_deploy_uploads_secret_with_code(self) -> None:
        root = Path(__file__).resolve().parents[1]
        script = (root / "scripts" / "cloudflare" / "deploy-v3.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn('--secrets-file "$SECRETS_FILE"', script)
        self.assertIn('ORDAX_OPERATOR_TOKEN', script)
        self.assertIn('trap cleanup EXIT', script)
        self.assertIn('target.chmod(0o600)', script)
        self.assertNotIn('wrangler secret put', script)

        migration_index = script.index("d1 migrations apply")
        deploy_index = script.index('wrangler deploy --config "$GENERATED_CONFIG"')
        self.assertLess(migration_index, deploy_index)


if __name__ == "__main__":
    unittest.main()
