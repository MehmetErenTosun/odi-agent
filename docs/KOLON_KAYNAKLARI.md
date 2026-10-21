# Kolon Kaynakları

Bu demo, ODI 12c work repository log tablolarını taklit eder. ODI repository'nin kolon kolon resmi tanımı Oracle'ın herkese açık dokümantasyonunda (docs.oracle.com) **yok**. Bu tanım yalnızca My Oracle Support'taki **Doc ID 1903225.1** ("Oracle Data Integrator 11g and 12c Repository Description") notunda yer alıyor. Not giriş gerektirdiği için okunamadı. Bu notun varlığını da yalnızca topluluk yazılarından biliyoruz.

**Bu yüzden aşağıdaki kolonların hiçbiri resmi kaynakla doğrulanmadı.**

## Durum değerleri

- `doğrulandı (resmi)`: Oracle'ın resmi kaynağıyla karşılaştırıldı.
- `doğrulanmadı (topluluk kaynağı)`: Resmi değil. "Dayanak" sütunu, hangi topluluk kaynağında görüldüğünü ya da hiç görülmediğini söyler.
- `doğrulanmadı (model bilgisi)`: Hiçbir kaynakla karşılaştırılmadı; yalnızca Claude'un genel Oracle bilgisine dayanır. Oracle teşhis görünümleri bölümünde kullanılır.

## Kaynaklar

- **[G]** rmorenobello, "Oracle Data Integrator (ODI) - useful queries" (GitHub gist). Gerçek bir repository'ye yazılmış SQL sorguları içeriyor. https://gist.github.com/rmorenobello/0d8add698f70c53020665faf9b813a27
- **[W]** odirepo.wikidot.com, `SNP_SESS_TASK_LOG` sayfası. Kolon listesi ve açıklamalar var; ODI sürümü belirtilmemiş. http://odirepo.wikidot.com/snp-sess-task-log
- **[C]** ClearPeaks, "ETL Monitoring Dashboard in OBIEE using ODI tables". https://clearpeaks.com/?p=26043
- **[D]** DevEPM, "ODI Hidden Gems". Doc ID 1903225.1'i işaret ediyor. https://devepm.wordpress.com/2020/02/26/odi-hidden-gems-snp-tables-query-to-get-executed-code-example/

"Model bilgisi" yazan satırlar, yukarıdaki kaynaklarda görülmeyip Claude'un genel ODI bilgisinden gelen adlardır. En zayıf dayanak bunlardır.

## SNP_SESSION

| Kolon | Durum | Dayanak |
|---|---|---|
| SESS_NO | doğrulanmadı (topluluk kaynağı) | [G] sorgularında, [C] metninde |
| SESS_NAME | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| SESS_BEG | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| SESS_END | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| SESS_DUR | doğrulanmadı (topluluk kaynağı) | [G]'de yalnızca `SNP_SCEN_REPORT.SESS_DUR` var; SNP_SESSION'da görülmedi |
| SESS_STATUS | doğrulanmadı (topluluk kaynağı) | [G] sorgularında; değerler [C]'den |
| SESS_RC | doğrulanmadı (topluluk kaynağı) | Kaynaklarda görülmedi, model bilgisi |
| SESS_MESS | doğrulanmadı (topluluk kaynağı) | Kaynaklarda görülmedi, model bilgisi |
| AGENT_NAME | doğrulanmadı (topluluk kaynağı) | Kaynaklarda görülmedi, model bilgisi |
| CONTEXT_CODE | doğrulanmadı (topluluk kaynağı) | [G]'de yalnızca `SNP_SCEN_REPORT.CONTEXT_CODE` var |

Durum kodları ([C]): `D` Done, `R` Running, `W` Waiting, `E` Error, `M` Warning, `A` Done in previous run. Durum: doğrulanmadı.

## SNP_SESS_STEP

| Kolon | Durum | Dayanak |
|---|---|---|
| SESS_NO | doğrulanmadı (topluluk kaynağı) | Model bilgisi |
| NNO | doğrulanmadı (topluluk kaynağı) | Model bilgisi |
| STEP_NAME | doğrulanmadı (topluluk kaynağı) | Model bilgisi |

**Uyarı:** Bu tablo ODI 12c'de olmayabilir. Ayrıntılar "Bilinen belirsizlikler" bölümünde (madde 1).

## SNP_STEP_LOG

