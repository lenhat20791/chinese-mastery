import json
import random
import sqlite3

import streamlit as st

from userdb import get_user_db

DB_PATH = "chinese_mastery.db"  # Kho chữ dùng chung (chỉ đọc khi chạy)


def get_db():
    """Kết nối kho chữ `vocab`."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def current_user_id():
    user_id = st.session_state.get("auth_user_id")
    if user_id is None:
        raise RuntimeError("Chưa đăng nhập")
    return user_id


# ---------------------------------------------------------------------------
# Tiến độ cá nhân (lưu theo user_id trong kho người dùng)
# ---------------------------------------------------------------------------

def ensure_user_progress(user_id):
    get_user_db().execute("INSERT OR IGNORE INTO user_progress (user_id) VALUES (?)", (user_id,))


def load_user_progress():
    user_id = current_user_id()
    conn = get_user_db()
    query = """
        SELECT current_realm, realm_level, spiritual_energy, current_day,
               consecutive_streak, last_study_date, is_bottleneck
        FROM user_progress WHERE user_id = ?
    """
    row = conn.execute(query, (user_id,)).fetchone()
    if row is None:
        ensure_user_progress(user_id)
        row = conn.execute(query, (user_id,)).fetchone()
    return {
        "id": user_id,
        "current_realm": row[0],
        "realm_level": row[1],
        "spiritual_energy": row[2],
        "current_day": row[3],
        "consecutive_streak": row[4],
        "last_study_date": row[5],
        "is_bottleneck": bool(row[6]),
    }


def update_user_energy(amount):
    """
    Nạp thêm hoặc tiêu hao Linh Lực.
    amount > 0: nạp (học bài/ôn bài); amount < 0: tiêu hao (phí Lôi Kiếp).
    """
    get_user_db().execute(
        "UPDATE user_progress SET spiritual_energy = MAX(0, spiritual_energy + ?) WHERE user_id = ?",
        (amount, current_user_id()),
    )


def advance_user_day(new_day=None):
    get_user_db().execute(
        "UPDATE user_progress SET current_day = COALESCE(?, current_day + 1) WHERE user_id = ?",
        (new_day, current_user_id()),
    )


def promote_user_realm():
    """Tăng 1 tiểu tầng cảnh giới (ví dụ Luyện Khí Tầng 1 -> Tầng 2)."""
    user_id = current_user_id()
    conn = get_user_db()
    row = conn.execute(
        "SELECT current_realm, realm_level FROM user_progress WHERE user_id = ?", (user_id,)
    ).fetchone()
    new_level = row["realm_level"] + 1
    base_name = row["current_realm"].split("Tầng")[0].strip()
    updated_realm_name = f"{base_name} Tầng {new_level}"
    conn.execute(
        "UPDATE user_progress SET realm_level = ?, current_realm = ? WHERE user_id = ?",
        (new_level, updated_realm_name, user_id),
    )
    return updated_realm_name


def set_bottleneck_state(is_active: bool):
    """Kích hoạt hoặc gỡ bỏ trạng thái Bình Cảnh (khóa tiến độ học từ mới)."""
    get_user_db().execute(
        "UPDATE user_progress SET is_bottleneck = ? WHERE user_id = ?",
        (1 if is_active else 0, current_user_id()),
    )


def record_exam_result(exam_type, stage_number, total_q, correct_q, is_passed, weak_words=""):
    score_pct = (correct_q / total_q) * 100 if total_q > 0 else 0
    get_user_db().execute(
        """
        INSERT INTO exam_history (user_id, exam_type, stage_number, total_questions, correct_answers,
                                  score_percent, is_passed, weak_words_tested)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (current_user_id(), exam_type, stage_number, total_q, correct_q, score_pct,
         1 if is_passed else 0, weak_words),
    )


FEEDBACK_ACTIONS = {
    # action: (cột đếm, trạng thái, có gắn cờ Tâm Ma không)
    1: ("failed_count", "FAILED", True),
    2: ("vague_count", "VAGUE", True),
    3: ("mastered_count", "MASTERED", False),
}


def record_feedback(vocab_id, action):
    # 1 = FAILED, 2 = VAGUE, 3 = MASTERED
    if action not in FEEDBACK_ACTIONS:
        return
    count_col, status, is_demon = FEEDBACK_ACTIONS[action]
    get_user_db().execute(
        f"""
        INSERT INTO word_mastery (user_id, vocab_id, review_count, {count_col}, last_status, is_inner_demon)
        VALUES (?, ?, 1, 1, ?, ?)
        ON CONFLICT (user_id, vocab_id) DO UPDATE SET
            review_count = review_count + 1,
            {count_col} = {count_col} + 1,
            last_status = excluded.last_status,
            is_inner_demon = MAX(is_inner_demon, excluded.is_inner_demon),
            last_reviewed_at = CURRENT_TIMESTAMP
        """,
        (current_user_id(), vocab_id, status, 1 if is_demon else 0),
    )


