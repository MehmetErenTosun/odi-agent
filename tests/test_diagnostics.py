import json
import re
import tempfile
import unittest
from pathlib import Path

from odi_agent import seed
from odi_agent.db import connect_readonly
from odi_agent.diagnostics import (DEMO_KAYNAK, DURUM_CALISTI, DURUM_YETKISIZ, SABLON_PATH,
                                   YASAK_KELIMELER, Calistirici, DemoCalistirici, GuvenlikHatasi,
                                   Sablon, SablonHatasi, TeshisSonucu, Yetkiler, sablonlari_yukle,
                                   sql_dogrula, teshis_yap, uygun_sablonlar, yetkileri_yukle)

DOCS_FILE = Path(__file__).resolve().parent.parent / "docs" / "KOLON_KAYNAKLARI.md"

GECERLI_SABLON = {
    "ad": "deneme",
    "aciklama": "Deneme şablonu.",
    "tetikleyen_kodlar": ["ORA-00054"],
    "sql": "SELECT SID FROM V$SESSION",
    "gorunumler": {"V$SESSION": ["SID"]},
    "gereken_yetki": ["SELECT ON V_$SESSION"],
    "parametreler": [],
}


def sablon(**degisen):
    return Sablon(**{**GECERLI_SABLON, **degisen})


class SayacliCalistirici(Calistirici):
    """Kaç kez çağrıldığını sayan sahte çalıştırıcı."""

    def __init__(self):
        self.cagrilar = []

    def _sorgula(self, sablon, parametreler):
        self.cagrilar.append(sablon.ad)
        return TeshisSonucu(sablon.ad, DURUM_CALISTI, [], "sahte")


class TmpDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def dosya(self, ad, icerik):
        path = Path(self.tmp.name) / ad
        path.write_text(icerik if isinstance(icerik, str) else json.dumps(icerik), encoding="utf-8")
        return path


class SqlDogrulaTest(unittest.TestCase):
    def test_gecerli(self):
        for sql in ("SELECT SID FROM V$SESSION",
                    "select sid from v$session",
                    "  \n  SELECT SID FROM V$SESSION",
                    "SELECT LAST_UPDATE_DATE, CREATED_BY FROM T",
                    "SELECT SID FROM V$SESSION WHERE SID = :sid"):
            with self.subTest(sql=sql):
                sql_dogrula(sql)

    def test_saldirgan_ornekler_reddedilir(self):
        ornekler = [
            "DELETE FROM T",
            "SELECT 1 FROM DUAL; DROP TABLE T",
            "SELECT 1 FROM DUAL;",
            "SELECT * FROM T FOR UPDATE",
            "select * from t for\n  update nowait",
            "BEGIN NULL; END;",
            "DECLARE X NUMBER BEGIN NULL END",
            "WITH FUNCTION f RETURN NUMBER IS BEGIN RETURN 1 END SELECT f FROM DUAL",
            "WITH x AS (SELECT 1 FROM DUAL) SELECT * FROM x",
            "SELECT * FROM T /* ; DROP */",
            "SELECT * FROM T --\nDELETE FROM T",
            "SELECT 'a;b' FROM DUAL",
            "SELECT q'[x]' FROM DUAL",
            'SELECT "DELETE" FROM T',
            "SELECT * FROM T@UZAK",
            "SELECT DBMS_LOCK.SLEEP(1) FROM DUAL",
            "SELECT SYS.UTL_HTTP.REQUEST(:u) FROM DUAL",
            "SELECT X INTO Y FROM T",
            "EXECUTE IMMEDIATE :x",
            "CALL p()",
            "MERGE INTO T USING S ON (1 = 1)",
            "LOCK TABLE T IN EXCLUSIVE MODE",
            "GRANT DBA TO X",
            "TRUNCATE TABLE T",
            "SELECT * FROM T WHERE 1 = 1 UNION SELECT * FROM U WHERE X IN (SELECT 1 FROM DUAL) "
            "AND DROP_ME = 1 OR 1 = 1 COMMIT",
            "SELECT 1 FROM DUAL； DROP TABLE T",  # tam genişlikli noktalı virgül
            "SELECT 1 FROM DUAL",                  # ASCII dışı boşluk
            "",
            "   ",
            None,
        ]
        for sql in ornekler:
            with self.subTest(sql=sql):
                with self.assertRaises(GuvenlikHatasi):
                    sql_dogrula(sql)


