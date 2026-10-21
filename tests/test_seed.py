import re
import sqlite3
import tempfile
import unittest
from pathlib import Path

from odi_agent import seed

TABLES = ["SNP_SESSION", "SNP_SESS_STEP", "SNP_STEP_LOG", "DEMO_STEP_INFO", "DEMO_RESOLUTION"]


class SeedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)
        cls.conn = sqlite3.connect(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def query(self, sql):
        return self.conn.execute(sql).fetchall()

    def test_step_log_has_session(self):
        orphans = self.query("""
            SELECT l.SESS_NO FROM SNP_STEP_LOG l
            LEFT JOIN SNP_SESSION s ON s.SESS_NO = l.SESS_NO
            WHERE s.SESS_NO IS NULL""")
        self.assertEqual(orphans, [])

    def test_error_sessions_have_rc_and_message(self):
        errors = self.query("SELECT SESS_RC, SESS_MESS FROM SNP_SESSION WHERE SESS_STATUS = 'E'")
        self.assertTrue(errors)
        for rc, mess in errors:
            self.assertTrue(rc)
            self.assertTrue(mess)

    def test_failed_incremental_append_step_exists(self):
        rows = self.query("""
            SELECT 1 FROM SNP_STEP_LOG l
            JOIN SNP_SESS_STEP st ON st.SESS_NO = l.SESS_NO AND st.NNO = l.NNO
            JOIN DEMO_STEP_INFO i ON i.STEP_NAME = st.STEP_NAME
            WHERE l.STEP_STATUS = 'E' AND i.LOAD_TYPE = 'INCREMENTAL_APPEND'""")
        self.assertTrue(rows)

    def test_same_seed_gives_same_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            other_path = Path(tmp) / "other.db"
            seed.build(other_path)
            other = sqlite3.connect(other_path)
            try:
                for table in TABLES:
                    sql = f"SELECT * FROM {table} ORDER BY 1, 2"
                    self.assertEqual(self.query(sql), other.execute(sql).fetchall(), table)
            finally:
                other.close()

    def test_same_error_code_has_different_resolution_per_step(self):
        # Ajanın asıl değeri: aynı hata kodu, adıma göre farklı renk ve çözüm alır.
        rows = self.query("""
            SELECT r.ERROR_PATTERN, st.STEP_NAME, r.RENK, r.COZUM_NOTU
            FROM DEMO_RESOLUTION r
            JOIN SNP_SESS_STEP st ON st.SESS_NO = r.SESS_NO AND st.NNO = r.NNO""")
        for code in ("ORA-12801", "ORA-00054"):
            with self.subTest(code=code):
                matches = [r for r in rows if r[0] == code]
                has_contrast = any(
                    a[1] != b[1] and a[2] != b[2] and a[3] != b[3]
                    for a in matches for b in matches
                )
                self.assertTrue(has_contrast, f"{code} için farklı adım/renk/çözüm yok")

    def test_resolution_person_and_date(self):
        rows = self.query("""
            SELECT r.COZEN_KISI, r.COZUM_TARIHI, s.SESS_END
            FROM DEMO_RESOLUTION r JOIN SNP_SESSION s ON s.SESS_NO = r.SESS_NO""")
        self.assertTrue(rows)
        for person, fixed_at, sess_end in rows:
            self.assertTrue(person)
            self.assertTrue(fixed_at)
            self.assertGreaterEqual(fixed_at, sess_end)  # aynı metin biçimi, sıralama tutarlı

    def test_wrapper_messages_cover_all_cause_types(self):
        messages = [r[0] for r in self.query(
            "SELECT STEP_MESS FROM SNP_STEP_LOG WHERE STEP_MESS LIKE 'ORA-12801%'")]
        causes = {m.split("\n")[1].split(":")[0] if "\n" in m else None for m in messages}
        self.assertIn("ORA-00060", causes)  # geçici: restart çözer
        self.assertIn("ORA-01652", causes)  # kalıcı: restart çözmez
        self.assertIn(None, causes)         # asıl sebep satırı yok

    def test_no_invented_error_codes(self):
        # Mesajlardaki her ORA kodu seed.py'deki bilinen Oracle mesajlarından gelmeli.
        known = set(seed.ORA_MESSAGES)
        for (mess,) in self.query("SELECT STEP_MESS FROM SNP_STEP_LOG WHERE STEP_MESS IS NOT NULL"):
            for code in re.findall(r"ORA-\d{5}", mess):
                self.assertIn(code, known)

    def test_identifiers_are_ascii(self):
        tables = [r[0] for r in self.query("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            self.assertTrue(table.isascii(), table)
            for col in self.query(f"PRAGMA table_info({table})"):
                self.assertTrue(col[1].isascii(), f"{table}.{col[1]}")


if __name__ == "__main__":
    unittest.main()
