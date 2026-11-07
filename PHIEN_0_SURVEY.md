# Phiên 0 — Khảo Sát & Chốt Điểm Đấu Nối

## I. OVERVIEW: Luồng Gọi Chính

### A. Điểm vào từ `cultivation_tab.py::render_cultivation()`

1. **Trang chủ (Home)**
   - Gọi: `core.get_state()` → lấy trạng thái người chơi từ DB
   - Gọi: `core.equipped_artifacts(state)` → lấy danh sách pháp bảo đang trang bị
   - Gọi: `core.player_stats(idx, artifacts, bonuses)` → tính chỉ số ATK/HP
   - Gọi: `core.all_titles()` → lấy danh sách huy hiệu người dùng
   - Gọi: `core.check_achievements()` → kiểm tra unlock huy hiệu

2. **3 Trò chơi ôn tập** (Fortune / Match / Sentence)
   - Gọi: `game_minigames.render_fortune(ctx)`
   - Gọi: `game_minigames.render_match(ctx)`
   - Gọi: `game_minigames.render_sentence(ctx)`
   - Tất cả đều gọi `core.get_state()` ở đầu
   - **Settle** (chốt lượt): Gọi `core.settle(base_ls, idx_scale, words_learned, ...)`

3. **Phường Thị (Market)**
   - Tab **Bí phương** (Recipes):
     - Gọi: `core.recipe_price(recipe)` → tính giá mua
     - Gọi: `core.buy_recipe(code, idx)` → mua bí phương → DB
   
   - Tab **Chế tạo** (Crafting):
     - Gọi: `core.recipe_materials(recipe)` → danh sách nguyên liệu cần
     - Gọi: `core.craft(code, idx, use_pill=False)` → chế tạo pháp bảo → DB
     - Gọi: `core.upgrade(artifact_id)` → nâng cấp pháp bảo → DB
   
   - Tab **Pháp bảo** (Artifacts):
     - Gọi: `core.artifact_bonus(recipe, quality, upgrade)` → tính bonus stats
     - Gọi: `core.equip(artifact_id, idx, slot=None)` → trang bị → DB
     - Gọi: `core.unequip(slot)` → tháo pháp bảo → DB
     - Gọi: `core.sell_artifact(artifact_id)` → bán pháp bảo → DB
     - Gọi: `core.upgrade_cost()`, `core.upgrade_chance()` → tính chi phí nâng cấp
   
   - Tab **Kho đồ** (Inventory):
     - Gọi: `core.discard_item(code)` → vứt bỏ vật phẩm → DB

4. **Công Pháp Các & Đan Điền** (Techniques)
   - Phần session state (chưa lưu DB)
   - `st.session_state.tech_farmed`: danh sách công pháp thu được
   - `st.session_state.tech_equipped`: danh sách công pháp đang trang bị

5. **Huy Hiệu** (Badges)
   - Gọi: `core.counter_value(state, counter, words_learned)`
   - Gọi: `core.equip_title(code)` → đeo danh hiệu → DB


---

## II. HÀM & KHỐI CODE CHÍNH

### A. `game_core.py`

#### **State Management**
- `get_state(force=False)` — lấy trạng thái session, load từ DB nếu cần (line 148)
- `_load(uid)` — load toàn bộ dữ liệu người chơi từ DB (line 135)
- `today()` — ngày hiện tại (UTC+7)
- `local_hour()` — giờ hiện tại

#### **Kinh tế**
- `reward_ls(base, mult, state, idx_scale)` — tính Linh Thạch thực nhận (line 374)
- `play_multiplier(plays_before)` — hệ số giảm sau 10/30 lượt mỗi ngày
- `scale(idx)` — hệ số cảnh giới (1.25^idx)
- `diminishing(points, cap, k)` — công thức lợi suất giảm dần

#### **Quẻ Bói**
- `draw_fortune(pool, mastery, pick_words)` — chọn quẻ hôm nay
- `start_fortune(vocab_id, tier)` — khởi tạo quẻ → DB
- `resolve_fortune(correct, idx)` — chốt quẻ (đúng/sai), cộng buff/streak → DB

