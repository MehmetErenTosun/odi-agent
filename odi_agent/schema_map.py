"""ODI repository tablo ve kolon adları. Ajan kodu bu adları yalnızca buradan okur.

Hiçbir ad resmi kaynakla doğrulanmadı; bkz. docs/KOLON_KAYNAKLARI.md
("Bilinen belirsizlikler"). SNP_SESS_STEP yerine SNP_SB_STEP kullanılacaksa
StepName sınıfı ve step_name_join() birlikte değiştirilir.
"""


class Session:
    TABLE = "SNP_SESSION"
    SESS_NO = "SESS_NO"
    STATUS = "SESS_STATUS"
    END = "SESS_END"


class StepLog:
    TABLE = "SNP_STEP_LOG"
    SESS_NO = "SESS_NO"
    NNO = "NNO"
    STATUS = "STEP_STATUS"
    MESS = "STEP_MESS"  # [G]'de ERROR_MESSAGE olabilir


class StepName:
    TABLE = "SNP_SESS_STEP"  # 12c'de SNP_SB_STEP olabilir
    SESS_NO = "SESS_NO"
    NNO = "NNO"
    NAME = "STEP_NAME"


STATUS_ERROR = "E"


def step_name_join(alias, sess_no_expr, nno_expr):
    """Adım adını getiren JOIN ifadesi. Join anahtarı tablo ile birlikte değişebilir."""
    return (
        f"JOIN {StepName.TABLE} {alias} "
        f"ON {alias}.{StepName.SESS_NO} = {sess_no_expr} "
        f"AND {alias}.{StepName.NNO} = {nno_expr}"
    )


# Demo'ya özel tablolar (ODI'de yok).

class StepInfo:
    TABLE = "DEMO_STEP_INFO"
    STEP_NAME = "STEP_NAME"
    LOAD_TYPE = "LOAD_TYPE"


class Resolution:
    TABLE = "DEMO_RESOLUTION"
    SESS_NO = "SESS_NO"
    NNO = "NNO"
    ERROR_PATTERN = "ERROR_PATTERN"
    NOTE = "COZUM_NOTU"
    COLOR = "RENK"
    PERSON = "COZEN_KISI"
    DATE = "COZUM_TARIHI"


class DiagResult:
    TABLE = "DEMO_DIAG_SONUC"
    TEMPLATE = "SABLON_ADI"
    ROW_NO = "SATIR_NO"
    ROW_JSON = "SATIR_JSON"
