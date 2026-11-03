"""Nạp các từ đã dịch (tools/hsk_vi_cache.json) vào bảng vocab của chinese_mastery.db.

- Chỉ nhận từ đã có bản dịch; chạy lại nhiều lần an toàn (bỏ qua từ đã có theo chữ Hán).
- Từ mới nằm cuối lộ trình: study_day tiếp nối sau ngày cuối hiện có, 4 từ/ngày, xếp theo (HSK, tần suất).
- Sau khi import hãy commit chinese_mastery.db (đây là lúc dữ liệu từ vựng thay đổi).

    python tools/import_hsk_vocab.py [--dry-run] [--per-day 4]
"""
import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_PATH = Path(__file__).resolve().parent / "hsk_vi_cache.json"
DB_PATH = ROOT / "chinese_mastery.db"
DOMAIN = "HSK_OPEN"
PRIORITY_GROUP = 4


def build_rows(cache, existing, start_id, start_day, per_day):
    items = [(hanzi, data) for hanzi, data in cache["words"].items()
             if "vi" in data and "meta" in data and hanzi not in existing]
    items.sort(key=lambda kv: (kv[1]["meta"]["level"], kv[1]["meta"]["frequency"], kv[0]))
    rows = []
    for n, (hanzi, data) in enumerate(items):
        meta, vi = data["meta"], data["vi"]
        day = start_day + n // per_day
        example = vi["example_zh"]
        hanviet = vi["hanviet"][:1].upper() + vi["hanviet"][1:]
        rows.append((
            start_id + n, hanzi, meta["traditional"] or hanzi, meta["pinyin"], hanviet, vi["meaning_vi"], DOMAIN,
            meta["level"], day, (day - 1) // 10 + 1, example, vi["example_pinyin"], vi["example_vi"],
            example.replace(hanzi, " ______ ", 1), None, PRIORITY_GROUP,
        ))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--per-day", type=int, default=4)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    conn = sqlite3.connect(DB_PATH)
    existing = {r[0] for r in conn.execute("SELECT hanzi FROM vocab")}
    max_id, max_day = conn.execute("SELECT COALESCE(MAX(id), 0), COALESCE(MAX(study_day), 0) FROM vocab").fetchone()
    last_day_count = conn.execute("SELECT COUNT(*) FROM vocab WHERE study_day = ?", (max_day,)).fetchone()[0]
    start_day = max_day + 1 if last_day_count >= args.per_day else max_day
    rows = build_rows(cache, existing, max_id + 1, start_day, args.per_day)
    print(f"Sẽ thêm {len(rows)} từ (ngày {start_day} -> {rows[-1][8] if rows else start_day}).")
    if args.dry_run or not rows:
        conn.close()
        return
    conn.executemany(
        "INSERT INTO vocab (id, hanzi, traditional, pinyin, hanviet, meaning_vi, domain, hsk_level, study_day, "
        "stage_10d, example_zh, example_pinyin, example_vi, example_cloze, chiet_tu, priority_group) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
    conn.commit()
    total = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
    conn.close()
    print(f"Đã thêm {len(rows)} từ. Tổng số từ hiện có: {total}.")


if __name__ == "__main__":
    main()
