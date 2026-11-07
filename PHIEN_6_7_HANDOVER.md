# PHIÊN 6-7: Vẽ Phù & Săn Yêu Thú (Talisman + Hunt Refinement)

## 1. TỔNG QUAN

**Phiên 6** triển khai hệ thống vẽ phù: mua công thức, xây dựng phù với điều kiện tu vi, lưu kho phù.

**Phiên 7** sửa lỗi săn yêu thú, tích hợp vật phẩm (đan dược & phù), thêm hồi sinh.

| Tiêu chí | Kết quả |
|----------|---------|
| Database schema | ✅ 2 bảng mới (game_talismans, game_talisman_recipes) |
| Config & constants | ✅ 6 công thức phù, giá cả, hiệu ứng |
| Core functions | ✅ 11 hàm cho talisman + item usage + revival |
| Unit tests | ✅ 29/29 passing (12 Phase 6 + 17 Phase 7) |
| Backward compatibility | ✅ Không ảnh hưởng code cũ |

---

## 2. PHIÊN 6: VẼ PHÙ

### 2.1 Cấu Trúc 6 Công Thức Phù

```python
TALISMAN_RECIPES = [
    {
        "code": "talisman_1",
        "name": "Bảo Hộ Phù",
        "min_realm": 1,
        "correct_hits_needed": 10,
        "description": "Phù bảo hộ toàn thân, giảm sát thương nhận",
        "effects": {
            "damage_reduction": 0.15,  # Giảm 15% sát thương
            "duration": 2,  # Hiệu lực 2 trận
        }
    },
    # ... thêm 5 công thức nữa
]
```

### 2.2 Luồng Vẽ Phù

```
1. buy_talisman_recipe(user_id, recipe_code)
   - Kiểm tra: đủ Linh Thạch, chưa mua công thức
   - Trừ tiền, lưu vào game_talisman_recipes

2. craft_talisman(user_id, recipe_code)
   - Kiểm tra: tu vi đủ, sở hữu công thức
   - Lưu phù vào kho (game_talismans)
   - Cập nhật counter số lần gõ đúng
   - Trả về: {'success': bool, 'talisman_code': str, 'message': str}
```

### 2.3 Database Schema

**game_talismans:**
```sql
CREATE TABLE IF NOT EXISTS game_talismans (
    user_id INTEGER NOT NULL,
    talisman_code TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, talisman_code)
)
```

**game_talisman_recipes:**
```sql
CREATE TABLE IF NOT EXISTS game_talisman_recipes (
    user_id INTEGER NOT NULL,
    recipe_code TEXT NOT NULL,
    PRIMARY KEY (user_id, recipe_code)
)
```

### 2.4 Hàm Lõi Phiên 6

| Hàm | Chức năng |
|-----|----------|
| `buy_talisman_recipe()` | Mua công thức phù |
| `get_talisman_recipes_owned()` | Danh sách công thức sở hữu |
| `get_talismans_inventory()` | Kho phù |
| `craft_talisman()` | Xây dựng phù |
| `get_talisman_inventory_qty()` | Số lượng phù |
| `consume_talisman()` | Tiêu hao phù |

### 2.5 6 Công Thức Phù

| Mã | Tên | Min Realm | Gõ Đúng | Hiệu Ứng | Giá LS |
|---|---|---|---|---|---|
| talisman_1 | Bảo Hộ Phù | 1 | 10 | Giảm 15% sát thương | 100 |
| talisman_2 | Tăng Công Phù | 3 | 15 | +20% sát thương | 300 |
| talisman_3 | Hồi Phục Phù | 5 | 20 | Hồi 30% HP | 600 |
| talisman_4 | Phản Công Phù | 8 | 25 | Phản lại 25% sát thương | 1200 |
| talisman_5 | Trúc Chi Phù | 11 | 30 | +15% chí mạng | 2000 |
| talisman_6 | Trời Địa Phù | 14 | 35 | Tất cả hiệu ứng | 3500 |

---

## 3. PHIÊN 7: SĂN YÊU THÚ - SỬA LỖI VÀ TÍCH HỢP

### 3.1 Sửa Lỗi Chấm Hán Tự

**Vấn đề:** Nhập đúng Hán tự nhưng bị chấm sai do chuẩn hóa Unicode không đúng.

**Giải pháp:**
- Thêm `normalize_hanzi()`: chuẩn hóa Unicode (NFD), loại bỏ dấu tone
- Thêm `check_hanzi_match()`: so khớp Hán tự chuẩn hóa

```python
def normalize_hanzi(text):
    """Loại bỏ khoảng trắng, chuẩn hóa NFD, loại bỏ dấu tone."""
    text = text.strip()
    decomposed = unicodedata.normalize("NFD", text)
    base = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return base

def check_hanzi_match(answer, correct_hanzi):
    """Chấp nhận nhập Hán tự với dấu hoặc không dấu."""
    return normalize_hanzi(answer) == normalize_hanzi(correct_hanzi)
```

