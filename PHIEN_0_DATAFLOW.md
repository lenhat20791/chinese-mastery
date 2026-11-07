# Phiên 0 — Ánh Xạ Luồng Dữ Liệu (Data Flow Map)

## 📊 Luồng Dữ Liệu Chi Tiết: 4 File Chính

```
┌─────────────────────────────────────────────────────────────────────┐
│                    cultivation_tab.py                               │
│  render_cultivation() → _render_home/market/techniques/badges       │
└─────────────────────────────────────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                ▼                ▼                ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │ 🏯 Home      │  │ 🏪 Market    │  │ 📜 Techniques│
        │ _render_home │  │_render_market│  │ _render_tech │
        │              │  │              │  │              │
        │ get_state()  │  │ get_state()  │  │session_state │
        │ player_stats │  │ buy_recipe   │  │ tech_farmed  │
        │ equipped_art │  │ craft()      │  │ tech_equipped│
        │              │  │ equip()      │  │ (⚠️ no DB)   │
        │              │  │ discard_item │  │              │
        │              │  │              │  │              │
        └──────────────┘  └──────────────┘  └──────────────┘
                │                │
                └────────────────┼────────────────────┐
                                 ▼                     ▼
                         ┌─────────────────┐  ┌──────────────┐
                         │ game_config.py  │  │game_core.py  │
                         │                 │  │              │
                         │ CFG VALUES:     │  │ Core Logic:  │
                         │ ECON_SCALE      │  │              │
                         │ DAILY_*         │  │ get_state()  │
                         │ RECIPES         │  │ apply_changes│
                         │ ARTIFACTS       │  │ settle()     │
                         │ ITEMS           │  │ resolve_fort │
                         │ BADGES          │  │ craft()      │
                         │ ...             │  │ equip()      │
                         │                 │  │ discard_item │
                         └─────────────────┘  │ check_achiev │
                                 ▲             │              │
                                 │             └──────────────┘
                                 │                      │
                                 └──────────────────────┘
                                        │
                                        ▼
                        ┌────────────────────────────────┐
                        │       USER DATABASE (DB)       │
                        │  sqlite3 / Turso (HTTP)        │
                        │                                │
                        │ ✓ game_profile                │
                        │ ✓ game_daily                  │
                        │ ✓ game_inventory              │
                        │ ✓ game_recipes                │
                        │ ✓ game_artifacts              │
                        │ ✓ game_fortune                │
                        │ ✓ game_achievements           │
                        │ ✓ game_counters               │
                        │ ✓ game_log                    │
                        │ ⚠️ game_techniques (MISSING)  │
                        │                                │
                        └────────────────────────────────┘
```

---

## 🎮 Minigames & Settlement

```
┌─────────────────────────────────────────┐
│      game_minigames.py                  │
│  render_fortune()                       │
│  render_match()                         │
│  render_sentence()                      │
│                                         │
│ ┌────────────────────────────────────┐ │
│ │ Lưu state trong session:           │ │
│ │ st.session_state.g_match           │ │
│ │ st.session_state.g_sent            │ │
│ │                                    │ │
│ │ Khi xong round:                    │ │
│ │  → collect results                 │ │
│ │  → gọi core.settle(...)            │ │
│ │  → apply_changes() → DB            │ │
│ │  → UI re-render                    │ │
│ └────────────────────────────────────┘ │
└─────────────────────────────────────────┘
            │
            │ gọi
            ▼
┌─────────────────────────────────────────┐
│  game_core.py::settle()                 │
│                                         │
│  Input:                                 │
│    base_ls: int                         │
│    idx_scale: float                     │
│    words_learned: int                   │
│    results: [(vocab_id, ok), ...]      │
│    incr, maxes, items, log              │
│                                         │
│  Logic:                                 │
│  1. mult = play_multiplier(plays)       │
│  2. ls = base_ls * idx * mult * buff    │
│  3. record_review_batch(results)  →DB   │
│  4. apply_changes(ls, items, incr...)   │
│  5. check_achievements(words_learned)   │
│                                         │
│  Output:                                │
│    (ls_earned, mult, new_badges)       │
│                                         │
│  Side Effects:                          │
│    - DB write via apply_changes()       │
│    - Session reload game_state          │
└─────────────────────────────────────────┘
```

---

## 💎 Market Actions Flow

