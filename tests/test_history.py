import tempfile
import unittest
from pathlib import Path

from odi_agent import seed
from odi_agent.classifier import hatalari_sinifla
from odi_agent.db import connect_readonly
from odi_agent.history import (FARKLI_ADIM_UYARISI, FARKLI_SEBEP_UYARISI,
                               SEBEP_BILINMIYOR_NOTU, gecmis_benzerler)
from odi_agent.schema_map import Resolution

ADIM = "MAP_FACT_SIPARIS_DEMO"


class HistoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)
        cls.conn = connect_readonly(cls.db_path)
        cls.result = gecmis_benzerler(cls.conn, "ORA-12801", ADIM, asil_sebep="ORA-00060")

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def all_items(self, result=None):
        result = result or self.result
        return result.ayni_adim + result.farkli_sebep + result.farkli_adim

    # Asıl sebebe göre gruplama

    def test_same_step_same_cause(self):
        self.assertEqual(len(self.result.ayni_adim), 2)
        for item in self.result.ayni_adim:
            self.assertEqual(item.adim, ADIM)
            self.assertEqual(item.asil_sebep, "ORA-00060")
            self.assertEqual(item.uyarilar, [])

    def test_same_step_different_cause_separated(self):
        self.assertEqual(len(self.result.farkli_sebep), 2)
        for item in self.result.farkli_sebep:
            self.assertEqual(item.adim, ADIM)
            self.assertEqual(item.asil_sebep, "ORA-01652")
            self.assertEqual(item.uyarilar, [FARKLI_SEBEP_UYARISI])

    def test_reverse_cause_query(self):
        result = gecmis_benzerler(self.conn, "ORA-12801", ADIM, asil_sebep="ORA-01652")
        self.assertEqual({i.asil_sebep for i in result.ayni_adim}, {"ORA-01652"})
        self.assertEqual({i.asil_sebep for i in result.farkli_sebep}, {"ORA-00060"})

    def test_other_step_and_other_cause_gets_both_warnings(self):
        stok = [i for i in self.result.farkli_adim if i.adim == "MAP_AGG_STOK_DEMO"]
        self.assertTrue(stok)
        for item in stok:
            self.assertEqual(item.uyarilar, [FARKLI_ADIM_UYARISI, FARKLI_SEBEP_UYARISI])

    def test_other_step_same_cause_gets_only_step_warning(self):
        agg = [i for i in self.result.farkli_adim if i.adim == "MAP_AGG_SIPARIS_GUNLUK_DEMO"]
        self.assertTrue(agg)
        for item in agg:
            self.assertEqual(item.renk, "YESIL")
            self.assertEqual(item.uyarilar, [FARKLI_ADIM_UYARISI])

    def test_unknown_current_cause_keeps_groups_and_notes(self):
        result = gecmis_benzerler(self.conn, "ORA-12801", ADIM)
        self.assertEqual(result.farkli_sebep, [])
        self.assertEqual(len(result.ayni_adim), 4)
        for item in self.all_items(result):
            self.assertIn(SEBEP_BILINMIYOR_NOTU, item.uyarilar)

    def test_non_wrapper_has_no_cause_warnings(self):
        result = gecmis_benzerler(self.conn, "ORA-00054", "MAP_DIM_MUSTERI_DEMO")
        self.assertEqual(result.farkli_sebep, [])
        self.assertTrue(result.ayni_adim)
        for item in self.all_items(result):
            self.assertNotIn(FARKLI_SEBEP_UYARISI, item.uyarilar)
            self.assertNotIn(SEBEP_BILINMIYOR_NOTU, item.uyarilar)

    def test_cause_matches_classifier(self):
        # Sınıflayıcı ile geçmiş eşleştirme aynı fonksiyonu kullanıyor; asıl sebepte ayrışmamalı.
        classified = {s.sess_no: s.asil_sebep for s in hatalari_sinifla(self.conn)}
        codes = [c for (c,) in self.conn.execute(
            f"SELECT DISTINCT {Resolution.ERROR_PATTERN} FROM {Resolution.TABLE}")]
        checked = 0
        for code in codes:
            for item in self.all_items(gecmis_benzerler(self.conn, code, "OLMAYAN_ADIM")):
                self.assertEqual(item.asil_sebep, classified[item.sess_no], f"oturum {item.sess_no}")
                checked += 1
        self.assertEqual(checked, 22)

    # Genel davranış

    def test_every_item_has_person_date_and_note(self):
        for item in self.all_items():
            self.assertTrue(item.cozen_kisi)
            self.assertTrue(item.cozum_tarihi)
            self.assertTrue(item.cozum_notu)

    def test_groups_are_disjoint(self):
        groups = [{i.sess_no for i in g} for g in
                  (self.result.ayni_adim, self.result.farkli_sebep, self.result.farkli_adim)]
        self.assertFalse(groups[0] & groups[1])
        self.assertFalse(groups[0] & groups[2])
        self.assertFalse(groups[1] & groups[2])

    def test_code_must_match_exactly(self):
        result = gecmis_benzerler(self.conn, "ORA-00054", ADIM)
        twelve_801 = {i.sess_no for i in self.all_items()}
        self.assertTrue(self.all_items(result))
        self.assertFalse({i.sess_no for i in self.all_items(result)} & twelve_801)

    def test_unknown_code_returns_empty_groups(self):
        result = gecmis_benzerler(self.conn, "ORA-99999", ADIM)
        self.assertEqual(self.all_items(result), [])

    def test_excluded_session_not_returned(self):
        excluded = self.result.ayni_adim[0].sess_no
        result = gecmis_benzerler(self.conn, "ORA-12801", ADIM, asil_sebep="ORA-00060",
                                  haric_sess_no=excluded)
        self.assertNotIn(excluded, {i.sess_no for i in self.all_items(result)})
        self.assertEqual(len(self.all_items(result)), len(self.all_items()) - 1)

    def test_newest_first(self):
        for group in (self.result.ayni_adim, self.result.farkli_sebep, self.result.farkli_adim):
            dates = [i.cozum_tarihi for i in group]
            self.assertEqual(dates, sorted(dates, reverse=True))


if __name__ == "__main__":
    unittest.main()