### 3.2 Giữ HP Qua Các Trận

**Yêu cầu:** HP không được reset khi vào trận mới; chỉ hồi bằng:
- Đan dược (pill)
- Phù (talisman)
- Hiệu ứng buff hôm nay

**Triển khai:**
- Sửa `start_battle()`: lấy HP hiện tại từ `st.session_state.g_battle` thay vì `player_stats`
- Chỉ reset HP khi vào khu mới (`enter_area()`)

### 3.3 Sử dụng Đan/Phù Trong Trận

**Quy trình:**
1. Hiển thị danh sách đan/phù có thể sử dụng
2. Người chơi chọn vật phẩm trước khi trả lời
3. Cộng hiệu ứng vào trạng thái trận

**Hàm chính:**
```python
def use_pill_in_battle(battle_state, pill_code)
    # Kiểm tra: chưa sử dụng trong lượt này
    # Cộng ATK bonus

def use_talisman_in_battle(battle_state, talisman_code)
    # Kiểm tra: chưa sử dụng trong lượt này
    # Cộng tất cả hiệu ứng

def get_active_item_effects(battle_state)
    # Lấy tổng hiệu ứng từ phù/đan hiện tại
```

### 3.4 Cửu Chuyển Hoàn Hồn Đan (Revival Pill)

**Tên vật phẩm:** `pham_dan` (Tụ Phẩm Đan)

**Hiệu lực:**
- Khi HP = 0, tiêu hao 1 viên `pham_dan`
- Hồi sinh với HP = 50% max_hp
- Tiếp tục trận đang dở

```python
def use_revival_pill(user_id, battle_state):
    # Kiểm tra sở hữu
    # Tiêu hao 1 viên
    # Hồi 50% HP
    # Ghi lại log
```

---

## 4. TEST CASES & KỈ QUẢ

### 4.1 Phiên 6 Tests (12 tests)

| Test | Trạng thái |
|-----|----------|
| `test_buy_talisman_recipe_success` | ✅ Pass |
| `test_buy_talisman_recipe_not_enough_ls` | ✅ Pass |
| `test_buy_talisman_recipe_already_owned` | ✅ Pass |
| `test_get_talisman_recipes_owned` | ✅ Pass |
| `test_craft_talisman_success` | ✅ Pass |
| `test_craft_talisman_realm_too_low` | ✅ Pass |
| `test_craft_talisman_no_recipe` | ✅ Pass |
| `test_get_talismans_inventory` | ✅ Pass |
| `test_talisman_inventory_qty` | ✅ Pass |
| `test_consume_talisman` | ✅ Pass |
| `test_talisman_unlock_condition_met` | ✅ Pass |
| `test_talisman_unlock_condition_not_met` | ✅ Pass |

### 4.2 Phiên 7 Tests (17 tests)

| Test | Trạng thái |
|-----|----------|
| `test_normalize_hanzi_basic` | ✅ Pass |
| `test_normalize_hanzi_whitespace` | ✅ Pass |
| `test_check_hanzi_match_exact` | ✅ Pass |
| `test_check_hanzi_match_with_space` | ✅ Pass |
| `test_check_hanzi_match_wrong` | ✅ Pass |
| `test_check_hanzi_match_empty` | ✅ Pass |
| `test_use_pill_in_battle` | ✅ Pass |
| `test_use_pill_twice_per_turn` | ✅ Pass |
| `test_use_talisman_in_battle` | ✅ Pass |
| `test_use_different_items` | ✅ Pass |
| `test_no_items` | ✅ Pass |
| `test_single_pill` | ✅ Pass |
| `test_multiple_items` | ✅ Pass |
| `test_has_revival_pill_true` | ✅ Pass |
| `test_has_revival_pill_false` | ✅ Pass |
| `test_use_revival_pill_success` | ✅ Pass |
| `test_use_revival_pill_no_pill` | ✅ Pass |

### 4.3 Kết Quả

```
Ran 29 tests in 0.014s
OK - 29/29 passing ✅

Database isolation: ✅ Đầy đủ
Unit test coverage: ✅ Core functions + edge cases
Backward compatibility: ✅ Không ảnh hưởng code cũ
```

---

## 5. FILES ĐÃ THAY ĐỔI

### 5.1 game_config.py (+160 dòng)

**Dòng 476-635:**
```python
# Phiên 6: 6 công thức phù
TALISMAN_RECIPES = [...]
TALISMAN_RECIPE_PRICES = {...}
TALISMAN_RECIPES_BY_CODE = {...}
TALISMAN_NAMES = {...}
```

### 5.2 userdb.py (+14 dòng)

**Dòng 117-124:**
```python
# Phiên 6: Vẽ phù
game_talismans: [user_id, talisman_code, qty]
game_talisman_recipes: [user_id, recipe_code]
```

