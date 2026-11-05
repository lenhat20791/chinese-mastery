import csv
import json
import time
from pathlib import Path
from google import genai
from google.genai import types

# Import cấu hình
from config import WORK_DIR, GEMINI_API_KEY

CSV_FILE = WORK_DIR / "words_ai_completed.csv"
GEMINI_MODEL = "gemini-3.5-flash-lite"

def main():
    if not GEMINI_API_KEY:
        print("❌ LỖI: Chưa có GEMINI_API_KEY trong biến môi trường.")
        return
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Đọc dữ liệu hiện tại
    rows = []
    missing_indices = []
    
    with open(CSV_FILE, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for i, row in enumerate(reader):
            rows.append(row)
            # Phát hiện từ bị khuyết IPA, Nghĩa, hoặc Ví dụ
            if not row["meaning_vi"].strip() or not row["ipa"].strip() or not row["example_en"].strip():
                missing_indices.append(i)
                
    print(f"🔍 Phát hiện {len(missing_indices)} từ bị khuyết dữ liệu. Đang tiến hành vá lỗi...")
    
    if not missing_indices:
        print("✅ Không có từ nào bị thiếu. File CSV đã hoàn hảo.")
        return

    # Lệnh ép AI cực kỳ khắt khe
    sys_prompt = """Bạn là chuyên gia ngôn ngữ học. Hãy điền BẮT BUỘC phần dữ liệu CÒN THIẾU (Phiên âm IPA, Nghĩa tiếng Việt, Câu ví dụ tiếng Anh) cho các từ vựng sau.
TUYỆT ĐỐI KHÔNG ĐƯỢC ĐỂ TRỐNG TRƯỜNG "ipa" VÀ "meaning_vi".
Trả về mảng JSON định dạng: 
[{"word": "từ gốc", "ipa": "phiên âm", "meaning_vi": "nghĩa ngắn gọn", "example_en": "ví dụ", "example_vi": "dịch ví dụ"}]"""
    
    config = types.GenerateContentConfig(
        temperature=0.1,
        response_mime_type="application/json",
        system_instruction=sys_prompt
    )
    
    batch_size = 30
    for i in range(0, len(missing_indices), batch_size):
        batch_idxs = missing_indices[i:i+batch_size]
        prompt_data = [
            {
                "word": rows[idx]["word"], 
                "ipa_hien_tai": rows[idx]["ipa"], 
                "nghia_hien_tai": rows[idx]["meaning_vi"],
                "chu_de": rows[idx]["domain"]
            } 
            for idx in batch_idxs
        ]
        
        print(f"⏳ Đang gọi AI vá lỗi batch {i//batch_size + 1} (gồm {len(batch_idxs)} từ)...")
        
        try:
            resp = client.models.generate_content(
                model=GEMINI_MODEL,
                contents="Hãy điền đủ IPA, nghĩa và ví dụ cho các từ sau:\n" + json.dumps(prompt_data, ensure_ascii=False),
                config=config
            )
            results = json.loads(resp.text)
            
            # Ghi đè dữ liệu mới vào bộ nhớ
            for res in results:
                word = res.get("word", "")
                for idx in batch_idxs:
                    if rows[idx]["word"] == word:
                        if res.get("ipa"): rows[idx]["ipa"] = res["ipa"]
                        if res.get("meaning_vi"): rows[idx]["meaning_vi"] = res["meaning_vi"]
                        if res.get("example_en"): rows[idx]["example_en"] = res["example_en"]
                        if res.get("example_vi"): rows[idx]["example_vi"] = res["example_vi"]
            
            print(f"   ✅ Đã vá xong {len(results)} từ.")
            time.sleep(1)
        except Exception as e:
            print(f"   ❌ Lỗi: {e}")
            time.sleep(5)
            
    # Ghi lại file CSV
    with open(CSV_FILE, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        
    print("\n🎉 Đã vá lỗi thành công toàn bộ file CSV!")

if __name__ == "__main__":
    main()