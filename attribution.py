import uuid, sqlite3
from datetime import datetime
from starlette.requests import Request

CLICK_KEYS = {"gclid","gbraid","wbraid","utm_source","utm_medium","utm_campaign","utm_term","utm_content"}
DB_PATH = "data.db"
DEBOUNCE_SECONDS = 60  # skip re-inserting same anon_id+gclid within this window

def _ensure_tables(con: sqlite3.Connection):
    """
    Create/upgrade tables to the expected schema without dropping data.
    - sessions: keep your existing `timestamp` column name; add anon_id/referrer if missing.
    - click_attribution: fresh table with ts, anon_id, landing_url, referrer, and UTM fields.
    - indexes: safe to (re)create.
    """

    # --- helpers ---
    def table_columns(conn, table):
        return [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]

    def ensure_column(conn, table, name, ddl_type):
        cols = table_columns(conn, table)
        if name not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}")

    # --- sessions table (use your original column names) ---
    # If it doesn't exist, create it with timestamp + anon_id + referrer from the start.
    con.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip TEXT,
            user_agent TEXT,
            path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            anon_id TEXT,
            referrer TEXT
        )
    """)

    # If it already existed, make sure required columns are present.
    ensure_column(con, "sessions", "anon_id", "TEXT")
    ensure_column(con, "sessions", "referrer", "TEXT")

    # --- click_attribution table (new) ---
    con.execute("""
        CREATE TABLE IF NOT EXISTS click_attribution (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts DATETIME DEFAULT CURRENT_TIMESTAMP,
            anon_id TEXT,
            landing_url TEXT,
            referrer TEXT,
            gclid TEXT,
            gbraid TEXT,
            wbraid TEXT,
            utm_source TEXT,
            utm_medium TEXT,
            utm_campaign TEXT,
            utm_term TEXT,
            utm_content TEXT
        )
    """)

    # --- indexes ---
    # sessions uses 'timestamp' (your schema), not 'ts'
    con.execute("CREATE INDEX IF NOT EXISTS idx_sessions_anon_ts ON sessions(anon_id, timestamp)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_clicks_anon_ts ON click_attribution(anon_id, ts)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_clicks_gclid ON click_attribution(gclid)")

    con.commit()

def _lim(s, n):
    if s is None:
        return None
    return s if len(s) <= n else s[:n]

def _recent_duplicate(con: sqlite3.Connection, anon_id: str, gclid: str | None) -> bool:
    """
    Return True if there is a recent row for this anon_id+gclid within DEBOUNCE_SECONDS.
    We only debounce when gclid is present (it’s the most reliable dedupe key).
    """
    if not gclid:
        return False
    row = con.execute(
        """
        SELECT (julianday('now') - julianday(ts))*86400.0 AS seconds_ago
        FROM click_attribution
        WHERE anon_id = ? AND gclid = ?
        ORDER BY ts DESC
        LIMIT 1
        """,
        (anon_id, gclid),
    ).fetchone()
    return bool(row and row[0] is not None and row[0] < DEBOUNCE_SECONDS)

def attribution_before(req: Request, sess: dict):
    """
    FastHTML `before=` hook: ensures anon_id, logs session hit,
    captures click params (first-touch in session, all-touches in DB with debounce).
    """
    path = str(req.url.path)
    # Don't log static assets or favicon requests
    if path.startswith("/static") or path == "/favicon.ico":
        return    

    # 0) Ensure stable anon id inside the existing Starlette session cookie
    anon_id = sess.setdefault("anon_id", str(uuid.uuid4()))

    # 1) Request context
    ip   = getattr(req.client, "host", "") or ""
    ua   = req.headers.get("user-agent", "") or ""
    ref  = req.headers.get("referer", "") or ""
    qp   = req.query_params or {}
    landing_url = str(req.url)

    # 2) Capture any click params present on this request
    captured = {k: qp.get(k) for k in CLICK_KEYS if qp.get(k)}

    con = sqlite3.connect(DB_PATH)
    try:
        _ensure_tables(con)

        # 3) Log this request to sessions (every hit)
        con.execute(
            "INSERT INTO sessions (anon_id, ip, user_agent, path) VALUES (?, ?, ?, ?)",
            (
                anon_id,
                _lim(ip, 128),
                _lim(ua, 1024),
                _lim(path, 1024),
            ),
        )

        # 4) If click params exist: first-touch in session + all-touch in DB with debounce
        if captured:
            # First-touch cache in session (optional; handy for business logic/UX)
            if not any(k in sess for k in CLICK_KEYS):
                sess.update(captured)
                sess["click_ts"]   = datetime.now().isoformat()
                sess["landing_url"] = landing_url
                sess["referrer"]    = ref

            # Debounce anon_id+gclid within the configured window
            if not _recent_duplicate(con, anon_id, captured.get("gclid")):
                con.execute("""
                    INSERT INTO click_attribution
                    (anon_id, landing_url, referrer, gclid, gbraid, wbraid,
                     utm_source, utm_medium, utm_campaign, utm_term, utm_content)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    anon_id,
                    _lim(landing_url, 2048),
                    _lim(ref, 2048),
                    _lim(captured.get("gclid"), 256),
                    _lim(captured.get("gbraid"), 256),
                    _lim(captured.get("wbraid"), 256),
                    _lim(captured.get("utm_source"), 256),
                    _lim(captured.get("utm_medium"), 256),
                    _lim(captured.get("utm_campaign"), 512),
                    _lim(captured.get("utm_term"), 512),
                    _lim(captured.get("utm_content"), 512),
                ))
        con.commit()
    finally:
        con.close()
