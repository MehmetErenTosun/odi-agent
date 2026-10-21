# ODI Error Triage Agent (Demo)

When an overnight ETL load fails in an Oracle Data Integrator (ODI) 12c data warehouse, someone on call has to answer three questions fast: *Is it safe to just restart? Has this happened before, and how was it fixed? What is the database actually doing right now?* This project is a working demo of an agent that helps answer those questions, on synthetic data.

## What it does

- **Classifies every failed step** as 🔴 RED (do not touch), 🟠 ORANGE (needs human approval) or 🟢 GREEN (safe to retry, with a limited number of retries). Rules live in a config file (`rules.json`), not in code, and every result comes with the chain of rules that produced it.
- **Never lets a risky step look safe.** Incremental-append steps are capped at ORANGE because a blind restart can load the same data twice. The cap is enforced in code: if someone edits the config to mark them GREEN, the config is rejected at load time.
- **Finds the real error.** Oracle often wraps the root cause in a generic error (for example `ORA-12801`, parallel query failed). The agent unwraps it, skips noise lines such as `ORA-06512`, and classifies by the underlying cause. If the cause cannot be found, the step can never be GREEN.
- **Matches past fixes the right way.** The same error code can mean different things in different steps. History is grouped into: same step and same cause, same step but different cause (flagged as "fix may not apply"), and different step (flagged).
- **Defines read-only diagnostic queries** for locks, tablespace/TEMP usage and parallel servers. Every query passes a SQL validator first (single `SELECT` only; no semicolons, comments, string literals, `FOR UPDATE`, DML/DDL, PL/SQL, `DBMS_`/`UTL_` calls, or database links). Which diagnostics may run is decided by the DBA in `yetkiler.json`; if the file is missing or broken, nothing runs. In this demo the SQL is never executed against Oracle: the results are synthetic rows labelled as demo data.
- **Shows it all in a Streamlit panel**, bound to localhost only, with a permanent "synthetic data" banner.

## Engineering notes

