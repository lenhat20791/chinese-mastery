import random
from database import get_recent_words_for_exam, get_inner_demons, get_review_options, get_hanzi_options

def generate_mini_exam(current_day):
    """
    Sinh đề thi Tiểu Khảo (Mỗi 3 ngày):
    - Tổng cộng: 12 câu trắc nghiệm
    - 8 câu từ 3 ngày gần nhất
    - 4 câu từ danh sách Tâm Ma (nếu thiếu tâm ma thì bù bằng từ ngẫu nhiên trong chu kỳ)
    """
    recent_words = get_recent_words_for_exam(current_day, days_back=3, limit=8)
    demon_words = get_inner_demons(limit=4)
    
    # Gom danh sách từ cần thi, tránh trùng lặp
    selected_dict = {w["id"]: w for w in demon_words}
    for w in recent_words:
        selected_dict[w["id"]] = w
        
    exam_words = list(selected_dict.values())
    
    # Nếu chưa đủ 12 câu do thiếu từ, bổ sung thêm từ các ngày trước
    if len(exam_words) < 12:
        extra_words = get_recent_words_for_exam(current_day, days_back=current_day, limit=12 - len(exam_words))
        for w in extra_words:
            if w["id"] not in selected_dict:
                exam_words.append(w)
                selected_dict[w["id"]] = w
                
    random.shuffle(exam_words)
    
    # Tạo câu hỏi và 4 đáp án cho từng từ
    questions = []
    for word in exam_words:
        options = get_review_options(word)
        questions.append({
            "vocab_id": word["id"],
            "hanzi": word["hanzi"],
            "pinyin": word["pinyin"],
            "hanviet": word["hanviet"],
            "correct_meaning": word["meaning_vi"],
            "options": options
        })
    return questions
def generate_major_exam(current_day):
    """
    Sinh đề thi Đại Khảo (Mỗi 10 ngày):
    - Tổng cộng: 30 câu
    - Phần 1 (20 câu Trắc nghiệm): Quét 40 từ vựng của 10 ngày vừa học + vét sạch Tâm Ma.
    - Phần 2 (10 câu Điền khuyết - Typing Cloze): Đục lỗ câu công vụ, yêu cầu gõ đúng chữ Hán.
    """
    # Lấy toàn bộ từ đã học trong chu kỳ 10 ngày vừa qua
    start_day = max(1, current_day - 9)
    recent_words = get_recent_words_for_exam(current_day, days_back=10, limit=40)
    demon_words = get_inner_demons(limit=10)
    
    combined_dict = {w["id"]: w for w in demon_words}
    for w in recent_words:
        combined_dict[w["id"]] = w
        
    all_words = list(combined_dict.values())
    random.shuffle(all_words)
    
    # 20 câu trắc nghiệm
    mc_words = all_words[:20] if len(all_words) >= 20 else all_words
    mc_questions = []
    for word in mc_words:
        mc_questions.append({
            "type": "CHOICE",
            "vocab_id": word["id"],
            "hanzi": word["hanzi"],
            "pinyin": word["pinyin"],
            "hanviet": word["hanviet"],
            "correct_meaning": word["meaning_vi"],
            "options": get_review_options(word)
        })
        
    # 10 câu gõ phím Cloze Test
    cloze_candidates = all_words[20:30] if len(all_words) >= 30 else all_words[:10]
    cloze_questions = []
    for word in cloze_candidates:
        cloze_questions.append({
            "type": "CLOZE",
            "vocab_id": word["id"],
            "hanzi": word["hanzi"],
            "pinyin": word["pinyin"],
            "hanviet": word["hanviet"],
            "meaning_vi": word["meaning_vi"],
            "example_cloze": word["example_cloze"],
            "example_vi": word["example_vi"]
        })
        
    return mc_questions + cloze_questions
def generate_tribulation_exam(current_day, is_major_breakthrough=False):
    """
    Sinh đề thi Lôi Kiếp (Đột phá Cảnh Giới).
    Tỷ lệ khắt khe: 50% kiến thức tầng hiện tại, 30% Tâm Ma, 20% Toàn bộ kiến thức cũ.
    - is_major_breakthrough = False (Đột phá Tiểu Tầng): Đề 20 câu.
    - is_major_breakthrough = True (Đại Khảo Độ Kiếp): Đề 50 câu.
    """
    total_q = 50 if is_major_breakthrough else 20
    
    q_current = int(total_q * 0.5)
    q_demon = int(total_q * 0.3)
    q_past = total_q - q_current - q_demon
    
    # 1. Lấy từ vựng theo tỷ lệ
    days_back = 45 if is_major_breakthrough else 5
    
    # 50% từ vựng của giai đoạn (5 ngày hoặc 45 ngày qua)
    current_words = get_recent_words_for_exam(current_day, days_back, q_current)
    
    # 30% bốc ngẫu nhiên từ danh sách những từ hay sai (Tâm ma)
    demon_words = get_inner_demons(q_demon)
    
    # 20% bốc ngẫu nhiên từ Toàn Bộ lịch sử học (days_back = current_day nghĩa là lục lại từ ngày 1)
    past_words = get_recent_words_for_exam(current_day, current_day, q_past)
    
    # 2. Gộp lại và loại bỏ trùng lặp (trường hợp data ít, 1 từ bị bốc trúng 2 lần)
    pool = {}
    for w in current_words + demon_words + past_words:
        pool[w['id']] = w
        
    final_words = list(pool.values())
    random.shuffle(final_words)
    
    # Cắt cho đúng số lượng câu hỏi yêu cầu
    final_words = final_words[:total_q]
    
    # 3. Đóng gói thành danh sách câu hỏi trắc nghiệm 4 đáp án (A,B,C,D)
    questions = []
    for w in final_words:
        # Hàm get_review_options sẽ trả về 4 từ (1 đúng, 3 sai) để làm đáp án
        options = get_hanzi_options(w)
        
        q = {
            'vocab_id': w['id'],
            'question_text': f"Nghĩa: {w['meaning_vi']}", # Hỏi nghĩa tiếng Việt
            'pinyin_hint': w['pinyin'],                 # Gợi ý Pinyin (có thể ẩn/hiện trên UI)
            'options': options,                         # 4 nút đáp án bằng chữ Hán
            'correct_id': w['id'],
            'word_data': w
        }
        questions.append(q)
        
    return questions