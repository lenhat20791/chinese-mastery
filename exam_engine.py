import random
from database import get_recent_words_for_exam, get_inner_demons, get_hanzi_options
import game_config as cfg


def _to_question(w, phase):
    return {
        'vocab_id': w['id'],
        'question_text': f"Nghĩa: {w['meaning_vi']}",
        'pinyin_hint': w['pinyin'],
        'options': get_hanzi_options(w),   # 4 chữ Hán (1 đúng, 3 sai)
        'correct_id': w['id'],
        'word_data': w,
        'phase': phase,                    # 'loi' (Lôi Kiếp) | 'tam_ma' (Tâm Ma Kiếp)
    }


def _loi_kiep_words(current_day, total_q, days_back):
    """Tỷ lệ khắt khe: 50% kiến thức tầng hiện tại, 30% Tâm Ma, 20% toàn bộ kiến thức cũ."""
    q_current = int(total_q * 0.5)
    q_demon = int(total_q * 0.3)
    q_past = total_q - q_current - q_demon
    words = (get_recent_words_for_exam(current_day, days_back, q_current)
             + get_inner_demons(q_demon)
             + get_recent_words_for_exam(current_day, current_day, q_past))
    pool = {w['id']: w for w in words}
    final = list(pool.values())
    random.shuffle(final)
    return final[:total_q]


def tam_ma_words(current_day, count, exclude_ids=()):
    """Từ cho Tâm Ma Kiếp: ưu tiên tâm ma đang bám, thiếu thì bù từ kiến thức cũ."""
    picked = {}
    for w in get_inner_demons(count * 2):
        if w['id'] not in exclude_ids and len(picked) < count:
            picked[w['id']] = w
    if len(picked) < count:
        for w in get_recent_words_for_exam(current_day, current_day, count * 2):
            if w['id'] not in exclude_ids and w['id'] not in picked and len(picked) < count:
                picked[w['id']] = w
    return list(picked.values())


def generate_tribulation_exam(current_day, is_major_breakthrough=False):
    """
    - Tiểu Thiên Kiếp (3 ngày): 20 câu Lôi Kiếp.
    - Đại Thiên Kiếp (10 ngày): 40 câu Lôi Kiếp + TAM_MA_Q_MAJOR câu Tâm Ma Kiếp ở cuối.
    """
    if not is_major_breakthrough:
        return [_to_question(w, 'loi') for w in _loi_kiep_words(current_day, 20, 5)]

    tam_ma_q = cfg.TAM_MA_Q_MAJOR
    loi_words = _loi_kiep_words(current_day, 50 - tam_ma_q, 45)
    questions = [_to_question(w, 'loi') for w in loi_words]
    used = {w['id'] for w in loi_words}
    questions += [_to_question(w, 'tam_ma') for w in tam_ma_words(current_day, tam_ma_q, used)]
    return questions
