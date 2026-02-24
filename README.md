# Hisse Senedi Sinyal Çekici ve E-posta Bildirimi

Bu proje, yapılandırılabilir URL'lerden hisse senedi sinyal verilerini çeker ve son 3 iş gününe (hafta sonları hariç) ait sinyalleri içeren günlük e-posta bildirimlerini HTML tablo biçiminde birden çok alıcıya gönderir.

## Özellikler
- **Profesyonel Kod Yapısı**: Modüler, okunabilir ve bakımı kolay bir yapıya sahiptir. Loglama, yapılandırma sınıfı ve yardımcı fonksiyonlar içerir.
- **Veri Çekme (Data Scraping)**: `Config.STOCK_LIST_URL` ve ortam değişkenleri (`SCRAPE_URL`, `SCRAPE_CMI_URL`) üzerinden hisse senedi sinyallerini çeker.
- **Mobil Uyumlu E-posta Şablonu**: E-posta şablonu, tabloların mobil cihazlarda yatay olarak kaydırılabilmesini sağlayacak şekilde duyarlı hale getirilmiştir.
- **Gemini AI Analizi**: E-postadaki yasal uyarının üzerinde, en güncel (son 48 saat) hisse senedi sinyalleri için `gemini-1.5-pro` modelini kullanarak doğrudan sonuca odaklı ve net bir analiz eklenir. Markdown işaretleri temizlenir ve analiz Türkçe olarak sunulur.
- **İş Günü Filtresi**: Yalnızca son 3 iş gününe (Pazartesi'den Cuma'ya) ait sinyalleri içerir.
- **Dinamik Hisse Senedi Listesi**: GitHub'dan çekilen katılım endeksi hisse senedi listesiyle filtreleme yapar.
- **Mükerrer Kayıt Temizliği**: Her hisse senedi için sadece en güncel sinyal gösterilir.
- **Birden Çok Alıcı**: `TO_EMAIL` içinde belirtilen birden çok alıcıya e-posta gönderir.
- **HTML E-posta**: Sinyalleri stilize edilmiş bir HTML tablosu olarak biçimlendirir.
- **Gelişmiş Hata Yönetimi ve Loglama**: İstisnaları yakalar ve detaylı log bilgileri sağlar.

## Ön Koşullar
- Python 3.11+
- `requirements.txt` dosyasındaki gerekli Python paketleri:
  - `requests`
  - `beautifulsoup4`
  - `pandas`
  - `google-genai`
  - `lxml`
- **Uygulama Şifresi olan bir Gmail hesabı** (Gmail SMTP kullanılıyorsa).

## Kurulum
1. **Depoyu Klonlayın**:
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **`requirements.txt` Oluşturun**:
   Proje dizininde aşağıdaki içeriğe sahip bir `requirements.txt` dosyası oluşturun:
   ```
   requests>=2.28.0
   beautifulsoup4>=4.11.0
   pandas>=1.5.0
   google-genai>=0.3.0
   lxml>=4.9.0
   ```

3. **GitHub Secrets'ı Yapılandırın**:
   Aşağıdaki ortam değişkenlerini GitHub deponuzun Secrets bölümüne ekleyin:
   - `EMAIL_USER`: E-posta göndermek için kullanılacak e-posta adresiniz.
   - `EMAIL_PASSWORD`: E-posta hesabınızın uygulama şifresi.
   - `TO_EMAIL`: Raporların gönderileceği alıcı e-posta adresleri (virgülle ayrılmış).
   - `SCRAPE_URL`: Agresif hisse sinyallerini çekmek için kullanılacak URL.
   - `SCRAPE_CMI_URL`: CMI/CMF hisse sinyallerini çekmek için kullanılacak URL.
   - `GEMINI_API_KEY`: Gemini AI analizi için API anahtarınız.

   *Not: `SMTP_SERVER` GitHub Secret olarak ayarlanmış olsa da, `main.py` dosyası şu an için SMTP sunucusunu doğrudan `smtp.gmail.com` olarak kullanmaktadır. Eğer farklı bir SMTP sunucusu kullanmak isterseniz `main.py` dosyasında ilgili satırı güncellemeniz gerekecektir.*

4. **Bağımlılıkları Yükleyin**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Kodu Çalıştırın**:
   ```bash
   python main.py
   ```

6. **Ekran Görüntüsü**:
<img width="601" height="475" alt="image" src="https://github.com/user-attachments/assets/c52c5822-2775-44ec-8bbf-650ef80bfbfc" />



Burada paylaşılan bilgiler kendime notlardır ve kesinlikle yatırım tavsiyesi değildir. Tüm yatırım kararlarınızı kendi sorumluluğunuzda alınız.📍
