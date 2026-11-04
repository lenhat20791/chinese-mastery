# PROJECT_OVERVIEW — Thực Chiến Tiếng Trung (chinese-mastery)

File này dành cho AI đọc trước khi viết/sửa code. Cập nhật lại sau mỗi đợt thay đổi lớn.

## 1. Tổng quan
- Streamlit app học tiếng Trung theo phong cách tu tiên. Mục tiêu lý tưởng: HSK4 trong ~1 năm, sau đó HSK5 không giới hạn thời gian (không bắt buộc).
- Python 3.10, Streamlit 1.52. Chạy: `streamlit run app.py`. Test: `python -W ignore -m unittest discover -s tests -t .`
- Ngôn ngữ giao diện: tiếng Việt. Console Windows cp1252 → đặt `PYTHONIOENCODING=utf-8` khi in tiếng Việt/Hán.

## 2. Dữ liệu
| Nơi | Vai trò |
|---|---|
| `chinese_mastery.db` (SQLite, commit vào git) | Từ vựng gốc (bảng vocabulary). CHỈ commit khi nguồn từ vựng thay đổi. |
| `user_data.db` / Turso (qua `userdb.py`) | Dữ liệu người dùng + tiến độ + dữ liệu game. Dùng Turso nếu có secrets, ngược lại SQLite cục bộ. |
| Sao lưu | `backup_manager.py` đẩy bảng người dùng + 9 bảng game lên Google Drive (nút thủ công). Restore chịu được bản backup cũ. |
| `vocab_cleaned_final.json`, `makemehanzi_dict.txt`, `reference_data.py` | Dữ liệu tham chiếu (bộ thủ, nét…). |
| `assets/` | Ảnh: `monsters/`, `boss/`, `artifacts/`, `map/map.png` (tên file = mã, `.png/.webp/.jpg`). Thiếu ảnh → emoji dự phòng. |

Từ vựng: 294 từ HSK4 công sở (priority_group 1-3) + 2197 từ HSK1–5 mở rộng (domain `HSK_OPEN`, priority_group 4) sau khi chạy `tools/`.

## 3. Bản đồ module
- `app.py`: điểm vào. Login (`auth.require_login`), sidebar (hero-card, cảnh giới, stepper), 6–7 tab. Tab 0 học hằng ngày (FLASHCARD → SHADOWING → CLOZE → COMPLETED), tab 1 `render_cultivation`, tab 2 thống kê/tâm ma, sổ tay, phát âm, bộ thủ, admin (tabs[6]).
- Thiên kiếp: ngày chia hết cho 3 → Tiểu thiên kiếp (20 câu, `MINI_3D`), chia hết cho 10 → Đại thiên kiếp (50 câu, `MAJOR_10D`). Logic ở `exam_engine.generate_tribulation_exam`, tiêu hao `get_tribulation_cost`.
- `database.py`: tiến độ học (`load_user_progress`, `advance_user_day`, `record_exam_result`, `record_review_batch`, tâm ma `is_inner_demon`), `load_day_words` (cache_data).
- `userdb.py`: kết nối Turso/Local thống nhất (`get_user_db`, `execute_many`, `init_schema`), 9 bảng game (`GAME_TABLES`).
- `auth.py`: đăng nhập/token/xóa user (xóa cả `GAME_TABLES`).
- `game_config.py`: TOÀN BỘ số liệu cân bằng + nội dung (cảnh giới, kinh tế, vùng, quái, item, bí phương, huy hiệu). Chỉnh game ở đây trước.
- `game_questions.py`: kho từ đã học (`learned_day_for`, `load_pool`), sinh câu hỏi (h2m, m2h, audio, pinyin, cloze), `evaluate`, `check_pinyin`.
- `game_core.py`: trạng thái game (`get_state` cache trong `st.session_state["game_state"]`, `apply_changes` ghi atomic), `realm_info`, kinh tế, `settle` (kết thúc mỗi lượt chơi: hệ số, ghi review, huy hiệu), chế tạo/nâng cấp/trang bị, quẻ bói.
- `game_minigames.py`: Quẻ bói, Lật bài, Đối câu. `game_hunt.py`: bản đồ + chiến đấu theo lượt. `cultivation_tab.py`: điều hướng tab game (radio `game_nav`), trang chủ/chợ/huy hiệu. `game_ui.py`: ảnh, audio (Web Speech), CSS nút theo key.
- `tools/translate_vocab.py` (Gemini dịch HSK1–5, cần `GEMINI_API_KEY`), `tools/import_hsk_vocab.py` (nhập vào DB, idempotent).
- `tests/test_game.py`: logic thuần + luồng DB trên SQLite tạm.

