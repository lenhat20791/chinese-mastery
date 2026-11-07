# Phiên 11: Thiết Kế Lại Giao Diện Công Pháp Các

## 📋 Tóm Tắt Thay Đổi

### Vấn đề Cũ (Phiên 10)
- Giao diện công pháp được chia thành 3 subtab: "Kho Công Pháp", "Đan Điền", "Trang Bị"
- Người dùng phải chọn vị trí (hàng, cột) thủ công để đặt công pháp
- Khung đan điền là grid 4×5 nhưng mỗi công pháp chiếm ô khác nhau (size ngẫu nhiên)
- Không có cơ chế auto-placement

### Giải Pháp Mới (Phiên 11)
✅ **Giao diện thống nhất 1 layout**
- **Panel trái (40%):** Danh sách công pháp đã thu thập
- **Panel phải (60%):** Khung đan điền 4×5 + Thông tin buff tổng hợp

✅ **Auto-Placement System**
- Người chơi chỉ cần click "Sử dụng" → công pháp tự tìm ô trống phù hợp
- Hệ thống tự tính kích thước công pháp dựa trên đẳng cấp (cao = to, buff nhiều)

✅ **Visual Enhancements**
- Công pháp được hiển thị với **màu theo đẳng cấp**
- Kích thước hiển thị trên grid = kích thước thực tế chiếm
- Tooltip khi rê chuột: Tên, Đẳng cấp, Tu vi (+%), Buff chỉ số

✅ **Chức Năng Sắp Xếp**
- Nút "Sắp xếp tối ưu": Tái tổ chức công pháp để tiết kiệm diện tích tối đa
- Nút "Thu hồi tất cả": Xóa toàn bộ công pháp khỏi đan điền
- Click vào công pháp trong đan điền → Thu hồi riêng

✅ **Thông Tin Buff Thống Nhất**
- Bảng tổng buff hiển thị:
  - Tổng HP buff: Σ(hp_mult) từ tất cả công pháp đang sử dụng
  - Tổng ATK buff: Σ(atk_mult) từ tất cả công pháp đang sử dụng
  - Danh sách chi tiết các công pháp + buff riêng của mỗi cái

## 🎨 Layout Chi Tiết

```
┌─────────────────────────────────────────────────────┐
│  📜 Công Pháp Các                                   │
│  Chọn công pháp để sử dụng, hệ thống sẽ tự động... │
├────────────────────┬─────────────────────────────────┤
│                    │                                 │
│   Panel Trái       │      Panel Phải                 │
│   (Danh sách)      │      (Khung Đan Điền)           │
│                    │                                 │
│  📜 Công Pháp Sở   │    💎 Khung Đan Điền (4×5)     │
│  Hữu               │                                 │
│                    │    ┌─┐┌─┐┌─┐┌─┐┌─┐             │
│  ═══════════════   │    ├─┼─┼─┼─┼─┤                 │
│  🌪️ Xâm Cơ       │    ├─┼─┼─┼─┼─┤                 │
│  Thanh Phong Kiếm  │    ├─┼─┼─┼─┼─┤                 │
│  3×3, 5% HP        │    ├─┼─┼─┼─┼─┤                 │
│  ✨ [Sử dụng]     │    └─┘└─┘└─┘└─┘└─┘             │
│  [Thu hồi]        │                                 │
│  ═══════════════   │    📊 Tổng Buff Hiện Tại       │
│  ✅ Dị Nhân...     │    ❤️ HP: ×1.234 (+123%)       │
│                    │    ⚔️ ATK: ×0.567 (+56%)        │
│                    │                                 │
│                    │    [🧹 Sắp xếp] [♻️ Thu hồi]   │
│                    │                                 │
└────────────────────┴─────────────────────────────────┘
```

## 💾 Cấu Trúc Dữ Liệu

### Game_techniques Table
```sql
CREATE TABLE game_techniques (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    technique_code TEXT,
    dantian_row INTEGER DEFAULT -1,  -- -1 = chưa đặt
    dantian_col INTEGER DEFAULT -1,
    is_equipped INTEGER DEFAULT 0,    -- cũ, không dùng
    acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Kích Thước Công Pháp (Grid-based)
```python
{
    "code": "thanh_phong_kiem",
    "name": "Thanh Phong Kiếm",
    "grade": 0,  # 0=Xâm Cơ, 1=Dị Nhân, 2=Thiên Tài, 3=Thánh Tích, 4=Thần Tích
    "size": (3, 3),  # (height, width) = 9 ô
    "hp_mult": 0.0,
    "atk_mult": 0.18
}
```

## 🎯 Luồng Logic

### 1. Tải Công Pháp
```
user_id → core.get_techniques_inventory()
    ↓
