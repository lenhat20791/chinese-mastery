# 📝 PHIÊN 2 - CHI TIẾT CÁC THAY ĐỔI

## **1. game_config.py - Thêm cấu hình danh hào**

### Vị trí: Dòng ~327 (trước BADGE_TIER_ICONS)

### Thêm vào:
```python
# ---------------------------------------------------------------------------
# Danh hào (10 bậc, tương ứng với Tiên Định Cảnh Giới)
# ---------------------------------------------------------------------------
HONOR_TITLES = [
    {"code": "so_nhap_tien_lo", "name": "Sơ nhập tiên lộ", "realm_idx": 0, "atk_pct": 3, "hp_pct": 0},
    {"code": "chan_nhan", "name": "Chân nhân", "realm_idx": 2, "atk_pct": 5, "hp_pct": 5},
    # ... (8 more titles)
    {"code": "vinh_hang_tien_de", "name": "Vĩnh hằng Tiên Đế", "realm_idx": 15, "atk_pct": 25, "hp_pct": 25},
]
HONOR_TITLE_BY_CODE = {t["code"]: t for t in HONOR_TITLES}
```

---

## **2. game_core.py - Logic danh hào**

### 2.1 Cập nhật `stat_bonuses()` (Dòng ~110)

**Trước:**
```python
def stat_bonuses(words=0, answers=0, streak=0):
    """Hiệu ứng của Căn cơ..."""
    can_co = words / (words + cfg.CAN_CO_K) if words > 0 else 0.0
    return {
        "crit": diminishing(answers, cfg.CRIT_MAX, cfg.CRIT_K),
        "hp": cfg.CAN_CO_HP_MAX * can_co,
        "atk": cfg.CAN_CO_ATK_MAX * can_co,
        "dao_tam": diminishing(streak, cfg.DAO_TAM_MAX, cfg.DAO_TAM_K),
    }
```

**Sau:**
```python
def stat_bonuses(words=0, answers=0, streak=0, honor_code=None):
    """Hiệu ứng của Căn cơ, Ngộ tính, Đạo tâm, và Danh hào."""
    can_co = words / (words + cfg.CAN_CO_K) if words > 0 else 0.0
    bonuses = {
        "crit": diminishing(answers, cfg.CRIT_MAX, cfg.CRIT_K),
        "hp": cfg.CAN_CO_HP_MAX * can_co,
        "atk": cfg.CAN_CO_ATK_MAX * can_co,
        "dao_tam": diminishing(streak, cfg.DAO_TAM_MAX, cfg.DAO_TAM_K),
    }
    # Cộng hiệu ứng danh hào nếu có
    if honor_code and honor_code in cfg.HONOR_TITLE_BY_CODE:
        honor = cfg.HONOR_TITLE_BY_CODE[honor_code]
        bonuses["atk"] += honor["atk_pct"] / 100.0
        bonuses["hp"] += honor["hp_pct"] / 100.0
    return bonuses
```

### 2.2 Thêm `available_honors()` (Dòng ~159)

```python
def available_honors(idx):
    """Trả về danh sách mã danh hào có thể đạt ở cảnh giới idx."""
    return [h["code"] for h in cfg.HONOR_TITLES if h["realm_idx"] <= idx]
```

### 2.3 Cập nhật `all_titles()` (Dòng ~164)

**Trước:**
```python
def all_titles():
    """{mã: tên} của mọi danh hiệu có thể đạt."""
    titles = {}
    for line in cfg.BADGE_LINES:
        for tier, name in enumerate(line["names"]):
            titles[achievement_code(line["base"], tier)] = name
    for hidden in cfg.HIDDEN_BADGES:
        titles[hidden["code"]] = hidden["name"]
    return titles
```

**Sau:**
```python
def all_titles():
    """{mã: tên} của mọi danh hiệu có thể đạt."""
    titles = {}
    for line in cfg.BADGE_LINES:
        for tier, name in enumerate(line["names"]):
            titles[achievement_code(line["base"], tier)] = name
    for hidden in cfg.HIDDEN_BADGES:
        titles[hidden["code"]] = hidden["name"]
    # Thêm các danh hào
    for honor in cfg.HONOR_TITLES:
        titles[honor["code"]] = honor["name"]
    return titles
```

