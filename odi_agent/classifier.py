"""Hatalı ODI oturumlarını KIRMIZI / TURUNCU / YESIL olarak sınıflar.

Kurallar rules.json'dan okunur. Restart (yeniden çalıştırma) burada YAPILMAZ.
Hata kodu mesajdaki ilk ORA kodudur. Bu kod sarmalayıcıysa (ör. ORA-12801)
rengi ondan sonra gelen asıl sebep kodu belirler. Yoksayılan kodlar (ör. ORA-06512,
yalnızca satır bilgisi) mesajdan tamamen çıkarılır.
"""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from odi_agent.schema_map import STATUS_ERROR, Session, StepInfo, StepLog, StepName, step_name_join

RULES_PATH = Path(__file__).with_name("rules.json")
COLORS = ("KIRMIZI", "TURUNCU", "YESIL")  # en riskliden en güvenliye; sıra karşılaştırmada kullanılır
INCREMENTAL_APPEND = "INCREMENTAL_APPEND"
ORA_CODE = re.compile(r"ORA-\d{5}")
REQUIRED_KEYS = ("varsayilan_renk", "yesil_max_deneme", "sarmalayici_kodlar",
                 "yoksayilan_kodlar", "sebep_bulunamazsa_renk", "hata_kodlari", "adim_istisnalari",
                 "yukleme_tipi_tavani", "bilinmeyen_yukleme_tipi_tavani")


class RulesError(ValueError):
    pass


@dataclass
class Siniflama:
    sess_no: int
    nno: int
    adim: str
    hata_kodu: str | None
    asil_sebep: str | None
    yukleme_tipi: str | None
    renk: str
    gerekce: list[str]
    max_deneme: int | None


def load_rules(path=RULES_PATH):
    rules = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_rules(rules)
    return rules


def validate_rules(rules):
    missing = [k for k in REQUIRED_KEYS if k not in rules]
    if missing:
        raise RulesError(f"Eksik ayar: {', '.join(missing)}")

    colors = [rules["varsayilan_renk"], rules["bilinmeyen_yukleme_tipi_tavani"],
              rules["sebep_bulunamazsa_renk"],
              *rules["hata_kodlari"].values(),
              *(e["renk"] for e in rules["adim_istisnalari"]),
              *rules["yukleme_tipi_tavani"].values()]
    invalid = sorted({c for c in colors if c not in COLORS})
    if invalid:
        raise RulesError(f"Geçersiz renk: {', '.join(invalid)}")

    # Ayar dosyası bozulsa bile incremental append asla YESIL olamaz.
    cap = rules["yukleme_tipi_tavani"].get(INCREMENTAL_APPEND)
    if cap is None or cap == "YESIL":
        raise RulesError(f"{INCREMENTAL_APPEND} için YESIL'den düşük bir tavan zorunlu")

    # Asıl sebebi bilinmeyen sarmalayıcı hata asla YESIL olamaz.
    if rules["sebep_bulunamazsa_renk"] == "YESIL":
        raise RulesError("sebep_bulunamazsa_renk YESIL olamaz")
    for key in ("sarmalayici_kodlar", "yoksayilan_kodlar"):
        if not isinstance(rules[key], list):
            raise RulesError(f"{key} bir liste olmalı")
    overlap = set(rules["sarmalayici_kodlar"]) & set(rules["yoksayilan_kodlar"])
    if overlap:
        raise RulesError(f"Hem sarmalayıcı hem yoksayılan: {', '.join(sorted(overlap))}")

    retries = rules["yesil_max_deneme"]
    if not isinstance(retries, int) or retries < 1:
        raise RulesError("yesil_max_deneme pozitif bir tam sayı olmalı")


def extract_error_codes(message, rules):
    """(ilk kod, asıl sebep) döner. Yoksayılan kodlar baştan çıkarılır. Asıl sebep yalnızca
    ilk kod sarmalayıcıysa aranır; ondan sonra gelen ilk sarmalayıcı olmayan koddur
    (iç içe sarmalayıcılar atlanır). Geçmiş eşleştirme de bu fonksiyonu kullanır."""
    wrappers, ignored = rules["sarmalayici_kodlar"], rules["yoksayilan_kodlar"]
    codes = [c for c in ORA_CODE.findall(message or "") if c not in ignored]
    if not codes:
        return None, None
    first = codes[0]
    if first not in wrappers:
        return first, None
    cause = next((c for c in codes[1:] if c not in wrappers), None)
    return first, cause


def _color_for_code(code, step_name, rules, reasons):
    exception = next((e for e in rules["adim_istisnalari"]
                      if e["adim"] == step_name and e["hata_kodu"] == code), None)
    if exception:
        reasons.append(f"Adım istisnası ({exception['renk']}): {exception['neden']}")
        return exception["renk"]
    if code in rules["hata_kodlari"]:
        color = rules["hata_kodlari"][code]
        reasons.append(f"{code} kuralı: {color}")
        return color
    color = rules["varsayilan_renk"]
    reasons.append(f"{code or 'ORA kodu bulunamadı'}: kural yok, varsayılan {color}")
    return color


def classify(sess_no, nno, step_name, message, load_type, rules):
    code, cause = extract_error_codes(message, rules)
    reasons = []

    if code in rules["sarmalayici_kodlar"]:
        if cause:
            reasons.append(f"{code} sarmalayıcı; asıl sebep {cause}")
            color = _color_for_code(cause, step_name, rules, reasons)
        else:
            color = rules["sebep_bulunamazsa_renk"]
            reasons.append(f"{code} sarmalayıcı; asıl sebep bulunamadı, renk {color}")
    else:
        color = _color_for_code(code, step_name, rules, reasons)

    if load_type is None:
        cap, cap_reason = rules["bilinmeyen_yukleme_tipi_tavani"], "Yükleme tipi bilinmiyor"
    else:
        cap, cap_reason = rules["yukleme_tipi_tavani"].get(load_type), f"{load_type} tavanı"
    if cap and COLORS.index(cap) < COLORS.index(color):
        reasons.append(f"{cap_reason}: {color} yerine {cap} (çift yükleme riski)")
        color = cap

    return Siniflama(sess_no, nno, step_name, code, cause, load_type, color, reasons,
                     rules["yesil_max_deneme"] if color == "YESIL" else None)


def hatalari_sinifla(conn, rules=None):
    """SESS_STATUS = 'E' olan oturumların hatalı adımlarını sınıflar."""
    rules = rules or load_rules()
    sql = f"""
        SELECT l.{StepLog.SESS_NO}, l.{StepLog.NNO}, st.{StepName.NAME},
               l.{StepLog.MESS}, i.{StepInfo.LOAD_TYPE}
        FROM {Session.TABLE} s
        JOIN {StepLog.TABLE} l ON l.{StepLog.SESS_NO} = s.{Session.SESS_NO}
        {step_name_join("st", f"l.{StepLog.SESS_NO}", f"l.{StepLog.NNO}")}
        LEFT JOIN {StepInfo.TABLE} i ON i.{StepInfo.STEP_NAME} = st.{StepName.NAME}
        WHERE s.{Session.STATUS} = ? AND l.{StepLog.STATUS} = ?
        ORDER BY l.{StepLog.SESS_NO}, l.{StepLog.NNO}"""
    rows = conn.execute(sql, (STATUS_ERROR, STATUS_ERROR)).fetchall()
    return [classify(*row, rules) for row in rows]