| Kolon | Durum | Dayanak |
|---|---|---|
| SESS_NO | doğrulanmadı (topluluk kaynağı) | [G] join anahtarı |
| NNO | doğrulanmadı (topluluk kaynağı) | [G] join anahtarı |
| NB_RUN | doğrulanmadı (topluluk kaynağı) | [G] join anahtarı |
| STEP_BEG | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| STEP_END | doğrulanmadı (topluluk kaynağı) | [G], yorum satırında |
| STEP_DUR | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| STEP_STATUS | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |
| STEP_RC | doğrulanmadı (topluluk kaynağı) | Kaynaklarda görülmedi; [W]'deki `TASK_RC`'ye benzetildi |
| STEP_MESS | doğrulanmadı (topluluk kaynağı) | Kaynaklarda görülmedi. [G] hata metnini `ERROR_MESSAGE` kolonundan alıyor; [W]'de `TASK_MESS` ve `ERROR_MESSAGE` birlikte var |
| NB_ROW | doğrulanmadı (topluluk kaynağı) | [G], yorum satırında; [W]'de task log için |
| NB_INS | doğrulanmadı (topluluk kaynağı) | [G], yorum satırında; [W]'de task log için |
| NB_UPD | doğrulanmadı (topluluk kaynağı) | [G], yorum satırında; [W]'de task log için |
| NB_DEL | doğrulanmadı (topluluk kaynağı) | [G], yorum satırında; [W]'de task log için |
| NB_ERR | doğrulanmadı (topluluk kaynağı) | [G] sorgularında |

## Bilinen belirsizlikler

Şema bu belirsizlikler çözülene kadar **değiştirilmeyecek**. Doğrulamayı proje sahibi yapacak.

1. **`SNP_SESS_STEP` ODI 12c'de olmayabilir.**
   - Bir topluluk yorumunda, bu tabloyu kullanan bir sorgunun 12c'de çalışmadığı söyleniyor. Yorum, [D]'yi bulan aramanın sonuçlarında geçiyordu; yorumun kaynak sayfası ayrıca okunmadı.
   - [G]'deki 12c sorgularında bu tablo hiç geçmiyor.
2. **Alternatif: `SNP_SB_STEP`.**
   - [G]'deki 12c sorguları adım adını `SNP_SB_STEP.STEP_NAME`'den alıyor ve `SNP_SB_TASK` ile join ediyor.
   - "SB" büyük ihtimalle "session blueprint" anlamına geliyor (doğrulanmadı).
   - Bu tablonun kolonları ve `SNP_STEP_LOG` ile nasıl bağlandığı (`SESS_NO`/`NNO` mu, başka bir anahtar mı) bilinmiyor.
3. **Hata metni `ERROR_MESSAGE` kolonundan okunuyor olabilir.**
   - [G], adım seviyesindeki hata metnini `SNP_STEP_LOG.ERROR_MESSAGE`'dan okuyor. Demo'daki `STEP_MESS` hiçbir kaynakta görülmedi.
   - [W]'de task log için hem `TASK_MESS` hem `ERROR_MESSAGE` var. Adım logunda da ikisinin birlikte olması mümkün; hangisinin tam metni tuttuğu bilinmiyor.
4. **Hiçbir kaynakta görülmeyen kolonlar.** Bunlar yalnızca model bilgisine dayanıyor:
   - `SNP_SESSION`: `SESS_RC`, `SESS_MESS`, `AGENT_NAME`
   - `SNP_STEP_LOG`: `STEP_RC`, `STEP_MESS`
   - `SNP_SESS_STEP`: `SESS_NO`, `NNO`, `STEP_NAME`. Tablonun kendisi de belirsiz, bkz. madde 1.
5. **Başka tablolarda görülen kolonlar.**
   - `SESS_DUR` ve `CONTEXT_CODE`, [G]'de yalnızca `SNP_SCEN_REPORT` tablosunda görüldü.
   - `SNP_SESSION`'da olup olmadıkları bilinmiyor.

## İleride

- `SNP_SESS_TASK_LOG` (görev seviyesi log): Kapsam küçük kalsın diye eklenmedi. [W]'de kolon listesi var (TASK_STATUS, TASK_RC, TASK_MESS, ERROR_MESSAGE, NB_ROW...).

## Oracle teşhis görünümleri

`odi_agent/diagnostics.json`'daki teşhis şablonlarının kullandığı Oracle sözlük görünümleri, kolonları ve yetki adları.

**Hiçbiri resmi Oracle dokümanıyla karşılaştırılmadı.** Bu adımda Oracle Database Reference açılıp kontrol edilmedi. Proje sahibi stajda ODI repository'sine ve Oracle sözlük görünümlerine hiç erişemedi (stajyer yetkisiyle mümkün değildi); yalnızca ODI Operator arayüzünden hata mesajlarına baktı. Bu yüzden hiçbir ad kullanıcı deneyimiyle doğrulanmış sayılmaz. Sorgular gerçek bir Oracle veritabanında hiç çalıştırılmadı.

### V$SESSION (şablon: `kilit_durumu`)

| Kolon | Durum | Dayanak |
|---|---|---|
| SID | doğrulanmadı (model bilgisi) | Model bilgisi |
| SERIAL# | doğrulanmadı (model bilgisi) | Model bilgisi |
| USERNAME | doğrulanmadı (model bilgisi) | Model bilgisi |
| STATUS | doğrulanmadı (model bilgisi) | Model bilgisi |
| EVENT | doğrulanmadı (model bilgisi) | Model bilgisi |
| BLOCKING_SESSION | doğrulanmadı (model bilgisi) | Model bilgisi |
| SQL_ID | doğrulanmadı (model bilgisi) | Model bilgisi |

