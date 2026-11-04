# PROJECT_OVERVIEW — Thực Chiến Tiếng Trung (chinese-mastery)

> **AI đọc file này TRƯỚC khi viết/sửa code.** Cập nhật lại sau mỗi đợt thay đổi lớn. Giao diện và comment viết bằng tiếng Việt.
> Cập nhật gần nhất: sau đợt 3 (chỉ số, Tâm Ma Kiếp, ảnh tu sĩ, phát âm). Mục 12 là checklist để gắn khóa học MỚI (ví dụ tiếng Anh) vào hệ thống.

## 1. Tổng quan
- Streamlit app học tiếng Trung, phong cách tu tiên. Học từ mới mỗi ngày (tab 1), ôn lại bằng mini game "Động Phủ" (tab 2).
- Mục tiêu lý tưởng (không bắt buộc): HSK4 (~1200 từ) trong ~1 năm, sau đó HSK5 (~2500 từ) không giới hạn thời gian.
- Nhiều người dùng (đăng nhập tài khoản), tiến độ lưu theo `user_id`. Admin có tab quản lý.
- Python 3.10, Streamlit 1.52. Chạy: `streamlit run app.py`. Test: `python -W ignore -m unittest discover -s tests -t .` (17 test).
- Windows: đặt `$env:PYTHONIOENCODING="utf-8"` khi in tiếng Việt/Hán. Khi chạy thử, nhớ tắt tiến trình Streamlit cũ (Ctrl+F5 ở trình duyệt) kẻo chạy bản code cũ.
- Triển khai: Streamlit Cloud + Turso (DB người dùng) + Google Drive (sao lưu thủ công). `.github/workflows/keep_alive.yml` ping app mỗi 6 giờ để khỏi ngủ.
- Cấm commit: `credentials.json`, `token.json`, `.streamlit/secrets.toml`, `user_data.db`, `makemehanzi_dict.txt` (đã trong `.gitignore`).

## 2. Cấu trúc thư mục
```
chinese-mastery/
├─ app.py                  Điểm vào: login, sidebar, 6–7 tab, toàn bộ luồng học hằng ngày + thiên kiếp (~870 dòng)
├─ auth.py                 Đăng nhập, token URL, tạo/xóa user, màn hình login
├─ admin_panel.py          Tab "Quản Lý" (chỉ admin): tài khoản + sao lưu
├─ database.py             Đọc kho từ vựng + ghi tiến độ học / tâm ma / thi (dùng user_id từ session)
├─ userdb.py               Kết nối DB người dùng (Turso hoặc SQLite cục bộ) + schema + GAME_TABLES
├─ backup_manager.py       Sao lưu/khôi phục lên Google Drive (BACKUP_TABLES, CORE_TABLES)
├─ exam_engine.py          Sinh đề thiên kiếp (Tiểu 20 câu; Đại 40 Lôi Kiếp + 10 Tâm Ma Kiếp)
├─ extra_tabs.py           Sổ tay, tập phát âm, bộ thủ, dialog chi tiết từ, iframe Web Speech
├─ reference_data.py       Dữ liệu tham chiếu bộ thủ/âm
├─ chiet_tu.py             Công cụ sinh chiết tự (dữ liệu makemehanzi) cho DB từ vựng
├─ game_config.py          TOÀN BỘ số liệu cân bằng + nội dung game (sửa game ở đây trước)
├─ game_core.py            Trạng thái game, kinh tế, chế tạo, chỉ số, settle, quẻ bói, huy hiệu
├─ game_questions.py       Kho từ đã học + sinh câu hỏi cho mini game / trận đánh
├─ game_minigames.py       Quẻ bói, Lật bài, Đối câu / sắp xếp câu
├─ game_hunt.py            Bản đồ 32 khu + trận đánh theo lượt (quái/tinh anh/boss)
├─ game_ui.py              Ảnh/emoji, nút phát âm `speak`, `audio_listener` (phát âm cho nút Streamlit theo key), CSS tô màu nút
├─ cultivation_tab.py      Tab "Động Phủ": điều hướng (radio), trang chủ, chợ, huy hiệu
├─ guide_tab.py            Trang "📖 Hướng Dẫn" (7 tab con)
├─ style.css               CSS toàn app (theme tối tím vàng)
├─ requirements.txt        streamlit, google-api-python-client, google-auth-*, google-genai, requests
├─ chinese_mastery.db      SQLite từ vựng gốc (bảng `vocab`) — commit vào git
├─ vocab_cleaned_final.json  Dữ liệu từ vựng nguồn (chiết tự…)
├─ logo.png / logo_cropped.png
├─ PROJECT_OVERVIEW.md     (file này)
├─ .streamlit/config.toml  Theme tối, headless
├─ .github/                keep_alive.py + workflows/keep_alive.yml
├─ tools/
│   ├─ translate_vocab.py  Dùng Gemini dịch HSK1–5 sang tiếng Việt (cần GEMINI_API_KEY)
│   └─ import_hsk_vocab.py Nhập HSK vào `vocab` (idempotent)
├─ tests/
│   ├─ __init__.py
│   └─ test_game.py        Test logic thuần + luồng DB trên SQLite tạm
└─ assets/
    ├─ monsters/           11 ảnh quái (tên file = mã quái, .png)
    ├─ boss/               10 ảnh boss
    ├─ artifacts/          9 ảnh pháp bảo
    ├─ map/                map.png (gốc 8MB, không dùng trực tiếp), map_web.jpg (1400px, nền bản đồ)
    └─ hinh tu luyen/      anh_tu_luyen.png (gốc), avatar_web.webp (ảnh tu sĩ ở trang chủ Động Phủ)
```
Tên file ảnh = mã trong `game_config`; thiếu ảnh → emoji dự phòng (`game_ui.show_image_or_emoji`).

## 3. Dữ liệu
### 3.1 Kho từ vựng — `chinese_mastery.db` (chỉ đọc khi chạy, `database.DB_PATH`)
Bảng `vocab`: `id, hanzi, traditional, pinyin, hanviet, meaning_vi, domain, hsk_level, study_day, stage_10d, example_zh, example_pinyin, example_vi, example_cloze, chiet_tu, priority_group` (mặc định 4).
- 294 từ HSK4 công sở/giao tiếp (`priority_group` 1–3, học trước) + ~2200 từ HSK1–5 mở rộng (`domain='HSK_OPEN'`, `priority_group` 4) nhập bằng `tools/`. `study_day` = ngày học (mỗi ngày 4 từ).
- Cache: `database._load_vocabulary` (`st.cache_data`) nạp toàn bộ bảng, `load_day_words(day)` lọc theo ngày. Bảng `user_progress`/`word_mastery`/`exam_history` trong file này là DI SẢN (dữ liệu cũ một người dùng, `import_legacy_progress` chuyển sang tài khoản admin); đừng dùng.
- Chỉ commit file này khi nguồn từ vựng thay đổi (tiến độ học KHÔNG commit).

