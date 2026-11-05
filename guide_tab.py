"""Trang Hướng Dẫn: cách học, động phủ, thiên kiếp, pháp bảo, cảnh giới và lộ trình."""
import streamlit as st

import game_config as cfg
import game_core as core
from course_config import get_config
from database import get_db

EN_TARGET = {"A2": "B2", "B1": "C1", "B2": "C2"}

def _realm_rows():
    rows = []
    for r, name in enumerate(cfg.MAJOR_REALMS):
        start = cfg.SUB_THRESHOLDS[3 * r]
        end = cfg.SUB_THRESHOLDS[3 * r + 3] if 3 * r + 3 < len(cfg.SUB_THRESHOLDS) else cfg.HSK5_WORDS
        rows.append({"Cảnh giới": name, "Giới": cfg.world_of(r), "Số từ": f"{start} → {end}",
                     "Khu săn": f"{cfg.AREAS[2 * r]['name']} · {cfg.AREAS[2 * r + 1]['name']}"})
    return rows


def render_guide():
    zh = get_config()["has_pinyin"]
    st.markdown("## 📖 Hướng Dẫn Tu Luyện" + ("" if zh else " — Khóa Tiếng Anh"))
    if not zh:
        st.caption("Cách chơi, Động Phủ, Thiên Kiếp, pháp bảo và cảnh giới dùng chung cho cả hai khóa; "
                   "phần dưới đã được điều chỉnh cho khóa tiếng Anh. Mỗi khóa có tiến độ, Linh Thạch và kho đồ riêng.")
    st.button("⬅️ Quay lại việc học", key="guide_back", type="primary",
              on_click=lambda: st.session_state.update(show_guide=False))
    t_daily, t_game, t_stat, t_art, t_farm, t_realm, t_road = st.tabs(
        ["🌅 Học & Thiên Kiếp", "🏯 Động Phủ", "🧬 Chỉ Số", "🗡️ Pháp Bảo", "💎 Nguyên liệu & Linh Thạch",
         "⚡ Cảnh Giới", "🧭 Lộ Trình"])

    with t_daily:
        st.markdown(f"""
**Tu luyện hằng ngày = học bài MỚI.** Mỗi ngày bạn học 4 từ mới qua 3 chặng:
1. **Flashcard** – hấp thụ {"chữ, nghĩa, pinyin" if zh else "từ, nghĩa tiếng Việt, phiên âm IPA"}.
2. **Shadowing** – nghe và nhại lại phát âm.
3. **Điền từ (Cloze)** – điền vào câu để nhớ cách dùng.

Hoàn thành xong, bấm nút sang bài/thiên kiếp ở cuối buổi: ✨ Linh Lực theo số phút bạn tập trung sẽ tự được cộng (không cần bấm lưu).

**Động Phủ là nơi ÔN LẠI** các từ đã học (không học từ mới ở đây). Chơi bao nhiêu cũng được.

### ⚡ Thiên Kiếp (kiểm tra định kỳ)
- **Tiểu Thiên Kiếp** – cuối mỗi 3 ngày: 20 câu ôn các từ vừa học.
- **Đại Thiên Kiếp** – cuối mỗi 10 ngày: 50 câu, gồm **{50 - cfg.TAM_MA_Q_MAJOR} câu Lôi Kiếp** rồi
  **{cfg.TAM_MA_Q_MAJOR} câu Tâm Ma Kiếp** ở cuối.
- Cần đúng **≥ 85%** để vượt kiếp, sang ngày kế và thăng tu vi.
- **Tâm Ma Kiếp**: các từ bạn hay sai (Tâm Ma Bảng) hiện hình. Càng nhiều tâm ma, lôi kiếp càng mạnh: mỗi câu sai
  ở giai đoạn này bị trừ **thêm** `T × (1 − giảm nhờ Đạo tâm)` điểm, với `T = tâm ma / (tâm ma + {cfg.TAM_MA_K})`.
  Thanh **🛡️ Đạo thể** cạn dần theo số câu sai; cạn hết nghĩa là trượt kiếp. Ôn sạch Tâm Ma Bảng trước kỳ thi sẽ dễ qua hơn.
- Trượt: bạn rơi vào **Bình Cảnh** – việc học từ mới bị phong ấn. Hãy **Bế Quan** để tích đủ Linh Lực rồi bấm
  **Kích Hoạt Lôi Kiếp** để thi lại.
- Từ nào sai nhiều sẽ vào **Tâm Ma Bảng** để bạn ôn riêng.
""")

    with t_game:
        LAT_MODES = ("**Hán ↔ nghĩa**, **Hán ↔ pinyin**, **🔊 nghe ↔ pinyin**, **🔊 nghe ↔ Hán**" if zh else
                     "**từ tiếng Anh ↔ nghĩa tiếng Việt** và **🔊 phát âm ↔ nghĩa tiếng Việt**")
        QUESTIONS = ("Hán → nghĩa, nghĩa → Hán, nghe → chọn chữ, điền pinyin (và điền từ khi đủ điều kiện)" if zh else
                     "từ → nghĩa, nghĩa → từ, nghe → chọn từ (và điền từ khi đủ điều kiện)")
        st.markdown(f"""
Mọi hoạt động trong Động Phủ đều là một bài ôn từ vựng và đều được ghi vào **📔 Nhật Ký Tu Tiên**.

### 🔮 Quẻ Bói (mỗi ngày 1 lần)
Rút quẻ để nhận lời sấm và **buff trong ngày** (thêm Linh Thạch, Hộ Thân Phù chắn đòn, tăng tỉ lệ rơi đồ).
Giải đúng câu đố của quẻ để nhận thưởng; sai thì quẻ chuyển Hung và từ đó vào Tâm Ma.

### 🃏 Lật Bài
Mỗi ván 4 cặp, trộn nhiều thể thức: {LAT_MODES}
(tối đa 2 cặp là dạng nghe; nút 🔊 có đánh số, bấm để phát âm rồi chọn mặt khớp ở cột phải). Đúng: giữ màu xanh.
Sai: chuyển đỏ và không chọn lại. Chơi vô hạn để cày Linh Thạch (thưởng giảm dần theo số lượt trong ngày).

### 🧩 Đối Câu / Sắp Xếp Câu
Sắp các từ thành câu đúng ngữ pháp. Mở khóa từ Trúc Cơ Kỳ và ≥ {cfg.GAME_UNLOCKS['sentence']['words']} từ đã học.

### 🗺️ Săn Yêu Thú (chiến đấu theo lượt)
- Mỗi lượt là **một câu hỏi**: {QUESTIONS}.
- Đúng: bạn dùng tuyệt kỹ **{cfg.SKILL_NAME}** gây sát thương, **combo** tăng sát thương. Sai: quái phản công.
- Bản đồ chia **Phàm Giới** (9 cảnh giới đầu) và **Tiên Giới** (7 cảnh giới có chữ Tiên). Mỗi cảnh giới có **2 khu**:
  - ⚔️ **Khu thường**: quái thường, rơi nguyên liệu thường.
  - 👑 **Khu tinh anh & Boss**: tinh anh rơi thêm nguyên liệu hiếm/quý. Hạ **{cfg.SPECIAL_MIN_KILLS} tinh anh** để mở
    **thách đấu Boss** (vượt cơ quan rồi đánh boss, rơi đồ quý).
- Rê chuột / chạm vào biểu tượng trên bản đồ để xem tên khu và vật phẩm rơi. Khu 🔒 cần đạt cảnh giới tương ứng.
- **Đi sâu**: cứ {cfg.DEPTH_EVERY} trận thắng liên tiếp, nhật ký báo bạn đi sâu hơn và quái mạnh dần.
  Rút lui hoặc thua rồi vào lại thì quái **trở về sức mạnh ban đầu** (ngang cảnh giới của khu).
""")

    with t_stat:
        ex = [core.stat_bonuses(answers=n)["crit"] * 100 for n in (500, 3000, 10000)]
        hp = [core.stat_bonuses(words=n)["hp"] * 100 for n in (600, 1250, 2500)]
        dt = [core.stat_bonuses(streak=n)["dao_tam"] * 100 for n in (7, 30, 100, 365)]
        st.markdown(f"""
Ba chỉ số này **tự tăng khi bạn học**, không thể mua. Hiệu ứng có **lợi suất giảm dần** (công thức
`trần × điểm / (điểm + K)`): càng cao thì mỗi điểm thêm càng ít hiệu quả, nên không thể cày một chỉ số để vượt
quái quá xa. Tổng sức mạnh nhờ chỉ số chỉ khoảng **+15%**; phần lớn sức mạnh vẫn đến từ cảnh giới và pháp bảo.

| Chỉ số | Là gì | Tác dụng | Công thức |
|---|---|---|---|
| 🧠 **Ngộ tính** | Tổng số câu đã trả lời đúng (mọi trò chơi) | Tăng **tỉ lệ chí mạng** (sát thương ×{cfg.CRIT_MULT}) | `{int(cfg.CRIT_MAX * 100)}% × N / (N + {cfg.CRIT_K})` |
| 📖 **Căn cơ** | Số từ vựng đã học | Tăng **HP** và **sát thương** gốc | `{cfg.CAN_CO_HP_MAX * 100:.1f}% × W / (W + {cfg.CAN_CO_K})` (mỗi bên) |
| 🔥 **Đạo tâm** | Số ngày học liên tiếp | **Giảm sát thương Tâm Ma Kiếp** | `{int(cfg.DAO_TAM_MAX * 100)}% × D / (D + {cfg.DAO_TAM_K})` |

**Ví dụ**
- Ngộ tính 500 / 3000 / 10000 câu đúng → chí mạng {ex[0]:.1f}% / {ex[1]:.1f}% / {ex[2]:.1f}%.
- Căn cơ 600 / 1250 / 2500 từ → HP và sát thương +{hp[0]:.1f}% / +{hp[1]:.1f}% / +{hp[2]:.1f}%.
- Đạo tâm 7 / 30 / 100 / 365 ngày → giảm sát thương Tâm Ma Kiếp {dt[0]:.1f}% / {dt[1]:.1f}% / {dt[2]:.1f}% / {dt[3]:.1f}%.

Nghỉ học làm chuỗi ngày về 0 nên Đạo tâm mất; Ngộ tính và Căn cơ thì giữ nguyên.
""")

    with t_art:
        order = " → ".join(f"{t['name']}" for t in cfg.ARTIFACT_TIERS.values())
        odds = " · ".join(f"{n} {int(o * 100)}%" for n, o in zip(cfg.QUALITY_NAMES, cfg.QUALITY_ODDS))
        st.markdown(f"""
- **Bậc**: {order}. Mỗi bậc có 3 phẩm: Hạ – Trung – Thượng.
- **Bí phương** mua ở Phường Thị bằng Linh Thạch; mỗi bí phương cố định hình dáng, bậc và cảnh giới yêu cầu.
- **Chế tạo**: tốn Linh Thạch + nguyên liệu. Phẩm được random: {odds}. **Bảo hiểm**: sau {cfg.PITY_MID_AT} lần
  không ra Trung Phẩm+ thì chắc chắn ra, sau {cfg.PITY_HIGH_AT} lần không ra Thượng Phẩm thì chắc chắn ra.
  💊 Tụ Phẩm Đan làm tăng tỉ lệ phẩm cao.
- **Công / Thủ**: pháp bảo *Công* tăng sức công (cộng thẳng + %), pháp bảo *Thủ* tăng HP (cộng thẳng + %).
- **Mang tối đa {cfg.ARTIFACT_SLOTS} pháp bảo** (2 công, 2 thủ hoặc 1 công + 1 thủ tùy bạn). Thay pháp bảo bằng nút
  *Thay ô*, hoặc **bán** pháp bảo cũ để thu hồi {int(cfg.SELL_REFUND_RATIO * 100)}% Linh Thạch chế tạo.
- **Nâng cấp** (+1 … +{cfg.UPGRADE_MAX}) tốn Linh Thạch và nguyên liệu, có thể thất bại.
""")

    with t_farm:
        st.markdown(f"""
### 💎 Công dụng Linh Thạch
Linh Thạch là tiền tệ duy nhất của Động Phủ, dùng để:
1. **Mua bí phương** ở Phường Thị (mỗi bí phương mở một pháp bảo).
2. **Chế tạo pháp bảo** (cùng nguyên liệu săn được).
3. **Nâng cấp pháp bảo** +1 … +{cfg.UPGRADE_MAX} (tốn thêm nguyên liệu, có thể thất bại).
4. **Mua Tụ Phẩm Đan** để tăng tỉ lệ ra phẩm cao khi chế tạo.
5. Bán pháp bảo cũ để **thu hồi {int(cfg.SELL_REFUND_RATIO * 100)}%** Linh Thạch chế tạo.

Kiếm Linh Thạch bằng cách chơi Quẻ Bói, Lật Bài, Đối Câu và đặc biệt là săn yêu thú, tinh anh, boss.

### Vòng lặp
`Học từ mới → ôn ở Động Phủ → có Linh Thạch + nguyên liệu → mua bí phương / chế tạo / nâng cấp → mạnh hơn → vào khu cao hơn`

### Săn nguyên liệu
- Mỗi **bộ nguyên liệu** phục vụ 2 cảnh giới liền kề (ví dụ Linh Khí + Trúc Cơ). Mỗi bộ gồm 3 nguyên liệu thường,
  2 hiếm, 1 quý.
- **Khu thường** → nguyên liệu *thường*. **Khu tinh anh** → thêm *hiếm* và rất ít *quý*. **Boss** → hiếm nhiều, *quý* khả dụng cao.
- Bí phương nào cũng ghi rõ nên săn ở khu nào (xem tab *Bí phương* trong Phường Thị).

### Cày Linh Thạch
- {cfg.DAILY_FULL_PLAYS} trận đầu mỗi ngày nhận **100%**, trận {cfg.DAILY_FULL_PLAYS + 1}–{cfg.DAILY_MID_PLAYS} nhận
  **{int(cfg.MULT_MID * 100)}%**, từ trận {cfg.DAILY_MID_PLAYS + 1} nhận **{int(cfg.MULT_LOW * 100)}%**.
- Không giới hạn số lượt chơi; thưởng giảm để tránh lạm phát. Cảnh giới cao hơn thì thưởng và giá đều tăng.
- Boss cho Linh Thạch nhiều nhất mỗi trận.
""")

    with t_realm:
        REALM_END = (f"Độ Kiếp Kỳ ứng với hoàn thành **HSK 4 (~{cfg.HSK4_WORDS} từ)** và Tiên Đế ứng với **HSK 5 (~{cfg.HSK5_WORDS} từ)**."
                     if zh else f"Độ Kiếp Kỳ ứng với khoảng **{cfg.HSK4_WORDS} từ** và Tiên Đế ứng với khoảng **{cfg.HSK5_WORDS} từ** đã học.")
        st.markdown(f"""
Có **{len(cfg.MAJOR_REALMS)} cảnh giới**, mỗi cảnh giới chia **Sơ – Trung – Hậu Kỳ** (48 tiểu kỳ). Tu vi tăng theo
**số từ đã học**; {REALM_END}
""")
        st.dataframe(_realm_rows(), hide_index=True, use_container_width=True)

    with t_road:
        if zh:
            st.markdown(f"""
### Thứ tự học
1. **Giao tiếp trước**: các từ/câu dùng hằng ngày và công sở được ưu tiên để nói được sớm.
2. **Từ vựng đời sống** sau đó.
3. Tiếp tục mở rộng lên HSK 4 rồi HSK 5.

### Mục tiêu tham khảo
- **HSK 4 (~{cfg.HSK4_WORDS} từ) trong khoảng 1 năm** (4 từ mới/ngày) – đây là mục tiêu lý tưởng, không bắt buộc.
- **HSK 5 (~{cfg.HSK5_WORDS} từ)** sau đó, không giới hạn thời gian.
- Có thể chậm hơn nhưng đều đặn: mỗi ngày học bài mới, rồi dành vài phút ở Động Phủ để ôn từ cũ.
""")
        else:
            level = st.session_state.get("course_level") or "B1"
            target = EN_TARGET.get(level, "C1")
            conn = get_db()
            total = conn.execute("SELECT COUNT(*) FROM vocab").fetchone()[0]
            conn.close()
            st.markdown(f"""
### Thứ tự học
1. Học theo **trình độ CEFR bạn đã chọn ({level})**: kho từ chỉ gồm các từ **cao hơn** trình độ này, nên không phải học lại từ quá dễ.
2. Trong kho từ, các nhóm **giao tiếp công sở, hành chính – nhân sự, giảng dạy** được đưa lên trước, sau đó mở rộng vốn từ theo CEFR tăng dần.
3. Mỗi ngày 4 từ mới, ôn lại ở Động Phủ như khóa tiếng Trung.

### Mục tiêu tham khảo
- Lý tưởng là **tăng 2 bậc CEFR trong khoảng 1 năm**: A2 → B2, B1 → C1, B2 → C2. Với trình độ **{level}**, mục tiêu là **{target}** — đây chỉ là mục tiêu lý tưởng, không bắt buộc.
- Kho từ của bạn hiện có **{total} từ** (~{-(-total // get_config()["words_per_day"])} ngày học với {get_config()["words_per_day"]} từ/ngày).

### 🎯 Đổi trình độ
Thấy từ quá dễ hoặc quá khó? Mở **🎯 Trình độ** ở menu bên trái (dưới ô chọn khóa học) để chọn lại **A2 / B1 / B2**.
Kho từ được lọc lại theo trình độ mới, ngày học chuyển tới từ đầu tiên bạn chưa học; Linh Thạch, kho đồ và độ thuộc các từ đã học được giữ nguyên.
""")