```
User Action                  Callback               Core Function        DB
─────────────────            ────────────────       ─────────────────    ──

Buy Recipe     ──→  _cb_buy()  ──→  buy_recipe()  ──→  apply_changes()  ──→  game_recipes
                                                        (+incr= log)          game_log

Craft          ──→  _cb_craft() ──→  craft()  ──→  apply_changes()  ──→  game_artifacts
                                                   (+ items, log,           game_inventory
                                                    pity update)           game_profile
                                                                           game_log

Equip          ──→  _cb_equip()  ──→  equip()  ──→  apply_changes()  ──→  game_counters
                                                     (equip_1/2)           (equip_X keys)

Unequip        ──→  _cb_unequip() ──→ unequip() ──→ apply_changes()  ──→  game_counters

Sell           ──→  _cb_sell()  ──→  sell_artifact() ──→ apply_changes()  ──→  game_artifacts
                                                         (DELETE)               (deleted)
                                                         (+ls, log)             game_profile
                                                                               game_log

Discard Item   ──→  _cb_discard() ──→ discard_item() ──→ apply_changes() ──→  game_inventory
                                                         (-qty)                 (qty updated)
                                                         (log)                  game_log

Upgrade        ──→  _cb_upgrade() ──→ upgrade()  ──→  apply_changes()  ──→  game_artifacts
                                                       (items, log)            (upgrade++)
                                                       (may fail)              game_inventory
                                                                               game_log
```

---

## 🏅 Achievement/Badge Flow

```
User plays minigame
    ↓
core.settle(..., words_learned, ...)
    ↓
    ├─→ apply_changes()  [DB write]
    │
    └─→ check_achievements(words_learned)
            ↓
            Mở khóa huy hiệu nếu đủ điều kiện:
              - counter_value(state, key) >= threshold
            ↓
            apply_changes(extra=[
              "INSERT INTO game_achievements (user_id, code) VALUES ..."
            ])
            ↓
            return [new_badge_codes]
            ↓
            _toast_new(badges)  [UI notification]
```

---

## ⚙️ apply_changes() — Atomic Transaction

```python
def apply_changes(ls=0, items=None, incr=None, maxes=None, log=None, plays=0, extra=None):
    """
    Lõi ghi dữ liệu vào DB. Luôn được theo sau bởi get_state(force=True).
    """
    state = get_state()
    statements = []
    
    # 1. Linh Thạch
    if ls != 0:
        statements.append(("UPDATE game_profile SET linh_thach = MAX(0, linh_thach + ?) ...", (ls, uid)))
        if ls > 0:
            incr["ls_earned"] = incr.get("ls_earned", 0) + ls
    
    # 2. Vật phẩm (item)
    for code, qty in (items or {}).items():
        statements.append((
            "INSERT INTO game_inventory ... ON CONFLICT ... DO UPDATE SET qty = qty + excluded.qty",
            (uid, code, qty)
        ))
    if items:
        statements.append(("DELETE FROM game_inventory WHERE user_id = ? AND qty <= 0", (uid,)))
    
    # 3. Counters tăng (incr)
    for key, amount in (incr or {}).items():
        statements.append((
            "INSERT INTO game_counters ... ON CONFLICT ... DO UPDATE SET value = value + excluded.value",
            (uid, key, amount)
        ))
    
    # 4. Counters MAX (maxes)
    for key, value in (maxes or {}).items():
        statements.append((
            "INSERT INTO game_counters ... ON CONFLICT ... DO UPDATE SET value = MAX(...)",
            (uid, key, value)
        ))
    
    # 5. Plays (lượt chơi hôm nay)
    if plays != 0:
        statements.append((
            "INSERT INTO game_daily ... ON CONFLICT ... DO UPDATE SET plays = plays + excluded.plays",
            (uid, day, plays)
        ))
    
    # 6. Log
    for kind, text in ([log] if isinstance(log, tuple) else (log or [])):
        statements.append(("INSERT INTO game_log (user_id, kind, text) VALUES (...)", (uid, kind, text)))
    if log:
        statements.append((
            "DELETE FROM game_log WHERE user_id = ? AND id <= "
            "(SELECT MAX(id) FROM game_log WHERE user_id = ?) - 300",
            (uid, uid)
        ))
    
    # 7. Extra (custom statements)
    statements.extend(extra or [])
    
    # Execute all atomically
    if statements:
        get_user_db().batch(statements)
    
    # Reload state from DB
    return get_state(force=True)
```

---

## 🔄 Session State vs DB State

