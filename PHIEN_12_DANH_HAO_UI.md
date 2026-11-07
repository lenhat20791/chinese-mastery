# Phiên 12: Giao Diện Danh Hào Mới

## Tóm Tắt Thay Đổi

### 1. Đổi Tên Tab
- **Cũ:** `🏅 Huy Hiệu`
- **Mới:** `🏅 Danh Hào`
- **Mã tab:** `"danh_hao"` (thay vì `"badges"`)

### 2. Hủy Bỏ Hệ Thống Danh Hiệu Cũ
- Xóa hàm `_render_badges(state, ctx)` khỏi `cultivation_tab.py`
- Hệ thống danh hiệu truyền thống (huy hiệu thành tích, ẩn) không còn hiển thị trong giao diện

### 3. Tạo File Giao Diện Mới
- **File:** `danh_hao_ui.py`
- **Hàm chính:** `render_danh_hao_tab()`
- **Định dạng:** Hiển thị theo cột: Danh hào | Điều kiện | Buff được nhận | Nút sử dụng

## Tính Năng Chi Tiết

### Layout Giao Diện
```
Danh hào | Điều kiện cần đạt | Buff được nhận | Thao tác
---------------------------------------------------------
⭕ Sơ nhập tiên lộ | Linh Khí Kỳ | +3% công | [🔗 Đeo]
✅ Chân nhân | Trúc Cơ Kỳ | +5% công +5% HP | [✅ Đeo]
...
```

### Các Nút Thao Tác
1. **Nút "🔗 Đeo"** (Danh hào chưa trang bị):
   - Click để trang bị danh hào
   - Danh hào cũ sẽ tự động bị tháo
   - Nhận buff tương ứng

2. **Nút "✅ Đeo"** (Danh hào đang trang bị):
   - Disabled (không thể bấm)
   - Hiển thị trạng thái đang hoạt động

3. **Nút "🔓 Tháo danh hào"** (Phần danh hào hiện tại):
   - Tháo danh hào đang đeo
   - Mất buff liên quan

### Điều Kiện Mở Khóa
- Mỗi danh hào có `realm_idx` tương ứng
- Người chơi chỉ có thể trang bị danh hào khi đạt cảnh giới >= `realm_idx`
- Ví dụ: "Sơ nhập tiên lộ" (realm_idx=0) mở khóa ở Linh Khí Kỳ

### Buff Nhận Được
Mỗi danh hào cấp:
- **ATK%**: Tăng % sát thương
- **HP%**: Tăng % sinh lực
- Buff được cộng vào bonus và ảnh hưởng đến `stat_bonuses()`

## Cấu Trúc Code

### File Thay Đổi
1. **cultivation_tab.py**
   - Import `danh_hao_ui`
   - Thay đổi `NAV` dict: `"badges": "🏅 Huy Hiệu"` → `"danh_hao": "🏅 Danh Hào"`
   - Thay `else: _render_badges(state, ctx)` → `elif page == "danh_hao": danh_hao_ui.render_danh_hao_tab()`
   - Xóa hàm `_render_badges`

2. **danh_hao_ui.py** (File mới)
   - Hàm `render_danh_hao_tab()`: Hiển thị giao diện danh hào
   - Sử dụng `core.available_honors(idx)` để lấy danh hào có sẵn
   - Gọi `core.equip_title(honor_code)` khi trang bị

### Hàm Game Core (Không Thay Đổi)
- `core.get_state()`: Lấy state hiện tại với `state["title"]`
- `core.available_honors(idx)`: Trả về list danh hào có thể trang bị ở cảnh giới `idx`
- `core.equip_title(code)`: Trang bị danh hào (hoặc `None` để tháo)
- `core.all_titles()`: Lấy dict {mã: tên} của tất cả danh hiệu và danh hào
- `core.stat_bonuses(words, answers, streak, honor_code)`: Tính bonus bao gồm buff danh hào

### Database
- Cột `equipped_title` đã tồn tại trong bảng `game_profile`
- Lưu mã danh hào đang trang bị (NULL = không đeo)

## Quy Trình Trang Bị Danh Hào

1. Người chơi click nút "🔗 Đeo"
2. Hệ thống gọi `core.equip_title(honor_code)`
3. `core.equip_title()`:
   - Kiểm tra danh hào có sẵn ở cảnh giới hiện tại?
   - Cập nhật `equipped_title` trong `game_profile`
   - Reload state
4. Giao diện rerun, hiển thị danh hào mới trang bị
5. Buff danh hào được áp dụng trong `stat_bonuses()` khi tính chỉ số

## Testing

### Kiểm Tra Cơ Bản
```python
# 1. Mở tab Danh Hào
# → Nên thấy danh hào khả dụng theo cảnh giới hiện tại

# 2. Click "🔗 Đeo" danh hào
# → Danh hào được trang bị
# → Buff được cộng vào chỉ số (ATK%, HP%)
# → Nút thay thành "✅ Đeo" (disabled)

# 3. Click "🔗 Đeo" danh hào khác
# → Danh hào cũ tự động bị tháo
# → Danh hào mới được trang bị
# → Buff cập nhật

# 4. Click "🔓 Tháo danh hào"
# → Danh hào bị tháo
# → Mất buff
# → Danh sách hiện danh hào "Chưa trang bị danh hào nào."
```

### Kiểm Tra Điều Kiện
- Ở Linh Khí Kỳ: Chỉ thấy "Sơ nhập tiên lộ"
- Ở Trúc Cơ Kỳ+: Thêm "Chân nhân"
- Ở cảnh giới cao: Danh sách danh hào tăng dần

## Danh Sách Danh Hào (HONOR_TITLES)

| Danh hào | realm_idx | ATK% | HP% |
|---------|-----------|------|-----|
| Sơ nhập tiên lộ | 0 | 3 | 0 |
| Chân nhân | 2 | 5 | 5 |
| Lão tổ | 3 | 7 | 7 |
| Tôn giả | 6 | 9 | 9 |
| Nửa bước chí tôn | 7 | 12 | 12 |
| Chí tôn nhân gian | 8 | 15 | 15 |
| Phi thăng tiên giới | 9 | 17 | 17 |
| Tung hoành tiên giới | 10 | 19 | 19 |
| Chí tôn tiên giới | 14 | 22 | 22 |
| Vĩnh hằng Tiên Đế | 15 | 25 | 25 |

## Ghi Chú

- Giao diện mới tập trung **chỉ** vào danh hào (hệ thống danh hiệu mới)
- Hệ thống huy hiệu thành tích cũ (thử thách, ẩn) không còn bị hiển thị
- Nếu cần quay lại huy hiệu, cần tạo tab riêng hoặc tích hợp lại vào danh hào
- Buff danh hào được cộng trực tiếp vào `stat_bonuses()`, không cần tính toán riêng
