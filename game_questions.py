"""Kho từ đã học cho trò chơi và sinh câu hỏi ôn tập (không phụ thuộc giao diện, dễ kiểm thử)."""
import random
import re
import unicodedata

import streamlit as st

from course_config import get_config
from database import active_variant, current_user_id, get_db
from userdb import get_user_db

QTYPES = ("h2m", "m2h", "audio", "pinyin", "cloze")
PUNCT = "。，、！？；：,.!?;:“”\"'‘’（）() …—-"
STUDYING_PHASES = ("SHADOWING", "CLOZE", "REVIEW", "COMPLETED")


def learned_day_for(user, phase):
    """Ngày cuối cùng được xem là đã học: hôm nay chỉ tính khi đã qua chặng thẻ từ (hoặc Bình Cảnh)."""
    day = user["current_day"]
    return day if user.get("is_bottleneck") or phase in STUDYING_PHASES else day - 1


@st.cache_data(show_spinner=False)
def _load_pool(learned_day, course):
    conn = get_db(course)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM vocab WHERE study_day <= ? ORDER BY study_day, id", (learned_day,)
    ).fetchall()]
    conn.close()
    return rows


def load_pool(learned_day):
    """Các từ đã học (study_day <= learned_day) của khóa đang học, thứ tự ổn định."""
    return _load_pool(learned_day, active_variant())


@st.cache_data(show_spinner=False)
def _all_hanzi(course):
    conn = get_db(course)
    words = sorted({r[0] for r in conn.execute("SELECT hanzi FROM vocab")}, key=len, reverse=True)
    conn.close()
    return words


def all_hanzi():
    return _all_hanzi(active_variant())


def join_tokens(tokens):
    """Ghép các cụm thành câu: tiếng Trung liền nhau, tiếng Anh cách bằng dấu cách."""
    return ("" if get_config()["has_pinyin"] else " ").join(tokens)


def load_mastery():
    """vocab_id -> (review_count, failed_count, is_demon)."""
    rows = get_user_db().execute(
        "SELECT vocab_id, review_count, failed_count, is_inner_demon FROM word_mastery WHERE user_id = ?",
        (current_user_id(),),
    ).fetchall()
    return {r[0]: (r[1] or 0, r[2] or 0, r[3] or 0) for r in rows}


def word_weight(word_id, mastery):
    """Từ chưa vững (sai nhiều, tâm ma, ít được ôn) có trọng số cao hơn."""
    reviews, failed, demon = mastery.get(word_id, (0, 0, 0))
    weight = 1.0 + 3.0 * failed / (reviews + 1) + (2.0 if demon else 0.0)
    if reviews == 0:
        weight += 1.5
    return weight


def pick_words(pool, mastery, count, rng=random, exclude=()):
    candidates = [w for w in pool if w["id"] not in set(exclude)]
    chosen = []
    while candidates and len(chosen) < count:
        weights = [word_weight(w["id"], mastery) for w in candidates]
        word = rng.choices(candidates, weights=weights, k=1)[0]
        chosen.append(word)
        candidates.remove(word)
    return chosen


def pick_words_with_rotation(pool, mastery, count, session_state_key="word_rotation", rng=random, exclude=()):
    """Pick words without early repeats by cycling through pool via session state."""
    if session_state_key not in st.session_state:
        st.session_state[session_state_key] = {"used_ids": set(), "position": 0}
    
    rotation = st.session_state[session_state_key]
    candidates = [w for w in pool if w["id"] not in set(exclude) and w["id"] not in rotation["used_ids"]]
    
    # If we've used all candidates, reset and start new rotation
    if not candidates:
        rotation["used_ids"] = set()
        rotation["position"] = 0
        candidates = [w for w in pool if w["id"] not in set(exclude)]
    
    chosen = []
    while candidates and len(chosen) < count:
        weights = [word_weight(w["id"], mastery) for w in candidates]
        word = rng.choices(candidates, weights=weights, k=1)[0]
        chosen.append(word)
        candidates.remove(word)
        rotation["used_ids"].add(word["id"])
    
    return chosen


def short_meaning(word, limit=70):
    meaning = (word.get("meaning_vi") or "").strip()
    return meaning if len(meaning) <= limit else meaning[:limit - 1].rstrip() + "…"


def _strip_tones(text):
    text = text.lower().replace("ü", "u").replace("v", "u")
    decomposed = unicodedata.normalize("NFD", text)
    base = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z]", "", base)


