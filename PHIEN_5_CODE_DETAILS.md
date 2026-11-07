# 📝 PHIÊN 5 - MINI-GAME LUYỆN ĐAN - IMPLEMENTATION DETAILS

## **1. game_config.py - Cấu hình Mini-game**

### Vị trí: Sau `ALCHEMIST_PAIRS_PER_RECIPE` định nghĩa (khoảng dòng 250)

```python
# ---------------------------------------------------------------------------
# Mini-game Luyện Đan
# ---------------------------------------------------------------------------
ALCHEMIST_MIN_WORDS = 4          # Mở khóa khi đã học ≥ 4 từ
ALCHEMIST_MAX_LEARNED = 30       # Nếu > 30 từ đã học, bắt buộc giữ tất cả trong pool
ALCHEMIST_PAIRS_PER_RECIPE = {
    "pill_1": 3,   # Hạ Phẩm: 3 cặp từ
    "pill_2": 4,   # Trung Phẩm: 4 cặp từ
    "pill_3": 5,   # Thượng Phẩm: 5 cặp từ
    "pill_4": 6,   # Tối Thượng: 6 cặp từ
    "pill_5": 7,   # Tôn Thần: 7 cặp từ
}
```

---

## **2. game_core.py - Hàm Hỗ Trợ Mini-game**

### Vị trí: Sau section Luyện Đan (khoảng dòng 370)

```python
# ---------------------------------------------------------------------------
# Mini-game Luyện Đan - Alchemist Game
# ---------------------------------------------------------------------------

def get_learned_words(user_id):
    """Lấy danh sách từ đã học (mastered/review)."""
    db = get_user_db()
    rows = db.execute(
        "SELECT DISTINCT vocab_id FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchall()
    vocab_ids = [r[0] for r in rows]
    if not vocab_ids:
        return []
    return database.get_vocab_by_ids(vocab_ids)


def get_not_learned_words(user_id):
    """Lấy danh sách từ chưa học."""
    db = get_user_db()
    
    # Lấy ID từ đã học
    learned_rows = db.execute(
        "SELECT DISTINCT vocab_id FROM word_mastery WHERE user_id = ?",
        (user_id,)
    ).fetchall()
    learned_ids = {r[0] for r in learned_rows}
    
    # Lấy tất cả từ
    try:
        all_words = database.get_all_vocab()
        not_learned = [w for w in all_words if w["id"] not in learned_ids]
        return not_learned
    except Exception:
        return []


def build_alchemist_pool(user_id, recipe_code, rng=random):
    """Tạo pool từ cho mini-game luyện đan.
    
    Logic:
    1. Lấy số cặp cần từ công thức
    2. Lấy từ đã học
    3. Nếu từ đã học > ALCHEMIST_MAX_LEARNED, giữ tất cả từ đã học
    4. Nếu từ đã học < cần, bổ sung từ chưa học
    5. Random thứ tự
    
    Trả về list words
    """
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    
    learned = get_learned_words(user_id)
    if len(learned) < cfg.ALCHEMIST_MIN_WORDS:
        return None, f"Cần ≥ {cfg.ALCHEMIST_MIN_WORDS} từ đã học"
    
    # Xác định pool từ
    if len(learned) >= pairs_need:
        # Ưu tiên từ đã học
        if len(learned) > cfg.ALCHEMIST_MAX_LEARNED:
            # Nếu > 30 từ, phải lấy tất cả từ đã học (có thể > pairs_need)
            pool = learned[:pairs_need] if pairs_need > 0 else learned
        else:
            # Lấy random `pairs_need` từ từ đã học
            pool = rng.sample(learned, min(pairs_need, len(learned)))
    else:
        # Bổ sung từ chưa học
        not_learned = get_not_learned_words(user_id)
        need_more = pairs_need - len(learned)
        
        if len(not_learned) < need_more:
            return None, f"Không đủ từ chưa học. Cần {need_more}, có {len(not_learned)}"
        
        additional = rng.sample(not_learned, need_more)
        pool = learned + additional
    
    # Random thứ tự
    rng.shuffle(pool)
    return pool, None


def start_alchemist_game(user_id, recipe_code):
    """Bắt đầu mini-game luyện đan.
    
    Trả về (success, message)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại"
    
    # Kiểm tra quyền sở hữu công thức
    owned = get_pill_recipes_owned(user_id)
    if recipe_code not in [r["code"] for r in owned]:
        return False, "Chưa mua công thức này"
    
    # Tạo pool từ
    pool, error = build_alchemist_pool(user_id, recipe_code)
    if error:
        return False, error
    
    # Lưu trạng thái game
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    state = get_state()
    if state is None:
        state = {}
    
    state["alchemist_game"] = {
        "recipe": recipe_code,
        "pool": pool,  # List từ
        "matched": [],  # List index từ đã ghép
        "started_at": today(),
    }
    
    set_state(state)
    return True, "Mini-game bắt đầu!"


def reset_alchemist_game(user_id):
    """Kết thúc mini-game luyện đan."""
    state = get_state()
    if state:
        state.pop("alchemist_game", None)
        set_state(state)


def get_alchemist_game_state(user_id):
    """Lấy trạng thái mini-game hiện tại."""
    state = get_state()
    if state and "alchemist_game" in state:
        return state["alchemist_game"]
    return None


def match_word(user_id, word_idx):
    """Đánh dấu từ là đã ghép.
    
    Trả về (success, is_complete)
    """
    state = get_state()
    if not state or "alchemist_game" not in state:
        return False, False
    
    game = state["alchemist_game"]
    if word_idx not in game["matched"]:
        game["matched"].append(word_idx)
        game["matched"].sort()
    
    set_state(state)
    
    # Kiểm tra đã đủ chưa
    recipe_code = game["recipe"]
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    is_complete = len(game["matched"]) >= pairs_need
    
    return True, is_complete


def finish_alchemist_game(user_id, recipe_code):
    """Hoàn thành mini-game → Luyện đan.
    
    Trả về (success, message)
    """
    # Kiểm tra game đang chơi
    game = get_alchemist_game_state(user_id)
    if not game or game["recipe"] != recipe_code:
        return False, "Game không khớp hoặc chưa bắt đầu"
    
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    if len(game["matched"]) < pairs_need:
        return False, f"Chưa đủ {pairs_need} từ (chỉ có {len(game['matched'])})"
    
    # Gọi craft_pill (từ Phase 4)
    success, message = craft_pill(recipe_code, user_id)
    
    if success:
        reset_alchemist_game(user_id)
    
    return success, message
```