#### **Phường Thị & Chế Tạo**
- `recipe_price(recipe)` — giá mua bí phương
- `recipe_craft_cost(recipe)` — chi phí chế tạo
- `recipe_materials(recipe)` → [(item_code, qty), ...]
- `buy_recipe(code, idx)` → DB (game_recipes)
- `buy_pill(idx)` → DB (game_inventory: pham_dan)
- `craft(code, idx, use_pill=False, rng)` → DB (game_artifacts, game_inventory, game_profile: pity)
- `equip(artifact_id, idx, slot)` → DB (game_counters: equip_1, equip_2)
- `unequip(slot)` → DB
- `sell_artifact(artifact_id)` → DB (DELETE, refund LS)
- **`discard_item(code)` — vứt bỏ vật phẩm → DB (game_inventory)** (line 489)

#### **Nâng cấp Pháp Bảo**
- `upgrade(artifact_id, rng)` → DB (game_artifacts: upgrade++, game_inventory)
- `upgrade_cost(recipe, level)` — chi phí nâng cấp
- `upgrade_chance(level)` — xác suất thành công

#### **Huy Hiệu**
- `check_achievements(words_learned)` → list huy hiệu mới unlock → DB (game_achievements)
- `counter_value(state, counter, words_learned)` — lấy giá trị counter
- `all_titles()` → {mã: tên danh hiệu}
- `equip_title(code)` → DB (game_profile: equipped_title)

#### **SETTLE (Chốt lượt)**
- **`settle(base_ls, idx_scale, words_learned, results=(), incr=None, maxes=None, items=None, log=None, count_play=True, record=True)`** (line 556)
  - Tính Linh Thạch theo hệ số lượt
  - Ghi kết quả ôn tập `record_review_batch(results)` vào word_mastery
  - Cộng counter (night_plays, etc.)
  - Gọi `check_achievements(words_learned)` → unlock huy hiệu
  - **Không quay lại state được trả về** — trả về `(ls, mult, new_badges)`

#### **apply_changes() — Atomic DB Writer** (line 254)
- Lõi của mọi thay đổi trạng thái
- Nhận: `ls=0, items={}, incr={}, maxes={}, log=None, plays=0, extra=[]`
- Ghi DB atomically
- **Trả về**: `state = get_state(force=True)` (load lại từ DB)

---

### B. `game_minigames.py`

#### **Quẻ Bói**
- `render_fortune(ctx)` — render giao diện, xử lý câu trả lời (line 21)
- `_fortune_answer(ok, word_id, ctx)` — callback khi bấm chọn (line 19)
  - Gọi: `core.resolve_fortune(ok, ctx["idx"])`
  - Gọi: `record_review_batch([(word_id, ok)])`

#### **Ghép Bài (Match)**
- `render_match(ctx)` — render, track state trong `st.session_state.g_match`
- `build_match_modes(words, rng)` — gán thể thức (Hán↔Nghĩa, nghe↔Pinyin, etc.)
- **State trong session**: `g_match = {"idx": i, "done": {...}, ...}`
- Callback: `_match_pick(i, j)`, `_match_check()`, `_match_next(ctx)` → gọi `core.settle()`

#### **Đối Câu (Sentence)**
- `render_sentence(ctx)` — render, track `st.session_state.g_sent`
- Callback: `_sent_pick(i)`, `_sent_undo()`, `_sent_check()`, `_sent_cloze(i)`, `_sent_next(ctx)` → gọi `core.settle()`

---

### C. `game_config.py`

#### **Kinh tế**
- `BASE_DAY_INCOME = 100`
- `ECON_SCALE = 1.25` (nhân thêm mỗi cảnh giới)
- `DAILY_FULL_PLAYS = 10` (nhận 100% LS)
- `DAILY_MID_PLAYS = 30` (11-30 nhận 40%, 31+ nhận 10%)
- `MULT_MID = 0.4, MULT_LOW = 0.1`

#### **Quẻ Bói**
- `FORTUNE_REWARD = 6` (Linh Thạch khi đúng, nhân cảnh giới)
- `FORTUNE_BUFFS = {"ls": (..., 10, 20), "shield": (..., 1, 2), "drop": (..., 20, 40)}`
- Buff lưu ở `game_fortune.buff` dạng `"code:value"` (ví dụ: `"ls:20"`)

