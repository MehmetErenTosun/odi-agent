import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from odi_agent import seed
from odi_agent.classifier import RulesError, classify, hatalari_sinifla, load_rules, validate_rules
from odi_agent.db import connect_readonly
from odi_agent.schema_map import Resolution, Session

MESAJ = "ORA-{}: demo mesaj"
SARMALAYICI = "ORA-12801: error signaled in parallel query server P003"
DEADLOCK = "ORA-00060: deadlock detected while waiting for resource"
TEMP = "ORA-01652: unable to extend temp segment by 128 in tablespace TEMP"
SATIR = "ORA-06512: at line 5"
KILIT = "ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired"


def mesaj(*lines):
    return "\n".join(lines)


class ClassifierDbTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)
        cls.conn = connect_readonly(cls.db_path)
        cls.rules = load_rules()
        cls.results = hatalari_sinifla(cls.conn, cls.rules)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def find(self, step, code):
        found = [r for r in self.results if r.adim == step and r.hata_kodu == code]
        self.assertTrue(found, f"{step} / {code} bulunamadı")
        return found

    def test_only_error_sessions(self):
        expected = self.conn.execute(
            f"SELECT COUNT(*) FROM {Session.TABLE} WHERE {Session.STATUS} = 'E'").fetchone()[0]
        self.assertEqual(expected, 25)
        self.assertEqual(len(self.results), expected)

    def test_open_case_incremental_append_capped(self):
        for r in self.find("MAP_FACT_SIPARIS_DEMO", "ORA-12801"):
            if r.asil_sebep != "ORA-00060":
                continue  # aynı adımda ORA-01652 sebepli geçmiş kayıtlar da var
            self.assertEqual(r.renk, "TURUNCU")
            self.assertEqual(r.asil_sebep, "ORA-00060")
            self.assertEqual(len(r.gerekce), 3)  # sarmalayıcı + asıl sebep kuralı + tavan
            self.assertIn("asıl sebep ORA-00060", r.gerekce[0])
            self.assertIn("ORA-00060 kuralı: YESIL", r.gerekce[1])
            self.assertIn("INCREMENTAL_APPEND", r.gerekce[2])

    def test_open_case_wrapper_without_cause(self):
        for r in self.find("MAP_AGG_ODEME_DEMO", "ORA-12801"):
            self.assertEqual(r.yukleme_tipi, "FULL_RELOAD")  # tavan devrede değil
            self.assertIsNone(r.asil_sebep)
            self.assertEqual(r.renk, "TURUNCU")
            self.assertIn("asıl sebep bulunamadı", r.gerekce[0])

    def test_wrapper_without_cause_never_green(self):
        wrappers = set(self.rules["sarmalayici_kodlar"])
        for r in self.results:
            if r.hata_kodu in wrappers and r.asil_sebep is None:
                self.assertNotEqual(r.renk, "YESIL", f"oturum {r.sess_no}")

    def test_open_case_green_with_retry_limit(self):
        for r in self.find("MAP_DIM_MUSTERI_DEMO", "ORA-00054"):
            self.assertEqual(r.renk, "YESIL")
            self.assertEqual(r.max_deneme, 3)

    def test_step_exception(self):
        for r in self.find("MAP_FACT_STOK_HAREKET_DEMO", "ORA-00054"):
            self.assertEqual(r.renk, "KIRMIZI")
            self.assertIn("Adım istisnası", r.gerekce[0])

    def test_non_green_has_no_retry_limit(self):
        for r in self.results:
            if r.renk != "YESIL":
                self.assertIsNone(r.max_deneme)

    def test_matches_historical_colors(self):
        # rules.json ile örnek veri tutarlı: geçmişte verilen renkler yeniden üretilmeli.
        history = dict(self.conn.execute(
            f"SELECT {Resolution.SESS_NO}, {Resolution.COLOR} FROM {Resolution.TABLE}").fetchall())
        self.assertEqual(len(history), 22)
        for r in self.results:
            if r.sess_no in history:
                self.assertEqual(r.renk, history[r.sess_no], f"oturum {r.sess_no}")

    def test_rules_come_from_file(self):
        changed = copy.deepcopy(self.rules)
        changed["hata_kodlari"]["ORA-00942"] = "TURUNCU"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "rules.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            results = hatalari_sinifla(self.conn, load_rules(path))
        colors = {r.renk for r in results if r.hata_kodu == "ORA-00942"}
        self.assertEqual(colors, {"TURUNCU"})

    def test_connection_is_readonly(self):
        with self.assertRaises(sqlite3.OperationalError):
            self.conn.execute(f"DELETE FROM {Session.TABLE}")