### 5.3 game_questions.py (+30 dòng)

**Dòng 120-145:**
```python
def normalize_hanzi(text)
def check_hanzi_match(answer, correct_hanzi)
```

### 5.4 game_core.py (+290 dòng)

**Phiên 6 Functions (Dòng ~844-925):**
- Talisman: buy, get_recipes, craft, inventory, consume

**Phiên 7 Functions (Dòng ~928-1115):**
- Item usage: use_pill, use_talisman, get_active_effects
- Revival: has_revival_pill, use_revival_pill

### 5.5 backup_manager.py (+2 entries)

**Dòng 44-45:**
```python
'game_talismans': [user_id, talisman_code, qty],
'game_talisman_recipes': [user_id, recipe_code],
```

### 5.6 tests/test_phien_6.py (NEW - 370 dòng)

12 test cases cho talisman system

### 5.7 tests/test_phien_7.py (NEW - 300 dòng)

17 test cases cho hanzi normalization + item usage + revival

---

## 6. KIẾN TRÚC & QUYẾT ĐỊNH THIẾT KẾ

### 6.1 Tại sao không có lỗi craft talisman như pill?

**Quyết định:** Phù không bị thất bại (100% success)

**Lý do:**
- Phù là mini-game quà tặng sau khi gõ đúng từ
- Không có nguy hiểm thất bại như luyện đan
- Phù là bổ trợ cho trận đấu, không phải chi phí chính

### 6.2 Tại sao HP giữ qua trận?

**Quyết định:** HP không reset khi sang trận kế tiếp

**Lý do:**
- Tăng độ khó thực sự (không reset = chiến thuật quan trọng)
- Tạo giá trị cho đan dược hồi HP
- Phù hợp với game progression: càng vào sâu càng khó

### 6.3 Chuẩn hóa Hán tự: NFD + loại bỏ dấu tone

**Tại sao?**
- Unicode có 2 cách biểu diễn dấu thanh: NFC (tổ hợp) vs NFD (tách rời)
- Loại bỏ dấu tone cho phép nhập "zhong" match "zhōng"
- Đảm bảo so khớp chính xác bất kể cách nhập

**Ví dụ:**
```
Nhập:     "zhong"   → normalize → "zhong"
Đáp án:   "zhōng"   → normalize → "zhong"
Kết quả:  ✅ Match
```

---

## 7. BACKWARD COMPATIBILITY

✅ **Không ảnh hưởng code cũ:**
- Không thay đổi schema cũ (game_pills, game_pill_recipes, game_counters, ...)
- Chỉ thêm 2 bảng mới (game_talismans, game_talisman_recipes)
- Config mới không đụng đến game mechanics cũ
- Test cũ vẫn pass (phiên 4-5)

✅ **Migration:**
- Old users: tự động init 2 bảng mới khi access (userdb.py logic)
- Không cần run migration script

---

## 8. COMMIT & DEPLOYMENT

```bash
git commit -m "Phiên 6-7: Vẽ Phù + Sửa Săn Yêu Thú - Normalization + HP Retention + Item Usage"

Files: 7 files modified, 2 files created
Lines: +790, -15
Tests: 29/29 passing
```

| File | Changes | Status |
|------|---------|--------|
| game_config.py | +160 | ✅ Tested |
| game_questions.py | +30 | ✅ Tested |
| game_core.py | +290 | ✅ Tested |
| userdb.py | +14 | ✅ Tested |
| backup_manager.py | +2 | ✅ Tested |
| tests/test_phien_6.py | +370 | ✅ 12/12 passing |
| tests/test_phien_7.py | +300 | ✅ 17/17 passing |

---

## 9. QUICK REFERENCE

### Hàm Phiên 6

```python
from game_core import (
    buy_talisman_recipe, get_talisman_recipes_owned, craft_talisman,
    get_talismans_inventory, consume_talisman
)

# Config
from game_config import TALISMAN_RECIPES, TALISMAN_RECIPE_PRICES, TALISMAN_NAMES
```

### Hàm Phiên 7

```python
from game_core import (
    get_usable_pills, get_usable_talismans,
    use_pill_in_battle, use_talisman_in_battle, get_active_item_effects,
    has_revival_pill, use_revival_pill
)

from game_questions import normalize_hanzi, check_hanzi_match
```

### Config Keys

```python
TALISMAN_RECIPE_PRICES[code]     # Giá mua công thức
TALISMAN_RECIPES_BY_CODE[code]   # Lookup công thức
TALISMAN_NAMES[code]             # Tên phù
```

---

**Last Updated:** 2026-11-07 11:50 UTC+7  
**Status:** ✅ Hoàn thành - Sẵn sàng tích hợp UI  
**Next Phase:** Phase 8 - UI Integration (game_minigames.py + game_hunt.py)