### 3.2 DB người dùng — `userdb.py` (`get_user_db()`)
Dùng Turso (HTTP) nếu có secrets, ngược lại SQLite cục bộ `user_data.db`. Cùng giao diện: `.execute(sql, params)`, `.execute_many([(sql, params), ...])` (atomic), `init_schema()` tạo bảng (gọi khi khởi động), `get_meta/set_meta`.
| Bảng | Khóa | Nội dung |
|---|---|---|
| `users` | id | tài khoản (username, display_name, mật khẩu băm, is_admin) |
| `auth_tokens` | token_hash | đăng nhập qua token trên URL (`?token=`), có hạn |
| `user_progress` | user_id | `current_day, spiritual_energy, consecutive_streak, last_study_date, is_bottleneck, current_realm, realm_level` |
| `word_mastery` | (user_id, vocab_id) | `review_count, failed_count, vague_count, mastered_count, last_status, is_inner_demon, last_reviewed_at` |
| `exam_history` | id | lịch sử thiên kiếp (`exam_type, stage_number, total_questions, correct_answers, score_percent, is_passed`) |
| `session_state` | user_id | JSON vị trí buổi học (F5/đổi máy không mất tiến trình) |
| `meta` | key | cờ hệ thống |
| `game_profile` | user_id | `linh_thach, equipped_artifact(di sản), equipped_title, pity_mid, pity_high, fortune_streak, fortune_last_day` |
| `game_daily` | (user_id, day) | `plays` — số lượt chơi mini game trong ngày |
| `game_inventory` | (user_id, item_code) | `qty` nguyên liệu/đan dược |
| `game_recipes` | | bí phương đã mua |
| `game_artifacts` | id | pháp bảo đã chế (`recipe_code, quality, upgrade`) |
| `game_fortune` | | quẻ bói hôm nay |
| `game_achievements` | | huy hiệu/danh hiệu đã mở |
| `game_counters` | (user_id, key) | bộ đếm tổng quát (xem 6.4). Cũng lưu 2 ô pháp bảo: `equip_1`, `equip_2` (0 = trống) |
| `game_log` | id | Nhật Ký Tu Tiên; `settle` tự xóa, chỉ giữ 300 dòng mới nhất/người |

`userdb.GAME_TABLES` liệt kê 9 bảng game (`auth.delete_user` xóa theo danh sách này). `backup_manager.BACKUP_TABLES` = cột của mọi bảng cần sao lưu; `CORE_TABLES` = 5 bảng lõi (users, user_progress, word_mastery, exam_history, session_state) bắt buộc có trong backup; bảng game là tùy chọn (restore chịu được backup cũ).

## 4. Luồng học hằng ngày (tab 1, trong `app.py`)
- `st.session_state.phase`: `FLASHCARD` → `SHADOWING` → `CLOZE` → `REVIEW` (ôn từ sai trong ngày) → `COMPLETED`; ngoài ra `be_quan` (cày Linh Lực khi Bình Cảnh) và `loi_kiep` (đang thi). `sub_phase` của FLASHCARD: `flashcard` | `quiz`. Stepper ở sidebar: `PHASE_ORDER`, `stepper_html`.
- `SESSION_DEFAULTS` (đầu `app.py`) khai báo mọi key session_state kèm factory; thêm state mới thì thêm vào đó.
- Lưu/khôi phục vị trí: `session_snapshot()` / `restore_session()` ↔ `database.save_session_snapshot/load_session_snapshot`. Bài thi dở dang bị làm lại từ đầu.
- `go_next_day()`: `advance_user_day()` + reset toàn bộ state trong ngày. `update_user_energy(minutes)` cộng Linh Lực — được gọi bởi các nút ở màn COMPLETED (đã BỎ nút "Lưu Tu Vi" thừa).
- Mỗi 3 ngày → Tiểu Thiên Kiếp (`MINI_3D`, 20 câu); mỗi 10 ngày → Đại Thiên Kiếp (`MAJOR_10D`, 50 câu). Chi phí `get_tribulation_cost`. Cần ≥ 85% để qua; trượt → Bình Cảnh (`is_bottleneck`), phải Bế Quan tích Linh Lực rồi bấm "Kích Hoạt Lôi Kiếp" (`exam_type="LÔI KIẾP"`).
- **Tâm Ma Kiếp** (chỉ Đại Thiên Kiếp): 40 câu `phase="loi"` + `TAM_MA_Q_MAJOR`(10) câu `phase="tam_ma"` ở cuối (ưu tiên từ tâm ma). `start_exam` đặt `exam_tm_t = demons/(demons+TAM_MA_K)`, `exam_dao_tam` (giảm nhờ Đạo tâm), `exam_extra`, `exam_wrong`. Câu sai ở Tâm Ma Kiếp trừ thêm `T × (1 − dao_tam)` điểm. Qua kiếp khi `đúng − exam_extra ≥ int(tổng × 0.85)`. UI có thanh "🛡️ Đạo thể".
- Tâm ma: từ có `is_inner_demon=1` (sai nhiều); `exorcise_inner_demon` khi trả lời đúng trong thi; `get_inner_demons(n)`, `get_all_demons_detailed`.
- Phát âm: Web Speech API (`speechSynthesis`, `lang='zh-CN'`). Tốc độ = lựa chọn sidebar `speech_rate` (1.0/0.85/0.75/0.6) × hệ số (từ ≤ 6 ký tự: 0.55; câu: 0.85). Có ở 3 nơi: JS cuối `app.py`, `extra_tabs.SPEAK_SCRIPT`, `game_ui.speak`. **Khóa học tiếng Anh cần đổi `lang` (en-US) và hệ số.**
- Các tab phụ: `extra_tabs.render_notebook` (sổ tay), `render_pronunciation`, `render_radicals`; tab 3 thống kê/tâm ma trong `app.py` (`get_cultivation_stats`).
- Sidebar: hero-card (cảnh giới, Linh Lực, căn cơ, ngày), nút "📖 Hướng Dẫn" (cam, key `guide_open`, đặt `show_guide` → `render_guide()` + `st.stop()` trước khi tạo tab), stepper, tốc độ phát âm, đăng xuất.

## 5. Bản đồ module game (Động Phủ)
- `cultivation_tab.render_cultivation(user, learned_day)` → `_body` (`@st.fragment`) dựng `ctx` rồi gọi trang theo radio `game_nav` (`home, fortune, match, sentence, hunt, market, badges`).
- **`ctx`**: `{"pool": list từ đã học, "words": len(pool), "realm": realm_info(...), "idx": chỉ số đại cảnh giới 0..15, "mastery": {vocab_id: (review, failed, demon)}, "grammar": bool, "bonuses": stat_bonuses(...)}`. Mọi hàm render game nhận `ctx`.
- `game_questions`: `learned_day_for(user, phase)` (ngày đã học hợp lệ), `load_pool(day)` (từ đã học = `study_day <= day`), `pick_words(pool, mastery, n)` (ưu tiên từ hay sai/tâm ma), `make_question(word, pool, qtype, allow_cloze)` → dict `{type, prompt, hint, options|None, audio, word, ...}` với type `h2m, m2h, audio, pinyin, cloze`; `evaluate(q, choice)`, `check_pinyin`, `short_meaning`, `tokenize_sentence`.
- `game_core`: `get_state()` (cache ở `st.session_state["game_state"]`), `apply_changes(...)`, `settle(...)`, `realm_info(words)`, `scale(idx)`, `play_multiplier`, chế tạo `buy_recipe/craft/upgrade/sell_artifact`, trang bị `equip/unequip/equipped_artifacts`, chỉ số `stat_bonuses/player_stats`, quẻ `draw_fortune/start_fortune/resolve_fortune`, huy hiệu `check_achievements/equip_title`.
- `game_hunt`: hàm thuần (test được) `depth_mult, monster_stats(realm_idx, kind, wins)→(atk,hp), hit_damage(...)→(dmg,is_crit), roll_loot, scale_loot, area_tooltip`; UI `render_hunt`, `render_battle`, `render_area_panel`; state `g_battle`, `g_run`, `hunt_pick`.
- `game_minigames`: `render_fortune/render_match/render_sentence`; state `g_match`, `g_sentence…`.

## 6. Cơ chế game (số liệu thật nằm trong `game_config.py`)
### 6.1 Cảnh giới
16 đại cảnh giới × 3 tiểu kỳ = 48 mốc theo SỐ TỪ ĐÃ HỌC (`SUB_THRESHOLDS`): 9 cảnh giới Phàm Giới trải 0→1200 từ (HSK4), 7 cảnh giới Tiên Giới trải 1200→2500 (HSK5). Thứ tự (`MAJOR_REALMS`): Linh Khí, Trúc Cơ, Kim Đan, Nguyên Anh, Xuất Khiếu, Hóa Thần, Luyện Hư, Hợp Thể, Độ Kiếp | Tán Tiên, Địa Tiên, Chân Tiên, Kim Tiên, Đại La Kim Tiên, Tiên Tôn, Tiên Đế. `PHAM_REALMS=9`. `realm_info(words)` → `{idx, name, progress, next_need, ...}`.

