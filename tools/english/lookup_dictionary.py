import sqlite3
import csv
import argparse
from pathlib import Path

# Import cấu hình
from config import SRC_DICT_DB, WORK_DIR

def map_pos_to_skypedia(penn_pos):
    """Chuyển đổi nhãn từ loại Penn Treebank sang dạng cơ bản để khớp từ điển"""
    p = penn_pos.upper()
    if p.startswith('NN'): return 'noun'
    if p.startswith('VB'): return 'verb'
    if p.startswith('JJ'): return 'adj'
    if p.startswith('RB'): return 'adv'
    return ''

def main():
    parser = argparse.ArgumentParser(description="Tra cứu nghĩa, IPA và ví dụ từ từ điển Skypedia")
    parser.parse_args()

    in_csv = WORK_DIR / "words_leveled.csv"
    out_csv = WORK_DIR / "words_enriched.csv"

    if not in_csv.exists():
        print("❌ Lỗi: Không tìm thấy words_leveled.csv. Hãy chạy select_words.py trước.")
        return
    if not SRC_DICT_DB.exists():
        print("❌ Lỗi: Không tìm thấy dictionary_en_vi.db. Hãy chạy fetch_sources.py trước.")
        return

    print("📂 Đang kết nối kho từ điển Offline...")
    conn = sqlite3.connect(SRC_DICT_DB)
    cursor = conn.cursor()

    words_data = []
    
    # Đọc 5.500 từ cốt lõi
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            words_data.append(row)

    print(f"🔍 Bắt đầu tra cứu {len(words_data):,} từ...\n")
    
    enriched_data = []
    stats = {
        "full_match": 0,    # Có đủ IPA, Nghĩa, Ví dụ
        "partial": 0,       # Có nghĩa nhưng thiếu IPA hoặc Ví dụ
        "not_found": 0      # Không có trong từ điển
    }

    for idx, item in enumerate(words_data):
        word = item["word"]
        pos_hint = map_pos_to_skypedia(item["pos"])
        
        # 1. Tìm ID của từ
        cursor.execute("SELECT id FROM words WHERE word = ? COLLATE NOCASE LIMIT 1", (word,))
        w_row = cursor.fetchone()
        
        ipa = ""
        meaning_vi = ""
        example_en = ""
        needs_ai = 1 # Mặc định cần AI xử lý (để gắn domain công sở và rà soát)
        
        if w_row:
            word_id = w_row[0]
            
            # 2. Lấy IPA (Ưu tiên giọng Mỹ - NAmE / US)
            cursor.execute("""
                SELECT ipa FROM pronunciations 
                WHERE word_id = ? 
                ORDER BY 
                    CASE 
                        WHEN region LIKE '%US%' THEN 1 
                        WHEN region LIKE '%NAmE%' THEN 2 
                        ELSE 3 
                    END
                LIMIT 1
            """, (word_id,))
            ipa_row = cursor.fetchone()
            if ipa_row and ipa_row[0]:
                ipa = ipa_row[0].strip()

            # 3. Lấy Nghĩa và Ví dụ
            cursor.execute("""
                SELECT d.definition, wd.example 
                FROM definitions d
                JOIN word_definitions wd ON d.id = wd.definition_id
                WHERE wd.word_id = ?
            """, (word_id,))
            
            results = cursor.fetchall()
            if results:
                # Ưu tiên lấy dòng nào có sẵn câu ví dụ ngắn gọn
                best_def = ""
                best_ex = ""
                for m, ex in results:
                    m = m.strip() if m else ""
                    ex = ex.strip() if ex else ""
                    
                    if m and not best_def:
                        best_def = m
                    if m and ex:
                        best_def = m
                        best_ex = ex
                        break # Tìm thấy cặp hoàn hảo đầu tiên thì dừng
                
                meaning_vi = best_def
                example_en = best_ex
        
        # Phân loại thống kê
        if meaning_vi and example_en and ipa:
            stats["full_match"] += 1
            # Tuy đủ dữ liệu cơ bản, nhưng những từ thuộc priority cao vẫn cần 
            # AI duyệt để gắn domain="OFFICE/TEACHER" và chỉnh văn phong.
            # Ta vẫn để needs_ai = 1, Gemini sẽ quyết định có ghi đè ví dụ hay không.
        elif meaning_vi:
            stats["partial"] += 1
        else:
            stats["not_found"] += 1

        enriched_data.append({
            "word": word,
            "pos": item["pos"],
            "cefr": item["cefr"],
            "frequency": item["frequency"],
            "ipa": ipa,
            "meaning_vi": meaning_vi,
            "example_en": example_en,
            "needs_ai": needs_ai
        })

    conn.close()

    # Ghi file kết quả
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["word", "pos", "cefr", "frequency", "ipa", "meaning_vi", "example_en", "needs_ai"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(enriched_data)

    print("📊 BÁO CÁO TRA CỨU TỪ ĐIỂN OFFLINE:")
    print(f" - Hoàn hảo (Đủ Nghĩa + IPA + Ví dụ): {stats['full_match']:,} từ")
    print(f" - Khuyết thiếu (Có nghĩa nhưng thiếu IPA/Ví dụ): {stats['partial']:,} từ")
    print(f" - Trắng thông tin (Không có trong DB): {stats['not_found']:,} từ")
    print(f"\n💾 Đã xuất file chuẩn bị cho AI: {out_csv.relative_to(Path.cwd())}")

if __name__ == "__main__":
    main()