class SablonYuklemeTest(TmpDirTest):
    def yukle(self, *sablonlar):
        return sablonlari_yukle(self.dosya("s.json", {"sablonlar": list(sablonlar)}))

    def test_gercek_dosya(self):
        sablonlar = sablonlari_yukle()
        self.assertEqual([s.ad for s in sablonlar],
                         ["kilit_durumu", "tablespace_doluluk", "temp_doluluk",
                          "paralel_sunucu_kullanimi"])

    def test_gorunum_ve_kolonlar_sqlde_gecer(self):
        for s in sablonlari_yukle():
            for gorunum, kolonlar in s.gorunumler.items():
                with self.subTest(sablon=s.ad, gorunum=gorunum):
                    self.assertIn(gorunum, s.sql)
                    for kolon in kolonlar:
                        self.assertRegex(s.sql, rf"(?<![\w$#]){re.escape(kolon)}(?![\w$#])")

    def test_gecerli_sablon(self):
        self.assertEqual(self.yukle(GECERLI_SABLON)[0], sablon())

    def test_eksik_alan(self):
        for alan in GECERLI_SABLON:
            with self.subTest(alan=alan):
                eksik = {k: v for k, v in GECERLI_SABLON.items() if k != alan}
                with self.assertRaises(SablonHatasi):
                    self.yukle(eksik)

    def test_select_disi_sql(self):
        for sql in ("DELETE FROM T", "SELECT * FROM T FOR UPDATE", "SELECT 1 FROM DUAL; DROP TABLE T"):
            with self.subTest(sql=sql):
                with self.assertRaises(SablonHatasi):
                    self.yukle({**GECERLI_SABLON, "sql": sql})

    def test_ayni_ad_iki_kez(self):
        with self.assertRaises(SablonHatasi):
            self.yukle(GECERLI_SABLON, GECERLI_SABLON)

    def test_gecersiz_kod_ve_turler(self):
        for degisen in ({"tetikleyen_kodlar": ["ORA-54"]}, {"tetikleyen_kodlar": []},
                        {"gereken_yetki": []}, {"gereken_yetki": "SELECT ON V_$SESSION"},
                        {"gorunumler": {}}, {"parametreler": ["sid"]}):
            with self.subTest(degisen=degisen):
                with self.assertRaises(SablonHatasi):
                    self.yukle({**GECERLI_SABLON, **degisen})

    def test_bozuk_ya_da_eksik_dosya(self):
        for path in (self.dosya("bozuk.json", "{bozuk"), self.dosya("liste.json", "[]"),
                     Path(self.tmp.name) / "yok.json"):
            with self.subTest(path=path.name):
                with self.assertRaises(SablonHatasi):
                    sablonlari_yukle(path)

    def test_eslesme(self):
        sablonlar = sablonlari_yukle()

        def adlar(kod, sebep):
            return [s.ad for s in uygun_sablonlar(sablonlar, kod, sebep)]

        self.assertEqual(adlar("ORA-00054", None), ["kilit_durumu"])
        self.assertEqual(adlar("ORA-12801", "ORA-00060"), ["kilit_durumu", "paralel_sunucu_kullanimi"])
        self.assertEqual(adlar("ORA-12801", None), ["paralel_sunucu_kullanimi"])
        self.assertEqual(adlar("ORA-01652", None), ["tablespace_doluluk", "temp_doluluk"])
        self.assertEqual(adlar("ORA-00942", None), [])
        self.assertEqual(adlar(None, None), [])


class SablonDosyasiTaramaTest(unittest.TestCase):
    def test_dml_anahtar_kelimesi_yok(self):
        metin = SABLON_PATH.read_text(encoding="utf-8")
        for kelime in YASAK_KELIMELER:
            with self.subTest(kelime=kelime):
                self.assertIsNone(re.search(rf"\b{kelime}\b", metin, re.IGNORECASE))
        self.assertIsNone(re.search(r"\bFOR\s+UPDATE\b", metin, re.IGNORECASE))
        for s in json.loads(metin)["sablonlar"]:
            sql_dogrula(s["sql"])

    def test_adlar_belgede_ve_dogrulanmadi(self):
        belge = DOCS_FILE.read_text(encoding="utf-8")
        self.assertNotIn("doğrulandı (kullanıcı deneyimi)", belge)
        for s in sablonlari_yukle():
            for ad in [*s.gorunumler, *(k for ks in s.gorunumler.values() for k in ks), *s.gereken_yetki]:
                with self.subTest(ad=ad):
                    self.assertIn(ad, belge)


