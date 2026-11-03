"""Dịch từ vựng HSK 1-5 sang tiếng Việt bằng Gemini trong một lần chạy (có lưu cache, chạy lại sẽ tiếp tục).

Cách dùng (PowerShell):
    $env:GEMINI_API_KEY="khóa-của-bạn"
    python tools/translate_vocab.py --source E:\\complete-hsk-vocabulary
Tùy chọn: --levels 1 2 3 4 5, --model gemini-2.5-flash, --batch 25, --limit 50 (chạy thử), --dry-run
Kết quả lưu ở tools/hsk_vi_cache.json; sau đó chạy tools/import_hsk_vocab.py để nạp vào chinese_mastery.db.
"""
import argparse
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = Path(__file__).resolve().parent / "hsk_vi_cache.json"
DB_PATH = ROOT / "chinese_mastery.db"
DEFAULT_SOURCE = Path(r"E:\complete-hsk-vocabulary")
DEFAULT_MODEL = "gemini-2.5-flash"
FIELDS = ("hanviet", "meaning_vi", "example_zh", "example_pinyin", "example_vi")

PROMPT = """Bạn là giáo viên tiếng Trung cho người Việt. Với mỗi từ HSK dưới đây, hãy trả về JSON.
Quy tắc:
- hanviet: âm Hán Việt, viết hoa chữ cái đầu (vd 爱 -> "Ái"); nếu từ không có âm Hán Việt tự nhiên thì để chuỗi rỗng.
- meaning_vi: nghĩa tiếng Việt ngắn gọn, tự nhiên (1-3 nghĩa chính, tối đa 80 ký tự), dịch từ nghĩa tiếng Anh cho sẵn.
- example_zh: MỘT câu ví dụ đơn giản, đúng ngữ pháp, dùng chính xác từ đó (nguyên văn chữ giản thể), độ khó phù hợp HSK, 6-18 chữ.
- example_pinyin: pinyin có dấu thanh của câu ví dụ.
- example_vi: bản dịch tiếng Việt tự nhiên của câu ví dụ.
Chỉ trả về một mảng JSON, mỗi phần tử có đúng các khóa: hanzi, hanviet, meaning_vi, example_zh, example_pinyin, example_vi.
Giữ nguyên thứ tự và giá trị hanzi như đầu vào.

Danh sách từ (hanzi | pinyin | nghĩa tiếng Anh):
{lines}
"""


def load_source(source, levels):
    words = []
    for level in levels:
        path = Path(source) / "wordlists" / "exclusive" / "old" / f"{level}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data:
            form = entry["forms"][0]
            words.append({
                "hanzi": entry["simplified"],
                "traditional": form.get("traditional") or "",
                "pinyin": form["transcriptions"]["pinyin"],
                "english": "; ".join(form.get("meanings", []))[:200],
                "level": level,
                "frequency": entry.get("frequency", 10**9),
                "pos": entry.get("pos", []),
            })
    return words


def existing_hanzi():
    if not DB_PATH.exists():
        return set()
    conn = sqlite3.connect(DB_PATH)
    try:
        return {row[0] for row in conn.execute("SELECT hanzi FROM vocab")}
    finally:
        conn.close()


def load_cache():
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {"words": {}}


def save_cache(cache):
    tmp = CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(CACHE_PATH)


def validate(word, item):
    """Trả về dict đã làm sạch hoặc None nếu kết quả dịch không dùng được."""
    if not isinstance(item, dict) or item.get("hanzi") != word["hanzi"]:
        return None
    clean = {k: str(item.get(k) or "").strip() for k in FIELDS}
    if not clean["meaning_vi"] or not clean["example_vi"] or not clean["example_pinyin"]:
        return None
    if word["hanzi"] not in clean["example_zh"]:
        return None
    return clean


def call_gemini(client, model, batch, retries=5):
    from google.genai import types

    lines = "\n".join(f"{w['hanzi']} | {w['pinyin']} | {w['english']}" for w in batch)
    delay = 5
    for attempt in range(1, retries + 1):
        try:
            response = client.models.generate_content(
                model=model, contents=PROMPT.format(lines=lines),
                config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.3))
            data = json.loads(response.text)
            if isinstance(data, list):
                return data
            raise ValueError("phản hồi không phải mảng JSON")
        except Exception as exc:  # lỗi mạng, giới hạn tốc độ, JSON hỏng...
            print(f"  lần {attempt}/{retries} lỗi: {exc}", file=sys.stderr)
            time.sleep(delay)
            delay = min(delay * 2, 60)
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--levels", type=int, nargs="+", default=[1, 2, 3, 4, 5])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--batch", type=int, default=25)
    parser.add_argument("--limit", type=int, default=0, help="chỉ dịch tối đa N từ (để chạy thử)")
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--passes", type=int, default=3, help="số vòng thử lại cho các từ bị lỗi")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    skip = existing_hanzi()
    cache = load_cache()
    words = [w for w in load_source(args.source, args.levels) if w["hanzi"] not in skip]
    for w in words:  # luôn cập nhật metadata để import đúng thứ tự
        cache["words"].setdefault(w["hanzi"], {})["meta"] = {
            k: w[k] for k in ("traditional", "pinyin", "level", "frequency", "pos")}
    todo = [w for w in words if "vi" not in cache["words"][w["hanzi"]]]
    done = len(words) - len(todo)
    if args.limit:
        todo = todo[:args.limit]
    print(f"Nguồn: {len(words)} từ mới (bỏ {len(skip)} từ đã có trong DB) · đã dịch {done} · lần này dịch {len(todo)}")
    if args.dry_run:
        if todo:
            print(PROMPT.format(lines="\n".join(f"{w['hanzi']} | {w['pinyin']} | {w['english']}" for w in todo[:3])))
        return
    if not todo:
        save_cache(cache)
        print("Không còn từ nào cần dịch.")
        return
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Thiếu biến môi trường GEMINI_API_KEY.")
    from google import genai

    client = genai.Client(api_key=api_key)
    for round_no in range(1, args.passes + 1):
        pending = [w for w in todo if "vi" not in cache["words"][w["hanzi"]]]
        if not pending:
            break
        print(f"Vòng {round_no}: {len(pending)} từ")
        for start in range(0, len(pending), args.batch):
            batch = pending[start:start + args.batch]
            results = {item.get("hanzi"): item
                       for item in call_gemini(client, args.model, batch) if isinstance(item, dict)}
            ok = 0
            for w in batch:
                clean = validate(w, results.get(w["hanzi"]))
                if clean:
                    cache["words"][w["hanzi"]]["vi"] = clean
                    ok += 1
            save_cache(cache)
            print(f"  {start + len(batch)}/{len(pending)}: nhận {ok}/{len(batch)}")
            time.sleep(args.sleep)
    left = [w["hanzi"] for w in todo if "vi" not in cache["words"][w["hanzi"]]]
    print(f"Xong. Còn {len(left)} từ chưa dịch được" + (f": {' '.join(left[:30])}" if left else "."))


if __name__ == "__main__":
    main()
