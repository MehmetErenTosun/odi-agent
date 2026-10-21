"""Panelin göstereceği veriyi hazırlar. Streamlit'ten bağımsızdır, SQL yazmaz.

Sınıflama ve eşleştirme classifier.py ile history.py'de yapılır; burada yalnızca
sonuçlar gösterime uygun düz sözlüklere çevrilir.
"""

from dataclasses import asdict

from odi_agent.classifier import hatalari_sinifla
from odi_agent.diagnostics import teshis_yap, uygun_sablonlar
from odi_agent.history import gecmis_benzerler

GRUPLAR = ("ayni_adim", "farkli_sebep", "farkli_adim")


def hata_listesi(conn, rules, siniflamalar=None):
    """Hatalı oturumlar, en yeni oturum üstte."""
    siniflamalar = siniflamalar if siniflamalar is not None else hatalari_sinifla(conn, rules)
    rows = [{
        "sess_no": s.sess_no,
        "adim": s.adim,
        "hata_kodu": s.hata_kodu,
        "asil_sebep": s.asil_sebep,
        "renk": s.renk,
    } for s in siniflamalar]
    return sorted(rows, key=lambda r: r["sess_no"], reverse=True)


def renk_filtrele(satirlar, renkler):
    """renkler None ise hepsi, boş liste ise hiçbiri."""
    if renkler is None:
        return list(satirlar)
    return [r for r in satirlar if r["renk"] in renkler]


def oturum_detayi(conn, siniflama, rules):
    """Seçili hata için gerekçe, deneme limiti ve geçmiş eşleştirme grupları."""
    gecmis = gecmis_benzerler(conn, siniflama.hata_kodu, siniflama.adim,
                              asil_sebep=siniflama.asil_sebep,
                              haric_sess_no=siniflama.sess_no, rules=rules)
    return {
        "sess_no": siniflama.sess_no,
        "adim": siniflama.adim,
        "hata_kodu": siniflama.hata_kodu,
        "asil_sebep": siniflama.asil_sebep,
        "renk": siniflama.renk,
        "gerekce": list(siniflama.gerekce),
        "max_deneme": siniflama.max_deneme,
        "gecmis": {grup: [asdict(item) for item in getattr(gecmis, grup)] for grup in GRUPLAR},
    }


def teshis_sonuclari(siniflama, sablonlar, yetkiler, calistirici):
    """Seçili hata için uygun teşhis şablonlarının sonuçları. Rengi değiştirmez."""
    uygun = uygun_sablonlar(sablonlar, siniflama.hata_kodu, siniflama.asil_sebep)
    return [{
        "ad": s.ad,
        "aciklama": s.aciklama,
        "durum": r.durum,
        "neden": r.neden,
        "yetkiler": [{"ad": y, "tanimli": y in yetkiler.verilen} for y in s.gereken_yetki],
        "satirlar": r.satirlar,
        "kaynak": r.kaynak,
    } for s, r in zip(uygun, teshis_yap(uygun, yetkiler, calistirici))]
