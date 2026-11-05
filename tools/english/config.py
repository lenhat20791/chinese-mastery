import os
from pathlib import Path

# --- ĐƯỜNG DẪN LÀM VIỆC ---
BASE_DIR = Path(__file__).parent
WORK_DIR = BASE_DIR / "work"
SRC_DIR = WORK_DIR / "src"

# Đường dẫn clone repo nguồn (chỉ tải về, không đưa vào git)
REPO_CEFR = "https://github.com/Maximax67/Words-CEFR-Dataset.git"
REPO_DICT = "https://github.com/skypediacode/english-vietnamese-dictionary.git"

SRC_CEFR_DB = SRC_DIR / "Words-CEFR-Dataset" / "word_cefr_minified.db"
SRC_DICT_DB = SRC_DIR / "english-vietnamese-dictionary" / "dictionary_en_vi.db"

# Đầu ra cuối cùng
OUT_DB = BASE_DIR.parent.parent / "english_mastery.db"

# --- CẤU HÌNH LỘ TRÌNH (Theo mục 13.9) ---
WORDS_PER_DAY = 4
EN_CEFR_VOCAB = {
    "A2": 1000,
    "B1": 2000,
    "B2": 3250,
    "C1": 4500,
    "C2": 5500
}

# --- CẤU HÌNH AI (Gemini) ---
# Lấy API Key từ biến môi trường của hệ thống
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash" # Dùng bản flash cho rẻ và nhanh khi xử lý batch lớn

# Ngưỡng tần suất tối thiểu để giữ lại từ (loại bỏ các từ quá hiếm)
MIN_FREQUENCY_COUNT = 5