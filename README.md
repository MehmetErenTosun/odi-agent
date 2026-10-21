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
