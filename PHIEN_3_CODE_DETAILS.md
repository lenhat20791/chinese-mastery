# 📝 PHIÊN 3 - CODE DETAILS

## **1. game_config.py - Thêm cấu hình Cultivation Boost**

**Vị trí**: Dòng 119-120 (trong phần "Chỉ số tu luyện")

```python
# Cũ (Phiên 2)
DAO_TAM_MAX, DAO_TAM_K = 0.25, 90    # Đạo tâm (chuỗi ngày) -> giảm sát thương Tâm Ma Kiếp
TAM_MA_K = 30

# Mới (Phiên 3)
DAO_TAM_MAX, DAO_TAM_K = 0.25, 90    # Đạo tâm (chuỗi ngày) -> giảm sát thương Tâm Ma Kiếp
CULTIVATION_BOOST_ATK_PCT = 5.0      # tăng 5% sát thương cơ bản mỗi cấp tu vi
CULTIVATION_BOOST_HP_PCT = 5.0       # tăng 5% HP cơ bản mỗi cấp tu vi
TAM_MA_K = 30
```

**Ý nghĩa**:
- `CULTIVATION_BOOST_ATK_PCT = 5.0`: Realm tăng 1 cấp → ATK cơ bản tăng 5%
- `CULTIVATION_BOOST_HP_PCT = 5.0`: Realm tăng 1 cấp → HP cơ bản tăng 5%
- Độc lập, có thể điều chỉnh riêng sau này

---

## **2. game_core.py - Thêm hàm `cultivation_boost()`**

**Vị trí**: Dòng 98-102 (sau hàm `diminishing()`)

### Hàm mới:
```python
def cultivation_boost(idx):
    """Boost chỉ số cơ bản theo tu vi: +5% ATK và +5% HP mỗi cấp. Trả về (atk_pct, hp_pct)."""
    atk_pct = (cfg.CULTIVATION_BOOST_ATK_PCT / 100.0) * idx
    hp_pct = (cfg.CULTIVATION_BOOST_HP_PCT / 100.0) * idx
    return atk_pct, hp_pct
```

### Ví dụ:
```python
cultivation_boost(0)   # (0.0, 0.0)         - Realm 0: Không boost
cultivation_boost(1)   # (0.05, 0.05)       - Realm 1: +5%
cultivation_boost(5)   # (0.25, 0.25)       - Realm 5: +25%
cultivation_boost(15)  # (0.75, 0.75)       - Realm 15: +75%
```

---

## **3. game_core.py - Cập nhật hàm `player_stats()`**

**Vị trí**: Dòng 125-147

### Cũ (Phiên 2):
```python
def player_stats(idx, artifacts=None, bonuses=None):
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
    atk, hp = base_atk, base_hp
    for art in artifacts or []:
        recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
        flat, pct = artifact_bonus(recipe, art["quality"], art["upgrade"])
        if recipe["kind"] == "atk":
            atk += flat + base_atk * pct
        else:
            hp += flat + base_hp * pct
    b = bonuses or {}
    return {"atk": atk * (1 + b.get("atk", 0)), "hp": hp * (1 + b.get("hp", 0)), "crit": b.get("crit", 0.0)}
```

### Mới (Phiên 3):
```python
def player_stats(idx, artifacts=None, bonuses=None):
    # Chỉ số cơ bản theo tu vi
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
    
    # Boost chỉ số cơ bản theo cultivation level (5% mỗi cấp tu vi)
    cult_atk_pct, cult_hp_pct = cultivation_boost(idx)
    boosted_base_atk = base_atk * (1 + cult_atk_pct)
    boosted_base_hp = base_hp * (1 + cult_hp_pct)
    
    atk, hp = boosted_base_atk, boosted_base_hp
    
    # Cộng pháp bảo (tính % trên chỉ số cơ bản đã được boost)
    for art in artifacts or []:
        recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
        flat, pct = artifact_bonus(recipe, art["quality"], art["upgrade"])
        if recipe["kind"] == "atk":
            atk += flat + boosted_base_atk * pct
        else:
            hp += flat + boosted_base_hp * pct
    
    # Cộng bonus từ các yếu tố khác (Căn cơ, Danh hào, Đạo tâm)
    # KHÔNG cộng dồn cultivation boost lại
    b = bonuses or {}
    return {"atk": atk * (1 + b.get("atk", 0)), "hp": hp * (1 + b.get("hp", 0)), "crit": b.get("crit", 0.0)}
```

