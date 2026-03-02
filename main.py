# author: @dipavcisi0007
# source: https://x.com/dipAVCISI007/status/1894070221469577311
# edited by: therkut & Gemini
# BIST Pay Endeksleri - Katılım Filtreli Agresif ve CMI Sinyal Taraması

import os
import smtplib
import requests
import pandas as pd
import time
import re
import logging
from io import StringIO
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None

# --- KONFİGÜRASYON ---
class Config:
    MODEL_ID = "gemini-2.5-flash"
    STOCK_LIST_URL = "https://raw.githubusercontent.com/therkut/bistLists/refs/heads/main/data/stock_xktum_data.csv"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    REQUEST_TIMEOUT = 25
    BUSINESS_DAYS_LOOKBACK = 3
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    SYSTEM_PROMPT = (
        "Sen uzman bir kantitatif finansal analistsin. Verileri doğrudan sonuca odaklanarak yorumlarsın."
    )

def clean_markdown(text):
    """Metindeki tüm Markdown işaretlerini temizler."""
    if not text:
        return ""
    # Yıldızları, alt çizgileri ve kareleri temizle
    text = re.sub(r'[\*\#\_]', '', text)
    # Satır başındaki listeleme işaretlerini güzelleştir
    text = re.sub(r'^\s*[\-\+]\s+', '• ', text, flags=re.MULTILINE)
    return text.strip()

class SignalScanner:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': Config.USER_AGENT})
        self.stock_list = []

    def load_participation_stocks(self):
        """Katılım endeksi listesini yükler."""
        try:
            response = self.session.get(Config.STOCK_LIST_URL, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            # io.StringIO kullanımı Pandas sürüm hatalarını engeller
            df = pd.read_csv(StringIO(response.text))
            self.stock_list = df['stock'].dropna().astype(str).str.strip().str.upper().tolist()
            logger.info(f"Katılım listesi yüklendi: {len(self.stock_list)} hisse.")
        except Exception as e:
            logger.error(f"Liste yüklenemedi: {e}")
            self.stock_list = []

    def scrape(self, url, is_cmi_mode=False):
        """Veri kazıma, filtreleme ve mükerrer kayıt temizliği yapar."""
        if not self.stock_list:
            self.load_participation_stocks()

        try:
            response = self.session.get(url, timeout=Config.REQUEST_TIMEOUT)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            table = soup.find('table')
            if not table:
                return []

            rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]

            raw_signals = []
            today = datetime.now()
            cutoff_date = self._get_cutoff_date(today)
            stock_set = set(self.stock_list)

            for row in rows:
                cols = [c.get_text(strip=True) for c in row.find_all('td')]
                if len(cols) < 5: continue

                symbol = cols[0].replace("BIST:", "").upper().strip()

                if is_cmi_mode:
                    data = {"stock": symbol, "support": "-", "signal": cols[1], "cmi": cols[2], "cmf": cols[3], "date": cols[4]}
                else:
                    data = {"stock": symbol, "support": cols[1], "signal": cols[2], "cmi": cols[3], "cmf": "-", "date": cols[4]}

                try:
                    dt_obj = datetime.strptime(data['date'], Config.DATE_FORMAT)
                    if dt_obj >= cutoff_date and symbol in stock_set:
                        data['display_date'] = dt_obj.strftime("%d.%m %H:%M")
                        data['dt_obj'] = dt_obj
                        raw_signals.append(data)
                except ValueError:
                    continue

            # Mükerrer Kayıt Temizliği (Her hissenin sadece en güncel sinyalini al)
            unique_signals = {}
            for s in raw_signals:
                if s['stock'] not in unique_signals or s['dt_obj'] > unique_signals[s['stock']]['dt_obj']:
                    unique_signals[s['stock']] = s

            # Tarihe göre yeniden eskiye sırala
            sorted_signals = sorted(unique_signals.values(), key=lambda x: x['dt_obj'], reverse=True)

            logger.info(f"Tarama tamamlandı (CMI modu: {is_cmi_mode}). Bulunan sinyal sayısı: {len(sorted_signals)}")
            return sorted_signals
        except Exception as e:
            logger.error(f"Kazıma hatası ({url}): {e}")
            return []

    def _get_cutoff_date(self, ref_date):
        count, days_back = 0, 0
        while count < Config.BUSINESS_DAYS_LOOKBACK:
            curr = ref_date - timedelta(days=days_back)
            if curr.weekday() < 5: count += 1
            days_back += 1
        return (ref_date - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)

def analyze_signals(signals, is_cmi_report=True):
    """Gemini API üzerinden doğrudan sonuç odaklı ve net bir analiz üretir.

    Eğer `is_cmi_report` True ise hem CMI hem CMF bilgisi kullanılır,
    değilse yalnızca CMI alanı bağlam oluşturmak için kullanılır.
    """
    if not signals or not genai: return None

    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key: return None

    # Sadece en güncel (son 48 saat) verilere odaklan
    recent = [s for s in signals if s['dt_obj'] >= datetime.now() - timedelta(days=2)]
    if not recent: return None

    if is_cmi_report:
        context = "\n".join([f"{s['stock']}: Sinyal {s['signal']}, CMI {s['cmi']}, CMF {s['cmf']}" for s in recent[:15]])
    else:
        context = "\n".join([f"{s['stock']}: Sinyal {s['signal']}, CMI {s['cmi']}" for s in recent[:15]])

    prompt = (
        f"{Config.SYSTEM_PROMPT}\n\nVeriler:\n{context}\n\n"
        "TALİMAT: Aşağıdaki verileri kullanarak doğrudan sonuca yönelik, net ve aksiyon odaklı bir özet yaz. "
        "Giriş cümleleri kurma. En güçlü nakit girişi olanları vurgula ve durumu net özetle. "
        "En fazla 3 cümle. Markdown (yıldız, kare vb.) kullanma. Türkçe."
    )

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model=Config.MODEL_ID, contents=prompt)
        return clean_markdown(response.text)
    except Exception as e:
        logger.error(f"Gemini hatası: {e}")
        return None

