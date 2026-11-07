# 📝 PHIÊN 4 - IMPLEMENTATION DETAILS

## **1. game_config.py - Cấu hình Đan Dược**

### Vị trí: Sau `ITEM_SETS` (khoảng dòng 365)

```python
# ---------------------------------------------------------------------------
# Công thức luyện đan
# ---------------------------------------------------------------------------
PILL_RECIPES = [
    {
        "code": "pill_1",
        "name": "Hạ Phẩm Yêu Đan",
        "min_realm": 0,
        "materials": [("r0_0", 2), ("r0_1", 1)],  # 2x Hắc Thiết, 1x Yêu Lang Bì
        "bonus_atk_pct": 2.0,
        "success_rate": 0.80,
    },
    {
        "code": "pill_2",
        "name": "Trung Phẩm Yêu Đan",
        "min_realm": 3,
        "materials": [("r0_3", 2), ("pill_1", 1)],  # 2x Tinh Thiết, 1x Hạ Phẩm Yêu Đan
        "bonus_atk_pct": 5.0,
        "success_rate": 0.70,
    },
    {
        "code": "pill_3",
        "name": "Thượng Phẩm Yêu Đan",
        "min_realm": 6,
        "materials": [("r1_2", 3), ("r1_4", 2)],  # 3x Huyền Thiết, 2x Xích Tinh Thạch
        "bonus_atk_pct": 8.0,
        "success_rate": 0.60,
    },
    {
        "code": "pill_4",
        "name": "Tối Thượng Yêu Đan",
        "min_realm": 10,
        "materials": [("r2_0", 3), ("r2_4", 2), ("r2_4", 1)],  # 3x Hàn Thiết, 2x Thiên Lôi Mộc, 1x Hàn Ngọc
        "bonus_atk_pct": 12.0,
        "success_rate": 0.50,
    },
    {
        "code": "pill_5",
        "name": "Tôn Thần Yêu Đan",
        "min_realm": 15,
        "materials": [("r3_2", 4), ("r3_4", 3), ("r3_5", 1)],  # 4x Linh Mộc Tâm, 3x Thiên Lôi Mộc, 1x Tiên Duyên
        "bonus_atk_pct": 15.0,
        "success_rate": 0.40,
    },
]

# Bảng giá mua công thức (Linh Thạch)
PILL_RECIPE_PRICES = {
    "pill_1": 50,
    "pill_2": 200,
    "pill_3": 500,
    "pill_4": 1500,
    "pill_5": 3000,
}

# Mapping nhanh
PILL_RECIPES_BY_CODE = {p["code"]: p for p in PILL_RECIPES}

# Tên vật phẩm
ITEM_NAMES = {
    "r0_0": "Hắc Thiết",
    "r0_1": "Yêu Lang Bì",
    "r0_2": "Thanh Linh Thảo",
    "r0_3": "Tinh Thiết",
    "r0_4": "Hạ Phẩm Yêu Đan",
    "r0_5": "Linh Mộc Tâm",
    
    "r1_0": "Huyền Thiết",
    "r1_1": "Hỏa Giao Lân",
    "r1_2": "Tử Linh Chi",
    "r1_3": "Xích Tinh Thạch",
    "r1_4": "Trung Phẩm Yêu Đan",
    "r1_5": "Kim Đan Tinh Hoa",
    
    "r2_0": "Hàn Thiết",
    "r2_1": "Băng Giao Cốt",
    "r2_2": "Tuyết Liên Diệp",
    "r2_3": "Hàn Ngọc",
    "r2_4": "Lôi Tinh",
    "r2_5": "Thiên Lôi Mộc",
    
    "r3_0": "U Minh Thiết",
    "r3_1": "Hoang Mạc Sa Tinh",
    "r3_2": "Vân Hải Linh Tảo",
    "r3_3": "Cố Ngọc",
    "r3_4": "Thiên Lôi Mộc",
    "r3_5": "Tiên Duyên",
    
    "pill_1": "Hạ Phẩm Yêu Đan",
    "pill_2": "Trung Phẩm Yêu Đan",
    "pill_3": "Thượng Phẩm Yêu Đan",
    "pill_4": "Tối Thượng Yêu Đan",
    "pill_5": "Tôn Thần Yêu Đan",
}
```

---

## **2. userdb.py - Thêm Bảng Đan Dược**

### Vị trí: Trong `SCHEMA` (sau `game_recipes`)

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