## 4. Cơ chế game hiện có
- **Cảnh giới**: 16 đại cảnh giới × 3 tiểu kỳ (Sơ/Trung/Hậu) = 48 mốc, tính từ SỐ TỪ ĐÃ HỌC (`SUB_THRESHOLDS`): 9 cảnh giới phàm giới đầu trải 0→1200 từ (HSK4), 7 cảnh giới Tiên trải 1200→2500 (HSK5). Thứ tự: Linh Khí, Trúc Cơ, Kim Đan, Nguyên Anh, Xuất Khiếu, Hóa Thần, Luyện Hư, Hợp Thể, Độ Kiếp, Tán Tiên, Địa Tiên, Chân Tiên, Kim Tiên, Đại La Kim Tiên, Tiên Tôn, Tiên Đế.
- **Kho từ đã học** = vocab có `study_day <= learned_day_for(user, phase)`. Từ của hôm nay chỉ tính khi đã qua giai đoạn học hoặc đang ở bình cảnh.
- **Kinh tế**: Linh Thạch (LS). Giá = ngày cày × 100 × 1.25^idx. Hệ số thưởng mỗi ngày: 10 trận đầu 100%, trận 11–30 ×0.4, từ 31 ×0.1 (tính từ số trận TRƯỚC khi cộng). Thưởng săn quái tính theo idx của vùng, không theo người chơi.
- **Pháp bảo**: 5 bậc (Linh Khí, Pháp Bảo, Linh Bảo, Tiên Bảo, Tiên Khí) × 3 phẩm (Hạ/Trung/Thượng; hệ số 1.0/1.25/1.6; xác suất 60/30/10, đan dược 40/40/20; bảo hiểm lần 6 ≥ Trung, lần 12 = Thượng). Nâng cấp tối đa +9, mỗi cấp +10%, thất bại chỉ mất nguyên liệu. Mua bí phương ở chợ (quyết định hình dáng + bậc), nguyên liệu: thường / hiếm / quý.
- **Mini game**: mỗi lượt chơi gắn với ôn từ vựng và gọi `settle(...)`. Dùng `on_click` callback, KHÔNG dùng `st.rerun(scope="fragment")` (lỗi khi rerun toàn trang).
- **Game state**: `game_profile`, `game_daily`, `game_inventory`, `game_recipes`, `game_artifacts`, `game_fortune`, `game_achievements`, `game_counters`, `game_log`.

## 5. Lưu ý kỹ thuật quan trọng (đấu nối an toàn)
- Mọi thay đổi trạng thái game đi qua `game_core.apply_changes` (batch atomic rồi reload state). Không ghi DB lẻ.
- Thêm bảng game mới: khai báo trong `userdb.py` + `GAME_TABLES` + `backup_manager.BACKUP_TABLES` (KHÔNG thêm vào `CORE_TABLES`) — `auth.delete_user` tự xóa theo `GAME_TABLES`.
- Thêm key widget phải duy nhất. Key đang dùng: `game_nav`, `match_*`, `ml_/mr_{id}`, `fortune_opt_{i}`, `sent_*`, `hunt_*`, `opt_{turn}_{i}`, `pin_{turn}`.
- Tab được render mỗi rerun; `st.tabs` không lazy. Giữ hàm render nhẹ.
- AppTest: radio nhận giá trị key (`"fortune"`, `"hunt"`…), không phải nhãn.
- `execute_many` trên Turso chưa kiểm thử thật (chỉ LocalConnection).
- Không commit `credentials.json`, `token.json`, `.streamlit/secrets.toml`.