#### **Trò chơi**
- `MATCH_PAIR_REWARD = 3` (LS mỗi cặp đúng)
- `MATCH_PERFECT_BONUS = 2` (thêm nếu 100%)
- `SENTENCE_REWARD = 3` (mỗi câu)
- `SENTENCE_PERFECT_BONUS = 4` (thêm)

#### **Pháp Bảo**
- `ARTIFACT_TIERS = {"linh_khi": {...}, "phap_bao": {...}, ...}` (5 tier)
- `QUALITY_NAMES = ("Hạ Phẩm", "Trung Phẩm", "Thượng Phẩm")`
- `QUALITY_ODDS = (0.60, 0.30, 0.10)` (bình thường)
- `QUALITY_ODDS_PILL = (0.40, 0.40, 0.20)` (có dùng đan)
- `PITY_MID_AT = 6, PITY_HIGH_AT = 12` (bảo hiểm)
- `RECIPES = [{code, name, tier, kind, region, min_idx}, ...]` (9 bí phương)

#### **Vật Phẩm**
- `ITEMS = {code: {name, folder, img_code, emoji}}`
- `ITEM_SETS = [{name, items: [(name, img_code), ...]}, ...]` (6 bộ)
- Mã vật phẩm: `r{region}_{0-5}` (thường 0-2, hiếm 3-4, quý 5)
- `pham_dan`: Tụ Phẩm Đan (dùng chế tạo)

#### **Huy Hiệu**
- `BADGE_LINES = [{base, counter, names: [Bronze, Silver, Gold], tiers: [need, need, need]}, ...]`
- `HIDDEN_BADGES = [{code, name, desc}, ...]`
- Mã huy hiệu: `"{base}_{tier}"` (ví dụ: `"scholar_0"`, `"scholar_1"`, `"scholar_2"`)

---

### D. `cultivation_tab.py`

#### **Render & Navigation**
- `render_cultivation(user, learned_day)` — main tab (line ~450?)
- `_render_home(state, ctx, user)` — trang chủ (line 72)
- `_render_market(state, ctx)` — phường thị (line ~130)
- `_render_techniques(state, ctx)` — công pháp (line ~400)
- `_render_badges(state, ctx)` — huy hiệu (line ~450)

#### **Context (ctx)**
```python
ctx = {
    "idx": realm_idx (0-15),
    "realm": realm_info(...),
    "pool": vocab_list,
    "mastery": mastery_dict,
    "words": total_learned,
    "bonuses": {"crit": 0.x, "hp": 0.x, "atk": 0.x, "dao_tam": 0.x},
}
```

#### **Session State**
- `st.session_state.game_state` → trạng thái người chơi (tương ứng `core.get_state()`)
- `st.session_state.g_match` → trạng thái minigame match
- `st.session_state.g_sent` → trạng thái minigame sentence
- `st.session_state.tech_farmed` → công pháp trong kho
- `st.session_state.tech_equipped` → công pháp đang trang bị

---

## III. CƠ SỞ DỮ LIỆU

### Schema (userdb.py)

#### **game_profile** (1 hàng/người chơi)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT PRIMARY KEY | |
| linh_thach | INT | Tiền chính |
| equipped_artifact | INT (deprecated) | Ô pháp bảo cũ (không dùng) |
| equipped_title | TEXT | Danh hiệu đang đeo |
| pity_mid | INT | Bảo hiểm Trung Phẩm (5 lần) |
| pity_high | INT | Bảo hiểm Thượng Phẩm (11 lần) |
| fortune_streak | INT | Chuỗi ngày bói quẻ liên tiếp |
| fortune_last_day | TEXT | Ngày bói quẻ cuối (YYYY-MM-DD) |

#### **game_daily** (mỗi ngày)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| day | TEXT | YYYY-MM-DD |
| plays | INT | Số lượt chơi trong ngày |
| **PRIMARY KEY** | (user_id, day) | |

#### **game_inventory** (mỗi item/người)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| item_code | TEXT | r{region}_{0-5}, pham_dan, ... |
| qty | INT | Số lượng |
| **PRIMARY KEY** | (user_id, item_code) | |

#### **game_recipes** (bí phương đã mua)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| recipe_code | TEXT | Code bí phương |
| **PRIMARY KEY** | (user_id, recipe_code) | |

