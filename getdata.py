import logging
import html
import bleach
from datetime import datetime
from typing import List, Dict, Any
import feedparser
import requests
from bs4 import BeautifulSoup
import os
import io
import smtplib
from email.message import EmailMessage
from retry import retry
import os, pathlib, subprocess, modal
import orjson, gzip, datetime as dt, tempfile, pathlib
import base64
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import re
from urllib.parse import urljoin

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
log_stream = io.StringIO()
buffer_handler = logging.StreamHandler(log_stream)
buffer_handler.setLevel(logging.INFO)
buffer_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(buffer_handler)

#################### GMAIL UTILS ####################

def save_secret_to_json(secret:str):
    json_str = os.getenv(secret)
    if json_str:
        with open(f'{secret}.json', 'w') as f:
            f.write(json_str)

def authenticate_gmail():
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    save_secret_to_json('GMAIL_TOKEN')
    save_secret_to_json('HN_CREDS')
    
    if os.path.exists("GMAIL_TOKEN.json"):
        creds = Credentials.from_authorized_user_file("GMAIL_TOKEN.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("HN_CREDS.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("HN_CREDS.json", "w") as token:
            token.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)

def get_messages_by_label(service, labelid):
    response = service.users().messages().list(userId='me', labelIds=[labelid]).execute()
    messages = []
    if 'messages' in response:
        messages.extend(response['messages'])
    return messages

def get_message_details(service, msg_id, format='full'):
    try:
        message = service.users().messages().get(userId='me', id=msg_id, format=format).execute()
        return message
    except Exception as error:
        print(f'An error occurred: {error}')
        return None

def get_content_id(part):
    """Get Content-ID from headers for inline image reference."""
    headers = part.get('headers', [])
    for header in headers:
        if header['name'].lower() == 'content-id':
            # Strip < and > if present
            cid = header['value']
            if cid.startswith('<') and cid.endswith('>'):
                cid = cid[1:-1]
            return cid
    return None


def is_image(filename):
    """Check if a filename is likely an image based on extension."""
    if not filename:
        return False
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    return any(filename.lower().endswith(ext) for ext in image_extensions)

def process_parts(service, user_id, msg_id, parts):
    """Process message parts to extract text, HTML, and images."""
    plain_text = ""
    html_content = ""
    images = []

    print('PROCESS PARTS!!')
    
    for part in parts:
        mime_type = part.get('mimeType', '')

        # Handle nested parts recursively
        if 'parts' in part:
            nested_text, nested_html, nested_images = process_parts(service, user_id, msg_id, part['parts'])
            plain_text += nested_text
            html_content += nested_html
            images.extend(nested_images)
            continue
        
        # Get part body
        body = part.get('body', {})
        
        # Extract content based on MIME type
        if 'data' in body:
            data = base64.urlsafe_b64decode(body['data']).decode('utf-8', errors='replace')
            if 'text/plain' in mime_type:
                plain_text += data
            elif 'text/html' in mime_type:
                html_content += data
        
        # Handle attachments (images)
        if 'attachmentId' in body:
            filename = part.get('filename', '')
            if is_image(filename) or 'image/' in mime_type:
                # Get attachment data
                attachment = service.users().messages().attachments().get(
                    userId=user_id, messageId=msg_id, id=body['attachmentId']).execute()
                
                # Decode attachment data
                file_data = base64.urlsafe_b64decode(attachment['data'])
                
                # Add to images list
                images.append({
                    'filename': filename,
                    'content_id': get_content_id(part),
                    'data': file_data,
                    'mime_type': mime_type
                })
    
    return plain_text, html_content, images

