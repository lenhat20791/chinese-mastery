# Phiên 0 — Roadmap & Checklist

## ✅ Phiên 0 Hoàn Tất

### Kiểm Tra 4 File Chính

- [x] **game_minigames.py** (15.8 KB)
  - [x] 3 render functions: fortune, match, sentence
  - [x] Luồng settle → apply_changes
  - [x] Session state: g_match, g_sent
  
- [x] **game_core.py** (24.3 KB)
  - [x] apply_changes() — atomic DB writer (line 254)
  - [x] settle() — chốt lượt (line 556)
  - [x] discard_item() — vứt bỏ (line 489)
  - [x] buy/craft/equip/unequip/sell/upgrade
  - [x] resolve_fortune, check_achievements
  
- [x] **game_config.py** (21.8 KB)
  - [x] ECON_SCALE, DAILY_FULL_PLAYS, MULT_*
  - [x] RECIPES, ARTIFACTS, ITEMS, BADGE_LINES
  - [x] FORTUNE_BUFFS (ls, shield, drop)
  
- [x] **cultivation_tab.py** (25.7 KB)
  - [x] Navigation: _render_home, _render_market, _render_techniques, _render_badges
  - [x] Market: buy, craft, equip, discard
  - [x] Techniques: session-only (⚠️ needs DB migration)

### Kết Quả Khảo Sát

- [x] Xác định hàm chính: `settle()`, `apply_changes()`, `discard_item()`
- [x] Xác định nơi lưu dữ liệu: DB schema 9 bảng
- [x] Xác định luồng gọi: 7 connection points
- [x] Xác định lỗi tiềm năng: Techniques lưu session-only

---

## 📋 Phiên 1 — Xác Nhận settle() Call Sites

### Mục Tiêu
Rà soát tất cả **chỗ gọi `settle()`** trong minigames:
1. Kiểm tra parameters được truyền đúng
2. Kiểm tra return value `(ls, mult, badges)` được xử lý
3. Đảm bảo `record_review_batch()` gọi đúng
4. Đảm bảo huy hiệu được thông báo

### Tasks
- [ ] **render_fortune()** (game_minigames.py)
  - [ ] Tìm gọi settle() (nếu có)
  - [ ] Kiểm tra huy hiệu toast
  - [ ] Xác nhận buff lưu đúng game_fortune.buff
  
- [ ] **render_match()** (game_minigames.py)
  - [ ] Tìm gọi settle() ở `_match_next()`
  - [ ] Kiểm tra ls=MATCH_PAIR_REWARD * matched_pairs
  - [ ] Kiểm tra items={} (nếu cần lưu vật phẩm)
  - [ ] Kiểm tra incr={"answers_correct": n} được cộng
  
- [ ] **render_sentence()** (game_minigames.py)
  - [ ] Tìm gọi settle() ở `_sent_next()`
  - [ ] Tương tự match
  
- [ ] **Kiểm tra toast & UI**
  - [ ] `_toast_new(badges)` được gọi
  - [ ] Hiển thị "🏅 Danh hiệu mới: ..."

### Deliverable
- File report: `PHIEN_1_SETTLE_AUDIT.md`
- Chứa: danh sách call sites, parameters, xác nhận ✓/✗

---

## 📋 Phiên 2 — Phường Thị Actions

### Mục Tiêu
Xác nhận tất cả market actions gọi `apply_changes()` đúng:
1. buy_recipe → insert game_recipes
2. craft → insert game_artifacts, update game_profile (pity)
3. equip → update game_counters (equip_X)
4. discard_item → delete game_inventory
5. upgrade → update game_artifacts.upgrade
6. sell_artifact → delete game_artifacts, refund LS

### Tasks
- [ ] **buy_recipe()** (game_core.py, line ~425)
  - [ ] Trừ LS từ game_profile
  - [ ] Insert vào game_recipes
  - [ ] Log ghi vào game_log
  
- [ ] **craft()** (game_core.py, line ~450)
  - [ ] Trừ LS, trừ items từ game_inventory
  - [ ] Insert game_artifacts với quality
  - [ ] Update game_profile (pity_mid, pity_high)
  - [ ] Log ghi vào game_log
  
- [ ] **equip()/unequip()** (game_core.py, line ~470)
  - [ ] Update game_counters (equip_1, equip_2)
  - [ ] Kiểm tra artifact.id có trong game_artifacts
  
- [ ] **discard_item()** (game_core.py, line 489)
  - [ ] ✓ Xác định vị trí
  - [ ] Trừ qty từ game_inventory
  - [ ] Log ghi vào game_log
  
- [ ] **upgrade()** (game_core.py, line ~510)
  - [ ] Trừ LS, trừ items
  - [ ] Update game_artifacts.upgrade++
  - [ ] Xử lý thất bại (không trừ LS)
  
- [ ] **sell_artifact()** (game_core.py, line ~500)
  - [ ] Tính hoàn lại = 50% craft cost
  - [ ] DELETE game_artifacts
  - [ ] Thao tác equip_X nếu đang mang

### Deliverable
- File report: `PHIEN_2_MARKET_AUDIT.md`

---

## 📋 Phiên 3 — Migrate Techniques → DB

### Mục Tiêu
Chuyển Kỹ Năng Công Pháp từ session state sang DB:
1. Tạo 2 bảng mới: game_techniques, game_dan_dien
2. Cập nhật _load() để load techniques
3. Cập nhật _render_techniques() để save/load from DB

