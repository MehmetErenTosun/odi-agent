import importlib.util
import os
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path

from odi_agent import seed
from odi_agent.classifier import hatalari_sinifla, load_rules
from odi_agent.db import connect_readonly
from odi_agent.diagnostics import (DEMO_KAYNAK, DURUM_CALISTI, DURUM_YETKISIZ, YETKI_ENV,
                                   DemoCalistirici, sablonlari_yukle, yetkileri_yukle)
from odi_agent.history import SEBEP_BILINMIYOR_NOTU, FARKLI_SEBEP_UYARISI
from odi_agent.panel_data import (GRUPLAR, hata_listesi, oturum_detayi, renk_filtrele,
                                  teshis_sonuclari)
from odi_agent.schema_map import Resolution

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "odi_agent"
PANEL_FILE = PACKAGE_DIR / "panel.py"
HAS_STREAMLIT = importlib.util.find_spec("streamlit") is not None


class PanelDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)
        cls.conn = connect_readonly(cls.db_path)
        cls.rules = load_rules()
        cls.siniflamalar = hatalari_sinifla(cls.conn, cls.rules)
        cls.satirlar = hata_listesi(cls.conn, cls.rules)
        resolved = {r[0] for r in cls.conn.execute(f"SELECT {Resolution.SESS_NO} FROM {Resolution.TABLE}")}
        cls.open_sessions = [s for s in cls.siniflamalar if s.sess_no not in resolved]

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def open_case(self, adim):
        found = [s for s in self.open_sessions if s.adim == adim]
        self.assertEqual(len(found), 1, adim)
        return found[0]

    # Hata listesi

    def test_list_has_all_errors_with_fields(self):
        self.assertEqual(len(self.satirlar), 25)
        for r in self.satirlar:
            self.assertEqual(set(r), {"sess_no", "adim", "hata_kodu", "asil_sebep", "renk"})
            self.assertTrue(r["adim"])
            self.assertIn(r["renk"], ("KIRMIZI", "TURUNCU", "YESIL"))

    def test_list_matches_classifier(self):
        # Mantık panelde yeniden yazılmamış: renkler sınıflayıcıyla birebir aynı.
        expected = {s.sess_no: (s.adim, s.hata_kodu, s.asil_sebep, s.renk) for s in self.siniflamalar}
        for r in self.satirlar:
            self.assertEqual((r["adim"], r["hata_kodu"], r["asil_sebep"], r["renk"]),
                             expected[r["sess_no"]])

    def test_list_newest_first(self):
        numbers = [r["sess_no"] for r in self.satirlar]
        self.assertEqual(numbers, sorted(numbers, reverse=True))

    # Renk filtresi

    def test_filter_single_color(self):
        yesil = renk_filtrele(self.satirlar, ["YESIL"])
        self.assertTrue(yesil)
        self.assertTrue(all(r["renk"] == "YESIL" for r in yesil))

    def test_filter_two_colors(self):
        two = renk_filtrele(self.satirlar, ["KIRMIZI", "TURUNCU"])
        self.assertEqual({r["renk"] for r in two}, {"KIRMIZI", "TURUNCU"})
        self.assertEqual(len(two) + len(renk_filtrele(self.satirlar, ["YESIL"])), len(self.satirlar))

    def test_filter_none_means_all_and_empty_means_nothing(self):
        self.assertEqual(renk_filtrele(self.satirlar, None), self.satirlar)
        self.assertEqual(renk_filtrele(self.satirlar, []), [])

    # Oturum detayı

    def test_detail_of_open_incremental_append_case(self):
        s = next(x for x in self.open_sessions
                 if x.adim == "MAP_FACT_SIPARIS_DEMO" and x.asil_sebep == "ORA-00060")
        d = oturum_detayi(self.conn, s, self.rules)
        self.assertEqual(d["renk"], "TURUNCU")
        self.assertEqual(d["gerekce"], s.gerekce)
        self.assertEqual([len(d["gecmis"][g]) for g in GRUPLAR], [2, 2, 4])
        for item in d["gecmis"]["farkli_sebep"]:
            self.assertEqual(item["uyarilar"], [FARKLI_SEBEP_UYARISI])
        two_warnings = [i for i in d["gecmis"]["farkli_adim"] if len(i["uyarilar"]) == 2]
        self.assertEqual(len(two_warnings), 2)

    def test_max_deneme_only_for_green(self):
        seen = set()
        for s in self.siniflamalar:
            d = oturum_detayi(self.conn, s, self.rules)
            seen.add(d["renk"])
            if d["renk"] == "YESIL":
                self.assertEqual(d["max_deneme"], 3)
            else:
                self.assertIsNone(d["max_deneme"])
        self.assertEqual(seen, {"KIRMIZI", "TURUNCU", "YESIL"})

    def test_history_rows_have_person_date_and_note(self):
        for s in self.siniflamalar:
            d = oturum_detayi(self.conn, s, self.rules)
            for grup in GRUPLAR:
                for item in d["gecmis"][grup]:
                    self.assertTrue(item["cozen_kisi"])
                    self.assertTrue(item["cozum_tarihi"])
                    self.assertTrue(item["cozum_notu"])

    def test_selected_session_not_in_own_history(self):
        for s in self.siniflamalar:
            d = oturum_detayi(self.conn, s, self.rules)
            for grup in GRUPLAR:
                self.assertNotIn(s.sess_no, [i["sess_no"] for i in d["gecmis"][grup]])

    def test_wrapper_without_cause_case(self):
        s = self.open_case("MAP_AGG_ODEME_DEMO")
        d = oturum_detayi(self.conn, s, self.rules)
        self.assertIsNone(d["asil_sebep"])
        self.assertIn("asıl sebep bulunamadı", d["gerekce"][0])
        items = [i for g in GRUPLAR for i in d["gecmis"][g]]
        self.assertTrue(items)
        for item in items:
            self.assertIn(SEBEP_BILINMIYOR_NOTU, item["uyarilar"])

    # Teşhis

    def teshis(self, s):
        return teshis_sonuclari(s, sablonlari_yukle(), yetkileri_yukle(), DemoCalistirici(self.conn))

    def test_teshis_wrapper_with_deadlock_cause(self):
        s = next(x for x in self.open_sessions
                 if x.adim == "MAP_FACT_SIPARIS_DEMO" and x.asil_sebep == "ORA-00060")
        sonuclar = {r["ad"]: r for r in self.teshis(s)}
        self.assertEqual(set(sonuclar), {"kilit_durumu", "paralel_sunucu_kullanimi"})

        kilit = sonuclar["kilit_durumu"]
        self.assertEqual(kilit["durum"], DURUM_CALISTI)
        self.assertEqual(kilit["kaynak"], DEMO_KAYNAK)
        self.assertEqual(kilit["satirlar"], seed.DIAG_RESULTS["kilit_durumu"])
        self.assertEqual(kilit["yetkiler"], [{"ad": "SELECT ON V_$SESSION", "tanimli": True}])

        px = sonuclar["paralel_sunucu_kullanimi"]
        self.assertEqual(px["durum"], DURUM_YETKISIZ)
        self.assertEqual(px["satirlar"], [])
        self.assertIsNone(px["kaynak"])
        self.assertEqual(px["yetkiler"], [{"ad": "SELECT ON V_$PX_SESSION", "tanimli": False}])

    def test_teshis_none_for_unmatched_code(self):
        s = next(x for x in self.siniflamalar if x.hata_kodu == "ORA-00942")
        self.assertEqual(self.teshis(s), [])

    def test_teshis_does_not_change_color(self):
        for s in self.siniflamalar:
            renk = s.renk
            sonuclar = self.teshis(s)
            self.assertEqual(oturum_detayi(self.conn, s, self.rules)["renk"], renk)
            for r in sonuclar:
                self.assertNotIn("renk", r)
                self.assertTrue(r["yetkiler"])
                self.assertIn("kaynak", r)
        yeniden = {x.sess_no: x.renk for x in hatalari_sinifla(self.conn, self.rules)}
        self.assertEqual(yeniden, {x.sess_no: x.renk for x in self.siniflamalar})

    # Panel yalnızca gösterir

    def test_panel_files_have_no_sql_writes_or_streamlit_in_data_module(self):
        panel = PANEL_FILE.read_text(encoding="utf-8")
        data = (PACKAGE_DIR / "panel_data.py").read_text(encoding="utf-8")
        for name, text in (("panel.py", panel), ("panel_data.py", data)):
            for word in ("SELECT", "INSERT", "UPDATE", "DELETE", "sqlite3.connect"):
                self.assertNotIn(word, text, f"{name}: {word}")
        self.assertNotIn("streamlit", data)
        self.assertIn("connect_readonly", panel)


