"""Đăng nhập, quản lý tài khoản và phiên đăng nhập (token trên URL, giữ qua F5)."""
import base64
import datetime
import hashlib
import hmac
import re
import secrets
import time
from pathlib import Path

import streamlit as st

from database import ensure_user_progress, import_legacy_progress
from userdb import GAME_TABLES, get_user_db, init_schema

PBKDF2_ITERATIONS = 200_000
TOKEN_MINUTES = 60
TOKEN_PARAM = "s"
USERNAME_RE = re.compile(r"^[a-z0-9_.-]{2,32}$")
MIN_PASSWORD_LEN = 4

DEFAULT_ADMIN = ("admin", "123456")


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password, stored):
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except (ValueError, AttributeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def normalize_username(username):
    return (username or "").strip().lower()


@st.cache_resource(show_spinner=False)
def bootstrap():
    """Chạy một lần mỗi tiến trình: tạo bảng, tạo admin mặc định (kèm tiến độ cũ) nếu chưa có tài khoản."""
    init_schema()
    conn = get_user_db()
    if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        username, password = DEFAULT_ADMIN
        user_id = conn.execute(
            "INSERT INTO users (username, display_name, password_hash, is_admin) VALUES (?, ?, ?, 1)",
            (username, "Admin", hash_password(password)),
        ).lastrowid
        ensure_user_progress(user_id)
        import_legacy_progress(user_id)
    conn.execute("DELETE FROM auth_tokens WHERE expires_at < ?", (_now_iso(),))
    return True


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ---------------------------------------------------------------------------
# Tài khoản
# ---------------------------------------------------------------------------

def create_user(username, display_name, password):
    username = normalize_username(username)
    if not USERNAME_RE.match(username):
        return False, "Tên đăng nhập gồm 2-32 ký tự: chữ thường không dấu, số, '.', '_' hoặc '-'."
    if len(password) < MIN_PASSWORD_LEN:
        return False, f"Mật khẩu cần tối thiểu {MIN_PASSWORD_LEN} ký tự."
    conn = get_user_db()
    if conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
        return False, "Tên đăng nhập đã tồn tại."
    user_id = conn.execute(
        "INSERT INTO users (username, display_name, password_hash, is_admin) VALUES (?, ?, ?, 0)",
        (username, (display_name or "").strip() or username, hash_password(password)),
    ).lastrowid
    ensure_user_progress(user_id)
    return True, f"Đã tạo tài khoản '{username}'."


def authenticate(username, password):
    row = get_user_db().execute(
        "SELECT id, username, display_name, password_hash, is_admin FROM users WHERE username = ?",
        (normalize_username(username),),
    ).fetchone()
    stored = row["password_hash"] if row else hash_password("dummy")  # giữ thời gian xử lý như nhau
    if verify_password(password, stored) and row:
        return {k: row[k] for k in ("id", "username", "display_name", "is_admin")}
    return None


def list_users():
    rows = get_user_db().execute(
        """
        SELECT u.id, u.username, u.display_name, u.is_admin, u.created_at,
               p.current_day, p.current_realm
        FROM users u LEFT JOIN user_progress p ON p.user_id = u.id
        ORDER BY u.id
        """
    ).fetchall()
    return [dict(r) for r in rows]


def reset_password(user_id, new_password):
    if len(new_password) < MIN_PASSWORD_LEN:
        return False, f"Mật khẩu cần tối thiểu {MIN_PASSWORD_LEN} ký tự."
    conn = get_user_db()
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(new_password), user_id))
    conn.execute("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,))  # buộc đăng nhập lại
    return True, "Đã đổi mật khẩu."


def delete_user(user_id):
    conn = get_user_db()
    row = conn.execute("SELECT is_admin FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return False, "Không tìm thấy tài khoản."
    if row["is_admin"]:
        return False, "Không thể xóa tài khoản admin."
    # Mỗi khóa học có hồ sơ riêng (id khác id tài khoản) nên phải xóa dữ liệu theo mọi id hồ sơ
    profile_ids = [r[0] for r in conn.execute("SELECT id FROM profiles WHERE user_id = ?", (user_id,)).fetchall()]
    ids = sorted({user_id, *profile_ids})
    progress_tables = ["word_mastery", "exam_history", "session_state", "user_progress", *GAME_TABLES]
    statements = [(f"DELETE FROM {table} WHERE user_id = ?", (i,)) for table in progress_tables for i in ids]
    statements += [
        ("DELETE FROM profiles WHERE user_id = ?", (user_id,)),
        ("DELETE FROM auth_tokens WHERE user_id = ?", (user_id,)),
        ("DELETE FROM users WHERE id = ?", (user_id,)),
    ]
    conn.batch(statements)
    return True, "Đã xóa tài khoản và toàn bộ tiến độ của người đó."


def admin_has_default_password():
    row = get_user_db().execute(
        "SELECT password_hash FROM users WHERE username = ? AND is_admin = 1", (DEFAULT_ADMIN[0],)
    ).fetchone()
    return bool(row) and verify_password(DEFAULT_ADMIN[1], row["password_hash"])


# ---------------------------------------------------------------------------
# Phiên đăng nhập (cookie giữ đăng nhập qua F5)
# ---------------------------------------------------------------------------

def _token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(user_id):
    token = secrets.token_urlsafe(32)
    expires = (datetime.datetime.now(datetime.timezone.utc)
               + datetime.timedelta(minutes=TOKEN_MINUTES)).strftime("%Y-%m-%dT%H:%M:%S")
    get_user_db().execute(
        "INSERT INTO auth_tokens (token_hash, user_id, expires_at) VALUES (?, ?, ?)",
        (_token_hash(token), user_id, expires),
    )
    return token


def user_from_token(token):
    row = get_user_db().execute(
        """
        SELECT u.id, u.username, u.display_name, u.is_admin
        FROM auth_tokens t JOIN users u ON u.id = t.user_id
        WHERE t.token_hash = ? AND t.expires_at > ?
        """,
        (_token_hash(token), _now_iso()),
    ).fetchone()
    return {k: row[k] for k in ("id", "username", "display_name", "is_admin")} if row else None


def _url_token():
    try:
        return st.query_params.get(TOKEN_PARAM)
    except Exception:
        return None


def _start_session(user, token):
    st.session_state.auth_user_id = user["id"]
    st.session_state.auth_username = user["username"]
    st.session_state.auth_name = user["display_name"] or user["username"]
    st.session_state.auth_is_admin = bool(user["is_admin"])
    st.session_state.auth_token = token
    st.query_params[TOKEN_PARAM] = token


def logout():
    token = st.session_state.get("auth_token")
    if token:
        get_user_db().execute("DELETE FROM auth_tokens WHERE token_hash = ?", (_token_hash(token),))
    st.session_state.clear()
    st.query_params.clear()
def _render_login():
    logo = base64.b64encode((Path(__file__).parent / "logo_cropped.png").read_bytes()).decode()
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            f"""
            <div class='hero' style='flex-direction:column; text-align:center;'>
                <img src='data:image/png;base64,{logo}' alt='HSK'>
                <div class='hero-title'>Thực Chiến Tiếng Trung</div>
                <div class='hero-sub'>Đăng nhập để tiếp tục tu luyện</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập")
            password = st.text_input("Mật khẩu", type="password")
            submitted = st.form_submit_button("Đăng nhập", use_container_width=True, type="primary")
        if submitted:
            user = authenticate(username, password)
            if user:
                _start_session(user, issue_token(user["id"]))
                st.session_state["choose_course"] = True
                st.rerun()
            time.sleep(1)  # làm chậm việc dò mật khẩu
            st.error("Sai tên đăng nhập hoặc mật khẩu.")


def require_login():
    """Dừng trang và hiện màn hình đăng nhập nếu chưa đăng nhập."""
    bootstrap()
    if not st.session_state.get("auth_user_id"):
        token = _url_token()
        user = user_from_token(token) if token else None
        if user:
            _start_session(user, token)
        else:
            if token:
                st.query_params.clear()
            _render_login()
            st.stop()
