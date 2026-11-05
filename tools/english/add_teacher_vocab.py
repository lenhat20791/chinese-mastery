import argparse
import json
import math
import sqlite3
import time
from pathlib import Path

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, OUT_DB


GEMINI_MODEL = "gemini-3.5-flash-lite"
FALLBACK_MODEL = "gemini-1.5-flash"
MAX_RETRIES = 4
CEFR_LEVELS = {"A1", "A2", "B1", "B2", "C1", "C2"}
REQUIRED_WORDS = {
    "lesson plan",
    "assessment",
    "rubric",
    "feedback",
    "attendance",
    "assignment",
}


def build_prompt(required_words, existing_words, total_count):
    """Tạo yêu cầu bổ sung mục từ giáo viên, không lặp từ đã có trong DB."""
    required = sorted(required_words)
    return (
        "Bạn là chuyên gia biên soạn học liệu tiếng Anh cho giáo viên Sinh học THCS "
        "(lớp 6-9) tại Việt Nam.\n"
        f"Hãy trả về JSON array đúng {total_count} mục từ/cụm từ tiếng Anh hữu ích cho "
        "nghiệp vụ sư phạm và giao tiếp tự nhiên với học sinh.\n"
        "Bắt buộc có chính xác mỗi mục trong danh sách required_words; dùng đúng cách viết "
        "của mục từ, không bỏ hoặc thay thế. Các mục còn lại hãy bổ sung thuật ngữ lớp học "
        "hoặc câu giao tiếp giáo viên-học sinh; không trùng existing_words.\n"
        "Mỗi ví dụ tiếng Anh ngắn, tự nhiên, phù hợp THCS, dưới 15 từ; dịch tiếng Việt "
        "mượt và đúng ngữ cảnh. IPA dùng giọng Mỹ. CEFR chỉ chọn A1, A2, B1, B2, C1, C2.\n"
        "Trả về JSON thuần, không markdown. Mỗi object có đúng các trường:\n"
        '{"word":"...", "pos":"...", "cefr":"...", "meaning_vi":"...", '
        '"ipa":"...", "example_en":"...", "example_vi":"..."}\n\n'
        f"required_words: {json.dumps(required, ensure_ascii=False)}\n"
        f"existing_words (không được trả lại): {json.dumps(sorted(existing_words), ensure_ascii=False)}"
    )


def _generate_json(client, prompt):
    """Gọi Gemini theo cùng model, cấu hình JSON, retry và fallback đang dùng."""
    config = types.GenerateContentConfig(
        temperature=0.2,
        response_mime_type="application/json",
        system_instruction=(
            "Bạn tạo dữ liệu từ vựng chính xác, ưu tiên ngữ cảnh giảng dạy Sinh học THCS "
            "và giao tiếp tích cực, tôn trọng với học sinh."
        ),
    )
    model = GEMINI_MODEL
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=model, contents=prompt, config=config
            )
            return json.loads(response.text)
        except Exception as exc:
            if "404" in str(exc) and model != FALLBACK_MODEL:
                print(f"Gemini không nhận model {model}; chuyển sang model dự phòng đã dùng trước đây.")
                model = FALLBACK_MODEL
                continue
            if attempt == MAX_RETRIES:
                raise RuntimeError(
                    f"Gọi Gemini thất bại sau {MAX_RETRIES} lần ({type(exc).__name__})."
                ) from None
            wait = 5 * 2 ** (attempt - 1)
            print(f"Lần gọi Gemini {attempt}/{MAX_RETRIES} thất bại ({type(exc).__name__}); thử lại sau {wait}s.")
            time.sleep(wait)
    raise RuntimeError("Không nhận được kết quả từ Gemini.")


def validate_entries(results, required_words, existing_words, expected_count):
    """Kiểm tra output để chỉ ghi các mục mới, đúng schema và đủ số lượng."""
    if not isinstance(results, list):
        raise ValueError("Gemini phải trả về JSON array.")

    accepted = []
    seen = set()
    for row in results:
        if not isinstance(row, dict):
            continue
        word = str(row.get("word", "")).strip().lower()
        is_required = word in required_words
        if not word or word in seen or (word in existing_words and not is_required):
            print(f"Bỏ qua mục trống/trùng/đã có trong DB: {word!r}")
            continue
        try:
            if row.get("cefr") not in CEFR_LEVELS:
                raise ValueError(f"CEFR không hợp lệ cho {word!r}.")
            normalized = _normalize_row(row, word)
        except ValueError as exc:
            if is_required:
                raise
            print(f"Bỏ qua mục thừa không hợp lệ: {exc}")
            continue
        accepted.append(normalized)
        seen.add(word)

    missing = required_words - seen
    if missing:
        raise ValueError(f"Gemini chưa trả đủ từ bắt buộc: {', '.join(sorted(missing))}.")

    required_rows = [e for e in accepted if e["word"] in required_words]
    extras = [e for e in accepted if e["word"] not in required_words]
    return required_rows + extras[: max(expected_count - len(required_rows), 0)]


