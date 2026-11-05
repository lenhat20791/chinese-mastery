"""Cấu hình thông số riêng cho từng khóa học (Tiếng Trung / Tiếng Anh)"""
import streamlit as st

COURSES = {
    "zh": {
        "db_path": "chinese_mastery.db",
        "tts_lang": "zh-CN",
        "tts_rate_short_factor": 0.55,
        "tts_rate_sentence_factor": 0.85,
        "label_word": "chữ Hán",
        "has_pinyin": True,
        "has_radicals": True,
        "has_hanviet": True,
        "words_per_day": 4,
        "levels": None,
        "title": "Tiếng Trung",
        "flag": "🇨🇳",
        "pronunciation_tab": "render_pronunciation",
        "compose_examples": True,
        "hero_title": "Thực Chiến Tiếng Trung Công Sở",
        "priority_labels": {
            1: "Từ vựng giao tiếp công việc",
            2: "Từ kết nối và bổ trợ câu",
            3: "Đời sống xoay quanh công việc",
            4: "Mở rộng vốn từ HSK 1–5",
        },
    },
    "en": {
        "db_path": "english_mastery.db",
        "tts_lang": "en-US",
        "tts_rate_short_factor": 0.80,
        "tts_rate_sentence_factor": 0.85,
        "label_word": "từ vựng",
        "has_pinyin": False,
        "has_radicals": False,
        "has_hanviet": False,
        "words_per_day": 4,
        "levels": ["A2", "B1", "B2"],
        "title": "Tiếng Anh",
        "flag": "🇬🇧",
        "pronunciation_tab": "render_pronunciation_en",
        "compose_examples": False,
        "hero_title": "Thực Chiến Tiếng Anh Công Sở",
        "priority_labels": {
            1: "Từ vựng công sở",
            2: "Từ vựng giảng dạy – sư phạm THCS",
            4: "Mở rộng vốn từ theo CEFR",
        },
    }
}

def get_config(course_id=None):
    """Lấy cấu hình của khóa học hiện tại."""
    if course_id is None:
        course_id = st.session_state.get("active_course", "zh")
    return COURSES.get(course_id.split(":")[0], COURSES["zh"])