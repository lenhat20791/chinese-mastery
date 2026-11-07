# Phiên 0 — INDEX & Navigation Guide

## 📚 Tài Liệu Phiên 0

| File | Mục Đích | Kích Thước | Dùng Khi |
|------|---------|----------|---------|
| [PHIEN_0_SUMMARY.md](PHIEN_0_SUMMARY.md) | 📌 Tóm tắt điều hành | 10.6 KB | **Bắt đầu ở đây** — overview toàn bộ |
| [PHIEN_0_QUICK_REF.md](PHIEN_0_QUICK_REF.md) | ⚡ Lookup nhanh hàm | 6.2 KB | Cần tìm hàm/tham số nhanh |
| [PHIEN_0_DATAFLOW.md](PHIEN_0_DATAFLOW.md) | 📊 Diagram & flow | 14.1 KB | Debug flow, understand data movement |
| [PHIEN_0_SURVEY.md](PHIEN_0_SURVEY.md) | 📋 Khảo sát chi tiết | 16.4 KB | Deep dive, reference toàn diện |
| [PHIEN_0_ROADMAP.md](PHIEN_0_ROADMAP.md) | 🗺️ Kế hoạch 5 phiên | 8.4 KB | Lên kế hoạch phiên tiếp theo |

---

## 🎯 Quick Navigation

### Tôi muốn...

#### 📖 **Hiểu tổng quát Phiên 0**
→ Đọc [PHIEN_0_SUMMARY.md](PHIEN_0_SUMMARY.md) (10 phút)

#### ⚡ **Tìm nhanh hàm `settle()`**
→ Xem [PHIEN_0_QUICK_REF.md](PHIEN_0_QUICK_REF.md) → Section "Game Core Functions"

#### 🔍 **Debug luồng dữ liệu Quẻ Bói**
→ Xem [PHIEN_0_DATAFLOW.md](PHIEN_0_DATAFLOW.md) → Section "Minigames & Settlement"

#### 🗄️ **Hiểu schema DB game_artifacts**
→ Xem [PHIEN_0_SURVEY.md](PHIEN_0_SURVEY.md) → Section III "game_artifacts"

#### 📍 **Tìm call sites của apply_changes()**
→ Xem [PHIEN_0_DATAFLOW.md](PHIEN_0_DATAFLOW.md) → Section "Market Actions Flow" 

#### 🚀 **Chuẩn bị Phiên 1 (Settle Audit)**
→ Xem [PHIEN_0_ROADMAP.md](PHIEN_0_ROADMAP.md) → Section "Phiên 1"

#### 💾 **Lưu ý cần migration**
→ Xem [PHIEN_0_SURVEY.md](PHIEN_0_SURVEY.md) → Section VI "Những Thay Đổi Cần Migration"

#### 📈 **Xem timeline 5 phiên**
→ Xem [PHIEN_0_ROADMAP.md](PHIEN_0_ROADMAP.md) → Section "Timeline & Dependencies"

---

## 📍 Tọa Độ Hàm Chính

| Hàm | File | Line | Chức Năng |
|-----|------|------|----------|
| `settle()` | game_core.py | 556 | Chốt lượt, tính LS, unlock huy hiệu |
| `apply_changes()` | game_core.py | 254 | Ghi DB atomically |
| `discard_item()` | game_core.py | 489 | Vứt bỏ vật phẩm |
| `get_state()` | game_core.py | 148 | Load/cache state từ DB |
| `resolve_fortune()` | game_core.py | ~410 | Chốt quẻ, thêm buff, streak |
| `craft()` | game_core.py | ~450 | Chế tạo pháp bảo |
| `check_achievements()` | game_core.py | 580 | Unlock huy hiệu |
| `render_fortune()` | game_minigames.py | 21 | Render quẻ bói |
| `render_match()` | game_minigames.py | 70+ | Render ghép bài |
| `render_sentence()` | game_minigames.py | 300+ | Render đối câu |
| `_render_market()` | cultivation_tab.py | 130 | Render phường thị |
| `_render_home()` | cultivation_tab.py | 72 | Render trang chủ |

