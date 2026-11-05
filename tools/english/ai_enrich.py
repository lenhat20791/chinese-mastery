import csv
import json
import sys
import time
import argparse
from pathlib import Path
from google import genai
from google.genai import types

# Import cấu hình
from config import WORK_DIR, GEMINI_API_KEY

# Đặt đúng model bạn đã sử dụng thành công trước đó
GEMINI_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-1.5-flash"

MAX_RETRIES = 4
VALID_DOMAINS = {"OFFICE", "TEACHER", "GENERAL"}
VALID_PRIORITY = {1, 2, 3, 4}

# Cấu hình file
IN_CSV = WORK_DIR / "words_enriched.csv"
OUT_CSV = WORK_DIR / "words_ai_completed.csv"
CACHE_FILE = WORK_DIR / "ai_cache.jsonl"

def setup_gemini():
    if not GEMINI_API_KEY:
        print("❌ LỖI: Chưa có GEMINI_API_KEY trong biến môi trường.")
        sys.exit(1)
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    system_instruction = """Bạn là một chuyên gia ngôn ngữ học và biên soạn học liệu. 
Nhiệm vụ: Đọc danh sách từ vựng tiếng Anh, phân loại và sinh câu ví dụ theo 2 bối cảnh công việc đặc thù. Trả về mảng JSON.

PHÂN LOẠI CHỦ ĐỀ (domain) & ĐỘ ƯU TIÊN (priority_group):
1. Nếu từ vựng phù hợp dùng trong công việc của Trợ lý, Thư ký, hoặc Chuyên viên Hành chính Nhân sự (báo cáo, số liệu, đối tác, phỏng vấn):
   -> domain = "OFFICE", priority_group = 1.
2. Nếu từ vựng phù hợp dùng trong giảng dạy môn Sinh học cấp THCS (lớp 6-9) hoặc quản lý học sinh trong lớp:
   -> domain = "TEACHER", priority_group = 2.
3. Nếu từ KHÔNG THỂ áp dụng tự nhiên vào 2 nhóm trên:
   -> domain = "GENERAL", priority_group = 4.

YÊU CẦU SINH VÍ DỤ (CỰC KỲ QUAN TRỌNG):
- Với nhóm "OFFICE": example_en BẮT BUỘC đặt trong ngữ cảnh văn phòng chuyên nghiệp (trợ lý báo cáo sếp, HR nói chuyện với ứng viên).
- Với nhóm "TEACHER": example_en BẮT BUỘC đặt trong ngữ cảnh lớp học Sinh học THCS.
- Với nhóm "GENERAL": Ví dụ giao tiếp thông thường.
- Câu ví dụ phải ngắn gọn (dưới 15 từ). example_vi là bản dịch tiếng Việt mượt mà.

Yêu cầu định dạng Output (JSON Array):
[
  {
    "word": "từ vựng gốc",
    "domain": "OFFICE/TEACHER/GENERAL",
    "priority_group": 1,
    "meaning_vi": "Nghĩa tiếng Việt ngắn gọn (giữ nguyên hoặc tự bổ sung nếu thiếu)",
    "ipa": "Phiên âm IPA (giữ nguyên hoặc tự bổ sung nếu thiếu)",
    "example_en": "Câu ví dụ tiếng Anh theo ngữ cảnh",
    "example_vi": "Dịch nghĩa câu ví dụ"
  }
]"""
    
    config = types.GenerateContentConfig(
        temperature=0.2, 
        response_mime_type="application/json",
        system_instruction=system_instruction,
    )
    return client, config

def load_cache():
    cache = {}
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    cache[data["word"]] = data
    return cache

def save_to_cache(results):
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        for res in results:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")

def validate_results(results, expected_words):
    """Giữ lại các bản ghi hợp lệ cho đúng các từ đã gửi; trả về (danh sách hợp lệ, số bản ghi bị loại)."""
    if not isinstance(results, list):
        return [], len(expected_words)
    good, seen = [], set()
    for res in results:
        if not isinstance(res, dict):
            continue
        word = res.get("word")
        if word not in expected_words or word in seen:
            continue
        try:
            res["priority_group"] = int(res.get("priority_group"))
        except (TypeError, ValueError):
            continue
        if res.get("domain") not in VALID_DOMAINS or res["priority_group"] not in VALID_PRIORITY:
            continue
        if not str(res.get("example_en", "")).strip() or not str(res.get("example_vi", "")).strip():
            continue
        seen.add(word)
        good.append(res)
    return good, len(expected_words) - len(good)


