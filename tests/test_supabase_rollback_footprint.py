from pathlib import Path
import unittest


class SupabaseRollbackFootprintTests(unittest.TestCase):
    def test_only_device_setup_v2_migration_remains(self) -> None:
        root = Path(__file__).resolve().parents[1]
        supabase = root / "control-plane" / "supabase"

        for obsolete in (
            "002_agent_pairing_and_artifacts.sql",
            "003_job_dependencies.sql",
            "004_agent_presence_expiry.sql",
        ):
            self.assertFalse((supabase / obsolete).exists())

        self.assertTrue(
            (
                supabase
                / "functions"
                / "ordax-device-setup"
                / "index.ts"
            ).is_file()
        )
        self.assertTrue(
            (
                supabase
                / "migrations"
                / "20260925203914_device_user_setup.sql"
            ).is_file()
        )

    def test_legacy_tables_are_not_reintroduced_in_remaining_sql(self) -> None:
        root = Path(__file__).resolve().parents[1]
        supabase = root / "control-plane" / "supabase"
        remaining = "\n".join(
            path.read_text(encoding="utf-8")
            for path in supabase.rglob("*.sql")
        )
        self.assertNotIn("ordax_dev_agents", remaining)
        self.assertNotIn("ordax_dev_jobs", remaining)
        self.assertNotIn("ordax_dev_pairing_tokens", remaining)


if __name__ == "__main__":
    unittest.main()
