import json
import os
import random
import sqlite3
import tempfile
from pathlib import Path

import streamlit as st

from userdb import get_user_db
from course_config import get_config

DB_PATH = "chinese_mastery.db"  # Kho chữ tiếng Trung (chỉ đọc khi chạy)


def active_course():
    return st.session_state.get("active_course", "zh")


def variant_key(course, level=None, occupation=None):
    """Khóa kho chữ theo khóa học, trình độ và nghề nghiệp."""
    if occupation:
        return f"{course}:{level or ''}:{occupation}"
    return f"{course}:{level}" if level else course


def active_variant():
    """Khóa kho từ của hồ sơ đang học; dùng làm tham số của các hàm cache."""
    return variant_key(
        active_course(),
        st.session_state.get("course_level"),
        st.session_state.get("course_occupation"),
    )


CEFR_ORDER = ["A1", "A2", "B1", "B2", "C1", "C2"]


def _level_db_path(base_path, level, words_per_day):
    """Kho từ con theo trình độ: chỉ giữ từ CEFR cao hơn trình độ hiện tại, đánh lại ngày học.

    Giữ nguyên `id` từ để tiến độ/độ thuộc đã lưu vẫn dùng được khi đổi trình độ.
    """
    src = Path(base_path)
    path = Path(tempfile.gettempdir()) / f"cm_{src.stem}_{level}_{int(src.stat().st_mtime)}.db"
    if path.exists():
        return str(path)
    keep = set(CEFR_ORDER[CEFR_ORDER.index(level) + 1:])
    conn = sqlite3.connect(src)
    conn.row_factory = sqlite3.Row
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vocab'").fetchone()[0]
    rows = [dict(r) for r in conn.execute("SELECT * FROM vocab ORDER BY study_day, priority_group, id")
            if r["hsk_level"] in keep]
    conn.close()
    for n, row in enumerate(rows):
        row["study_day"] = n // words_per_day + 1
        row["stage_10d"] = (row["study_day"] - 1) // 10 + 1
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.unlink(missing_ok=True)
    out = sqlite3.connect(tmp)
    out.execute(schema)
    if rows:
        cols = list(rows[0])
        out.executemany(
            f"INSERT INTO vocab ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [tuple(r[c] for c in cols) for r in rows])
    out.commit()
    out.close()
    os.replace(tmp, path)
    return str(path)


def _occupation_db_path(base_path, occupation, words_per_day):
    """Kho tiếng Anh theo nghề nghiệp, kèm từ giao tiếp chung và ngày học liên tục."""
    if occupation not in {"OFFICE", "TEACHER"}:
        raise ValueError(f"Nghề nghiệp tiếng Anh không hợp lệ: {occupation}")
    src = Path(base_path)
    path = Path(tempfile.gettempdir()) / f"cm_{src.stem}_{occupation}_{int(src.stat().st_mtime)}.db"
    if path.exists():
        return str(path)
    conn = sqlite3.connect(src)
    conn.row_factory = sqlite3.Row
    schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='vocab'").fetchone()[0]
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM vocab WHERE domain IN (?, 'GENERAL') ORDER BY study_day, priority_group, id",
        (occupation,),
    )]
    conn.close()
    for n, row in enumerate(rows):
        row["study_day"] = n // words_per_day + 1
        row["stage_10d"] = (row["study_day"] - 1) // 10 + 1
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.unlink(missing_ok=True)
    out = sqlite3.connect(tmp)
    out.execute(schema)
    if rows:
        cols = list(rows[0])
        out.executemany(
            f"INSERT INTO vocab ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
            [tuple(r[c] for c in cols) for r in rows])
    out.commit()
    out.close()
    os.replace(tmp, path)
    return str(path)


def vocab_db_path(variant):
    parts = variant.split(":", 2)
    base = parts[0]
    level = parts[1] if len(parts) > 1 else None
    occupation = parts[2] if len(parts) > 2 else None
    cfg = get_config(base)
    path = cfg["db_path"]
    if level in CEFR_ORDER[:-1]:
        path = _level_db_path(path, level, cfg["words_per_day"])
    if occupation:
        if base != "en":
            raise ValueError("Chỉ khóa tiếng Anh hỗ trợ lọc theo nghề nghiệp.")
        path = _occupation_db_path(path, occupation, cfg["words_per_day"])
    return path


def get_db(course=None):
    """Kết nối kho từ `vocab` của khóa học (mặc định: khóa đang học)."""
    conn = sqlite3.connect(vocab_db_path(course or active_variant()))
    conn.row_factory = sqlite3.Row
    return conn


def auth_user_id():
    """Trả về ID của tài khoản đăng nhập (dùng cho bảo mật, quản lý user, đổi mật khẩu)."""
    user_id = st.session_state.get("auth_user_id")
    if user_id is None:
        raise RuntimeError("Chưa đăng nhập")
    return user_id