### So sánh (dòng thay đổi):
| Cũ | Mới |
|----|-----|
| `atk, hp = base_atk, base_atk` | Thêm 3 dòng tính boost + `atk, hp = boosted_base_atk, boosted_base_hp` |
| `atk += flat + base_atk * pct` | `atk += flat + boosted_base_atk * pct` (dùng base đã boost) |
| `hp += flat + base_hp * pct` | `hp += flat + boosted_base_hp * pct` (dùng base đã boost) |

### Lợi ích:
1. ✅ Cultivation boost áp dụng **trên chỉ số cơ bản** (trước pháp bảo)
2. ✅ Pháp bảo tính % trên **base đã boost** → pháp bảo mạnh hơn ở cấp cao
3. ✅ Bonus khác (Căn cơ, Danh hào) cộng **1 lần cuối** → KHÔNG cộng dồn

---

## **4. tests/test_game.py - Thêm 4 test cases**

### Test 1: `test_cultivation_boost()` (Dòng 123-153)
```python
def test_cultivation_boost(self):
    """Kiểm tra boost chỉ số cơ bản theo tu vi: +5% ATK và +5% HP mỗi cấp."""
    # Test hàm cultivation_boost
    atk_pct_0, hp_pct_0 = core.cultivation_boost(0)
    self.assertEqual((atk_pct_0, hp_pct_0), (0, 0))
    
    atk_pct_1, hp_pct_1 = core.cultivation_boost(1)
    self.assertAlmostEqual(atk_pct_1, cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
    self.assertAlmostEqual(hp_pct_1, cfg.CULTIVATION_BOOST_HP_PCT / 100.0)
    
    # ... kiểm tra realm 10 ...
    
    # Test player_stats với cultivation boost
    stats_0 = core.player_stats(0)
    stats_1 = core.player_stats(1)
    
    # Ở realm 0: không có boost
    self.assertAlmostEqual(stats_0["atk"], cfg.PLAYER_BASE_ATK)
    
    # Ở realm 1: +5% boost
    expected_atk_1 = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 1 * (1 + cfg.CULTIVATION_BOOST_ATK_PCT / 100.0)
    self.assertAlmostEqual(stats_1["atk"], expected_atk_1)
    
    # ... kiểm tra realm 10 và double-stacking ...
```

**Kiểm tra**:
- Hàm `cultivation_boost()` trả về % đúng
- `player_stats()` tính chỉ số đúng ở từng realm
- Cultivation boost KHÔNG cộng dồn với bonus khác

---

### Test 2: `test_cultivation_progression_e2e()` (Dòng 155-192)
```python
def test_cultivation_progression_e2e(self):
    """E2E test: Tăng cấp từ realm 0 -> 15 và xác nhận chỉ số được tính đúng."""
    for idx in range(16):
        stats = core.player_stats(idx)
        atk = stats["atk"]
        hp = stats["hp"]
        
        # Kiểm tra chỉ số tăng khi lên cấp
        if prev_atk is not None:
            self.assertGreaterEqual(atk, prev_atk)
        
        # Kiểm tra cultivation boost được tính đúng
        expected_atk_pct, expected_hp_pct = core.cultivation_boost(idx)
        expected_atk = base_atk * (1 + expected_atk_pct)
        expected_hp = base_hp * (1 + expected_hp_pct)
        self.assertAlmostEqual(atk, expected_atk, places=5)
        
        # Kiểm tra boost % tăng đều đặn: +5% mỗi cấp
        if idx > 0:
            diff_atk_pct = expected_atk_pct - prev_atk_pct
            expected_diff = cfg.CULTIVATION_BOOST_ATK_PCT / 100.0
            self.assertAlmostEqual(diff_atk_pct, expected_diff, places=9)
```

**Kiểm tra**:
- E2E: Từ realm 0→15, chỉ số luôn tăng
- Cultivation boost được tính đúng ở từng realm
- Boost tăng đều đặn: +5% mỗi cấp

---

### Test 3: `test_backward_compatibility_realm_0()` (Dòng 194-204)
```python
def test_backward_compatibility_realm_0(self):
    """Backward compatibility: Realm 0 (Sơ nhập tiên lộ) không có boost, chỉ số giống như cũ."""
    # Ở realm 0, cultivation boost = 0%
    atk_pct_0, hp_pct_0 = core.cultivation_boost(0)
    self.assertEqual((atk_pct_0, hp_pct_0), (0, 0))
    
    # player_stats(0) không có boost => chỉ số = chỉ số cơ bản
    stats_0 = core.player_stats(0)
    expected_atk_0 = cfg.PLAYER_BASE_ATK
    expected_hp_0 = cfg.PLAYER_BASE_HP
    self.assertAlmostEqual(stats_0["atk"], expected_atk_0)
    self.assertAlmostEqual(stats_0["hp"], expected_hp_0)
```

