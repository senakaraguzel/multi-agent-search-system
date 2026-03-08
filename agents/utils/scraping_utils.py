import hashlib
import re
from bs4 import BeautifulSoup
from readability import Document

def generate_html_hash(html_content: str) -> str:
    """Icerigin benzersizligini (De-duplication) saglamak amaciyla SHA256 hashi olusturur."""
    if not html_content:
         return ""
    return hashlib.sha256(html_content.encode('utf-8')).hexdigest()

def remove_boilerplate(html_content: str) -> str:
    """Haber/Makale sayfalarindaki footer, nav ve reklam (boilerplate) etiketlerini temizleyip core text'i doner."""
    try:
        doc = Document(html_content)
        clean_html = doc.summary()
        # HTML taglarini temizle ve yalnizca text birak
        soup = BeautifulSoup(clean_html, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        # Fazla bosluklari kaldir
        text = re.sub(r'\s+', ' ', text)
        return text
    except Exception as e:
        print(f"[ScrapingUtils] Boilerplate kaldirma hatasi: {e}")
        # Hata durumunda BS4 ile kaba bir temizlik yap
        soup = BeautifulSoup(html_content, 'html.parser')
        for script in soup(["script", "style", "nav", "footer", "header"]):
             script.extract()
        return soup.get_text(separator=' ', strip=True)

def parse_tables(html_content: str) -> list:
    """Specific(istatistiksel) veriler için tabloları satırlara ayırır.
    Wikipedia wikitable class'larına öncelik verir; varsa tablo başlığını da ekler.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Önce Wikipedia/data tablolarına bak (wikitable, sortable, vs)
    priority_tables = soup.find_all('table', class_=lambda c: c and any(
        kw in c for kw in ['wikitable', 'sortable', 'infobox', 'football-table', 'toccolours']
    ))
    # Yoksa tüm tabloları al
    all_tables = priority_tables if priority_tables else soup.find_all('table')

    parsed_tables = []
    for table in all_tables:
        rows = []

        # Tablo başlığını (caption) varsa ilk satır olarak ekle
        caption = table.find('caption')
        if caption:
            caption_text = caption.get_text(strip=True)
            if caption_text:
                rows.append([caption_text])

        for tr in table.find_all('tr'):
            cells = []
            for td in tr.find_all(['td', 'th']):
                cells.append(td.get_text(strip=True))
            if any(cells):  # Boş satırları atla
                rows.append(cells)

        if len(rows) > 1:  # Sadece header'dan ibaret tabloları atla
            parsed_tables.append(rows)

    return parsed_tables