| Data | Storage | Persistence | Ghi Chú |
|------|---------|-------------|--------|
| `game_state` | `st.session_state` | Per-page-load (cache) | Reload từ DB khi cần |
| `g_match` | `st.session_state` | Per-page-load | Reset mỗi lần quay lại Market |
| `g_sent` | `st.session_state` | Per-page-load | Reset mỗi lần quay lại |
| `tech_farmed` | `st.session_state` | Per-page-load | ⚠️ **CẦN DB** |
| `tech_equipped` | `st.session_state` | Per-page-load | ⚠️ **CẦN DB** |
| `game_profile` | DB | Persistent | Load mỗi lần gọi `get_state()` |
| `game_inventory` | DB | Persistent | Load mỗi lần gọi `get_state()` |
| `game_artifacts` | DB | Persistent | Load mỗi lần gọi `get_state()` |
| `game_log` | DB | Persistent (40 cuối) | Load mỗi lần gọi `get_state()` |

---

## 📍 Xác Định Vị Trí (Location Reference)

### game_core.py
- Line 135: `_load(uid)` — Tổng hợp dữ liệu từ DB
- Line 148: `get_state(force=False)` — Load/cache state
- Line 254: `apply_changes(...)` — Ghi DB atomically
- Line 374: `reward_ls(base, mult, state, idx_scale)` — Tính LS
- Line 400-500: Fortune & Market functions
- Line 489: **`discard_item(code)`** — Vứt bỏ vật phẩm
- Line 556: **`settle(base_ls, idx_scale, words_learned, ...)`** — Chốt lượt
- Line 580: `check_achievements(words_learned)` — Unlock huy hiệu

### game_minigames.py
- Line 1-30: Imports & setup
- Line 21: `render_fortune(ctx)` — Quẻ bói
- Line 19: `_fortune_answer(ok, word_id, ctx)` — Callback quẻ
- Line 70+: `render_match(ctx)` — Ghép bài
- Line 300+: `render_sentence(ctx)` — Đối câu

### cultivation_tab.py
- Line 1-60: Imports & helpers
- Line 72: `_render_home(state, ctx, user)` — Trang chủ
- Line 130-280: `_render_market(state, ctx)` — Phường thị
  - Recipes tab (180-220)
  - Craft tab (220-250)
  - Artifacts tab (250-290)
  - Inventory tab (290-320)
- Line 300-430: `_render_techniques(state, ctx)` — Công pháp (Session-only)
- Line 450+: `_render_badges(state, ctx)` — Huy hiệu

### game_config.py
- Line 1-50: Cảnh giới (Realms)
- Line 50-100: Kinh tế (Economy)
- Line 100-150: Trò chơi config
- Line 150-250: Pháp bảo (Artifacts) & Bí phương (Recipes)
- Line 250-300: Vật phẩm (Items)
- Line 300-350: Huy hiệu (Badges)

---

## 🎯 Summary: Connection Points

| # | Call Site | Callee | Effect | DB Table |
|---|-----------|--------|--------|----------|
| 1 | `_fortune_answer()` → `resolve_fortune()` | core | Buff + Streak | game_fortune, game_profile |
| 2 | `render_match/sentence()` → `settle()` | core | LS + Badges | game_profile, game_achievements, game_log |
| 3 | `_render_market()` → `buy_recipe()` | core | Bí phương | game_recipes, game_profile, game_log |
| 4 | `_render_market()` → `craft()` | core | Pháp bảo | game_artifacts, game_inventory, game_profile |
| 5 | `_render_market()` → `equip()` | core | Trang bị | game_counters |
| 6 | `_render_market()` → `discard_item()` | core | Vứt bỏ | game_inventory, game_log |
| 7 | `_render_market()` → `upgrade()` | core | Nâng cấp | game_artifacts, game_inventory |
| 8 | `check_achievements()` → badge unlock | core | Huy hiệu | game_achievements, game_log |

---

## 🚨 Critical Data Integrity Points

1. **apply_changes() ALWAYS called** → Ensures atomic DB writes
2. **get_state(force=True)** → Reload after any DB change
3. **play_multiplier()** → Based on game_daily.plays
4. **Pity tracking** → game_profile (pity_mid, pity_high) must match rolls
5. **Artifact slots** → game_counters (equip_1, equip_2) must reference valid game_artifacts.id
6. **Buff active window** → game_fortune.buff only active on same day (game_fortune.day)

---

**PHIÊN 0 HOÀN TẤT** ✓
