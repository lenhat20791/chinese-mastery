# Phiên 5-6: Luyện Đan & Vẽ Phù - Hoàn Thành

**Ngày hoàn thành:** 2026-11-07  
**Commits:** b45fff1, 3ac5bf3

---

## 📋 Tóm Tắt

Phiên 5-6 thêm hai mini-game mới vào Động Phủ:
1. **⚗️ Luyện Đan** (Alchemy) - Chấm Hán tự để luyện đan
2. **🪬 Vẽ Phù** (Talisman) - Chấm Hán tự để vẽ phù bảo hộ

Cả hai mini-game sử dụng chung cơ chế: người chơi phải gõ đúng Hán tự một số lần nhất định để chế tạo thành công.

---

## ✅ Công Việc Hoàn Thành

### 1. Thêm Tab Giao Diện
- ✅ Thêm `⚗️ Luyện Đan` và `🪬 Vẽ Phù` vào **NAV** trong `cultivation_tab.py`
- ✅ Cập nhật **UNLOCK_KEY** - cả hai mini-game mở khóa sau khi mở khóa "Săn Yêu Thú"
- ✅ Thêm logic render trong `_body()` function

### 2. Tạo Hàm Render
- ✅ `render_alchemy()` trong `game_minigames.py`
  - Tab Công Thức: hiển thị 5 loại đan, giá cả, yêu cầu realm
  - Tab Luyện Viên: chọn công thức, gõ Hán tự, theo dõi tiến độ
  - Tab Kho Đan: hiển thị đan đã luyện, số lượng
  - Ảnh minh họa: `lo_dan.png`

- ✅ `render_talisman()` trong `game_minigames.py`
  - Tab Công Thức: hiển thị 6 loại phù, giá cả, yêu cầu realm, hiệu ứng
  - Tab Vẽ Phù: chọn công thức, gõ Hán tự, theo dõi tiến độ
  - Tab Kho Phù: hiển thị phù đã vẽ, số lượng
  - Ảnh minh họa: `phu_luc.png`

### 3. Cập Nhật Config
- ✅ **PILL_RECIPES**: thêm 4 fields cho mỗi loại
  - `min_idx`: mốc realm yêu cầu (0, 3, 6, 10, 15)
  - `correct_hits_needed`: số lần gõ đúng (10-30)
  - `description`: mô tả công dụng
  - `emoji`: biểu tượng (🧪)

- ✅ **TALISMAN_RECIPES**: thêm `min_idx` cho 6 loại
  - `min_idx`: mốc realm yêu cầu (1, 3, 5, 8, 11, 14)
  - Đã có sẵn `correct_hits_needed`, `description`

### 4. Viết Tests
- ✅ Tạo `test_phien_5_6.py` với 7 test cases:
  1. PILL_RECIPES structure (5 recipes ✓)
  2. TALISMAN_RECIPES structure (6 recipes ✓)
  3. Recipe prices mapping ✓
  4. render_alchemy/render_talisman functions exist ✓
  5. NAV entries (alchemy, talisman) ✓
  6. UNLOCK_KEY entries (both unlock after hunt) ✓
  7. All tests PASSED ✓

---

## 📊 Chi Tiết Mini-Games

### Luyện Đan (Alchemy)

**5 Công Thức Đan:**

| Mã | Tên | Min Realm | Gõ Đúng | Bonus | Giá |
|----|-----|-----------|---------|-------|-----|
| pill_1 | Hạ Phẩm Yêu Đan | 0 | 10 | +2% ATK | 50 |
| pill_2 | Trung Phẩm Yêu Đan | 3 | 15 | +5% ATK | 200 |
| pill_3 | Thượng Phẩm Yêu Đan | 6 | 20 | +8% ATK | 500 |
| pill_4 | Tối Thượng Yêu Đan | 10 | 25 | +12% ATK | 1500 |
| pill_5 | Tôn Thần Yêu Đan | 15 | 30 | +15% ATK | 3000 |

**Luồng:**
1. Mua công thức (trừ Linh Thạch)
2. Chọn công thức để luyện
3. Gõ đúng Hán tự từ pool học tập
4. Sau N lần gõ đúng → đan được luyện thành công
5. Lưu vào kho

### Vẽ Phù (Talisman)

**6 Công Thức Phù:**

| Mã | Tên | Min Realm | Gõ Đúng | Hiệu Ứng | Giá |
|----|-----|-----------|---------|----------|-----|
| talisman_1 | Bảo Hộ Phù | 1 | 10 | Giảm 15% sát thương | 100 |
| talisman_2 | Tăng Công Phù | 3 | 15 | +20% sát thương | 300 |
| talisman_3 | Hồi Phục Phù | 5 | 20 | Hồi 30% HP | 600 |
| talisman_4 | Phản Công Phù | 8 | 25 | Phản 25% sát thương | 1200 |
| talisman_5 | Trúc Chi Phù | 11 | 30 | +15% chí mạng | 2000 |
| talisman_6 | Trời Địa Phù | 14 | 35 | Tất cả hiệu ứng | 3500 |