### DBA_TABLESPACE_USAGE_METRICS (şablon: `tablespace_doluluk`)

| Kolon | Durum | Dayanak |
|---|---|---|
| TABLESPACE_NAME | doğrulanmadı (model bilgisi) | Model bilgisi |
| USED_SPACE | doğrulanmadı (model bilgisi) | Model bilgisi; birimin blok olduğu da doğrulanmadı |
| TABLESPACE_SIZE | doğrulanmadı (model bilgisi) | Model bilgisi; birimin blok olduğu da doğrulanmadı |
| USED_PERCENT | doğrulanmadı (model bilgisi) | Model bilgisi |

### DBA_TEMP_FREE_SPACE (şablon: `temp_doluluk`)

| Kolon | Durum | Dayanak |
|---|---|---|
| TABLESPACE_NAME | doğrulanmadı (model bilgisi) | Model bilgisi |
| TABLESPACE_SIZE | doğrulanmadı (model bilgisi) | Model bilgisi; birimin bayt olduğu da doğrulanmadı |
| ALLOCATED_SPACE | doğrulanmadı (model bilgisi) | Model bilgisi |
| FREE_SPACE | doğrulanmadı (model bilgisi) | Model bilgisi |

### V$PX_SESSION (şablon: `paralel_sunucu_kullanimi`)

| Kolon | Durum | Dayanak |
|---|---|---|
| QCSID | doğrulanmadı (model bilgisi) | Model bilgisi |
| DEGREE | doğrulanmadı (model bilgisi) | Model bilgisi |
| REQ_DEGREE | doğrulanmadı (model bilgisi) | Model bilgisi |

Sorgudaki `COUNT(*)` koordinatör oturumu da sayıyor olabilir; doğrulanmadı.

### Yetki adları (`yetkiler.json`)

| Yetki | Durum | Dayanak |
|---|---|---|
| SELECT ON V_$SESSION | doğrulanmadı (model bilgisi) | `V$` adlarının `V_$` nesnelerine bakan public synonym olduğu ve yetkinin `V_$` üzerine verildiği model bilgisi |
| SELECT ON DBA_TABLESPACE_USAGE_METRICS | doğrulanmadı (model bilgisi) | Model bilgisi |
| SELECT ON DBA_TEMP_FREE_SPACE | doğrulanmadı (model bilgisi) | Model bilgisi |
| SELECT ON V_$PX_SESSION | doğrulanmadı (model bilgisi) | Model bilgisi |

`SELECT_CATALOG_ROLE` gibi bir rolün bunların hepsini kapsayıp kapsamadığı da doğrulanmadı.

### Sınırlamalar

1. **SQL doğrulayıcısı ikinci savunma hattıdır.** Yasak kelime listesi, başka bir şemadaki kullanıcı fonksiyonunun SELECT içinden çağrılmasını (yan etkili olabilir) yakalayamaz; yalnızca `DBMS_` ve `UTL_` paketlerini engeller. Asıl güvence: gerçek sistemde ajan Oracle'a, yalnızca teşhis görünümlerine SELECT yetkisi olan ve başka hiçbir yetkisi olmayan ayrı bir kullanıcıyla bağlanmalıdır.
2. **Şablonlar veritabanının genel durumunu sorgular.** Hata veren ODI oturumunu veritabanı oturumuyla eşleştirmez (parametreler boş). Gerçek sistemde bu eşleştirme ayrıca tasarlanmalıdır.

### Nasıl doğrulanır

1. Oracle Database Reference'ta (docs.oracle.com) her görünümün sayfasını aç, kolonları bu listeyle karşılaştır, **ya da**
2. Kişisel bir test veritabanında `DESCRIBE V$SESSION` gibi komutlar çalıştır. Şirket ortamını kullanma.
3. Eşleşen satırın durumunu `doğrulandı (resmi)` yap. Farklıysa bu dosyayı, `diagnostics.json`'u ve `seed.py`'deki `DIAG_RESULTS`'u birlikte düzelt.

## Demo'ya özel tablolar (ODI'de yok)

`DEMO_STEP_INFO`, `DEMO_RESOLUTION` ve `DEMO_DIAG_SONUC` bu proje için uyduruldu, doğrulama gerekmez.

## Nasıl doğrulanır

1. MOS Doc ID 1903225.1'i aç ve kolonları bu listeyle karşılaştır, **ya da**
2. Kişisel bir test ODI 12c ortamında `DESCRIBE SNP_SESSION` gibi komutlar çalıştır. Şirket ortamını kullanma.
3. Eşleşen satırın durumunu `doğrulandı (resmi)` yap. Farklıysa hem bu dosyayı hem `odi_agent/schema.sql`'i düzelt.
