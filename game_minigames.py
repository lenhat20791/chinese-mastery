"""Ba trò chơi ôn tập theo lượt: Quẻ Bói, Ghép Bài, Sắp Xếp Câu."""
import random
from pathlib import Path

import streamlit as st

import game_config as cfg
import game_core as core
import game_questions as gq
import game_ui
from course_config import get_config
from database import active_variant, get_vocab_by_ids, record_review_batch


def _toast_new(badges):
    for name in badges:
        st.toast(f"🏅 Danh hiệu mới: {name}")


def _remaining_plays_note(state):
    return "Nhận 100% Linh Thạch cho mỗi ván chơi."


# ---------------------------------------------------------------------------
# Quẻ bói
# ---------------------------------------------------------------------------

def _fortune_answer(ok, word_id, ctx):
    state = core.resolve_fortune(ok, ctx["idx"])
    record_review_batch([(word_id, ok)])
    _toast_new(core.check_achievements(ctx["words"]))
    return state


def render_fortune(ctx):
    state = core.get_state()
    pool = ctx["pool"]
    if state["fortune"] is None:
        word, tier = core.draw_fortune(pool, ctx["mastery"], gq.pick_words)
        state = core.start_fortune(word["id"], tier)
    fortune = state["fortune"]
    word = next((w for w in pool if w["id"] == fortune["vocab_id"]), None) or get_vocab_by_ids([fortune["vocab_id"]])[0]

    st.markdown(f"### 🔮 Quẻ Bói Hằng Ngày — **{fortune['tier']}**")
    st.caption(f"Chuỗi ngày bói quẻ liên tiếp: {state['streak']} 🔥")
    if fortune["status"] == "pending":
        st.info(cfg.FORTUNE_TEXT[fortune["tier"]])
        st.markdown(f"<div class='quiz-prompt' style='text-align:center;font-size:56px'>{word['hanzi']}</div>"
                    f"<div style='text-align:center'>{word.get('pinyin') or ''}</div>", unsafe_allow_html=True)
        game_ui.speak(word["hanzi"])
        st.write("Đoán đúng nghĩa của chữ này để nhận phúc duyên hôm nay:")
        rng = random.Random(f"{state['uid']}:{state['day']}:options")
        options = gq.meaning_options(word, pool, rng=rng)
        for i, option in enumerate(options):
            st.button(option["label"], key=f"fortune_opt_{i}", use_container_width=True,
                      on_click=_fortune_answer, args=(option["ok"], word["id"], ctx))
        return
    if fortune["status"] == "ok":
        buff = core.parse_buff(fortune["buff"])
        name, desc, _, _ = cfg.FORTUNE_BUFFS[buff[0]]
        st.success(f"✅ Ngộ ra chữ **{word['hanzi']}** — {gq.short_meaning(word)}")
        st.markdown(f"**Phúc duyên hôm nay:** {name} — {desc.format(v=buff[1])}")
    else:
        st.error(cfg.FORTUNE_TEXT["Hung"])
        st.markdown(f"Chữ **{word['hanzi']}** ({word.get('pinyin') or ''}) nghĩa là: {gq.short_meaning(word)}. "
                    "Chữ này đã được đưa vào Tâm Ma Bảng để ôn lại.")
    st.caption("Quẻ mới sẽ xuất hiện vào ngày mai.")


# ---------------------------------------------------------------------------
# Ghép bài
# ---------------------------------------------------------------------------

MATCH_MODES = {
    "hm": "Hán ↔ nghĩa", "hp": "Hán ↔ pinyin", "ah": "Nghe ↔ Hán", "am": "Nghe ↔ nghĩa",
}


AUDIO_MODES = ("ah", "am")


def _right_face(word, mode):
    if mode in ("hm", "am"):
        return gq.short_meaning(word, 40)
    if mode == "hp":
        return word.get("pinyin") or ""
    return word["hanzi"]


