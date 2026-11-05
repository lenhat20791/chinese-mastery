import sqlite3
import sys
import argparse
from pathlib import Path
from config import OUT_DB, WORDS_PER_DAY

def main():
    parser = argparse.ArgumentParser(description="Kiểm tra tính hợp lệ của DB tiếng Anh")
    parser.parse_args()

    if not OUT_DB.exists():
        print(f"❌ Lỗi: Không tìm thấy file {OUT_DB.name}")
        sys.exit(1)

    print("🔍 Đang chạy kiểm thử dữ liệu toàn diện...\n")
    conn = sqlite3.connect(OUT_DB)
    cursor = conn.cursor()
    errors = 0

    # 1. Kiểm tra rỗng dữ liệu
    cursor.execute("SELECT hanzi FROM vocab WHERE meaning_vi = '' OR pinyin = '' OR example_zh = ''")
    missing = cursor.fetchall()
    if missing:
        print(f"❌ LỖI: Có {len(missing)} từ bị khuyết nghĩa, IPA hoặc ví dụ.")
        errors += 1

    # 2. Đảm bảo mỗi ngày có ĐÚNG 4 từ
    cursor.execute(f"""
        SELECT study_day, COUNT(*) FROM vocab 
        GROUP BY study_day 
        HAVING COUNT(*) != {WORDS_PER_DAY}
    """)
    bad_days = cursor.fetchall()
    if bad_days:
        print(f"❌ LỖI: Có {len(bad_days)} ngày học không đủ {WORDS_PER_DAY} từ.")
        errors += 1

    # 3. Kiểm tra trùng nghĩa tiếng Việt trong CÙNG 1 NGÀY (Gây lỗi Lật Bài)
    cursor.execute("""
        SELECT study_day, meaning_vi, COUNT(*)
        FROM vocab
        GROUP BY study_day, meaning_vi
        HAVING COUNT(*) > 1
    """)
    dupes = cursor.fetchall()
    if dupes:
        print(f"⚠️ CẢNH BÁO: Có {len(dupes)} trường hợp trùng nghĩa tiếng Việt trong cùng 1 ngày học.")
        print("   (Điều này có thể làm mini game Lật Bài bị nhiễu do 2 đáp án giống nhau).")
        errors += 1

    # In Thống kê
    print("📊 THỐNG KÊ CEFR:")
    cursor.execute("SELECT hsk_level, COUNT(*) FROM vocab GROUP BY hsk_level")
    for row in cursor.fetchall(): 
        print(f" - Mức {row[0]}: {row[1]:,} từ")

    print("\n📊 THỐNG KÊ CHỦ ĐỀ (Domain):")
    cursor.execute("SELECT domain, COUNT(*) FROM vocab GROUP BY domain")
    for row in cursor.fetchall(): 
        print(f" - {row[0]}: {row[1]:,} từ")

    print("\n🎲 NGHIỆM THU NGẪU NHIÊN 30 TỪ VỰNG:")
    cursor.execute("SELECT hanzi, domain, hsk_level, meaning_vi, example_zh, example_vi FROM vocab ORDER BY RANDOM() LIMIT 30")
    for i, (word, domain, lvl, mean, ex_en, ex_vi) in enumerate(cursor.fetchall()):
        print(f"{i+1:02d}. [{domain} | {lvl}] {word}: {mean}")
        print(f"    EN: {ex_en}")
        print(f"    VI: {ex_vi}\n")

    conn.close()

    if errors > 0:
        print("❌ DATABASE KHÔNG ĐẠT CHUẨN. Vui lòng kiểm tra lại log.")
        sys.exit(1)
    else:
        print("✅ DATABASE VƯỢT QUA TOÀN BỘ BÀI KIỂM TRA!")

if __name__ == "__main__":
    main()