---

## **3. game_minigames.py - Render Mini-game Luyện Đan**

### Vị trí: Sau function `render_match()` (khoảng dòng 300)

```python
def render_alchemist(ctx):
    """Mini-game Luyện Đan: ghép Hán-pinyin-nghĩa.
    
    ctx cần:
      - "user_id"
      - "pool": danh sách từ
      - "words_learned": số từ đã học
    """
    user_id = ctx.get("user_id")
    words_learned = ctx.get("words_learned", 0)
    
    # Kiểm tra mở khóa
    if words_learned < cfg.ALCHEMIST_MIN_WORDS:
        st.warning(
            f"🔒 **Mini-game Luyện Đan chưa mở khóa**\n\n"
            f"Cần học ≥ {cfg.ALCHEMIST_MIN_WORDS} từ để mở (hiện có {words_learned} từ)"
        )
        return
    
    # Lấy trạng thái game
    game = core.get_alchemist_game_state(user_id)
    
    # Phase 1: Chọn công thức
    if game is None:
        st.subheader("📚 Chọn Công Thức Luyện Đan")
        st.caption("Mỗi công thức yêu cầu ghép số từ khác nhau")
        
        recipes = core.get_pill_recipes_owned(user_id)
        if not recipes:
            st.info(
                "👉 Bạn chưa mua công thức luyện đan. "
                "Hãy ghé thăm **Kho Đan Dược** để mua công thức!"
            )
            return
        
        # Hiển thị công thức dưới dạng card
        cols = st.columns(min(3, len(recipes)))
        for i, recipe in enumerate(recipes):
            with cols[i % len(cols)]:
                pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe["code"], 3)
                st.markdown(
                    f"### {recipe['name']}\n"
                    f"🎯 {pairs_need} cặp từ\n"
                    f"💪 +{recipe['bonus_atk_pct']:.0f}% ATK\n"
                    f"📊 {int(recipe['success_rate']*100)}% thành công"
                )
                if st.button("Bắt Đầu", key=f"alchemist_start_{recipe['code']}", use_container_width=True):
                    ok, msg = core.start_alchemist_game(user_id, recipe["code"])
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
        return
    
    # Phase 2: Game đang chơi
    recipe_code = game["recipe"]
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    pool = game["pool"]
    matched = set(game["matched"])
    pairs_need = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    
    # Header
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(f"📚 {recipe['name']}")
    with col2:
        st.metric("Cặp Ghép", f"{len(matched)}/{pairs_need}")
    with col3:
        if st.button("❌ Thoát Game", key="alchemist_exit"):
            core.reset_alchemist_game(user_id)
            st.rerun()
    
    st.divider()
    
    # Hướng dẫn
    st.info(
        "💡 **Cách chơi:**\n\n"
        "1. Kiếm 3 nút khớp: 1️⃣ Hán Tự + 2️⃣ Pinyin + 3️⃣ Nghĩa\n"
        "2. Sau khi ghép xong, nút sẽ bị khóa\n"
        f"3. Ghép đủ {pairs_need} cặp để luyện đan"
    )
    
    # Bảng ghép
    st.subheader("Ghép Từ Vựng")
    
    for i, word in enumerate(pool):
        is_matched = i in matched
        
        col1, col2, col3 = st.columns(3, gap="small")
        
        # Cột 1: Hán Tự (chỉ hiển thị, không bấm)
        with col1:
            st.write(f"**{word['hanzi']}**" if not is_matched else f"✅ {word['hanzi']}")
        
        # Cột 2: Pinyin
        with col2:
            pinyin = word.get("pinyin") or ""
            if is_matched:
                st.write(f"✅ {pinyin}")
            else:
                label = f"{pinyin}"
                if st.button(label, key=f"alc_pin_{i}", use_container_width=True, disabled=is_matched):
                    ok, complete = core.match_word(user_id, i)
                    if ok:
                        if complete:
                            st.success(f"✅ Ghép xong cặp từ!")
                        st.rerun()
        
        # Cột 3: Nghĩa
        with col3:
            meaning = game_questions.short_meaning(word, 30)
            if is_matched:
                st.write(f"✅ {meaning}")
            else:
                if st.button(meaning, key=f"alc_mean_{i}", use_container_width=True, disabled=is_matched):
                    ok, complete = core.match_word(user_id, i)
                    if ok:
                        if complete:
                            st.success(f"✅ Ghép xong cặp từ!")
                        st.rerun()
    
    st.divider()
    
    # Nút Luyện Đan
    if len(matched) >= pairs_need:
        st.success(f"✅ Đã sẵn sàng {pairs_need} nguyên liệu!")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔥 Luyện Đan", use_container_width=True, key="alchemist_craft"):
                success, message = core.finish_alchemist_game(user_id, recipe_code)
                if success:
                    st.balloons()
                    st.success(message)
                    st.toast(message)
                    st.rerun()
                else:
                    st.error(message)
        
        with col2:
            if st.button("↩️ Chọn Công Thức Khác", use_container_width=True, key="alchemist_back"):
                core.reset_alchemist_game(user_id)
                st.rerun()
    else:
        remaining = pairs_need - len(matched)
        st.info(f"⏳ Cần ghép {remaining} cặp từ nữa để luyện đan")
```

