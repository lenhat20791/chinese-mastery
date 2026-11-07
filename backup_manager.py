"""Sao lưu / khôi phục tiến độ của tất cả người dùng lên Google Drive (file JSON)."""
import datetime
import io
import json
import os

import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from userdb import get_user_db, set_meta

# Quyền hạn tối thiểu: chỉ truy cập các file do chính ứng dụng tạo ra
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"
DRIVE_FOLDER_ID = "1-jpbHMEUaOQASvQFX89KfxzeZO-6Vq_B"
BACKUP_PREFIX = "progress_backup_"
KEEP_BACKUPS = 8
BACKUP_FORMAT = "chinese-mastery-progress"

# Bảng cần sao lưu và các cột hợp lệ (danh sách cố định để lúc khôi phục không chèn cột lạ)
BACKUP_TABLES = {
    "users": ["id", "username", "display_name", "password_hash", "is_admin", "created_at"],
    "user_progress": ["user_id", "current_realm", "realm_level", "spiritual_energy", "current_day",
                      "consecutive_streak", "last_study_date", "is_bottleneck"],
    "word_mastery": ["user_id", "vocab_id", "review_count", "failed_count", "vague_count",
                     "mastered_count", "last_status", "is_inner_demon", "last_reviewed_at"],
    "exam_history": ["id", "user_id", "exam_type", "stage_number", "total_questions", "correct_answers",
                     "score_percent", "is_passed", "weak_words_tested", "taken_at"],
    "session_state": ["user_id", "data", "updated_at"],
    "profiles": ["id", "user_id", "course", "level", "created_at"],
    "game_profile": ["user_id", "linh_thach", "equipped_artifact", "equipped_title", "pity_mid", "pity_high",
                     "fortune_streak", "fortune_last_day"],
    "game_daily": ["user_id", "day", "plays"],
    "game_inventory": ["user_id", "item_code", "qty"],
    "game_recipes": ["user_id", "recipe_code"],
    "game_artifacts": ["id", "user_id", "recipe_code", "quality", "upgrade", "created_at"],
    "game_fortune": ["user_id", "day", "vocab_id", "tier", "status", "buff"],
    "game_achievements": ["user_id", "code", "unlocked_at"],
    "game_counters": ["user_id", "key", "value"],
    "game_log": ["id", "user_id", "ts", "kind", "text"],
    # Phiên 4: Luyện đan
    "game_pills": ["user_id", "pill_code", "qty"],
    "game_pill_recipes": ["user_id", "recipe_code"],
    # Phiên 6: Vẽ phù
    "game_talismans": ["user_id", "talisman_code", "qty"],
    "game_talisman_recipes": ["user_id", "recipe_code"],
    "game_talisman_words": ["user_id", "course", "data"],
    # Phiên 8-9: Công pháp & đan điền
    "game_techniques": ["id", "user_id", "technique_code", "dantian_row", "dantian_col", "is_equipped", "acquired_at"],
    "game_techniques_equipped": ["user_id", "technique_slot_1", "technique_slot_2"],
}
CORE_TABLES = ["users", "user_progress", "word_mastery", "exam_history", "session_state"]


def _secret_exists(name):
    try:
        return name in st.secrets
    except Exception:
        return False


def get_drive_service():
    """Xác thực Drive: ưu tiên st.secrets (trên mây), nếu không thì token.json/credentials.json cục bộ."""
    creds = None

    if _secret_exists("google_token") and _secret_exists("google_credentials"):
        try:
            creds = Credentials.from_authorized_user_info(dict(st.secrets["google_token"]), SCOPES)
        except Exception as e:
            print(f"Lỗi đọc token từ secrets: {e}")
    elif os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if os.path.exists(CREDENTIALS_FILE):
            try:
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
                with open(TOKEN_FILE, "w", encoding="utf-8") as token:
                    token.write(creds.to_json())
            except Exception:
                return None
        elif _secret_exists("google_credentials"):
            try:
                cred_info = dict(st.secrets["google_credentials"])
                token_info = dict(st.secrets["google_token"]) if _secret_exists("google_token") else {}
                if "refresh_token" in token_info:
                    creds = Credentials(
                        token=token_info.get("token"),
                        refresh_token=token_info.get("refresh_token"),
                        token_uri=token_info.get("token_uri"),
                        client_id=cred_info.get("client_id"),
                        client_secret=cred_info.get("client_secret"),
                        scopes=SCOPES,
                    )
                    creds.refresh(Request())
            except Exception:
                return None
        else:
            return None

    return build("drive", "v3", credentials=creds) if creds else None


