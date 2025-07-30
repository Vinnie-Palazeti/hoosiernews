import logging
import sqlite3
import html
import bleach
import time
from datetime import datetime
from typing import List, Dict, Any
import feedparser
import requests
from bs4 import BeautifulSoup
import os
import io
from logging.handlers import SMTPHandler
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from gmail_utils import authenticate_gmail, get_messages_by_label, get_message_content
from retry import retry
load_dotenv()

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

log_stream = io.StringIO()
buffer_handler = logging.StreamHandler(log_stream)
buffer_handler.setLevel(logging.INFO)
buffer_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(buffer_handler)

def send_summary_email(body: str):
    msg = EmailMessage()
    msg["Subject"] = "Hoosier News Logs"
    msg["From"] = "vinnie.palazeti@indystats.com"
    msg["To"] = "vinnie.palazeti@indystats.com"
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login("vinnie.palazeti@indystats.com", os.getenv("GMAIL_APP_PASSWORD"))
        smtp.send_message(msg)

# Mapping names
NAME_MAP = {
    "www.tribstar.com - RSS Results":"Tribstar",
    "Current Publishing":'YouAreCurrent',
    "Jesse <jesse@jesseforindy.com>":"Jesse Brown",
    "Indiana Public Media - WFIU/WTIU":"Indiana Public Media",
    "Indianapolis Local News":'WRTV'
}

RSS_FEEDS = [
    'https://www.hoosieragtoday.com/feed/',
    'https://indianacapitalchronicle.com/feed/',
    'https://mirrorindy.org/feed/',
    'https://indypolitics.org/feed/',
    'https://indianapolisrecorder.com/feed/',
    'https://youarecurrent.com/feed/',
    "https://www.ipm.org/index.rss",
    "https://www.wrtv.com/news/local-news.rss"
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/115.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.google.com/",
    "DNT": "1",  # Do Not Track
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "cross-site",
    "Sec-Fetch-User": "?1",
}


@retry(tries=3, delay=2)
def fetch_rss_feed(url: str) -> feedparser.FeedParserDict:    
    logger.info("Fetching RSS feed: %s", url)
    response = requests.get(url, headers=HEADERS, timeout=10)
    response.raise_for_status()  
    return feedparser.parse(response.content)

def parse_feed_entries(feed: feedparser.FeedParserDict) -> List[Dict[str, Any]]:
    entries = []
    if not feed or not feed.entries:
        return entries
    site = NAME_MAP.get(getattr(feed.feed, 'title', ''), getattr(feed.feed, 'title', 'Unknown'))
    for entry in feed.entries:
        published = getattr(entry, 'published', '') or getattr(entry, 'updated', '')
        try:
            date_parsed = datetime(*entry.published_parsed[:6]).isoformat()
        except Exception:
            date_parsed = published
        entries.append({
            'date': date_parsed,
            'site': site,
            'title': entry.get('title', '').strip(),
            'summary': html.unescape(bleach.clean(entry.get('summary', ''), tags=[], strip=True)),
            'url': entry.get('link'),
            'content': None,
            'email': False,
            'created_at': datetime.utcnow().isoformat()
        })
    logger.info(f"found {len(entries)} entries for RSS: {site}")
    return entries 

@retry(tries=3, delay=2)
def fetch_nwitimes() -> List[Dict[str, Any]]:
    url = "https://www.nwitimes.com/news/"
    logger.info("Fetching NWItimes page: %s", url)
    resp = requests.get(url, timeout=10, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("a", href=True) if ('news/local' in a['href'] or 'news/state-regional' in a['href']) and 'article' in a['href']]
    results = []
    found = []
    for a in stories:
        href = a['href'].replace('/news/','')
        text = a.get_text(strip=True)
        if text == '':
            continue
        if href in found:
            continue
        else:
            found.append(href)        
        results.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'site': 'NWI Times',
            'title': text,
            'summary': text,
            'url': requests.compat.urljoin(url, href),
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for NWI times")
    return results