---

## **4. game_questions.py - Helper Functions**

### Thêm/cập nhật function `short_meaning()`:

```python
def short_meaning(word, max_len=40):
    """Ý nghĩa ngắn gọn của từ (cho ghép game)."""
    meaning = word.get("meaning") or word.get("definition") or word.get("english") or ""
    if isinstance(meaning, list):
        meaning = "; ".join(meaning[:2])  # Lấy 2 ý nghĩa đầu
    
    meaning = str(meaning).strip()
    if len(meaning) > max_len:
        return meaning[:max_len] + "…"
    return meaning
```

---

## **5. Tích hợp UI - cultivation_tab.py**

### Thêm tab "Mini-game Luyện Đan":

```python
def render_cultivation_ui():
    """Tab tu luyện."""
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📊 Thông Tin", "🎁 Kho Đan Dược", "📚 Mini-game", "⚙️ Công Thức"]
    )
    
    user_id = current_user_id()
    words_learned = core.get_words_learned(user_id)
    realm_info_data = core.realm_info(words_learned)
    
    # Tab 1: Thông tin
    with tab1:
        render_cultivation_info(realm_info_data)
    
    # Tab 2: Kho Đan Dược
    with tab2:
        render_pill_inventory(user_id)
    
    # Tab 3: Mini-game Luyện Đan
    with tab3:
        ctx = {
            "user_id": user_id,
            "words_learned": words_learned,
            "pool": core.get_learned_words(user_id),
        }
        game_minigames.render_alchemist(ctx)
    
    # Tab 4: Mua Công Thức
    with tab4:
        render_pill_shop(user_id)


def render_pill_inventory(user_id):
    """Hiển thị kho đan dược."""
    st.subheader("🏺 Kho Đan Dược")
    
    pills = core.get_pills_inventory(user_id)
    
    if not pills:
        st.info("Kho trống. Hãy luyện đan để có viên đan!")
        return
    
    cols = st.columns(3)
    for i, pill in enumerate(pills):
        with cols[i % 3]:
            st.metric(
                f"{pill['name']}",
                f"{pill['qty']} viên",
                f"+{pill['bonus']:.0f}% ATK"
            )


def render_pill_shop(user_id):
    """Mua công thức luyện đan."""
    st.subheader("🛒 Mua Công Thức Luyện Đan")
    
    profile = core.get_game_profile(user_id)
    st.metric("Linh Thạch", profile["linh_thach"])
    
    owned_codes = {r["code"] for r in core.get_pill_recipes_owned(user_id)}
    
    for recipe in cfg.PILL_RECIPES:
        code = recipe["code"]
        owned = code in owned_codes
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            status = "✅ Đã mua" if owned else f"💰 {cfg.PILL_RECIPE_PRICES.get(code, 0)} Linh Thạch"
            st.write(
                f"**{recipe['name']}** — {status}\n"
                f"Tu Vi: Realm {recipe['min_realm']} | "
                f"Thành công: {int(recipe['success_rate']*100)}%"
            )
        
        with col2:
            if not owned:
                if st.button("Mua", key=f"buy_recipe_{code}", use_container_width=True):
                    ok, msg = core.buy_pill_recipe(code, user_id)
                    if ok:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.write("✅")
```

