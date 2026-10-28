import sqlite3
import random

DB_PATH = "chinese_mastery.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_user_progress():
    conn = get_db()
    cursor = conn.cursor()
    # Thêm is_bottleneck vào truy vấn
    cursor.execute("""
        SELECT id, current_realm, realm_level, spiritual_energy, current_day, consecutive_streak, last_study_date, is_bottleneck 
        FROM user_progress LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "id": row[0],
            "current_realm": row[1],
            "realm_level": row[2],
            "spiritual_energy": row[3],
            "current_day": row[4],
            "consecutive_streak": row[5],
            "last_study_date": row[6],
            "is_bottleneck": bool(row[7]) # Lấy trạng thái Bình Cảnh
        }
    return None

def update_user_energy(amount):
    """
    Nạp thêm hoặc tiêu hao Linh Lực. 
    Nếu amount > 0: Nạp linh lực (do học bài/ôn bài).
    Nếu amount < 0: Tiêu hao (do mua khiên bảo vệ chuỗi hoặc đóng phí Độ Kiếp).
    """
    conn = get_db()
    cursor = conn.cursor()
    
    # Đảm bảo linh lực không bao giờ rớt xuống số âm
    cursor.execute("""
        UPDATE user_progress 
        SET spiritual_energy = MAX(0, spiritual_energy + ?)
        WHERE id = 1
    """, (amount,))
    
    conn.commit()
    conn.close()

def advance_user_day(new_day=None):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE user_progress SET current_day = COALESCE(?, current_day + 1) WHERE id = 1", (new_day,))
    conn.commit()
    conn.close()

# Danh sách 8 Đại Cảnh Giới tương ứng với các giai đoạn 10 ngày
MAJOR_REALMS = [
    "Luyện Khí Kỳ",
    "Trúc Cơ Kỳ",
    "Kim Đan Kỳ",
    "Nguyên Anh Kỳ",
    "Hóa Thần Kỳ",
    "Luyện Hư Kỳ",
    "Hợp Thể Kỳ",
    "Đại Thừa Kỳ"
]

def promote_user_realm():
    """
    Tăng 1 tiểu tầng cảnh giới (Ví dụ: Luyện Khí Kỳ Tầng 1 -> Tầng 2).
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT current_realm, realm_level FROM user_progress WHERE id = 1")
    row = cursor.fetchone()
    current_realm = row["current_realm"]
    new_level = row["realm_level"] + 1
    
    base_name = current_realm.split("Tầng")[0].strip()
    updated_realm_name = f"{base_name} Tầng {new_level}"
    
    cursor.execute("""
        UPDATE user_progress 
        SET realm_level = ?, current_realm = ?
        WHERE id = 1
    """, (new_level, updated_realm_name))
    conn.commit()
    conn.close()
    return updated_realm_name

def breakthrough_major_realm(current_day):
    """
    Đột phá Đại Cảnh Giới sau khi vượt qua Đại Khảo 10 ngày.
    Reset tiểu tầng về 1 và lên Đại Cảnh Giới kế tiếp.
    """
    conn = get_db()
    cursor = conn.cursor()
    stage_idx = min(len(MAJOR_REALMS) - 1, current_day // 10)
    new_realm_name = f"{MAJOR_REALMS[stage_idx]} Tầng 1"
    
    cursor.execute("""
        UPDATE user_progress
        SET realm_level = 1, current_realm = ?
        WHERE id = 1
    """, (new_realm_name,))
    conn.commit()
    conn.close()
    return new_realm_name

def record_exam_result(exam_type, stage_number, total_q, correct_q, is_passed, weak_words=""):
    """
    Ghi lịch sử thi đúng theo schema của bảng exam_history.
    """
    conn = get_db()
    cursor = conn.cursor()
    score_pct = (correct_q / total_q) * 100 if total_q > 0 else 0
    cursor.execute("""
        INSERT INTO exam_history (exam_type, stage_number, total_questions, correct_answers, score_percent, is_passed, weak_words_tested)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (exam_type, stage_number, total_q, correct_q, score_pct, 1 if is_passed else 0, weak_words))
    conn.commit()
    conn.close()

def load_day_words(day):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vocab WHERE study_day = ? ORDER BY id ASC", (day,))
    words = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return words

def record_feedback(vocab_id, action):
    # 1 = FAILED, 2 = VAGUE, 3 = MASTERED
    conn = get_db()
    cursor = conn.cursor()
    if action == 1:
        cursor.execute("""
            UPDATE word_mastery 
            SET review_count = review_count + 1,
                failed_count = failed_count + 1,
                last_status = 'FAILED',
                is_inner_demon = 1,
                last_reviewed_at = CURRENT_TIMESTAMP
            WHERE vocab_id = ?
        """, (vocab_id,))
    elif action == 2:
        cursor.execute("""
            UPDATE word_mastery 
            SET review_count = review_count + 1,
                vague_count = vague_count + 1,
                last_status = 'VAGUE',
                is_inner_demon = 1,
                last_reviewed_at = CURRENT_TIMESTAMP
            WHERE vocab_id = ?
        """, (vocab_id,))
    elif action == 3:
        cursor.execute("""
            UPDATE word_mastery 
            SET review_count = review_count + 1,
                mastered_count = mastered_count + 1,
                last_status = 'MASTERED',
                last_reviewed_at = CURRENT_TIMESTAMP
            WHERE vocab_id = ?
        """, (vocab_id,))
    conn.commit()
    conn.close()

def get_review_options(correct_word):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT meaning_vi FROM vocab WHERE id != ? ORDER BY RANDOM() LIMIT 3", (correct_word["id"],))
    distractors = [row["meaning_vi"] for row in cursor.fetchall()]
    conn.close()
    
    options = distractors + [correct_word["meaning_vi"]]
    random.shuffle(options)
    return options

def get_inner_demons(limit=4):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.*, wm.failed_count, wm.vague_count, wm.review_count,
               (CAST(wm.failed_count AS FLOAT) / MAX(wm.review_count, 1)) AS fail_rate
        FROM vocab v
        JOIN word_mastery wm ON v.id = wm.vocab_id
        WHERE wm.is_inner_demon = 1
        ORDER BY fail_rate DESC, wm.failed_count DESC, RANDOM()
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def exorcise_inner_demon(vocab_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE word_mastery
        SET is_inner_demon = 0,
            mastered_count = mastered_count + 1,
            last_status = 'MASTERED',
            last_reviewed_at = CURRENT_TIMESTAMP
        WHERE vocab_id = ?
    """, (vocab_id,))
    conn.commit()
    conn.close()

def get_recent_words_for_exam(current_day, days_back=3, limit=8):
    conn = get_db()
    cursor = conn.cursor()
    start_day = max(1, current_day - days_back + 1)
    cursor.execute("""
        SELECT * FROM vocab 
        WHERE study_day >= ? AND study_day <= ?
        ORDER BY RANDOM()
        LIMIT ?
    """, (start_day, current_day, limit))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def save_exam_record(exam_type, target_day, score, passed, details_json=""):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO exam_history (exam_type, target_day, score, passed, details)
        VALUES (?, ?, ?, ?, ?)
    """, (exam_type, target_day, score, 1 if passed else 0, details_json))
    conn.commit()
    conn.close()
def get_cultivation_stats():
    """
    Lấy số liệu thống kê tổng quan về tiến độ học và trạng thái từ vựng.
    """
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM vocab")
    total_vocab = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT 
            SUM(CASE WHEN last_status = 'MASTERED' THEN 1 ELSE 0 END) AS mastered,
            SUM(CASE WHEN last_status = 'VAGUE' THEN 1 ELSE 0 END) AS vague,
            SUM(CASE WHEN last_status = 'FAILED' THEN 1 ELSE 0 END) AS failed,
            SUM(CASE WHEN is_inner_demon = 1 THEN 1 ELSE 0 END) AS demons,
            SUM(CASE WHEN review_count > 0 THEN 1 ELSE 0 END) AS learned
        FROM word_mastery
    """)
    row = cursor.fetchone()
    conn.close()
    
    return {
        "total_vocab": total_vocab,
        "mastered": row["mastered"] or 0,
        "vague": row["vague"] or 0,
        "failed": row["failed"] or 0,
        "demons": row["demons"] or 0,
        "learned": row["learned"] or 0
    }

def get_all_demons_detailed():
    """
    Lấy toàn bộ danh sách từ đang bị dính cờ Tâm Ma kèm chi tiết số lần sai.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.hanzi, v.pinyin, v.hanviet, v.meaning_vi, v.study_day,
               wm.failed_count, wm.vague_count, wm.review_count,
               ROUND((CAST(wm.failed_count AS FLOAT) / MAX(wm.review_count, 1)) * 100, 1) AS fail_rate_pct
        FROM vocab v
        JOIN word_mastery wm ON v.id = wm.vocab_id
        WHERE wm.is_inner_demon = 1
        ORDER BY wm.failed_count DESC, wm.review_count DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_recent_exam_history(limit=10):
    """
    Lấy danh sách lịch sử các lần thi gần nhất.
    """
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT exam_type, stage_number, total_questions, correct_answers, 
               score_percent, is_passed, taken_at
        FROM exam_history
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows
def set_bottleneck_state(is_active: bool):
    """Kích hoạt hoặc gỡ bỏ trạng thái Bình Cảnh (khóa tiến độ học từ mới)."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_progress 
        SET is_bottleneck = ?
        WHERE id = 1
    """, (1 if is_active else 0,))
    conn.commit()
    conn.close()

def get_tribulation_cost(is_major_breakthrough=False):
    """
    Tính toán chi phí linh lực để mở khóa bài thi Lôi Kiếp.
    - is_major_breakthrough = False: Đột phá Tiểu tầng (ví dụ Tầng 3 lên 4).
    - is_major_breakthrough = True: Đột phá Đại Cảnh Giới (ví dụ Luyện Khí lên Trúc Cơ).
    """
    # Công thức: 5 ngày x 20 linh lực/ngày = 100 max. Thu phí 35% cho Tiểu Khảo.
    base_cost = 35 
    
    if is_major_breakthrough:
        return base_cost * 3  # Đột phá cảnh giới lớn tốn kém gấp 3 (105 Linh lực)
    
    return base_cost
def get_hanzi_options(correct_word, limit=4):
    """Sinh 4 đáp án chữ Hán (1 đúng, 3 sai ngẫu nhiên) cho test nhanh."""
    import random
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, hanzi, pinyin 
        FROM vocab 
        WHERE id != ? 
        ORDER BY RANDOM() 
        LIMIT ?
    """, (correct_word['id'], limit - 1))
    rows = cursor.fetchall()
    conn.close()
    
    # Tạo danh sách các từ sai
    options = [{'id': r[0], 'hanzi': r[1], 'pinyin': r[2]} for r in rows]
    # Nhét từ đúng vào
    options.append({
        'id': correct_word['id'], 
        'hanzi': correct_word['hanzi'], 
        'pinyin': correct_word['pinyin']
    })
    random.shuffle(options)
    return options