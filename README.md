# ODI Hata Teşhis Ajanı (Demo)

Oracle ODI 12c için hata teşhis ve otomatik müdahale ajanının demo sürümü. Ayrıntılar `CLAUDE.md`'de.

Hazır olanlar: **uydurma örnek veri**, hata sınıflama (KIRMIZI/TURUNCU/YESIL), geçmiş çözüm eşleştirme, teşhis sorgu iskeleti (yalnızca demo verisiyle) ve salt okunur panel. Gerçek Oracle bağlantısı ve otomatik restart henüz yazılmadı.

## Teşhis

- `odi_agent/diagnostics.json`: Oracle teşhis sorgu şablonları (kilit, tablespace, TEMP, paralel sorgu). Görünüm ve kolon adları doğrulanmadı.
- `odi_agent/yetkiler.json`: şirketin verdiği yetkiler. Yalnızca yetkisi `true` olan şablon çalışır; dosya yoksa ya da bozuksa hiçbiri çalışmaz. Yol `ODI_YETKILER` ortam değişkeniyle değiştirilebilir.
- Her şablon çalıştırılmadan önce bir doğrulayıcıdan geçer: yalnızca tek bir SELECT; noktalı virgül, yorum, metin sabiti, `FOR UPDATE`, DML/DDL/PL-SQL yasak.
- Demoda şablonların SQL'i çalıştırılmaz; sonuçlar `DEMO_DIAG_SONUC` tablosundan gelir ve "demo verisi" etiketlidir.

## Örnek veri

ODI'nin log tablolarını taklit eden küçük bir SQLite veritabanı (`data/odi_demo.db`):

- `SNP_SESSION`, `SNP_SESS_STEP`, `SNP_STEP_LOG`: ODI taklidi. Kolon adları doğrulanmadı, bkz. `docs/KOLON_KAYNAKLARI.md`.
- `DEMO_STEP_INFO`: adımların yükleme tipi (incremental append / full reload / merge).
- `DEMO_RESOLUTION`: geçmiş hataların çözümleri, rengi, çözen kişi ve tarih.
- `DEMO_DIAG_SONUC`: teşhis şablonlarının uydurma sonuçları.

Aynı hata kodu (ör. ORA-12801) farklı adımlarda farklı renk ve çözümle kayıtlıdır. Ajan, cevabını adıma göre seçebilmelidir.

Tüm isimler, mesajlar ve kişiler uydurmadır.

## Çalıştırma

Python 3.10+ gerekir. Yalnızca panel dış paket (Streamlit) kullanır; veri, sınıflama ve testler standart kütüphane ile çalışır.

```
pip install -r requirements.txt            # yalnızca panel için
python -m odi_agent.seed                   # data/odi_demo.db oluşturur
python -m unittest -v                      # testler
python -m streamlit run odi_agent/panel.py # paneli açar (proje kökünden)
```

Panel salt okunurdur: veritabanına yazmaz, yalnızca `classifier.py`, `history.py` ve teşhis sonuçlarını gösterir. Teşhis bölümündeki veriler demo verisidir, gerçek sistemden alınmadı. Seed'i bu sürümden önce çalıştırdıysan yeniden çalıştır (`DEMO_DIAG_SONUC` tablosu eklendi). Komutu `streamlit run` yerine `python -m streamlit run` olarak çalıştırmak gerekir; böylece proje kökü import yoluna eklenir.