---

## 🗄️ Database Schema Quick View

### Core Tables (Bắt Buộc)
```
game_profile(user_id)
  ├─ linh_thach: int
  ├─ equipped_title: str
  ├─ pity_mid, pity_high: int
  ├─ fortune_streak, fortune_last_day: int, date
  
game_inventory(user_id, item_code)
  └─ qty: int

game_artifacts(id, user_id)
  ├─ recipe_code: str
  ├─ quality: 0-2 (Hạ/Trung/Thượng)
  └─ upgrade: 0-9

game_fortune(user_id, day)
  ├─ vocab_id: int
  ├─ tier: "Đại Cát" | "Cát" | "Bình"
  ├─ status: "pending" | "ok" | "fail"
  └─ buff: "ls:20" | "shield:2" | "drop:40"

game_achievements(user_id, code)
  └─ unlocked_at: timestamp

game_counters(user_id, key)
  ├─ key: "equip_1" | "equip_2" | "answers_correct" | "crafts" | ...
  └─ value: int

game_log(id, user_id, ts, kind, text)
  └─ Giữ 300 log cuối mỗi user
```

### NEW (Cần Migration)
```
game_techniques(id, user_id, tech_id)
game_dan_dien(user_id, equipped_json)
```

---

## 🔗 Connection Points (7 Điểm Nối)

```
1. Quẻ Bối
   game_minigames::_fortune_answer()
   → core::resolve_fortune()
   → game_fortune table

2. Ghép Bài / Đối Câu
   game_minigames::_match_next() / _sent_next()
   → core::settle()
   → game_profile, game_achievements, game_log tables

3. Mua Bí Phương
   cultivation_tab::_cb_buy()
   → core::buy_recipe()
   → game_recipes table

4. Chế Tạo
   cultivation_tab::_cb_craft()
   → core::craft()
   → game_artifacts, game_inventory tables

5. Trang Bị
   cultivation_tab::_cb_equip()
   → core::equip()
   → game_counters table

6. Vứt Bỏ
   cultivation_tab::_cb_discard()
   → core::discard_item()
   → game_inventory table

7. Nâng Cấp / Bán
   cultivation_tab::_cb_upgrade() / _cb_sell()
   → core::upgrade() / sell_artifact()
   → game_artifacts, game_inventory tables
```

---

## 🎯 Key Formulas

### Economy
```python
ls_earned = base_ls * ECON_SCALE^idx * play_multiplier(plays) * (1 + buff%)
play_multiplier(plays):
  0-9: 1.0
  10-29: 0.4
  30+: 0.1
```

### Achievement
```python
unlock_badge(badge_line["base"], tier):
  if counter_value >= badge_line["tiers"][tier]
```

### Craft Quality
```python
roll_quality(odds, pity_mid, pity_high):
  if pity_high >= 11: return 2 (Thượng)
  elif pity_mid >= 5: return 1 or 2
  else: return 0, 1, or 2 (normal)
```

---

## 🔄 Atomic DB Pattern

```python
def apply_changes(ls=0, items=None, incr=None, maxes=None, log=None, plays=0, extra=None):
    # Build SQL batch
    statements = [
        "UPDATE game_profile SET linh_thach = ...",
        "INSERT INTO game_inventory ... ON CONFLICT ...",
        "INSERT INTO game_counters ... ON CONFLICT ...",
        # ... more
    ]
    
    # Execute atomically
    get_user_db().batch(statements)
    
    # Reload state from DB
    return get_state(force=True)
```

**Rule**: Luôn `get_state(force=True)` sau khi apply_changes()

---

## 🚀 Phiên Tiếp Theo

### Phiên 1 — Settle Audit
- Verify settle() call sites (2-3 giờ)
- Check return value handling
- Ensure achievement toast

