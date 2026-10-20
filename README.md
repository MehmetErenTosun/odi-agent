# ODI Hata Teşhis Ajanı (Demo)

Oracle ODI 12c için hata teşhis ve otomatik müdahale ajanının demo sürümü. Ayrıntılar `CLAUDE.md`'de.

Şu an yalnızca **uydurma örnek veri** hazır. Ajan mantığı henüz yazılmadı.

## Örnek veri

ODI'nin log tablolarını taklit eden küçük bir SQLite veritabanı (`data/odi_demo.db`):

- `SNP_SESSION`, `SNP_SESS_STEP`, `SNP_STEP_LOG`: ODI taklidi. Kolon adları doğrulanmadı, bkz. `docs/KOLON_KAYNAKLARI.md`.
- `DEMO_STEP_INFO`: adımların yükleme tipi (incremental append / full reload / merge).
- `DEMO_RESOLUTION`: geçmiş hataların çözümleri, rengi, çözen kişi ve tarih.

Aynı hata kodu (ör. ORA-12801) farklı adımlarda farklı renk ve çözümle kayıtlıdır. Ajan, cevabını adıma göre seçebilmelidir.

Tüm isimler, mesajlar ve kişiler uydurmadır.

## Çalıştırma

Python 3.10+ yeterli; dış paket yok.

```
python -m odi_agent.seed     # data/odi_demo.db oluşturur
python -m unittest -v        # veri testleri
```
