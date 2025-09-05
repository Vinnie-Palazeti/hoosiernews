# import sqlite3

# with sqlite3.connect('data.db') as con:
#     con.row_factory = sqlite3.Row
#     cursor = con.cursor()
#     # q = """select date, title, created_at from posts where site = 'Jesse Brown' order by created_at desc"""
#     q = """select site, count(*) as cnt from posts group by site"""
#     data = [dict(row) for row in cursor.execute(q).fetchall()]
#     breakpoint()
    
    # q = """
    # DELETE FROM posts
    # WHERE site = 'Indianapolis Local News';
    # """
    
    # q = "delete from posts where url LIKE '%courier%'"
    # cursor.execute(q)
    # con.commit()
    

# ### there should be the most recent data in here...
# ## I just pulled it..

# ## but getdata is not pulling it..
# q = """
# select date, title, created_at from posts where site = 'Jesse Brown' order by created_at desc
# """
# data = cursor.execute(q).fetchall()
# re = [dict(row) for row in data]
 

# breakpoint()


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
def fetch_NWI_business() -> List[Dict[str, Any]]:
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


if __name__ == "__main__":
    fetch_NWI_business()