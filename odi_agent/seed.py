"""Uydurma ODI log verisi üretir ve SQLite veritabanına yazar.

Çalıştırma: python -m odi_agent.seed
Tüm isimler, mesajlar ve kişiler uydurmadır.
"""

import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "odi_demo.db"

SEED = 42
TOTAL_SESSIONS = 80
DAYS = 30
LAST_DAY = datetime(2026, 10, 15)  # sabit, böylece veri her gün aynı kalır
AGENT_NAME = "OracleDIAgent_DEMO"
CONTEXT_CODE = "DEMO_PROD"
TIME_FMT = "%Y-%m-%d %H:%M:%S"

# Senaryo -> adımlar: (adım adı, yükleme tipi, hedef tablo, tipik satır sayısı)
SCENARIOS = {
    "LOAD_DIM_URUN_DEMO": [
        ("MAP_STG_URUN_DEMO", "FULL_RELOAD", "STG_URUN_DEMO", 12_000),
        ("MAP_DIM_URUN_DEMO", "MERGE", "DIM_URUN_DEMO", 800),
    ],
    "LOAD_DIM_MUSTERI_DEMO": [
        ("MAP_STG_MUSTERI_DEMO", "FULL_RELOAD", "STG_MUSTERI_DEMO", 250_000),
        ("MAP_DIM_MUSTERI_DEMO", "MERGE", "DIM_MUSTERI_DEMO", 4_000),
        ("MAP_DIM_MUSTERI_ADRES_DEMO", "MERGE", "DIM_MUSTERI_ADRES_DEMO", 3_000),
    ],
    "LOAD_FACT_SIPARIS_DEMO": [
        ("MAP_STG_SIPARIS_DEMO", "FULL_RELOAD", "STG_SIPARIS_DEMO", 90_000),
        ("MAP_FACT_SIPARIS_DEMO", "INCREMENTAL_APPEND", "FACT_SIPARIS_DEMO", 90_000),
        ("MAP_AGG_SIPARIS_GUNLUK_DEMO", "FULL_RELOAD", "AGG_SIPARIS_GUNLUK_DEMO", 1_500),
    ],
    "LOAD_FACT_STOK_DEMO": [
        ("MAP_STG_STOK_DEMO", "FULL_RELOAD", "STG_STOK_DEMO", 60_000),
        ("MAP_FACT_STOK_HAREKET_DEMO", "INCREMENTAL_APPEND", "FACT_STOK_HAREKET_DEMO", 45_000),
        ("MAP_FACT_STOK_SNAPSHOT_DEMO", "FULL_RELOAD", "FACT_STOK_SNAPSHOT_DEMO", 30_000),
        ("MAP_AGG_STOK_DEMO", "FULL_RELOAD", "AGG_STOK_DEMO", 900),
    ],
    "LOAD_FACT_ODEME_DEMO": [
        ("MAP_STG_ODEME_DEMO", "FULL_RELOAD", "STG_ODEME_DEMO", 70_000),
        ("MAP_FACT_ODEME_DEMO", "INCREMENTAL_APPEND", "FACT_ODEME_DEMO", 70_000),
        ("MAP_AGG_ODEME_DEMO", "FULL_RELOAD", "AGG_ODEME_DEMO", 1_200),
    ],
    "LOAD_DIM_MAGAZA_DEMO": [
        ("MAP_STG_MAGAZA_DEMO", "FULL_RELOAD", "STG_MAGAZA_DEMO", 400),
        ("MAP_DIM_MAGAZA_DEMO", "MERGE", "DIM_MAGAZA_DEMO", 20),
        ("MAP_DIM_BOLGE_DEMO", "MERGE", "DIM_BOLGE_DEMO", 5),
    ],
}