### Phiên 2 — Market Audit
- Verify market actions → apply_changes() (3-4 giờ)
- Check DB consistency

### Phiên 3 — Migrate Techniques
- Create game_techniques table
- Persist tech_farmed/tech_equipped to DB
- Update _load(), apply_changes() (4-5 giờ)
- 🔴 **CRITICAL** — data loss risk

### Phiên 4 — Optimize Badges
- Check achievement unlock logic
- Verify badge tiers & rewards (2 giờ)

### Phiên 5 — Optimize Fortune
- Check fortune streak continuity
- Verify buff application window (2 giờ)

---

## 📝 Cheat Sheet

### Check if fortune.buff is active
```python
if state["fortune"] and state["fortune"]["status"] == "ok":
    buff = parse_buff(state["fortune"]["buff"])  # → (code, value)
```

### Get all equipped artifacts
```python
artifacts = core.equipped_artifacts(state)
# → [{"id": ..., "recipe_code": "...", "quality": 0-2, "upgrade": 0-9}, ...]
```

### Calculate LS reward
```python
ls = core.reward_ls(base_ls, mult, state, idx_scale)
# = base_ls * idx_scale * play_mult * (1 + buff_ls/100)
```

### List owned recipes
```python
owned_recipes = [r for r in cfg.RECIPES if r["code"] in state["recipes"]]
```

### Check realm info
```python
realm = core.realm_info(words_learned)
# → {"stage": int, "idx": major, "sub": sub, "name": str, "next_need": int}
```

---

## 🐛 Common Issues & Locations

| Issue | File | Line | Fix |
|-------|------|------|-----|
| Artifact slot mismatch | game_counters equip_1/2 | N/A | Validate ID references valid artifact |
| Pity not tracking | game_profile pity_mid/high | ~420 | Ensure roll_quality() updates pity |
| Buff expired | game_fortune.buff with old day | ~410 | Check day == today() in resolve_fortune |
| Achievement not unlock | game_achievements | ~580 | Check counter_value() threshold |
| Inventory overload | game_inventory qty | ~120 | Paging in UI, cleanup old items |
| Session state lost | st.session_state | N/A | Move tech_farmed/equipped to DB |

---

## 📞 Quick Help

**Q: Hàm discard_item() ở đâu?**
A: game_core.py line 489, gọi từ cultivation_tab.py _cb_discard()

**Q: Settle() trả về gì?**
A: (ls_earned, mult, new_badges_list) — xem game_minigames.py line 300+

**Q: Làm sao để thêm item vào inventory?**
A: apply_changes(items={"item_code": qty}) → game_inventory

**Q: Buff áp dụng như thế nào?**
A: reward_ls() × (1 + buff_value/100) — xem game_core.py line 374

**Q: Phiên 1 nên làm gì trước?**
A: Xem PHIEN_0_ROADMAP.md → "Phiên 1 — Tasks"

---

## 🎬 How to Use These Documents

### For Developers
1. Start with **PHIEN_0_SUMMARY.md** (overview)
2. Bookmark **PHIEN_0_QUICK_REF.md** (daily use)
3. Use **PHIEN_0_DATAFLOW.md** (when debugging)
4. Keep **PHIEN_0_SURVEY.md** (for detailed reference)

### For Project Managers
1. Read **PHIEN_0_SUMMARY.md** (status)
2. Check **PHIEN_0_ROADMAP.md** (timeline)

### For New Team Members
1. Start with **PHIEN_0_SUMMARY.md** (30 min)
2. Deep dive **PHIEN_0_SURVEY.md** (2 hours)
3. Reference **PHIEN_0_QUICK_REF.md** (as needed)

---

**Created**: Nov 7, 2026  
**Phiên 0 Status**: ✅ COMPLETE  
**Next**: Phiên 1 (Settle Audit) or `/continue`

---

[← Back to Chinese Mastery Repo](README.md)
