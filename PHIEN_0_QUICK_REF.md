# Phiên 0 — Quick Reference: Hàm & Điểm Nối

## 🎮 Game Core Functions

### State & Load
```python
core.get_state(force=False)              # → Dict[uid, day, ls, inventory, recipes, artifacts, ...]
core.apply_changes(ls=0, items={}, ...) # → state (after DB write)
```

### Settle (Chốt Lượt)
```python
core.settle(base_ls, idx_scale, words_learned, results=(), incr=None, maxes=None, 
            items=None, log=None, count_play=True, record=True)
# → (ls_earned, mult, new_badges)
```

### Fortune (Quẻ Bói)
```python
core.draw_fortune(pool, mastery, pick_words)        # → (word, tier)
core.start_fortune(vocab_id, tier)                  # → state (DB)
core.resolve_fortune(correct, idx)                  # → state (DB, buff+streak)
core.active_buff(state)                             # → (code, value) or None
core.buff_value(state, code)                        # → int value
```

### Chế Tạo & Phường Thị
```python
core.buy_recipe(code, idx)              # → (ok, message)
core.buy_pill(idx)                      # → (ok, message)
core.craft(code, idx, use_pill=False)   # → (ok, message, quality)
core.upgrade(artifact_id)               # → (ok, message)
core.equip(artifact_id, idx, slot)      # → (ok, message)
core.unequip(slot)                      # → (ok, message)
core.sell_artifact(artifact_id)         # → (ok, message)
core.discard_item(code)                 # → (ok, message)
```

### Huy Hiệu
```python
core.check_achievements(words_learned)  # → [new_badge_codes]
core.all_titles()                       # → {code: name}
core.equip_title(code)                  # → DB
```

### Stats & Bonus
```python
core.player_stats(idx, artifacts, bonuses)   # → {atk, hp, crit}
core.stat_bonuses(words, answers, streak)    # → {crit, hp, atk, dao_tam}
core.equipped_artifacts(state)               # → [artifact_dict]
```

---

## 📍 Điểm Nối (Call Sites)

### 1️⃣ **Quẻ Bói** (`game_minigames.py::render_fortune`)
```python
def render_fortune(ctx):
    state = core.get_state()
    if state["fortune"] is None:
        word, tier = core.draw_fortune(...)
        state = core.start_fortune(...)
    
    # Khi user bấm:
    ok = ... # user answer
    state = core.resolve_fortune(ok, ctx["idx"])
    record_review_batch([(word_id, ok)])
```

### 2️⃣ **Ghép Bài** (`game_minigames.py::render_match`)
```python
# Khi hoàn thành:
ls, mult, badges = core.settle(
    base_ls=MATCH_PAIR_REWARD * len(matched),
    idx_scale=scale(ctx["idx"]),
    words_learned=ctx["words"],
    results=[(w_id, ok) for w_id, ok in results],
    incr={"answers_correct": correct_count},
    log=("match", f"...")
)
```

### 3️⃣ **Đối Câu** (`game_minigames.py::render_sentence`)
```python
# Tương tự match, khi xong:
ls, mult, badges = core.settle(
    base_ls=SENTENCE_REWARD * len(rounds),
    ...
)
```

### 4️⃣ **Phường Thị - Mua Bí Phương** (`cultivation_tab.py::_cb_buy`)
```python
def _cb_buy(code, idx):
    ok, msg = core.buy_recipe(code, idx)
    st.toast(("✅ " if ok else "⚠️ ") + msg)
```

### 5️⃣ **Phường Thị - Chế Tạo** (`cultivation_tab.py::_cb_craft`)
```python
def _cb_craft(code, idx, pill_key):
    ok, msg, quality = core.craft(code, idx, use_pill=...)
    st.toast(("✅ " if ok else "⚠️ ") + msg)
```

### 6️⃣ **Phường Thị - Trang Bị** (`cultivation_tab.py::_cb_equip`)
```python
def _cb_equip(artifact_id, idx, slot=None):
    ok, msg = core.equip(artifact_id, idx, slot)
    st.toast(("✅ " if ok else "⚠️ ") + msg)
```

### 7️⃣ **Phường Thị - Bán & Vứt Bỏ** (`cultivation_tab.py`)
```python
def _cb_sell(artifact_id):
    ok, msg = core.sell_artifact(artifact_id)
    st.toast(...)

def _cb_discard(code):
    ok, msg = core.discard_item(code)
    st.toast(...)
```

---

## 🗄️ DB Tables & Đọc Ghi

| Bảng | Đọc từ | Ghi vào | Hàm |
|-----|--------|---------|-----|
| game_profile | _load | apply_changes | settle, craft, upgrade, resolve_fortune |
| game_daily | _load | apply_changes | settle |
| game_inventory | _load | apply_changes | craft, buy_pill, discard_item, upgrade |
| game_recipes | _load | apply_changes | buy_recipe |
| game_artifacts | _load | apply_changes | craft, equip, unequip, sell_artifact, upgrade |
| game_fortune | _load | apply_changes | start_fortune, resolve_fortune |
| game_achievements | _load | apply_changes | check_achievements |
| game_counters | _load | apply_changes | (nhiều: equip_1/2, answers_correct, crafts, ...) |
| game_log | _load | apply_changes | settle, craft, buy_recipe, discard_item (giữ 300 log cuối) |

---

## 🔑 Key DB Columns

### game_profile
- `user_id`: khóa chính
- `linh_thach`: tiền game
- `pity_mid`: bảo hiểm Trung Phẩm (0-5)
- `pity_high`: bảo hiểm Thượng Phẩm (0-11)
- `fortune_streak`: ngày liên tiếp bói quẻ
- `fortune_last_day`: YYYY-MM-DD

### game_inventory
- `(user_id, item_code)`: khóa chính
- `qty`: số lượng (xóa nếu ≤ 0)

### game_artifacts
- `id`: khóa chính (autoincrement)
- `user_id, recipe_code, quality, upgrade`

### game_counters (đa mục)
- `(user_id, key)`: khóa chính
- key ∈ {equip_1, equip_2, answers_correct, crafts, upgrades, night_plays, ...}

### game_log (40 cuối)
- `(id)`: khóa chính
- `kind` ∈ {fortune, market, craft, match, sentence, hunt, ...}

---

## ⚠️ Công Thức Quan Trọng

```python
# Linh Thạch nhận từ một lượt
ls_earned = base_ls * idx_scale * play_multiplier(plays) * buff_multiplier

# Chỉ số cảnh giới
scale(idx) = 1.25 ^ idx

# Hệ số lượt (giảm dần sau 10 và 30 lượt)
play_multiplier(plays):
  if plays < 10: return 1.0
  if plays < 30: return 0.4
  return 0.1

# Bảo hiểm chế tạo
roll_quality(odds, pity_mid, pity_high):
  if pity_high + 1 >= 12: return 2  # Thượng Phẩm
  if pity_mid + 1 >= 6: return 1 or 2  # Trung+ Phẩm
  return 0, 1, or 2 (normal odds)
```

---

## 🚀 Deployment Checklist

- [ ] Phiên 1: Verify settle() call sites in minigames
- [ ] Phiên 2: Verify market actions (buy, craft, equip, discard)
- [ ] Phiên 3: Migrate tech/đan điền to DB
- [ ] Phiên 4: Optimize achievements
- [ ] Phiên 5: Optimize fortune/buff
