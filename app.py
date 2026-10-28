import streamlit as st
import datetime
import streamlit.components.v1 as components
from database import (
    load_user_progress,
    update_user_energy,
    advance_user_day,
    load_day_words,
    record_feedback,
    get_review_options,
    exorcise_inner_demon,
    promote_user_realm,
    breakthrough_major_realm,
    record_exam_result,
    get_cultivation_stats,
    get_all_demons_detailed,
    get_recent_exam_history,
    set_bottleneck_state,
    get_tribulation_cost,
    get_hanzi_options
)
from exam_engine import generate_mini_exam, generate_major_exam, generate_tribulation_exam
from backup_manager import backup_to_drive, restore_latest_from_drive
# --- CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="Thực Chiến Tiếng Trung - Phản Xạ Nhanh",
    page_icon="⚔️",
    layout="wide"
)

# --- CSS ĐỊNH DẠNG GIAO DIỆN & CHỮ TO ---
st.markdown("""
<style>
    /* Ẩn container iframe chạy ngầm */
    div[data-testid="stCustomComponentV1"] {
        position: fixed !important;
        bottom: 0 !important;
        left: 0 !important;
        width: 0px !important;
        height: 0px !important;
        overflow: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .realm-badge {
        font-size: 1.15rem;
        font-weight: 700;
        color: #d97706;
        background: #fef3c7;
        padding: 6px 14px;
        border-radius: 8px;
        border: 1px solid #f59e0b;
        display: inline-block;
        margin-bottom: 10px;
    }

    .vocab-card {
        background-color: #ffffff;
        border-radius: 16px;
        padding: 40px 20px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
        border: 1px solid #e2e8f0;
        text-align: center;
        margin-top: 15px;
        margin-bottom: 25px;
    }

    .hanzi-display {
        font-size: 5.5rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        letter-spacing: 0.35em !important;
        line-height: 1.2 !important;
        margin-bottom: 15px !important;
        text-align: center !important;
    }

    .pinyin-display {
        font-size: 1.8rem;
        color: #2563eb;
        font-weight: 600;
        margin-bottom: 10px;
    }

    .hanviet-badge {
        background-color: #ede9fe;
        color: #6d28d9;
        font-size: 1.15rem;
        font-weight: 600;
        padding: 6px 14px;
        border-radius: 6px;
        display: inline-block;
        margin-bottom: 15px;
    }

    .meaning-display {
        font-size: 1.4rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 20px;
    }

    .example-box {
        background-color: #f8fafc;
        border-left: 4px solid #3b82f6;
        padding: 16px;
        text-align: left;
        border-radius: 6px;
        margin-top: 15px;
    }

    .example-zh {
        font-size: 1.35rem;
        color: #0f172a;
        font-weight: 600;
        margin-bottom: 6px;
    }

    .example-pinyin {
        font-size: 1.1rem;
        color: #64748b;
        margin-bottom: 6px;
    }

    .example-vi {
        font-size: 1.15rem;
        color: #334155;
    }

    .cloze-sentence {
        font-size: clamp(1.4rem, 4vw, 1.8rem);
        color: #1e293b;
        font-weight: 600;
        line-height: 1.6;
        background: #f1f5f9;
        padding: 20px;
        border-radius: 8px;
        border: 1px dashed #94a3b8;
        margin: 15px 0;
    }

    .pinyin-hidden {
        filter: blur(8px);
        user-select: none;
        transition: filter 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)
# --- KHỞI TẠO SESSION STATE ---
if "user" not in st.session_state:
    st.session_state.user = load_user_progress()

if "phase" not in st.session_state:
    st.session_state.phase = "FLASHCARD" 

if "failed_today" not in st.session_state:
    st.session_state.failed_today = []  # Danh sách ghi sổ đen các từ sai trong ngày

if "review_queue" not in st.session_state:
    st.session_state.review_queue = []  # Hàng đợi ôn tập cho Chặng 4

if "current_review_options" not in st.session_state:
    st.session_state.current_review_options = []

# Biến phục vụ Kỳ Khảo Thí (Exam State)
if "exam_questions" not in st.session_state:
    st.session_state.exam_questions = []

if "exam_idx" not in st.session_state:
    st.session_state.exam_idx = 0

if "exam_score" not in st.session_state:
    st.session_state.exam_score = 0

if "exam_completed" not in st.session_state:
    st.session_state.exam_completed = False

if "exam_type" not in st.session_state:
    st.session_state.exam_type = "MINI_3D"  # "MINI_3D" hoặc "MAJOR_10D"

if "card_idx" not in st.session_state:
    st.session_state.card_idx = 0

if "is_flipped" not in st.session_state:
    st.session_state.is_flipped = False

if "shadowing_idx" not in st.session_state:
    st.session_state.shadowing_idx = 0

if "shadowing_revealed" not in st.session_state:
    st.session_state.shadowing_revealed = False

if "cloze_idx" not in st.session_state:
    st.session_state.cloze_idx = 0

if "cloze_status" not in st.session_state:
    st.session_state.cloze_status = None  # None, "CORRECT", "INCORRECT"

if "session_start" not in st.session_state:
    st.session_state.session_start = datetime.datetime.now()

if 'sub_phase' not in st.session_state:
    st.session_state.sub_phase = 'flashcard' # Trạng thái thẻ: 'flashcard' (Hấp thụ) hoặc 'quiz' (Luyện hóa)

if 'current_options' not in st.session_state:
    st.session_state.current_options = []

if 'earned_energy_today' not in st.session_state:
    st.session_state.earned_energy_today = 0

today_words = load_day_words(st.session_state.user["current_day"])
total_words = len(today_words)

# Biến phát âm âm thanh Web Speech
speak_text = ""

# --- SIDEBAR: CẢNH GIỚI & TU TIÊN ---
with st.sidebar:
    st.title("⚡ Tu Tiên Bảng")
    st.markdown(f"<div class='realm-badge'>Cảnh giới: {st.session_state.user['current_realm']}</div>", unsafe_allow_html=True)
    
    elapsed_minutes = max(1, int((datetime.datetime.now() - st.session_state.session_start).total_seconds() / 60))
    total_energy = st.session_state.user["spiritual_energy"] + elapsed_minutes
    
    st.metric(label="✨ Tổng Linh Lực", value=f"{total_energy} Điểm", delta=f"+{elapsed_minutes} phút hôm nay")
    st.metric(label="📅 Ngày tu luyện", value=f"Ngày {st.session_state.user['current_day']} / 74")
    
    st.divider()
    # Thêm menu chọn tốc độ đọc
    st.session_state.speech_rate = st.selectbox(
        "🎧 Tốc độ phát âm:", 
        options=[1.0, 0.85, 0.75], 
        index=0,  # Đổi index thành 0 để mặc định chọn 1.0x (bình thường)
        format_func=lambda x: f"Tốc độ {x}x"
    )
    
    st.divider()
    st.markdown("**Lộ trình buổi học 3 chặng:**")
    st.markdown(f"{'👉' if st.session_state.phase == 'FLASHCARD' else '✅'} **Chặng 1:** Flashcard Lật Thẻ")
    st.markdown(f"{'👉' if st.session_state.phase == 'SHADOWING' else '✅' if st.session_state.phase in ['CLOZE', 'COMPLETED'] else '⚪'} **Chặng 2:** Luyện Đọc Cả Câu (Shadowing)")
    st.markdown(f"{'👉' if st.session_state.phase == 'CLOZE' else '✅' if st.session_state.phase == 'COMPLETED' else '⚪'} **Chặng 3:** Gõ Bàn Phím Điền Khuyết")

    st.divider()
    # ==========================================
    # 🛠️ DEVELOPER MODE - BẢNG HACK ĐỂ TEST APP
    # ==========================================
    with st.expander("🛠️ MENU HACK (DÀNH CHO DEV)"):
        if st.button("💰 Hack +100 Linh Lực", use_container_width=True):
            update_user_energy(100)
            st.session_state.user['spiritual_energy'] += 100
            st.toast("Đã buff 100 Linh Lực!", icon="💉")
            st.rerun()
            
        if st.button("⏩ Tua nhanh +1 Ngày", use_container_width=True):
            advance_user_day()
            st.session_state.user['current_day'] += 1
            st.session_state.phase = "FLASHCARD"  # Reset về học bài mới
            st.session_state.card_idx = 0
            st.toast(f"Đã sang Ngày {st.session_state.user['current_day']}!", icon="⏩")
            st.rerun()
            
        if st.button("🔒 Ép kẹt Bình Cảnh (Tẩu Hỏa)", use_container_width=True):
            set_bottleneck_state(True)
            st.session_state.user['is_bottleneck'] = True
            st.session_state.phase = "FLASHCARD" # Ép tải lại trang chính để rào chắn chặn lại
            st.toast("Đã rơi vào Bình Cảnh!", icon="🚨")
            st.rerun()
            
        if st.button("🔓 Gỡ Bình Cảnh (Clear Bug)", use_container_width=True):
            set_bottleneck_state(False)
            st.session_state.user['is_bottleneck'] = False
            st.toast("Đã gỡ rào chắn Bình Cảnh!", icon="✅")
            st.rerun()

# --- TIÊU ĐỀ CHÍNH ---
# --- TIÊU ĐỀ CHÍNH & HỆ THỐNG TAB ---
st.title("🎯 Thực Chiến Tiếng Trung Công Sở")

tab_study, tab_stats = st.tabs(["⚔️ Tu Luyện Hàng Ngày", "📊 Tâm Ma Bảng & Thống Kê"])

# =========================================================================
# TAB 1: TU LUYỆN HÀNG NGÀY
# =========================================================================
with tab_study:
    st.caption(f"Lộ trình Ngày {st.session_state.user['current_day']}: Làm chủ 4 từ vựng mục tiêu")
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
                st.session_state.phase = 'be_quan' # Màn hình này ta sẽ code sau
                st.rerun()
        with col2:
            if user['spiritual_energy'] >= loi_kiep_cost:
                if st.button("⚡ Kích Hoạt Lôi Kiếp", type="primary", use_container_width=True):
                    update_user_energy(-loi_kiep_cost) # Trừ phí
                    st.session_state.user['spiritual_energy'] -= loi_kiep_cost # Cập nhật tạm UI
                    st.session_state.exam_questions = generate_tribulation_exam(user['current_day'], False)
                    st.session_state.exam_idx = 0
                    st.session_state.exam_score = 0
                    st.session_state.exam_completed = False
                    st.session_state.exam_type = "LÔI KIẾP"
                    st.session_state.phase = "loi_kiep" # Màn hình Lôi Kiếp ta sẽ code sau
                    st.rerun()
            else:
                st.button("⚡ Lôi Kiếp (Không đủ Linh Lực)", disabled=True, use_container_width=True)
        
        st.stop() # Lệnh này chặn không cho vẽ tiếp giao diện Flashcard bên dưới
    # =========================================================================
    # CHẶNG 1: FLASHCARD (HẤP THỤ & LUYỆN HÓA)
    # =========================================================================
    if st.session_state.phase == "FLASHCARD":
        st.subheader("📚 Chặng 1: Nạp Từ Vựng Phản Xạ & Luyện Hóa")
        if st.session_state.card_idx < total_words:
            word = today_words[st.session_state.card_idx]
            st.progress((st.session_state.card_idx) / total_words)
            st.caption(f"Tiến độ Chặng 1: Từ {st.session_state.card_idx + 1} / {total_words}")

            if st.session_state.sub_phase == 'flashcard':
                # --- PHA HẤP THỤ ---
                with st.container():
                    st.markdown("<div class='vocab-card'>", unsafe_allow_html=True)
                    st.markdown(f"<div class='hanzi-display'>{word['hanzi']}</div>", unsafe_allow_html=True)
                    
                    speak_text = word['hanzi']
                    st.markdown(f"<div class='pinyin-display'>{word['pinyin']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='hanviet-badge'>Âm Hán Việt: {word['hanviet']}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div class='meaning-display'>{word['meaning_vi']}</div>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div class='example-box'>
                        <div class='example-zh'>📌 {word['example_zh']}</div>
                        <div class='example-pinyin'>{word['example_pinyin']}</div>
                        <div class='example-vi'>{word['example_vi']}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)

                if st.button("👁️ Đã Nhớ -> Kiểm Tra Thực Chiến", use_container_width=True, type="primary"):
                    st.session_state.current_options = get_hanzi_options(word)
                    st.session_state.sub_phase = 'quiz'
                    st.rerun()

            elif st.session_state.sub_phase == 'quiz':
                # --- PHA LUYỆN HÓA ---
                
                # 1. TIÊM CSS ĐỂ ĐỘ ĐỘC QUYỀN CÁC NÚT ĐÁP ÁN (To, Đậm, Giãn chữ)
                st.markdown("""
                <style>
                    /* Bắt thẳng vào testid cốt lõi của nút Streamlit */
                    div[data-testid="stButton"] button {
                        padding: 15px 0px !important; 
                        border-radius: 12px !important;
                        min-height: 70px !important; /* Ép nút cao lên */
                    }
                    
                    /* Nhắm thẳng vào tất cả thẻ chữ bên trong nút */
                    div[data-testid="stButton"] button p, 
                    div[data-testid="stButton"] button div, 
                    div[data-testid="stButton"] button span {
                        font-size: 32px !important; /* Chữ cực to */
                        font-weight: 900 !important; /* Đen đậm nét */
                        letter-spacing: 12px !important; /* Giãn cách rõ ràng */
                        color: #0f172a !important;
                    }
                </style>
                """, unsafe_allow_html=True)

                st.warning("⚔️ **THỰC CHIẾN:** Hãy chọn chữ Hán đúng với nghĩa dưới đây!")
                st.markdown(f"<h3 style='text-align: center; margin-bottom: 20px;'>{word['meaning_vi']}</h3>", unsafe_allow_html=True)
                
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
                                record_feedback(word['id'], "failed")
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

            speak_text = word['example_zh']

            with st.container():
                st.markdown("<div class='vocab-card'>", unsafe_allow_html=True)
                st.markdown(f"<div class='hanzi-display' style='font-size: clamp(1.8rem, 4.5vw, 2.5rem); margin-bottom: 15px;'>{word['example_zh']}</div>", unsafe_allow_html=True)
                
                pinyin_class = "" if st.session_state.shadowing_revealed else "pinyin-hidden"
                st.markdown(f"<div class='pinyin-display {pinyin_class}'>{word['example_pinyin']}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='meaning-display' style='color: #475569; font-size: 1.15rem;'>{word['example_vi']}</div>", unsafe_allow_html=True)
                
                if not st.session_state.shadowing_revealed:
                    st.caption("🎧 Lắng nghe âm thanh và đọc nhại theo 1-2 lần. Bấm Space để đối soát Pinyin.")
                st.markdown("</div>", unsafe_allow_html=True)

            st.write("")
            col_sh_audio, col_sh_reveal, col_sh_next = st.columns([1, 1, 1])
            with col_sh_audio:
                st.button("🔊 Nghe Lại Câu", key="btn_shadowing_audio", use_container_width=True)
            with col_sh_reveal:
                if st.button("👁️ Hiện Pinyin (Space)", key="btn_shadowing_reveal", use_container_width=True):
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

            st.markdown(f"<div class='cloze-sentence'>{word['example_cloze']}</div>", unsafe_allow_html=True)
            st.markdown(f"💡 **Gợi ý từ cần điền:** {word['meaning_vi']} *(Âm Hán Việt: {word['hanviet']})*")
            st.caption("Dịch nghĩa toàn câu: " + word['example_vi'])

            with st.form(key=f"cloze_form_{st.session_state.cloze_idx}"):
                user_input = st.text_input(
                    "Bật bộ gõ tiếng Trung, gõ Pinyin và chọn đúng chữ Hán điền vào chỗ trống:",
                    key="input_cloze_answer"
                )
                col_submit, col_skip = st.columns([2, 1])
                with col_submit:
                    submitted = st.form_submit_button("Kiểm tra đáp án (Enter)", use_container_width=True)
                with col_skip:
                    skipped = st.form_submit_button("Bỏ qua & Xem đáp án", use_container_width=True)

            if submitted:
                cleaned_input = user_input.strip()
                if cleaned_input == word["hanzi"]:
                    st.success(f"🎉 Chính xác! Từ cần điền là: **{word['hanzi']}** ({word['pinyin']})")
                    
                    # --- THÊM THƯỞNG LINH LỰC KHI GÕ ĐÚNG ---
                    if st.session_state.cloze_status != "CORRECT": # Tránh trường hợp spam nút enter cộng dồn điểm
                        update_user_energy(5)
                        st.session_state.user['spiritual_energy'] += 5
                        st.toast("Tuyệt đỉnh! +5 Linh Lực cho kỹ năng gõ phím!", icon="🔥")
                    # ----------------------------------------
                    
                    st.session_state.cloze_status = "CORRECT"
                    speak_text = word["example_zh"]
                else:
                    st.error(f"❌ Chưa chính xác. Đáp án đúng là: **{word['hanzi']}** ({word['pinyin']})")
                    record_feedback(word["id"], 1)
                    if word not in st.session_state.failed_today:
                        st.session_state.failed_today.append(word)
                    st.session_state.cloze_status = "INCORRECT"

            if skipped:
                st.warning(f"Đáp án đúng là: **{word['hanzi']}** ({word['pinyin']})")
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
                st.markdown(f"**{word['hanzi']}** ({word['pinyin']}): {word['meaning_vi']}")
            else:
                st.error("❌ **CHƯA CHÍNH XÁC!**")
                st.markdown(f"Từ vựng: <span style='font-size: 1.8rem; font-weight: bold;'>{word['hanzi']}</span> ({word['pinyin']})", unsafe_allow_html=True)
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

            st.write("**Chọn chữ Hán đúng với nghĩa dưới đây:**")
            st.markdown(f"<h3 style='text-align: center; margin-bottom: 20px;'>{current_word['meaning_vi']}</h3>", unsafe_allow_html=True)

            # 1. TIÊM CSS NÚT KHỔNG LỒ
            st.markdown("""
            <style>
                div[data-testid="stButton"] button { padding: 15px 0px !important; border-radius: 12px !important; min-height: 70px !important; }
                div[data-testid="stButton"] button p, div[data-testid="stButton"] button div, div[data-testid="stButton"] button span {
                    font-size: 32px !important; font-weight: 900 !important; letter-spacing: 12px !important; color: #0f172a !important;
                }
            </style>
            """, unsafe_allow_html=True)

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
                st.session_state.exam_questions = generate_tribulation_exam(user['current_day'], False)
                st.session_state.exam_idx = 0
                st.session_state.exam_score = 0
                st.session_state.exam_completed = False
                st.session_state.phase = 'loi_kiep'
                st.session_state.pop('be_quan_word', None)
                st.rerun()
        
        st.divider()
        
        # Lấy 1 từ ngẫu nhiên để test cày điểm
        if 'be_quan_word' not in st.session_state or st.session_state.be_quan_word is None:
            # Lấy ngẫu nhiên 1 từ trong lịch sử học
            from database import get_recent_words_for_exam
            words = get_recent_words_for_exam(user['current_day'], user['current_day'], 1)
            if words:
                st.session_state.be_quan_word = words[0]
                st.session_state.be_quan_options = get_hanzi_options(words[0])
        
        if st.session_state.get('be_quan_word'):
            bq_word = st.session_state.be_quan_word
            st.warning("⚔️ **THỰC CHIẾN:** Chọn chữ Hán đúng để nhận Linh Lực!")
            st.markdown(f"<h3 style='text-align: center; margin-bottom: 20px;'>{bq_word['meaning_vi']}</h3>", unsafe_allow_html=True)
            
            # CSS nới rộng nút
            st.markdown("""
            <style>
                div[data-testid="stButton"] button { padding: 15px 0px !important; border-radius: 12px !important; min-height: 70px !important; }
                div[data-testid="stButton"] button p, div[data-testid="stButton"] button div, div[data-testid="stButton"] button span {
                    font-size: 32px !important; font-weight: 900 !important; letter-spacing: 12px !important; color: #0f172a !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
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
            
            st.progress((curr_idx) / total_q)
            st.caption(f"Đạo lôi thứ {curr_idx + 1} / {total_q} | Sinh tử kiếp")
            
            st.markdown(f"<h3 style='text-align: center; margin: 30px 0;'>{q['question_text']}</h3>", unsafe_allow_html=True)
            
            # CSS nút to 
            st.markdown("""
            <style>
                div[data-testid="stButton"] button { padding: 15px 0px !important; border-radius: 12px !important; min-height: 70px !important; }
                div[data-testid="stButton"] button p, div[data-testid="stButton"] button div, div[data-testid="stButton"] button span {
                    font-size: 32px !important; font-weight: 900 !important; letter-spacing: 12px !important; color: #0f172a !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            cols = st.columns(2)
            for i, opt in enumerate(q["options"]):
                with cols[i % 2]:
                    if st.button(opt['hanzi'], key=f"lk_opt_{curr_idx}_{i}", use_container_width=True):
                        if opt['id'] == q["correct_id"]:
                            st.session_state.exam_score += 1
                            exorcise_inner_demon(q["vocab_id"]) # Thanh tẩy tâm ma
                            speak_text = opt['hanzi']
                        
                        if curr_idx + 1 < total_q:
                            st.session_state.exam_idx += 1
                        else:
                            st.session_state.exam_completed = True
                        st.rerun()
        else:
            total_q = len(st.session_state.exam_questions)
            score = st.session_state.exam_score
            pass_pct = 0.85 # Tỉ lệ yêu cầu: 85% mới được qua
            is_passed = (score >= int(total_q * pass_pct))
            
            st.markdown(f"<h2 style='text-align:center;'>Kết quả Lôi Kiếp: {score}/{total_q}</h2>", unsafe_allow_html=True)
            
            if is_passed:
                st.balloons()
                st.success("🎉 ĐỘT PHÁ THÀNH CÔNG! Tâm ma tan biến, tu vi tăng tiến.")
                
                # Mở khóa Bình Cảnh, thăng cấp
                set_bottleneck_state(False)
                st.session_state.user['is_bottleneck'] = False
                new_realm = promote_user_realm()
                st.session_state.user['current_realm'] = new_realm
                
                if st.button("🚀 Chinh phục Cảnh Giới Mới", type="primary", use_container_width=True):
                    st.session_state.phase = "FLASHCARD"
                    st.rerun()
            else:
                st.error("💥 ĐỘT PHÁ THẤT BẠI! Căn cơ chưa vững, Linh Lực tiêu tán. Trở về Bình Cảnh.")
                
                # Khóa Bình Cảnh
                set_bottleneck_state(True)
                st.session_state.user['is_bottleneck'] = True
                
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
        
        col_save, col_next_day = st.columns(2)
        with col_save:
            if st.button("💾 Lưu Tu Vi & Hoàn Tất", use_container_width=True):
                update_user_energy(elapsed)
                st.toast("Đã lưu tiến độ vào cơ sở dữ liệu thành công!", icon="✅")
                st.rerun()
                
        with col_next_day:
            curr_d = st.session_state.user["current_day"]
            
            if curr_d % 10 == 0:
                if st.button("👑 ĐỘT PHÁ: TIẾN VÀO ĐẠI THIÊN KIẾP (10 NGÀY)", use_container_width=True):
                    update_user_energy(elapsed)
                    st.session_state.exam_type = "MAJOR_10D"
                    # Đổi sang dùng hàm sinh đề Lôi Kiếp mới (50 câu)
                    st.session_state.exam_questions = generate_tribulation_exam(curr_d, is_major_breakthrough=True)
                    st.session_state.exam_idx = 0
                    st.session_state.exam_score = 0
                    st.session_state.exam_completed = False
                    st.session_state.phase = "loi_kiep" # Trỏ về màn hình Lôi Kiếp mới
                    st.rerun()
                    
            elif curr_d % 3 == 0:
                if st.button("⚡ ĐỘT PHÁ: TIẾN VÀO TIỂU THIÊN KIẾP (3 NGÀY)", use_container_width=True):
                    update_user_energy(elapsed)
                    st.session_state.exam_type = "MINI_3D"
                    # Đổi sang dùng hàm sinh đề Lôi Kiếp mới (20 câu)
                    st.session_state.exam_questions = generate_tribulation_exam(curr_d, is_major_breakthrough=False)
                    st.session_state.exam_idx = 0
                    st.session_state.exam_score = 0
                    st.session_state.exam_completed = False
                    st.session_state.phase = "loi_kiep" # Trỏ về màn hình Lôi Kiếp mới
                    st.rerun()
                    
            else:
                if st.button("🚀 Sang Bài Học Ngày Tiếp Theo", use_container_width=True):
                    update_user_energy(elapsed)
                    advance_user_day()
                    st.session_state.user["current_day"] += 1
                    st.session_state.phase = "FLASHCARD"
                    st.session_state.card_idx = 0
                    st.session_state.shadowing_idx = 0
                    st.session_state.cloze_idx = 0
                    st.session_state.is_flipped = False
                    st.session_state.shadowing_revealed = False
                    st.session_state.cloze_status = None
                    st.session_state.failed_today = []
                    st.session_state.review_queue = []
                    st.session_state.current_review_options = []
                    st.session_state.session_start = datetime.datetime.now()
                    st.rerun()

# =========================================================================
# TAB 2: TÂM MA BẢNG & THỐNG KÊ CHI TIẾT
# =========================================================================
with tab_stats:
    st.subheader("📊 Bảng Phong Thần - Quản Lý Tiến Độ & Tâm Ma")
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
        st.dataframe(
            exams,
            column_config={
                "exam_type": "Kỳ Thi",
                "stage_number": "Giai Đoạn",
                "total_questions": "Tổng Câu",
                "correct_answers": "Số Câu Đúng",
                "score_percent": st.column_config.NumberColumn("Điểm (%)", format="%.1f%%"),
                "is_passed": "Kết Quả (1: Đạt)",
                "taken_at": "Thời Gian"
            },
            use_container_width=True,
            hide_index=True
        )
    else:
        st.caption("Chưa có lịch sử thi cử nào được ghi nhận.")
        st.divider()
        st.markdown("### ☁️ Đồng Bộ & An Toàn Dữ Liệu (Google Drive)")
        st.caption("Chính sách an toàn: Hệ thống tự động duy trì 2 bản sao lưu của 2 ngày học gần nhất.")
        
        col_bk1, col_bk2 = st.columns(2)
        with col_bk1:
            if st.button("📤 Sao Lưu Tiến Độ Lên Drive", use_container_width=True):
                with st.spinner("Đang đóng gói và đồng bộ lên Google Drive..."):
                    success, msg = backup_to_drive(st.session_state.user["current_day"])
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                        
        with col_bk2:
            if st.button("📥 Khôi Phục Bản Mới Nhất Từ Drive", use_container_width=True):
                with st.spinner("Đang tải dữ liệu từ Google Drive và ghi đè..."):
                    success, msg = restore_latest_from_drive()
                    if success:
                        st.success(msg)
                        # Xóa sạch trạng thái session cũ và reset trang về trạng thái mới
                        st.session_state.clear()
                        st.rerun()
                    else:
                        st.error(msg)
# =========================================================================
# CHẠY NGẦM: BẮT PHÍM TẮT & PHÁT ÂM QUA WEB SPEECH API (ĐẶT Ở CUỐI FILE)
# =========================================================================
js_handler = f"""
<script>
    const synth = window.speechSynthesis;

    function playAudio(text) {{
        if (!synth || !text) return;
        synth.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'zh-CN';
        
        // Hãm tốc độ gốc của trình duyệt: lấy tốc độ chọn trên UI nhân với 0.85
        const uiRate = {st.session_state.get('speech_rate', 1.0)};
        utter.rate = uiRate * 0.85; 
        
        synth.speak(utter);
    }}

    {f"playAudio('{speak_text}');" if speak_text else ""}

    const doc = window.parent.document;
    
    // Lắng nghe mọi cú click trên giao diện, nếu click trúng nút "Nghe Lại Câu" thì phát âm
    doc.addEventListener('click', function(e) {{
        if (e.target && e.target.innerText && e.target.innerText.includes('Nghe Lại Câu')) {{
            playAudio('{speak_text}');
        }}
    }});

    doc.onkeydown = function(e) {{
        // Phím Space: Lật thẻ hoặc Hiện Pinyin ở Chặng 2
        if (e.code === 'Space') {{
            const btnFlip = doc.getElementById('btn_flip_card');
            const btnReveal = doc.getElementById('btn_shadowing_reveal');
            if (btnFlip) btnFlip.click();
            if (btnReveal) btnReveal.click();
        }}
        // Phím 1, 2, 3 ở Chặng 1 Flashcard
        if (e.key === '1') {{
            const btnFailed = doc.getElementById('btn_failed');
            if (btnFailed) btnFailed.click();
        }}
        if (e.key === '2') {{
            const btnVague = doc.getElementById('btn_vague');
            if (btnVague) btnVague.click();
        }}
        if (e.key === '3') {{
            const btnMastered = doc.getElementById('btn_mastered');
            if (btnMastered) btnMastered.click();
        }}
    }};
</script>
"""
components.html(js_handler, height=0)