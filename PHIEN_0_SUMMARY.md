# Phiên 0 — HOÀN TẤT: Khảo Sát & Chốt Điểm Đấu Nối

## 📌 Executive Summary

### Phạm Vi Khảo Sát
Rà soát 4 file chính theo yêu cầu:
1. **game_minigames.py** — điều hướng/render game, luồng Quẻ Bói & Đối Câu
2. **game_core.py** — settle(), apply_changes(), discard_item() & trạng thái người chơi
3. **game_config.py** — cấu hình game, vật phẩm, công thức, quái/boss
4. **cultivation_tab.py** — điều hướng game, body/fragments, phường thị

### Kết Quả: Chốt Điểm

✅ **Tên hàm/khối code thật**:
- `core.settle()` — line 556 (chốt lượt, tính LS, unlock huy hiệu)
- `core.apply_changes()` — line 254 (ghi DB atomically)
- `core.discard_item()` — line 489 (vứt bỏ vật phẩm)
- `core.get_state()` — line 148 (load trạng thái + cache)

✅ **Nơi lưu dữ liệu**: 9 bảng trong user_data.db
- game_profile, game_daily, game_inventory, game_recipes, game_artifacts
- game_fortune, game_achievements, game_counters, game_log

✅ **Thay đổi cần migration**:
- Bảng mới: `game_techniques`, `game_dan_dien`
- Schema: userdb.py
- Chiến lược: Load techniques vào state, persist changes via apply_changes()

✅ **Thứ tự triển khai**: 5 phiên, độc lập và phụ thuộc rõ ràng

---

## 🔗 Connection Points (7 Điểm Nối)

| # | Tên | Từ File | Đến Hàm | Effect | DB Table |
|---|-----|---------|---------|--------|----------|
| 1 | Quẻ Bối | game_minigames | resolve_fortune | Buff + Streak | game_fortune, game_profile |
| 2 | Ghép Bài | game_minigames | settle() | LS + Badges | game_profile, game_achievements, game_log |
| 3 | Đối Câu | game_minigames | settle() | LS + Badges | (idem) |
| 4 | Mua Bí Phương | cultivation_tab | buy_recipe() | Mua thành công | game_recipes, game_log |
| 5 | Chế Tạo | cultivation_tab | craft() | Tạo pháp bảo | game_artifacts, game_inventory, game_profile |
| 6 | Trang Bị | cultivation_tab | equip() | Trang bị bảo | game_counters |
| 7 | Vứt Bỏ | cultivation_tab | discard_item() | Vứt bỏ đồ | game_inventory, game_log |

---

## 📊 Luồng Dữ Liệu (Data Flow)

### Game Loop (Minigames → Settle → DB)
```
User plays minigame (Fortune/Match/Sentence)
    ↓
  collect results: [(vocab_id, ok), ...]
    ↓
  core.settle(base_ls, idx_scale, words_learned, results, ...)
    ↓
    ├─ apply_changes(ls=earned, incr={"answers_correct": n}, items, log)
    │   ├─ batch SQL to game_profile, game_inventory, game_counters, game_log
    │   └─ get_state(force=True) → reload from DB
    │
    ├─ record_review_batch(results) → word_mastery table
    │
    └─ check_achievements(words_learned)
        ├─ check each BADGE_LINES
        ├─ unlock & log to game_achievements
        └─ return new_badges list
    
  return (ls_earned, mult, new_badges)
    ↓
  st.toast("✅ +N 💎") + _toast_new(badges)
```

### Market Loop (User Action → apply_changes → DB)
```
User clicks button (buy/craft/equip/discard/upgrade/sell)
    ↓
  callback: _cb_buy(), _cb_craft(), _cb_equip(), _cb_discard(), etc.
    ↓
  core.function() returns (ok, message) or (ok, message, quality)
    ↓
  apply_changes() [with appropriate params]
    ├─ batch SQL
    ├─ get_state(force=True)
    └─ return updated_state
    ↓
  _toast_result((ok, message))
    ↓
  UI re-renders from updated state
```

---

## 🗄️ Database Schema (9 Bảng)