Trả về: [
    { id, code, grade, dantian_row, dantian_col, ... }
]
```

### 2. Hiển Thị Panel Trái
```
Công pháp sắp xếp: grade cao → thấp
    ↓
For each công pháp:
    - Hiển thị: emoji, tên, đẳng cấp (màu)
    - If đang sử dụng: [Thu hồi]
    - Else: [Sử dụng]
```

### 3. Hiển Thị Khung Đan Điền
```
Nạp grid từ techniques_in_grid
    ↓
For (r=0; r<4; r++)
    For (c=0; c<5; c++)
        grid[r][c] = ?
            - None → ô trống (hiển thị "r,c")
            - tech_id → công pháp (hiển thị: emoji, tên, màu)
```

### 4. Sử Dụng Công Pháp
```
Người chơi click [Sử dụng]
    ↓
DantianGrid.find_first_free_position(size)
    ↓
    - Tìm được → place_technique_in_dantian(user_id, tech_id, r, c)
    - Không tìm được → ⚠️ Cảnh báo đầy, đề nghị tháo công pháp
    ↓
Cập nhật DB, rerun()
```

### 5. Sắp Xếp Tối Ưu
```
Người chơi click [Sắp xếp]
    ↓
_optimize_placement(techniques_in_grid)
    - Sắp xếp theo size giảm dần
    - Tìm vị trí tối ưu cho mỗi công pháp
    - Return: {tech_id: (r, c)}
    ↓
Cập nhật DB toàn bộ, rerun()
```

## 🔧 Files Thay Đổi

### 1. **techniques_ui.py** (NEW)
Toàn bộ giao diện công pháp mới
- `DantianGrid` class: Quản lý grid placement
- `_optimize_placement()`: Sắp xếp tối ưu
- `_render_technique_list_panel()`: Panel danh sách trái
- `_render_dantian_grid()`: Grid khung đan điền phải
- `_render_buff_summary()`: Bảng tổng buff
- `render_techniques_tab()`: Main entry point

### 2. **cultivation_tab.py** (MODIFIED)
- Import: `import techniques_ui`
- `_render_techniques()`: Gọi `techniques_ui.render_techniques_tab()`

## 📊 Bảng Màu Đẳng Cấp (Gán Cứng)
```python
TECHNIQUE_COLORS = (
    "#808080",  # Xâm Cơ - Xám
    "#4CAF50",  # Dị Nhân - Xanh lá
    "#2196F3",  # Thiên Tài - Xanh dương
    "#FF9800",  # Thánh Tích - Cam
    "#F44336",  # Thần Tích - Đỏ
)
```

## ✅ Test Cases

### Test 1: Hiển Thị Danh Sách
- [ ] Hiển thị tất cả công pháp sở hữu
- [ ] Sắp xếp đẳng cấp cao → thấp
- [ ] Rê chuột → tooltip hiển thị đầy đủ

### Test 2: Auto-Placement
- [ ] Click [Sử dụng] → công pháp nhảy vào ô trống đầu tiên
- [ ] Khung đầy → cảnh báo + đề nghị tháo công pháp
- [ ] Placement khác nhau cho các size khác nhau

### Test 3: Sắp Xếp Tối Ưu
- [ ] Click [Sắp xếp] → công pháp tái tổ chức
- [ ] Kích thước lớn xếp trước
- [ ] Diện tích được tiết kiệm tối đa

### Test 4: Thu Hồi
- [ ] Click [Thu hồi] trên công pháp → xóa khỏi grid
- [ ] Click [Thu hồi tất cả] → xóa hết
- [ ] Danh sách và grid cập nhật đúng

### Test 5: Buff Summary
- [ ] Hiển thị tổng HP/ATK buff đúng
- [ ] Danh sách chi tiết công pháp + buff riêng

## 🚀 Triển Khai

```bash
# 1. Code đã sẵn sàng
# 2. Test với app.py
streamlit run app.py

# 3. Kiểm tra tab "📜 Công Pháp Các"
# - Hiển thị danh sách trái
# - Hiển thị grid phải
# - Click "Sử dụng" → auto-placement
```

## 🔮 Tương Lai (Phiên 12+)

- [ ] **Drag-and-drop**: Kéo công pháp trực tiếp trên grid
- [ ] **Animation**: Hiệu ứng khi đặt/tháo công pháp
- [ ] **Filter/Sort**: Lọc theo loại (tâm pháp/bí pháp), sort theo buff
- [ ] **Undo/Redo**: Hoàn tác sắp xếp
- [ ] **Rotation/Flip**: Xoay công pháp (nếu size khác nhau khi xoay)