class ClassifyRuleTest(unittest.TestCase):
    """Veritabanı gerektirmeyen kural testleri."""

    def setUp(self):
        self.rules = load_rules()

    def test_unknown_code_defaults_to_red(self):
        r = classify(1, 1, "MAP_DIM_URUN_DEMO", MESAJ.format("99999"), "MERGE", self.rules)
        self.assertEqual(r.renk, "KIRMIZI")

    def test_message_without_ora_code_defaults_to_red(self):
        r = classify(1, 1, "MAP_DIM_URUN_DEMO", "beklenmeyen hata", "MERGE", self.rules)
        self.assertIsNone(r.hata_kodu)
        self.assertEqual(r.renk, "KIRMIZI")

    def test_green_exception_still_capped_on_incremental_append(self):
        self.rules["adim_istisnalari"].append({
            "adim": "MAP_FACT_ODEME_DEMO", "hata_kodu": "ORA-00001",
            "renk": "YESIL", "neden": "test"})
        r = classify(1, 1, "MAP_FACT_ODEME_DEMO", MESAJ.format("00001"),
                     "INCREMENTAL_APPEND", self.rules)
        self.assertEqual(r.renk, "TURUNCU")

    def test_unknown_load_type_is_not_green(self):
        r = classify(1, 1, "MAP_BILINMEYEN_DEMO", MESAJ.format("12801"), None, self.rules)
        self.assertEqual(r.renk, "TURUNCU")

    def test_missing_incremental_append_cap_rejected(self):
        del self.rules["yukleme_tipi_tavani"]["INCREMENTAL_APPEND"]
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    def test_green_incremental_append_cap_rejected(self):
        self.rules["yukleme_tipi_tavani"]["INCREMENTAL_APPEND"] = "YESIL"
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    def test_invalid_color_rejected(self):
        self.rules["hata_kodlari"]["ORA-00060"] = "MAVI"
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    # Sarmalayıcı (wrapper) hata kodları

    def classify_msg(self, message, load_type="FULL_RELOAD", step="MAP_AGG_SIPARIS_GUNLUK_DEMO"):
        return classify(1, 1, step, message, load_type, self.rules)

    def test_wrapper_with_transient_cause_is_green(self):
        r = self.classify_msg(mesaj(SARMALAYICI, DEADLOCK))
        self.assertEqual(r.hata_kodu, "ORA-12801")
        self.assertEqual(r.asil_sebep, "ORA-00060")
        self.assertEqual(r.renk, "YESIL")
        self.assertIn("ORA-12801 sarmalayıcı; asıl sebep ORA-00060", r.gerekce[0])

    def test_wrapper_with_transient_cause_still_capped(self):
        r = self.classify_msg(mesaj(SARMALAYICI, DEADLOCK), load_type="INCREMENTAL_APPEND")
        self.assertEqual(r.renk, "TURUNCU")

    def test_wrapper_with_permanent_cause(self):
        r = self.classify_msg(mesaj(SARMALAYICI, TEMP))
        self.assertEqual(r.asil_sebep, "ORA-01652")
        self.assertEqual(r.renk, "TURUNCU")

    def test_wrapper_without_cause_is_not_green(self):
        r = self.classify_msg(SARMALAYICI)
        self.assertIsNone(r.asil_sebep)
        self.assertEqual(r.renk, "TURUNCU")

    def test_wrapper_own_green_rule_is_ignored(self):
        self.rules["hata_kodlari"]["ORA-12801"] = "YESIL"
        r = self.classify_msg(SARMALAYICI)
        self.assertNotEqual(r.renk, "YESIL")

    def test_wrapper_with_cause_without_rule_defaults_to_red(self):
        r = self.classify_msg(mesaj(SARMALAYICI, "ORA-01722: invalid number"))
        self.assertEqual(r.asil_sebep, "ORA-01722")
        self.assertEqual(r.renk, "KIRMIZI")

    def test_nested_wrappers_skipped(self):
        r = self.classify_msg(mesaj(SARMALAYICI, SARMALAYICI, DEADLOCK))
        self.assertEqual(r.asil_sebep, "ORA-00060")
        self.assertEqual(r.renk, "YESIL")

    def test_step_exception_applies_to_cause(self):
        self.rules["adim_istisnalari"].append({
            "adim": "MAP_AGG_SIPARIS_GUNLUK_DEMO", "hata_kodu": "ORA-00060",
            "renk": "KIRMIZI", "neden": "test"})
        r = self.classify_msg(mesaj(SARMALAYICI, DEADLOCK))
        self.assertEqual(r.renk, "KIRMIZI")
        self.assertIn("Adım istisnası", r.gerekce[1])

    def test_multiline_non_wrapper_unchanged(self):
        r = self.classify_msg(mesaj(
            "ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired",
            "ORA-06512: at line 5"), step="MAP_DIM_MUSTERI_DEMO", load_type="MERGE")
        self.assertEqual(r.hata_kodu, "ORA-00054")
        self.assertIsNone(r.asil_sebep)
        self.assertEqual(r.renk, "YESIL")

    # Yoksayılan kodlar (ORA-06512: yalnızca satır bilgisi)

    def test_ignored_code_between_wrapper_and_cause(self):
        r = self.classify_msg(mesaj(SARMALAYICI, SATIR, DEADLOCK))
        self.assertEqual(r.asil_sebep, "ORA-00060")
        self.assertEqual(r.renk, "YESIL")

    def test_ignored_code_after_cause(self):
        r = self.classify_msg(mesaj(SARMALAYICI, DEADLOCK, SATIR))
        self.assertEqual(r.asil_sebep, "ORA-00060")

    def test_wrapper_with_only_ignored_code_has_no_cause(self):
        r = self.classify_msg(mesaj(SARMALAYICI, SATIR))
        self.assertIsNone(r.asil_sebep)
        self.assertEqual(r.renk, "TURUNCU")

    def test_ignored_code_before_permanent_cause(self):
        r = self.classify_msg(mesaj(SARMALAYICI, SATIR, TEMP))
        self.assertEqual(r.asil_sebep, "ORA-01652")
        self.assertEqual(r.renk, "TURUNCU")

    def test_ignored_code_first_in_message(self):
        r = self.classify_msg(mesaj(SATIR, KILIT), step="MAP_DIM_MUSTERI_DEMO", load_type="MERGE")
        self.assertEqual(r.hata_kodu, "ORA-00054")
        self.assertEqual(r.renk, "YESIL")

    def test_only_ignored_code_defaults_to_red(self):
        r = self.classify_msg(SATIR)
        self.assertIsNone(r.hata_kodu)
        self.assertEqual(r.renk, "KIRMIZI")

    def test_ignored_list_comes_from_rules(self):
        self.rules["yoksayilan_kodlar"] = []
        r = self.classify_msg(mesaj(SARMALAYICI, SATIR, DEADLOCK))
        self.assertEqual(r.asil_sebep, "ORA-06512")
        self.assertEqual(r.renk, "KIRMIZI")

    def test_missing_ignored_list_rejected(self):
        del self.rules["yoksayilan_kodlar"]
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    def test_code_in_both_lists_rejected(self):
        self.rules["yoksayilan_kodlar"].append("ORA-12801")
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    def test_green_fallback_for_missing_cause_rejected(self):
        self.rules["sebep_bulunamazsa_renk"] = "YESIL"
        with self.assertRaises(RulesError):
            validate_rules(self.rules)

    def test_missing_wrapper_list_rejected(self):
        del self.rules["sarmalayici_kodlar"]
        with self.assertRaises(RulesError):
            validate_rules(self.rules)


if __name__ == "__main__":
    unittest.main()
