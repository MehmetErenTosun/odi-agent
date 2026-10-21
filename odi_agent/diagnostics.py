"""Oracle teşhis şablonları: yükleme, SQL güvenlik doğrulaması, yetki kontrolü, çalıştırma.

Şablonlar diagnostics.json'dan, şirketin verdiği yetkiler yetkiler.json'dan okunur.
Gerçek Oracle bağlantısı yok: DemoCalistirici SQLite'taki uydurma sonuçları döner.
Teşhis sonucu sınıflama rengini değiştirmez. Görünüm ve kolon adları doğrulanmadı,
bkz. docs/KOLON_KAYNAKLARI.md ("Oracle teşhis görünümleri").
"""

import json
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

from odi_agent.classifier import ORA_CODE
from odi_agent.schema_map import DiagResult

SABLON_PATH = Path(__file__).with_name("diagnostics.json")
YETKI_PATH = Path(__file__).with_name("yetkiler.json")
YETKI_ENV = "ODI_YETKILER"  # testler ve farklı ortamlar için yol değiştirme

DEMO_KAYNAK = "demo verisi"
DURUM_CALISTI = "çalıştı"
DURUM_YETKISIZ = "yetki tanımlı değil"

ZORUNLU_ALANLAR = ("ad", "aciklama", "tetikleyen_kodlar", "sql", "gorunumler",
                   "gereken_yetki", "parametreler")

# Doğrulayıcı ikinci savunma hattıdır; asıl güvence Oracle'da yalnızca SELECT yetkili kullanıcıdır.
YASAK_KELIMELER = ("INSERT", "UPDATE", "DELETE", "MERGE", "CREATE", "ALTER", "DROP", "TRUNCATE",
                   "RENAME", "GRANT", "REVOKE", "COMMENT", "BEGIN", "DECLARE", "EXEC", "EXECUTE",
                   "CALL", "LOCK", "COMMIT", "ROLLBACK", "SAVEPOINT", "INTO", "WITH", "FUNCTION",
                   "PROCEDURE")
YASAK_ISARETLER = ((";", "noktalı virgül (ikinci deyim)"), ("--", "yorum"), ("/*", "yorum"),
                   ("'", "metin sabiti"), ('"', "tırnaklı ad"), ("@", "database link"))
_YASAK_KELIME = re.compile(r"\b(" + "|".join(YASAK_KELIMELER) + r")\b", re.IGNORECASE)
_FOR_UPDATE = re.compile(r"\bFOR\s+UPDATE\b", re.IGNORECASE)
_PAKET = re.compile(r"\b(DBMS|UTL)_\w*", re.IGNORECASE)
_ILK_SELECT = re.compile(r"\s*SELECT\b", re.IGNORECASE)
_BIND = re.compile(r":(\w+)")


class GuvenlikHatasi(ValueError):
    pass


class SablonHatasi(ValueError):
    pass


@dataclass
class Sablon:
    ad: str
    aciklama: str
    tetikleyen_kodlar: list[str]
    sql: str
    gorunumler: dict[str, list[str]]
    gereken_yetki: list[str]
    parametreler: list[str]


@dataclass
class Yetkiler:
    verilen: frozenset[str] = frozenset()
    hata: str | None = None  # dosya okunamadıysa sebep; o durumda verilen boştur


@dataclass
class TeshisSonucu:
    sablon_adi: str
    durum: str
    satirlar: list[dict] = field(default_factory=list)
    kaynak: str | None = None
    neden: str | None = None


def sql_dogrula(sql):
    """Yalnızca tek bir, yorum ve metin sabiti içermeyen SELECT deyimine izin verir."""
    if not isinstance(sql, str) or not sql.strip():
        raise GuvenlikHatasi("SQL boş")
    if not sql.isascii():
        raise GuvenlikHatasi("SQL'de ASCII dışı karakter var")
    for isaret, neden in YASAK_ISARETLER:
        if isaret in sql:
            raise GuvenlikHatasi(f"Yasak: {neden} ({isaret})")
    if not _ILK_SELECT.match(sql):
        raise GuvenlikHatasi("SQL SELECT ile başlamalı")
    if _FOR_UPDATE.search(sql):
        raise GuvenlikHatasi("Yasak: FOR UPDATE")
    for desen in (_YASAK_KELIME, _PAKET):
        m = desen.search(sql)
        if m:
            raise GuvenlikHatasi(f"Yasak kelime: {m.group(0)}")