#### **game_artifacts** (pháp bảo người chơi sở hữu)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INT PRIMARY KEY AUTOINCREMENT | |
| user_id | INT | |
| recipe_code | TEXT | Code bí phương |
| quality | INT | 0=Hạ, 1=Trung, 2=Thượng |
| upgrade | INT | +0 đến +9 |
| created_at | TEXT | Timestamp |
| INDEX | (user_id, id) | |

#### **game_fortune** (quẻ hôm nay, mỗi ngày 1 hàng)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| day | TEXT | YYYY-MM-DD |
| vocab_id | INT | Từ cần đoán |
| tier | TEXT | "Đại Cát", "Cát", "Bình" |
| status | TEXT | "pending", "ok", "fail" |
| buff | TEXT | Buff nhận được (ví dụ: "ls:20") |
| **PRIMARY KEY** | (user_id, day) | |

#### **game_achievements** (huy hiệu unlock)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| code | TEXT | "scholar_0", "scholar_1", ... |
| unlocked_at | TEXT | Timestamp |
| **PRIMARY KEY** | (user_id, code) | |

#### **game_counters** (counters đa mục đích)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| user_id | INT | |
| key | TEXT | "equip_1", "equip_2", "answers_correct", "crafts", ... |
| value | INT | |
| **PRIMARY KEY** | (user_id, key) | |

**Chú ý**: 2 ô pháp bảo lưu ở `game_counters` với key `equip_1`, `equip_2` (value = artifact.id hoặc 0)

#### **game_log** (40 log gần nhất)
| Cột | Kiểu | Ghi chú |
|-----|------|--------|
| id | INT PRIMARY KEY AUTOINCREMENT | |
| user_id | INT | |
| ts | TEXT | Timestamp |
| kind | TEXT | "fortune", "market", "craft", ... |
| text | TEXT | Mô tả hành động |
| INDEX | (user_id, id) | |

---

## IV. DATA FLOW: Ví Dụ Chế Tạo Pháp Bảo

```
User click "🔨 Chế tạo" với bí phương "thanh_phong_kiem"
    ↓
Kiểm tra: có bí phương? (game_recipes) ✓
Kiểm tra: cảnh giới đủ? (idx >= min_idx) ✓
Kiểm tra: Linh Thạch đủ? (state.ls >= cost) ✓
Kiểm tra: nguyên liệu? (game_inventory) ✓
    ↓
core.craft(code, idx, use_pill, rng):
  1. roll_quality(odds, pity_mid, pity_high) → (quality, pity_mid_new, pity_high_new)
  2. Tạo dict items = {r0_0: -6, r0_1: -4, ...} (hoàn nguyên)
  3. apply_changes(
       ls=-cost,
       items=items,
       incr={"crafts": 1},
       log=("craft", "Luyện thành công ..."),
       extra=[
         "INSERT INTO game_artifacts (user_id, recipe_code, quality) ...",
         "UPDATE game_profile SET pity_mid=?, pity_high=? ...",
       ]
     )
    ↓
apply_changes():
  1. Batch SQL statements:
     - UPDATE game_profile SET linh_thach = MAX(0, linh_thach - {cost})
     - INSERT/UPDATE game_inventory (mỗi item)
     - DELETE game_inventory WHERE qty <= 0
     - INSERT/UPDATE game_counters (crafts++)
     - INSERT game_log
     - [extra statements]
  2. get_user_db().batch(statements)
  3. return get_state(force=True) → load lại từ DB
    ↓
State updated → UI re-render hiển thị artifact mới
```

---

## V. Điểm Đầu Nối & Thách Thức

### Vị Trí Khớp Nối Chính

| **Điểm** | **Hàm** | **Từ** | **Đến** | **Luồng Dữ Liệu** |
|---------|--------|--------|--------|-----------------|
| 1 | `settle()` | minigames | core | (ls, mult, new_badges) |
| 2 | `buy_recipe()` | cultivation (market) | core | success, message → DB |
| 3 | `craft()` | cultivation (market) | core | success, message, quality → DB |
| 4 | `equip()` | cultivation (market) | core | success, message → DB |
| 5 | `discard_item()` | cultivation (market) | core | success, message → DB |
| 6 | `check_achievements()` | settle / market actions | core | [new badge codes] |
| 7 | `get_state()` | every game/market action | core | full state from DB |

