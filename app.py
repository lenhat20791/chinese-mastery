import base64
import datetime
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from admin_panel import render_admin_panel
from auth import logout, require_login
from database import (
    load_user_progress,
    update_user_energy,
    advance_user_day,
    load_day_words,
    record_feedback,
    exorcise_inner_demon,
    promote_user_realm,
    record_exam_result,
    get_cultivation_stats,
    get_all_demons_detailed,
    get_recent_exam_history,
    set_bottleneck_state,
    get_tribulation_cost,
    get_hanzi_options,
    get_recent_words_for_exam,
    get_vocab_by_ids,
    active_course,
    change_profile_level,
    change_profile_occupation,
    create_profile,
    list_profiles,
    load_session_snapshot,
    save_session_snapshot,
)
from exam_engine import generate_tribulation_exam
from extra_tabs import render_notebook, render_pronunciation, render_pronunciation_en, render_radicals
from cultivation_tab import render_cultivation
from guide_tab import render_guide
from game_core import realm_info, stat_bonuses
import game_config as game_cfg
from database import _demon_rows
from game_questions import learned_day_for as game_learned_day, load_pool as load_game_pool
from userdb import get_meta, set_meta
from course_config import COURSES, get_config

# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Thực Chiến - Phản Xạ Nhanh",
    page_icon="logo_cropped.png",
    layout="wide"
)

LOGO_B64 = base64.b64encode((Path(__file__).parent / "logo_cropped.png").read_bytes()).decode()

# --- GIAO DIỆN: CSS nằm ở style.css ---
with open(Path(__file__).parent / "style.css", encoding="utf-8") as _css:
    st.markdown(f"<style>{_css.read()}</style>", unsafe_allow_html=True)

# --- ĐĂNG NHẬP: chưa đăng nhập thì dừng tại đây ---
require_login()

# --- KHÓA HỌC: chọn khi đăng nhập & chuyển nhanh (mỗi khóa có hồ sơ tiến độ riêng) ---
# State KHÔNG bị xóa khi chuyển khóa (đăng nhập + tùy chọn chung)
KEEP_ON_SWITCH = ("auth_", "active_course", "profile_id", "speech_rate", "_profiles")
EN_LEVELS = {"A2 (dưới B1)": "A2", "B1": "B1", "B2": "B2"}
EN_OCCUPATIONS = {"Công sở": "OFFICE", "Giáo viên THCS": "TEACHER"}
COURSE_BLURB = {
    "zh": "Học phản xạ HSK với phong cách Tu Tiên Động Phủ.",
    "en": "Giao tiếp công sở & sư phạm THCS (khung CEFR).",
}


def _course_label(course):
    cfg = COURSES[course]
    return f"{cfg['flag']} {cfg['title'].split()[-1]}"


def _user_profiles(force=False):
    if force or "_profiles" not in st.session_state:
        st.session_state["_profiles"] = list_profiles(st.session_state.auth_user_id)
    return st.session_state["_profiles"]


def enter_course(course, profile_id, force=False):
    """Vào một khóa học: bỏ toàn bộ state gắn với khóa cũ để khởi tạo lại từ hồ sơ mới.

    Vị trí buổi học của khóa cũ đã được lưu ở cuối lượt chạy trước (`session_snapshot`);
    `restore_session` sẽ nạp vị trí của khóa mới ở lượt chạy kế tiếp.
    """
    s = st.session_state
    if not force and s.get("active_course") == course and s.get("profile_id") == profile_id:
        s.pop("choose_course", None)
        return
    for key in list(s.keys()):
        if not key.startswith(KEEP_ON_SWITCH):
            del s[key]
    s["active_course"] = course
    s["profile_id"] = profile_id
    set_meta(f"last_course_{s.auth_user_id}", course)


def _pick_course(course, level_key=None, occupation_key=None):
    level = EN_LEVELS.get(st.session_state.get(level_key)) if level_key else None
    occupation = EN_OCCUPATIONS.get(st.session_state.get(occupation_key)) if occupation_key else None
    profile_id = create_profile(st.session_state.auth_user_id, course, level, occupation)
    _user_profiles(force=True)
    enter_course(course, profile_id)


def _on_change_level():
    profile = next(p for p in _user_profiles() if p["course"] == st.session_state.active_course)
    new_level = EN_LEVELS[st.session_state.level_change_select]
    if new_level == profile["level"]:
        return
    change_profile_level(profile["id"], new_level)
    _user_profiles(force=True)
    enter_course(profile["course"], profile["id"], force=True)
    st.session_state["_level_changed"] = new_level


def render_level_changer():
    """Đổi trình độ CEFR của khóa tiếng Anh (kho từ và ngày học được tính lại)."""
    profile = next((p for p in _user_profiles() if p["course"] == st.session_state.active_course), None)
    if not profile or not COURSES[profile["course"]]["levels"]:
        return
    if st.session_state.pop("_level_changed", None):
        st.success("Đã đổi trình độ và cập nhật lại từ vựng.")
    current = profile["level"] or "B1"
    labels = list(EN_LEVELS)
    with st.popover(f"🎯 Trình độ: {current} — đổi", use_container_width=True):
        st.caption("Đổi trình độ sẽ lọc lại kho từ (bỏ từ dễ hơn trình độ mới) và đưa bạn tới từ đầu tiên "
                   "chưa học. Tiến độ và Linh Thạch được giữ nguyên.")
        st.selectbox("Trình độ hiện tại", labels, index=list(EN_LEVELS.values()).index(current),
                     key="level_change_select")
        st.button("✅ Áp dụng trình độ mới", key="level_change_apply", use_container_width=True,
                  on_click=_on_change_level)


def _on_change_occupation():
    profile = next(p for p in _user_profiles() if p["course"] == st.session_state.active_course)
    new_occupation = EN_OCCUPATIONS[st.session_state.occupation_select]
    if new_occupation == profile["occupation"]:
        return
    change_profile_occupation(profile["id"], new_occupation)
    _user_profiles(force=True)
    enter_course(profile["course"], profile["id"], force=True)
    st.session_state["course_occupation"] = new_occupation
    st.session_state["_occupation_changed"] = new_occupation


def render_occupation_changer():
    profile = next((p for p in _user_profiles() if p["course"] == st.session_state.active_course), None)
    if not profile or profile["course"] != "en":
        return
    if st.session_state.pop("_occupation_changed", None):
        st.success("Đã đổi nghề nghiệp và cập nhật lại lộ trình từ vựng.")
    current = profile["occupation"] or "OFFICE"
    labels = list(EN_OCCUPATIONS)
    with st.popover(f"💼 Nghề nghiệp: {next(k for k, v in EN_OCCUPATIONS.items() if v == current)}",
                    use_container_width=True):
        st.caption("Lộ trình gồm từ vựng theo nghề nghiệp và từ giao tiếp chung. Tiến độ từ đã thuộc được giữ lại.")
        st.selectbox("Nghề nghiệp học tiếng Anh", labels,
                     index=list(EN_OCCUPATIONS.values()).index(current),
                     key="occupation_select", on_change=_on_change_occupation)