## 6. Cập nhật đã triển khai (đợt 2)
- `game_config.py`: `MAJOR_REALMS` (thứ tự Tiên: Tán, Địa, Chân, Kim, Đại La, Tôn, Đế), `ITEM_SETS` (8 bộ nguyên liệu, mã `r{bộ}_{0..5}`, bộ s dùng cho cảnh giới 2s và 2s+1), `MONSTERS`/`BOSSES` (mã = tên ảnh), `AREAS` (32 khu = 2 mỗi cảnh giới: khu thường + khu tinh anh/boss; toạ độ x,y theo pixel trên `map_web.jpg` 1595x890, chỉnh ở `_AREA_DATA`), `RECIPES` (9 pháp bảo, mã = tên ảnh, có `kind` atk/def, `region == min_idx // 2`; `LEGACY_RECIPE_CODES` map mã cũ lk1... sang mã mới).
- `game_hunt.py` viết lại: bản đồ ảnh `assets/map/map_web.jpg` (bản nhẹ của `map.png`) với nút bấm CSS tuyệt đối (`mapbtn_{i}`, tooltip = `help`), chọn khu qua `hunt_pick`; 3 loại trận normal/elite/boss; độ sâu `g_run` (mỗi trận thắng +5% quái, cứ 5 trận có log "đi sâu", rút lui/thua/boss → reset); log đánh trúng "Bạn sử dụng tuyệt kỹ +Hỏa Cầu Thuật tấn công X, gây N sát thương + combo K"; mở boss khi hạ 3 tinh anh trong khu (counter `elite_r{realm}`).
- Pháp bảo: 2 ô (`state["equipped"]` = list 2 phần tử, lưu ở `game_counters` key `equip_1/equip_2`; cột `equipped_artifact` chỉ để đọc dữ liệu cũ), `core.equipped_artifacts`, `core.equip(id, idx, slot)`, `core.unequip`, `core.sell_artifact` (hoàn 50% phí chế). Công → +ATK (cộng thẳng + %), Thủ → +HP.
- `guide_tab.py` + nút "📖 Hướng Dẫn" ở sidebar (`show_guide` trong session_state, `st.stop()` trước tabs).
- Kho item cũ theo mã vùng cũ r0..r7 vẫn hợp lệ (cùng định dạng).

## 6b. Cập nhật đợt 3
- **Chỉ số** (`game_config.py` hằng `CRIT_*`, `CAN_CO_*`, `DAO_TAM_*`, `TAM_MA_K`; hàm `core.stat_bonuses(words, answers, streak)`, `core.diminishing`): lợi suất giảm dần `trần × p / (p + K)`. Ngộ tính (`answers_correct`) → chí mạng (×1.5), Căn cơ (số từ đã học) → +HP và +ATK (mỗi bên tối đa 7.5%), Đạo tâm (`consecutive_streak`) → giảm sát thương Tâm Ma Kiếp (tối đa 25%). `ctx["bonuses"]` được tạo trong `cultivation_tab._body` và truyền vào `core.player_stats(idx, artifacts, bonuses)` (trả thêm `crit`). `game_hunt.hit_damage(...)` trả `(dmg, is_crit)`.
- **Tâm Ma Kiếp**: `exam_engine.generate_tribulation_exam` — Đại Thiên Kiếp = 40 câu `phase="loi"` + `TAM_MA_Q_MAJOR`=10 câu `phase="tam_ma"` (ưu tiên từ tâm ma). `app.start_exam` đặt `exam_tm_t = demons/(demons+TAM_MA_K)`, `exam_dao_tam`, `exam_extra`, `exam_wrong`. Câu sai ở Tâm Ma Kiếp trừ thêm `T × (1 − dao_tam)`; qua kiếp khi `đúng − exam_extra ≥ int(tổng × 0.85)`. UI có thanh "Đạo thể". Tiểu Thiên Kiếp giữ nguyên (20 câu, không có Tâm Ma Kiếp).
- Ảnh tu sĩ: `assets/hinh tu luyen/avatar_web.webp` (bản nhẹ của `anh_tu_luyen.png`), `cultivation_tab._show_avatar`; fallback SVG nếu thiếu ảnh.
- Phát âm: từ ngắn (≤ 6 ký tự) dùng hệ số 0.55, câu 0.85, nhân với tốc độ chọn ở sidebar (`app.py`, `extra_tabs.SPEAK_SCRIPT`, `game_ui.speak`).
- Đã bỏ nút "Lưu Tu Vi & Hoàn Tất"; Linh Lực vẫn được cộng bởi các nút sang ngày/thiên kiếp ở màn COMPLETED.
- Săn quái: rút lui có bước xác nhận (`confirm_retreat`). Nhật ký `game_log` tự giữ tối đa 300 dòng/người (`game_core.settle`).
- Hướng dẫn: thêm tab "🧬 Chỉ Số", mục công dụng Linh Thạch, mô tả Tâm Ma Kiếp.