def current_profile_id():
    """Trả về ID của tiến độ khóa học hiện tại (dùng cho học tập, game, kho đồ)."""
    # Nếu chưa có profile_id trong session (user cũ hoặc đang load), fallback về auth_user_id (vì profile 'zh' mặc định có id = user_id)
    return st.session_state.get("profile_id") or auth_user_id()

def current_user_id():
    """Alias giữ lại để tương thích ngược 100% với các lệnh gọi từ game_core, game_minigames cũ."""
    return current_profile_id()


# ---------------------------------------------------------------------------
# Hồ sơ khóa học (profiles): mỗi khóa của một tài khoản có tiến độ riêng
# ---------------------------------------------------------------------------

EN_PROFILE_MIN_ID = 1_000_000


def list_profiles(user_id):
    """[{id, course, level, occupation}] của tài khoản, khóa tiếng Trung đứng trước."""
    rows = get_user_db().execute(
        "SELECT id, course, level, occupation FROM profiles WHERE user_id = ? ORDER BY course DESC", (user_id,)
    ).fetchall()
    return [{"id": r[0], "course": r[1], "level": r[2], "occupation": r[3]} for r in rows]


def create_profile(user_id, course, level=None, occupation=None):
    """Tạo hồ sơ khóa học (idempotent) cùng tiến độ mặc định; trả về profile_id."""
    existing = next((p for p in list_profiles(user_id) if p["course"] == course), None)
    if existing:
        return existing["id"]
    conn = get_user_db()
    occupation = occupation or ("OFFICE" if course == "en" else None)
    if course == "zh":
        profile_id = user_id  # tương thích dữ liệu cũ: profile zh có id = user id
    else:
        max_id = conn.execute("SELECT MAX(id) FROM profiles").fetchone()[0] or 0
        profile_id = max(max_id + 1, EN_PROFILE_MIN_ID)
    conn.batch([
        ("INSERT INTO profiles (id, user_id, course, level, occupation) VALUES (?, ?, ?, ?, ?)",
         (profile_id, user_id, course, level, occupation)),
        ("INSERT OR IGNORE INTO user_progress (user_id) VALUES (?)", (profile_id,)),
    ])
    return profile_id


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


def record_review_batch(results):
    """Ghi hàng loạt kết quả ôn trong trò chơi: [(vocab_id, đúng?)] bằng một lần gọi DB."""
    if not results:
        return
    user_id = current_user_id()
    statements = []
    for vocab_id, correct in results:
        if correct:
            statements.append((
                """
                INSERT INTO word_mastery (user_id, vocab_id, review_count, mastered_count, last_status)
                VALUES (?, ?, 1, 1, 'MASTERED')
                ON CONFLICT (user_id, vocab_id) DO UPDATE SET
                    review_count = review_count + 1,
                    mastered_count = mastered_count + 1,
                    last_status = 'MASTERED',
                    last_reviewed_at = CURRENT_TIMESTAMP
                """, (user_id, vocab_id)))
        else:
            statements.append((
                """
                INSERT INTO word_mastery (user_id, vocab_id, review_count, failed_count, last_status, is_inner_demon)
                VALUES (?, ?, 1, 1, 'FAILED', 1)
                ON CONFLICT (user_id, vocab_id) DO UPDATE SET
                    review_count = review_count + 1,
                    failed_count = failed_count + 1,
                    last_status = 'FAILED',
                    is_inner_demon = 1,
                    last_reviewed_at = CURRENT_TIMESTAMP
                """, (user_id, vocab_id)))
    get_user_db().batch(statements)


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


def _compose_day_examples(day_words, vocabulary, compose=True):
    """Chọn câu tự nhiên có từ mục tiêu và ưu tiên từ đã học hoặc sắp học."""
    if not compose:  # khóa tiếng Anh: câu ví dụ đã được sinh riêng cho từng từ
        return [dict(word) for word in day_words]
    sentence_sources = []
    for source in vocabulary:
        sentence = source.get("example_zh") or ""
        if sentence:
            matched_words = [word for word in vocabulary if word["hanzi"] in sentence]
            sentence_sources.append((source, matched_words))

    used_sentences = set()
    result = []
    for target in day_words:
        day = target["study_day"]
        candidates = []
        for source, matched_words in sentence_sources:
            sentence = source["example_zh"]
            if target["hanzi"] not in sentence:
                continue

            related_words = [
                word for word in matched_words
                if word["id"] != target["id"]
                and (
                    word["study_day"] < day
                    or day <= word["study_day"] <= day + 3
                )
            ]
            if not related_words:
                continue

            past_words = [word for word in related_words if word["study_day"] < day]
            nearest_future_day = min(
                (word["study_day"] for word in related_words if word["study_day"] >= day),
                default=day + 4,
            )
            score = (
                bool(past_words),
                max((word["study_day"] for word in past_words), default=0),
                len(past_words),
                -nearest_future_day,
                len(related_words),
                source["domain"] == target["domain"],
                source["id"] == target["id"],
            )
            candidates.append((score, source))

        candidates.sort(key=lambda candidate: candidate[0], reverse=True)
        source = next(
            (candidate for _, candidate in candidates
             if candidate["example_zh"] not in used_sentences),
            None,
        )
        if source is None:
            source = next(
                (candidate for candidate, _ in sentence_sources
                 if candidate["id"] == target["id"]
                 and candidate["example_zh"] not in used_sentences),
                None,
            )
        if source is None:
            source = next(
                (candidate for candidate, _ in sentence_sources
                 if target["hanzi"] in candidate["example_zh"]
                 and candidate["example_zh"] not in used_sentences),
                target,
            )

        sentence = source.get("example_zh") or target.get("example_zh", "")
        used_sentences.add(sentence)
        result.append({
            **target,
            "example_zh": sentence,
            "example_pinyin": source.get("example_pinyin") or target.get("example_pinyin", ""),
            "example_vi": source.get("example_vi") or target.get("example_vi", ""),
            "example_cloze": sentence.replace(target["hanzi"], "______", 1)
            if target["hanzi"] in sentence
            else target.get("example_cloze", sentence),
        })
    return result


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