def _open_course_picker():
    st.session_state["choose_course"] = True


def _close_course_picker():
    st.session_state.pop("choose_course", None)


def _on_switch_radio():
    label = st.session_state.course_switcher_radio
    course = next((c for c in COURSES if _course_label(c) == label), None)
    profile = next((p for p in _user_profiles() if p["course"] == course), None)
    if profile:
        enter_course(course, profile["id"])


def render_course_picker(profiles):
    """Màn hình chọn khóa học: hiện sau khi đăng nhập, và khi user bấm "Thêm khóa học"."""
    have = {p["course"]: p for p in profiles}
    st.title("🎓 Chọn khóa học")
    st.write("Bạn muốn tu luyện khóa nào hôm nay? Mỗi khóa có tiến độ, Linh Thạch và kho đồ riêng.")
    cols = st.columns(len(COURSES))
    for col, (cid, cfg) in zip(cols, COURSES.items()):
        with col, st.container(border=True):
            st.markdown(f"## {cfg['flag']} {cfg['title']}")
            st.caption(COURSE_BLURB[cid])
            if cid in have:
                profile = have[cid]
                if profile["level"]:
                    st.write(f"Trình độ đăng ký: **{profile['level']}**")
                if profile["course"] == "en" and profile["occupation"]:
                    occupation_label = next((k for k, v in EN_OCCUPATIONS.items() if v == profile["occupation"]),
                                            profile["occupation"])
                    st.write(f"Nghề nghiệp: **{occupation_label}**")
                st.button("▶️ Tiếp tục học", key=f"pick_{cid}", type="primary", use_container_width=True,
                          on_click=_pick_course, args=(cid,))
            else:
                level_key = None
                occupation_key = None
                if cfg["levels"]:
                    level_key = f"pick_level_{cid}"
                    st.radio("Trình độ hiện tại của bạn", list(EN_LEVELS), key=level_key)
                    occupation_key = f"pick_occupation_{cid}"
                    st.radio("Nghề nghiệp của bạn", list(EN_OCCUPATIONS), key=occupation_key)
                st.button("🚀 Bắt đầu khóa này", key=f"pick_{cid}", type="primary", use_container_width=True,
                          on_click=_pick_course, args=(cid, level_key, occupation_key))
    if st.session_state.get("active_course") in have:
        st.button("← Quay lại khóa đang học", key="pick_cancel", on_click=_close_course_picker)


def render_course_switcher():
    """Chuyển nhanh khóa học ở đầu sidebar (không cần đăng xuất)."""
    profiles = _user_profiles()
    if len(profiles) < len(COURSES):
        st.button("➕ Thêm khóa học", key="course_add", use_container_width=True, on_click=_open_course_picker)
        if len(profiles) < 2:
            return
    st.markdown("**📚 Khóa học**")
    options = [_course_label(p["course"]) for p in profiles]
    current = _course_label(st.session_state.active_course)
    st.radio("Chọn khóa học", options, index=options.index(current) if current in options else 0,
             horizontal=True, label_visibility="collapsed", key="course_switcher_radio",
             on_change=_on_switch_radio)


_auth_uid = st.session_state.auth_user_id
_profiles = _user_profiles()
_by_course = {p["course"]: p for p in _profiles}
if not _profiles or st.session_state.get("choose_course"):
    render_course_picker(_profiles)
    st.stop()
if st.session_state.get("active_course") not in _by_course:
    # Phiên khôi phục qua token (F5): vào thẳng khóa dùng lần cuối
    _last = get_meta(f"last_course_{_auth_uid}")
    _course = _last if _last in _by_course else _profiles[0]["course"]
    st.session_state["active_course"] = _course
st.session_state["profile_id"] = _by_course[st.session_state["active_course"]]["id"]
st.session_state["course_level"] = _by_course[st.session_state["active_course"]]["level"]
st.session_state["course_occupation"] = _by_course[st.session_state["active_course"]]["occupation"]
cfg_now = get_config()
hero_title = cfg_now["hero_title"]
if st.session_state.active_course == "en":
    occupation_label = next(k for k, v in EN_OCCUPATIONS.items()
                            if v == st.session_state["course_occupation"])
    hero_title = f"Thực Chiến Tiếng Anh {occupation_label}"
if not cfg_now["has_pinyin"]:
    # Chữ Latin không cần giãn cách rộng như chữ Hán
    st.markdown("""<style>
    .hanzi-display{letter-spacing:.02em !important; font-family:'Noto Serif SC',Georgia,serif !important;}
    [class*="st-key-quiz_opt_"] button p,[class*="st-key-review_opt_"] button p,
    [class*="st-key-bq_opt_"] button p,[class*="st-key-lk_opt_"] button p{letter-spacing:0 !important;}
    .hz{letter-spacing:.02em !important;}
    </style>""", unsafe_allow_html=True)

# --- KHỞI TẠO SESSION STATE ---

# Trạng thái mặc định; factory để tránh dùng chung list giữa các lần reset
SESSION_DEFAULTS = {
    "user": load_user_progress,
    "phase": lambda: "FLASHCARD",
    "failed_today": list,        # Sổ đen các từ sai trong ngày
    "review_queue": list,        # Hàng đợi ôn tập Chặng 4
    "current_review_options": list,
    "exam_questions": list,
    "exam_idx": lambda: 0,
    "exam_score": lambda: 0,
    "exam_completed": lambda: False,
    "exam_type": lambda: "MINI_3D",  # "MINI_3D" | "MAJOR_10D" | "LÔI KIẾP"
    "exam_extra": lambda: 0.0,
    "exam_wrong": lambda: 0,
    "exam_tm_t": lambda: 0.0,
    "exam_dao_tam": lambda: 0.0,
    "exam_last_hit": lambda: "",
    "card_idx": lambda: 0,
    "shadowing_idx": lambda: 0,
    "shadowing_revealed": lambda: False,
    "cloze_idx": lambda: 0,
    "cloze_status": lambda: None,    # None, "CORRECT", "INCORRECT"
    "session_start": datetime.datetime.now,
    "sub_phase": lambda: "flashcard",  # 'flashcard' (Hấp thụ) | 'quiz' (Luyện hóa)
    "current_options": list,
}
for _key, _factory in SESSION_DEFAULTS.items():
    if _key not in st.session_state:
        st.session_state[_key] = _factory()