**Kiểm tra**:
- Realm 0 KHÔNG có boost (0%)
- Chỉ số realm 0 = chỉ số cơ bản (giống Phiên 2)
- User cũ không bị ảnh hưởng (backward compatible)

---

### Test 4: `test_no_double_stacking()` (Dòng 206-227)
```python
def test_no_double_stacking(self):
    """Kiểm tra: Cultivation boost KHÔNG cộng dồn với bonus từ Căn cơ/Danh hào/Đạo tâm."""
    # Tạo state với nhiều bonus
    bonus = core.stat_bonuses(words=5000, answers=5000, streak=180, honor_code="so_nhap_tien_lo")
    
    # Tính stats ở realm 5 với bonus
    stats_with_bonus = core.player_stats(5, bonuses=bonus)
    
    # Tính chỉ số từng bước
    atk_pct, hp_pct = core.cultivation_boost(5)
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** 5
    boosted_base_atk = base_atk * (1 + atk_pct)
    
    # Chỉ số cuối = boosted_base * (1 + bonus) - KHÔNG cộng dồn cultivation lại
    expected_atk = boosted_base_atk * (1 + bonus["atk"])
    
    self.assertAlmostEqual(stats_with_bonus["atk"], expected_atk, places=5)
```

**Kiểm tra**:
- Cultivation boost + Căn cơ + Danh hào: KHÔNG cộng dồn
- Công thức: `final = boosted_base × (1 + bonus)`, **KHÔNG** `boosted_base × (1 + bonus1) × (1 + bonus2)`

---

## **5. Test Results**

```
test_cultivation_boost (tests.test_game.PureLogicTests) ... ok
test_cultivation_progression_e2e (tests.test_game.PureLogicTests) ... ok
test_backward_compatibility_realm_0 (tests.test_game.PureLogicTests) ... ok
test_no_double_stacking (tests.test_game.PureLogicTests) ... ok
test_stat_bonuses (tests.test_game.PureLogicTests) ... ok

Ran 5 tests in 0.001s
OK
```

---

## **6. Ví dụ Cụ Thể**

### Scenario: Realm 5, Pháp Bảo Thanh Phong Kiếm, Căn Cơ, Danh Hào

**Cấu hình**:
- PLAYER_BASE_ATK = 12
- POWER_PER_REALM = 1.25
- CULTIVATION_BOOST_ATK_PCT = 5.0
- Thanh Phong Kiếm (ATK pháp): flat=100, pct=0.3
- Căn Cơ (từ học 5000): +5%
- Danh Hào "Chân nhân": +5%

**Tính toán**:

1. **Chỉ số cơ bản**:
   ```
   base_atk = 12 × 1.25^5 = 12 × 3.0518 ≈ 36.62
   ```

2. **Cultivation boost** (Realm 5):
   ```
   cult_atk_pct = 5% × 5 = 25%
   boosted_base_atk = 36.62 × (1 + 0.25) = 45.78
   ```

3. **Pháp bảo** (Thanh Phong Kiếm):
   ```
   atk = 45.78 + 100 + 45.78 × 0.3 = 45.78 + 100 + 13.73 ≈ 159.51
   ```

4. **Bonus khác** (Căn cơ + Danh hào):
   ```
   can_co = +5%
   honor = +5%
   total_bonus = 5% + 5% = 10%
   
   final_atk = 159.51 × (1 + 0.10) = 175.46
   ```

**Kết quả**: ATK ≈ **175.46**

---

## **7. So Sánh Cũ vs Mới**

### Phiên 2 (Cũ) - Không có Cultivation Boost:
```
base_atk = 36.62
atk = 36.62 + 100 + 36.62 × 0.3 = 46.41 + 100 ≈ 146.41
final_atk = 146.41 × 1.10 ≈ 161.05
```

### Phiên 3 (Mới) - Có Cultivation Boost:
```
boosted_base = 36.62 × 1.25 = 45.78  (25% từ cultivation boost)
atk = 45.78 + 100 + 45.78 × 0.3 ≈ 159.51
final_atk = 159.51 × 1.10 ≈ 175.46
```

**Tăng**: 175.46 / 161.05 ≈ 1.089 = **+8.9%** (gần bằng cultivation boost 25% tính trên base)

---

## **TỔNG KẾT**

✅ Logic cultivation boost rõ ràng: +5% mỗi cấp  
✅ Tính toán từng bước, KHÔNG cộng dồn  
✅ Backward compatible (Realm 0 giữ nguyên)  
✅ Test đầy đủ, tất cả PASS  
✅ Ready for next phase