def exorcise_inner_demon(vocab_id):
    get_user_db().execute(
        """
        INSERT INTO word_mastery (user_id, vocab_id, mastered_count, last_status, is_inner_demon)
        VALUES (?, ?, 1, 'MASTERED', 0)
        ON CONFLICT (user_id, vocab_id) DO UPDATE SET
            is_inner_demon = 0,
            mastered_count = mastered_count + 1,
            last_status = 'MASTERED',
            last_reviewed_at = CURRENT_TIMESTAMP
        """,
        (current_user_id(), vocab_id),
    )


def _demon_rows():
    rows = get_user_db().execute(
        """
        SELECT vocab_id, failed_count, vague_count, review_count
        FROM word_mastery WHERE user_id = ? AND is_inner_demon = 1
        """,
        (current_user_id(),),
    ).fetchall()
    return [dict(r) for r in rows]


def get_inner_demons(limit=4):
    demons = _demon_rows()
    vocab = {w["id"]: w for w in get_vocab_by_ids([d["vocab_id"] for d in demons])}
    result = []
    for d in demons:
        word = vocab.get(d["vocab_id"])
        if word:
            result.append({**word, **{k: d[k] for k in ("failed_count", "vague_count", "review_count")},
                           "fail_rate": d["failed_count"] / max(d["review_count"], 1)})
    random.shuffle(result)  # ngẫu nhiên khi bằng điểm
    result.sort(key=lambda w: (-w["fail_rate"], -w["failed_count"]))
    return result[:limit]


def get_cultivation_stats():
    """Số liệu tổng quan về tiến độ học và trạng thái từ vựng."""
    conn = get_db()
    total_vocab = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    conn.close()

    row = get_user_db().execute(
        """
        SELECT
            SUM(CASE WHEN last_status = 'MASTERED' THEN 1 ELSE 0 END) AS mastered,
            SUM(CASE WHEN last_status = 'VAGUE' THEN 1 ELSE 0 END) AS vague,
            SUM(CASE WHEN last_status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN is_inner_demon = 1 THEN 1 ELSE 0 END) AS demons,
            SUM(CASE WHEN review_count > 0 THEN 1 ELSE 0 END) AS learned
        FROM word_mastery WHERE user_id = ?
        """,
        (current_user_id(),),
    ).fetchone()
    return {
        "total_vocab": total_vocab,
        "mastered": row["mastered"] or 0,
        "vague": row["vague"] or 0,
        "failed": row["failed"] or 0,
        "demons": row["demons"] or 0,
        "learned": row["learned"] or 0,
    }


def get_all_demons_detailed():
    """Toàn bộ từ đang dính cờ Tâm Ma kèm số lần sai."""
    demons = _demon_rows()
    vocab = {w["id"]: w for w in get_vocab_by_ids([d["vocab_id"] for d in demons])}
    result = []
    for d in demons:
        word = vocab.get(d["vocab_id"])
        if word:
            result.append({
                "hanzi": word["hanzi"], "pinyin": word["pinyin"], "hanviet": word["hanviet"],
                "meaning_vi": word["meaning_vi"], "study_day": word["study_day"],
                "failed_count": d["failed_count"], "vague_count": d["vague_count"],
                "review_count": d["review_count"],
                "fail_rate_pct": round(d["failed_count"] / max(d["review_count"], 1) * 100, 1),
            })
    result.sort(key=lambda r: (-r["failed_count"], -r["review_count"]))
    return result


def get_recent_exam_history(limit=10):
    rows = get_user_db().execute(
        """
        SELECT exam_type, stage_number, total_questions, correct_answers,
               score_percent, is_passed, taken_at
        FROM exam_history WHERE user_id = ?
        ORDER BY id DESC LIMIT ?
        """,
        (current_user_id(), limit),
    ).fetchall()
    return [dict(r) for r in rows]


def get_tribulation_cost(is_major_breakthrough=False):
    """
    Chi phí linh lực để mở khóa bài thi Lôi Kiếp.
    Tiểu tầng: 35 (5 ngày x 20 linh lực/ngày = 100, thu 35%); đại cảnh giới: gấp 3.
    """
    base_cost = 35
    return base_cost * 3 if is_major_breakthrough else base_cost


# ---------------------------------------------------------------------------
# Lưu vị trí buổi học để F5 không mất tiến trình
# ---------------------------------------------------------------------------