def start_exam(is_major, exam_type):
    """Sinh đề Lôi Kiếp, đặt lại trạng thái thi và chuyển sang màn hình thi."""
    st.session_state.exam_questions = generate_tribulation_exam(
        st.session_state.user["current_day"], is_major_breakthrough=is_major
    )
    st.session_state.exam_idx = 0
    st.session_state.exam_score = 0
    st.session_state.exam_completed = False
    st.session_state.exam_result_saved = False
    st.session_state.exam_type = exam_type
    st.session_state.exam_major = is_major
    # Tâm Ma Kiếp: tâm ma càng nhiều lôi kiếp càng mạnh, Đạo tâm giảm bớt sát thương
    demons = len(_demon_rows())
    st.session_state.exam_tm_t = demons / (demons + game_cfg.TAM_MA_K)
    st.session_state.exam_dao_tam = stat_bonuses(streak=st.session_state.user.get("consecutive_streak", 0))["dao_tam"]
    st.session_state.exam_extra = 0.0
    st.session_state.exam_wrong = 0
    st.session_state.exam_last_hit = ""
    st.session_state.phase = "loi_kiep"


def go_next_day():
    """Sang ngày mới: lưu ngày vào DB và đặt lại toàn bộ tiến độ trong ngày."""
    advance_user_day()
    st.session_state.user["current_day"] += 1
    st.session_state.card_idx = 0
    st.session_state.shadowing_idx = 0
    st.session_state.cloze_idx = 0
    st.session_state.sub_phase = "flashcard"
    st.session_state.shadowing_revealed = False
    st.session_state.cloze_status = None
    st.session_state.failed_today = []
    st.session_state.review_queue = []
    st.session_state.current_review_options = []
    st.session_state.session_start = datetime.datetime.now()

def session_snapshot():
    """Vị trí buổi học hiện tại, lưu lên DB để F5 hoặc đổi thiết bị không mất tiến trình."""
    s = st.session_state
    phase = s.phase
    if phase == "loi_kiep" and s.exam_completed:
        phase = "FLASHCARD"  # kết quả thi đã được ghi (sang ngày mới hoặc Bình Cảnh)
    return {
        "day": s.user["current_day"],
        "phase": phase,
        "card_idx": s.card_idx,
        "shadowing_idx": s.shadowing_idx,
        "cloze_idx": s.cloze_idx,
        "sub_phase": s.sub_phase,
        "failed_today": [w["id"] for w in s.failed_today],
        "review_queue": [w["id"] for w in s.review_queue],
        "exam_type": s.exam_type,
        "exam_major": s.get("exam_major", False),
    }


def restore_session():
    """Nạp lại vị trí buổi học đã lưu (nếu còn đúng ngày). Bài thi dở dang sẽ được làm lại từ đầu."""
    s = st.session_state
    snap = load_session_snapshot()
    if not snap or snap.get("day") != s.user["current_day"]:
        s._saved_snap = None
        return
    s.card_idx = snap.get("card_idx", 0)
    s.shadowing_idx = snap.get("shadowing_idx", 0)
    s.cloze_idx = snap.get("cloze_idx", 0)
    s.sub_phase = snap.get("sub_phase", "flashcard")
    s.failed_today = get_vocab_by_ids(snap.get("failed_today", []))
    s.review_queue = get_vocab_by_ids(snap.get("review_queue", []))
    phase = snap.get("phase", "FLASHCARD")
    if phase == "loi_kiep":
        start_exam(snap.get("exam_major", False), snap.get("exam_type", "MINI_3D"))
    else:
        s.phase = phase
    if s.phase == "REVIEW" and s.review_queue:
        s.current_review_options = get_hanzi_options(s.review_queue[0])
    if s.sub_phase == "quiz":
        words = load_day_words(s.user["current_day"])
        if s.card_idx < len(words):
            s.current_options = get_hanzi_options(words[s.card_idx])
        else:
            s.sub_phase = "flashcard"
    s._saved_snap = session_snapshot()


if not st.session_state.get("_restored"):
    restore_session()
    st.session_state._restored = True


def audio_buttons(key_prefix):
    """Hai nút phát âm; JS ở cuối file bắt click theo nội dung nút."""
    col_word, col_ex = st.columns(2)
    with col_word:
        st.button("🔊 Nghe Từ Vựng", key=f"btn_{key_prefix}_word", use_container_width=True)
    with col_ex:
        st.button("🔊 Nghe Câu Ví Dụ", key=f"btn_{key_prefix}_ex", use_container_width=True)


today_words = load_day_words(st.session_state.user["current_day"])
total_words = len(today_words)

# Biến phục vụ phát âm Web Speech (JS ở cuối file)
speak_text = ""
current_hanzi = ""
current_example = ""

PHASE_ORDER = ["FLASHCARD", "SHADOWING", "CLOZE"]
STAGES = [
    ("Flashcard Lật Thẻ", "FLASHCARD"),
    ("Luyện Đọc Cả Câu (Shadowing)", "SHADOWING"),
    ("Gõ Bàn Phím Điền Khuyết", "CLOZE"),
]


def show_priority_group(word):
    group = word.get("priority_group")
    label = get_config()["priority_labels"].get(group)
    if label:
        st.caption(f"Nhóm ưu tiên {group}: {label}")


def stepper_html(phase):
    """Danh sách 3 chặng với trạng thái xong / đang học / chưa tới."""
    items = []
    for n, (label, key) in enumerate(STAGES, start=1):
        if phase == key:
            cls, mark = "active", str(n)
        elif phase == "COMPLETED" or (phase in PHASE_ORDER and PHASE_ORDER.index(key) < PHASE_ORDER.index(phase)):
            cls, mark = "done", "✓"
        else:
            cls, mark = "", str(n)
        items.append(f"<li class='{cls}'><span class='dot'>{mark}</span>{label}</li>")
    return "<ul class='stepper'>" + "".join(items) + "</ul>"