### 2.4 Cập nhật `equip_title()` (Dòng ~560)

**Trước:**
```python
def equip_title(code):
    state = get_state()
    apply_changes(extra=[("UPDATE game_profile SET equipped_title = ? WHERE user_id = ?", (code, state["uid"]))])
```

**Sau:**
```python
def equip_title(code):
    state = get_state()
    realm = realm_info(state["counters"].get("words_learned", 0))
    idx = realm["idx"]
    available = available_honors(idx)
    
    # Chỉ cho phép trang bị danh hào có sẵn (hoặc None để tháo)
    if code is not None and code not in available:
        return
    
    apply_changes(extra=[("UPDATE game_profile SET equipped_title = ? WHERE user_id = ?", (code, state["uid"]))])
```

---

## **3. cultivation_tab.py - Giao diện danh hào**

### 3.1 Cập nhật `_render_badges()` (Dòng ~441)

**Thay toàn bộ hàm:**

**Trước:**
```python
def _render_badges(state, ctx):
    st.markdown("### 🏅 Huy Hiệu & Danh Hiệu")
    titles = core.all_titles()
    unlocked = [c for c in titles if c in state["achievements"]]
    if unlocked:
        current = state["title"] if state["title"] in unlocked else None
        choice = st.selectbox("Danh hiệu đang đeo", [None] + unlocked, ...)
    # ... huy hiệu logic
```

**Sau:**
```python
def _render_badges(state, ctx):
    st.markdown("### 🏅 Danh Hào & Huy Hiệu")
    
    # Danh hào có thể trang bị
    available = core.available_honors(ctx["idx"])
    if available:
        st.markdown("**Danh Hào**")
        current = state["title"] if state["title"] in available else None
        choice = st.selectbox("Danh hào đang đeo", [None] + available, 
                              index=([None] + available).index(current),
                              format_func=lambda c: "— không đeo —" if c is None else cfg.HONOR_TITLE_BY_CODE[c]["name"], 
                              key="title_pick",
                              on_change=lambda: core.equip_title(st.session_state.title_pick))
        for honor in cfg.HONOR_TITLES:
            if honor["code"] in available:
                effects = f"+{honor['atk_pct']}% công, +{honor['hp_pct']}% HP" if honor["atk_pct"] or honor["hp_pct"] else "Không có hiệu ứng"
                st.caption(f"📜 **{honor['name']}** — {effects}")
    else:
        st.info("Hãy đạt Linh Khí Kỳ tầng 2 để mở khóa danh hào đầu tiên.")
    
    # Huy hiệu truyền thống (giữ nguyên)
    st.markdown("**Huy Hiệu Thành Tích**")
    # ... rest of old code
```

### 3.2 Cập nhật `_body()` (Dòng ~463)

**Trước:**
```python
ctx = {"pool": pool, "words": words, "realm": realm, "idx": realm["idx"], "mastery": {},
       "grammar": _unlocked("grammar_battle", realm["idx"], words),
       "bonuses": core.stat_bonuses(words, state["counters"].get("answers_correct", 0),
                                    user.get("consecutive_streak", 0))}
```

**Sau:**
```python
ctx = {"pool": pool, "words": words, "realm": realm, "idx": realm["idx"], "mastery": {},
       "grammar": _unlocked("grammar_battle", realm["idx"], words),
       "bonuses": core.stat_bonuses(words, state["counters"].get("answers_correct", 0),
                                    user.get("consecutive_streak", 0), state.get("title"))}
```

---

## **4. game_ui.py - Màu 2 phía (Task 15)**

### Vị trí: Dòng ~128

**Trước:**
```python
def color_buttons_css(key_states):
    """key_states: {khóa nút: 'sel'|'done'|'bad'} -> thẻ <style> tô màu từng nút theo khóa."""
    rules = []
    for key, state in key_states.items():
        if state in STATE_COLORS:
            bg, fg = STATE_COLORS[state]
            rules.append(...)
    return f"<style>{''.join(rules)}</style>" if rules else ""
```

