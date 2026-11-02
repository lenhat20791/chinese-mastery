import urllib.request
import json
import sqlite3
import time
import os
from google import genai
from google.genai import types

# Đặt khóa qua biến môi trường GEMINI_API_KEY (không ghi cứng vào code)
API_KEY = os.environ["GEMINI_API_KEY"]
client = genai.Client(api_key=API_KEY)

DB_FILE = 'chinese_mastery.db'
DICT_URL = "https://raw.githubusercontent.com/skishore/makemeahanzi/master/dictionary.txt"
DICT_FILE = "makemehanzi_dict.txt"

PROMPT_SYSTEM = """
Bạn là chuyên gia ngôn ngữ học tiếng Trung.
Tôi sẽ cung cấp danh sách từ vựng, kèm theo CÁC THÀNH PHẦN CHỮ HÁN CHUẨN XÁC 100% được bóc tách từ từ điển gốc.
Nhiệm vụ của bạn là:
1. Gọi tên và giải thích ngắn gọn ý nghĩa của các thành phần/bộ thủ đó.
2. Sáng tác 1 câu chuyện ghi nhớ liên kết CÁC THÀNH PHẦN ĐÓ lại với nhau.

Đầu ra PHẢI LÀ MẢNG JSON, mỗi phần tử có cấu trúc:
{
    "id": <id>,
    "chiet_tu": {
        "components": [
            {"radical": "thành phần 1", "name": "tên tiếng việt", "meaning": "nghĩa"},
            {"radical": "thành phần 2", "name": "tên tiếng việt", "meaning": "nghĩa"}
        ],
        "story": "Câu chuyện..."
    }
}
TUYỆT ĐỐI CHỈ TRẢ VỀ JSON. KHÔNG ĐƯỢC TỰ BỊA THÊM BỘ THỦ NÀO KHÁC NGOÀI CÁC THÀNH PHẦN TÔI CUNG CẤP TRONG YÊU CẦU.
"""

def prepare_dictionary():
    if not os.path.exists(DICT_FILE):
        print("📥 Đang tải từ điển MakeMeHanzi (khoảng 3MB)...")
        urllib.request.urlretrieve(DICT_URL, DICT_FILE)
        print("✅ Tải hoàn tất!")

    hanzi_dict = {}
    with open(DICT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    data = json.loads(line)
                    char = data.get("character")
                    decomp = data.get("decomposition", "")
                    # Xóa các ký tự biểu diễn cấu trúc không cần thiết
                    for sc in "⿰⿱⿲⿳⿴⿵⿶⿷⿸⿹⿺⿻?":
                        decomp = decomp.replace(sc, "")
                    hanzi_dict[char] = decomp
                except:
                    pass
    return hanzi_dict

def rebuild_database():
    hanzi_dict = prepare_dictionary()
    
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Reset toàn bộ cột chiet_tu để làm lại từ đầu bằng bộ khung thép
    c.execute("UPDATE vocab SET chiet_tu = NULL")
    conn.commit()
    print("🧹 Đã dọn sạch dữ liệu cũ bị lỗi.")

    while True:
        c.execute("SELECT id, hanzi, meaning_vi FROM vocab WHERE chiet_tu IS NULL LIMIT 25")
        words = c.fetchall()
        
        if not words:
            print("🎉 HOÀN TẤT! 100% CƠ SỞ DỮ LIỆU ĐÃ ĐẠT CHUẨN HỌC THUẬT.")
            break

        print(f"⏳ Đang xử lý mẻ {len(words)} từ...")
        
        prompt_user = "Danh sách từ cần xử lý:\n"
        for w in words:
            w_id, hanzi, meaning = w
            prompt_user += f"- ID {w_id}: {hanzi} (Nghĩa: {meaning}).\n"
            # Ép AI dùng đúng bộ thủ từ điển gốc
            for char in hanzi:
                if char in hanzi_dict and hanzi_dict[char]:
                    prompt_user += f"  + Chữ '{char}' MẶC ĐỊNH gồm các thành phần: {hanzi_dict[char]}\n"

        try:
            response = client.models.generate_content(
                model='gemini-3.5-flash-lite',
                contents=prompt_user,
                config=types.GenerateContentConfig(
                    system_instruction=PROMPT_SYSTEM,
                    response_mime_type="application/json",
                    temperature=0.3 # Giảm độ sáng tạo để bám sát dữ liệu gốc
                )
            )
            
            data = json.loads(response.text)
            for item in data:
                chiet_tu_json = json.dumps(item["chiet_tu"], ensure_ascii=False)
                c.execute("UPDATE vocab SET chiet_tu = ? WHERE id = ?", (chiet_tu_json, item["id"]))
                
            conn.commit()
            print(f"✅ Xong {len(data)} từ.")
        except Exception as e:
            print("❌ Lỗi (Sẽ thử lại):", e)
            
        time.sleep(3)

    conn.close()

if __name__ == "__main__":
    rebuild_database()