| Bảng | Rows/User | Keys | Purpose | Write Via |
|-----|-----------|------|---------|-----------|
| game_profile | 1 | user_id | LS, equipment, pity, fortune streak | apply_changes, craft, resolve_fortune |
| game_daily | ~365 | (user_id, day) | Plays count per day | apply_changes (settle) |
| game_inventory | ~50 | (user_id, item_code) | Item quantities | apply_changes (craft, discard, upgrade) |
| game_recipes | ~9 | (user_id, recipe_code) | Owned recipes | apply_changes (buy_recipe) |
| game_artifacts | ~10 | id + user_id | Crafted weapons, quality, upgrade | apply_changes (craft, upgrade, equip) |
| game_fortune | 1/day | (user_id, day) | Daily fortune, buff, status | apply_changes (start, resolve) |
| game_achievements | ~30 | (user_id, code) | Unlocked badges | apply_changes (check_achievements) |
| game_counters | ~50 | (user_id, key) | equip_1/2, answers_correct, crafts, night_plays, etc. | apply_changes (any action) |
| game_log | 40 | id + user_id | Recent activity (oldest 40) | apply_changes (maintain via cleanup) |

**NEW (cần migration)**:
- game_techniques | ~50 | (user_id, tech_id) | Owned techniques
- game_dan_dien | 1 | user_id | Equipped techniques JSON

---

## 🎯 Luồng Gọi Hàm (Call Graph)

### settle() — Central Hub
```python
settle(base_ls, idx_scale, words_learned, results=(), incr=None, maxes=None, items=None, log=None, count_play=True, record=True)
├─ record_review_batch(results)  # → word_mastery table
├─ apply_changes(ls, items, incr, maxes, log, plays)
│  └─ get_state(force=True)  # → DB reload
├─ check_achievements(words_learned)
│  ├─ counter_value(state, counter)
│  ├─ apply_changes(extra=[badge insert])
│  └─ return [new_badge_codes]
└─ return (ls, mult, badges)
```

### apply_changes() — Atomic Writer
```python
apply_changes(ls, items, incr, maxes, log, plays, extra)
├─ build batch SQL statements
│  ├─ UPDATE game_profile (LS)
│  ├─ INSERT/UPDATE/DELETE game_inventory (items)
│  ├─ INSERT/UPDATE game_counters (incr: answers_correct, crafts, ...)
│  ├─ INSERT/UPDATE game_counters (maxes: max pity, max streak, ...)
│  ├─ INSERT/UPDATE game_daily (plays)
│  ├─ INSERT game_log (maintain 300 limit)
│  └─ [extra statements from caller]
├─ get_user_db().batch(statements)  # atomic
└─ return get_state(force=True)  # reload from DB
```

---

## ⚙️ Công Thức Quan Trọng

### Kinh Tế (Economy)
```python
# Linh Thạch nhận từ lượt
ls_earned = base_ls * scale(idx_scale) * play_multiplier(plays_today) * buff_mult

scale(idx) = 1.25 ^ idx

play_multiplier(plays):
  if plays < 10: return 1.0
  elif plays < 30: return 0.4
  else: return 0.1

buff_mult = 1 + buff_value("ls") / 100
```

### Chế Tạo (Crafting)
```python
# Bảo hiểm (Pity)
roll_quality(odds, pity_mid, pity_high):
  if pity_high + 1 >= 12:
    return 2  # guaranteed Thượng Phẩm
  elif pity_mid + 1 >= 6:
    return 1 or 2 (weighted)  # guaranteed Trung+
  else:
    return 0, 1, or 2 (normal odds)
```

### Huy Hiệu (Achievements)
```python
# Counter-based unlock
check_achievements(words_learned):
  for badge_line in BADGE_LINES:
    value = counter_value(state, badge_line["counter"])
    for tier in [0, 1, 2]:
      if value >= badge_line["tiers"][tier]:
        unlock(f"{badge_line['base']}_{tier}")
```

---

## 🚨 Critical Data Integrity Points

1. **apply_changes() atomicity**
   - Luôn batch SQL, luôn get_state(force=True) sau
   - Đảm bảo consistency

2. **Artifact slot validation**
   - game_counters.equip_1/2 phải reference valid game_artifacts.id
   - Có check khi equip/unequip

3. **Pity state tracking**
   - game_profile.pity_mid, pity_high phải match roll history
   - Reset pity khi quality >= threshold

4. **Play multiplier**
   - Dựa trên game_daily.plays (1 lượt = 1 plays++)
   - Không reset mid-day