### 6.2 Kinh tế
Tiền: **Linh Thạch (LS)**. Hệ số thưởng mỗi ngày theo số lượt đã chơi TRƯỚC lượt này (`game_daily.plays`): 10 lượt đầu ×1, 11–30 ×0.4 (`MULT_MID`), từ 31 ×0.1 (`MULT_LOW`); không giới hạn lượt. Thưởng nhân `scale(idx)` = `1.25^idx` (săn quái dùng idx của KHU, không phải của người chơi, để khu thấp không cày được nhiều). `POWER_PER_REALM = 1.25`. Giá bí phương/chế tạo ≈ ngày cày × 100 × 1.25^idx.

### 6.3 Mini game
- **Quẻ bói** (1 lần/ngày): rút quẻ Đại Cát/Cát/Bình (15/35/50%); giải đúng đố nghĩa → buff trong ngày (`FORTUNE_BUFFS`: thêm LS, Hộ Thân Phù, tăng rơi đồ); sai → quẻ Hung + từ vào tâm ma.
- **Lật bài** (đã làm): mỗi ván `MATCH_MAX_PAIRS=4` cặp, thưởng `MATCH_PAIR_REWARD=3`/cặp + `MATCH_PERFECT_BONUS=2`. Mỗi cặp có thể thức riêng (`game_minigames.build_match_modes`): `hm` Hán↔nghĩa, `hp` Hán↔pinyin, `ap` 🔊↔pinyin, `ah` 🔊↔Hán (không có nghe↔nghĩa Việt). Tối đa n//2 cặp dạng nghe; mặt cột phải (`_right_face`) không trùng nhau. Nút trái dạng nghe hiện "🔊 số"; phát âm bằng `game_ui.audio_listener({key: text})` (listener gắn vào trang cha). Key nút `ml_{id}`/`mr_{id}`, tô màu bằng `color_buttons_css`. State `g_match` có thêm `modes`, `audio_no`.
- **Đối câu / sắp xếp câu**: mở từ Trúc Cơ + ≥ 30 từ (`GAME_UNLOCKS["sentence"]`).
- Mở khóa (`GAME_UNLOCKS`): fortune/match/hunt cần ≥ 4 từ; sentence và `grammar_battle` (câu điền từ trong trận đánh) cần Trúc Cơ + 30 từ.

### 6.4 Săn yêu thú (`game_hunt.py`)
- Bản đồ `assets/map/map_web.jpg` (1595×890 gốc), 32 khu = 16 cảnh giới × 2. Nút bấm đặt tuyệt đối bằng CSS (`st.container(key="hunt_map")` + `mapbtn_{i}`; tọa độ pixel trong `_AREA_DATA` của `game_config.py` → % qua `MAP_W/MAP_H`, `MAP_ICON_OFFSET_Y`). Tooltip = `help` của nút (có thể lệch, chỉnh `_AREA_DATA`). Chọn khu qua `hunt_pick` + selectbox dự phòng. "Thần Lăng Tiên Uyên" không có nhãn trên ảnh.
- Mỗi cảnh giới: khu 1 = quái thường (rơi nguyên liệu thường); khu 2 = tinh anh + boss (hiếm/quý). Hạ `SPECIAL_MIN_KILLS`=3 tinh anh (counter `elite_r{realm}`) để mở thách đấu boss (qua `SPECIAL_EVENTS`=3 cơ quan, rồi đánh boss).
- Trận đánh theo lượt: mỗi lượt = 1 câu hỏi ôn (`make_question`). Đúng → "Bạn sử dụng tuyệt kỹ +Hỏa Cầu Thuật tấn công X, gây N sát thương + combo K" (có thể thêm "💥 Chí mạng!"); sai → quái phản công, combo về 0. Hết HP → thua. Rút lui có bước xác nhận (`confirm_retreat`).
- Độ sâu: `g_run={area,wins}`; mỗi trận thắng +`DEPTH_STEP` 5% HP/ATK quái (tối đa ×`DEPTH_MAX`), cứ `DEPTH_EVERY`=5 trận log "đi sâu vào khu vực". Rút lui/thua/sau boss → reset. Quái khởi đầu ngang cảnh giới của KHU.
- Loot: `ITEM_SETS` 8 bộ × 6 vật phẩm (mã `r{bộ}_{0..5}`, bộ s dùng cho cảnh giới 2s và 2s+1: 3 thường `_0.._2`, 2 hiếm `_3,_4`, 1 quý `_5`). Bảng rơi `DROP_NORMAL/DROP_ELITE/DROP_BOSS/DROP_EVENT`. `scale_loot(loot, drop_factor)` giảm theo hệ số lượt chơi.
- 11 quái (`MONSTERS`) + 10 boss (`BOSSES`), mã = tên ảnh; boss luân phiên cho 16 khu. Hỗn Độn, Cùng Kỳ, Tinh Hà Thần Châu chưa có ảnh → chưa đưa vào.

### 6.5 Pháp bảo
- 9 món (`RECIPES`, mã = tên ảnh, `kind` atk/def, `min_idx` cảnh giới tối thiểu, `region == min_idx // 2` ràng buộc với bộ nguyên liệu): Công = Thanh Phong Kiếm, Xích Diễm Đao, Hàn Băng Châu, Hỗn Độn Ấn, Ngọc Hư Tiên Kiếm; Thủ = Hộ Tâm Kính, Huyền Quy Thuẫn, Cửu U Phiên, Vân Hải Chung. `LEGACY_RECIPE_CODES` đổi mã cũ (lk1…) sang mã mới; pháp bảo không còn trong danh sách bị ẩn.
- 5 bậc (`ARTIFACT_TIERS`: Linh Khí, Pháp Bảo, Linh Bảo, Tiên Bảo, Tiên Khí) × 3 phẩm (hệ số 1.0/1.25/1.6, xác suất 60/30/10; có Tụ Phẩm Đan 40/40/20). Bảo hiểm: lần 6 không ra ≥Trung thì chắc chắn ra; lần 12 không ra Thượng thì chắc chắn ra. Nâng cấp +1…+9 (`UPGRADE_*`), mỗi cấp +10%, thất bại chỉ mất nguyên liệu.
- Tối đa 2 ô (`ARTIFACT_SLOTS`): 2 công / 2 thủ / 1+1. Công → +ATK, Thủ → +HP (cộng thẳng `base × 1.25^min_idx × ratio × phẩm × cấp` + % trên chỉ số gốc `4% × (bậc+1) × …`). Thay ô, bán lại hoàn `SELL_REFUND_RATIO`=50% LS chế tạo.
- Ràng buộc nhất quán: cảnh giới → bí phương → bộ nguyên liệu → khu săn. Có test `test_areas`/craft. Thêm pháp bảo mới thì giữ `region == min_idx // 2`.

### 6.6 Chỉ số tu luyện (lợi suất giảm dần `trần × p / (p + K)`, `game_core.stat_bonuses`)
- **Ngộ tính** = số câu đáp đúng (`counters["answers_correct"]`) → tỉ lệ chí mạng, trần 25%, K=3000, chí mạng ×1.5.
- **Căn cơ** = số từ đã học → +HP và +ATK, mỗi bên trần 7.5%, K=1250.
- **Đạo tâm** = chuỗi ngày học (`user["consecutive_streak"]`) → giảm sát thương Tâm Ma Kiếp, trần 25%, K=90.
- `ctx["bonuses"]` truyền vào `core.player_stats(idx, artifacts, bonuses)` → `{atk, hp, crit}`.

### 6.7 Huy hiệu / danh hiệu
Theo `ACHIEVEMENT_LINES` (3 bậc mỗi dòng) dựa trên counter; `check_achievements(words)` gọi trong `settle`; chọn danh hiệu bằng `equip_title`.

### 6.8 Counters thường dùng (`game_counters.key`)
`answers_correct, monsters_killed, bosses_killed, flawless_boss, matches_played, perfect_matches, elite_r{realm}, equip_1, equip_2`… Thêm counter mới chỉ cần truyền trong `incr={...}` của `settle`/`apply_changes`.