def check_pinyin(answer, word):
    """Chấp nhận pinyin có dấu, số thanh hoặc không dấu; đối chiếu không dấu."""
    given = _strip_tones(answer or "")
    return bool(given) and given == _strip_tones(word.get("pinyin") or "")


def meaning_options(word, pool, count=4, rng=random):
    """Đáp án nghĩa tiếng Việt: 1 đúng + các nghĩa khác từ kho đã học."""
    correct = short_meaning(word)
    others = [w for w in pool if w["id"] != word["id"] and short_meaning(w) and short_meaning(w) != correct]
    rng.shuffle(others)
    options = [{"label": correct, "ok": True}]
    seen = {correct}
    for other in others:
        label = short_meaning(other)
        if label not in seen:
            seen.add(label)
            options.append({"label": label, "ok": False})
        if len(options) >= count:
            break
    rng.shuffle(options)
    return options


def hanzi_options(word, pool, count=4, rng=random):
    others = [w for w in pool if w["id"] != word["id"] and w["hanzi"] != word["hanzi"]]
    rng.shuffle(others)
    options = [{"label": word["hanzi"], "ok": True, "sub": word.get("pinyin") or ""}]
    seen = {word["hanzi"]}
    for other in others:
        if other["hanzi"] not in seen:
            seen.add(other["hanzi"])
            options.append({"label": other["hanzi"], "ok": False, "sub": other.get("pinyin") or ""})
        if len(options) >= count:
            break
    rng.shuffle(options)
    return options


def has_cloze(word):
    return bool(word.get("example_cloze")) and "_" in word["example_cloze"] and bool(word.get("example_zh"))


def available_types(word, pool, allow_cloze):
    types = ["h2m", "m2h"]
    if get_config()["has_pinyin"]:
        types.append("pinyin")
    if word.get("hanzi"):
        types.append("audio")
    if allow_cloze and has_cloze(word):
        types.append("cloze")
    return types


def make_question(word, pool, qtype=None, allow_cloze=False, rng=random):
    """Câu hỏi ôn: dict gồm type, word, prompt, options (trắc nghiệm) hoặc None (nhập pinyin)."""
    if qtype is None:
        qtype = rng.choice(available_types(word, pool, allow_cloze))
    q = {"type": qtype, "word": word, "options": None, "hint": ""}
    if qtype == "h2m":
        q["prompt"] = word["hanzi"]
        q["hint"] = "Chọn nghĩa đúng của chữ này"
        q["options"] = meaning_options(word, pool, rng=rng)
    elif qtype == "m2h":
        q["prompt"] = short_meaning(word)
        q["hint"] = "Chọn chữ Hán đúng với nghĩa này"
        q["options"] = hanzi_options(word, pool, rng=rng)
    elif qtype == "audio":
        q["prompt"] = "🔊"
        q["hint"] = "Nghe âm thanh, chọn chữ Hán đúng"
        q["options"] = hanzi_options(word, pool, rng=rng)
        q["audio"] = word["hanzi"]
    elif qtype == "pinyin":
        q["prompt"] = word["hanzi"]
        q["hint"] = "Gõ pinyin của chữ này (không cần dấu thanh)"
    else:
        q["prompt"] = word["example_cloze"]
        q["hint"] = "Điền chữ còn thiếu vào câu"
        q["options"] = hanzi_options(word, pool, rng=rng)
    return q


def evaluate(question, choice):
    """choice: chỉ số đáp án (trắc nghiệm) hoặc chuỗi pinyin."""
    if question["options"] is None:
        return check_pinyin(choice, question["word"])
    return bool(question["options"][choice]["ok"])


def correct_label(question):
    word = question["word"]
    if question["options"] is None:
        return word.get("pinyin") or ""
    return next(o["label"] for o in question["options"] if o["ok"])


def tokenize_sentence(sentence, vocab_hanzi):
    """Tách câu thành cụm, bỏ dấu câu: tiếng Trung khớp dài nhất theo từ điển, tiếng Anh tách theo từ."""
    if not get_config()["has_pinyin"]:
        return [t for t in (w.strip(PUNCT) for w in sentence.split()) if t]
    text = "".join(ch for ch in sentence if ch not in PUNCT)
    tokens, i = [], 0
    while i < len(text):
        for word in vocab_hanzi:
            if len(word) > 1 and text.startswith(word, i):
                tokens.append(word)
                i += len(word)
                break
        else:
            tokens.append(text[i])
            i += 1
    return tokens