@unittest.skipUnless(HAS_STREAMLIT, "streamlit kurulu değil")
class PanelSmokeTest(unittest.TestCase):
    """Streamlit'in AppTest aracıyla panelin açıldığını doğrular. Satıra tıklayarak seçim
    yapma AppTest'te simüle edilemez; o kısım elle kontrol edilir."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @contextmanager
    def ortam(self, db_path, yetki_yolu=None):
        """Ortam değişkenleri, sonraki at.run() çağrılarını da kapsayacak şekilde ayarlanır."""
        degisenler = {"ODI_DEMO_DB": str(db_path), YETKI_ENV: yetki_yolu}
        previous = {k: os.environ.get(k) for k in degisenler}
        for k, v in degisenler.items():
            if v is not None:
                os.environ[k] = v
        try:
            yield
        finally:
            for k, v in previous.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def run_panel(self, db_path, yetki_yolu=None):
        from streamlit.testing.v1 import AppTest
        with self.ortam(db_path, yetki_yolu):
            at = AppTest.from_file(str(PANEL_FILE), default_timeout=60)
            return at, at.run()

    @staticmethod
    def teshis_basliklari(at):
        return [m.value for m in at.markdown if m.value.startswith("**") and "_" in m.value]

    def test_panel_opens_with_warnings_table_and_diagnosis(self):
        _, at = self.run_panel(self.db_path)
        self.assertFalse(at.exception)
        self.assertTrue(any("uydurmadır" in w.value for w in at.warning))
        self.assertTrue(any("gerçek sistemden alınmadı" in w.value for w in at.warning))
        self.assertEqual(len(at.dataframe[0].value), 25)
        self.assertFalse(any("henüz yazılmadı" in i.value for i in at.info))
        self.assertTrue(any(m.value == "### Teşhis" for m in at.markdown))
        self.assertTrue(any(s.value.startswith("Oturum ") for s in at.subheader))  # varsayılan seçim
        # Varsayılan seçim: sebepsiz ORA-12801; demo yetki dosyasında paralel sorgu yetkisi kapalı.
        self.assertEqual(self.teshis_basliklari(at),
                         [f"**paralel_sunucu_kullanimi** · {DURUM_YETKISIZ}"])
        self.assertTrue(any("❌ tanımlı değil" in c.value for c in at.caption))

    def test_missing_permission_file_skips_all(self):
        _, at = self.run_panel(self.db_path, yetki_yolu=str(Path(self.tmp.name) / "yok.json"))
        self.assertFalse(at.exception)
        self.assertTrue(any("gerçek sistemden alınmadı" in w.value for w in at.warning))
        basliklar = self.teshis_basliklari(at)
        self.assertTrue(basliklar)
        for b in basliklar:
            self.assertTrue(b.endswith(f"· {DURUM_YETKISIZ}"), b)
        self.assertTrue(any("yok.json okunamadı" in c.value for c in at.caption))

    def test_color_filter_limits_table(self):
        with self.ortam(self.db_path):
            _, at = self.run_panel(self.db_path)
            at.multiselect[0].set_value(["YESIL"])
            at.run()
        self.assertFalse(at.exception)
        renkler = set(at.dataframe[0].value["Renk"])
        self.assertEqual(renkler, {"🟢 YESIL"})

    def test_missing_database_shows_message_and_keeps_warning(self):
        _, at = self.run_panel(Path(self.tmp.name) / "yok.db")
        self.assertFalse(at.exception)
        self.assertTrue(any("Veritabanı yok" in e.value for e in at.error))
        self.assertTrue(any("uydurmadır" in w.value for w in at.warning))


if __name__ == "__main__":
    unittest.main()
