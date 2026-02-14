# author: @dipavcisi0007
# source: https://x.com/dipAVCISI007/status/1894070221469577311
# edited by: therkut & Gemini
# BIST Pay Endeksleri - Katılım Filtreli Agresif ve CMI Sinyal Taraması

import os
import smtplib
import requests
import pandas as pd
from bs4 import BeautifulSoup
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart

def load_stock_list(url="https://raw.githubusercontent.com/therkut/bistLists/refs/heads/main/data/stock_xktum_data.csv"):
    """GitHub üzerinden katılım endeksi hisse listesini çeker."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"Uyarı: Katılım listesi çekilemedi (HTTP {response.status_code}). Tüm hisseler getirilecek.")
            return []

        from io import StringIO
        df = pd.read_csv(StringIO(response.text))
        
        if 'stock' not in df.columns:
            print("Uyarı: CSV içinde 'stock' sütunu bulunamadı.")
            return []
            
        stock_list = df['stock'].dropna().astype(str).str.strip().tolist()
        return stock_list
    except Exception as e:
        print(f"Uyarı: Hisse listesi yüklenirken hata oluştu: {e}")
        return []

def scrape_data(url, is_cmi_mode=False):
    """Web sitesinden sağlanan HTML tablo yapısına göre verileri çeker."""
    if not url:
        return []

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"Hata: {url} adresine bağlanılamadı: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    table = soup.find('table')
    if not table:
        print(f"Hata: {url} sayfasında tablo bulunamadı.")
        return []

    rows = table.find('tbody').find_all('tr') if table.find('tbody') else table.find_all('tr')[1:]

    stock_signals = []
    today = datetime.now()
    
    # 3 İş günü filtresi
    business_days_count = 0
    days_back = 0
    while business_days_count < 3:
        current_date = today - timedelta(days=days_back)
        if current_date.weekday() < 5:
            business_days_count += 1
        days_back += 1
    
    three_business_days_ago = today - timedelta(days=days_back)
    three_business_days_ago = three_business_days_ago.replace(hour=0, minute=0, second=0, microsecond=0)

    STOCK_LIST = load_stock_list()

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 5: continue 
        
        # Hisse adını al ve "BIST:" ekini temizle
        stock_raw = cols[0].get_text(strip=True)
        stock = stock_raw.replace("BIST:", "").strip()

        # Moduna göre sütun eşleşmesi
        if is_cmi_mode:
            # CMI yapısı: 0:Hisse, 1:Signal Fiyatı, 2:Cmi, 3:Cmf, 4:Tarih
            support_price = "-" # CMI tablosunda destek yok
            signal_price = cols[1].get_text(strip=True)
            cmi_val = cols[2].get_text(strip=True)
            cmf_val = cols[3].get_text(strip=True)
            date_str = cols[4].get_text(strip=True)
        else:
            # Agresif yapısı: 0:Hisse, 1:Destek, 2:Signal, 3:Cmi, 4:Tarih
            support_price = cols[1].get_text(strip=True)
            signal_price = cols[2].get_text(strip=True)
            cmi_val = cols[3].get_text(strip=True)
            cmf_val = "-" # Agresif tablosunda cmf yok
            date_str = cols[4].get_text(strip=True)

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            if date_obj >= three_business_days_ago:
                if not STOCK_LIST or stock in STOCK_LIST:
                    stock_signals.append({
                        "stock": stock,
                        "support_price": support_price,
                        "signal_price": signal_price,
                        "cmi": cmi_val,
                        "cmf": cmf_val,
                        "date": date_str
                    })
        except ValueError:
            continue

    return stock_signals

def send_email(stock_signals, from_name, from_address, to_addresses, password, subject, report_title, is_cmi_mode=False, smtp_server="smtp.gmail.com", smtp_port=465):
    """Verilen sinyalleri e-posta olarak gönderir."""
    if not stock_signals:
        print(f"{report_title} için kriterlere uygun sinyal bulunmadığından e-posta gönderilmedi.")
        return

    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    current_year = now.strftime("%Y")

    # Tablo başlıklarını moda göre belirleyelim
    header_html = """
        <th style="padding:12px; text-align:left; color: #495057;">Hisse</th>
        <th style="padding:12px; text-align:center; color: #495057;">Sinyal</th>
        <th style="padding:12px; text-align:center; color: #495057;">Cmi</th>
    """
    if is_cmi_mode:
        header_html += '<th style="padding:12px; text-align:center; color: #495057;">Cmf</th>'
    else:
        header_html += '<th style="padding:12px; text-align:center; color: #495057;">Destek</th>'
    
    header_html += '<th style="padding:12px; text-align:right; color: #495057;">Tarih</th>'

    html_body = f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; padding: 20px;">
    <div style="max-width:650px; margin:0 auto; background-color: #ffffff; border-radius:12px; overflow:hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
        <div style="background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%); color:white; padding:30px; text-align:center;">
            <h2 style="margin:0; font-size: 24px;">📊 {report_title}</h2>
            <p style="margin:10px 0 0 0; opacity: 0.8;">{date_str} Günlük Tarama Raporu</p>
        </div>
        <div style="padding:20px;">
            <table width="100%" style="border-collapse:collapse; margin-top: 10px;">
                <thead>
                    <tr style="background-color:#f8f9fa; border-bottom: 2px solid #dee2e6;">
                        {header_html}
                    </tr>
                </thead>
                <tbody>
    """

    for i, signal in enumerate(stock_signals):
        bg_color = "#ffffff" if i % 2 == 0 else "#fcfcfc"
        
        # Satır içeriği
        row_content = f"""
            <td style="padding:12px; font-weight: bold; color: #2c3e50;">{signal['stock']}</td>
            <td style="padding:12px; text-align:center; color: #27ae60; font-weight: 500;">{signal['signal_price']}</td>
            <td style="padding:12px; text-align:center; color: #7f8c8d;">{signal['cmi']}</td>
        """
        
        if is_cmi_mode:
            row_content += f'<td style="padding:12px; text-align:center; color: #2980b9;">{signal["cmf"]}</td>'
        else:
            row_content += f'<td style="padding:12px; text-align:center;">{signal["support_price"]}</td>'
            
        row_content += f'<td style="padding:12px; text-align:right; font-size:11px; color: #95a5a6;">{signal["date"]}</td>'

        html_body += f'<tr style="background-color: {bg_color}; border-bottom: 1px solid #eee;">{row_content}</tr>'

    html_body += f"""
                </tbody>
            </table>
        </div>
        <div style="background-color:#fff3cd; padding:15px; text-align:center; font-size:12px; color:#856404; border-left: 5px solid #ffeeba;">
            <strong>⚠️ YASAL UYARI:</strong> Bu veriler otomatik taranmıştır, yatırım tavsiyesi değildir.
        </div>
        <div style="background-color:#f8f9fa; padding:20px; text-align:center; font-size:11px; color:#6c757d; border-top: 1px solid #eee;">
            Bu rapor <strong>therkut</strong> tarafından otomatik oluşturulmuştur.<br>
            © {current_year} | Katılım Endeksi Filtresi Uygulanmıştır.
        </div>
    </div>
    </body>
    </html>
    """

    msg = MIMEMultipart()
    msg['From'] = f"{from_name} <{from_address}>"
    msg['To'] = ", ".join(to_addresses)
    msg['Subject'] = f"{subject} ({date_str})"
    msg.attach(MIMEText(html_body, 'html'))

    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(from_address, password)
            server.sendmail(from_address, to_addresses, msg.as_string())
        print(f"{report_title} e-postası başarıyla gönderildi!")
    except Exception as e:
        print(f"{report_title} e-posta gönderim hatası: {e}")

