# 📋 PHIÊN 5 - BÀN GIAO: MINI-GAME LUYỆN ĐAN

## **TỔNG QUAN**

**Phiên 5** triển khai **Mini-game Luyện Đan** - luyện ghép Hán tự-pinyin-nghĩa để tạo nguyên liệu đan dược từ từ vựng đã học.

### Yêu cầu chính:
1. ✅ Chỉ mở khi người chơi đã học ≥ 4 từ
2. ✅ Chọn công thức trước khi chơi (từ Phase 4)
3. ✅ Ghép Hán tự-pinyin-nghĩa; khóa những từ đã xử lý
4. ✅ Khi đủ nguyên liệu → bật nút "Luyện Đan"
5. ✅ Tiêu hao nguyên liệu và tính toán thành công/thất bại

---

## **PHẦN 1: HIỂU CẤU TRÚC MINI-GAME**

### Tổng quan:
- **Mục tiêu**: Ghép từ từ đã học để có nguyên liệu
- **Mở khóa**: ≥ 4 từ đã học
- **Chọn công thức**: Quyết định cần bao nhiêu từ (mỗi công thức khác nhau)
- **Tạo pool từ**: 
  - Ưu tiên từ đã học (nếu > 30 từ, giữ tất cả)
  - Bổ sung từ chưa học nếu chưa đủ
- **Ghép**: Hán-pinyin-nghĩa (3 cột, ghép theo cặp)
- **Khi dùng**: Tiêu hao nguyên liệu, luyện đan Phase 4

---

## **PHẦN 2: TRIỂN KHAI MINI-GAME**

### Files thay đổi:

#### 1. **game_config.py** (Cấu hình mini-game)

Thêm vào:
```python
# Mini-game Luyện Đan
ALCHEMIST_MIN_WORDS = 4          # Mở khóa mini-game khi đã học ≥ 4 từ
ALCHEMIST_MAX_LEARNED = 30       # Nếu > 30 từ đã học, bắt buộc giữ tất cả
ALCHEMIST_PAIRS_PER_RECIPE = {
    "pill_1": 3,   # Hạ Phẩm: 3 cặp từ
    "pill_2": 4,   # Trung Phẩm: 4 cặp từ
    "pill_3": 5,   # Thượng Phẩm: 5 cặp từ
    "pill_4": 6,   # Tối Thượng: 6 cặp từ
    "pill_5": 7,   # Tôn Thần: 7 cặp từ
}
```

#### 2. **game_minigames.py** (Thêm mini-game Luyện Đan)