def send_professional_email(signals, title, is_cmi):
    """Yüksek uyumluluklu HTML e-posta gönderir."""
    user = os.environ.get('EMAIL_USER')
    password = os.environ.get('EMAIL_PASSWORD')
    to_emails = os.environ.get('TO_EMAIL')

    missing = []
    if not user: missing.append('EMAIL_USER')
    if not password: missing.append('EMAIL_PASSWORD')
    if not to_emails: missing.append('TO_EMAIL')
    if not signals: missing.append('signals')
    if missing:
        logger.warning(f"E-posta gönderimi atlandı ({title}). Eksik/boş: {', '.join(missing)}")
        return

    analysis = analyze_signals(signals, is_cmi)
    report_date = datetime.now().strftime("%d.%m.%Y")

    col_extra_name = "Cmf" if is_cmi else "Destek"
    col_extra_key = "cmf" if is_cmi else "support"

    rows_html = ""
    for i, s in enumerate(signals):
        bg = "#ffffff" if i % 2 == 0 else "#f8f9fa"
        rows_html += f"""
        <tr style="background-color: {bg}; border-bottom: 1px solid #edf2f7;">
            <td style="padding: 12px 8px; font-weight: bold; color: #1a202c;">{s['stock']}</td>
            <td style="padding: 12px 8px; text-align: center; color: #38a169; font-weight: 700;">{s['signal']}</td>
            <td style="padding: 12px 8px; text-align: center; color: #4a5568;">{s['cmi']}</td>
            <td style="padding: 12px 8px; text-align: center; color: #2d3748;">{s[col_extra_key]}</td>
            <td style="padding: 12px 8px; text-align: right; color: #718096; font-size: 11px;">{s['display_date']}</td>
        </tr>"""

    html = f"""
    <html>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Helvetica, Arial, sans-serif; background-color: #f7fafc;">
        <div style="max-width: 600px; margin: 20px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
            <div style="background-color: #f1f5f9; padding: 30px 20px; text-align: center; border-bottom: 3px solid #2d3748;">
                <h2 style="margin: 0; color: #000000; font-size: 24px; font-weight: 800; line-height: 1.2;">{title}</h2>
                <p style="margin: 8px 0 0; color: #000000; font-size: 14px; font-weight: 600;">{report_date} Günlük Veri Raporu</p>
            </div>
            <div style="padding: 10px;">
                <table width="100%" style="border-collapse: collapse; font-size: 13px;">
                    <thead>
                        <tr style="background-color: #edf2f7; color: #2d3748; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">
                            <th style="padding: 12px 8px; text-align: left;">Hisse</th>
                            <th style="padding: 12px 8px;">Sinyal</th>
                            <th style="padding: 12px 8px;">Cmi</th>
                            <th style="padding: 12px 8px;">{col_extra_name}</th>
                            <th style="padding: 12px 8px; text-align: right;">Tarih</th>
                        </tr>
                    </thead>
                    <tbody>{rows_html}</tbody>
                </table>
                {f'<div style="margin-top: 25px; padding: 15px; background: #f0fff4; border-left: 5px solid #38a169; border-radius: 4px; color: #22543d;"><h4 style="margin: 0 0 8px; font-size: 14px; font-weight: 800; color: #1c4532;">🤖 Gemini Analiz</h4><p style="margin: 0; font-size: 13px; line-height: 1.6;">{analysis}</p></div>' if analysis else ''}
            </div>
            <div style="background: #fffaf0; padding: 12px; text-align: center; font-size: 11px; color: #9c4221; border-top: 1px solid #feebc8;">Yasal Uyarı: Yatırım tavsiyesi değildir. Katılım filtresi uygulanmıştır.</div>
            <div style="background: #f1f5f9; padding: 20px; text-align: center; font-size: 11px; color: #a0aec0;">© {datetime.now().year} Magnus Trade Professional | Otomatik Rapor</div>
        </div>
    </body>
    </html>"""

    msg = MIMEMultipart()
    msg['Subject'] = f"{title} - {report_date}"
    msg['From'] = f"Magnus Trade <{user}>"
    msg['To'] = to_emails
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(user, password)
            server.sendmail(user, to_emails.split(','), msg.as_string())
        logger.info(f"E-posta başarıyla gönderildi: {title}")
    except Exception as e:
        logger.error(f"E-posta gönderim hatası: {e}")

if __name__ == "__main__":
    scanner = SignalScanner()

    agresif_url = os.environ.get('SCRAPE_URL')
    if agresif_url:
        logger.info("Agresif tarama başlatılıyor...")
        data = scanner.scrape(agresif_url, is_cmi_mode=False)
        send_professional_email(data, "Agresif Hisse Sinyalleri", is_cmi=False)

    cmi_url = os.environ.get('SCRAPE_CMI_URL')
    if cmi_url:
        logger.info("CMI/CMF tarama başlatılıyor...")
        data = scanner.scrape(cmi_url, is_cmi_mode=True)
        send_professional_email(data, "CMI/CMF Nakit Akışı Raporu", is_cmi=True)