## 7. Quy tắc kỹ thuật bắt buộc (đấu nối an toàn)
1. **Ghi trạng thái game CHỈ qua `game_core.apply_changes` / `settle`** (batch atomic rồi reload state). Không ghi DB lẻ trong UI. Kết thúc một lượt chơi gọi `core.settle(base_ls, idx_scale, words_learned, results=[(vocab_id, ok)], incr=..., items=..., log=(kind, text))`: tính hệ số, ghi review từ (`record_review_batch`), huy hiệu, log.
2. **Callback**: dùng `on_click` cho nút game. KHÔNG dùng `st.rerun(scope="fragment")` (lỗi khi rerun toàn trang). `_body` là `@st.fragment`.
3. **Key widget phải duy nhất.** Đang dùng: `game_nav`, `match_start/match_again`, `ml_{id}`, `mr_{id}`, `fortune_opt_{i}`, `sent_*`, `hunt_pick`, `mapbtn_{i}`, `opt_{turn}_{i}`, `pin_{turn}`, `pin_form_{turn}`, `battle_*`, `guide_open`, `guide_back`, `lk_opt_{idx}_{i}`, `btn_shadowing_reveal`. Tiền tố riêng cho module mới (ví dụ `en_`).
4. **Thêm bảng người dùng mới**: khai báo trong `userdb.py` (CREATE TABLE IF NOT EXISTS) → thêm vào `GAME_TABLES` (nếu là dữ liệu game/khóa học, để xóa user) → thêm cột vào `backup_manager.BACKUP_TABLES` (KHÔNG thêm vào `CORE_TABLES`). Mọi bảng phải có `user_id`.
5. `st.tabs` không lazy: mọi tab chạy mỗi rerun → giữ hàm render nhẹ; cache nặng bằng `st.cache_data`. Cache game state ở session_state (`get_state(force=True)` để nạp lại).
6. CSS: `style.css` (global) + CSS inline qua `st.markdown(<style>)`. `st.container(key="x")` tạo class `.st-key-x`; nút `key="y"` có `.st-key-y button`. Khi dùng `%` trong f-string CSS nhớ escape.
7. Turso/DB chậm (HTTP): gom ghi theo trận bằng `execute_many`, không ghi từng thao tác.
8. AppTest: radio nhận giá trị là KEY (`"fortune"`, `"hunt"`…) chứ không phải nhãn. Widget trong `AppTest.from_function` cần `userdb.init_schema()` trong script. Test DB: patch `userdb.LOCAL_USER_DB` và `userdb._turso_config` (xem `tests/test_game.py`).
9. Ảnh lớn phải có bản web nhẹ (map 8MB → 274KB; avatar 7MB → 16KB). Không nạp ảnh gốc trong app.
10. Pyc/`__pycache__` bị ignore; không commit DB người dùng. Nút sao lưu thủ công Google Drive nằm ở tab Quản Lý.

## 8. Hướng dẫn trong app (`guide_tab.render_guide`)
7 tab: Học & Thiên Kiếp, Động Phủ, Chỉ Số, Pháp Bảo, Nguyên liệu & Linh Thạch (có mục công dụng LS), Cảnh Giới (bảng 16 cảnh giới + khu săn), Lộ Trình (giao tiếp → đời sống → HSK4–5). Nội dung lấy số trực tiếp từ `game_config` — đổi cân bằng thì hướng dẫn tự cập nhật.

## 9. Kiểm thử
`tests/test_game.py` (17 test): ngưỡng cảnh giới, hệ số lượt, bảo hiểm, toán chiến đấu, độ sâu quái, 32 khu, chỉ số (`test_stat_bonuses`), thể thức Lật bài (`test_match_modes`), luồng DB (chế tạo, trang bị, bán). Chưa có test tự động cho Tâm Ma Kiếp (đã thử tay bằng AppTest: 0 exception). Chưa kiểm thử trên Turso thật và trình duyệt thật.

## 10. Lịch sử cập nhật
- Đợt 1: khung tu tiên (cảnh giới, kinh tế, 3 mini game, săn quái, chợ, chế tạo, huy hiệu), bảng game, công cụ dịch/nhập HSK.
- Đợt 2: đổi tên quái/boss/pháp bảo theo ảnh, bản đồ 32 khu bấm được, độ sâu quái, 2 ô pháp bảo công/thủ + bán lại, log "tuyệt kỹ", trang Hướng Dẫn, file này.
- Đợt 4: Lật bài nhiều thể thức (4 cặp/ván, thể thức hm/hp/ap/ah, tối đa 2 cặp nghe), thưởng mỗi cặp 2→3 LS để bù số cặp giảm 6→4, thêm `game_ui.audio_listener`, cập nhật hướng dẫn, test `test_match_modes` (17 test).
- Đợt 3: chỉ số Ngộ tính/Căn cơ/Đạo tâm (lợi suất giảm dần), chí mạng, Tâm Ma Kiếp, ảnh tu sĩ `avatar_web.webp`, phát âm từ chậm hơn, bỏ nút Lưu Tu Vi, xác nhận rút lui, đề `exam_engine` tách Lôi Kiếp/Tâm Ma Kiếp.

## 11. Việc còn lại / ý tưởng đã duyệt
- ~~Lật bài nhiều thể thức~~ — đã làm (đợt 4); chưa thử âm thanh trên trình duyệt thật.
- Chỉnh tọa độ nút bản đồ theo trình duyệt thật; thêm ảnh Hỗn Độn/Cùng Kỳ/Tinh Hà Thần Châu → thêm vào config.
- Mô phỏng cân bằng LS (kiếm vs tiêu) khi có số liệu chơi thật.
- Đã loại bỏ (không làm): vật phẩm tiêu hao, nhiệm vụ ngày, tuyệt kỹ theo cảnh giới. Chỉ có một tuyệt kỹ "Hỏa Cầu Thuật" (`SKILL_NAME`).
- Chưa chạy thật: `tools/translate_vocab.py` (cần `GEMINI_API_KEY`), `tools/import_hsk_vocab.py`, Turso `execute_many` với dữ liệu lớn.

## 12. (PHƯƠNG ÁN CŨ — đã được THAY bằng mục 13; chỉ giữ để tham khảo bảng các điểm gắn cứng tiếng Trung)
Gắn khóa học MỚI (ví dụ: tiếng Anh giao tiếp cho giáo viên THCS / nhân viên hành chính nhân sự)
Hiện app GẮN CỨNG vào tiếng Trung ở các điểm sau; khóa học mới phải xử lý từng điểm:
| Điểm gắn cứng | Vị trí | Gợi ý |
|---|---|---|
| Kho từ `vocab` có `hanzi, pinyin, hanviet` | `chinese_mastery.db`, `database._load_vocabulary`, `get_hanzi_options`, `get_vocab_by_ids` | Tạo DB/bảng riêng (ví dụ `english_mastery.db`, bảng `en_vocab`: `id, word, ipa, meaning_vi, example_en, example_vi, topic, study_day, priority_group`) và module `en_database.py` mô phỏng các hàm của `database.py` |
| Phát âm `zh-CN` | `app.py` (JS cuối file), `extra_tabs.SPEAK_SCRIPT`, `game_ui.speak` | Truyền `lang` làm tham số (`en-US`), bỏ hệ số theo độ dài ký tự Hán |
| Câu hỏi trắc nghiệm | `game_questions.make_question` (h2m, m2h, audio, pinyin, cloze) | Viết `en_questions.py` có cùng dạng dict `{type, prompt, hint, options, audio, word}`; bỏ `pinyin`/bộ thủ |
| Tiến độ học theo ngày | `user_progress`, `advance_user_day`, `session_state` | Bảng riêng theo khóa (`course` + `user_id` hoặc bảng `en_progress`) để không lẫn ngày học tiếng Trung |
| Cảnh giới theo số từ | `game_config.SUB_THRESHOLDS`, `HSK4_WORDS` | Chỉ áp dụng cho tiếng Trung; khóa mới cần ngưỡng riêng hoặc tab độc lập |
| Hướng dẫn / lộ trình | `guide_tab.py` | Thêm trang hướng dẫn riêng |