class YetkiTest(TmpDirTest):
    def calistir(self, yetkiler, sablonlar=None):
        sablonlar = sablonlar or sablonlari_yukle()
        calistirici = SayacliCalistirici()
        sonuclar = teshis_yap(sablonlar, yetkiler, calistirici)
        return {r.sablon_adi: r for r in sonuclar}, calistirici.cagrilar

    def assert_hepsi_atlandi(self, yetkiler):
        self.assertTrue(yetkiler.hata)
        self.assertEqual(yetkiler.verilen, frozenset())
        sonuclar, cagrilar = self.calistir(yetkiler)
        self.assertEqual(cagrilar, [])
        for r in sonuclar.values():
            self.assertEqual(r.durum, DURUM_YETKISIZ)
            self.assertEqual(r.neden, yetkiler.hata)

    def test_dosya_eksik(self):
        self.assert_hepsi_atlandi(yetkileri_yukle(Path(self.tmp.name) / "yok.json"))

    def test_dosya_bozuk(self):
        self.assert_hepsi_atlandi(yetkileri_yukle(self.dosya("y.json", "{bozuk")))

    def test_dosya_bicimi_bozuk(self):
        for icerik in ([], {"yetkiler": ["SELECT ON V_$SESSION"]}, {"baska": {}}):
            with self.subTest(icerik=icerik):
                self.assert_hepsi_atlandi(yetkileri_yukle(self.dosya("y.json", icerik)))

    def test_kismi_dosya(self):
        yetkiler = yetkileri_yukle(self.dosya("y.json", {"yetkiler": {"SELECT ON V_$SESSION": True}}))
        sonuclar, cagrilar = self.calistir(yetkiler)
        self.assertEqual(cagrilar, ["kilit_durumu"])
        self.assertEqual(sonuclar["kilit_durumu"].durum, DURUM_CALISTI)
        for ad in ("tablespace_doluluk", "temp_doluluk", "paralel_sunucu_kullanimi"):
            self.assertEqual(sonuclar[ad].durum, DURUM_YETKISIZ)
            self.assertIn("Tanımlı değil", sonuclar[ad].neden)

    def test_yalnizca_json_true_yetki_sayilir(self):
        yetkiler = yetkileri_yukle(self.dosya("y.json", {"yetkiler": {
            "SELECT ON V_$SESSION": "true", "SELECT ON DBA_TEMP_FREE_SPACE": 1,
            "SELECT ON V_$PX_SESSION": False}}))
        self.assertIsNone(yetkiler.hata)
        self.assertEqual(yetkiler.verilen, frozenset())

    def test_iki_yetkiden_biri_eksik(self):
        iki = sablon(gereken_yetki=["A", "B"])
        sonuclar, cagrilar = self.calistir(Yetkiler(frozenset({"A"})), [iki])
        self.assertEqual(cagrilar, [])
        self.assertIn("B", sonuclar["deneme"].neden)
        sonuclar, cagrilar = self.calistir(Yetkiler(frozenset({"A", "B"})), [iki])
        self.assertEqual(cagrilar, ["deneme"])

    def test_demo_yetki_dosyasi(self):
        yetkiler = yetkileri_yukle()
        self.assertIsNone(yetkiler.hata)
        self.assertIn("SELECT ON V_$SESSION", yetkiler.verilen)
        self.assertNotIn("SELECT ON V_$PX_SESSION", yetkiler.verilen)


class DemoCalistiriciTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = Path(cls.tmp.name) / "test.db"
        seed.build(cls.db_path)
        cls.conn = connect_readonly(cls.db_path)  # salt okunur bağlantıyla çalışmalı
        cls.calistirici = DemoCalistirici(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        cls.tmp.cleanup()

    def test_demo_etiketli_ve_seed_ile_ayni(self):
        for s in sablonlari_yukle():
            with self.subTest(sablon=s.ad):
                r = self.calistirici.calistir(s, {})
                self.assertEqual(r.kaynak, DEMO_KAYNAK)
                self.assertEqual(r.durum, DURUM_CALISTI)
                self.assertEqual(r.satirlar, seed.DIAG_RESULTS[s.ad])

    def test_satiri_olmayan_sablon_bos_doner(self):
        r = self.calistirici.calistir(sablon(ad="tabloda_yok"), {})
        self.assertEqual(r.satirlar, [])
        self.assertEqual(r.kaynak, DEMO_KAYNAK)

    def test_yukleyiciyi_atlatan_yasak_sql_reddedilir(self):
        for sql in ("DELETE FROM T", "SELECT * FROM T FOR UPDATE"):
            with self.subTest(sql=sql):
                with self.assertRaises(GuvenlikHatasi):
                    self.calistirici.calistir(sablon(sql=sql), {})

    def test_parametre_uyusmazligi(self):
        with self.assertRaises(SablonHatasi):
            self.calistirici.calistir(sablon(), {"fazla": 1})
        parametreli = sablon(sql="SELECT SID FROM V$SESSION WHERE SID = :sid", parametreler=["sid"])
        with self.assertRaises(SablonHatasi):
            self.calistirici.calistir(parametreli, {})
        self.calistirici.calistir(parametreli, {"sid": 1})


if __name__ == "__main__":
    unittest.main()
