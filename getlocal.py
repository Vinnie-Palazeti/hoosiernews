import gzip, orjson
import sqlite3, os, io, logging
from typing import List, Dict, Any
from pathlib import Path
from email.message import EmailMessage
import smtplib
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)
log_stream = io.StringIO()
buffer_handler = logging.StreamHandler(log_stream)
buffer_handler.setLevel(logging.INFO)
buffer_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
logging.getLogger().addHandler(buffer_handler)

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

def send_summary_email(body: str):
    msg = EmailMessage()
    msg["Subject"] = "Hoosier News Logs"
    msg["From"] = "vinnie.palazeti@indystats.com"
    msg["To"] = "vinnie.palazeti@indystats.com"
    msg.set_content(body)
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login("vinnie.palazeti@indystats.com", os.getenv('EMAIL_PASSWORD'))
        smtp.send_message(msg)

def main():
    with open("/var/log/getlocal-start.log", "a") as f:
        f.write(datetime.now().isoformat() + "\n")        
        
    logger.info("STARTING SCRIPT: getlocal.py")
    data_dir = Path('~/news/data').expanduser()
    files = list(data_dir.glob('entries-*.jsonl.gz'))
    # files = [Path('/var/folders/ff/zfwbsr290232x88rkrnvhfxw0000gp/T/entries-2025-09-01T16:21:13.292276.jsonl.gz')]    
    logger.info("files found: %d", len(files))
    rows = []
    for file in files:
        with gzip.open(file, "rb") as f:
            rows.extend([orjson.loads(line) for line in f])
    logger.info("found records %d", len(rows))
    if rows: 
        try:
            inserted = upsert_posts('data.db', rows)
            logger.info("Inserted %d new records", inserted)
            
            # Only delete if upsert was successful
            for file in files:
                try:
                    file.unlink()
                    logger.info("Deleted %s", file.name)
                except OSError as e:
                    logger.error("Failed to delete %s: %s", file.name, e)

        except Exception as e:
            logger.error("Failed to upsert data, keeping files: %s", e)
    else:
        logger.info("no rows found!")

    log_contents = log_stream.getvalue()
    
    with open("/var/log/getlocal.log", "a") as f:
        f.write(log_contents)    
    
    if log_contents:
        send_summary_email(log_contents)
                
if __name__ == "__main__":
    main()