def save_session_snapshot(snapshot):
    get_user_db().execute(
        """
        INSERT INTO session_state (user_id, data, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT (user_id) DO UPDATE SET data = excluded.data, updated_at = CURRENT_TIMESTAMP
        """,
        (current_user_id(), json.dumps(snapshot)),
    )


def load_session_snapshot():
    row = get_user_db().execute(
        "SELECT data FROM session_state WHERE user_id = ?", (current_user_id(),)
    ).fetchone()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Kho chữ dùng chung (chỉ đọc)
# ---------------------------------------------------------------------------

def load_day_words(day):
    conn = get_db()
    words = [dict(r) for r in conn.execute(
        "SELECT * FROM vocab WHERE study_day = ? ORDER BY id ASC", (day,)
    ).fetchall()]
    conn.close()
    return words


def get_vocab_by_ids(ids):
    """Các từ theo danh sách id, giữ nguyên thứ tự; bỏ qua id không tồn tại."""
    ids = list(ids)
    if not ids:
        return []
    conn = get_db()
    marks = ",".join("?" * len(ids))
    found = {r["id"]: dict(r) for r in conn.execute(f"SELECT * FROM vocab WHERE id IN ({marks})", ids)}
    conn.close()
    return [found[i] for i in ids if i in found]


def get_recent_words_for_exam(current_day, days_back=3, limit=8):
    conn = get_db()
    start_day = max(1, current_day - days_back + 1)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM vocab WHERE study_day >= ? AND study_day <= ? ORDER BY RANDOM() LIMIT ?",
        (start_day, current_day, limit),
    ).fetchall()]
    conn.close()
    return rows


def count_learned_words(current_day):
    """Số từ đã học hoặc đang học (tính đến ngày hiện tại)."""
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM vocab WHERE study_day <= ?", (current_day,)).fetchone()[0]
    conn.close()
    return total


def get_learned_words(current_day, limit, offset):
    """Một trang từ đã học, ngày mới nhất lên đầu."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM vocab WHERE study_day <= ? ORDER BY study_day DESC, id ASC LIMIT ? OFFSET ?",
        (current_day, limit, offset),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_hanzi_options(correct_word, limit=4):
    """Sinh 4 đáp án chữ Hán (1 đúng, 3 sai ngẫu nhiên) cho test nhanh."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, hanzi, pinyin FROM vocab WHERE id != ? ORDER BY RANDOM() LIMIT ?",
        (correct_word["id"], limit - 1),
    ).fetchall()
    conn.close()

    options = [{"id": r[0], "hanzi": r[1], "pinyin": r[2]} for r in rows]
    options.append({
        "id": correct_word["id"],
        "hanzi": correct_word["hanzi"],
        "pinyin": correct_word["pinyin"],
    })
    random.shuffle(options)
    return options


# ---------------------------------------------------------------------------
# Chuyển tiến độ cũ (bảng một người dùng trong chinese_mastery.db) sang tài khoản admin
# ---------------------------------------------------------------------------

def import_legacy_progress(user_id):
    conn = get_db()
    try:
        progress = conn.execute("SELECT * FROM user_progress WHERE id = 1").fetchone()
        mastery = conn.execute("SELECT * FROM word_mastery WHERE review_count > 0").fetchall()
        exams = conn.execute("SELECT * FROM exam_history").fetchall()
    except sqlite3.OperationalError:
        return
    finally:
        conn.close()

    statements = []
    if progress:
        statements.append((
            """
            INSERT OR REPLACE INTO user_progress (user_id, current_realm, realm_level, spiritual_energy,
                current_day, consecutive_streak, last_study_date, is_bottleneck)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, progress["current_realm"], progress["realm_level"], progress["spiritual_energy"],
             progress["current_day"], progress["consecutive_streak"], progress["last_study_date"],
             progress["is_bottleneck"]),
        ))
    for m in mastery:
        statements.append((
            """
            INSERT OR REPLACE INTO word_mastery (user_id, vocab_id, review_count, failed_count, vague_count,
                mastered_count, last_status, is_inner_demon, last_reviewed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, m["vocab_id"], m["review_count"], m["failed_count"], m["vague_count"],
             m["mastered_count"], m["last_status"], int(bool(m["is_inner_demon"])), m["last_reviewed_at"]),
        ))
    for e in exams:
        statements.append((
            """
            INSERT INTO exam_history (user_id, exam_type, stage_number, total_questions, correct_answers,
                score_percent, is_passed, weak_words_tested, taken_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, e["exam_type"], e["stage_number"], e["total_questions"], e["correct_answers"],
             e["score_percent"], int(bool(e["is_passed"])), e["weak_words_tested"], e["taken_at"]),
        ))
    get_user_db().batch(statements)
