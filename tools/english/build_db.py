import sqlite3
import csv
import argparse
import re
from pathlib import Path

# Import cấu hình
from config import WORK_DIR, OUT_DB, WORDS_PER_DAY

def generate_cloze(example, word):
    """Tạo câu điền khuyết bằng cách thay từ gốc thành '___'"""
    if not example or not word: return ""
    # Dùng regex để thay thế không phân biệt hoa thường, chỉ thay thế whole word nếu có thể
    pattern = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    cloze = pattern.sub("___", example)
    if cloze == example: # Nếu không tìm thấy boundary, thay thế chuỗi thường
        pattern_fallback = re.compile(re.escape(word), re.IGNORECASE)
        cloze = pattern_fallback.sub("___", example)
    return cloze

def cefr_to_int(cefr):
    mapping = {"A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}
    return mapping.get(cefr, 99)

def main():
    parser = argparse.ArgumentParser(description="Dựng english_mastery.db từ dữ liệu đã làm giàu")
    parser.parse_args()

    in_csv = WORK_DIR / "words_ai_completed.csv"
    if not in_csv.exists():
        print("❌ Lỗi: Không tìm thấy words_ai_completed.csv. Hãy chạy ai_enrich.py trước.")
        return

    print("📂 Đang đọc và sắp xếp dữ liệu từ vựng...")
    
    words = []
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            words.append(row)

    # Thuật toán sắp xếp lộ trình học (Mục 13.12):
    # 1. Nhóm ưu tiên (priority_group) TĂNG DẦN: 1 (Office) -> 2 (Teacher) -> 4 (General)
    # 2. Mức CEFR (cefr_to_int) TĂNG DẦN: A1 -> C2
    # 3. Tần suất (frequency) GIẢM DẦN: Học từ dùng nhiều nhất trước
    words.sort(key=lambda x: (
        int(x["priority_group"]), 
        cefr_to_int(x["cefr"]), 
        -int(x["frequency"])
    ))

    print(f"🛠️ Bắt đầu tạo database {OUT_DB.name}...")
    
    if OUT_DB.exists():
        OUT_DB.unlink() # Xóa file cũ nếu có để ghi đè sạch

    conn = sqlite3.connect(OUT_DB)
    cursor = conn.cursor()

    # Schema CỨNG phải khớp 100% với chinese_mastery.db để tái sử dụng game
    cursor.execute("""
        CREATE TABLE vocab (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hanzi TEXT NOT NULL,
            traditional TEXT,
            pinyin TEXT,
            hanviet TEXT,
            meaning_vi TEXT,
            domain TEXT,
            hsk_level TEXT,
            study_day INTEGER,
            stage_10d INTEGER,
            example_zh TEXT,
            example_pinyin TEXT,
            example_vi TEXT,
            example_cloze TEXT,
            chiet_tu TEXT,
            priority_group INTEGER DEFAULT 4
        )
    """)

    insert_data = []
    for index, w in enumerate(words):
        # Tính toán ngày học (Mỗi ngày học WORDS_PER_DAY từ)
        study_day = (index // WORDS_PER_DAY) + 1
        stage_10d = ((study_day - 1) // 10) + 1
        
        example_en = w["example_en"].strip()
        cloze = generate_cloze(example_en, w["word"])

        # Ánh xạ trường dữ liệu từ Anh sang Trung (Mục 13.2)
        insert_data.append((
            w["word"],                  # hanzi -> Tiếng Anh
            "",                         # traditional
            w["ipa"],                   # pinyin -> IPA
            "",                         # hanviet
            w["meaning_vi"],            # meaning_vi
            w["domain"],                # domain (OFFICE/TEACHER/GENERAL)
            w["cefr"],                  # hsk_level -> CEFR
            study_day,                  # study_day
            stage_10d,                  # stage_10d
            example_en,                 # example_zh -> Câu ví dụ Tiếng Anh
            "",                         # example_pinyin
            w["example_vi"].strip(),    # example_vi
            cloze,                      # example_cloze
            "",                         # chiet_tu
            int(w["priority_group"])    # priority_group
        ))

    cursor.executemany("""
        INSERT INTO vocab (
            hanzi, traditional, pinyin, hanviet, meaning_vi, domain, hsk_level, 
            study_day, stage_10d, example_zh, example_pinyin, example_vi, example_cloze, chiet_tu, priority_group
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, insert_data)

    conn.commit()
    
    # Kiểm tra tính toàn vẹn
    cursor.execute("PRAGMA integrity_check")
    integrity = cursor.fetchone()[0]
    
    # Thống kê nhanh
    cursor.execute("SELECT MAX(study_day), COUNT(*) FROM vocab")
    max_day, total_words = cursor.fetchone()
    
    conn.close()

    print("\n📊 THỐNG KÊ LỘ TRÌNH HỌC:")
    print(f" - Tổng số từ đã nhập: {total_words:,}")
    print(f" - Tổng số ngày học: {max_day:,} ngày (Mỗi ngày {WORDS_PER_DAY} từ)")
    print(f" - Trạng thái DB: {integrity}")
    print(f"\n🎉 HOÀN TẤT! File database đã sẵn sàng tại: {OUT_DB.resolve()}")

if __name__ == "__main__":
    main()