# Oracle'ın genel, kamuya açık hata mesajları (şema adı DEMO_DWH uydurmadır).
ORA_MESSAGES = {
    "ORA-01652": "ORA-01652: unable to extend temp segment by 128 in tablespace TEMP",
    "ORA-12541": "ORA-12541: TNS:no listener",
    "ORA-00001": "ORA-00001: unique constraint (DEMO_DWH.PK_FACT_ODEME_DEMO) violated",
    "ORA-01555": 'ORA-01555: snapshot too old: rollback segment number 12 with name "_SYSSMU12$" too small',
    "ORA-00942": "ORA-00942: table or view does not exist",
    "ORA-12801": "ORA-12801: error signaled in parallel query server P003",
    "ORA-00054": "ORA-00054: resource busy and acquire with NOWAIT specified or timeout expired",
}

# Geçmiş olaylar: (adım, hata kodu, renk, çözüm notu). Her biri iki kez yaşanmış.
# ORA-12801 ve ORA-00054 bilerek farklı adımlarda farklı renk ve çözümle kayıtlı:
# ajanın değeri, aynı hata koduna bağlama göre farklı cevap verebilmesi.
INCIDENTS = [
    ("MAP_AGG_SIPARIS_GUNLUK_DEMO", "ORA-12801", "YESIL",
     "Paralellik derecesi 8'den 4'e düşürüldü, adım otomatik yeniden çalıştırıldı."),
    ("MAP_FACT_SIPARIS_DEMO", "ORA-12801", "TURUNCU",
     "Incremental append: hedefte o yükleme tarihine ait satırlar sayıldı, çift yükleme "
     "olmadığı görüldü; onay alınıp yeniden çalıştırıldı."),
    ("MAP_DIM_MUSTERI_DEMO", "ORA-00054", "YESIL",
     "Kilidi tutan rapor sorgusu bitince adım otomatik yeniden denendi."),
    ("MAP_FACT_STOK_HAREKET_DEMO", "ORA-00054", "KIRMIZI",
     "Kilit başka ekibin batch işindeydi; ekip ile koordine edildi, ajan müdahale etmedi."),
    ("MAP_STG_STOK_DEMO", "ORA-01652", "TURUNCU",
     "DBA'den TEMP tablespace büyütmesi istendi, onay sonrası yeniden çalıştırıldı."),
    ("MAP_STG_ODEME_DEMO", "ORA-12541", "YESIL",
     "Kaynak veritabanının listener'ı birkaç dakika sonra açıldı, yeniden deneme başarılı."),
    ("MAP_FACT_ODEME_DEMO", "ORA-00001", "KIRMIZI",
     "Kaynakta mükerrer ödeme kaydı vardı; iş birimine bildirildi, veri düzeltilmeden yükleme yapılmadı."),
    ("MAP_FACT_STOK_SNAPSHOT_DEMO", "ORA-01555", "TURUNCU",
     "Kaynak tablo yoğun güncelleniyordu; çalışma saati kaydırılıp onayla yeniden çalıştırıldı."),
    ("MAP_DIM_MAGAZA_DEMO", "ORA-00942", "KIRMIZI",
     "Kaynak tablonun adı değişmişti; mapping geliştirici tarafından düzeltilmeli, ajan dokunmaz."),
]
OCCURRENCES_PER_INCIDENT = 2

# Son gün açık (henüz çözülmemiş) kalan hatalar: ajanın teşhis edeceği vakalar.
OPEN_ERRORS = [
    ("MAP_FACT_SIPARIS_DEMO", "ORA-12801"),
    ("MAP_DIM_MUSTERI_DEMO", "ORA-00054"),
]

COZEN_KISILER = ["Ayşe Demo", "Mert Örnek", "Selin Test", "Kaan Deneme"]

STEP_TO_SCENARIO = {step[0]: scen for scen, steps in SCENARIOS.items() for step in steps}


def _fmt(dt):
    return dt.strftime(TIME_FMT)