@retry(tries=3, delay=2)
def fetch_courier():
    url="https://www.courierpress.com/news/local-news/"
    logger.info("Fetching Courier & Press page: %s", url)
    resp = requests.get(url, timeout=10, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")  
    stories = [a for a in soup.find_all("a", class_="gnt_m_flm_a", href=True) if 'story/news/local/' in a['href']]
    results = []
    for a in stories:
        # print(a)
        href = a['href']
        title = a.get_text(strip=True)
        summary  = a["data-c-br"]
        date = href.partition('local/')[-1][:10].replace('/','-')
        # timestamp = a.find("div", class_="gnt_m_flm_sbt")["data-c-dt"]
        results.append({
            'date': date,
            'site': 'Courier & Press',
            'title': title,
            'summary': summary,
            'url': requests.compat.urljoin(url, href),
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for Courier")
    return results

@retry(tries=3, delay=2)
def fetch_tribstar() -> List[Dict[str, Any]]:
    url = "https://www.tribstar.com/news/local_news/"
    logger.info("Fetching Tribstar page: %s", url)
    resp = requests.get(url, timeout=10, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    articles = soup.find_all("article")
    articles = [art for art in articles if any("news/local_news" in a["href"] for a in art.find_all("a", href=True))]
    
    found=[]
    results = []    
    for a in articles:
        href = a.find("a", href=lambda h: "news/local_news" in h)["href"]
        time = a.find('time')
        headline=a.find('h3', class_='tnt-headline').get_text(strip=True)
        summary = a.find('p', class_="tnt-summary")
        if summary:
            summary=summary.get_text(strip=True)
        else:
            summary = ''
        
        if href in found:
            continue
        else:
            found.append(href)
        try:
            time = time.get_text(strip=True)
            time = datetime.strptime(time, "%b %d, %Y")
            time = time.strftime("%Y-%m-%d")
        except Exception:
            pass
        
        results.append({
            'date': time,
            'site': 'Tribstar',
            'title': headline,
            'summary': summary,
            'url': requests.compat.urljoin(url, href),
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for TribStar")
    return results 

@retry(tries=3, delay=2)
def fetch_indystar() -> List[Dict[str, Any]]:
    url = "https://www.indystar.com/news/"
    logger.info("Fetching IndyStar page: %s", url)
    resp = requests.get(url, timeout=10, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("a", href=True) if 'story' in a['href']]
    results = []
    for a in stories:
        href = a['href']
        try:
            parts = href.split('2025/')[-1].split('/')
            y, m, d = '2025', parts[0], parts[1]
            date = f"{y}-{m}-{d}"
        except Exception:
            date = datetime.now().isoformat()
        results.append({
            'date': date,
            'site': 'IndyStar',
            'title': a.get_text(strip=True),
            'summary': a.get_text(strip=True),
            'url': requests.compat.urljoin(url, href),
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for IndyStar")
    return results

@retry(tries=3, delay=2)
def fetch_ibj() -> List[Dict[str, Any]]:
    url = "https://www.ibj.com/latest-publication"
    logger.info("Fetching IBJ page: %s", url)
    resp = requests.get(url, timeout=10, headers=HEADERS)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for article in soup.find_all("article"):
        a = article.find('a', href=True)
        t = article.find('time')
        p = article.find('p')
        if not a or not t or 'www.ibj.com/articles' not in a['href']:
            continue
        results.append({
            'date': t['datetime'],
            'site': 'IBJ',
            'title': a.get_text(strip=True),
            'summary': p.get_text(strip=True) if p else '',
            'url': a['href'],
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for IBJ")
    return results

@retry(tries=3, delay=2)
def fetch_emails(max_emails: int = 5) -> List[Dict[str, Any]]:
    service = authenticate_gmail()
    messages = get_messages_by_label(service, os.getenv('GMAIL_LABEL'))
    entries = []
    for msg in messages[:max_emails]:
        msg_data = get_message_content(service, msg['id'])
        sender = msg_data.get('sender')
        entries.append({
            'date': msg_data.get('date'),
            'site': NAME_MAP.get(sender, sender),
            'title': msg_data.get('subject'),
            'summary': msg_data.get('subject'),
            'url': None,
            'content': msg_data.get('html_content'),
            'email': True,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(entries)} entries for Jesse Email")
    return entries

def upsert_posts(db_path: str, data: List[Dict[str, Any]]) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            site TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT,
            url TEXT UNIQUE,
            content TEXT,
            email BOOLEAN,
            created_at TEXT
        )
    """)
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_unique
        ON posts(site, title, date)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_posts_site_created_at
          ON posts(site, created_at DESC)
    """)
        
    cursor.executemany("""
        INSERT OR IGNORE INTO posts
        (date, site, title, summary, url, content, email, created_at)
        VALUES (:date, :site, :title, :summary, :url, :content, :email, :created_at)
    """, data)
    inserted = conn.total_changes
    conn.commit()
    conn.close()
    return inserted




def main():    
    all_entries: List[Dict[str, Any]] = []
    for url in RSS_FEEDS:
        try:
            feed = fetch_rss_feed(url)
            all_entries.extend(parse_feed_entries(feed) or [])   
        except:
            print(url, 'failed!')
            continue
    all_entries.extend(fetch_indystar())
    all_entries.extend(fetch_ibj())
    all_entries.extend(fetch_emails())
    all_entries.extend(fetch_nwitimes())
    all_entries.extend(fetch_courier())
    all_entries.extend(fetch_tribstar())
    inserted = upsert_posts('data.db', all_entries)
    logger.info("Inserted %d new records", inserted)
    log_contents = log_stream.getvalue()
    if log_contents:
        send_summary_email(log_contents)

if __name__ == "__main__":
    main()
