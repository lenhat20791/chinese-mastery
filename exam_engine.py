import random
from database import get_recent_words_for_exam, get_inner_demons, get_hanzi_options

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
        # get_hanzi_options trả về 4 chữ Hán (1 đúng, 3 sai)
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