- 105 automated tests, including 30 adversarial SQL inputs for the validator.
- The agent code reads ODI table and column names from one module (`schema_map.py`).
- Every Oracle table, view and column name is marked **unverified** in `docs/KOLON_KAYNAKLARI.md`. Nothing is presented as verified without a source.
- The project code makes no AI or external service calls. (Streamlit's own internal behaviour was not audited; its usage statistics are turned off.)

## Status and limitations

This is a demo, not a production tool. All data is synthetic and it has never been connected to a real Oracle database. Automatic restart is planned, not built: today the colors are shown only as recommendations. The diagnostic queries are untested against real Oracle. The main remaining safeguard to design for production is a dedicated Oracle user with SELECT-only grants. Full list in the "Gizlilik ve yetki" section below.

## Background

Built by Mehmet Eren Tosun. The idea comes from my data warehouse internship, where I worked hands-on with Oracle ODI 12c and PL/SQL: analysing mappings, investigating data quality issues, tracking failed loads in ODI Operator and covering overnight production monitoring shifts. Each rule in this project encodes a judgement that an on-call engineer otherwise makes by hand during an overnight failure. No code, schema or data from that internship is used; everything here is synthetic. Developed with Claude Code: I set the design, safety rules and test criteria, and reviewed every plan before implementation.

*Türkçe açıklama aşağıda.*

# ODI Hata Teşhis Ajanı (Demo)

Oracle ODI 12c için hata teşhis ve otomatik müdahale (planlanan, henüz yok) ajanının demo sürümü. Ayrıntılar `CLAUDE.md`'de.

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

## Gizlilik ve yetki

Kısa özet: bu demo hiçbir yere veri göndermez, hiçbir şeyi değiştirmez ve gerçek bir sisteme bağlı değildir.

### 1. Ajan neyi okur?

- Demo veritabanındaki altı tablo. ODI'nin log tablolarını taklit eden üçü: oturumlar (`SNP_SESSION`), adımlar (`SNP_SESS_STEP`), adım logları (`SNP_STEP_LOG`). Demo için uydurulan üçü: adımların yükleme tipi (`DEMO_STEP_INFO`), geçmiş çözümler (`DEMO_RESOLUTION`) ve teşhis sonuçları (`DEMO_DIAG_SONUC`).
- Teşhis için dört Oracle görünümü tasarlandı: `V$SESSION`, `DBA_TABLESPACE_USAGE_METRICS`, `DBA_TEMP_FREE_SPACE`, `V$PX_SESSION`. **Demoda bunlar okunmaz**; yerine uydurma sonuçlar (`DEMO_DIAG_SONUC`) gösterilir.
- Demo veritabanı salt okunur modda açılır (SQLite `mode=ro`): panel yazmak istese bile yazamaz. Gerçek Oracle bağlantısı henüz yok; ileride yazılırsa salt okunur olması, bağlanılan kullanıcının yetkisine bağlı olacak (madde 2).

### 2. Ajan neyi asla yapmaz?

- Veri yazmaz, silmez, tablo oluşturmaz ya da değiştirmez (yazma/değiştirme komutları, yani DML/DDL yok). Ajanın kodunda yazan hiçbir sorgu yok; `INSERT` yalnızca demo veriyi hazırlayan ayrı betikte (`seed.py`).
- Hataları otomatik **yeniden çalıştırmaz** (restart). Bu özellik henüz yazılmadı. Renkler (kırmızı/turuncu/yeşil) şu an yalnızca öneri olarak gösterilir.
- Bir **SQL doğrulayıcı** vardır: teşhis sorgusu çalışmadan önce yalnızca tek bir okuma sorgusu (SELECT) olup olmadığına bakar; noktalı virgül, yorum, metin sabiti, `FOR UPDATE`, yazma/PL-SQL kelimeleri ve `DBMS_`/`UTL_` paketlerini reddeder.
- **Ama bu ikinci savunma hattıdır.** Örneğin başka bir şemadaki, yan etkili bir kullanıcı fonksiyonunun SELECT içinden çağrılmasını yakalayamaz. **Asıl güvence**, gerçek sistemde ajanın Oracle'a yalnızca teşhis görünümlerine SELECT yetkisi olan, başka hiçbir yetkisi olmayan ayrı bir kullanıcıyla bağlanmasıdır. Bu kullanıcı henüz yok; kurulması gerekir.

### 3. Ne dışarı çıkar?

- **Şu an hiçbir şey.** Projede hiçbir yapay zekâ (AI) ya da dış servis çağrısı yok. Veri bu bilgisayarın dışına gitmez.
- Kurulum sırasında paketler internetten indirilir (`pip install`). Çalışma anında ajan ağa veri göndermez. Streamlit'in iç davranışı ayrıca denetlenmedi; yalnızca kullanım istatistiği toplamanın kapalı olduğu doğrulandı.
- Panel yalnızca bu bilgisayardan açılır (`127.0.0.1`); aynı ağdaki başka cihazlar erişemez.
- `.env.example` dosyasında boş bir `ANTHROPIC_API_KEY` satırı vardır; bu ileride kullanılmak üzere ayrılmış bir yer tutucudur, **hiçbir kod onu okumaz**.
- *Planlanan, henüz yok:* İleride AI eklenirse dışarı yalnızca hata mesajı, adım adı ve teşhis sonucu gidecek; veri satırları gitmeyecek. Bu bir tasarım niyetidir, kodda karşılığı yoktur ve eklendiğinde bu bölüm güncellenmelidir.

### 4. Yetkiyi kim belirler?

- Şirketin veritabanı yöneticisi (DBA), `odi_agent/yetkiler.json` dosyasıyla. Ajan yalnızca orada `true` yazan yetkiye sahip şablonları çalıştırır; kalanları "yetki tanımlı değil" diyerek atlar.
- Dosya yoksa ya da bozuksa **hiçbir teşhis çalışmaz** (varsayılan: hepsi kapalı). `"true"` (metin) ya da `1` gibi değerler yetki sayılmaz.
- Not: depodaki demo dosyasında üç yetki açık, biri (`V$PX_SESSION`) bilerek kapalıdır; kapalı durumu panelde göstermek için.

### 5. Ajan neyi bilemez?

- Yetkinin Oracle'da **gerçekten** verilip verilmediğini bilemez; yalnızca `yetkiler.json`'a güvenir. Dosya yanlışsa ajan yanılır.
- Teşhis sorguları gerçek Oracle'da **hiç denenmedi**. Görünüm ve kolon adları resmi dokümanla **doğrulanmadı**. Aynı şekilde `SNP_` ile başlayan ODI tablo ve kolon adları da doğrulanmadı (`docs/KOLON_KAYNAKLARI.md`).
- Gerçek sistemde yetki hatası (ör. ORA-00942) dönerse bunun "yetki eksik" diye raporlanması gerekir; bu davranış demoda yok ve denenmedi.
- Teşhis sorguları veritabanının genel durumuna bakar; hata veren ODI oturumunu veritabanı oturumuyla eşleştirmez.

### 6. Bu bir demo

Tüm isimler, mesajlar, kişiler ve sonuçlar uydurmadır. Gerçek bir sisteme bağlanılmadı. Panelde sabit bir uyarı bunu hatırlatır.

## Çalıştırma

Python 3.10+ gerekir. Yalnızca panel dış paket (Streamlit) kullanır; veri, sınıflama ve testler standart kütüphane ile çalışır.

```
pip install -r requirements.txt            # yalnızca panel için
python -m odi_agent.seed                   # data/odi_demo.db oluşturur
python -m unittest -v                      # testler
python -m streamlit run odi_agent/panel.py # paneli açar (proje kökünden)
```

Panel salt okunurdur: veritabanına yazmaz, yalnızca `classifier.py`, `history.py` ve teşhis sonuçlarını gösterir. Teşhis bölümündeki veriler demo verisidir, gerçek sistemden alınmadı. Seed'i bu sürümden önce çalıştırdıysan yeniden çalıştır (`DEMO_DIAG_SONUC` tablosu eklendi). Komutu `streamlit run` yerine `python -m streamlit run` olarak çalıştırmak gerekir; böylece proje kökü import yoluna eklenir.