def call_gemini(client, config, prompt_text):
    """Gọi Gemini có thử lại (chờ tăng dần); dùng model dự phòng khi gặp lỗi 404."""
    model = GEMINI_MODEL
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt_text, config=config)
            return json.loads(response.text)
        except Exception as e:
            if "404" in str(e) and model != FALLBACK_MODEL:
                print(f"   🔄 SDK không định tuyến được {model}, đang dùng kênh dự phòng...")
                model = FALLBACK_MODEL
                continue
            wait = 5 * 2 ** (attempt - 1)
            print(f"   ❌ Lần {attempt}/{MAX_RETRIES} lỗi: {e}")
            if attempt == MAX_RETRIES:
                return None
            print(f"   Thử lại sau {wait}s...")
            time.sleep(wait)
    return None


def main():
    parser = argparse.ArgumentParser(description="Gọi Gemini để gắn domain và sinh ví dụ")
    parser.add_argument("--limit", type=int, default=0, help="Số lượng từ chạy thử (0 = chạy tất cả)")
    parser.add_argument("--batch-size", type=int, default=30, help="Số từ mỗi lần gọi API")
    args = parser.parse_args()

    client, config = setup_gemini()
    cache = load_cache()
    
    print(f"📦 Đã tải {len(cache)} từ từ bộ nhớ cache.")

    words_to_process = []
    all_rows = []
    with open(IN_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_rows.append(row)
            if row["word"] not in cache:
                words_to_process.append(row)

    if args.limit > 0:
        words_to_process = words_to_process[:args.limit]
        print(f"⚠️ CHẾ ĐỘ CHẠY THỬ: Chỉ xử lý {args.limit} từ.")

    print(f"🚀 Bắt đầu xử lý AI cho {len(words_to_process)} từ (Batch size: {args.batch_size})...\n")

    for i in range(0, len(words_to_process), args.batch_size):
        batch = words_to_process[i:i + args.batch_size]
        
        prompt_data = []
        for w in batch:
            prompt_data.append({
                "word": w["word"],
                "meaning_vi_current": w["meaning_vi"],
                "ipa_current": w["ipa"]
            })
            
        prompt_text = "Hãy xử lý danh sách từ sau:\n" + json.dumps(prompt_data, ensure_ascii=False, indent=2)
        
        print(f"⏳ Đang gọi Gemini batch {i//args.batch_size + 1} (từ {i+1} đến {min(i+args.batch_size, len(words_to_process))})...")
        
        results = call_gemini(client, config, prompt_text)
        if results is None:
            print("   ⚠️ Bỏ qua batch này sau nhiều lần lỗi; chạy lại script để xử lý tiếp (cache được giữ).")
            continue

        good, rejected = validate_results(results, {w["word"] for w in batch})
        save_to_cache(good)
        for res in good:
            cache[res["word"]] = res
        print(f"   ✅ Hợp lệ {len(good)} từ" + (f", loại {rejected} bản ghi lỗi (sẽ thử lại ở lần chạy sau)." if rejected else "."))
        time.sleep(1)

    print("\n💾 Đang ghi dữ liệu hoàn chỉnh ra CSV...")
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["word", "pos", "cefr", "frequency", "domain", "priority_group", "meaning_vi", "ipa", "example_en", "example_vi"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in all_rows:
            w = row["word"]
            if w in cache:
                c = cache[w]
                writer.writerow({
                    "word": w,
                    "pos": row["pos"],
                    "cefr": row["cefr"],
                    "frequency": row["frequency"],
                    "domain": c.get("domain", "GENERAL"),
                    "priority_group": c.get("priority_group", 4),
                    "meaning_vi": c.get("meaning_vi") or row["meaning_vi"],
                    "ipa": c.get("ipa") or row["ipa"],
                    "example_en": c.get("example_en", ""),
                    "example_vi": c.get("example_vi", "")
                })
            else:
                writer.writerow({
                    "word": w, "pos": row["pos"], "cefr": row["cefr"], "frequency": row["frequency"],
                    "domain": "GENERAL", "priority_group": 4, "meaning_vi": row["meaning_vi"],
                    "ipa": row["ipa"], "example_en": row["example_en"], "example_vi": ""
                })

    missing = sum(1 for r in all_rows if r["word"] not in cache)
    if missing:
        print(f"⚠️ Còn {missing} từ chưa có kết quả AI (câu dịch ví dụ để trống); hãy chạy lại script.")
    print(f"🎉 Hoàn tất! File sẵn sàng tại: {OUT_CSV}")

if __name__ == "__main__":
    main()