**Luồng:**
1. Mua công thức (trừ Linh Thạch)
2. Chọn công thức để vẽ
3. Gõ đúng Hán tự từ pool học tập
4. Sau N lần gõ đúng → phù được vẽ thành công
5. Lưu vào kho

---

## 🎮 Cách Sử Dụng

### Đối với Người Chơi

1. **Mở khóa:** Phải đạt Realm 1+ (đã học ≥ từ để mở Săn Yêu Thú)
2. **Luyện Đan/Vẽ Phù:**
   - Bấm vào tab trong Động Phủ
   - Tab **📜 Công Thức**: Mua công thức nếu chưa có
   - Tab **⚗️ Luyện Viên / 🪬 Vẽ Phù**: Chọn công thức, gõ Hán tự
   - Khi đạt đủ số lần gõ đúng → tự động chế tạo thành công
   - Tab **🧪 Kho Đan / 🧿 Kho Phù**: Xem tích lũy

---

## 📁 Files Sửa Đổi/Tạo

### Tạo Mới
- `test_phien_5_6.py` - Test suite (7 tests, all passed)

### Sửa Đổi
- `game_minigames.py`
  - Thêm `from pathlib import Path` ở đầu
  - Thêm hàm `render_alchemy(ctx)`
  - Thêm hàm `render_talisman(ctx)`
  - Tổng cộng: +428 dòng mới

- `cultivation_tab.py`
  - Cập nhật NAV: +2 entries (alchemy, talisman)
  - Cập nhật UNLOCK_KEY: +2 entries
  - Cập nhật `_body()` function: +2 elif blocks

- `game_config.py`
  - PILL_RECIPES: +4 fields cho 5 recipes (min_idx, correct_hits_needed, description, emoji)
  - TALISMAN_RECIPES: +1 field (min_idx) cho 6 recipes

---

## 🔧 Kiểm Tra

```bash
# Chạy test
python test_phien_5_6.py
# Output:
# [OK] All 5 PILL_RECIPES have required fields
# [OK] All 6 TALISMAN_RECIPES have required fields
# [OK] All PILL_RECIPES have prices in PILL_RECIPE_PRICES
# [OK] All TALISMAN_RECIPES have prices in TALISMAN_RECIPE_PRICES
# [OK] render_alchemy and render_talisman functions exist
# [OK] NAV entries added: alchemy and talisman
# [OK] UNLOCK_KEY entries correct (both unlock after hunt)
# [SUCCESS] All tests passed! Phien 5-6 structure is correct.
```

---

## 🎯 Điểm Chính

✅ **Ảnh Minh Họa Đúng:**
- `lo_dan.png` → Luyện Đan tab
- `phu_luc.png` → Vẽ Phù tab
- (Không còn sai lấy ảnh từ Công Pháp Các)

✅ **Tab Chức Năng Đầy Đủ:**
- Luyện Đan có 3 tabs: Công Thức, Luyện Viên, Kho Đan
- Vẽ Phù có 3 tabs: Công Thức, Vẽ Phù, Kho Phù

✅ **Mini-Game Logic:**
- Người chơi gõ Hán tự → kiểm tra với `gq.check_hanzi_match()`
- Hỗ trợ Hán tự có dấu hoặc không dấu
- Hiển thị tiến độ gõ đúng
- Tự động chế tạo khi đạt số lần đủ

✅ **Unlock System:**
- Cả hai mini-game mở khóa khi người chơi mở Săn Yêu Thú (Realm 1+)

---

## 📝 Commit Messages

1. **b45fff1** - Phien 5-6: Add Alchemy (Luyen Dan) and Talisman (Ve Phu) minigames with UI tabs
2. **3ac5bf3** - Fix: Add min_idx to talisman_6 and update Path import

---

## ✨ Kết Quả

**Phiên 5-6 HOÀN THÀNH** ✓

Hai mini-game mới đã được thêm vào giao diện Động Phủ với:
- ✓ Tab giao diện riêng
- ✓ Ảnh minh họa chính xác
- ✓ Cơ chế chế tạo (chấm Hán tự)
- ✓ Kho lưu trữ sản phẩm
- ✓ Hệ thống mở khóa
- ✓ 7/7 tests passed

Bạn sẽ thấy hai tab mới trong Động Phủ sau khi mở khóa Săn Yêu Thú!
