# 📋 PHIÊN 4 - BÀN GIAO: NỀN TẢNG LUYỆN ĐAN VÀ KHO ĐAN DƯỢC

## **TỔNG QUAN**

**Phiên 4** triển khai **Luyện Đan (Alchemy)** - hệ thống chế tạo đan dược từ nguyên liệu để tăng chỉ số và chuẩn bị cho mini-game trong Phiên 5.

### Yêu cầu chính:
1. ✅ Khai báo 5 công thức đan dược với điều kiện tu vi, nguyên liệu, hiệu quả, tỷ lệ thành công
2. ✅ Triển khai luyện đan: tiêu hao nguyên liệu, tính toán thành công/thất bại
3. ✅ Lưu đan thành công vào kho, có thể dùng khi đi săn
4. ✅ Kiểm tra quyền, điều kiện tu vi, xác suất, nguyên liệu và tồn kho

---

## **PHẦN 1: HIỂU CÔNG THỨC ĐAN DƯỢC**

### Cấu trúc 5 công thức:

| Tên | Mã | Tu Vi Min | Nguyên Liệu Cần | Hiệu Quả | Tỷ Lệ Thành Công |
|-----|-----|-----------|------------------|---------|------------------|
| Hạ Phẩm Yêu Đan | `pill_1` | Realm 0 | 2x Hắc Thiết, 1x Yêu Lang Bì | +2% ATK | 80% |
| Trung Phẩm Yêu Đan | `pill_2` | Realm 3 | 2x Tinh Thiết, 1x Hạ Phẩm Yêu Đan | +5% ATK | 70% |
| Thượng Phẩm Yêu Đan | `pill_3` | Realm 6 | 3x Huyền Thiết, 2x Xích Tinh Thạch | +8% ATK | 60% |
| Tối Thượng Yêu Đan | `pill_4` | Realm 10 | 3x Hàn Thiết, 2x Thiên Lôi Mộc, 1x Hàn Ngọc | +12% ATK | 50% |
| Tôn Thần Yêu Đan | `pill_5` | Realm 15 | 4x Linh Mộc Tâm, 3x Thiên Lôi Mộc, 1x Tiên Duyên | +15% ATK | 40% |

---

## **PHẦN 2: TRIỂN KHAI LUYỆN ĐAN**

### Files thay đổi:

#### 1. **game_config.py** (Thêm cấu hình đan dược)

Thêm vào phần "Bộ vật phẩm" (sau ITEM_SETS):
```python
# Công thức luyện đan: (mã, tên, tu vi min, nguyên liệu, hiệu quả ATK%, tỷ lệ thành công)
PILL_RECIPES = [
    {
        "code": "pill_1",
        "name": "Hạ Phẩm Yêu Đan",
        "min_realm": 0,
        "materials": [("r0_0", 2), ("r0_1", 1)],  # 2x Hắc Thiết, 1x Yêu Lang Bì
        "bonus_atk_pct": 2.0,
        "success_rate": 0.80,
        "price": 100,
    },
    {
        "code": "pill_2",
        "name": "Trung Phẩm Yêu Đan",
        "min_realm": 3,
        "materials": [("r0_3", 2), ("pill_1", 1)],  # 2x Tinh Thiết, 1x Hạ Phẩm Yêu Đan
        "bonus_atk_pct": 5.0,
        "success_rate": 0.70,
        "price": 300,
    },
    {
        "code": "pill_3",
        "name": "Thượng Phẩm Yêu Đan",
        "min_realm": 6,
        "materials": [("r1_2", 3), ("r1_4", 2)],  # 3x Huyền Thiết, 2x Xích Tinh Thạch
        "bonus_atk_pct": 8.0,
        "success_rate": 0.60,
        "price": 800,
    },
    {
        "code": "pill_4",
        "name": "Tối Thượng Yêu Đan",
        "min_realm": 10,
        "materials": [("r2_0", 3), ("r2_4", 2), ("r2_4", 1)],  # 3x Hàn Thiết, 2x Thiên Lôi Mộc, 1x Hàn Ngọc
        "bonus_atk_pct": 12.0,
        "success_rate": 0.50,
        "price": 2000,
    },
    {
        "code": "pill_5",
        "name": "Tôn Thần Yêu Đan",
        "min_realm": 15,
        "materials": [("r3_2", 4), ("r3_4", 3), ("r3_5", 1)],  # 4x Linh Mộc Tâm, 3x Thiên Lôi Mộc, 1x Tiên Duyên
        "bonus_atk_pct": 15.0,
        "success_rate": 0.40,
        "price": 5000,
    },
]

# Bảng giá công thức (Linh Thạch)
PILL_RECIPE_PRICE = {
    "pill_1": 50,
    "pill_2": 200,
    "pill_3": 500,
    "pill_4": 1500,
    "pill_5": 3000,
}
```