@st.cache_data(show_spinner=False)
def _load_vocabulary(course="zh"):
    conn = get_db(course)
    vocabulary = [dict(r) for r in conn.execute(
        "SELECT * FROM vocab ORDER BY study_day ASC, priority_group ASC, id ASC"
    ).fetchall()]
    conn.close()
    return vocabulary


@st.cache_data(show_spinner=False)
def _load_day_words_cached(day, course="zh"):
    vocabulary = _load_vocabulary(course)
    words = [dict(word) for word in vocabulary if word["study_day"] == day]
    return _compose_day_examples(words, vocabulary, get_config(course)["compose_examples"])


def load_day_words(day):
    return _load_day_words_cached(day, active_variant())


def change_profile_level(profile_id, new_level):
    """Đổi trình độ của hồ sơ: lọc lại kho từ, đưa ngày học về từ đầu tiên chưa học, bỏ vị trí buổi học cũ."""
    conn = get_user_db()
    profile = conn.execute("SELECT level, occupation FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    old_level, occupation = profile["level"], profile["occupation"]
    day = conn.execute("SELECT current_day FROM user_progress WHERE user_id = ?", (profile_id,)).fetchone()[0]
    learned = {w["id"] for w in _load_vocabulary(variant_key("en", old_level, occupation))
               if w["study_day"] < day}
    new_vocab = _load_vocabulary(variant_key("en", new_level, occupation))
    next_day = min((w["study_day"] for w in new_vocab if w["id"] not in learned),
                   default=max((w["study_day"] for w in new_vocab), default=1))
    conn.batch([
        ("UPDATE profiles SET level = ? WHERE id = ?", (new_level, profile_id)),
        ("UPDATE user_progress SET current_day = ? WHERE user_id = ?", (next_day, profile_id)),
        ("DELETE FROM session_state WHERE user_id = ?", (profile_id,)),
    ])
    return next_day


def change_profile_occupation(profile_id, new_occupation):
    """Đổi nghề nghiệp, lọc lại lộ trình và giữ tiến độ thuộc từ hiện có."""
    if new_occupation not in {"OFFICE", "TEACHER"}:
        raise ValueError(f"Nghề nghiệp tiếng Anh không hợp lệ: {new_occupation}")
    conn = get_user_db()
    profile = conn.execute("SELECT level, occupation FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    level, old_occupation = profile["level"], profile["occupation"]
    if new_occupation == old_occupation:
        return None
    day = conn.execute("SELECT current_day FROM user_progress WHERE user_id = ?", (profile_id,)).fetchone()[0]
    learned = {w["id"] for w in _load_vocabulary(variant_key("en", level, old_occupation))
               if w["study_day"] < day}
    new_vocab = _load_vocabulary(variant_key("en", level, new_occupation))
    next_day = min((w["study_day"] for w in new_vocab if w["id"] not in learned),
                   default=max((w["study_day"] for w in new_vocab), default=1))
    conn.batch([
        ("UPDATE profiles SET occupation = ? WHERE id = ?", (new_occupation, profile_id)),
        ("UPDATE user_progress SET current_day = ? WHERE user_id = ?", (next_day, profile_id)),
        ("DELETE FROM session_state WHERE user_id = ?", (profile_id,)),
    ])
    return next_day


def get_vocab_by_ids(ids, course=None):
    """Các từ theo danh sách id, giữ nguyên thứ tự; bỏ qua id không tồn tại."""
    ids = list(ids)
    if not ids:
        return []
    conn = get_db(course)
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


def get_hanzi_options(correct_word, limit=4, course=None):
    """Sinh 4 đáp án (1 đúng, 3 sai ngẫu nhiên) cho test nhanh."""
    conn = get_db(course)
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
    conn = get_db("zh")
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
