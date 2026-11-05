import sqlite3
import csv
import argparse
from pathlib import Path
from collections import defaultdict

# Import cấu hình từ config.py
from config import SRC_CEFR_DB, WORK_DIR, MIN_FREQUENCY_COUNT

def map_to_cefr(level_num):
    """Chuyển đổi số float thành mức CEFR (1=A1 ... 6=C2)"""
    try:
        lvl = round(float(level_num))
    except (ValueError, TypeError):
        return "B1" # Fallback an toàn
    
    mapping = {1: "A1", 2: "A2", 3: "B1", 4: "B2", 5: "C1", 6: "C2"}
    if lvl < 1: return "A1"
    if lvl > 6: return "C2"
    return mapping[lvl]

def get_columns(cursor, table_name):
    """Lấy danh sách các cột của một bảng"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]

def main():
    parser = argparse.ArgumentParser(description="Trích xuất và lọc thô dữ liệu từ Words-CEFR-Dataset")
    parser.parse_args()

    print(f"📂 Đang đọc cơ sở dữ liệu: {SRC_CEFR_DB.name}...")
    if not SRC_CEFR_DB.exists():
        print("❌ Lỗi: Không tìm thấy file DB. Hãy chạy fetch_sources.py trước.")
        return

    conn = sqlite3.connect(SRC_CEFR_DB)
    cursor = conn.cursor()

    # 1. Tự động nội soi cấu trúc DB để lấy đúng tên cột
    pt_cols = get_columns(cursor, "pos_tags")
    wp_cols = get_columns(cursor, "word_pos")

    # Tìm cột khóa chính/ngoại động thay vì fix cứng
    pt_id_col = "pos_tag_id" if "pos_tag_id" in pt_cols else pt_cols[0]
    wp_pt_id_col = "pos_tag_id" if "pos_tag_id" in wp_cols else next((c for c in wp_cols if 'pos' in c), wp_cols[2])
    tag_col = "pos_tag" if "pos_tag" in pt_cols else ("tag" if "tag" in pt_cols else pt_cols[1])
    
    # Đưa logic chọn cột ra ngoài f-string để tránh lỗi cú pháp Python
    lemma_in_wp = "lemma_word_id" in wp_cols
    lemma_select = "wp.lemma_word_id" if lemma_in_wp else "w.stem_word_id"

    # 2. Xây dựng câu truy vấn an toàn
    query = f"""
        SELECT 
            w.word, 
            pt.{tag_col}, 
            wp.level, 
            wp.frequency_count, 
            wp.word_id, 
            {lemma_select} as lemma_id
        FROM word_pos wp
        JOIN words w ON w.word_id = wp.word_id
        JOIN pos_tags pt ON pt.{pt_id_col} = wp.{wp_pt_id_col}
    """
    cursor.execute(query)
    
    word_dict = {} 
    
    raw_count = 0
    skipped_not_alpha = 0
    skipped_proper_noun = 0
    skipped_not_lemma = 0
    skipped_low_freq = 0

    for row in cursor.fetchall():
        raw_count += 1
        word, pos, level_num, freq, word_id, lemma_word_id = row
        
        # 1. Lọc định dạng (chỉ chữ cái viết thường)
        if not (word.isalpha() and word.islower()):
            skipped_not_alpha += 1
            continue
            
        # 2. Lọc POS tên riêng
        if pos in ["NNP", "NNPS"]:
            skipped_proper_noun += 1
            continue
            
        # 3. Lọc biến thể, chỉ lấy từ gốc (lemma)
        is_lemma = (lemma_word_id == word_id) or (lemma_word_id is None) or (lemma_word_id == 0)
        if not is_lemma:
            skipped_not_lemma += 1
            continue
            
        # 4. Lọc theo ngưỡng tần suất tối thiểu
        freq = int(freq) if freq else 0
        if freq < MIN_FREQUENCY_COUNT:
            skipped_low_freq += 1
            continue
            
        cefr = map_to_cefr(level_num)
        
        # 5. Khử trùng: Nếu từ đã tồn tại, chỉ ghi đè nếu dòng mới có tần suất cao hơn
        if word in word_dict:
            if freq > word_dict[word][2]:
                word_dict[word] = (pos, cefr, freq)
        else:
            word_dict[word] = (pos, cefr, freq)

    conn.close()

    # Thống kê phân bổ CEFR
    stats = defaultdict(int)
    for data in word_dict.values():
        stats[data[1]] += 1

    # Ghi ra CSV trung gian
    out_csv = WORK_DIR / "cefr.csv"
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["word", "pos", "cefr", "frequency"])
        for word, (pos, cefr, freq) in word_dict.items():
            writer.writerow([word, pos, cefr, freq])

    # In báo cáo
    print("\n📊 THỐNG KÊ TRÍCH XUẤT:")
    print(f" - Tổng số bản ghi thô quét qua: {raw_count:,}")
    print(f" - Loại vì chứa ký tự lạ / viết hoa: {skipped_not_alpha:,}")
    print(f" - Loại vì là tên riêng (NNP/NNPS): {skipped_proper_noun:,}")
    print(f" - Loại vì là biến thể (không phải lemma): {skipped_not_lemma:,}")
    print(f" - Loại vì tần suất < {MIN_FREQUENCY_COUNT}: {skipped_low_freq:,}")
    print(f"\n✅ SỐ TỪ GỐC HỢP LỆ THU ĐƯỢC: {len(word_dict):,}")
    
    print("\n📈 PHÂN BỔ THEO CEFR:")
    for lvl in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        print(f" - {lvl}: {stats[lvl]:,} từ")
        
    print(f"\n💾 Đã lưu file trung gian tại: {out_csv.relative_to(Path.cwd())}")

if __name__ == "__main__":
    main()