Thêm hàm:
```python
def render_alchemist(ctx):
    """Mini-game Luyện Đan: ghép Hán-pinyin-nghĩa để tạo nguyên liệu.
    
    ctx["alchemist"]: trạng thái game
    """
    state = core.get_state()
    pool = ctx["pool"]
    
    # Kiểm tra mở khóa
    words_learned = core.get_words_learned(ctx["user_id"])
    if words_learned < cfg.ALCHEMIST_MIN_WORDS:
        st.warning(f"🔒 Cần học ≥ {cfg.ALCHEMIST_MIN_WORDS} từ để mở Mini-game Luyện Đan")
        return
    
    # Chọn công thức
    if state["alchemist"] is None or state["alchemist"].get("recipe") is None:
        st.subheader("📚 Chọn Công Thức Luyện Đan")
        st.caption("Mỗi công thức yêu cầu ghép từ khác nhau")
        
        recipes = core.get_owned_pill_recipes(ctx["user_id"])
        if not recipes:
            st.info("Bạn chưa mua công thức nào. Hãy ghé thăm Kho Đan Dược để mua!")
            return
        
        cols = st.columns(len(recipes))
        for i, recipe in enumerate(recipes):
            with cols[i % len(cols)]:
                pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE[recipe["code"]]
                materials = recipe["materials"]
                st.markdown(
                    f"**{recipe['name']}** "
                    f"\n🎯 Cần {pairs_need} cặp từ"
                    f"\n💪 +{recipe['bonus_atk_pct']}% ATK"
                    f"\n📊 {int(recipe['success_rate']*100)}% thành công"
                )
                if st.button(f"Chọn", key=f"alchemist_recipe_{recipe['code']}", use_container_width=True):
                    core.start_alchemist_game(ctx["user_id"], recipe["code"])
                    st.rerun()
        return
    
    # Game đang chơi
    alchemist = state["alchemist"]
    recipe = cfg.PILL_RECIPES_BY_CODE[alchemist["recipe"]]
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE[recipe["code"]]
    matched = alchemist.get("matched", [])
    pairs_matched = len(matched)
    
    st.subheader(f"📚 Mini-game Luyện Đan: {recipe['name']}")
    st.caption(f"Ghép {pairs_need} cặp từ | {pairs_matched}/{pairs_need} ✅")
    
    # Hiển thị hướng dẫn
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**Hán Tự**")
    with col2:
        st.markdown("**Pinyin**")
    with col3:
        st.markdown("**Nghĩa**")
    
    # Render bảng ghép
    words = alchemist["pool"]
    for i in range(pairs_need):
        col1, col2, col3 = st.columns(3)
        
        word = words[i]
        is_matched = i in matched
        
        with col1:
            st.text(word["hanzi"], disabled=is_matched)
        with col2:
            if is_matched:
                st.text(word.get("pinyin") or "", disabled=True)
            else:
                st.button(word.get("pinyin") or "", 
                         key=f"alchemist_pin_{i}",
                         disabled=is_matched)
        with col3:
            if is_matched:
                st.text(gq.short_meaning(word), disabled=True)
            else:
                st.button(gq.short_meaning(word),
                         key=f"alchemist_mean_{i}",
                         disabled=is_matched)
    
    # Khi đủ từ, bật nút Luyện Đan
    if pairs_matched >= pairs_need:
        st.success(f"✅ Đã sẵn {pairs_need} nguyên liệu! Sẵn sàng luyện đan.")
        if st.button("🔥 Luyện Đan", use_container_width=True, key="alchemist_craft"):
            success, msg = core.craft_pill(recipe["code"], ctx["user_id"])
            if success:
                st.success(msg)
                core.reset_alchemist_game(ctx["user_id"])
                st.rerun()
            else:
                st.error(msg)
                # Xóa trò chơi, quay lại chọn công thức
                core.reset_alchemist_game(ctx["user_id"])
                st.rerun()
    else:
        st.info(f"⏳ Cần ghép {pairs_need - pairs_matched} cặp từ nữa")
        st.caption("💡 Hãy tiếp tục ôn tập để tạo nguyên liệu cho đan dược")
```

#### 3. **game_core.py** (Thêm hàm hỗ trợ mini-game)

```python
def start_alchemist_game(user_id, recipe_code):
    """Bắt đầu mini-game luyện đan.
    
    Tạo pool từ từ đã học + bổ sung từ chưa học nếu cần.
    """
    db = get_user_db()
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE[recipe_code]
    
    # Lấy từ đã học
    learned_words = core.get_learned_words(user_id)
    
    # Kiểm tra điều kiện
    if len(learned_words) < cfg.ALCHEMIST_MIN_WORDS:
        return False, f"Cần ≥ {cfg.ALCHEMIST_MIN_WORDS} từ"
    
    # Tạo pool: ưu tiên từ đã học, nếu thiếu thì bổ sung từ chưa học
    if len(learned_words) >= pairs_need:
        # Nếu > ALCHEMIST_MAX_LEARNED, bắt buộc giữ tất cả từ đã học
        if len(learned_words) > cfg.ALCHEMIST_MAX_LEARNED:
            pool = learned_words[:pairs_need]  # Giữ tất cả từ đã học
        else:
            pool = random.sample(learned_words, min(pairs_need, len(learned_words)))
    else:
        # Bổ sung từ chưa học
        not_learned = core.get_not_learned_words(user_id)
        pool = learned_words + random.sample(not_learned, pairs_need - len(learned_words))
    
    # Lưu trạng thái game
    state = core.get_state()
    state["alchemist"] = {
        "recipe": recipe_code,
        "pool": pool,
        "matched": [],
    }
    core.set_state(state)
    
    return True, "Mini-game bắt đầu!"


def reset_alchemist_game(user_id):
    """Kết thúc mini-game luyện đan."""
    state = core.get_state()
    state["alchemist"] = None
    core.set_state(state)


def get_owned_pill_recipes(user_id):
    """Lấy danh sách công thức luyện đan mà người chơi đã mua."""
    db = get_user_db()
    rows = db.execute(
        "SELECT recipe_code FROM game_pill_recipes WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    codes = [r[0] for r in rows]
    return [cfg.PILL_RECIPES_BY_CODE[code] for code in codes if code in cfg.PILL_RECIPES_BY_CODE]


def get_learned_words(user_id):
    """Lấy danh sách từ đã học (mastered)."""
    db = get_user_db()
    rows = db.execute(
        "SELECT vocab_id FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchall()
    vocab_ids = [r[0] for r in rows]
    return database.get_vocab_by_ids(vocab_ids)


def get_not_learned_words(user_id):
    """Lấy danh sách từ chưa học."""
    db = get_user_db()
    learned_ids = db.execute(
        "SELECT vocab_id FROM word_mastery WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    learned_ids = {r[0] for r in learned_ids}
    
    # Lấy từ từ vocab pool (ở current course)
    all_words = database.get_all_vocab()
    not_learned = [w for w in all_words if w["id"] not in learned_ids]
    return not_learned
```

