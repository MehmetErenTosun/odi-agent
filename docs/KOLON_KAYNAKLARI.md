# Kolon Kaynakları

Bu demo, ODI 12c work repository log tablolarını taklit eder. ODI repository'nin kolon kolon resmi tanımı Oracle'ın herkese açık dokümantasyonunda (docs.oracle.com) **yok**. Bu tanım yalnızca My Oracle Support'taki **Doc ID 1903225.1** ("Oracle Data Integrator 11g and 12c Repository Description") notunda yer alıyor. Not giriş gerektirdiği için okunamadı. Bu notun varlığını da yalnızca topluluk yazılarından biliyoruz.

**Bu yüzden aşağıdaki kolonların hiçbiri resmi kaynakla doğrulanmadı.**

## Durum değerleri

- `doğrulandı (resmi)`: Oracle'ın resmi kaynağıyla karşılaştırıldı.
- `doğrulanmadı (topluluk kaynağı)`: Resmi değil. "Dayanak" sütunu, hangi topluluk kaynağında görüldüğünü ya da hiç görülmediğini söyler.

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

**Uyarı:** Bu tablonun ODI 12c'de hâlâ kullanıldığı şüpheli. [G]'deki 12c sorguları adım adını `SNP_SB_STEP.STEP_NAME`'den alıyor ("SB" büyük ihtimalle session blueprint). Bir topluluk yorumunda da SNP_SESS_STEP kullanan sorgunun 12c'de çalışmadığı söyleniyor. Doğrulanınca bu tablo `SNP_SB_STEP` ile değiştirilebilir.

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

## İleride

- `SNP_SESS_TASK_LOG` (görev seviyesi log): Kapsam küçük kalsın diye eklenmedi. [W]'de kolon listesi var (TASK_STATUS, TASK_RC, TASK_MESS, ERROR_MESSAGE, NB_ROW...).

## Demo'ya özel tablolar (ODI'de yok)

`DEMO_STEP_INFO` ve `DEMO_RESOLUTION` bu proje için uyduruldu, doğrulama gerekmez.

## Nasıl doğrulanır

1. MOS Doc ID 1903225.1'i aç ve kolonları bu listeyle karşılaştır, **ya da**
2. Kişisel bir test ODI 12c ortamında `DESCRIBE SNP_SESSION` gibi komutlar çalıştır. Şirket ortamını kullanma.
3. Eşleşen satırın durumunu `doğrulandı (resmi)` yap. Farklıysa hem bu dosyayı hem `odi_agent/schema.sql`'i düzelt.
