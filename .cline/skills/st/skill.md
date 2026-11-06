---
name: st
description: Hỗ trợ phân tích, định vị đúng file, trích xuất đúng hàm/khối code cần đấu nối khi thêm tính năng mới cho webapp chinese-mastery. Bảo đảm an toàn hệ thống cũ, chống lỗi runtime và tiết kiệm tối đa token.
---

# Chinese-Mastery Feature Integration Skill (/st)

Áp dụng quy trình tra cứu có chủ đích và đấu nối chuẩn kỹ thuật cho ứng dụng `chinese-mastery` dựa trên tài liệu kiến trúc dự án.

---

## 1. Bản Đồ Định Vị File Theo Nhóm Tính Năng (Tra Cứu Mục Tiêu)
AI CHỈ ĐỌC đúng file và vùng code liên quan đến loại tính năng được yêu cầu, KHÔNG quét toàn bộ dự án:

| Loại tính năng cần thêm | File cần can thiệp | Vùng / Hàm cần kiểm tra chính xác |
|---|---|---|
| **Kinh tế / Vật phẩm / Điểm số** | `game_config.py`<br>`game_core.py` | `ITEM_SETS`, `RECIPES`, hệ số thưởng.<br>`settle()`, `apply_changes()`, `discard_item()`. |
| **Giao diện Động Phủ / Chợ / Kho** | `cultivation_tab.py`<br>`game_ui.py` | `_body` (`@st.fragment`), radio navigation.<br>`show_image_or_emoji()`, `color_buttons_css()`. |
| **Bản đồ / Săn thú / Boss / Trận đấu**| `game_hunt.py`<br>`game_config.py` | `render_hunt()`, `render_battle()`, `roll_loot()`, `scale_loot()`.<br>`_AREA_DATA`, `MONSTERS`, `BOSSES`. |
| **Mini-game / Câu hỏi / Luyện tập** | `game_minigames.py`<br>`game_questions.py` | Hàm render từng game (`g_match`, `g_sentence`).<br>`make_question()`, `load_pool()`, `evaluate()`. |
| **Khóa học (Tiếng Anh/Trung)** | `course_config.py`<br>`database.py` | Cờ cấu hình `has_pinyin`, `tts_lang`, ngưỡng cảnh giới.<br>`active_variant()`, các hàm bọc `@st.cache_data`. |
| **Cơ sở dữ liệu / Bảng mới** | `userdb.py`<br>`backup_manager.py` | `init_schema()`, danh sách `GAME_TABLES`.<br>Cập nhật mảng `BACKUP_TABLES` (không sửa `CORE_TABLES`). |
| **Luồng học hằng ngày / Stepper** | `app.py`<br>`exam_engine.py` | `SESSION_DEFAULTS`, `phase`, `go_next_day()`.<br>`start_exam()`, sinh đề Thiên Kiếp/Tâm Ma. |

---

## 2. Quy Tắc Đấu Nối Kỹ Thuật Bắt Buộc (Chống Lỗi Code Cũ)

1. **Ghi trạng thái Game tập trung**:
   - CHỈ ghi state qua `game_core.settle()` hoặc `game_core.apply_changes()`.
   - Tuyệt đối không tự ý ghi DB lẻ hoặc query SQL trực tiếp trong các file UI (`cultivation_tab.py`, `game_hunt.py`).

2. **Quy tắc Phân mảnh & Rerun trong Streamlit**:
   - Giao diện Động Phủ chạy trong `@st.fragment` (`_body`).
   - Sử dụng `on_click` callback cho các button tương tác.
   - CẤM gọi `st.rerun(scope="fragment")` vì sẽ gây crash khi đồng bộ trang.

3. **Bảo toàn Khóa Cache**:
   - Mọi hàm `@st.cache_data` liên quan đến từ vựng BẮT BUỘC phải nhận tham số `course` hoặc khóa `active_variant()` (ví dụ `en:B1:TEACHER` hoặc `zh`) để không làm rò rỉ dữ liệu giữa 2 khóa.

4. **Tránh Xung Đột Widget Key**:
   - Đặt tiền tố rõ ràng cho mọi widget mới (ví dụ tính năng Tiếng Anh dùng tiền tố `en_`, tính năng mới dùng tiền tố đặc thù). Không dùng key ngắn/chung chung dễ trùng với `game_nav`, `hunt_pick`, `ml_`, `mr_`.

5. **Định danh Profile & User**:
   - Dữ liệu học tập và game gắn với `profile_id` (qua `current_profile_id()`).
   - Chỉ tài khoản đăng nhập/admin mới dùng `auth_user_id()`.

---

## 3. Quy Trình Phản Hồi Khi Nhận Yêu Cầu Tính Năng Mới

Khi nhận được yêu cầu tính năng từ người dùng qua lệnh `/st`:
1. **Bước 1 (Định vị tối thiểu)**: Liệt kê tối đa 2-3 file và tên chính xác của các hàm cần đọc hoặc chèn code.
2. **Bước 2 (Kế hoạch đấu nối)**: Trình bày ngắn gọn:
   - Dữ liệu mới lưu vào đâu? (dùng counter, state hay bảng DB)
   - Tác động gì tới các luồng cũ?
3. **Bước 3 (Thực thi chuẩn xác)**: Chỉ viết/sửa đúng đoạn code cần thiết. Không xuất lại toàn bộ nội dung của những file lớn hàng trăm dòng.