## 7. Việc còn lại / lưu ý
- Toạ độ nút trên bản đồ được ước lượng từ ảnh; chỉnh trong `_AREA_DATA` nếu lệch (Thần Lăng Tiên Uyên chưa có nhãn trên ảnh).
- Hỗn Độn / Cùng Kỳ và Tinh Hà Thần Châu chưa có ảnh → chưa đưa vào game.

1. **Đổi tên** theo tên ảnh. Quái (11): thanh_phong_lang, nhat_muc_xa_yeu, hac_loi_dieu, kim_mao_thu, tu_bi_giao_long, bach_nien_moc_yeu, thuc_nhan_hoa, cuong_thiet_tru, thiem_dien_bao, tam_dau_yeu_su, cu_xi_hac_ho. Boss (10, luân phiên cho 16 khu, mạnh dần theo cảnh giới): ty_huu, thong_thien_cu_vien, phuong_hoang, thao_thiet, ky_lan, dai_bang_kim_xi_dieu, bach_ho, huyen_vu, thanh_long, cuu_vi_thien_ho. Ảnh quái ở `assets/monsters`, boss ở `assets/boss`.
2. **Pháp bảo (9 món, tối đa mang 2)**: công = Thanh Phong Kiếm, Xích Diễm Đao, Hàn Băng Châu, Hỗn Độn Ấn, Ngọc Hư Tiên Kiếm (tăng sức công cơ bản + %); thủ = Hộ Tâm Kính, Huyền Quy Thuẫn, Cửu U Phiên, Vân Hải Chung (tăng HP cơ bản + %). Cảnh giới tối thiểu: Linh Khí(Kỳ 0), Trúc Cơ; Kim Đan, Nguyên Anh; Hóa Thần, Luyện Hư; Độ Kiếp, Địa Tiên(bậc Tiên Bảo); Kim Tiên (Tiên Khí). Có thể thay pháp bảo; bán pháp bảo cũ hoàn 50% LS chế tạo (không tính nâng cấp). Tinh Hà Thần Châu tạm bỏ (chưa có ảnh); sẽ bổ sung pháp bảo mới sau.
3. **Chiến đấu**: log đánh trúng "Bạn sử dụng tuyệt kỹ +Hỏa Cầu Thuật tấn công [quái], gây x sát thương + combo y". Chỉ 1 tuyệt kỹ mặc định Hỏa Cầu Thuật (mở rộng sau). Quái mạnh dần theo số trận thắng trong phiên; mỗi 5 trận thắng có log "đi sâu vào khu vực, gặp quái mạnh hơn"; rút lui rồi vào lại → reset. Quái khởi đầu ngang tu vi khu vực.
4. **Khu vực**: mỗi cảnh giới 2 khu (1 quái thường farm item thường, 1 tinh anh + boss rơi core item). Phàm giới 18 khu, Tiên giới 14 khu, tên địa danh theo `assets/map/map.png`. Thứ tự Tiên giới: Tán Tiên (Tru Tiên Nhai, Nhiễm Ma Tiên Đầm), Địa Tiên (Tử Hà Cổ Động, Bách Thảo Tiên Cung), Chân Tiên (Thiên Tuyền Giang, Ngọc Hư Phong), Kim Tiên (Thái Ất Tiên Khư, Kim Diễm Linh Trì), Đại La Kim Tiên (Đại La Vạn Tiên Đảo, Vạn Đạo Tôn Điện), Tiên Tôn (Thần Lăng Tiên Uyên, Cửu Tiêu Băng Cung), Tiên Đế (Tuyên Cổ Điện, Vĩnh Hằng Đế Thành). Phàm giới theo danh sách ở `game_config.REGIONS`.
5. **Bản đồ**: dùng `map.png` làm nền, nút bấm đặt trên 32 địa danh (tọa độ % trong config, chỉnh được), popup tên khu + item rơi.
6. **Thống nhất**: cảnh giới – bí phương – nguyên liệu – core item – khu farm phải khớp (mỗi công thức chỉ cần item từ khu đúng cảnh giới).
7. **Hướng dẫn**: nút nổi bật ở sidebar dưới bảng tu vi, dẫn tới tab hướng dẫn (học hằng ngày, động phủ, tiểu khảo/đại khảo/thiên kiếp, các game, pháp bảo, săn nguyên liệu, cày LS, cảnh giới, lộ trình giao tiếp → đời sống → HSK4–5).