def get_message_content(service, msg_id, user_id='me'):
    """Get the content of a message including text, HTML, and images."""
    try:
        # Get the full message
        message = service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
        
        payload = message['payload'] ## ['partId', 'mimeType', 'filename', 'headers', 'body']
        headers = payload.get('headers', [])
        
        # Get subject and sender
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        
        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), 'No Date')
        # received = next((h['value'] for h in headers if h['name'].lower() == 'received'), 'No Date')
        
        ### can get received from here
        
        # Initialize variables to hold content
        plain_text = ""
        html_content = ""
        images = []
        
        # Extract partsn
        if 'parts' in payload:
            print('parts')
            plain_text, html_content, images = process_parts(service, user_id, msg_id, payload['parts'])
        else:
            print('single')
            body_data = payload.get('body', {}).get('data', '')
            if body_data:
                content = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                mime_type = payload.get('mimeType', '')
                if 'text/plain' in mime_type:
                    plain_text = content
                elif 'text/html' in mime_type:
                    html_content = content
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'plain_text': plain_text,
            'html_content': html_content,
            'images': images,
            'date':date
        }
        
    except Exception as error:
        print(f'Error getting message content: {error}')
        return None

################################################################################

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


@retry(tries=3, delay=2)
def fetch_rss_feed(url: str) -> feedparser.FeedParserDict:    
    logger.info("Fetching RSS feed: %s", url)
    response = requests.get(url, timeout=10)
    response.raise_for_status() 
    return feedparser.parse(response.content)

def parse_feed_entries(feed: feedparser.FeedParserDict, length:int=None) -> List[Dict[str, Any]]:
    entries = []
    if not feed or not feed.entries:
        return entries
    site = NAME_MAP.get(getattr(feed.feed, 'title', ''), getattr(feed.feed, 'title', 'Unknown'))
    
    if len(feed.entries) > 0:
        if "fox59" in feed.entries[0].get('link'): # lol
            site='Fox 59'
        if 'wrtv' in feed.entries[0].get('link'):
            site='WRTV'
            
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
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(entries)} entries for RSS: {site}")
    return entries 