5. **Buff window**
   - game_fortune.buff chỉ active khi status="ok" và day=today()
   - Buff hết hiệu lực ngày hôm sau

6. **Streak continuity**
   - fortune_streak++ nếu fortune_last_day = hôm qua
   - Nếu break, reset streak=1

---

## 🔄 State Management

### Session Cache (Per-Page-Load)
- `st.session_state.game_state` → caches core.get_state() result
- `st.session_state.g_match` → match game state (reset on page)
- `st.session_state.g_sent` → sentence game state (reset on page)
- `st.session_state.tech_farmed` → ⚠️ session-only (NEEDS DB)
- `st.session_state.tech_equipped` → ⚠️ session-only (NEEDS DB)

### DB Persistent State
- All tables in user_data.db
- Loaded fresh on every get_state(force=True)
- Updated atomically via apply_changes()

### Context (Calculated Real-Time)
```python
ctx = {
    "idx": realm_idx (0-15),
    "realm": realm_info(words_learned),
    "pool": current_vocab_pool,
    "mastery": mastery_dict,
    "words": total_learned,
    "bonuses": stat_bonuses(words, answers, streak),
}
```

---

## 📝 Documents Generated

### Phiên 0 Output Files
1. **PHIEN_0_SURVEY.md** (16.4 KB)
   - Toàn diện, mô tả từng hàm & bảng
   - Thích hợp cho reference

2. **PHIEN_0_QUICK_REF.md** (6.2 KB)
   - Quick lookup, tập trung hàm chính
   - Thích hợp lúc coding

3. **PHIEN_0_DATAFLOW.md** (14.1 KB)
   - Diagram & flow charts
   - Thích hợp lúc debug

4. **PHIEN_0_ROADMAP.md** (8.4 KB)
   - 5 phiên tiếp theo, tasks chi tiết
   - Thích hợp lúc lập kế hoạch

5. **PHIEN_0_SUMMARY.md** (This file)
   - Executive summary
   - Thích hợp lúc present

---

## ✨ Highlights: Những Điều Cần Chú Ý

### ✅ Tốt
- Luồng dữ liệu rõ ràng: action → callback → core func → apply_changes → DB → reload state
- apply_changes() atomic & well-designed
- settle() centralized, handles LS + achievements + log
- Config trong game_config.py, logic tách riêng

### ⚠️ Cần Cải Thiện
- **Kỹ Năng Công Pháp** (Techniques): lưu session-only, mất data khi reload
- **Hàm resolve_fortune()**: có complexity cao (streak + buff + pity)
- **Check_achievements()**: loop nested, có thể tối ưu
- **Inventory UI**: render từng item, có thể slow với item nhiều

### 🔴 Critical Issues
- Nếu `tech_equipped` là session-only mà user close browser → mất dữ liệu
- Cần migration ngay

---

## 🎬 Kết Luận & Tiếp Theo

### Phiên 0 Hoàn Tất ✓
- [x] Rà soát 4 file chính
- [x] Xác định hàm & khối code
- [x] Chốt vị trí DB & schema
- [x] Xác định luồng & điểm nối
- [x] Tạo roadmap 5 phiên

### Khuyến Nghị Tiếp Theo
**Phiên 1** (Settle Audit) — ~2-3 giờ
- Verify tất cả settle() call sites
- Ensure return value `(ls, mult, badges)` xử lý đúng
- Kiểm tra toast & achievements unlock

**Phiên 2** (Market Audit) — ~3-4 giờ
- Verify tất cả market actions gọi apply_changes()
- Kiểm tra DB state consistency

**Phiên 3** (Techniques Migration) — ~4-5 giờ
- Create game_techniques + game_dan_dien tables
- Update _load(), apply_changes(), _render_techniques()
- 🔴 CẦN NGAY (critical data loss risk)

---

## 📞 Support & Questions

Nếu có câu hỏi về:
- **Specific function**: Xem PHIEN_0_QUICK_REF.md (line reference)
- **Data flow**: Xem PHIEN_0_DATAFLOW.md (flow diagrams)
- **DB schema**: Xem PHIEN_0_SURVEY.md (Section III)
- **Next steps**: Xem PHIEN_0_ROADMAP.md (phiên tương ứng)

---

**PHIÊN 0 XONG ✓**

Sẵn sàng cho Phiên 1? → `/continue` hoặc `/st Phiên 1`