if __name__ == "__main__":
    email_user = os.environ.get('EMAIL_USER')
    email_pass = os.environ.get('EMAIL_PASSWORD')
    to_email = os.environ.get('TO_EMAIL')
    url_agresif = os.environ.get('SCRAPE_URL')
    url_cmi = os.environ.get('SCRAPE_CMI_URL')

    if not all([email_user, email_pass, to_email]):
        print("Hata: Temel kimlik bilgileri (EMAIL_USER, EMAIL_PASSWORD, TO_EMAIL) eksik.")
    else:
        to_email_list = [e.strip() for e in to_email.split(',')]
        
        # 1. Agresif Hisse Taraması
        if url_agresif:
            print("Agresif sinyaller taranıyor...")
            res_agresif = scrape_data(url_agresif, is_cmi_mode=False)
            send_email(res_agresif, "Magnus Trade", email_user, to_email_list, email_pass, 
                       "📊 Agresif Hisse Sinyal Raporu", "Agresif Hisse Sinyalleri", is_cmi_mode=False)

        # 2. CMI Hisse Taraması
        if url_cmi:
            print("CMI sinyalleri taranıyor...")
            res_cmi = scrape_data(url_cmi, is_cmi_mode=True)
            send_email(res_cmi, "therkut", email_user, to_email_list, email_pass, 
                       "📊 CMI/CMF Hisse Sinyal Raporu", "CMI/CMF Hisse Sinyalleri", is_cmi_mode=True)

