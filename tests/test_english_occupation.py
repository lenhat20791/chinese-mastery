import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import database
import userdb


class EnglishOccupationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.source = Path(self.tmp.name) / "english_test.db"
        conn = sqlite3.connect(self.source)
        conn.execute("""
            CREATE TABLE vocab (
                id INTEGER PRIMARY KEY,
                hanzi TEXT NOT NULL,
                meaning_vi TEXT,
                domain TEXT,
                hsk_level TEXT,
                study_day INTEGER,
                stage_10d INTEGER,
                priority_group INTEGER
            )
        """)
        conn.executemany(
            "INSERT INTO vocab VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (1, "office", "", "OFFICE", "A2", 1, 1, 1),
                (2, "teacher-a2", "", "TEACHER", "A2", 1, 1, 2),
                (3, "general-a2", "", "GENERAL", "A2", 2, 1, 4),
                (4, "teacher-b2", "", "TEACHER", "B2", 3, 1, 2),
                (5, "office-c1", "", "OFFICE", "C1", 3, 1, 1),
                (6, "general-c1", "", "GENERAL", "C1", 4, 1, 4),
            ],
        )
        conn.commit()
        conn.close()
        self.config_patch = mock.patch.object(
            database, "get_config",
            return_value={"db_path": str(self.source), "words_per_day": 2},
        )
        self.config_patch.start()

    def tearDown(self):
        self.config_patch.stop()
        self.tmp.cleanup()

    def test_occupation_variant_filters_and_reindexes_words(self):
        variant = database.variant_key("en", occupation="TEACHER")
        self.assertEqual(variant, "en::TEACHER")
        conn = sqlite3.connect(database.vocab_db_path(variant))
        rows = conn.execute("SELECT id, domain, study_day FROM vocab ORDER BY study_day, id").fetchall()
        conn.close()
        self.assertEqual([row[0] for row in rows], [2, 3, 4, 6])
        self.assertEqual([row[1] for row in rows], ["TEACHER", "GENERAL", "TEACHER", "GENERAL"])
        self.assertEqual([row[2] for row in rows], [1, 1, 2, 2])

    def test_level_and_occupation_filters_are_combined(self):
        variant = database.variant_key("en", "B1", "TEACHER")
        conn = sqlite3.connect(database.vocab_db_path(variant))
        rows = conn.execute("SELECT id, domain FROM vocab ORDER BY id").fetchall()
        conn.close()
        self.assertEqual(rows, [(4, "TEACHER"), (6, "GENERAL")])

    def test_changing_occupation_resets_to_unlearned_role_vocabulary(self):
        user_path = Path(self.tmp.name) / "user.db"
        with mock.patch.object(userdb, "LOCAL_USER_DB", str(user_path)), \
                mock.patch.object(userdb, "_turso_config", return_value=None):
            userdb.init_schema()
            profile_id = database.create_profile(1, "en", "B1", "OFFICE")
            userdb.get_user_db().execute(
                "UPDATE user_progress SET current_day = 3 WHERE user_id = ?", (profile_id,)
            )
            next_day = database.change_profile_occupation(profile_id, "TEACHER")
            profile = userdb.get_user_db().execute(
                "SELECT occupation FROM profiles WHERE id = ?", (profile_id,)
            ).fetchone()
        self.assertEqual(profile[0], "TEACHER")
        self.assertEqual(next_day, 1)


class ProfileOccupationMigrationTests(unittest.TestCase):
    def test_existing_profiles_default_to_office_occupation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "user.db"
            conn = sqlite3.connect(path)
            conn.execute("""
                CREATE TABLE profiles (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    course TEXT NOT NULL,
                    level TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, course)
                )
            """)
            conn.execute("INSERT INTO profiles (id, user_id, course, level) VALUES (10, 1, 'en', 'B1')")
            conn.execute("INSERT INTO profiles (id, user_id, course, level) VALUES (11, 1, 'zh', NULL)")
            conn.commit()
            conn.close()
            with mock.patch.object(userdb, "LOCAL_USER_DB", str(path)), \
                    mock.patch.object(userdb, "_turso_config", return_value=None):
                userdb.init_schema()
                conn = userdb.get_user_db()
                profile = conn.execute("SELECT occupation FROM profiles WHERE id = 10").fetchone()
                chinese_profile = conn.execute("SELECT occupation FROM profiles WHERE id = 11").fetchone()
                conn.close()
            self.assertEqual(profile[0], "OFFICE")
            self.assertIsNone(chinese_profile[0])


if __name__ == "__main__":
    unittest.main()