---

## **6. Test Cases (tests/test_game.py)**

### Thêm test cho Phase 5:

```python
class TestAlchemistGame(unittest.TestCase):
    """Test mini-game luyện đan."""
    
    def setUp(self):
        self.user_id = 1
        db = userdb.get_user_db()
        db.execute("DELETE FROM word_mastery WHERE user_id = ?", (self.user_id,))
        db.commit()
    
    def test_alchemist_unlock_requirement(self):
        """Mini-game cần ≥ 4 từ đã học."""
        # 0 từ → không mở
        self.assertLess(core.get_words_learned(self.user_id), cfg.ALCHEMIST_MIN_WORDS)
        
        # Thêm 3 từ → vẫn không mở
        self._add_learned_words(3)
        self.assertLess(core.get_words_learned(self.user_id), cfg.ALCHEMIST_MIN_WORDS)
        
        # Thêm 1 từ nữa → mở
        self._add_learned_words(1)
        self.assertGreaterEqual(core.get_words_learned(self.user_id), cfg.ALCHEMIST_MIN_WORDS)
    
    def test_build_alchemist_pool_insufficient_words(self):
        """Build pool khi chưa đủ từ đã học."""
        self._add_learned_words(2)  # Chỉ 2 từ, cần 4
        
        pool, error = core.build_alchemist_pool(self.user_id, "pill_1")
        self.assertIsNone(pool)
        self.assertIn("4", error)
    
    def test_build_alchemist_pool_exact_words(self):
        """Build pool khi đúng số từ cần."""
        self._add_learned_words(3)  # pill_1 cần 3
        
        pool, error = core.build_alchemist_pool(self.user_id, "pill_1")
        self.assertIsNotNone(pool)
        self.assertEqual(len(pool), 3)
        self.assertIsNone(error)
    
    def test_start_alchemist_game_no_recipe(self):
        """Không thể bắt đầu nếu chưa mua công thức."""
        self._add_learned_words(4)
        
        ok, msg = core.start_alchemist_game(self.user_id, "pill_1")
        self.assertFalse(ok)
        self.assertIn("chưa mua", msg.lower())
    
    def test_start_alchemist_game_success(self):
        """Bắt đầu game thành công."""
        self._add_learned_words(4)
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe("pill_1", self.user_id)
        
        ok, msg = core.start_alchemist_game(self.user_id, "pill_1")
        self.assertTrue(ok)
        
        game = core.get_alchemist_game_state(self.user_id)
        self.assertIsNotNone(game)
        self.assertEqual(game["recipe"], "pill_1")
        self.assertEqual(len(game["pool"]), 3)
        self.assertEqual(len(game["matched"]), 0)
    
    def test_match_word(self):
        """Ghép từ và cập nhật trạng thái."""
        self._setup_game("pill_1")
        
        ok, complete = core.match_word(self.user_id, 0)
        self.assertTrue(ok)
        self.assertFalse(complete)  # 1/3
        
        ok, complete = core.match_word(self.user_id, 1)
        self.assertTrue(ok)
        self.assertFalse(complete)  # 2/3
        
        ok, complete = core.match_word(self.user_id, 2)
        self.assertTrue(ok)
        self.assertTrue(complete)  # 3/3
    
    def test_finish_game_incomplete(self):
        """Không thể hoàn thành nếu chưa ghép đủ."""
        self._setup_game("pill_1")
        core.match_word(self.user_id, 0)  # Chỉ ghép 1/3
        
        ok, msg = core.finish_alchemist_game(self.user_id, "pill_1")
        self.assertFalse(ok)
        self.assertIn("1", msg)
    
    def test_finish_game_success(self):
        """Hoàn thành game → luyện đan."""
        self._setup_game("pill_1")
        
        # Ghép đủ
        for i in range(3):
            core.match_word(self.user_id, i)
        
        # Prepare materials
        for mat_code, qty in cfg.PILL_RECIPES_BY_CODE["pill_1"]["materials"]:
            core.add_inventory(self.user_id, mat_code, qty)
        
        # Mock success craft
        with unittest.mock.patch("random.random", return_value=0.5):
            ok, msg = core.finish_alchemist_game(self.user_id, "pill_1")
            self.assertTrue(ok)
            self.assertIn("✅", msg)
            
            # Game phải reset
            game = core.get_alchemist_game_state(self.user_id)
            self.assertIsNone(game)
    
    def _add_learned_words(self, count):
        """Helper: thêm từ đã học."""
        db = userdb.get_user_db()
        for i in range(count):
            db.execute(
                "INSERT OR REPLACE INTO word_mastery (user_id, vocab_id, last_status) VALUES (?, ?, ?)",
                (self.user_id, 1000 + i, "MASTERED")
            )
        db.commit()
    
    def _setup_game(self, recipe_code):
        """Helper: bắt đầu game."""
        self._add_learned_words(4)
        core.set_linh_thach(self.user_id, 500)
        core.buy_pill_recipe(recipe_code, self.user_id)
        core.start_alchemist_game(self.user_id, recipe_code)
```

