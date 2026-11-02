"""Kho dữ liệu người dùng: Turso (HTTP) khi có cấu hình, nếu không thì file SQLite cục bộ.

Kho chữ `vocab` nằm riêng trong chinese_mastery.db (xem database.py).
"""
import base64
import os
import sqlite3
import threading

import requests
import streamlit as st

LOCAL_USER_DB = "user_data.db"

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        display_name TEXT,
        password_hash TEXT NOT NULL,
        is_admin INTEGER NOT NULL DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS user_progress (
        user_id INTEGER PRIMARY KEY,
        current_realm TEXT DEFAULT 'Luyện Khí Tầng 1',
        realm_level INTEGER DEFAULT 1,
        spiritual_energy INTEGER DEFAULT 0,
        current_day INTEGER DEFAULT 1,
        consecutive_streak INTEGER DEFAULT 0,
        last_study_date TEXT,
        is_bottleneck INTEGER DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS word_mastery (
        user_id INTEGER NOT NULL,
        vocab_id INTEGER NOT NULL,
        review_count INTEGER DEFAULT 0,
        failed_count INTEGER DEFAULT 0,
        vague_count INTEGER DEFAULT 0,
        mastered_count INTEGER DEFAULT 0,
        last_status TEXT DEFAULT 'NEW',
        is_inner_demon INTEGER DEFAULT 0,
        last_reviewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, vocab_id)
    )""",
    """CREATE TABLE IF NOT EXISTS exam_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        exam_type TEXT NOT NULL,
        stage_number INTEGER NOT NULL,
        total_questions INTEGER NOT NULL,
        correct_answers INTEGER NOT NULL,
        score_percent REAL NOT NULL,
        is_passed INTEGER NOT NULL,
        weak_words_tested TEXT,
        taken_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    "CREATE INDEX IF NOT EXISTS idx_exam_user ON exam_history (user_id, id)",
    """CREATE TABLE IF NOT EXISTS session_state (
        user_id INTEGER PRIMARY KEY,
        data TEXT NOT NULL,
        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS auth_tokens (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
        key TEXT PRIMARY KEY,
        value TEXT
    )""",
]


class Row:
    """Hàng kết quả: truy cập được theo chỉ số, theo tên cột và dict(row)."""

    __slots__ = ("_cols", "_vals")

    def __init__(self, cols, vals):
        self._cols = cols
        self._vals = vals

    def __getitem__(self, key):
        if isinstance(key, str):
            return self._vals[self._cols.index(key)]
        return self._vals[key]

    def keys(self):
        return list(self._cols)

    def __iter__(self):
        return iter(self._vals)

    def __len__(self):
        return len(self._vals)


class TursoError(RuntimeError):
    pass


def _encode_arg(value):
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "integer", "value": str(int(value))}
    if isinstance(value, int):
        return {"type": "integer", "value": str(value)}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, bytes):
        return {"type": "blob", "base64": base64.b64encode(value).decode()}
    return {"type": "text", "value": str(value)}


def _decode_value(cell):
    kind = cell.get("type")
    if kind == "null":
        return None
    if kind == "integer":
        return int(cell["value"])
    if kind == "float":
        return float(cell["value"])
    if kind == "blob":
        return base64.b64decode(cell.get("base64", ""))
    return cell.get("value")


class TursoCursor:
    def __init__(self, result):
        cols = [c.get("name") for c in result.get("cols", [])]
        self._rows = [Row(cols, [_decode_value(c) for c in raw]) for raw in result.get("rows", [])]
        self.rowcount = result.get("affected_row_count", 0)
        last_id = result.get("last_insert_rowid")
        self.lastrowid = int(last_id) if last_id is not None else None

    def fetchone(self):
        return self._rows.pop(0) if self._rows else None

    def fetchall(self):
        rows, self._rows = self._rows, []
        return rows

    def __iter__(self):
        return iter(self.fetchall())


_http_lock = threading.Lock()
_http_session = None


def _session():
    global _http_session
    with _http_lock:
        if _http_session is None:
            _http_session = requests.Session()
        return _http_session


class TursoConnection:
    """Giao diện giống sqlite3, mỗi câu lệnh là một lần gọi HTTP (tự commit)."""

    def __init__(self, url, token):
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self._endpoint = url.rstrip("/") + "/v2/pipeline"
        self._headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def _pipeline(self, requests_list):
        try:
            resp = _session().post(
                self._endpoint,
                json={"requests": requests_list + [{"type": "close"}]},
                headers=self._headers,
                timeout=30,
            )
        except requests.RequestException as exc:
            raise TursoError(f"Không kết nối được Turso: {exc}") from exc
        if resp.status_code != 200:
            raise TursoError(f"Turso trả về lỗi {resp.status_code}: {resp.text[:200]}")
        results = resp.json().get("results", [])
        for item in results:
            if item.get("type") == "error":
                raise TursoError(item.get("error", {}).get("message", "Lỗi không xác định"))
        return results

    @staticmethod
    def _stmt(sql, params):
        return {"sql": sql, "args": [_encode_arg(p) for p in params]}

    def execute(self, sql, params=()):
        results = self._pipeline([{"type": "execute", "stmt": self._stmt(sql, params)}])
        return TursoCursor(results[0]["response"]["result"])

    def batch(self, statements):
        """Chạy danh sách (sql, params) trong một giao dịch; lỗi ở bước nào cũng hoàn tác toàn bộ."""
        if not statements:
            return
        steps = [{"stmt": self._stmt("BEGIN", ())}]
        for i, (sql, params) in enumerate(statements, start=1):
            steps.append({"stmt": self._stmt(sql, params), "condition": {"type": "ok", "step": i - 1}})
        last = len(statements)
        steps.append({"stmt": self._stmt("COMMIT", ()), "condition": {"type": "ok", "step": last}})
        steps.append({
            "stmt": self._stmt("ROLLBACK", ()),
            "condition": {"type": "not", "cond": {"type": "ok", "step": last + 1}},
        })
        results = self._pipeline([{"type": "batch", "batch": {"steps": steps}}])
        result = results[0]["response"]["result"]
        failed = next((e for e in result.get("step_errors", []) if e), None)
        if failed:
            raise TursoError(failed.get("message", "Giao dịch thất bại và đã hoàn tác"))

    def commit(self):
        pass

    def close(self):
        pass


class LocalConnection:
    """SQLite cục bộ (dùng khi chưa cấu hình Turso), cùng giao diện với TursoConnection."""

    def __init__(self, path):
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row

    def execute(self, sql, params=()):
        cursor = self._conn.execute(sql, params)
        self._conn.commit()
        return cursor

    def batch(self, statements):
        try:
            for sql, params in statements:
                self._conn.execute(sql, params)
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    def commit(self):
        self._conn.commit()

    def close(self):
        self._conn.close()


def _turso_config():
    url = os.environ.get("TURSO_DATABASE_URL")
    token = os.environ.get("TURSO_AUTH_TOKEN")
    if url and token:
        return url, token
    try:
        section = st.secrets.get("turso")
        if section and section.get("url") and section.get("auth_token"):
            return section["url"], section["auth_token"]
    except Exception:
        pass
    return None


def using_turso():
    return _turso_config() is not None


def get_user_db():
    config = _turso_config()
    if config:
        return TursoConnection(*config)
    return LocalConnection(LOCAL_USER_DB)


def init_schema():
    get_user_db().batch([(sql, ()) for sql in SCHEMA])


def get_meta(key, default=None):
    row = get_user_db().execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return row[0] if row else default


def set_meta(key, value):
    get_user_db().execute(
        "INSERT INTO meta (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
        (key, str(value)),
    )
