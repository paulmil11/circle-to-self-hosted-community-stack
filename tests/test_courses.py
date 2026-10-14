from __future__ import annotations

import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "schema/community.sql").read_text(encoding="utf-8")
COURSES = (ROOT / "schema/courses.sql").read_text(encoding="utf-8")
SEED = (ROOT / "examples/course-portal/seed.sql").read_text(encoding="utf-8")


class CourseSchemaTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "courses.sqlite"
        self.db = sqlite3.connect(self.db_path)
        self.db.executescript(BASE + COURSES + SEED)
        self.db.execute("INSERT INTO members (id,email,display_name) VALUES ('demo','demo@example.test','Demo Learner')")
        self.db.execute("INSERT INTO course_notes (member_id,lesson_id,prompt_key,answer_text) VALUES ('demo','choose-an-experiment','reflection','Private synthetic answer')")
        self.db.execute("INSERT INTO course_progress (member_id,lesson_id,position_seconds) VALUES ('demo','choose-an-experiment',12)")
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.temp.cleanup()

    def test_seed_is_repeatable_and_preserves_answers(self) -> None:
        self.db.executescript(COURSES + SEED)
        self.assertEqual(self.db.execute("SELECT count(*) FROM course_lessons").fetchone()[0], 2)
        self.assertEqual(self.db.execute("SELECT answer_text FROM course_notes").fetchone()[0], "Private synthetic answer")

    def test_lesson_cannot_use_another_courses_module(self) -> None:
        self.db.execute("INSERT INTO courses (id,slug,title,entitlement_key) VALUES ('other','other','Other','course:other')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("INSERT INTO course_lessons (id,course_id,module_id,title,kind,position) VALUES ('bad','other','getting-started','Bad','text',2)")

    def test_member_deletion_removes_notes_and_progress_but_keeps_curriculum(self) -> None:
        self.db.execute("DELETE FROM members WHERE id='demo'")
        self.assertEqual(self.db.execute("SELECT count(*) FROM course_notes").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM course_progress").fetchone()[0], 0)
        self.assertEqual(self.db.execute("SELECT count(*) FROM course_lessons").fetchone()[0], 2)

    def test_course_export_is_explicit_and_restores_with_foreign_keys(self) -> None:
        for include in (False, True):
            with self.subTest(include_courses=include):
                output = Path(self.temp.name) / "export.sql"
                command = [sys.executable, str(ROOT / "scripts/export_d1_sql.py"), "--db", str(self.db_path), "--out", str(output)]
                if include:
                    command.append("--include-courses")
                subprocess.run(command, check=True, capture_output=True, text=True)
                sql = output.read_text(encoding="utf-8")
                self.assertEqual("Private synthetic answer" in sql, include)
                restored = sqlite3.connect(":memory:")
                try:
                    restored.executescript(BASE + COURSES)
                    restored.executescript(sql)
                    self.assertEqual(restored.execute("SELECT count(*) FROM course_notes").fetchone()[0], int(include))
                    self.assertEqual(restored.execute("SELECT count(*) FROM course_progress").fetchone()[0], int(include))
                    self.assertEqual(restored.execute("PRAGMA foreign_key_check").fetchall(), [])
                finally:
                    restored.close()


if __name__ == "__main__":
    unittest.main()