@retry(tries=3, delay=2)
def fetch_heraldtimes() -> List[Dict[str, Any]]:
    url = "https://www.heraldtimesonline.com/news/local/"
    logger.info("Fetching Herald Times page: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("a", href=True) if 'news/local' in a['href']]
    results = []
    found = []
    for a in stories:
        href = a.get('href')
        text = a.get_text(strip=True)
        summary = a.get("data-c-br", text).strip()
        date = href.partition('local/')[-1][:10].replace('/','-')
        try:
            date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            date = datetime.now().strftime('%Y-%m-%d')
        if text == '':
            continue
        if href in found:
            continue
        else:
            found.append(href)     
               
        results.append({
            'date': date,
            'site': 'Herald Times',
            'title': text,
            'summary': summary,
            'url': requests.compat.urljoin(url, href),
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for Herald Times")
    return results

@retry(tries=3, delay=2)
def fetch_chalkbeat() -> List[Dict[str, Any]]:
    url = "https://www.chalkbeat.org/indiana/"
    logger.info("Fetching Chalkbeat page: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    thisyear = datetime.today().year
    story_groups = soup.find_all(class_="results-list-container")

    results = []
    found = set()

    for grp in story_groups:
        # Loop through each article in this group
        for article in grp.find_all(class_="PagePromo-content"):
            # Extract all <a> tags with valid links for this year
            links = [
                a["href"]
                for a in article.find_all("a", href=True)
                if f"/indiana/{thisyear}" in a["href"]
            ]
            if not links:
                continue  # Skip articles without valid URLs

            href = links[0]  # First link is the main story link
            full_url = requests.compat.urljoin(url, href)

            # Extract the article title
            title_tag = article.find(class_="PagePromo-title")
            title = title_tag.get_text(strip=True) if title_tag else None
            
            if not title:
                continue

            # Extract the article summary/description
            desc_tag = article.find(class_="PagePromo-description")
            summary = desc_tag.get_text(strip=True) if desc_tag else None

            # Extract date from URL if present
            try:
                date_str = href.split("/indiana/")[-1].split("/", 3)[:3]
                date = datetime.strptime("-".join(date_str), "%Y-%m-%d").strftime("%Y-%m-%d")
            except Exception:
                date = datetime.now().strftime("%Y-%m-%d")

            # Deduplication check
            if full_url in found:
                continue
            found.add(full_url)
            

            # Append result
            results.append({
                "date": date,
                "site": "Chalkbeat",
                "title": title,
                "summary": summary or title,
                "url": full_url,
                "content": None,
                "email": False,
                "created_at": datetime.now().isoformat(),
            })
    logger.info(f"Found {len(results)} entries for ChalkBeat")
    return results

@retry(tries=3, delay=2)
def fetch_nwitimes() -> List[Dict[str, Any]]:
    url = "https://www.nwitimes.com/news/"
    logger.info("Fetching NWItimes page: %s", url)
    resp = requests.get(url, timeout=10)
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
def fetch_indianalawyer():
    url='https://www.theindianalawyer.com/latest-publication'
    logger.info("Fetching Indiana Lawyer: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")  
    
    stories = [a for a in soup.find_all("article")]
    # Each story is an <article>; class may vary, so don't overfit the selector.
    stories = soup.find_all("article")
    results = []
    for art in stories:
        try:
            # URL + title
            h2_link = art.find("h2")
            if not h2_link:
                continue  # skip promos without a title
            a_tag = h2_link.find("a", href=True)
            if not a_tag:
                continue
            href = urljoin(url, a_tag["href"])
            title = a_tag.get_text(strip=True)

            # Date (prefer machine-readable datetime attr; fallback to text)
            date_iso = None
            t = art.find("time")
            if t and t.has_attr("datetime"):
                # Example: "2025-08-13T02:03:47-04:00"
                try:
                    date_iso = datetime.fromisoformat(t["datetime"]).date().isoformat()
                except Exception:
                    date_iso = None
            if not date_iso and t:
                # Fallback like "August 13, 2025"
                try:
                    date_iso = datetime.strptime(t.get_text(strip=True), "%B %d, %Y").date().isoformat()
                except Exception:
                    date_iso = None

            # Summary (first paragraph in the card)
            p = art.find("p")
            summary = p.get_text(strip=True) if p else ""

            # Optional: author and image if you want to keep them
            by = art.select_one(".byline a, .author a, .byline .author")
            author = by.get_text(strip=True) if by else None

            img = art.find("img")
            image = img.get("src") if img else None

            results.append({
                "date": date_iso,
                "site": "The Indiana Lawyer",
                "title": title,
                "summary": summary,
                "url": href,
                "content": None,
                "email": False,
                "created_at": datetime.now().isoformat(),
            })
        except Exception as e:
            logger.exception("Error parsing an article card: %s", e)
            continue

    logger.info("found %d entries for Indiana Lawyer", len(results))
    return results

@retry(tries=3, delay=2)
def fetch_courier():
    url="https://www.courierpress.com/news/local-news/"
    logger.info("Fetching Courier & Press page: %s", url)
    resp = requests.get(url, timeout=10)
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
    resp = requests.get(url, timeout=10)
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
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("a", href=True) if 'story' in a['href']]
    results = []
    breakpoint()
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
    resp = requests.get(url, timeout=10)
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

        # not sure why pothole email made it in here..
        if 'othole' in msg_data.get('subject'):
            continue
        content = msg_data.get('html_content')
        if not 'ActionNetwork.org' in content:
            continue
        
        clean_html = re.sub(r'href="https://click\.actionnetwork\.org[^"]*"', '', content)
        
        entries.append({
            'date': msg_data.get('date'),
            'site': NAME_MAP.get(sender, sender),
            'title': msg_data.get('subject'),
            'summary': msg_data.get('subject'),
            'url': None,
            'content': clean_html,
            'email': True,
            'created_at': datetime.now().isoformat()
        })
        
    logger.info(f"found {len(entries)} entries for Jesse Email")
    return entries

@retry(tries=3, delay=2)
def fetch_inside_indiana_business() -> List[Dict[str, Any]]:
    url = "https://www.insideindianabusiness.com/topics/news"
    logger.info("Fetching IIB page: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("article")][:20]
    results = []
    found = []
    for story in stories:
        link_tag = story.find("a", href=True)
        link = link_tag["href"] if link_tag else None
        h2_tag = story.find("h2")
        title = h2_tag.get_text(strip=True) if h2_tag else None
        p_tag = story.find("p")
        summary = p_tag.get_text(strip=True) if p_tag else None        
        if not title:
            continue
        if not link:
            continue
        else:
            found.append(link)     
            
        results.append({
            'date': datetime.now().strftime('%Y-%m-%d'),
            'site': 'Inside Indiana Business',
            'title': title,
            'summary': summary or title,
            'url': link,
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
        
    logger.info(f"found {len(results)} entries for IIB")    
    return results

@retry(tries=3, delay=2)
def fetch_nwi_business() -> List[Dict[str, Any]]:
    url = "https://nwindianabusiness.com/category/community/business-news/"
    logger.info("Fetching NWI Biz: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
    stories = [a for a in soup.find_all("article")][:10]
    
    results = []
    found = []
    for story in stories:
        link_tag = story.find("a", href=True)
        link = link_tag["href"] if link_tag else None
        h2_tag = story.find("h2")
        title = h2_tag.get_text(strip=True) if h2_tag else None
        p_tag = story.find("p")
        summary = p_tag.get_text(strip=True) if p_tag else None   
        
        date_ = story.find("span", class_='published')
        date_ = date_.get_text(strip=True) if date_ else None 
        if date_:
            date_ = datetime.strptime(date_, '%B %d, %Y').strftime('%Y-%m-%d')
        if not title:
            continue
        if not link:
            continue
        else:
            found.append(link)

        results.append({
            'date': date_ or datetime.now().strftime('%Y-%m-%d'),
            'site': 'NWI Business',
            'title': title,
            'summary': summary or title,
            'url': link,
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })
    logger.info(f"found {len(results)} entries for NWI Biz")    
    return results

@retry(tries=3, delay=2)
def fetch_journal_gazette() -> List[Dict[str, Any]]:
    url = "https://www.journalgazette.net/local/"
    logger.info("Fetching Journal Gazette: %s", url)
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    stories = [a for a in soup.find_all("article")][:10]
    
    results = []
    found = []
    
    for story in stories:
        link_tag = story.find("a", href=True)
        link = link_tag["href"] if link_tag else None
        title = story.find("h2")
        if not title:
            title = story.find('h3')
        title = title.get_text(strip=True) if title else None
        p_tag = story.find("p")
        summary = p_tag.get_text(strip=True) if p_tag else None
        date_ = story.find('time').get('datetime')
        
        if date_:
            date_ = date_[:10]
        if not title:
            continue
        if not link:
            continue
        else:
            found.append(link)

        results.append({
            'date': date_ or datetime.now().strftime('%Y-%m-%d'),
            'site': 'Journal Gazette',
            'title': title,
            'summary': summary or title,
            'url': link,
            'content': None,
            'email': False,
            'created_at': datetime.now().isoformat()
        })

    logger.info(f"found {len(results)} entries for Journal Gazette")    
    return results


def setup_ssh_client():
    """Set up SSH client to connect to your server"""
    ssh_dir = pathlib.Path('/root/.ssh')
    known_hosts = ssh_dir / 'known_hosts'
    server = os.getenv('SERVER').rpartition('@')[-1]
    
    # Add your server's host key
    if not known_hosts.exists():
        with open(known_hosts, 'w') as f:
            subprocess.run(['ssh-keyscan', '-H', server], stdout=f, check=True)
        known_hosts.chmod(0o600)
        

def send_file(local_path: str, remote_path: str, local:bool=False):
    server = os.getenv('SERVER')
    if local:
        key_file = os.getenv('SSH_KEY_PATH')
    else:
        key_text = os.getenv('SSH_PRIVATE_KEY')
        if not key_text.endswith('\n'):
            key_text += '\n'
        ssh_dir = pathlib.Path.home() / ".ssh"
        key_file = ssh_dir / "id_rsa"
        ssh_dir.mkdir(mode=0o700, exist_ok=True)
        key_file.write_text(key_text)
        key_file.chmod(0o600)
         
    subprocess.run(
        [
            "scp",
            "-i", str(key_file),
            str(local_path),
            f"{server}:{remote_path}",
        ],
        check=True,
    )

def _json_default(obj):
    if isinstance(obj, (dt.datetime, dt.date)):
        return obj.isoformat() 
    raise TypeError

def save_jsonl(entries, out_path: pathlib.Path):
    with gzip.open(out_path, "wb") as f:
        for row in entries:
            f.write(orjson.dumps(row, default=_json_default))
            f.write(b"\n")

NAME_MAP = {
    "www.tribstar.com - RSS Results":"Tribstar",
    "Current Publishing":'YouAreCurrent',
    "Jesse <jesse@jesseforindy.com>":"Jesse Brown",
    "Indiana Public Media - WFIU/WTIU":"Indiana Public Media",
    "Indianapolis Local News":'WRTV',
    "Featured News - THE INDIANA CITIZEN": "The Indiana Citizen"
}

RSS_FEEDS = [
    'https://www.hoosieragtoday.com/feed/',
    'https://indianacapitalchronicle.com/feed/',
    'https://mirrorindy.org/feed/',
    'https://indypolitics.org/feed/',
    'https://indianapolisrecorder.com/feed/',
    'https://youarecurrent.com/feed/',
    "https://www.ipm.org/index.rss",
    "https://www.wrtv.com/news/local-news.rss",
    "https://fox59.com/indiana-news/feed/",
    "https://indianacitizen.org/category/featured-news/feed/"
]

foos = {
    'indystar':fetch_indystar,
    'ibj':fetch_ibj,
    'emails':fetch_emails,
    'nwitimes':fetch_nwitimes,
    'courier':fetch_courier,
    'tribstar':fetch_tribstar,
    'herald':fetch_heraldtimes,
    'chalkbeat':fetch_chalkbeat,
    'indiana_lawyer': fetch_indianalawyer,
    'inside_indiana_business': fetch_inside_indiana_business,
    'nwi_business': fetch_nwi_business,
    'journal_gazette':fetch_journal_gazette
}

# from dotenv import load_dotenv
# load_dotenv()
# from getlocal import upsert_posts 

image = (
    modal.Image.debian_slim()
    .pip_install(
        "bleach",
        "feedparser", 
        "requests",
        "beautifulsoup4",
        "retry",
        "orjson",
        "google-api-python-client",
        "google-auth",
        "google-auth-oauthlib",
        "google-auth-httplib2"        
    )
    .apt_install("openssh-client")
    .run_commands(["mkdir -p /root/.ssh"])
)

app = modal.App("hoosier-news-getdata", image=image)
@app.function(
    secrets=[modal.Secret.from_name("hoosier-news")],
    schedule=modal.Cron("0 */5 * * *"),
    timeout=3000,
)

def main():
    logger.info(f"starting...")
    all_entries: List[Dict[str, Any]] = []
    
    for url in RSS_FEEDS:
        try:
            feed = fetch_rss_feed(url)
            all_entries.extend(parse_feed_entries(feed) or [])
            
        except Exception as e:
            logger.error(f"{url} failed:\n{e}")
            continue
        
    for site, fetch_fn in foos.items():
        try:
            all_entries.extend(fetch_fn())
        except Exception as e:
            logger.error(f"{site} failed:\n{e}")
    
    # inserted = upsert_posts('data.db', all_entries)
    # breakpoint()
            
    fn = f"entries-{datetime.now().isoformat()}.jsonl.gz"
    tmp_path = pathlib.Path(tempfile.gettempdir()) / fn   
    save_jsonl(all_entries, tmp_path)
    setup_ssh_client()
    send_file(tmp_path, f'/root/news/data/{fn}') 
    log_contents = log_stream.getvalue()
    if log_contents:
        send_summary_email(log_contents)
        
if __name__ == "__main__":
    main()