**Cách tích hợp an toàn (khuyến nghị, tối thiểu rủi ro cho hệ thống hiện có):**
1. Tạo các file MỚI, không sửa lõi: `en_config.py`, `en_database.py`, `en_questions.py`, `en_tab.py` (hàm `render_english()`).
2. Trong `app.py`: thêm nhãn vào `TAB_LABELS` (trước tab "Quản Lý" admin, nhớ đổi chỉ số `tabs[6]` nếu thêm tab) và `with tab_en: render_english()` — theo mẫu `with tab_game: render_cultivation(...)`.
3. Tái sử dụng (không viết lại): `auth.require_login` + `database.current_user_id()`, `userdb.get_user_db()`, `game_core.settle/apply_changes` (nếu muốn thưởng LS chung), `game_ui` (nút phát âm, tô màu nút), `exam_engine` làm mẫu bài thi, `style.css`.
4. Bảng mới: quy tắc mục 7.4 (có `user_id`, thêm vào `GAME_TABLES`/`BACKUP_TABLES`). Đặt tên bảng/khóa widget/key session_state có tiền tố `en_`.
5. Thêm test vào `tests/` (logic thuần + luồng DB tạm); chạy toàn bộ test trước khi commit.
6. Cập nhật file này sau khi xong (mục 2, 3, 12).

Điểm cần chú ý khi nhiều khóa học dùng chung game: `ctx["pool"]`/`words` hiện là kho từ TIẾNG TRUNG; nếu cho tiếng Anh dùng chung Động Phủ (săn quái, lật bài…), phải truyền `ctx` riêng có `pool` tiếng Anh và hàm `make_question` tương ứng, hoặc chỉ làm tab độc lập để tránh sửa lõi.

## 13. KẾ HOẠCH CHÍNH THỨC: thêm khóa học TIẾNG ANH (đa khóa học Anh–Trung) — chưa code
**Nguyên tắc vàng:** toàn bộ cơ chế học, ôn tập, game, tu tiên, thiên kiếp, kinh tế, pháp bảo, săn quái, chỉ số… GIỮ NGUYÊN. Khóa tiếng Anh chỉ thay DỮ LIỆU (kho từ, ngôn ngữ phát âm, nhãn hiển thị) và bỏ vài tính năng riêng tiếng Trung. Không viết lại game; không copy file game sang bản "en_". Mỗi khóa là một "tu tiên đạo" độc lập với tiến độ riêng.

### 13.1 Mô hình dữ liệu: "profile" theo khóa học (ít sửa nhất)
- Thêm bảng `profiles(id INTEGER PK, user_id INTEGER, course TEXT 'zh'|'en', level TEXT, created_at)`; UNIQUE(user_id, course). `level` của tiếng Anh: `A2` (dưới B1) | `B1` | `B2`; tiếng Trung để NULL.
- **Mọi bảng tiến độ/game hiện có (user_progress, word_mastery, exam_history, session_state, game_*) giữ nguyên schema; cột `user_id` của chúng từ nay chứa `profile_id`**. Nhờ vậy mỗi khóa có tiến độ, Linh Thạch, kho đồ, pháp bảo, nhật ký riêng mà không đổi khóa chính/không migrate bảng.
- Tương thích ngược: với mỗi user cũ, tạo profile `zh` có `profiles.id = users.id`. Profile mới (tiếng Anh) lấy id từ `1_000_000` trở lên (`MAX(id)+1` nhưng tối thiểu 1_000_000) để không đụng id user.
- `users`, `auth_tokens` vẫn dùng `user_id` thật (đăng nhập). Chỉ phần HỌC/GAME dùng profile_id.
- Code: `database.current_user_id()` hiện dùng cho cả hai nghĩa → tách: `auth_user_id()` (tài khoản, dùng trong `auth.py`/admin) và `current_profile_id()` (đọc `st.session_state["profile_id"]`; mọi hàm tiến độ/game dùng cái này). Giữ `current_user_id()` làm alias của `current_profile_id()` để không vỡ code cũ, rồi rà các chỗ trong `auth.py`, `admin_panel.py`, `backup_manager.py` đổi sang `auth_user_id()`.
- `auth.delete_user`: xóa theo MỌI profile của user (`SELECT id FROM profiles WHERE user_id=?`) trên các bảng tiến độ + `GAME_TABLES`, rồi xóa `profiles`.
- Backup: thêm `profiles` vào `BACKUP_TABLES` (KHÔNG vào `CORE_TABLES`; backup cũ không có bảng này → khi khôi phục tự tạo profile `zh` cho mỗi user).
- Session state: thêm `active_course`, `profile_id` (đặt khi login/chuyển khóa). Khóa học đang dùng lần cuối lưu bằng `meta` key `last_course_{user_id}`.

### 13.2 Kho từ vựng tiếng Anh: cùng schema để game không phải sửa
- File mới `english_mastery.db`, bảng `vocab` CÙNG tên cột với `chinese_mastery.db` (commit vào git khi dữ liệu đổi). Quy ước ánh xạ: `hanzi` = từ/cụm tiếng Anh; `pinyin` = phiên âm IPA (có thể rỗng); `traditional`, `hanviet`, `chiet_tu`, `example_pinyin` = rỗng; `meaning_vi` = nghĩa tiếng Việt; `example_zh` = câu ví dụ tiếng Anh; `example_vi`; `example_cloze` = câu điền khuyết; `domain` (chủ đề: `WORK_COMM`, `HR_ADMIN`, `TEACHER`, `GENERAL`…); `hsk_level` = mức CEFR (`A2/B1/B2/C1/C2`, giữ tên cột để khỏi đổi schema; hiển thị là CEFR); `study_day`, `stage_10d`, `priority_group` như cũ. (Tuỳ chọn: đổi tên cột hiển thị bằng `course_config.FIELD_LABELS` nhưng KHÔNG đổi tên cột DB.)
- Thứ tự học (`study_day` + `priority_group`): **giao tiếp công việc trước** (priority 1–3: họp, email, điện thoại, tuyển dụng/nhân sự, hành chính văn phòng, giảng dạy THCS), sau đó từ vựng chung theo CEFR (priority 4). Mỗi ngày 4 từ (mặc định, giữ như Trung; có thể tăng bằng `course_config.WORDS_PER_DAY` nếu người dùng muốn cấp tốc — cần xác nhận).
- Tạo/nhập dữ liệu bằng công cụ `tools/` (mẫu: `import_hsk_vocab.py`, `translate_vocab.py`); thêm `tools/import_english_vocab.py` idempotent.
- `database.get_db()`/`_load_vocabulary`/`load_day_words`/`get_vocab_by_ids`/`get_hanzi_options`, `game_questions.load_pool/all_hanzi` đều phải nhận `course` (lấy từ `st.session_state["active_course"]`) để chọn đúng file DB, và **`course` phải nằm trong tham số của hàm `@st.cache_data`** (nếu không, cache sẽ trả nhầm dữ liệu khóa kia).

### 13.3 `course_config.py` (file mới, một nơi duy nhất chứa khác biệt giữa khóa học)
Dict theo course `'zh'|'en'`: `db_path`, `tts_lang` (`zh-CN` / `en-US`), `tts_rate_short_factor` (zh 0.55; en ~0.8, điều chỉnh), `tts_rate_sentence_factor`, `label_word` ("chữ Hán"/"từ vựng"), `has_pinyin`, `has_radicals`, `has_hanviet`, `realm_thresholds`, `words_per_day`, `levels`, `title`/`flag` (🇨🇳/🇬🇧), `pronunciation_tab` (hàm render). Code chung KHÔNG được `if course == "en"` rải rác; chỉ đọc cờ từ đây. Ba nơi đang gắn cứng `zh-CN` (JS cuối `app.py`, `extra_tabs.SPEAK_SCRIPT`, `game_ui.speak`/`audio_listener`) phải đọc `tts_lang` và hệ số từ cấu hình.