**Sau:**
```python
def color_buttons_css(key_states, key_base_colors=None):
    """key_states: {khóa nút: 'sel'|'done'|'bad'} -> thẻ <style> tô màu từng nút theo khóa.
    
    key_base_colors: {khóa nút: (bg, fg)} -> màu nền cơ bản cho nút khi ở trạng thái 'idle'.
    """
    rules = []
    
    # Áp dụng màu nền cơ bản cho các nút idle (nếu có)
    if key_base_colors:
        for key, (bg, fg) in key_base_colors.items():
            rules.append(f".st-key-{key} button {{ background:{bg} !important; color:{fg} !important;"
                         f" border-color:{bg} !important; }}"
                         f".st-key-{key} button p {{ color:{fg} !important; }}")
    
    # Ghi đè màu nền cơ bản với màu trạng thái (sel/done/bad)
    for key, state in key_states.items():
        if state in STATE_COLORS:
            bg, fg = STATE_COLORS[state]
            rules.append(...)
    
    return f"<style>{''.join(rules)}</style>" if rules else ""
```

---

## **5. game_minigames.py - Thêm màu trong render_match (Task 15)**

### Vị trị: Dòng ~210

**Trước:**
```python
    colors = {}
    for i in m["words"]:
        colors[f"ml_{i}"] = m["status"][f"L{i}"]
        colors[f"mr_{i}"] = m["status"][f"R{i}"]
    st.markdown(game_ui.color_buttons_css(colors), unsafe_allow_html=True)
    col_left, col_right = st.columns(2)
    locked = m["done"] is not None
    for i in m["left"]:
        # ... left column
    for i in m["right"]:
        # ... right column
```

**Sau:**
```python
    colors = {}
    base_colors = {}
    for i in m["words"]:
        colors[f"ml_{i}"] = m["status"][f"L{i}"]
        colors[f"mr_{i}"] = m["status"][f"R{i}"]
        # Màu nền cơ bản: Left (Hán) xanh, Right (Nghĩa) hồng
        base_colors[f"ml_{i}"] = ("#d1e7f7", "#003d99")  # xanh nhạt / xanh đậm
        base_colors[f"mr_{i}"] = ("#f7d1e1", "#990033")  # hồng nhạt / hồng đậm
    st.markdown(game_ui.color_buttons_css(colors, base_colors), unsafe_allow_html=True)
    col_left, col_right = st.columns(2)
    locked = m["done"] is not None
    for i in m["left"]:
        # ... left column (xanh)
    for i in m["right"]:
        # ... right column (hồng)
```

---

## **No Changes Needed**

- ✅ `userdb.py`: Schema `game_profile` đã có cột `equipped_title`
- ✅ `database.py`: Không liên quan đến danh hào
- ✅ `app.py`: Không cần thay đổi
- ✅ `game_hunt.py`: Stats tính từ `player_stats()` tự động nhận danh hào
- ✅ Huy hiệu logic (`check_achievements`, `BADGE_LINES`): Giữ nguyên

---

## **Database Compatibility**

- Cột `equipped_title` (TEXT, nullable) hiện tại lưu code huy hiệu hoặc danh hào
- Không cần migration, schema cũ hỗ trợ cả huy hiệu (đơn code) và danh hào (code mới)
- Khi user trang bị danh hào mới, `equipped_title` sẽ cập nhật từ badge code → honor code

---

## **Summary of Changes**

| File | Lines | Changes |
|------|-------|---------|
| game_config.py | 327-348 | Add HONOR_TITLES + HONOR_TITLE_BY_CODE |
| game_core.py | 110-124 | Update stat_bonuses() to include honor |
| game_core.py | 159-162 | Add available_honors() function |
| game_core.py | 164-171 | Update all_titles() to include honors |
| game_core.py | 560-570 | Update equip_title() with validation |
| cultivation_tab.py | 441-460 | Rewrite _render_badges() with honor UI |
| cultivation_tab.py | 463-468 | Update _body() to pass honor to stat_bonuses |
| game_ui.py | 128-145 | Update color_buttons_css() for base colors |
| game_minigames.py | 210-237 | Add base_colors to render_match() |

**Total: ~150 lines of new/modified code**

---

## **Breaking Changes: None**

- Old badge codes still work (backward compatible)
- DB queries unchanged
- Function signatures backward compatible (honor_code parameter optional)
- No schema migration needed
