import csv
import argparse
from pathlib import Path
from collections import defaultdict

# Import đường dẫn từ config
from config import WORK_DIR

def main():
    parser = argparse.ArgumentParser(description="Lọc và cắt giảm số lượng từ vựng theo chuẩn CEFR")
    parser.parse_args()
    
    in_csv = WORK_DIR / "cefr.csv"
    out_csv = WORK_DIR / "words_leveled.csv"
    
    if not in_csv.exists():
        print("❌ Không tìm thấy file cefr.csv. Hãy chạy load_cefr_dataset.py trước.")
        return

    print("📂 Đang đọc và phân loại dữ liệu theo tần suất...")
    
    # Đọc dữ liệu
    words_by_level = defaultdict(list)
    with open(in_csv, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            word = row["word"]
            
            # Loại bỏ các từ 1 chữ cái vô nghĩa (chỉ giữ lại 'a' và 'i')
            if len(word) == 1 and word not in ["a", "i"]:
                continue
                
            words_by_level[row["cefr"]].append({
                "word": word,
                "pos": row["pos"],
                "cefr": row["cefr"],
                "frequency": int(row["frequency"])
            })

    # Sắp xếp từ vựng trong mỗi level theo tần suất giảm dần
    for lvl in words_by_level:
        words_by_level[lvl].sort(key=lambda x: x["frequency"], reverse=True)

    # Định mức lấy từ (Quota) để đạt đúng ranh giới của lộ trình học (Mục 13.9)
    # Tổng cộng sẽ là 5.500 từ
    quotas = {
        "A1": 500,
        "A2": 500,   # Tích lũy A1+A2 = 1.000 từ
        "B1": 1000,  # Tích lũy = 2.000 từ
        "B2": 1250,  # Tích lũy = 3.250 từ
        "C1": 1250,  # Tích lũy = 4.500 từ
        "C2": 1000   # Tích lũy = 5.500 từ
    }

    selected_words = []
    stats = {}

    for lvl in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        quota = quotas[lvl]
        available = words_by_level[lvl]
        
        # Cắt lấy đúng số lượng top đầu
        selected = available[:quota]
        selected_words.extend(selected)
        stats[lvl] = len(selected)

    # Ghi danh sách tinh hoa ra file CSV mới
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["word", "pos", "cefr", "frequency"])
        writer.writeheader()
        writer.writerows(selected_words)

    # Báo cáo kết quả
    print("\n✂️ KẾT QUẢ TINH TUYỂN (Chỉ lấy các từ có tần suất cao nhất):")
    total = 0
    for lvl in ["A1", "A2", "B1", "B2", "C1", "C2"]:
        print(f" - {lvl}: Lấy {stats[lvl]:,} / {len(words_by_level[lvl]):,} từ (Mục tiêu: {quotas[lvl]})")
        total += stats[lvl]
    
    print(f"\n✅ TỔNG CỘNG ĐÃ CHỌN: {total:,} từ vựng cốt lõi.")
    print(f"💾 Đã lưu danh sách tại: {out_csv.relative_to(Path.cwd())}")

if __name__ == "__main__":
    main()