#### 4. **game_questions.py** (Hỗ trợ ghép)

Thêm / sử dụng hàm:
```python
def short_meaning(word, max_len=40):
    """Ý nghĩa ngắn gọn của từ."""
    meaning = word.get("meaning") or word.get("definition") or ""
    return meaning[:max_len] + ("..." if len(meaning) > max_len else "")
```

---

## **PHẦN 3: LOGIC GHÉP HƯỚNG**

### Kiểm tra mỗi ghép:
1. **Chọn Hán tự** → Khóa nút này
2. **Chọn pinyin** → Kiểm tra có khớp không
3. **Chọn nghĩa** → Kiểm tra có khớp không
4. **Nếu khớp cả 3**:
   - Khóa 3 nút này
   - Thêm vào `matched[]`
   - Hiển thị ✅ hoặc ⚡
5. **Nếu sai**: Bật toast cảnh báo, cho phép chọn lại

---

## **PHẦN 4: TRIỂN KHAI KỲ VỌNG**

### Người dùng flow:
1. **Vào tab Cultivation**
2. **Chọn "Mini-game Luyện Đan"**
3. **Chọn công thức** (từ Phase 4)
4. **Ghép từ**: Hán-pinyin-nghĩa (chuỗi)
5. **Nút "Luyện Đan"** bật khi đủ nguyên liệu
6. **Luyện đan**: Tiêu hao nguyên liệu, tính thành công
7. **Kết quả**: Đan thành công/thất bại
8. **Quay lại**: Chọn công thức khác hoặc thoát

---

## **PHẦN 5: KIỂM THỰC**

### Các kiểm tra bắt buộc:

1. **Mở khóa Mini-game**
   - ✅ < 4 từ đã học: hiển thị "🔒"
   - ✅ ≥ 4 từ: cho phép chơi

2. **Chọn công thức**
   - ✅ Danh sách công thức mua
   - ✅ Mỗi công thức hiển thị số cặp cần ghép

3. **Tạo pool từ**
   - ✅ Ưu tiên từ đã học
   - ✅ Nếu > 30 từ đã học, giữ tất cả
   - ✅ Bổ sung từ chưa học nếu cần

4. **Ghép Hán-pinyin-nghĩa**
   - ✅ Khóa những từ đã xử lý
   - ✅ Hiển thị rõ từng cột

5. **Bật nút Luyện Đan**
   - ✅ Khi ≥ số cặp cần → bật nút
   - ✅ Bấm → luyện đan (gọi Phase 4)

6. **Tiêu hao nguyên liệu**
   - ✅ Dù thành công hay thất bại
   - ✅ Kho được cập nhật

---

## **IMPORTANT NOTES**

### ⚠️ Kỹ thuật:
1. **Pool từ cắt theo công thức**: Mỗi công thức có số cặp khác → tạo độ khó
2. **Khóa nút ghép**: Ngăn chọn lại cùng một từ
3. **Bảo toàn nguyên liệu**: Mini-game chỉ tiêu hao khi Luyện Đan được bấm

### 💡 Tại sao thiết kế này?
- ✅ Mini-game tạo động lực ôn tập từ vựng
- ✅ Từ đã học được tái sử dụng (ghép)
- ✅ Độ khó gia tăng (công thức cao cấp = nhiều từ)
- ✅ Liên kết với Phase 4 (luyện đan)

---

## **READY FOR IMPLEMENTATION**

```
Status: SPECIFICATION COMPLETE
Next: Code Implementation → Unit Tests → E2E Tests
Test Focus: Unlock, Pool Creation, Matching, Craft
Dependencies: Phase 4 (Pill recipes)
```

---

**Phiên 5 Spec**: 2026-11-07  
**Status**: ✅ READY FOR CODING  
**Depends on**: Phase 4 (Alchemy foundation)  
**Next**: Manual Testing & Polish
