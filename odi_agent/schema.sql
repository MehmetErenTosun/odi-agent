-- ODI 12c work repository log tablolarının küçük bir taklidi (SQLite).
-- Hiçbir kolon Oracle'ın resmi kaynağı (MOS Doc ID 1903225.1) ile doğrulanmadı.
-- Kolon bazında dayanaklar: docs/KOLON_KAYNAKLARI.md
-- Tarihler TEXT olarak 'YYYY-MM-DD HH:MM:SS' biçiminde, süreler saniye cinsinden.

CREATE TABLE SNP_SESSION (
    SESS_NO       INTEGER PRIMARY KEY,  -- doğrulanmadı
    SESS_NAME     TEXT,                 -- doğrulanmadı
    SESS_BEG      TEXT,                 -- doğrulanmadı
    SESS_END      TEXT,                 -- doğrulanmadı
    SESS_DUR      INTEGER,              -- doğrulanmadı
    SESS_STATUS   TEXT,                 -- doğrulanmadı (D, E, R, W, M, A)
    SESS_RC       TEXT,                 -- doğrulanmadı
    SESS_MESS     TEXT,                 -- doğrulanmadı
    AGENT_NAME    TEXT,                 -- doğrulanmadı
    CONTEXT_CODE  TEXT                  -- doğrulanmadı
);

CREATE TABLE SNP_SESS_STEP (
    SESS_NO    INTEGER,  -- doğrulanmadı
    NNO        INTEGER,  -- doğrulanmadı
    STEP_NAME  TEXT,     -- doğrulanmadı
    PRIMARY KEY (SESS_NO, NNO)
);

CREATE TABLE SNP_STEP_LOG (
    SESS_NO      INTEGER,  -- doğrulanmadı
    NNO          INTEGER,  -- doğrulanmadı
    NB_RUN       INTEGER,  -- doğrulanmadı
    STEP_BEG     TEXT,     -- doğrulanmadı
    STEP_END     TEXT,     -- doğrulanmadı
    STEP_DUR     INTEGER,  -- doğrulanmadı
    STEP_STATUS  TEXT,     -- doğrulanmadı
    STEP_RC      TEXT,     -- doğrulanmadı
    STEP_MESS    TEXT,     -- doğrulanmadı
    NB_ROW       INTEGER,  -- doğrulanmadı
    NB_INS       INTEGER,  -- doğrulanmadı
    NB_UPD       INTEGER,  -- doğrulanmadı
    NB_DEL       INTEGER,  -- doğrulanmadı
    NB_ERR       INTEGER,  -- doğrulanmadı
    PRIMARY KEY (SESS_NO, NNO, NB_RUN)
);

-- Aşağıdakiler ODI'de YOKTUR; demo'ya özel yardımcı tablolardır.

CREATE TABLE DEMO_STEP_INFO (
    STEP_NAME     TEXT PRIMARY KEY,
    LOAD_TYPE     TEXT CHECK (LOAD_TYPE IN ('INCREMENTAL_APPEND', 'FULL_RELOAD', 'MERGE')),
    TARGET_TABLE  TEXT
);

CREATE TABLE DEMO_RESOLUTION (
    SESS_NO        INTEGER,
    NNO            INTEGER,
    ERROR_PATTERN  TEXT,
    COZUM_NOTU     TEXT,
    RENK           TEXT CHECK (RENK IN ('KIRMIZI', 'TURUNCU', 'YESIL')),
    COZEN_KISI     TEXT,
    COZUM_TARIHI   TEXT,
    PRIMARY KEY (SESS_NO, NNO)
);

-- Teşhis şablonlarının uydurma sonuçları; her satır bir sonuç satırının JSON hâli.
CREATE TABLE DEMO_DIAG_SONUC (
    SABLON_ADI  TEXT,
    SATIR_NO    INTEGER,
    SATIR_JSON  TEXT,
    PRIMARY KEY (SABLON_ADI, SATIR_NO)
);