### 13.4 Tính năng KHÔNG áp dụng / thay thế cho tiếng Anh
| Tiếng Trung | Tiếng Anh |
|---|---|
| Pinyin (câu hỏi `pinyin`, thể thức Lật bài `hp`, `ap`) | BỎ. `game_questions.available_types` bỏ `pinyin` khi `has_pinyin=False`; Lật bài chỉ dùng `hm` (từ↔nghĩa) và `ah` (🔊↔từ), vẫn tối đa n//2 cặp nghe. IPA chỉ hiển thị thông tin trên thẻ, không thành câu hỏi |
| Tab 🧩 Bộ Thủ (`extra_tabs.render_radicals`), chiết tự, hán việt | BỎ khỏi danh sách tab |
| Tab 🗣️ Tập Phát Âm (thanh mẫu/vận mẫu) | Thay bằng bảng **phụ âm / nguyên âm** (IPA, từ mẫu, nút nghe `en-US`; có thể thêm cặp dễ nhầm /θ/-/ð/, /ɪ/-/iː/, /l/-/r/) — viết hàm `render_pronunciation_en` trong `extra_tabs.py` và chọn theo `pronunciation_tab` |
| Sổ tay (`render_notebook`) | GIỮ, đổi nhãn cột theo `FIELD_LABELS` |
| Shadowing/Cloze/Flashcard/Review, thiên kiếp, Tâm Ma Kiếp, quẻ bói, Lật bài, Đối câu, săn quái | GIỮ NGUYÊN logic. Đối câu: tách câu tiếng Anh theo dấu cách (`gq.tokenize_sentence` hiện dùng danh sách chữ Hán → thêm nhánh tách theo từ cho `en`) |
| Câu hỏi `m2h` (nghĩa→chữ) | Giữ: nghĩa → từ tiếng Anh |

### 13.5 Trình độ & lộ trình tiếng Anh
- Khi tạo profile `en`, người dùng chọn trình độ hiện tại: **Dưới B1 (A2)**, **B1**, **B2**. Lưu vào `profiles.level`.
- Mục tiêu lý tưởng: **tăng 2 bậc CEFR trong 1 năm**: A2→B2, B1→C1, B2→C2. Trên hướng dẫn nêu rõ đây là mục tiêu lý tưởng, không bắt buộc.
- `course_config` cho `en` định nghĩa tập từ cần học theo level (số lượng/ranh giới `hsk_level`=CEFR; ước lượng vốn từ tích lũy: A2 ~1.000, B1 ~2.000, B2 ~3.250, C1 ~4.500, C2 ~5.500+ — chi tiết và quyết định chốt ở 13.9). Người học bắt đầu từ từ thuộc level hiện tại (bỏ qua từ dưới level, ưu tiên nhóm công việc), ngưỡng 48 mốc cảnh giới (`SUB_THRESHOLDS`) được co giãn từ 0 → số từ cần học của lộ trình của profile đó (hàm `realm_info(words)` nhận thêm thresholds theo profile; mặc định giữ ngưỡng tiếng Trung).
- Trang hướng dẫn (`guide_tab.py`) có phiên bản theo khóa: phần lộ trình tiếng Anh nêu: giao tiếp công sở/giảng dạy trước → từ vựng chung sau → mục tiêu +2 bậc/năm. Các phần cơ chế (pháp bảo, săn quái…) dùng chung.

### 13.6 Phân luồng khi đăng nhập & chuyển khóa nhanh
1. Sau `auth` đăng nhập thành công: tải các profile của user.
2. **0 profile** (user mới): hiện màn hình chọn nhu cầu "Học tiếng Trung / Học tiếng Anh / Cả hai" (+ chọn trình độ nếu có tiếng Anh) → tạo profile tương ứng (`INSERT INTO profiles` + `INSERT user_progress` mặc định cho profile) → vào giao diện khóa đã chọn.
3. **Có profile**: vào thẳng khóa dùng lần cuối (`meta last_course_*`); user cũ chưa có bảng `profiles` được auto-tạo profile `zh`.
4. **Chuyển khóa nhanh**: nút/segmented control "🇨🇳 Trung | 🇬🇧 Anh" ở ĐẦU sidebar (chỉ hiện khi có ≥ 2 profile; nếu chỉ có 1 thì hiện nút "➕ Thêm khóa học"). Hàm `switch_course(course)` bắt buộc làm theo thứ tự: (a) `session_snapshot()` lưu vị trí khóa đang học; (b) đặt `active_course`, `profile_id`; (c) xóa toàn bộ state gắn khóa cũ: `phase`, `sub_phase`, các `exam_*`, `g_*` (g_match, g_battle, g_run, g_sentence…), `game_state`, `hunt_pick`, `game_nav`; (d) `restore_session()` của khóa mới; (e) `st.rerun()`. Mỗi khóa có tiến độ tu luyện, Linh Thạch, kho đồ, pháp bảo, nhật ký, ngày học, chuỗi ngày ĐỘC LẬP (người học song song chấp nhận "cày 2 game").
5. Giao diện (theme, tu tiên, tab) dùng chung; chỉ tiêu đề, cờ, ngôn ngữ và tab riêng theo `course_config`. Tên tài khoản/đăng xuất dùng chung.

### 13.7 Thứ tự triển khai khuyến nghị (mỗi bước chạy test + chạy app trước khi sang bước sau)
1. `profiles` + `current_profile_id()` + auto-tạo profile `zh` cho user cũ; chưa có UI chuyển khóa; app tiếng Trung phải chạy y hệt (test hồi quy: 17 test + đăng nhập user cũ còn nguyên tiến độ).
2. `course_config.py`; tham số hóa `course` cho hàm đọc kho từ và `@st.cache_data`; tham số hóa TTS.
3. `english_mastery.db` + `tools/import_english_vocab.py` (nhập vài trăm từ công sở mẫu để thử).
4. Màn hình chọn nhu cầu/trình độ + `switch_course` + nút chuyển ở sidebar.
5. Ẩn tính năng riêng tiếng Trung (pinyin, bộ thủ, Lật bài `hp/ap`), tab phát âm phụ âm/nguyên âm, tách câu tiếng Anh cho Đối câu.
6. Ngưỡng cảnh giới theo level/lộ trình tiếng Anh + hướng dẫn tiếng Anh.
7. Cập nhật `userdb.py` (schema `profiles`), `backup_manager`, `auth.delete_user`, test mới (profile độc lập, switch không lẫn state, cache theo course), cập nhật file này.

### 13.8 Những điều KHÔNG được làm
- Không nhân bản `game_*.py`/`exam_engine.py` thành bản tiếng Anh.
- Không đổi khóa chính/tên cột của bảng cũ, không đổi cột `hanzi` thành `word` trong DB (dùng ánh xạ ở 13.2).
- Không để dữ liệu khóa này lọt vào khóa kia: mọi truy vấn tiến độ/game phải dùng `current_profile_id()`; cache phải có `course` trong khóa.
- Không commit `chinese_mastery.db`/`english_mastery.db` nếu nguồn từ vựng không đổi; không commit DB người dùng.

### 13.9 Quyết định đã chốt (người dùng xác nhận)
1. **4 từ/ngày** (`WORDS_PER_DAY = 4`, giống tiếng Trung).
2. **Nguồn từ vựng:** clone một repo GitHub chứa danh sách từ có gắn CEFR (gợi ý: Oxford 3000/5000, hoặc danh sách CEFR tương tự — kiểm tra giấy phép trước khi dùng), rồi viết `tools/import_english_vocab.py` làm đúng quy trình như `tools/import_hsk_vocab.py` + `tools/translate_vocab.py`: nhập vào `english_mastery.db` (idempotent) → gọi API AI (Gemini, `GEMINI_API_KEY` từ biến môi trường, KHÔNG commit key) để lọc từ, chuẩn hóa, gắn `domain`/`priority_group` (công việc trước), và dịch `meaning_vi` + ví dụ nếu còn thiếu (chỉ dịch dòng chưa có nghĩa, chạy lại được, ghi theo lô).
3. **Giọng Anh–Mỹ:** `tts_lang = "en-US"`.
4. **Ngưỡng từ theo thang CEFR thực tế** (vốn từ tích lũy gần đúng theo các thang của Cambridge/Oxford và nghiên cứu Milton; các nguồn lệch nhau nên đặt trong `course_config.EN_CEFR_VOCAB` để dễ chỉnh):