### Tasks
- [ ] **Tạo schema** (userdb.py)
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
    equipped TEXT,  -- JSON: [{id, r, c, w, h}, ...]
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
  );
  ```
  
- [ ] **Cập nhật _load()** (game_core.py)
  - [ ] Load game_techniques
  - [ ] Load game_dan_dien
  - [ ] Thêm vào state: `"techniques": {...}, "dan_dien": [...]`
  
- [ ] **Cập nhật apply_changes()** (game_core.py)
  - [ ] Xử lý ghi game_techniques
  - [ ] Xử lý ghi game_dan_dien
  
- [ ] **Cập nhật _render_techniques()** (cultivation_tab.py)
  - [ ] Đọc từ state["techniques"], state["dan_dien"]
  - [ ] Khi dùng công pháp: apply_changes(extra=[INSERT game_dan_dien])
  - [ ] Khi thu hồi: apply_changes(extra=[UPDATE game_dan_dien])
  
- [ ] **Migration script** (tools/)
  - [ ] Chuyển session data hiện tại sang DB (nếu có user cũ)

### Deliverable
- `userdb.py`: updated schema
- `game_core.py`: updated _load(), apply_changes()
- `cultivation_tab.py`: updated _render_techniques()
- Migration script

---

## 📋 Phiên 4 — Tối Ưu Huy Hiệu

### Mục Tiêu
Đảm bảo huy hiệu unlock đúng thời điểm:
1. check_achievements() logic chính xác
2. Badge tiers (Bronze/Silver/Gold) tính đúng
3. Danh hiệu (titles) ghi đúng game_profile.equipped_title

### Tasks
- [ ] **Kiểm tra check_achievements()** (game_core.py, line 580)
  - [ ] Mỗi line trong BADGE_LINES:
    - [ ] Counter được xác định (words_learned, answers_correct, ...)
    - [ ] Tiers threshold hợp lý
    - [ ] LS reward tính đúng
  
- [ ] **Kiểm tra HIDDEN_BADGES** (game_config.py)
  - [ ] Từng badge ẩn có điều kiện rõ ràng
  
- [ ] **Kiểm tra equip_title()** (game_core.py)
  - [ ] Ghi vào game_profile.equipped_title
  
- [ ] **UI test** (cultivation_tab.py::_render_badges)
  - [ ] Hiển thị huy hiệu unlock
  - [ ] Hiển thị mốc tiếp theo
  - [ ] Progress bar tính đúng

### Deliverable
- File report: `PHIEN_4_BADGES_AUDIT.md`

---

## 📋 Phiên 5 — Tối Ưu Quẻ Bói & Buff

### Mục Tiêu
Đảm bảo fortune streak, buff được áp dụng đúng:
1. Quẻ chỉ có thể chốt 1 lần mỗi ngày
2. Buff chỉ active trên cùng ngày
3. Streak được cộng liên tiếp (ngày hôm nay = ngày hôm qua + 1)

### Tasks
- [ ] **Kiểm tra resolve_fortune()** (game_core.py, line ~410)
  - [ ] Kiểm tra `game_fortune.status != 'pending'` → không chốt lại
  - [ ] Kiểm tra streak logic
    - [ ] streak_day = hôm qua → streak++
    - [ ] streak_day ≠ hôm qua → streak = 1
  - [ ] Buff được tính đúng (great value cho "Đại Cát")
  
- [ ] **Kiểm tra buff active** (game_core.py)
  - [ ] `active_buff(state)` chỉ return buff nếu status="ok"
  - [ ] `buff_value(state, code)` trả về 0 nếu không active
  
- [ ] **Kiểm tra reward_ls()** (game_core.py, line 374)
  - [ ] Tính bonus = 1 + buff_value / 100
  - [ ] bonus áp dụng đúng: ls * (1 + bonus)
  
- [ ] **UI test** (game_minigames.py::render_fortune)
  - [ ] Hiển thị streak ngày hôm nay
  - [ ] Buff được hiển thị (nếu có)
  - [ ] Quẻ mới xuất hiện đúng ngày hôm sau

### Deliverable
- File report: `PHIEN_5_FORTUNE_AUDIT.md`

---

## 📊 Timeline & Dependencies

```
Phiên 0 (HIỆN TẠI) — 4 file chính
    ↓
Phiên 1 — settle() audit (độc lập)
    ↓
Phiên 2 — market audit (độc lập)
    ↓
Phiên 3 — migrate techniques (depends on 1, 2)
    ↓
Phiên 4 — badges audit (độc lập)
    ↓
Phiên 5 — fortune/buff audit (độc lập)
    ↓
CHỐT ĐIỂM & TRIỂN KHAI
```

**Estimated Effort**:
- Phiên 1: 2-3 giờ (grep + verify)
- Phiên 2: 3-4 giờ (xem code + verify DB calls)
- Phiên 3: 4-5 giờ (code + schema + migration)
- Phiên 4: 2 giờ (verify logic)
- Phiên 5: 2 giờ (verify logic)

**Total**: ~14-16 giờ

---

## 📁 Output Artifacts (Phiên 0)

```
E:\chinese-mastery\
├── PHIEN_0_SURVEY.md          ✓ Khảo sát toàn diện
├── PHIEN_0_QUICK_REF.md       ✓ Quick reference
├── PHIEN_0_DATAFLOW.md        ✓ Data flow diagrams
└── PHIEN_0_ROADMAP.md         ✓ This file
```

---

## 🎯 Next Action

**Tiếp theo Phiên 1**: Chuẩn bị audit settle() call sites

Bắt đầu khi nào? → User confirm hoặc `/continue` để sang Phiên 1
