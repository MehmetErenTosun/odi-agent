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

## Dil ve İletişim

- Programlama dili: Python.
- Açıklamalar Türkçe ve kısa olacak; İngilizce teknik terimler açıklanacak.
- Büyük bir adım atmadan önce ne yapılacağı anlatılacak ve onay istenecek.
