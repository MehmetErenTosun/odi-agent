# ODI Hata Teşhis Ajanı (Demo)

## Proje

Oracle ODI 12c için hata teşhis ve otomatik müdahale ajanının demo sürümü.

- Hatalı ODI oturumlarını (session) yakalar.
- Geçmişte aynı adımda (step) olan benzer hataları ve çözümlerini gösterir.
- Sistemi yalnızca okuma (read-only) sorgularıyla kontrol edip teşhis koyar ve çözüm önerir.
- Hatalar üç sınıfa ayrılır:
  - **Kırmızı:** Asla dokunma.
  - **Turuncu:** Kullanıcı onayıyla uygula.
  - **Yeşil:** Otomatik uygula, deneme (retry) sayısı sınırlı.
- Restart sonrası satır sayısı (row count) kontrol edilir.
- Incremental append mapping'ler çift yükleme (duplicate load) riski nedeniyle yeşil sayılmaz.

## Amaç

CV ve iş görüşmesi için çalışan bir demo. Kapsam küçük tutulacak.

## Kurallar

- Gerçek bir kuruma ait hiçbir kod, şema veya veri kullanılmayacak; tüm örnek veriler uydurmadır.
- API anahtarları koda yazılmaz, `.env` dosyasında tutulur.
- Tablo ve kolon adlarında Türkçe karakter kullanılmaz (ör. `COZUM_NOTU`, `ÇÖZÜM_NOTU` değil).
- ODI repository tablo/kolon adları resmi kaynakla doğrulanmadıysa uydurulmaz; `docs/KOLON_KAYNAKLARI.md`'de "doğrulanmadı" olarak işaretlenir.

## Bilinen sınırlamalar

- **Sarmalayıcı (wrapper) hata kodları:** ORA-12801 gibi kodlar asıl hatayı sarar. Sınıflayıcı (`odi_agent/classifier.py`), `rules.json`'daki `sarmalayici_kodlar` listesinde olan bir kod görünce rengi mesajdaki asıl sebep koduna göre belirler. Asıl sebep yoksa sonuç YESIL olamaz. **Listede olmayan bir sarmalayıcı kod gelirse sınıflayıcı onu asıl hata sanar.** Yeni sarmalayıcı kodlar listeye eklenmeli. Aynı şekilde, `yoksayilan_kodlar`'da olmayan bir bilgi kodu (ORA-06512 gibi yalnızca satır bilgisi veren) gelirse yanlışlıkla asıl sebep sanılabilir.
- **Geçmiş kaydın asıl sebebi log'dan okunuyor:** `odi_agent/history.py`, geçmiş çözümün asıl sebebini `SNP_STEP_LOG` mesajından okur. Log temizlenirse (purge) sebep görülemez ve kayıt `farkli_sebep` grubuna düşer.

## Dil ve İletişim

- Programlama dili: Python.
- Açıklamalar Türkçe ve kısa olacak; İngilizce teknik terimler açıklanacak.
- Büyük bir adım atmadan önce ne yapılacağı anlatılacak ve onay istenecek.