def build_match_modes(words, rng=random):
    """Gán thể thức cho từng cặp: tối đa n//2 cặp dạng nghe; mặt cột phải không trùng nhau."""
    n = len(words)
    audio_slots = set(rng.sample(range(n), rng.randint(1, n // 2))) if n >= 2 else set()
    modes, used = {}, set()
    for i, word in enumerate(words):
        if not get_config()["has_pinyin"]:
            options = ["am"] if i in audio_slots else ["hm"]
        else:
            options = ["ah"] if i in audio_slots else ["hm", "hp"]
        rng.shuffle(options)
        options.append("hm")
        for mode in options:
            face = _right_face(word, mode)
            if face and face not in used:
                used.add(face)
                modes[word["id"]] = mode
                break
        else:
            return None
    return modes


def start_match(ctx):
    pool = ctx["pool"]
    candidates = list(gq.pick_words(pool, ctx["mastery"], min(len(pool), cfg.MATCH_MAX_PAIRS * 3)))
    words, modes = [], None
    for _ in range(10):
        words = candidates[:cfg.MATCH_MAX_PAIRS]
        modes = build_match_modes(words)
        if modes:
            break
        random.shuffle(candidates)
    if not modes:
        words = candidates[:cfg.MATCH_MAX_PAIRS]
        modes = {w["id"]: "hm" for w in words}
    left = [w["id"] for w in words]
    right = left[:]
    random.shuffle(left)
    random.shuffle(right)
    audio_no = {wid: n for n, wid in enumerate([i for i in left if modes[i] in AUDIO_MODES], 1)}
    st.session_state.g_match = {
        "words": {w["id"]: w for w in words}, "modes": modes, "audio_no": audio_no,
        "left": left, "right": right,
        "status": {f"L{i}": "idle" for i in left} | {f"R{i}": "idle" for i in right},
        "sel": {"L": None, "R": None}, "correct": 0, "wrong": 0, "results": [], "done": None,
    }


def _match_remaining(m):
    active = ("idle", "sel")
    return [i for i in m["words"] if m["status"][f"L{i}"] in active and m["status"][f"R{i}"] in active]


def _match_click(side, wid, ctx):
    m = st.session_state.g_match
    key = f"{side}{wid}"
    if m["done"] or m["status"][key] not in ("idle", "sel"):
        return
    if m["status"][key] == "sel":
        m["status"][key] = "idle"
        m["sel"][side] = None
        return
    previous = m["sel"][side]
    if previous is not None:
        m["status"][f"{side}{previous}"] = "idle"
    m["sel"][side] = wid
    m["status"][key] = "sel"
    left, right = m["sel"]["L"], m["sel"]["R"]
    if left is not None and right is not None:
        if left == right:
            m["status"][f"L{left}"] = m["status"][f"R{right}"] = "done"
            m["correct"] += 1
            m["results"].append((left, True))
        else:
            m["status"][f"L{left}"] = m["status"][f"R{right}"] = "bad"
            m["wrong"] += 1
            m["results"].append((left, False))
        m["sel"] = {"L": None, "R": None}
    if not _match_remaining(m):
        _match_finish(m, ctx)


def _match_finish(m, ctx):
    n = len(m["words"])
    perfect = m["correct"] == n and m["wrong"] == 0
    base = m["correct"] * cfg.MATCH_PAIR_REWARD + (cfg.MATCH_PERFECT_BONUS if perfect else 0)
    incr = {"matches_played": 1, "answers_correct": m["correct"], "perfect_matches": 1 if perfect else 0}
    ls, mult, badges = core.settle(
        base, core.scale(ctx["idx"]), ctx["words"], results=m["results"], incr=incr,
        log=("match", f"Lật bài: đúng {m['correct']}/{n} cặp" + (" (hoàn hảo)" if perfect else "") + "."))
    m["done"] = {"ls": ls, "mult": mult, "perfect": perfect}
    _toast_new(badges)


def render_match(ctx):
    state = core.get_state()
    st.markdown("### 🃏 Lật Bài Linh Thạch")
    if get_config()["has_pinyin"]:
        modes_note = "Hán ↔ nghĩa, Hán ↔ pinyin, 🔊 nghe ↔ Hán/nghĩa"
    else:
        modes_note = "từ tiếng Anh ↔ nghĩa tiếng Việt, 🔊 phát âm ↔ nghĩa tiếng Việt"
    st.caption(f"Mỗi ván 6 cặp, trộn nhiều thể thức: {modes_note}. "
               "Bấm nút 🔊 để nghe, rồi chọn mặt khớp ở cột phải. Ghép sai sẽ khóa cả hai nút. "
               + _remaining_plays_note(state))
    m = st.session_state.get("g_match")
    if m is None:
        st.button("▶️ Bắt đầu ván mới", key="match_start", type="primary", on_click=start_match, args=(ctx,))
        return
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
        word = m["words"][i]
        mode = m["modes"][i]
        label = f"🔊 {m['audio_no'][i]}" if mode in AUDIO_MODES else word["hanzi"]
        col_left.button(label, key=f"ml_{i}", use_container_width=True, on_click=_match_click,
                        args=("L", i, ctx), disabled=locked or m["status"][f"L{i}"] in ("done", "bad"))
    for i in m["right"]:
        col_right.button(_right_face(m["words"][i], m["modes"][i]), key=f"mr_{i}", use_container_width=True,
                         on_click=_match_click, args=("R", i, ctx),
                         disabled=locked or m["status"][f"R{i}"] in ("done", "bad"))
    audio = {f"ml_{i}": m["words"][i]["hanzi"] for i in m["left"] if m["modes"][i] in AUDIO_MODES}
    if audio:
        game_ui.audio_listener(audio)
    if locked:
        d = m["done"]
        (st.success if d["perfect"] else st.info)(
            f"Kết thúc: đúng {m['correct']}/{len(m['words'])} cặp · +{d['ls']} 💎 Linh Thạch"
            + (" · Hoàn hảo!" if d["perfect"] else "") + (f" (hệ số {int(d['mult'] * 100)}%)" if d["mult"] < 1 else ""))
        st.button("🔁 Chơi ván khác", key="match_again", type="primary", on_click=start_match, args=(ctx,))


# ---------------------------------------------------------------------------
# Luyện Đan
# ---------------------------------------------------------------------------

def render_alchemy(ctx):
    import game_alchemy
    game_alchemy.render(ctx)


# ---------------------------------------------------------------------------
# Vẽ Phù
# ---------------------------------------------------------------------------

def render_talisman(ctx):
    """Phiên 6: Vẽ Phù - chấm Hán tự để vẽ phù."""
    user_id = core.current_user_id()
    state = core.get_state()
    idx = ctx["idx"]
    pool = ctx["pool"]
    
    st.markdown("### 🪬 Vẽ Phù")
    st.caption("Gõ lại từ đã học theo thứ tự ngẫu nhiên. Đủ số lần gõ đúng sẽ luôn vẽ thành công.")
    
    # Hiển thị ảnh minh họa
    phu_luc_path = Path(__file__).parent / "assets" / "hinh tu luyen" / "phu_luc.png"
    if phu_luc_path.exists():
        col1, col2 = st.columns([2, 1])
        with col2:
            st.image(str(phu_luc_path), use_container_width=True, caption="Bàn Vẽ Phù")
    
    tab_recipes, tab_craft, tab_inventory = st.tabs(["📜 Công Thức", "🪬 Vẽ Phù", "🧿 Kho Phù"])
    
    with tab_recipes:
        st.markdown("#### Công Thức Phù Lục")
        owned_recipes = {r["code"] for r in core.get_talisman_recipes_owned(user_id)}
        
        for i, recipe in enumerate(cfg.TALISMAN_RECIPES):
            c1, c2, c3 = st.columns([1, 4, 1])
            with c1:
                st.markdown(f"<div style='font-size:32px; text-align:center;'>🪬</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(f"**{recipe['name']}** · {cfg.MAJOR_REALMS[recipe['min_realm']]} trở lên  \n"
                           f"{recipe['description']}  \n"
                           f"_Cần {recipe['correct_hits_needed']} lần gõ đúng_")
            with c3:
                if recipe["code"] in owned_recipes:
                    st.success("✅ Sở hữu")
                else:
                    price = cfg.TALISMAN_RECIPE_PRICES[recipe["code"]]
                    if st.button(f"Mua ({price} 💎)", key=f"buy_talisman_{recipe['code']}", use_container_width=True):
                        ok, msg, ls_after = core.buy_talisman_recipe(user_id, recipe["code"])
                        if ok:
                            core.get_state(force=True)
                            st.toast(f"✅ Mua thành công: {recipe['name']}")
                            st.rerun()
                        else:
                            st.toast(f"❌ {msg}", icon="⚠️")
    
    with tab_craft:
        st.markdown("#### Vẽ Phù")
        owned = core.get_talisman_recipes_owned(user_id)
        if not owned:
            st.info("Hãy mua công thức trước khi vẽ phù.")
        else:
            selected = st.selectbox("Chọn công thức",
                                   [recipe["code"] for recipe in owned],
                                   format_func=lambda code: cfg.TALISMAN_RECIPES_BY_CODE[code]["name"],
                                   key="talisman_recipe_select")
            if selected:
                recipe_code = selected
                recipe = cfg.TALISMAN_RECIPES_BY_CODE[recipe_code]
                
                st.markdown(f"**{recipe['name']}** — {recipe['description']}")
                st.info(f"Gõ đúng {recipe['correct_hits_needed']} Hán tự để vẽ thành công.")
                
                can_draw = idx >= recipe["min_realm"]
                if not can_draw:
                    st.warning(f"Cần đạt {cfg.MAJOR_REALMS[recipe['min_realm']]} để vẽ phù này.")
                hits_key = f"talisman_hits_{user_id}_{active_variant()}_{recipe_code}"
                hits = st.session_state.get(hits_key, 0)
                current_word = core.talisman_word(user_id, active_variant(), pool) if pool else None
                
                if current_word:
                    st.markdown(f"<div style='text-align:center; font-size:64px; padding:20px;'>{current_word['hanzi']}</div>",
                               unsafe_allow_html=True)
                    game_ui.speak(current_word["hanzi"])
                    
                    with st.form(f"talisman_form_{recipe_code}", clear_on_submit=True):
                        user_input = st.text_input("Gõ Hán tự:", placeholder="Nhập chữ Hán...")
                        submitted = st.form_submit_button("Xác nhận", disabled=not can_draw)
                    if submitted:
                        if gq.check_hanzi_match(user_input, current_word["hanzi"]):
                            core.talisman_word(user_id, active_variant(), pool, advance=True)
                            hits += 1
                            st.session_state[hits_key] = hits
                            st.toast("✅ Đúng!")
                            if hits >= recipe["correct_hits_needed"]:
                                result = core.craft_talisman(user_id, recipe_code, ctx["words"])
                                st.session_state[hits_key] = 0
                                st.toast(result["message"], icon="🎉" if result["success"] else "⚠️")
                            st.rerun()
                        else:
                            st.error(f"❌ Sai! Đáp án: {current_word['hanzi']}")
                    st.progress(hits / recipe["correct_hits_needed"],
                                text=f"Tiến độ: {hits}/{recipe['correct_hits_needed']}")
                else:
                    st.info("Chưa có từ đã học để vẽ phù.")
    
    with tab_inventory:
        st.markdown("#### Kho Phù Bảo Hộ")
        inventory = core.get_talismans_inventory(user_id)
        if not inventory:
            st.info("Kho phù trống. Hãy vẽ phù để tích lũy.")
        else:
            cols_per_row = 5
            for i in range(0, len(inventory), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx_item = i + j
                    if idx_item < len(inventory):
                        talisman = inventory[idx_item]
                        with cols[j]:
                            recipe = cfg.TALISMAN_RECIPES_BY_CODE[talisman["code"]]
                            st.markdown(f"""
                            <div style="border: 2px solid #a574d4; border-radius: 8px; padding: 8px; text-align: center; background: rgba(27,20,36,0.7); height: 100px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative;">
                                <div style="font-size: 32px;">🪬</div>
                                <div style="font-size: 9px; margin-top: 4px;">{recipe['name']}</div>
                                <div style="position: absolute; bottom: 3px; right: 5px; background: #a574d4; color: #fff; font-weight: 700; font-size: 0.7rem; padding: 2px 4px; border-radius: 3px;">×{talisman['qty']}</div>
                            </div>
                            """, unsafe_allow_html=True)
# ---------------------------------------------------------------------------
# Sắp xếp câu / điền chữ
# ---------------------------------------------------------------------------