### Dữ Liệu Không Lưu DB

1. **Session Minigames**: `st.session_state.g_match`, `st.session_state.g_sent`
   - Chứa: questions, answers, UI state, idx
   - Reset mỗi lần reload page

2. **Kỹ Năng Công Pháp**: `st.session_state.tech_farmed`, `st.session_state.tech_equipped`
   - Chứa: danh sách công pháp
   - **CẦN MIGRATE ĐẬU DB**

---

## VI. Những Thay Đổi Cần Migration

### 1. **Bảng game_techniques** (NEW)
Lưu công pháp đã mua của người chơi.

```sql
CREATE TABLE game_techniques (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  tech_id TEXT NOT NULL,
  acquired_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, tech_id)
);

CREATE TABLE game_dan_dien (
  user_id INTEGER PRIMARY KEY,
  equipped TEXT,  -- JSON: [{id, r, c}, ...]
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 2. **Cột game_profile** (NEW hoặc game_counters)
Lưu trang bị hiện tại cho Đan Điền
- Option A: Thêm cột `equipped_dan_dien` (JSON)
- Option B: Dùng game_counters với key `dan_dien_equipped` (JSON text)

### 3. **Audit Log Chi Tiết**
Mở rộng game_log để track tất cả hành động (hiện tại chỉ track ~40 log cuối)

---

## VII. Thứ Tự Triển Khai (Deployment Order)

1. **Phiên 1**: Tìm và xác định **call sites của `settle()`** trong minigames
   - Mục tiêu: Làm sạch luồng dữ liệu settle, đảm bảo kết quả trả về được xử lý
   - Files: `game_minigames.py` (render_fortune, render_match, render_sentence)

2. **Phiên 2**: Kiểm tra **Phường Thị & các thao tác market**
   - Mục tiêu: Xác minh `apply_changes()` luôn được gọi đúng
   - Files: `cultivation_tab.py::_render_market`, `game_core.py` (buy, craft, equip, sell, discard)

3. **Phiên 3**: Migrate **Kỹ Năng Công Pháp** từ session state sang DB
   - Mục tiêu: Lưu công pháp vào `game_techniques`, đan điền vào `game_dan_dien`
   - Files: `cultivation_tab.py::_render_techniques`, `userdb.py` (schema), `game_core.py` (mới)

4. **Phiên 4**: Tối ưu **Huy Hiệu & Danh Hiệu**
   - Mục tiêu: Đảm bảo unlock đúng thời điểm
   - Files: `game_core.py::check_achievements()`, `cultivation_tab.py::_render_badges()`

5. **Phiên 5**: Tối ưu **Quẻ Bói & Buff**
   - Mục tiêu: Đảm bảo fortune streak, buff áp dụng đúng
   - Files: `game_core.py::resolve_fortune()`, `game_minigames.py::render_fortune()`

---

## VIII. Tóm Tắt Chốt Điểm

| **Thành Phần** | **Vị Trí** | **Trạng Thái** | **Ghi Chú** |
|--------------|----------|--------------|-----------|
| **settle()** | game_core.py:556 | ✓ Xác định | Trả về (ls, mult, badges) |
| **apply_changes()** | game_core.py:254 | ✓ Atomic | Lõi DB writer |
| **discard_item()** | game_core.py:489 | ✓ Xác định | Vứt bỏ vật phẩm |
| **get_state()** | game_core.py:148 | ✓ Cache + Load | State lấy từ DB |
| **Minigames flow** | game_minigames.py | ✓ Rõ ràng | Tất cả settle → DB |
| **Market flow** | cultivation_tab.py | ✓ Rõ ràng | Tất cả apply_changes → DB |
| **Tech/Đan Điền** | cultivation_tab.py:300+ | ⚠️ Session-only | CẦN migrate sang DB |
| **Badges unlock** | game_core.py:580 | ✓ Xác định | check_achievements() |

---

**Kết luận**: Toàn bộ luồng dữ liệu rõ ràng. DB schema đúng. Chỉ cần migrate Kỹ Năng Công Pháp từ session state sang DB.