### Cập nhật `BACKUP_TABLES` (trong backup_manager.py):

```python
BACKUP_TABLES = {
    # ... tables khác ...
    "game_pills": ["user_id", "pill_code", "qty"],
    "game_pill_recipes": ["user_id", "recipe_code"],
}
```

---

## **3. game_core.py - Hàm Luyện Đan**

### Vị trí: Sau hàm `diminishing()` (khoảng dòng 170)

```python
# ---------------------------------------------------------------------------
# Luyện Đan - Alchemy System
# ---------------------------------------------------------------------------

def get_inventory_qty(user_id, item_code):
    """Lấy số lượng vật phẩm trong kho."""
    db = get_user_db()
    row = db.execute(
        "SELECT qty FROM game_inventory WHERE user_id = ? AND item_code = ?",
        (user_id, item_code)
    ).fetchone()
    return row[0] if row else 0


def set_inventory_qty(user_id, item_code, qty):
    """Cập nhật số lượng vật phẩm."""
    db = get_user_db()
    if qty <= 0:
        db.execute("DELETE FROM game_inventory WHERE user_id = ? AND item_code = ?", (user_id, item_code))
    else:
        db.execute(
            "INSERT OR REPLACE INTO game_inventory (user_id, item_code, qty) VALUES (?, ?, ?)",
            (user_id, item_code, qty)
        )
    db.commit()


def add_inventory(user_id, item_code, qty):
    """Thêm vật phẩm vào kho."""
    current = get_inventory_qty(user_id, item_code)
    set_inventory_qty(user_id, item_code, current + qty)


def consume_inventory(user_id, item_code, qty):
    """Tiêu hao vật phẩm từ kho."""
    current = get_inventory_qty(user_id, item_code)
    if current < qty:
        return False
    set_inventory_qty(user_id, item_code, current - qty)
    return True


def get_pills_inventory(user_id):
    """Lấy danh sách đan dược trong kho."""
    db = get_user_db()
    rows = db.execute(
        "SELECT pill_code, qty FROM game_pills WHERE user_id = ? AND qty > 0 ORDER BY pill_code",
        (user_id,)
    ).fetchall()
    result = []
    for code, qty in rows:
        if code in cfg.PILL_RECIPES_BY_CODE:
            recipe = cfg.PILL_RECIPES_BY_CODE[code]
            result.append({"code": code, "name": recipe["name"], "qty": qty, "bonus": recipe["bonus_atk_pct"]})
    return result


def can_craft_pill(recipe_code, user_id, realm_idx):
    """Kiểm tra điều kiện luyện đan.
    
    Trả về (ok, reason_if_not_ok)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại"
    
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    db = get_user_db()
    
    # 1. Kiểm tra có công thức
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if not has_recipe:
        return False, "Chưa mua công thức này"
    
    # 2. Kiểm tra tu vi
    if realm_idx < recipe["min_realm"]:
        need_words = cfg.SUB_THRESHOLDS[recipe["min_realm"] * 3] if recipe["min_realm"] * 3 < len(cfg.SUB_THRESHOLDS) else 2500
        return False, f"Cần tu vi Realm {recipe['min_realm']} (≈ {need_words} từ)"
    
    # 3. Kiểm tra nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        qty_have = get_inventory_qty(user_id, mat_code)
        if qty_have < qty_need:
            mat_name = cfg.ITEM_NAMES.get(mat_code, mat_code)
            return False, f"Thiếu {mat_name}: cần {qty_need}, có {qty_have}"
    
    return True, None


def craft_pill(recipe_code, user_id):
    """Luyện một viên đan.
    
    1. Kiểm tra điều kiện
    2. Tiêu hao nguyên liệu
    3. Tính xác suất thành công
    4. Cập nhật kho
    
    Trả về (success, message)
    """
    # Lấy thông tin người chơi
    words_learned = get_words_learned(user_id)
    realm_info_data = realm_info(words_learned)
    realm_idx = realm_info_data["idx"]
    
    # Kiểm tra điều kiện
    ok, reason = can_craft_pill(recipe_code, user_id, realm_idx)
    if not ok:
        return False, reason
    
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    db = get_user_db()
    
    # Tiêu hao nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        if not consume_inventory(user_id, mat_code, qty_need):
            return False, f"Lỗi: không thể tiêu hao {cfg.ITEM_NAMES.get(mat_code, mat_code)}"
    
    # Tính toán thành công
    roll = random.random()
    success = roll < recipe["success_rate"]
    
    if success:
        # Thêm đan vào kho
        add_pill(user_id, recipe_code, 1)
        message = f"✅ Luyện đan thành công! Nhận 1x {recipe['name']}"
    else:
        message = f"❌ Luyện đan thất bại. Nguyên liệu đã bị tiêu hao."
    
    # Ghi log (tùy chọn)
    log_game_action(user_id, "craft_pill", f"{recipe['name']}: {success}")
    
    return success, message


def add_pill(user_id, pill_code, qty):
    """Thêm đan dược vào kho."""
    db = get_user_db()
    current = db.execute(
        "SELECT qty FROM game_pills WHERE user_id = ? AND pill_code = ?",
        (user_id, pill_code)
    ).fetchone()
    
    new_qty = (current[0] if current else 0) + qty
    db.execute(
        "INSERT OR REPLACE INTO game_pills (user_id, pill_code, qty) VALUES (?, ?, ?)",
        (user_id, pill_code, new_qty)
    )
    db.commit()


def buy_pill_recipe(recipe_code, user_id):
    """Mua công thức luyện đan.
    
    Trả về (success, message)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại"
    
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
    price = cfg.PILL_RECIPE_PRICES.get(recipe_code, 0)
    
    profile = get_game_profile(user_id)
    linh_thach = profile["linh_thach"]
    
    if linh_thach < price:
        missing = price - linh_thach
        return False, f"Thiếu Linh Thạch: cần {price}, có {linh_thach} (thiếu {missing})"
    
    # Mua công thức
    set_linh_thach(user_id, linh_thach - price)
    db.execute(
        "INSERT INTO game_pill_recipes (user_id, recipe_code) VALUES (?, ?)",
        (user_id, recipe_code)
    )
    db.commit()
    
    log_game_action(user_id, "buy_recipe", recipe_code)
    return True, f"✅ Mua công thức {recipe['name']} thành công!"


def get_pill_recipes_owned(user_id):
    """Lấy danh sách công thức mà người chơi đã mua."""
    db = get_user_db()
    rows = db.execute(
        "SELECT recipe_code FROM game_pill_recipes WHERE user_id = ? ORDER BY recipe_code",
        (user_id,)
    ).fetchall()
    result = []
    for (code,) in rows:
        if code in cfg.PILL_RECIPES_BY_CODE:
            result.append(cfg.PILL_RECIPES_BY_CODE[code])
    return result


def get_words_learned(user_id):
    """Lấy số từ đã học (cấp độ mastered)."""
    db = get_user_db()
    row = db.execute(
        "SELECT COUNT(DISTINCT vocab_id) FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchone()
    return row[0] if row else 0


def log_game_action(user_id, kind, text):
    """Ghi log hoạt động (tùy chọn)."""
    try:
        db = get_user_db()
        now = today()
        db.execute(
            "INSERT INTO game_log (user_id, ts, kind, text) VALUES (?, ?, ?, ?)",
            (user_id, now, kind, text)
        )
        db.commit()
    except Exception:
        pass
```