#### 2. **userdb.py** (Thêm bảng `game_pills` và `game_pill_recipes`)

Thêm vào SCHEMA:
```python
"""CREATE TABLE IF NOT EXISTS game_pills (
    user_id INTEGER NOT NULL,
    pill_code TEXT NOT NULL,
    qty INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, pill_code)
)""",
"""CREATE TABLE IF NOT EXISTS game_pill_recipes (
    user_id INTEGER NOT NULL,
    recipe_code TEXT NOT NULL,
    PRIMARY KEY (user_id, recipe_code)
)""",
```

Cập nhật `BACKUP_TABLES` (backup_manager.py):
```python
"game_pills": ["user_id", "pill_code", "qty"],
"game_pill_recipes": ["user_id", "recipe_code"],
```

#### 3. **game_core.py** (Thêm hàm luyện đan)

Thêm các hàm:
```python
def can_craft_pill(recipe_code, user_id, realm_idx):
    """Kiểm tra điều kiện luyện đan:
    1. Người chơi có công thức?
    2. Đủ cấp tu vi?
    3. Đủ nguyên liệu?
    
    Trả về (ok, reason)
    """
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    
    # 1. Kiểm tra có công thức
    db = get_user_db()
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if not has_recipe:
        return False, "Chưa mua công thức này"
    
    # 2. Kiểm tra tu vi
    if realm_idx < recipe["min_realm"]:
        need_words = cfg.SUB_THRESHOLDS[recipe["min_realm"] * 3]
        return False, f"Cần đạt Realm {recipe['min_realm']} (khoảng {need_words} từ)"
    
    # 3. Kiểm tra nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        qty_have = get_inventory_qty(user_id, mat_code)
        if qty_have < qty_need:
            return False, f"Không đủ {cfg.ITEM_NAME_BY_CODE.get(mat_code, mat_code)}: cần {qty_need}, có {qty_have}"
    
    return True, None


def craft_pill(recipe_code, user_id):
    """Luyện đan:
    1. Kiểm tra điều kiện
    2. Tiêu hao nguyên liệu
    3. Tính toán thành công
    4. Cơ cấu phúc
    5. Trả về kết quả (ok, message)
    """
    db = get_user_db()
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    
    # Lấy realm của người chơi từ số từ đã học
    words_learned = core.get_words_learned(user_id)
    realm_info = core.realm_info(words_learned)
    realm_idx = realm_info["idx"]
    
    ok, reason = can_craft_pill(recipe_code, user_id, realm_idx)
    if not ok:
        return False, reason
    
    # Tiêu hao nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        consume_inventory(user_id, mat_code, qty_need)
    
    # Tính toán thành công (với biến thể phúc)
    roll = random.random()
    success = roll < recipe["success_rate"]
    
    if success:
        # Thêm đan vào kho
        add_inventory(user_id, recipe_code, 1)
        message = f"✅ Luyện đan thành công! Nhận 1x {recipe['name']}"
    else:
        message = f"❌ Luyện đan thất bại. Nguyên liệu đã bị tiêu hao."
    
    # Ghi log
    log_game_action(user_id, "craft_pill", f"{recipe['name']}: {success}")
    
    return success, message


def use_pill(pill_code, user_id):
    """Sử dụng đan dược (giảm kho, trả về hiệu quả)."""
    recipe = cfg.PILL_RECIPES_BY_CODE[pill_code]
    consume_inventory(user_id, pill_code, 1)
    return recipe["bonus_atk_pct"]


def buy_pill_recipe(recipe_code, user_id):
    """Mua công thức luyện đan.
    
    Trả về (ok, reason)
    """
    db = get_user_db()
    
    # Kiểm tra đã mua chưa
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if has_recipe:
        return False, "Đã mua công thức này rồi"
    
    # Kiểm tra có đủ tiền
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    price = cfg.PILL_RECIPE_PRICE[recipe_code]
    linh_thach = get_linh_thach(user_id)
    
    if linh_thach < price:
        return False, f"Thiếu Linh Thạch: cần {price}, có {linh_thach}"
    
    # Mua
    add_linh_thach(user_id, -price)
    db.execute(
        "INSERT INTO game_pill_recipes (user_id, recipe_code) VALUES (?, ?)",
        (user_id, recipe_code)
    )
    db.commit()
    
    log_game_action(user_id, "buy_recipe", recipe_code)
    return True, f"✅ Mua công thức {recipe['name']} thành công!"
```