def create_db(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    return conn


def _plan_sessions(rng):
    """(gün, senaryo, hatalı adım, hata kodu, çözüm) listesi döner."""
    used = set()
    planned = []

    def take_slot(scenario, days):
        free = [d for d in days if (d, scenario) not in used]
        day = rng.choice(free)
        used.add((day, scenario))
        return day

    last = DAYS - 1
    for step, code in OPEN_ERRORS:
        scen = STEP_TO_SCENARIO[step]
        planned.append((take_slot(scen, [last]), scen, step, code, None))

    for step, code, renk, note in INCIDENTS:
        scen = STEP_TO_SCENARIO[step]
        for _ in range(OCCURRENCES_PER_INCIDENT):
            day = take_slot(scen, range(last))
            planned.append((day, scen, step, code, (renk, note)))

    while len(planned) < TOTAL_SESSIONS:
        scen = rng.choice(list(SCENARIOS))
        planned.append((take_slot(scen, range(DAYS)), scen, None, None, None))
    return planned


def generate(conn, seed=SEED):
    rng = random.Random(seed)
    first_day = LAST_DAY - timedelta(days=DAYS - 1)
    scen_hour = {scen: 1 + i for i, scen in enumerate(SCENARIOS)}

    conn.executemany(
        "INSERT INTO DEMO_STEP_INFO VALUES (?, ?, ?)",
        [(s[0], s[1], s[2]) for steps in SCENARIOS.values() for s in steps],
    )

    planned = []
    for day, scen, fail_step, code, resolution in _plan_sessions(rng):
        start = first_day + timedelta(days=day, hours=scen_hour[scen],
                                      minutes=rng.randint(0, 20))
        planned.append((start, scen, fail_step, code, resolution))
    planned.sort(key=lambda p: p[0])

    for sess_no, (start, scen, fail_step, code, resolution) in enumerate(planned, start=1001):
        t = start
        status, rc, mess = "D", None, None
        for nno, (step, load_type, _target, rows) in enumerate(SCENARIOS[scen], start=1):
            conn.execute("INSERT INTO SNP_SESS_STEP VALUES (?, ?, ?)", (sess_no, nno, step))
            if status == "E":
                continue  # hatadan sonraki adımlar çalışmaz, log satırı yok
            dur = rng.randint(20, 600)
            end = t + timedelta(seconds=dur)
            if step == fail_step:
                status, rc, mess = "E", code.split("-")[1], ORA_MESSAGES[code]
                counts = (0, 0, 0, 0, 0)
                if resolution:
                    renk, note = resolution
                    fixed_at = end + timedelta(minutes=rng.randint(20, 360))
                    conn.execute(
                        "INSERT INTO DEMO_RESOLUTION VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (sess_no, nno, code, note, renk,
                         rng.choice(COZEN_KISILER), _fmt(fixed_at)),
                    )
            else:
                n = int(rows * rng.uniform(0.8, 1.2))
                if load_type == "MERGE":
                    ins = int(n * rng.uniform(0.05, 0.3))
                    counts = (n, ins, n - ins, 0, 0)
                else:
                    counts = (n, n, 0, 0, 0)
            conn.execute(
                "INSERT INTO SNP_STEP_LOG VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (sess_no, nno, _fmt(t), _fmt(end), dur,
                 "E" if step == fail_step else "D",
                 rc if step == fail_step else None,
                 mess if step == fail_step else None,
                 *counts),
            )
            t = end
        conn.execute(
            "INSERT INTO SNP_SESSION VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (sess_no, scen, _fmt(start), _fmt(t), int((t - start).total_seconds()),
             status, rc, mess, AGENT_NAME, CONTEXT_CODE),
        )
    conn.commit()


def build(db_path=DEFAULT_DB_PATH, seed=SEED):
    conn = create_db(db_path)
    try:
        generate(conn, seed)
        tables = ["SNP_SESSION", "SNP_SESS_STEP", "SNP_STEP_LOG",
                  "DEMO_STEP_INFO", "DEMO_RESOLUTION"]
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}
    finally:
        conn.close()


def main():
    counts = build()
    print(f"Veritabanı oluşturuldu: {DEFAULT_DB_PATH}")
    for table, n in counts.items():
        print(f"  {table:<16} {n:>4} satır")


if __name__ == "__main__":
    main()