| Mức | Vốn từ tích lũy |
|---|---|
| A2 | ~1.000 |
| B1 | ~2.000 |
| B2 | ~3.250 |
| C1 | ~4.500 |
| C2 | ~5.500+ |

   Lộ trình = từ mức hiện tại lên +2 bậc: dưới B1 (A2) → B2 cần ~2.250 từ mới; B1 → C1 ~2.500; B2 → C2 ~2.250. Người học BẮT ĐẦU từ danh sách từ của mức kế tiếp sau mức hiện tại (từ dưới mức đã biết không đưa vào, trừ từ công việc quan trọng). Với 4 từ/ngày, ~2.250–2.500 từ ≈ 560–625 ngày học → nhiều hơn 1 năm; vì vậy `course_config` cần tính `days_needed = words/WORDS_PER_DAY` và hướng dẫn phải nói rõ: muốn kịp 1 năm thì học đều mỗi ngày kèm ôn Động Phủ, hoặc cho phép tăng `WORDS_PER_DAY` (xin ý kiến người dùng khi code). 48 mốc cảnh giới được co giãn theo tổng số từ của lộ trình (xem 13.5).

### 13.10 Chốt thêm
- **Giữ 4 từ/ngày.** "+2 bậc trong 1 năm" chỉ là mục tiêu lý tưởng, KHÔNG bắt buộc; hướng dẫn trong app phải nói đúng như vậy (không hứa hẹn, không ép tăng số từ).
- **Repo nguồn dự kiến:** `https://github.com/tvdung94/Vietnamese-English-Dictionary.git`. Lúc viết tài liệu URL này trả 404 (có thể repo private/đổi tên/sai URL) nên CHƯA xác minh được định dạng, giấy phép, và có gắn CEFR hay không. Việc đầu tiên khi làm `tools/import_english_vocab.py`: `git clone` thử, đọc README/LICENSE/cấu trúc file; ghi kết quả vào file này.
- Đây là từ điển Việt–Anh (có thể không có mức CEFR). Nếu không có CEFR: dùng danh sách từ theo CEFR/tần suất khác (ví dụ Oxford 3000/5000) làm nguồn LỌC, từ điển Việt–Anh dùng làm nguồn nghĩa tiếng Việt, và/hoặc nhờ Gemini gắn CEFR + `domain` + `priority_group` + ví dụ, rồi dịch phần còn thiếu. Importer phải: idempotent, ghi theo lô, chạy lại được, cho phép dry-run, và nhớ key API chỉ lấy từ biến môi trường.
### 13.11 Đánh giá repo nguồn thay thế: `skypediacode/english-vietnamese-dictionary` (đã kiểm tra, repo công khai, có thật)
- **Nội dung:** file SQLite `dictionary_en_vi.db` (~42 MB), 104.829 từ/cụm, 158.307 nghĩa tiếng Việt, 175.735 cặp từ–nghĩa–ví dụ (100% có câu ví dụ tiếng Anh), IPA 100% (có cột `region`: BrE/NAmE/UK/US), có thành ngữ (~1.350) và phrasal verb (~3.000).
- **Schema:** `words(id, word, lang_code)`, `definitions(id, definition, pos, sub_pos)`, `word_definitions(word_id, definition_id, example)`, `pronunciations(word_id, ipa, region)`. Một từ có NHIỀU nghĩa/ví dụ/IPA.
- **Thiếu so với yêu cầu của ta:** KHÔNG có mức CEFR, KHÔNG có tần suất, KHÔNG có chủ đề công việc (`domain`). Từ điển quá lớn (104k mục), không phải danh sách học. Ví dụ do AI/quy trình sinh tự động → chất lượng không đồng đều, không đặc thù công sở.
- **Kết luận:** dùng được làm **nguồn nghĩa + IPA + ví dụ**, KHÔNG dùng một mình làm lộ trình. Cần thêm **danh sách lọc theo CEFR** (ví dụ Oxford 3000/5000 hoặc tương đương, kiểm tra giấy phép) rồi tra nghĩa từ DB này; từ chưa có mức/chủ đề thì nhờ Gemini gắn `hsk_level`(=CEFR), `domain`, `priority_group` và soạn ví dụ công sở nếu cần.
- **Quy trình importer đề xuất** (`tools/import_english_vocab.py`, idempotent, có `--dry-run`, ghi theo lô):
  1. Clone repo về ngoài thư mục dự án (không commit file 42 MB vào repo app).
  2. Đọc danh sách lọc CEFR → với mỗi từ: lấy 1 nghĩa chính (ưu tiên nghĩa khớp `pos` của danh sách lọc, nghĩa ngắn gọn), IPA `NAmE/US` (ưu tiên, vì dùng giọng Anh–Mỹ; không có thì lấy cái đầu), 1 câu ví dụ ngắn.
  3. Điền các cột `english_mastery.db` theo ánh xạ 13.2; `study_day` = thứ tự (nhóm công việc trước), mỗi ngày 4 từ.
  4. Từ thiếu nghĩa/ví dụ/mức/chủ đề → gọi Gemini theo lô; chỉ xử lý dòng chưa có.
  5. Từ nhiều nghĩa: chọn nghĩa phù hợp bối cảnh công việc; câu hỏi `m2h`/Lật bài cần `meaning_vi` ngắn và KHÔNG trùng giữa các từ trong cùng ván (đã có kiểm tra mặt trùng ở Lật bài).