#### 4. **game_config.py** (Thêm helper để tìm công thức nhanh)

```python
PILL_RECIPES_BY_CODE = {p["code"]: p for p in PILL_RECIPES}
ITEM_NAME_BY_CODE = {
    # Vật phẩm từ item sets
    "r0_0": "Hắc Thiết", "r0_1": "Yêu Lang Bì", "r0_2": "Thanh Linh Thảo", ...
    # Đan dược
    "pill_1": "Hạ Phẩm Yêu Đan", "pill_2": "Trung Phẩm Yêu Đan", ...
}
```

---

## **PHẦN 3: KIỂM THỰC**

### Các kiểm tra bắt buộc:

1. **Quyền mua công thức**
   - ✅ Người chơi chưa mua: cho phép + tính tiền
   - ✅ Người chơi đã mua: từ chối mua lại
   - ✅ Không đủ tiền: từ chối, báo thiếu bao nhiêu

2. **Điều kiện tu vi**
   - ✅ Tu vi < yêu cầu: từ chối, báo cần bao nhiêu từ
   - ✅ Tu vi ≥ yêu cầu: cho phép

3. **Xác suất luyện thành công**
   - ✅ Roll < success_rate: thành công
   - ✅ Roll ≥ success_rate: thất bại

4. **Nguyên liệu**
   - ✅ Kiểm tra từng nguyên liệu cần
   - ✅ Tiêu hao khi luyện (dù thành công hay thất bại)

5. **Tồn kho**
   - ✅ Lưu đan thành công vào kho
   - ✅ Lấy kho khi dùng

---

## **PHẦN 4: CẬP NHẬT UI (ở Tab Cultivation)**

### Hiển thị:
- **Công thức mua** (unlock theo tu vi)
- **Luyện đan** (chọn công thức → luyện → kết quả)
- **Kho đan dược** (danh sách đan có, số lượng)
- **Sử dụng đan** (trong khi đi săn - Phiên 5)

---

## **IMPORTANT NOTES**

### ⚠️ Kỹ thuật:
1. **Tiêu hao nguyên liệu dù thất bại**: Phù hợp hệ thống chế tạo thực tế
2. **Công thức bật theo tu vi**: Mini-game Phiên 5 cần các công thức để tạo nguyên liệu
3. **Linh Thạch từ săn**: Sử dụng Linh Thạch từ các trò chơi khác (Fortune, Match, Hunt)

### 💡 Lưu ý thiết kế:
- **Tỷ lệ thành công giảm dần**: Công thức cao cấp rủi ro cao → cân bằng
- **Nguyên liệu từ săn**: Để tạo động lực đi săn → lấy nguyên liệu
- **Đan từ mini-game Phiên 5**: Luyện đan giúp tăng hiệu suất kiếm đan

---

## **READY FOR IMPLEMENTATION**

```
Status: SPECIFICATION COMPLETE
Next: Code Implementation → Unit Tests → E2E Tests
Test Focus: Purchase, Requirements, RNG, Inventory
```

---

**Phiên 4 Spec**: 2026-11-07  
**Status**: ✅ READY FOR CODING  
**Depends on**: Phase 2 (pháp bảo), Phase 3 (tu vi)  
**Next**: Phiên 5 (Mini-game)