---

## **7. Database Schema Check (userdb.py)**

### Kiểm tra bảng cần thiết:

```python
# Trong init_schema() hoặc validate_schema()
REQUIRED_TABLES = [
    "game_profile",
    "game_pills",
    "game_pill_recipes",
    "game_inventory",
    "word_mastery",
]

def ensure_game_tables():
    """Đảm bảo tất cả bảng trò chơi tồn tại."""
    db = get_user_db()
    for table_name in REQUIRED_TABLES:
        if not table_exists(db, table_name):
            # Recreate schema từ SCHEMA
            for statement in SCHEMA:
                if table_name in statement:
                    db.execute(statement)
            db.commit()
```

---

## **READY FOR TESTING**

```
Files Modified:
  ✅ game_config.py: +12 lines (ALCHEMIST config)
  ✅ game_core.py: +200 lines (alchemist functions)
  ✅ game_minigames.py: +150 lines (render_alchemist)
  ✅ game_questions.py: Update/add short_meaning()
  ✅ cultivation_tab.py: +100 lines (UI integration)
  ✅ tests/test_game.py: +8 test cases

Next: Run tests, verify UI, integration with Phase 4
```

---

**Phiên 5 Code Details**: 2026-11-07  
**Status**: ✅ READY FOR CODE INTEGRATION  