# ---------------------------------------------------------------------------
# Xuất / nhập dữ liệu
# ---------------------------------------------------------------------------

def export_progress():
    conn = get_user_db()
    tables = {
        name: [dict(r) for r in conn.execute(f"SELECT {', '.join(cols)} FROM {name}").fetchall()]
        for name, cols in BACKUP_TABLES.items()
    }
    payload = {
        "format": BACKUP_FORMAT,
        "version": 1,
        "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "tables": tables,
    }
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def import_progress(raw):
    """Ghi đè toàn bộ dữ liệu người dùng bằng bản sao lưu; lỗi giữa chừng thì hoàn tác."""
    try:
        payload = json.loads(raw.decode("utf-8"))
        tables = payload["tables"]
        assert payload["format"] == BACKUP_FORMAT
        assert all(isinstance(tables[name], list) for name in CORE_TABLES)
        assert any(u.get("is_admin") for u in tables["users"]), "thiếu tài khoản admin"
    except (ValueError, KeyError, TypeError, AssertionError, AttributeError) as exc:
        return False, f"File sao lưu không hợp lệ ({exc})."

    # Bản sao lưu cũ chưa có bảng trò chơi: giữ nguyên dữ liệu trò chơi hiện tại
    present = [name for name in BACKUP_TABLES if isinstance(tables.get(name), list)]
    statements = [(f"DELETE FROM {name}", ()) for name in present + ["auth_tokens"]]
    for name in present:
        columns = BACKUP_TABLES[name]
        for row in tables[name]:
            used = [c for c in columns if c in row]
            marks = ", ".join("?" for _ in used)
            statements.append((
                f"INSERT INTO {name} ({', '.join(used)}) VALUES ({marks})",
                tuple(row[c] for c in used),
            ))
    try:
        # Bản sao lưu cũ chưa có hồ sơ khóa học: tạo lại hồ sơ tiếng Trung (id = id tài khoản)
        statements.append(("INSERT OR IGNORE INTO profiles (id, user_id, course) SELECT id, id, 'zh' FROM users", ()))
        get_user_db().batch(statements)
    except Exception as exc:
        return False, f"Khôi phục thất bại, dữ liệu hiện tại được giữ nguyên: {exc}"
    return True, f"Đã khôi phục {len(tables['users'])} tài khoản."


# ---------------------------------------------------------------------------
# Google Drive
# ---------------------------------------------------------------------------

def _list_backup_files(service):
    result = service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and trashed = false and name contains '{BACKUP_PREFIX}'",
        spaces="drive",
        fields="files(id, name, createdTime)",
        orderBy="createdTime desc",
    ).execute()
    return result.get("files", [])


def list_progress_backups():
    try:
        service = get_drive_service()
        return _list_backup_files(service) if service else []
    except Exception:
        return []


def backup_to_drive():
    """Tải bản sao lưu mới lên Drive và chỉ giữ KEEP_BACKUPS bản gần nhất."""
    try:
        service = get_drive_service()
        if not service:
            return False, "Không thể xác thực tài khoản Google Drive!"

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        media = MediaIoBaseUpload(io.BytesIO(export_progress()), mimetype="application/json", resumable=False)
        service.files().create(
            body={"name": f"{BACKUP_PREFIX}{timestamp}.json", "parents": [DRIVE_FOLDER_ID]},
            media_body=media,
            fields="id",
        ).execute()

        for old_file in _list_backup_files(service)[KEEP_BACKUPS:]:
            service.files().delete(fileId=old_file["id"]).execute()

        set_meta("last_backup_at", datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
        return True, f"Đã sao lưu tiến độ của mọi người lên Drive (giữ {KEEP_BACKUPS} bản gần nhất)."
    except Exception as e:
        return False, f"Lỗi sao lưu: {e}"


def restore_from_drive(file_id):
    try:
        service = get_drive_service()
        if not service:
            return False, "Không thể xác thực tài khoản Google Drive!"

        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, service.files().get_media(fileId=file_id))
        done = False
        while not done:
            _, done = downloader.next_chunk()
        return import_progress(buffer.getvalue())
    except Exception as e:
        return False, f"Lỗi khôi phục: {e}"