- **Giấy phép — BẮT BUỘC tuân thủ:** CC BY-SA 4.0. `english_mastery.db` là dữ liệu phái sinh → phải công bố cùng giấy phép CC BY-SA 4.0, ghi công (Skypedia, MinhQND, Wiktionary…; xem `ATTRIBUTION.md` của repo nguồn), nêu rõ đã chỉnh sửa. Cách làm: thêm `DATA_LICENSE_EN.md` (hoặc mục trong README) trích dẫn nguồn + giấy phép, và hiển thị dòng ghi công nhỏ trong trang Hướng Dẫn/footer của khóa tiếng Anh. Phần CODE của app không bị ràng buộc, nhưng file DB từ vựng tiếng Anh nếu đưa vào repo công khai phải kèm giấy phép này. Repo nguồn có tham chiếu OVDP (GPLv2) chỉ để đối chiếu; dữ liệu đã được hợp nhất vào CC BY-SA, nên vẫn giữ nguyên ghi công như repo nguồn yêu cầu. Nếu app/repo của bạn private và không phát hành DB ra ngoài thì nghĩa vụ chia sẻ nhẹ hơn, nhưng vẫn nên ghi công.
### 13.12 So sánh 2 nguồn CEFR & kiến trúc script xử lý từ vựng (đã kiểm tra thực tế)
**A. `tyypgzl/Oxford-5000-words`** — 1 file `full-word.json` (~7,9 MB), 5.948 bản ghi (4.958 từ duy nhất; 1 từ có thể lặp theo từ loại). Cấu trúc: `{id, value:{word, href, type(pos), level, us/uk{mp3,ogg}, phonetics{us,uk}, examples[]}}`. Phân bố: A1 1.076 · A2 990 · B1 902 · B2 1.571 · C1 1.404 (5 bản ghi không có level). Có IPA Mỹ (thiếu 2), câu ví dụ (thiếu 40, một số ví dụ là mẫu cấu trúc "abandon somebody…", cần lọc). Danh sách do Oxford biên soạn cho người học → chất lượng chọn từ cao, bám sát thang thi. **Rủi ro:** repo KHÔNG có LICENSE (API license trả 404); nội dung là dữ liệu của Oxford Learner's Dictionaries (bản quyền Oxford) bị cào lại → không nên phát hành lại ví dụ/URL âm thanh. Không có C2. Không có tần suất/chủ đề.
**B. `Maximax67/Words-CEFR-Dataset`** — giấy phép **MIT** (dùng tự do, giữ dòng bản quyền). SQLite `word_cefr_minified.db` (~20 MB) + CSV (`words.csv` 3,9 MB, `word_pos.csv` 9,5 MB, `pos_tags.csv`, `categories.csv`, `word_categories.csv`). Bảng: `words(word_id, word, stem_word_id)`, `word_pos(word_pos_id, word_id, pos_tag_id, lemma_word_id, frequency_count, level)`, categories theo CEFR-J. Phủ rộng mọi từ hợp lệ (hàng trăm nghìn dòng), có mức A1–**C2**, có **tần suất**, có POS (Penn Treebank), có lemma. Mức là SỐ (trung bình, ví dụ 4.00, 5.97 — làm tròn: 1=A1…6=C2) do thuật toán suy ra → nhiễu hơn Oxford ở từ hiếm; bao gồm cả tên riêng/địa danh (cần lọc; module `cefrpy` của cùng tác giả có lọc, 900 KB). Không có nghĩa, IPA, ví dụ.
**QUYẾT ĐỊNH ĐÃ CHỐT: KHÔNG dùng Oxford-5000 (rủi ro bản quyền, repo không có giấy phép). Chỉ dùng Words-CEFR-Dataset (MIT) làm nguồn mức CEFR + tần suất.** Phần A ở trên chỉ để tham khảo, đừng viết code đọc nó. Đánh đổi đã chấp nhận: mức CEFR do thuật toán suy ra nên kém chuẩn hơn ở từ hiếm → bù bằng bộ lọc chặt + Gemini rà soát.
| Vai trò | Nguồn |
|---|---|
| Danh sách từ + mức CEFR (A1–C2) + tần suất + POS + lemma | Words-CEFR-Dataset (MIT) |
| Nghĩa tiếng Việt, IPA, câu ví dụ | `skypediacode/english-vietnamese-dictionary` (CC BY-SA 4.0) |
| Chủ đề công việc (`domain`), `priority_group`, kiểm tra/sửa mức CEFR bất thường, ví dụ công sở, nghĩa còn thiếu | Gemini (lô, idempotent) |
Quy tắc chọn từ từ Words-CEFR: chỉ giữ từ viết thường toàn chữ cái, bỏ tên riêng (POS `NNP/NNPS`) và từ viết tắt/ký tự lạ; chỉ nhận dạng lemma (`lemma_word_id` = chính nó) để không học cả từ biến thể (runs, running…); mức làm tròn từ số (1=A1…6=C2), nếu từ có nhiều POS lấy POS có `frequency_count` lớn nhất; `frequency_count` ≥ ngưỡng (đặt trong config, chỉnh sau khi xem thống kê); từ phải có trong từ điển Việt–Anh (13.11) HOẶC được Gemini bổ sung nghĩa. Mức do thuật toán nhiễu: `ai_enrich` có bước kiểm tra "từ này có hợp lý ở mức CEFR đã gán không" cho các từ lệch (ví dụ tần suất rất cao nhưng mức ≥ C1, hoặc rất thấp nhưng mức ≤ A2) và ghi cờ `level_flag` để người duyệt.

**Các script cần tạo (thư mục `tools/english/`, mỗi file chạy độc lập, đọc/ghi qua `tools/english/work/` — thư mục này nằm trong `.gitignore`; có `--dry-run`, log tiến độ, chạy lại được):**
| File | Việc làm |
|---|---|
| `tools/english/config.py` | Đường dẫn nguồn (`SRC_CEFR_DB`, `SRC_DICT_DB`, `OUT_DB="english_mastery.db"`), danh sách mức, `WORDS_PER_DAY=4`, `EN_CEFR_VOCAB`, tên model Gemini, `GEMINI_API_KEY` từ biến môi trường |
| `tools/english/fetch_sources.py` | `git clone --depth 1` 2 repo (`Maximax67/Words-CEFR-Dataset`, `skypediacode/english-vietnamese-dictionary`) vào `tools/english/work/src/` (không commit); in commit hash + giấy phép để ghi công |
| `tools/english/load_cefr_dataset.py` | Từ `word_cefr_minified.db` → `work/cefr.csv` (word, pos, level_num→CEFR, frequency) theo "Quy tắc chọn từ" ở trên; in thống kê số từ/mức CEFR và ngưỡng tần suất đã dùng |
| `tools/english/select_words.py` | Từ `cefr.csv` → `work/words_leveled.csv`: loại từ quá ngắn/quá hiếm, khử trùng, giới hạn số từ mỗi mức theo `EN_CEFR_VOCAB` (A2~1.000, B1~2.000, B2~3.250, C1~4.500, C2~5.500 từ tích lũy; lấy các từ tần suất cao nhất của mỗi mức) |
| `tools/english/lookup_dictionary.py` | Với mỗi từ tra `dictionary_en_vi.db`: chọn nghĩa Việt ngắn phù hợp `pos`, IPA NAmE/US, 1 ví dụ ngắn sạch; từ không tìm thấy → đánh dấu `needs_ai`; → `work/words_enriched.csv` |
| `tools/english/ai_enrich.py` | Gemini theo lô (20–50 từ/lần, JSON schema chặt, retry/backoff, cache từng lô vào `work/ai_cache.jsonl` để chạy lại không tốn credit): dịch nghĩa/ví dụ còn thiếu, gắn `domain` (`WORK_COMM`, `HR_ADMIN`, `TEACHER`, `GENERAL`), `priority_group`, kiểm tra nghĩa ngắn gọn ≤ 40 ký tự, ví dụ công sở khi `domain` thuộc nhóm công việc |
| `tools/english/build_db.py` | Dựng `english_mastery.db` bảng `vocab` ĐÚNG schema chính (ánh xạ 13.2): sắp thứ tự học (nhóm công việc trước, rồi theo mức CEFR tăng dần, trong mức theo tần suất giảm dần), gán `study_day` = ⌈thứ tự/4⌉, `stage_10d`, `priority_group`; mỗi mức có thể xuất bản con theo trình độ người học (A2/B1/B2 bỏ từ dưới mức đã biết); chạy `PRAGMA integrity_check` |
| `tools/english/validate_db.py` | Kiểm tra: không trùng `meaning_vi` trong cùng ngày, không thiếu nghĩa/IPA/ví dụ, mỗi ngày đủ 4 từ, thống kê từ/mức/chủ đề, lấy ngẫu nhiên 30 dòng để người duyệt; trả mã lỗi ≠0 nếu có vi phạm |
| `tools/english/make_attribution.py` | Sinh `DATA_LICENSE_EN.md` (ghi công Maximax67 MIT + dòng bản quyền MIT, Skypedia/MinhQND/Wiktionary CC BY-SA 4.0, Gemini) kèm commit hash nguồn |
| `tools/english/run_all.py` | Chạy tuần tự các bước, bỏ qua bước đã có kết quả (`--force` để làm lại), in tổng kết |
Quy ước: mỗi script có hàm `main()` + `argparse`, dùng `sqlite3`/`csv`/`json` chuẩn (thêm `google-genai` đã có trong `requirements.txt`); KHÔNG import Streamlit; có test thuần cho `select_words` và `build_db` (dữ liệu giả nhỏ) trong `tests/test_english_tools.py`; không commit `work/` và các repo nguồn.
**Thứ tự làm đề xuất:** `fetch_sources` → `load_cefr_dataset` → `select_words` (xem thống kê) → `lookup_dictionary` (đo độ phủ) → `ai_enrich` (thử 100 từ trước) → `build_db` → `validate_db` → `make_attribution`.
Test thuần cần có: `select_words` (lọc tên riêng/lemma/làm tròn mức) và `build_db` (4 từ/ngày, nhóm công việc trước).