# --- SIDEBAR: CẢNH GIỚI & TU TIÊN ---
with st.sidebar:
    render_course_switcher()
    render_level_changer()
    render_occupation_changer()
    user = st.session_state.user
    elapsed_minutes = max(1, int((datetime.datetime.now() - st.session_state.session_start).total_seconds() / 60))
    total_energy = user["spiritual_energy"] + elapsed_minutes
    cost = get_tribulation_cost(is_major_breakthrough=False)
    energy_pct = min(100, int(total_energy / cost * 100))
    sidebar_words = len(load_game_pool(game_learned_day(user, st.session_state.phase)))
    sidebar_realm = realm_info(sidebar_words)
    day_pct = int(sidebar_realm["progress"] * 100)
    next_need = sidebar_realm["next_need"]
    words_label = f"{sidebar_words} / {next_need}" if next_need else f"{sidebar_words}"

    st.markdown(
        f"""
        <div class='hero-card'>
            <div class='realm-badge'>⚡ {sidebar_realm['name']}</div>
            <div class='stat-row'><span>✨ Linh Lực</span><b>{total_energy}</b></div>
            <div class='bar gold'><span style='width:{energy_pct}%'></span></div>
            <div class='stat-row'><span>📖 Căn cơ (từ đã học)</span><b>{words_label}</b></div>
            <div class='bar'><span style='width:{day_pct}%'></span></div>
            <div class='stat-row'><span>📅 Ngày tu luyện</span><b>{user['current_day']}</b></div>
            <div class='stat-row'><span>⏱️ Hôm nay</span><b>+{elapsed_minutes} phút</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("""<style>
    .st-key-guide_open button{background:linear-gradient(135deg,#ff9800,#e53935) !important;color:#fff !important;
    border:2px solid #ffd54f !important;font-weight:700;box-shadow:0 0 10px rgba(255,152,0,.7);}
    .st-key-guide_open button p{color:#fff !important;}
    </style>""", unsafe_allow_html=True)
    st.button("📖 Hướng Dẫn", key="guide_open", use_container_width=True,
              on_click=lambda: st.session_state.update(show_guide=True))

    st.markdown("**Lộ trình buổi học**")
    st.markdown(stepper_html(st.session_state.phase), unsafe_allow_html=True)

    st.divider()
    st.session_state.speech_rate = st.selectbox(
        "🎧 Tốc độ phát âm",
        options=[1.0, 0.85, 0.75, 0.6],
        index=0,
        format_func=lambda x: f"Tốc độ {x}x",
    )
    st.divider()
    st.caption(f"👤 Đang đăng nhập: **{st.session_state.auth_name}**")
    if st.button("🚪 Đăng xuất", use_container_width=True):
        logout()
        st.rerun()

# --- BANNER & HỆ THỐNG TAB ---
st.markdown(
    f"""
    <div class='hero'>
        <img src='data:image/png;base64,{LOGO_B64}' alt='HSK'>
        <div>
            <div class='hero-title'>{hero_title}</div>
            <div class='hero-sub'>Phản xạ nhanh · Nhớ lâu · Tu luyện mỗi ngày</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.get("show_guide"):
    render_guide()
    st.stop()

TAB_LABELS = ["⚔️ Tu Luyện Hàng Ngày", "🏯 Động Phủ", "📊 Tâm Ma Bảng & Thống Kê", "📒 Sổ Tay",
              "🗣️ Tập Phát Âm"]
if cfg_now["has_radicals"]:
    TAB_LABELS.append("🧩 Bộ Thủ")
admin_index = len(TAB_LABELS)
if st.session_state.auth_is_admin:
    TAB_LABELS.append("👑 Quản Lý")
tabs = st.tabs(TAB_LABELS)
tab_study, tab_game, tab_stats, tab_notebook, tab_pron = tabs[:5]
tab_radicals = tabs[5] if cfg_now["has_radicals"] else None

if st.session_state.auth_is_admin:
    with tabs[admin_index]:
        render_admin_panel()

with tab_game:
    render_cultivation(st.session_state.user, game_learned_day(st.session_state.user, st.session_state.phase))

with tab_notebook:
    render_notebook(st.session_state.user["current_day"], label_word=cfg_now["label_word"])
with tab_pron:
    (render_pronunciation if cfg_now["pronunciation_tab"] == "render_pronunciation" else render_pronunciation_en)()
if tab_radicals is not None:
    with tab_radicals:
        render_radicals()

# =========================================================================
# TAB 1: TU LUYỆN HÀNG NGÀY
# =========================================================================
with tab_study:
    st.caption(f"Lộ trình Ngày {st.session_state.user['current_day']}: Làm chủ {total_words} từ vựng mục tiêu")
    # --- CƠ CHẾ KHÓA CẤP (BÌNH CẢNH) ---
    user = st.session_state.user
    
    # Bỏ qua rào chắn nếu đang cố tình vào màn hình Bế quan hoặc Lôi kiếp
    if user.get("is_bottleneck") and st.session_state.phase not in ["be_quan", "loi_kiep"]:
        loi_kiep_cost = get_tribulation_cost(is_major_breakthrough=False)
        st.error("🚨 **BẠN ĐANG LÂM VÀO BÌNH CẢNH!** Tiến trình học từ mới bị phong ấn.")
        st.write(f"💧 **Linh lực hiện tại:** {user['spiritual_energy']} / {loi_kiep_cost}")
        st.progress(min(user['spiritual_energy'] / loi_kiep_cost, 1.0))
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🧘 Bế Quan Tu Luyện (Cày Linh Lực)", use_container_width=True):
                st.session_state.phase = 'be_quan'
                st.rerun()
        with col2:
            if user['spiritual_energy'] >= loi_kiep_cost:
                if st.button("⚡ Kích Hoạt Lôi Kiếp", type="primary", use_container_width=True):
                    update_user_energy(-loi_kiep_cost) # Trừ phí
                    st.session_state.user['spiritual_energy'] -= loi_kiep_cost # Cập nhật tạm UI
                    start_exam(False, "LÔI KIẾP")
                    st.rerun()
            else:
                st.button("⚡ Lôi Kiếp (Không đủ Linh Lực)", disabled=True, use_container_width=True)
        
    # =========================================================================
    # CHẶNG 1: FLASHCARD (HẤP THỤ & LUYỆN HÓA)
    # =========================================================================
    elif st.session_state.phase == "FLASHCARD":
        st.subheader("📚 Chặng 1: Nạp Từ Vựng Phản Xạ & Luyện Hóa")
        if st.session_state.card_idx < total_words:
            word = today_words[st.session_state.card_idx]
            st.progress((st.session_state.card_idx) / total_words)
            st.caption(f"Tiến độ Chặng 1: Từ {st.session_state.card_idx + 1} / {total_words}")
            show_priority_group(word)
            current_hanzi = word.get('hanzi', '')
            current_example = word.get('example_zh', '')
            if st.session_state.sub_phase == 'flashcard':
                # --- PHA HẤP THỤ ---
                speak_text = word['hanzi']
                pinyin_html = f"<div class='pinyin-display'>{word['pinyin']}</div>" if word["pinyin"] else ""
                hanviet_html = (f"<div class='hanviet-badge'>Âm Hán Việt: {word['hanviet']}</div>"
                                if cfg_now["has_hanviet"] else "")
                example_pinyin_html = (f"<div class='example-pinyin'>{word['example_pinyin']}</div>"
                                       if cfg_now["has_pinyin"] else "")
                st.markdown(
                    "<div class='vocab-card'>"
                    f"<div class='hanzi-display'>{word['hanzi']}</div>"
                    f"{pinyin_html}"
                    f"{hanviet_html}"
                    f"<div class='meaning-display'>{word['meaning_vi']}</div>"
                    "<div class='example-box'>"
                    f"<div class='example-zh'>📌 {word['example_zh']}</div>"
                    f"{example_pinyin_html}"
                    f"<div class='example-vi'>{word['example_vi']}</div>"
                    "</div></div>",
                    unsafe_allow_html=True,
                )
                chiet_tu_data = word.get('chiet_tu') if cfg_now["has_radicals"] else None
                if chiet_tu_data:
                    try:
                        ct_dict = json.loads(chiet_tu_data) if isinstance(chiet_tu_data, str) else chiet_tu_data
                        with st.expander("💡 Mẹo nhớ Hán tự (Bộ thủ & Chiết tự)"):
                            for comp in ct_dict.get('components', []):
                                st.markdown(f"🔹 **{comp.get('radical', '')}** ({comp.get('name', '')}): {comp.get('meaning', '')}")
                            st.info(f"📖 **Gợi nhớ:** {ct_dict.get('story', '')}")
                    except (ValueError, AttributeError):
                        st.caption("Dữ liệu chiết tự đang được cập nhật...")
                audio_buttons("flash")
                st.write("")
                if st.button("👁️ Đã Nhớ -> Kiểm Tra Thực Chiến", use_container_width=True, type="primary"):
                    st.session_state.current_options = get_hanzi_options(word)
                    st.session_state.sub_phase = 'quiz'
                    st.rerun()

            elif st.session_state.sub_phase == 'quiz':
                # --- PHA LUYỆN HÓA ---
                

                st.warning(f"⚔️ **THỰC CHIẾN:** Hãy chọn {cfg_now['label_word']} đúng với nghĩa dưới đây!")
                st.markdown(f"<div class='quiz-prompt'>{word['meaning_vi']}</div>", unsafe_allow_html=True)
                
                cols = st.columns(2)
                for i, opt in enumerate(st.session_state.current_options):
                    with cols[i % 2]:
                        # Nút bấm nay chỉ còn chữ Hán, CSS phía trên sẽ tự động phóng to nó
                        if st.button(opt['hanzi'], key=f"quiz_opt_{i}", use_container_width=True):
                            if opt['id'] == word['id']:
                                update_user_energy(2)
                                st.session_state.user['spiritual_energy'] += 2
                                st.toast("✅ Chính xác! +2 Linh Lực", icon="💧")
                                st.session_state.card_idx += 1
                                st.session_state.sub_phase = 'flashcard'
                            else:
                                record_feedback(word['id'], 1)
                                if word not in st.session_state.failed_today:
                                    st.session_state.failed_today.append(word)
                                st.error("❌ Sai! Tâm Ma trỗi dậy. Bắt đầu học lại từ này!")
                                st.session_state.card_idx += 1
                                st.session_state.sub_phase = 'flashcard'
                                speak_text = opt['hanzi']
                            st.rerun()
        else:
            st.session_state.phase = "SHADOWING"
            st.rerun() 

    # =========================================================================
    # CHẶNG 2: LUYỆN ĐỌC CẢ CÂU (SHADOWING)
    # =========================================================================
    elif st.session_state.phase == "SHADOWING":
        st.subheader("🗣️ Chặng 2: Luyện Đọc Cả Câu (Shadowing)")
        if st.session_state.shadowing_idx < total_words:
            word = today_words[st.session_state.shadowing_idx]
            st.progress((st.session_state.shadowing_idx) / total_words)
            st.caption(f"Tiến độ Chặng 2: Câu {st.session_state.shadowing_idx + 1} / {total_words}")
            show_priority_group(word)
            
            current_hanzi = word.get('hanzi', '')
            current_example = word.get('example_zh', '')
            speak_text = word['example_zh']

            pinyin_class = "" if st.session_state.shadowing_revealed else "pinyin-hidden"
            sentence_pinyin_html = (f"<div class='pinyin-display {pinyin_class}'>{word['example_pinyin']}</div>"
                                    if cfg_now["has_pinyin"] else "")
            st.markdown(
                "<div class='vocab-card'>"
                f"<div class='hanzi-display' style='font-size: clamp(1.8rem, 4.5vw, 2.5rem);'>{word['example_zh']}</div>"
                f"{sentence_pinyin_html}"
                f"<div class='meaning-display' style='font-size: 1.15rem;'>{word['example_vi']}</div>"
                "</div>",
                unsafe_allow_html=True,
            )
            if cfg_now["has_pinyin"] and not st.session_state.shadowing_revealed:
                st.caption("🎧 Lắng nghe âm thanh và đọc nhại theo 1-2 lần. Bấm Space để đối soát Pinyin.")
            elif not cfg_now["has_pinyin"]:
                st.caption("🎧 Lắng nghe âm thanh và đọc nhại theo 1-2 lần, rồi sang câu kế tiếp.")
            st.write("")
            audio_buttons("sh")

            col_sh_reveal, col_sh_next = st.columns(2)
            with col_sh_reveal:
                if cfg_now["has_pinyin"] and st.button("👁️ Hiện Pinyin (Space)", key="btn_shadowing_reveal", use_container_width=True):
                    st.session_state.shadowing_revealed = True
                    st.rerun()
            with col_sh_next:
                if st.button("➡️ Câu Kế Tiếp", key="btn_shadowing_next", use_container_width=True):
                    st.session_state.shadowing_revealed = False
                    st.session_state.shadowing_idx += 1
                    st.rerun()
        else:
            st.session_state.phase = "CLOZE"
            st.rerun()

    # =========================================================================
    # CHẶNG 3: BÀI TẬP GÕ BÀN PHÍM ĐIỀN KHUYẾT (TYPING CLOZE TEST)
    # =========================================================================
    elif st.session_state.phase == "CLOZE":
        st.subheader("⌨️ Chặng 3: Phản Xạ Gõ Bàn Phím Điền Khuyết")
        if st.session_state.cloze_idx < total_words:
            word = today_words[st.session_state.cloze_idx]
            st.progress((st.session_state.cloze_idx) / total_words)
            st.caption(f"Tiến độ Chặng 3: Câu {st.session_state.cloze_idx + 1} / {total_words}")
            show_priority_group(word)
            
            current_hanzi = word.get('hanzi', '')
            current_example = word.get('example_zh', '')

            audio_buttons("cloze")

            st.markdown(f"<div class='cloze-sentence'>{word['example_cloze']}</div>", unsafe_allow_html=True)
            hanviet_hint = f" *(Âm Hán Việt: {word['hanviet']})*" if cfg_now["has_hanviet"] else ""
            st.markdown(f"💡 **Gợi ý từ cần điền:** {word['meaning_vi']}{hanviet_hint}")
            st.caption("Dịch nghĩa toàn câu: " + word['example_vi'])

            with st.form(key=f"cloze_form_{st.session_state.cloze_idx}"):
                user_input = st.text_input(
                    "Bật bộ gõ tiếng Trung, gõ Pinyin và chọn đúng chữ Hán điền vào chỗ trống:"
                    if cfg_now["has_pinyin"] else "Gõ từ tiếng Anh còn thiếu vào chỗ trống:",
                    key="input_cloze_answer"
                )
                col_submit, col_skip = st.columns([2, 1])
                with col_submit:
                    submitted = st.form_submit_button("Kiểm tra đáp án (Enter)", use_container_width=True)
                with col_skip:
                    skipped = st.form_submit_button("Bỏ qua & Xem đáp án", use_container_width=True)

            answer_note = f"**{word['hanzi']}**" + (f" ({word['pinyin']})" if word["pinyin"] else "")
            if submitted:
                cleaned_input = user_input.strip()
                is_right = (cleaned_input == word["hanzi"] if cfg_now["has_pinyin"]
                            else cleaned_input.lower() == word["hanzi"].strip().lower())
                if is_right:
                    st.success(f"🎉 Chính xác! Từ cần điền là: {answer_note}")
                    
                    # --- THÊM THƯỞNG LINH LỰC KHI GÕ ĐÚNG ---
                    if st.session_state.cloze_status != "CORRECT": # Tránh trường hợp spam nút enter cộng dồn điểm
                        update_user_energy(5)
                        st.session_state.user['spiritual_energy'] += 5
                        st.toast("Tuyệt đỉnh! +5 Linh Lực cho kỹ năng gõ phím!", icon="🔥")
                    # ----------------------------------------
                    
                    st.session_state.cloze_status = "CORRECT"
                    speak_text = word["example_zh"]
                else:
                    st.error(f"❌ Chưa chính xác. Đáp án đúng là: {answer_note}")
                    record_feedback(word["id"], 1)
                    if word not in st.session_state.failed_today:
                        st.session_state.failed_today.append(word)
                    st.session_state.cloze_status = "INCORRECT"

            if skipped:
                st.warning(f"Đáp án đúng là: {answer_note}")
                record_feedback(word["id"], 1)
                if word not in st.session_state.failed_today:
                    st.session_state.failed_today.append(word)
                st.session_state.cloze_status = "INCORRECT"

            if st.session_state.cloze_status in ["CORRECT", "INCORRECT"]:
                if st.button("➡️ Sang Câu Tiếp Theo", key="btn_next_cloze_item", use_container_width=True):
                    st.session_state.cloze_status = None
                    st.session_state.cloze_idx += 1
                    st.rerun()
        else:
            if len(st.session_state.failed_today) > 0:
                st.session_state.phase = "REVIEW"
                st.session_state.review_queue = st.session_state.failed_today.copy()
                st.session_state.current_review_options = get_hanzi_options(st.session_state.review_queue[0])
            else:
                st.session_state.phase = "COMPLETED"
            st.rerun()

    # =========================================================================
    # CHẶNG 4 (ẨN): TRẢM TÂM MA - VÒNG LẶP HÀNG ĐỢI & POPUP PHẢN HỒI
    # =========================================================================
    elif st.session_state.phase == "REVIEW":
        st.subheader("🔥 Chặng 4: Trảm Tâm Ma Cuối Ngày")
        st.warning("Bạn có từ chưa thuộc hoặc gõ sai hôm nay. Hãy chọn đúng chữ Hán để hoàn tất tu luyện!")

        @st.dialog("Kết Quả Đối Soát")
        def show_feedback_dialog(is_correct, word):
            if is_correct:
                st.success("🎉 **CHÍNH XÁC!** Bạn đã làm chủ từ này.")
                st.markdown(f"**{word['hanzi']}**" + (f" ({word['pinyin']})" if word["pinyin"] else "") + f": {word['meaning_vi']}")
            else:
                st.error("❌ **CHƯA CHÍNH XÁC!**")
                pinyin_suffix = f" ({word['pinyin']})" if word["pinyin"] else ""
                st.markdown(f"Từ vựng: <span style='font-size: 1.8rem; font-weight: bold;'>{word['hanzi']}</span>{pinyin_suffix}", unsafe_allow_html=True)
                st.markdown(f"👉 **Nghĩa đúng là:** <span style='color: #16a34a; font-weight: bold; font-size: 1.15rem;'>{word['meaning_vi']}</span>", unsafe_allow_html=True)
                st.caption("⚠️ Từ này sẽ bị đẩy lại vào hàng đợi để kiểm tra lại.")
            
            st.write("")
            if st.button("Tiếp Tục ➡️", use_container_width=True, key="btn_dialog_continue"):
                if is_correct:
                    st.session_state.review_queue.pop(0)
                else:
                    # Đẩy từ làm sai xuống cuối hàng đợi
                    st.session_state.review_queue.append(st.session_state.review_queue.pop(0))
                
                # Bốc 4 đáp án mới cho từ tiếp theo (nếu còn)
                if len(st.session_state.review_queue) > 0:
                    st.session_state.current_review_options = get_hanzi_options(st.session_state.review_queue[0])
                st.rerun()

        if len(st.session_state.review_queue) > 0:
            current_word = st.session_state.review_queue[0]
            st.caption(f"Số từ còn lại trong hàng đợi: {len(st.session_state.review_queue)}")

            st.write(f"**Chọn {cfg_now['label_word']} đúng với nghĩa dưới đây:**")
            st.markdown(f"<div class='quiz-prompt'>{current_word['meaning_vi']}</div>", unsafe_allow_html=True)


            # 2. VẼ 4 NÚT ĐÁP ÁN CHỮ HÁN
            cols = st.columns(2)
            for idx, opt in enumerate(st.session_state.current_review_options):
                with cols[idx % 2]:
                    if st.button(opt['hanzi'], key=f"review_opt_{idx}", use_container_width=True):
                        # So sánh theo ID thay vì chuỗi tiếng Việt
                        is_correct = (opt['id'] == current_word["id"])
                        show_feedback_dialog(is_correct, current_word)
        else:
            st.session_state.phase = "COMPLETED"
            st.rerun()

    # =========================================================================
    # TRẠNG THÁI 1: BẾ QUAN TU LUYỆN (CÀY LINH LỰC KHI KẸT BÌNH CẢNH)
    # =========================================================================
    elif st.session_state.phase == 'be_quan':
        st.subheader("🧘 Bế Quan Tu Luyện")
        st.caption("Cày điểm Linh Lực bằng cách ôn tập kiến thức cũ. Mỗi câu đúng +1 Linh Lực.")
        
        user = st.session_state.user
        loi_kiep_cost = get_tribulation_cost(is_major_breakthrough=False)
        
        # Thanh tiến độ Linh lực
        st.progress(min(user['spiritual_energy'] / loi_kiep_cost, 1.0))
        st.write(f"💧 **Linh lực hiện tại:** {user['spiritual_energy']} / {loi_kiep_cost}")
        
        if user['spiritual_energy'] >= loi_kiep_cost:
            st.success("✨ Đã tích đủ Linh Lực! Cửa Lôi Kiếp đã mở.")
            if st.button("⚡ Tiến vào Lôi Kiếp", type="primary", use_container_width=True):
                update_user_energy(-loi_kiep_cost)
                st.session_state.user['spiritual_energy'] -= loi_kiep_cost
                start_exam(False, "LÔI KIẾP")
                st.session_state.pop('be_quan_word', None)
                st.rerun()
        
        st.divider()
        
        # Lấy 1 từ ngẫu nhiên để test cày điểm
        if 'be_quan_word' not in st.session_state or st.session_state.be_quan_word is None:
            # Lấy ngẫu nhiên 1 từ trong lịch sử học
            words = get_recent_words_for_exam(user['current_day'], user['current_day'], 1)
            if words:
                st.session_state.be_quan_word = words[0]
                st.session_state.be_quan_options = get_hanzi_options(words[0])
        
        if st.session_state.get('be_quan_word'):
            bq_word = st.session_state.be_quan_word
            st.warning(f"⚔️ **THỰC CHIẾN:** Chọn {cfg_now['label_word']} đúng để nhận Linh Lực!")
            st.markdown(f"<div class='quiz-prompt'>{bq_word['meaning_vi']}</div>", unsafe_allow_html=True)
            
            
            cols = st.columns(2)
            for i, opt in enumerate(st.session_state.be_quan_options):
                with cols[i % 2]:
                    if st.button(opt['hanzi'], key=f"bq_opt_{i}", use_container_width=True):
                        if opt['id'] == bq_word['id']:
                            update_user_energy(1)
                            st.session_state.user['spiritual_energy'] += 1
                            st.toast("✅ Chính xác! +1 Linh Lực", icon="💧")
                            speak_text = opt['hanzi']
                        else:
                            st.error("❌ Sai rồi! Tâm trí xáo trộn, không thu được Linh Lực.")
                        # Reset để vòng lặp qua từ khác
                        st.session_state.be_quan_word = None
                        st.rerun()
            
        if st.button("🚪 Thoát bế quan (Trở ra ngoài)", use_container_width=True):
            st.session_state.phase = 'FLASHCARD'
            st.session_state.pop('be_quan_word', None)
            st.rerun()

    # =========================================================================
    # TRẠNG THÁI 2: LÔI KIẾP (THI ĐỘT PHÁ CẢNH GIỚI)
    # =========================================================================
    elif st.session_state.phase == 'loi_kiep':
        st.subheader("⚡ THIÊN KIẾP GIÁNG LÂM")
        
        if not st.session_state.exam_completed:
            total_q = len(st.session_state.exam_questions)
            curr_idx = st.session_state.exam_idx
            q = st.session_state.exam_questions[curr_idx]
            in_tam_ma = q.get("phase") == "tam_ma"
            need = int(total_q * 0.85)
            allowed = max(total_q - need, 1)
            lost = st.session_state.exam_wrong + st.session_state.exam_extra
            body_left = max(0.0, 1 - lost / allowed)

            st.progress((curr_idx) / total_q)
            if in_tam_ma:
                st.error(f"👿 TÂM MA KIẾP — Đạo lôi thứ {curr_idx + 1} / {total_q}. "
                         f"Tâm ma hiện hình, mỗi câu sai bị lôi kiếp giáng mạnh hơn "
                         f"(+{st.session_state.exam_tm_t * (1 - st.session_state.exam_dao_tam):.2f} điểm trừ).")
            else:
                st.caption(f"Đạo lôi thứ {curr_idx + 1} / {total_q} | Sinh tử kiếp")
            st.progress(body_left, text=f"🛡️ Đạo thể: {body_left * 100:.0f}% (cạn là độ kiếp thất bại)")
            if st.session_state.get("exam_last_hit"):
                st.warning(st.session_state.exam_last_hit)

            st.markdown(f"<div class='quiz-prompt'>{q['question_text']}</div>", unsafe_allow_html=True)
            
            
            cols = st.columns(2)
            for i, opt in enumerate(q["options"]):
                with cols[i % 2]:
                    if st.button(opt['hanzi'], key=f"lk_opt_{curr_idx}_{i}", use_container_width=True):
                        st.session_state.exam_last_hit = ""
                        if opt['id'] == q["correct_id"]:
                            st.session_state.exam_score += 1
                            exorcise_inner_demon(q["vocab_id"]) # Thanh tẩy tâm ma
                            speak_text = opt['hanzi']
                        else:
                            st.session_state.exam_wrong += 1
                            if in_tam_ma:
                                hit = st.session_state.exam_tm_t * (1 - st.session_state.exam_dao_tam)
                                st.session_state.exam_extra += hit
                                st.session_state.exam_last_hit = (
                                    f"⚡ Lôi kiếp giáng xuống! Tâm ma khiến đạo thể tổn thêm {hit:.2f} điểm "
                                    f"(Đạo tâm hộ thể giảm {st.session_state.exam_dao_tam * 100:.1f}%).")
                        
                        if curr_idx + 1 < total_q:
                            st.session_state.exam_idx += 1
                        else:
                            st.session_state.exam_completed = True
                        st.rerun()
        else:
            total_q = len(st.session_state.exam_questions)
            score = st.session_state.exam_score
            need = int(total_q * 0.85)  # Tỉ lệ yêu cầu: 85% mới được qua
            effective = score - st.session_state.exam_extra  # câu sai ở Tâm Ma Kiếp bị trừ thêm
            is_passed = effective >= need - 1e-9

            # Chỉ ghi nhận kết quả & thăng cấp 1 lần (màn hình này chạy lại sau mỗi lần bấm nút)
            if not st.session_state.exam_result_saved:
                record_exam_result(st.session_state.exam_type, st.session_state.user["current_day"], total_q, score, is_passed)
                set_bottleneck_state(not is_passed)
                st.session_state.user['is_bottleneck'] = not is_passed
                if is_passed:
                    st.session_state.user['current_realm'] = promote_user_realm()
                    go_next_day()
                st.session_state.exam_result_saved = True

            st.markdown(f"<h2 style='text-align:center;'>Kết quả Lôi Kiếp: {score}/{total_q}</h2>", unsafe_allow_html=True)
            if st.session_state.exam_extra > 0:
                st.caption(f"👿 Tâm Ma Kiếp trừ thêm {st.session_state.exam_extra:.2f} điểm → điểm hiệu dụng "
                           f"{effective:.2f} (cần ≥ {need}).")
            
            if is_passed:
                st.balloons()
                st.success("🎉 ĐỘT PHÁ THÀNH CÔNG! Tâm ma tan biến, tu vi tăng tiến.")
                st.info(f"📅 Bạn đã sang Ngày {st.session_state.user['current_day']}.")
                if st.button("🚀 Bắt đầu bài học ngày mới", type="primary", use_container_width=True):
                    st.session_state.phase = "FLASHCARD"
                    st.rerun()
            else:
                st.error("💥 ĐỘT PHÁ THẤT BẠI! Căn cơ chưa vững, Linh Lực tiêu tán. Trở về Bình Cảnh.")
                if st.button("🧘 Quay lại Bế Quan tu luyện", use_container_width=True):
                    st.session_state.phase = "FLASHCARD" # Trả về màn hình chính để bị chặn bởi rào chắn
                    st.rerun()

    # =========================================================================
    # KẾT THÚC BUỔI HỌC: LƯU TIẾN ĐỘ & LINH LỰC
    # =========================================================================
    elif st.session_state.phase == "COMPLETED":
        st.balloons()
        st.success("🎉 Xuất sắc! Bạn đã hoàn thành nhiệm vụ tu luyện của ngày hôm nay.")
        
        elapsed = max(1, int((datetime.datetime.now() - st.session_state.session_start).total_seconds() / 60))
        st.info(f"⚡ Bạn đã tu luyện tập trung trong **{elapsed} phút**, quy đổi thành **+{elapsed} Điểm Linh Lực**.")
        
        if True:
            curr_d = st.session_state.user["current_day"]
            
            if curr_d % 10 == 0:
                if st.button("👑 ĐỘT PHÁ: TIẾN VÀO ĐẠI THIÊN KIẾP (10 NGÀY)", use_container_width=True):
                    update_user_energy(elapsed)
                    start_exam(True, "MAJOR_10D")  # 50 câu
                    st.rerun()

            elif curr_d % 3 == 0:
                if st.button("⚡ ĐỘT PHÁ: TIẾN VÀO TIỂU THIÊN KIẾP (3 NGÀY)", use_container_width=True):
                    update_user_energy(elapsed)
                    start_exam(False, "MINI_3D")  # 20 câu
                    st.rerun()
            else:
                if st.button("🚀 Sang Bài Học Ngày Tiếp Theo", use_container_width=True):
                    update_user_energy(elapsed)
                    go_next_day()
                    st.session_state.phase = "FLASHCARD"
                    st.rerun()

# =========================================================================
# TAB 2: TÂM MA BẢNG & THỐNG KÊ CHI TIẾT
# =========================================================================
with tab_stats:
    st.subheader("📊 Quản Lý Tiến Độ & Tâm Ma")
    stats = get_cultivation_stats()
    
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    with col_m1:
        pct = round((stats["learned"] / max(stats["total_vocab"], 1)) * 100, 1)
        st.metric("Tiến độ Lộ Trình", f"{stats['learned']}/{stats['total_vocab']}", f"{pct}%")
    with col_m2:
        st.metric("✅ Đã Làm Chủ", f"{stats['mastered']} từ")
    with col_m3:
        st.metric("⚠️ Mang Máng", f"{stats['vague']} từ")
    with col_m4:
        st.metric("🔥 Tâm Ma Đang Bám", f"{stats['demons']} từ", delta_color="inverse")

    st.progress(min(stats["learned"] / max(stats["total_vocab"], 1), 1.0))
    if stats["learned"] > 0:
        st.caption("Phân bố mức độ ghi nhớ")
        st.bar_chart(
            {
                "Làm chủ": stats["mastered"],
                "Mang máng": stats["vague"],
                "Sai": stats["failed"],
                "Tâm ma": stats["demons"],
            },
            color="#8a0f8f",
            height=220,
        )        
    st.divider()
    
    st.markdown("### 📜 Danh Sách Tâm Ma Cần Trảm (Sổ Đen)")
    all_demons = get_all_demons_detailed()
    
    if len(all_demons) > 0:
        st.warning(f"Hiện đang có **{len(all_demons)} từ vựng** bị dính cờ Tâm Ma. Hãy ôn kỹ để chuẩn bị cho kỳ Khảo Thí sắp tới!")
        st.dataframe(
            all_demons,
            column_config={
                "hanzi": "Chữ Hán",
                "pinyin": "Pinyin",
                "hanviet": "Hán Việt",
                "meaning_vi": "Nghĩa Tiếng Việt",
                "study_day": "Ngày Học",
                "failed_count": "Số Lần Sai",
                "vague_count": "Số Lần Máng",
                "review_count": "Tổng Lần Ôn",
                "fail_rate_pct": st.column_config.ProgressColumn(
                    "Tỷ Lệ Sai (%)",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100
                )
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.success("✨ Tâm cảnh thanh tịnh! Hiện không có từ nào bị dính cờ Tâm Ma.")
        
    st.divider()
    
    st.markdown("### 🏆 Lịch Sử Khảo Thí Thiên Kiếp")
    exams = get_recent_exam_history()
    if len(exams) > 0:
        st.line_chart(
            {"Điểm (%)": [e["score_percent"] for e in reversed(exams)]},
            color="#b7791f",
            height=180,
        )
        for e in exams:
            e["is_passed"] = "✅ Đạt" if e["is_passed"] else "❌ Rớt"
        st.dataframe(
            exams,
            column_config={
                "exam_type": "Kỳ Thi",
                "stage_number": "Giai Đoạn",
                "total_questions": "Tổng Câu",
                "correct_answers": "Số Câu Đúng",
                "score_percent": st.column_config.NumberColumn("Điểm (%)", format="%.1f%%"),
                "is_passed": "Kết Quả",
                "taken_at": "Thời Gian"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("Chưa có lịch sử thi cử nào được ghi nhận.")

# =========================================================================
# CHẠY NGẦM: BẮT PHÍM TẮT & PHÁT ÂM QUA WEB SPEECH API (ĐẶT Ở CUỐI FILE)
# =========================================================================
js_tts_lang = cfg_now["tts_lang"]
js_handler = f"""
<script>
    const synth = window.speechSynthesis;

    function playAudio(text) {{
        if (!synth || !text) return;
        synth.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = '{js_tts_lang}';
        
        // Từ ngắn (<= 6 ký tự) đọc chậm hơn câu để nghe rõ từng âm tiết
        const uiRate = {st.session_state.get('speech_rate', 1.0)};
        utter.rate = uiRate * (text.length <= 6 ? {cfg_now['tts_rate_short_factor']} : {cfg_now['tts_rate_sentence_factor']});
        
        synth.speak(utter);
    }}

    {f"playAudio({json.dumps(speak_text)});" if speak_text else ""}

    const doc = window.parent.document;

    // Xóa listener cũ để tránh vang tiếng do Streamlit chèn nhiều iframe
    if (doc.audioClickListener) {{
        doc.removeEventListener('click', doc.audioClickListener);
    }}

    // Nhận diện nút Từ hay nút Câu theo nội dung nút
    doc.audioClickListener = function(e) {{
        if (e.target && e.target.innerText) {{
            if (e.target.innerText.includes('Nghe Từ Vựng')) {{
                playAudio({json.dumps(current_hanzi)});
            }} else if (e.target.innerText.includes('Nghe Câu Ví Dụ')) {{
                playAudio({json.dumps(current_example)});
            }}
        }}
    }};
    doc.addEventListener('click', doc.audioClickListener);

    // Phím Space: Hiện Pinyin ở Chặng 2
    doc.onkeydown = function(e) {{
        if (e.code === 'Space') {{
            const btnReveal = doc.querySelector('.st-key-btn_shadowing_reveal button');
            if (btnReveal) btnReveal.click();
        }}
    }};
</script>
"""
components.html(js_handler, height=0)

# Lưu vị trí buổi học khi có thay đổi (để F5 không mất tiến trình)
_snap = session_snapshot()
if _snap != st.session_state.get("_saved_snap"):
    save_session_snapshot(_snap)
    st.session_state._saved_snap = _snap
