"""Salt okunur ODI hata paneli. Yalnızca gösterir; mantık classifier.py ve history.py'de.

Çalıştırma (proje kökünden): python -m streamlit run odi_agent/panel.py
"""

import os

import streamlit as st

from odi_agent.classifier import hatalari_sinifla, load_rules
from odi_agent.db import connect_readonly
from odi_agent.panel_data import hata_listesi, oturum_detayi, renk_filtrele
from odi_agent.seed import DEFAULT_DB_PATH

RENKLER = ("KIRMIZI", "TURUNCU", "YESIL")
ROZET = {"KIRMIZI": "🔴 KIRMIZI", "TURUNCU": "🟠 TURUNCU", "YESIL": "🟢 YESIL"}
ROZET_RENGI = {"KIRMIZI": "red", "TURUNCU": "orange", "YESIL": "green"}
GRUP_BASLIKLARI = {
    "ayni_adim": "Aynı adım, aynı sebep",
    "farkli_sebep": "Aynı adım, farklı asıl sebep",
    "farkli_adim": "Farklı adım",
}


def _bos(deger):
    return deger if deger else "-"


def _gecmis_grubu(baslik, satirlar):
    st.markdown(f"**{baslik}** ({len(satirlar)})")
    if not satirlar:
        st.caption("Kayıt yok")
        return
    for s in satirlar:
        with st.container(border=True):
            st.markdown(f"{ROZET[s['renk']]} · `{s['adim']}` · asıl sebep: {_bos(s['asil_sebep'])}")
            st.write(s["cozum_notu"])
            st.caption(f"Çözen: {s['cozen_kisi']} · Tarih: {s['cozum_tarihi']}")
            for uyari in s["uyarilar"]:
                st.caption(f"⚠️ {uyari}")


def _detay(detay):
    st.subheader(f"Oturum {detay['sess_no']} · {detay['adim']}")
    st.badge(detay["renk"], color=ROZET_RENGI[detay["renk"]])
    st.caption(f"Hata kodu: {_bos(detay['hata_kodu'])} · Asıl sebep: {_bos(detay['asil_sebep'])}")

    st.markdown("**Sınıflama gerekçesi**")
    for satir in detay["gerekce"]:
        st.markdown(f"- {satir}")
    if detay["max_deneme"] is not None:
        st.markdown(f"**En fazla {detay['max_deneme']} deneme**")

    st.markdown("### Geçmiş benzerler")
    for grup, baslik in GRUP_BASLIKLARI.items():
        _gecmis_grubu(baslik, detay["gecmis"][grup])

    st.markdown("### Teşhis")
    st.info("Teşhis (kilit, tablespace sorguları) henüz yazılmadı.")


def _goster(conn, rules):
    siniflamalar = hatalari_sinifla(conn, rules)
    tum_satirlar = hata_listesi(conn, rules, siniflamalar)
    sol, sag = st.columns([2, 3])

    with sol:
        st.subheader("Hatalı oturumlar")
        secili_renkler = st.multiselect("Renk", RENKLER, default=list(RENKLER))
        satirlar = renk_filtrele(tum_satirlar, secili_renkler)
        if not satirlar:
            st.info("Seçili renklerde hatalı oturum yok.")
            return
        tablo = [{
            "Oturum": r["sess_no"],
            "Adım": r["adim"],
            "Hata kodu": _bos(r["hata_kodu"]),
            "Asıl sebep": _bos(r["asil_sebep"]),
            "Renk": ROZET[r["renk"]],
        } for r in satirlar]
        olay = st.dataframe(tablo, hide_index=True, on_select="rerun",
                            selection_mode="single-row", key="hata_tablosu")
        secili = olay.selection.rows
        indeks = secili[0] if secili and secili[0] < len(satirlar) else 0  # seçim yoksa ilk satır

    sess_no = satirlar[indeks]["sess_no"]
    siniflama = next(s for s in siniflamalar if s.sess_no == sess_no)
    with sag:
        _detay(oturum_detayi(conn, siniflama, rules))


def main():
    st.set_page_config(page_title="ODI Hata Paneli", layout="wide")
    st.title("ODI Hata Teşhis Paneli")
    st.warning("Bu veriler uydurmadır. Gerçek bir sistemden alınmamıştır.")

    db_yolu = os.environ.get("ODI_DEMO_DB", DEFAULT_DB_PATH)
    try:
        conn = connect_readonly(db_yolu)
    except FileNotFoundError:
        st.error("Veritabanı yok. Önce şunu çalıştır: python -m odi_agent.seed")
        st.stop()
    try:
        _goster(conn, load_rules())
    finally:
        conn.close()


main()
