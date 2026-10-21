"""Bir hata için DEMO_RESOLUTION'daki geçmiş çözümleri getirir.

Sarmalayıcı kodlarda (ör. ORA-12801) asıl sebep de karşılaştırılır. Geçmiş kaydın
asıl sebebi log mesajından, sınıflayıcının kullandığı aynı fonksiyonla okunur.
"""

from dataclasses import dataclass, field

from odi_agent.classifier import extract_error_codes, load_rules
from odi_agent.schema_map import STATUS_ERROR, Resolution, StepLog, StepName, step_name_join

FARKLI_ADIM_UYARISI = "Farklı adımda çözülmüş; bu adıma uymayabilir"
FARKLI_SEBEP_UYARISI = "Aynı kod ama farklı asıl sebep, çözüm uymayabilir"
SEBEP_BILINMIYOR_NOTU = "Mevcut hatanın asıl sebebi bilinmiyor; sebep karşılaştırılamadı"


@dataclass
class GecmisCozum:
    sess_no: int
    adim: str
    renk: str
    cozum_notu: str
    cozen_kisi: str
    cozum_tarihi: str
    asil_sebep: str | None
    uyarilar: list[str] = field(default_factory=list)


@dataclass
class GecmisBenzerler:
    ayni_adim: list[GecmisCozum] = field(default_factory=list)
    farkli_sebep: list[GecmisCozum] = field(default_factory=list)
    farkli_adim: list[GecmisCozum] = field(default_factory=list)


def gecmis_benzerler(conn, hata_kodu, adim_adi, asil_sebep=None, haric_sess_no=None, rules=None):
    """Geçmiş çözümleri üç grupta döner:
    ayni_adim (aynı kod, adım ve asıl sebep), farkli_sebep (aynı kod ve adım,
    farklı ya da bilinmeyen asıl sebep), farkli_adim (aynı kod, farklı adım)."""
    rules = rules or load_rules()
    wrapper = hata_kodu in rules["sarmalayici_kodlar"]
    r, l = Resolution, StepLog
    # LEFT JOIN: log temizlenmişse kayıt yine gelir, asıl sebebi bilinmiyor sayılır.
    # haric_sess_no None ise "SESS_NO IS NOT NULL" olur ve hiçbir satırı elemez.
    sql = f"""
        SELECT r.{r.SESS_NO}, st.{StepName.NAME}, r.{r.COLOR}, r.{r.NOTE},
               r.{r.PERSON}, r.{r.DATE}, l.{l.MESS}
        FROM {r.TABLE} r
        {step_name_join("st", f"r.{r.SESS_NO}", f"r.{r.NNO}")}
        LEFT JOIN {l.TABLE} l ON l.{l.SESS_NO} = r.{r.SESS_NO} AND l.{l.NNO} = r.{r.NNO}
                             AND l.{l.STATUS} = ?
        WHERE r.{r.ERROR_PATTERN} = ? AND r.{r.SESS_NO} IS NOT ?
        ORDER BY r.{r.DATE} DESC, r.{r.SESS_NO} DESC"""

    result = GecmisBenzerler()
    for *row, message in conn.execute(sql, (STATUS_ERROR, hata_kodu, haric_sess_no)):
        _, past_cause = extract_error_codes(message, rules)
        item = GecmisCozum(*row, past_cause)
        same_step = item.adim == adim_adi
        # Geçmiş kaydın sebebi bilinmiyorsa aynı olduğu doğrulanamaz: farklı sayılır.
        different_cause = wrapper and asil_sebep is not None and past_cause != asil_sebep

        if not same_step:
            item.uyarilar.append(FARKLI_ADIM_UYARISI)
        if different_cause:
            item.uyarilar.append(FARKLI_SEBEP_UYARISI)
        if wrapper and asil_sebep is None:
            item.uyarilar.append(SEBEP_BILINMIYOR_NOTU)

        if not same_step:
            result.farkli_adim.append(item)
        elif different_cause:
            result.farkli_sebep.append(item)
        else:
            result.ayni_adim.append(item)
    return result