def _normalize_row(row, word):
    normalized = {
        "word": word,
        "cefr": row["cefr"],
        "meaning_vi": str(row.get("meaning_vi", "")).strip(),
        "ipa": str(row.get("ipa", "")).strip(),
        "example_en": str(row.get("example_en", "")).strip(),
        "example_vi": str(row.get("example_vi", "")).strip(),
    }
    if not all(normalized[key] for key in ("meaning_vi", "ipa", "example_en", "example_vi")):
        raise ValueError(f"Thiếu nghĩa, IPA hoặc ví dụ cho {word!r}.")
    if len(normalized["example_en"].split()) >= 15:
        raise ValueError(f"Ví dụ tiếng Anh quá dài cho {word!r}.")
    normalized["pos"] = str(row.get("pos", "")).strip()
    return normalized


def load_existing_words(db_path):
    with sqlite3.connect(db_path) as conn:
        return {
            row[0].strip().lower()
            for row in conn.execute("SELECT hanzi FROM vocab")
            if row[0]
        }


def insert_entries(db_path, entries):
    """Thêm các từ vào cuối lịch hiện có trong một transaction; không sửa dữ liệu cũ."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        existing = {
            row[0].strip().lower()
            for row in conn.execute("SELECT hanzi FROM vocab")
            if row[0]
        }
        duplicates = existing.intersection(entry["word"] for entry in entries)
        if duplicates:
            raise ValueError(
                "DB vừa thay đổi; không ghi để tránh trùng: " + ", ".join(sorted(duplicates))
            )

        max_day = conn.execute("SELECT COALESCE(MAX(study_day), 0) FROM vocab").fetchone()[0]
        rows = []
        for index, entry in enumerate(entries):
            study_day = max_day + index // 4 + 1
            rows.append((
                entry["word"], "", entry["ipa"], "", entry["meaning_vi"], "TEACHER",
                entry["cefr"], study_day, (study_day - 1) // 10 + 1,
                entry["example_en"], "", entry["example_vi"], "", "", 2,
            ))
        conn.executemany(
            """INSERT INTO vocab (
                hanzi, traditional, pinyin, hanviet, meaning_vi, domain, hsk_level,
                study_day, stage_10d, example_zh, example_pinyin, example_vi,
                example_cloze, chiet_tu, priority_group
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()
        return max_day + 1, max_day + math.ceil(len(entries) / 4)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Gọi Gemini tạo từ vựng sư phạm THCS và thêm vào english_mastery.db."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Ghi dữ liệu vào DB. Mặc định chỉ gọi API và xem trước, không sửa DB.",
    )
    parser.add_argument(
        "--database",
        type=Path,
        default=OUT_DB,
        help="Đường dẫn DB đích (mặc định: english_mastery.db trong project).",
    )
    args = parser.parse_args()

    if not args.database.is_file():
        parser.error(f"Không tìm thấy database: {args.database}")
    if not GEMINI_API_KEY:
        parser.error("Chưa có GEMINI_API_KEY trong biến môi trường.")

    existing_words = load_existing_words(args.database)
    missing_required = REQUIRED_WORDS - existing_words
    if not missing_required:
        print("Sáu thuật ngữ bắt buộc đã có trong DB; không gọi API và không thay đổi dữ liệu.")
        return

    total_count = math.ceil(len(missing_required) / 4) * 4
    print(f"Model: {GEMINI_MODEL}; từ bắt buộc còn thiếu: {len(missing_required)}.")
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = build_prompt(missing_required, existing_words, total_count + 4)
    results = _generate_json(client, prompt)
    entries = validate_entries(results, missing_required, existing_words, total_count)

    print(f"\nĐã kiểm tra {len(entries)} mục từ TEACHER:")
    for entry in entries:
        print(f"- {entry['word']} [{entry['cefr']}] — {entry['meaning_vi']}")
        print(f"  {entry['example_en']} — {entry['example_vi']}")

    if not args.apply:
        print("\nChế độ xem trước: DB chưa thay đổi. Chạy lại với --apply để ghi.")
        return

    first_day, last_day = insert_entries(args.database, entries)
    print(f"\nĐã thêm {len(entries)} từ vào ngày {first_day}-{last_day}; các bản ghi cũ không bị sửa.")


if __name__ == "__main__":
    main()