def _sablon_olustur(ham):
    if not isinstance(ham, dict):
        raise SablonHatasi("Şablon bir sözlük olmalı")
    ad = ham.get("ad", "?")
    eksik = [k for k in ZORUNLU_ALANLAR if k not in ham]
    if eksik:
        raise SablonHatasi(f"{ad}: eksik alan: {', '.join(eksik)}")
    for k in ("tetikleyen_kodlar", "gereken_yetki", "parametreler"):
        if not isinstance(ham[k], list) or not all(isinstance(x, str) for x in ham[k]):
            raise SablonHatasi(f"{ad}: {k} metin listesi olmalı")
    if not isinstance(ham["gorunumler"], dict) or not ham["gorunumler"]:
        raise SablonHatasi(f"{ad}: gorunumler boş olmayan bir sözlük olmalı")
    if not ham["gereken_yetki"]:
        raise SablonHatasi(f"{ad}: gereken_yetki boş olamaz")
    gecersiz = [k for k in ham["tetikleyen_kodlar"] if not ORA_CODE.fullmatch(k)]
    if gecersiz or not ham["tetikleyen_kodlar"]:
        raise SablonHatasi(f"{ad}: geçersiz tetikleyen_kodlar: {gecersiz}")
    try:
        sql_dogrula(ham["sql"])
    except GuvenlikHatasi as e:
        raise SablonHatasi(f"{ad}: {e}") from e
    if set(_BIND.findall(ham["sql"])) != set(ham["parametreler"]):
        raise SablonHatasi(f"{ad}: SQL'deki bind adları parametreler ile aynı değil")
    return Sablon(**{k: ham[k] for k in ZORUNLU_ALANLAR})


def sablonlari_yukle(path=SABLON_PATH):
    """Şablon dosyasını okur. Tek bir şablon bile hatalıysa hiçbiri yüklenmez."""
    try:
        veri = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise SablonHatasi(f"Şablon dosyası okunamadı: {e}") from e
    if not isinstance(veri, dict) or not isinstance(veri.get("sablonlar"), list):
        raise SablonHatasi("Şablon dosyasında 'sablonlar' listesi yok")
    sablonlar = [_sablon_olustur(ham) for ham in veri["sablonlar"]]
    adlar = [s.ad for s in sablonlar]
    tekrar = sorted({a for a in adlar if adlar.count(a) > 1})
    if tekrar:
        raise SablonHatasi(f"Aynı ad birden fazla: {', '.join(tekrar)}")
    return sablonlar


def uygun_sablonlar(sablonlar, hata_kodu, asil_sebep):
    """Hata kodu ya da asıl sebebi şablonun tetikleyen kodlarında olan şablonlar."""
    kodlar = {k for k in (hata_kodu, asil_sebep) if k}
    return [s for s in sablonlar if kodlar & set(s.tetikleyen_kodlar)]


def yetkileri_yukle(path=None):
    """yetkiler.json'u okur. Dosya eksik ya da bozuksa hiçbir yetki verilmemiş sayılır.
    Yalnızca JSON true değeri yetki sayılır ("true" ya da 1 sayılmaz)."""
    path = Path(path or os.environ.get(YETKI_ENV) or YETKI_PATH)
    try:
        veri = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return Yetkiler(hata=f"{path.name} okunamadı ({type(e).__name__}); hiçbir şablon çalışmaz")
    if not isinstance(veri, dict) or not isinstance(veri.get("yetkiler"), dict):
        return Yetkiler(hata=f"{path.name} biçimi bozuk; hiçbir şablon çalışmaz")
    return Yetkiler(frozenset(k for k, v in veri["yetkiler"].items() if v is True))


def eksik_yetkiler(sablon, yetkiler):
    return [y for y in sablon.gereken_yetki if y not in yetkiler.verilen]


class Calistirici(ABC):
    """Şablon çalıştırıcı arayüzü. SQL her çağrıda yeniden doğrulanır.

    OracleCalistirici bu adımda yazılmadı; gerçek bağlantı _sorgula'yı uygulayacak.
    """

    def calistir(self, sablon, parametreler=None):
        parametreler = parametreler or {}
        sql_dogrula(sablon.sql)
        if set(parametreler) != set(sablon.parametreler):
            raise SablonHatasi(f"{sablon.ad}: beklenen parametreler {sablon.parametreler}, "
                               f"gelen {sorted(parametreler)}")
        return self._sorgula(sablon, parametreler)

    @abstractmethod
    def _sorgula(self, sablon, parametreler):
        ...


class DemoCalistirici(Calistirici):
    """Şablonun SQL'ini çalıştırmaz; DEMO_DIAG_SONUC'taki uydurma satırları döner."""

    def __init__(self, conn):
        self.conn = conn

    def _sorgula(self, sablon, parametreler):
        d = DiagResult
        sql = f"""
            SELECT {d.ROW_JSON} FROM {d.TABLE}
            WHERE {d.TEMPLATE} = ? ORDER BY {d.ROW_NO}"""
        satirlar = [json.loads(r[0]) for r in self.conn.execute(sql, (sablon.ad,))]
        return TeshisSonucu(sablon.ad, DURUM_CALISTI, satirlar, DEMO_KAYNAK)


def teshis_yap(sablonlar, yetkiler, calistirici):
    """Yetkisi tanımlı şablonları çalıştırır, diğerlerini çalıştırıcıya hiç vermeden atlar."""
    sonuclar = []
    for s in sablonlar:
        eksik = eksik_yetkiler(s, yetkiler)
        if eksik:
            neden = yetkiler.hata or f"Tanımlı değil: {', '.join(eksik)}"
            sonuclar.append(TeshisSonucu(s.ad, DURUM_YETKISIZ, neden=neden))
        else:
            sonuclar.append(calistirici.calistir(s, {}))
    return sonuclar
