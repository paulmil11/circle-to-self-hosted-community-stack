from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IMPORTER = ROOT / "scripts" / "import_circle.py"
AUDITOR = ROOT / "scripts" / "audit_import.py"
EXPORTER = ROOT / "scripts" / "export_d1_sql.py"
SCHEMA = ROOT / "schema" / "community.sql"
FIXTURE = ROOT / "examples" / "circle-export"


class MigrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = Path(tempfile.mkdtemp(prefix="community-migration-test-"))
        self.export_dir = self.tempdir / "circle-export"
        shutil.copytree(FIXTURE, self.export_dir)
        self.db = self.tempdir / "community.sqlite"
        self.report = self.tempdir / "report.json"

    def tearDown(self) -> None:
        shutil.rmtree(self.tempdir)

    def run_import(self, reset: bool = False) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(IMPORTER),
            "--export-dir",
            str(self.export_dir),
            "--db",
            str(self.db),
            "--community-key",
            "example-community",
            "--report",
            str(self.report),
        ]
        if reset:
            command.append("--reset")
        return subprocess.run(command, check=True, text=True, capture_output=True)

    def test_import_preserves_raw_rows_and_normalizes_members(self) -> None:
        self.run_import(reset=True)
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        try:
            self.assertEqual(conn.execute("select count(*) from circle_raw_members").fetchone()[0], 3)
            self.assertEqual(conn.execute("select count(*) from members").fetchone()[0], 2)
            self.assertEqual(conn.execute("select count(*) from circle_spaces").fetchone()[0], 2)
            self.assertEqual(conn.execute("select count(*) from member_space_access").fetchone()[0], 3)

            avery = conn.execute(
                "select * from members where email = 'avery@example.test'"
            ).fetchone()
            robin = conn.execute(
                "select * from members where email = 'robin@example.test'"
            ).fetchone()
            self.assertEqual(avery["headline"], "Independent researcher")
            self.assertEqual(avery["lifecycle_status"], "lifetime")
            self.assertEqual(robin["lifecycle_status"], "cancelled")

            avery_spaces = [
                row[0]
                for row in conn.execute(
                    """
                    select s.name
                    from member_space_access msa
                    join circle_spaces s on s.circle_space_id = msa.circle_space_id
                    where msa.member_id = ?
                    order by s.name
                    """,
                    (avery["id"],),
                )
            ]
            self.assertEqual(avery_spaces, ["Introductions", "Resources, Videos & Links"])

            raw = json.loads(
                conn.execute(
                    "select raw_json from circle_raw_members where email = 'avery@example.test'"
                ).fetchone()[0]
            )
            self.assertEqual(raw["Headline"], "Old headline")
            self.assertEqual(raw["Headline__2"], "Independent researcher")

            self.assertEqual(
                conn.execute(
                    "select count(*) from member_entitlements where member_id = ?",
                    (avery["id"],),
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "select count(*) from member_entitlements where member_id = ?",
                    (robin["id"],),
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                conn.execute(
                    "select pause_all from member_email_preferences where member_id = ?",
                    (robin["id"],),
                ).fetchone()[0],
                1,
            )
        finally:
            conn.close()

        report = json.loads(self.report.read_text(encoding="utf-8"))
        self.assertEqual(report["warnings"]["missing_email_rows"], 1)
        self.assertEqual(report["warnings"]["duplicate_normalized_emails"], 0)

    def test_reimport_does_not_overwrite_confirmed_profile(self) -> None:
        self.run_import(reset=True)
        conn = sqlite3.connect(self.db)
        member_id = conn.execute(
            "select id from members where email = 'avery@example.test'"
        ).fetchone()[0]
        conn.execute(
            """
            update member_profiles
            set headline = 'Member-confirmed headline', confirmed_at = datetime('now')
            where member_id = ?
            """,
            (member_id,),
        )
        conn.commit()
        conn.close()

        self.run_import(reset=False)
        conn = sqlite3.connect(self.db)
        try:
            headline = conn.execute(
                "select headline from member_profiles where member_id = ?", (member_id,)
            ).fetchone()[0]
            self.assertEqual(headline, "Member-confirmed headline")
            self.assertEqual(conn.execute("select count(*) from circle_import_batches").fetchone()[0], 1)
            self.assertEqual(conn.execute("select count(*) from circle_raw_members").fetchone()[0], 3)
        finally:
            conn.close()

    def test_audit_and_normalized_d1_export(self) -> None:
        self.run_import(reset=True)
        audit = subprocess.run(
            [sys.executable, str(AUDITOR), "--db", str(self.db)],
            check=True,
            text=True,
            capture_output=True,
        )
        self.assertIn("foreign_key_violations: 0", audit.stdout)

        sql_out = self.tempdir / "d1.sql"
        subprocess.run(
            [sys.executable, str(EXPORTER), "--db", str(self.db), "--out", str(sql_out)],
            check=True,
            text=True,
            capture_output=True,
        )
        sql = sql_out.read_text(encoding="utf-8")
        self.assertIn('INSERT OR IGNORE INTO "members"', sql)
        self.assertNotIn('INTO "circle_raw_members"', sql)
        self.assertNotIn("This row is preserved but cannot become a member", sql)

        destination = sqlite3.connect(self.tempdir / "destination.sqlite")
        try:
            destination.executescript(SCHEMA.read_text(encoding="utf-8"))
            destination.executescript(sql)
            self.assertEqual(destination.execute("select count(*) from members").fetchone()[0], 2)
            self.assertEqual(destination.execute("pragma foreign_key_check").fetchall(), [])
        finally:
            destination.close()


if __name__ == "__main__":
    unittest.main()