---

## **4. Tích hợp với Existing Functions**

### Cập nhật `get_game_profile()` nếu chưa có:
```python
def get_game_profile(user_id):
    """Lấy profile trò chơi của người chơi."""
    db = get_user_db()
    row = db.execute(
        "SELECT linh_thach, equipped_artifact, equipped_title, pity_mid, pity_high, fortune_streak, fortune_last_day "
        "FROM game_profile WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    if not row:
        db.execute("INSERT INTO game_profile (user_id, linh_thach) VALUES (?, 0)", (user_id,))
        db.commit()
        return {
            "linh_thach": 0, "equipped_artifact": None, "equipped_title": None,
            "pity_mid": 0, "pity_high": 0, "fortune_streak": 0, "fortune_last_day": None
        }
    return {
        "linh_thach": row[0],
        "equipped_artifact": row[1],
        "equipped_title": row[2],
        "pity_mid": row[3],
        "pity_high": row[4],
        "fortune_streak": row[5],
        "fortune_last_day": row[6],
    }


def set_linh_thach(user_id, amount):
    """Cập nhật Linh Thạch."""
    db = get_user_db()
    db.execute("UPDATE game_profile SET linh_thach = ? WHERE user_id = ?", (amount, user_id))
    db.commit()
```

---

## **5. Test Cases (tests/test_game.py)**

### Thêm test cases cho Phase 4:

```python
class TestAlchemy(unittest.TestCase):
    """Test hệ thống luyện đan."""
    
    def setUp(self):
        self.user_id = 1
        # Reset kho người dùng
        db = userdb.get_user_db()
        db.execute("DELETE FROM game_inventory WHERE user_id = ?", (self.user_id,))
        db.execute("DELETE FROM game_pill_recipes WHERE user_id = ?", (self.user_id,))
        db.execute("DELETE FROM game_pills WHERE user_id = ?", (self.user_id,))
        db.commit()
    
    def test_buy_recipe_success(self):
        """Mua công thức thành công."""
        core.set_linh_thach(self.user_id, 500)
        ok, msg = core.buy_pill_recipe("pill_1", self.user_id)
        self.assertTrue(ok)
        self.assertIn("✅", msg)
    
    def test_buy_recipe_insufficient_funds(self):
        """Mua công thức, thiếu tiền."""
        core.set_linh_thach(self.user_id, 10)
        ok, msg = core.buy_pill_recipe("pill_1", self.user_id)
        self.assertFalse(ok)
        self.assertIn("Thiếu", msg)
    
    def test_buy_recipe_duplicate(self):
        """Không thể mua lại công thức đã mua."""
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_1", self.user_id)
        ok, msg = core.buy_pill_recipe("pill_1", self.user_id)
        self.assertFalse(ok)
        self.assertIn("đã mua", msg)
    
    def test_craft_pill_no_recipe(self):
        """Luyện đan nhưng chưa mua công thức."""
        ok, msg = core.craft_pill("pill_1", self.user_id)
        self.assertFalse(ok)
        self.assertIn("chưa mua", msg)
    
    def test_craft_pill_insufficient_realm(self):
        """Luyện đan nhưng realm chưa đủ."""
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_3", self.user_id)  # min_realm 6
        # user ở realm 0
        ok, msg = core.craft_pill("pill_3", self.user_id)
        self.assertFalse(ok)
        self.assertIn("tu vi", msg.lower())
    
    def test_craft_pill_insufficient_materials(self):
        """Luyện đan nhưng thiếu nguyên liệu."""
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_1", self.user_id)
        core.add_inventory(self.user_id, "r0_0", 1)  # Chỉ có 1, cần 2
        ok, msg = core.craft_pill("pill_1", self.user_id)
        self.assertFalse(ok)
        self.assertIn("Thiếu", msg)
    
    def test_craft_pill_success(self):
        """Luyện đan thành công."""
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_1", self.user_id)
        core.add_inventory(self.user_id, "r0_0", 2)
        core.add_inventory(self.user_id, "r0_1", 1)
        
        # Mock thành công
        with unittest.mock.patch("random.random", return_value=0.5):
            ok, msg = core.craft_pill("pill_1", self.user_id)
            self.assertTrue(ok)
            self.assertIn("✅", msg)
            
            # Kiểm tra kho được cập nhật
            qty = core.get_pills_inventory(self.user_id)[0]["qty"]
            self.assertEqual(qty, 1)
    
    def test_craft_pill_failure(self):
        """Luyện đan thất bại."""
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_1", self.user_id)
        core.add_inventory(self.user_id, "r0_0", 2)
        core.add_inventory(self.user_id, "r0_1", 1)
        
        # Mock thất bại
        with unittest.mock.patch("random.random", return_value=0.9):
            ok, msg = core.craft_pill("pill_1", self.user_id)
            self.assertTrue(ok)  # Chỉnh lại: thất bại vẫn là "ok" vì không có lỗi
            self.assertIn("❌", msg)
            
            # Kiểm tra nguyên liệu bị tiêu hao
            qty_r0_0 = core.get_inventory_qty(self.user_id, "r0_0")
            self.assertEqual(qty_r0_0, 0)
```

---

## **READY FOR TESTING**

```
Files Modified:
  ✅ game_config.py: +30 lines (PILL_RECIPES config)
  ✅ userdb.py: +2 tables (game_pills, game_pill_recipes)
  ✅ game_core.py: +200 lines (craft, buy, inventory functions)
  ✅ backup_manager.py: Update BACKUP_TABLES (2 tables)
  ✅ tests/test_game.py: +8 test cases

Next: Run tests, verify UI integration (Phiên 5)
```

---

**Phiên 4 Code Details**: 2026-11-07  
**Status**: ✅ READY FOR CODE INTEGRATION  
