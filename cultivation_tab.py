"""Tab Động Phủ: trang chủ tu tiên, các trò chơi ôn tập, phường thị và huy hiệu."""
import base64
import time

import streamlit as st

import game_config as cfg
import game_core as core
import game_hunt
import game_minigames
import game_questions as gq
import game_ui
from database import _demon_rows

NAV = {
    "home": "🏯 Động Phủ", "fortune": "🔮 Quẻ Bói", "match": "🃏 Lật Bài", "sentence": "📜 Đối Câu",
    "hunt": "🗺️ Săn Yêu Thú", "market": "🏪 Phường Thị", "badges": "🏅 Huy Hiệu",
}
UNLOCK_KEY = {"fortune": "fortune", "match": "match", "sentence": "sentence", "hunt": "hunt"}


def avatar_svg(idx):
    """Hình tu sĩ ngồi thiền, hào quang thêm vòng theo đại cảnh giới."""
    hue = (idx * 22 + 30) % 360
    rings = "".join(
        f'<circle cx="100" cy="100" r="{30 + i * 5.5:.1f}" fill="none" stroke="hsl({(hue + i * 9) % 360},80%,60%)" '
        f'stroke-width="2" opacity="{max(0.25, 1 - i * 0.045):.2f}"/>' for i in range(idx + 1))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">'
            f'<rect width="200" height="200" rx="16" fill="#1f1a2e"/>{rings}'
            f'<circle cx="100" cy="78" r="14" fill="#f2d4a8"/>'
            f'<path d="M70,140 Q100,95 130,140 Z" fill="hsl({hue},60%,45%)"/>'
            f'<path d="M62,142 Q100,156 138,142 L132,150 Q100,164 68,150 Z" fill="hsl({hue},50%,35%)"/></svg>')


def _show_avatar(idx):
    encoded = base64.b64encode(avatar_svg(idx).encode()).decode()
    st.markdown(f'<img src="data:image/svg+xml;base64,{encoded}" style="width:100%;max-width:200px;border-radius:16px"/>',
                unsafe_allow_html=True)


def _mastery():
    cached = st.session_state.get("g_mastery")
    if cached is None or time.time() - cached[0] > 60:
        cached = (time.time(), gq.load_mastery())
        st.session_state.g_mastery = cached
    return cached[1]


def _unlocked(name, idx, words):
    rule = cfg.GAME_UNLOCKS[name]
    return idx >= rule["realm_idx"] and words >= rule["words"]


def _unlock_text(name):
    rule = cfg.GAME_UNLOCKS[name]
    return f"Mở khóa khi đạt {cfg.MAJOR_REALMS[rule['realm_idx']]} và đã học ≥ {rule['words']} từ."


def _render_home(state, ctx, user):
    realm = ctx["realm"]
    titles = core.all_titles()
    col_img, col_info = st.columns([1, 2])
    with col_img:
        _show_avatar(ctx["idx"])
    with col_info:
        if state["title"] in titles:
            st.markdown(f"#### 🏅 {titles[state['title']]}")
        st.markdown(f"## {realm['name']}")
        if realm["next_need"] is None:
            st.progress(1.0, text="Đã đạt cảnh giới tối cao")
        else:
            st.progress(realm["progress"], text=f"Đột phá tiểu kỳ tiếp theo: {ctx['words']} / {realm['next_need']} từ")
        art = core.equipped_artifact(state)
        if art:
            recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
            st.markdown(f"**Pháp bảo:** {cfg.QUALITY_NAMES[art['quality']]} {recipe['name']} +{art['upgrade']}")
        else:
            st.caption("Chưa trang bị pháp bảo — ghé Phường Thị để mua bí phương.")
        buff = core.active_buff(state)
        if buff:
            name, desc, _, _ = cfg.FORTUNE_BUFFS[buff[0]]
            st.caption(f"✨ {name}: {desc.format(v=buff[1])}")
    stats = core.player_stats(ctx["idx"], core.equipped_artifact(state))
    demons = len(_demon_rows())
    c = st.columns(4)
    c[0].metric("💎 Linh Thạch", f"{state['ls']:,}")
    c[1].metric("⚔️ Công kích", f"{stats['atk']:.0f}")
    c[2].metric("❤️ Sinh lực", f"{stats['hp']:.0f}")
    c[3].metric("📖 Căn cơ (từ đã học)", ctx["words"])
    c = st.columns(4)
    answers = state["counters"].get("answers_correct", 0)
    c[0].metric("🧠 Ngộ tính (đáp đúng)", answers)
    c[1].metric("🔥 Đạo tâm (chuỗi ngày)", user.get("consecutive_streak", 0))
    c[2].metric("👿 Tâm ma", demons)
    c[3].metric("⚡ Linh lực", user.get("spiritual_energy", 0))
    st.markdown("#### 📔 Nhật Ký Tu Tiên")
    if not state["log"]:
        st.caption("Chưa có ghi chép. Hãy bói quẻ, lật bài hoặc đi săn yêu thú!")
    for entry in state["log"][:15]:
        st.markdown(f"- `{str(entry['ts'])[5:16]}` {entry['text']}")


def _toast_result(result):
    ok, message = result[0], result[1]
    (st.toast if ok else st.toast)(("✅ " if ok else "⚠️ ") + message)


def _cb_buy(code, idx):
    _toast_result(core.buy_recipe(code, idx))


def _cb_pill(idx):
    _toast_result(core.buy_pill(idx))


def _cb_craft(code, idx, pill_key):
    ok, message, quality = core.craft(code, idx, use_pill=bool(st.session_state.get(pill_key)))
    _toast_result((ok, message))


def _cb_equip(artifact_id, idx):
    _toast_result(core.equip(artifact_id, idx))


def _cb_upgrade(artifact_id):
    _toast_result(core.upgrade(artifact_id))


def _items_text(mats, inventory):
    return " · ".join(
        f"{'✅' if inventory.get(c, 0) >= q else '❌'} {cfg.ITEMS[c]['emoji']} {cfg.ITEMS[c]['name']} {inventory.get(c, 0)}/{q}"
        for c, q in mats)


def _render_market(state, ctx):
    idx = ctx["idx"]
    st.markdown(f"### 🏪 Phường Thị — 💎 {state['ls']:,} Linh Thạch")
    t_recipes, t_craft, t_art, t_inv = st.tabs(["📜 Bí phương", "🔨 Chế tạo", "🗡️ Pháp bảo", "🎒 Kho đồ"])
    with t_recipes:
        for recipe in cfg.RECIPES:
            tier = cfg.ARTIFACT_TIERS[recipe["tier"]]
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                game_ui.show_image_or_emoji("artifacts", recipe["code"], tier["emoji"], 70)
            c2.markdown(f"**{recipe['name']}** · {tier['name']}  \n"
                        f"Cần {cfg.MAJOR_REALMS[recipe['min_idx']]} · nguyên liệu vùng {cfg.REGIONS[recipe['region']]['name']}")
            if recipe["code"] in state["recipes"]:
                c3.success("Đã sở hữu")
            else:
                c3.button(f"Mua {core.recipe_price(recipe):,} 💎", key=f"buy_{recipe['code']}", on_click=_cb_buy,
                          args=(recipe["code"], idx), disabled=state["ls"] < core.recipe_price(recipe))
    with t_craft:
        owned = [r for r in cfg.RECIPES if r["code"] in state["recipes"]]
        if not owned:
            st.info("Hãy mua bí phương trước.")
        else:
            code = st.selectbox("Bí phương", [r["code"] for r in owned], key="craft_recipe",
                                format_func=lambda c: f"{cfg.RECIPE_BY_CODE[c]['name']} ({cfg.ARTIFACT_TIERS[cfg.RECIPE_BY_CODE[c]['tier']]['name']})")
            recipe = cfg.RECIPE_BY_CODE[code]
            mats = core.recipe_materials(recipe)
            cost = core.recipe_craft_cost(recipe)
            st.markdown(f"**Phí chế tạo:** {cost:,} 💎 · **Yêu cầu:** {cfg.MAJOR_REALMS[recipe['min_idx']]}")
            st.markdown(_items_text(mats, state["inventory"]))
            pills = state["inventory"].get("pham_dan", 0)
            use_pill = st.checkbox(f"Dùng 💊 Tụ Phẩm Đan (có {pills}) để tăng tỉ lệ phẩm cao", key="craft_pill",
                                   disabled=pills < 1)
            odds = cfg.QUALITY_ODDS_PILL if use_pill and pills else cfg.QUALITY_ODDS
            st.caption("Tỉ lệ: " + " · ".join(f"{n} {int(o * 100)}%" for n, o in zip(cfg.QUALITY_NAMES, odds))
                       + f" · bảo hiểm: Trung Phẩm+ sau {cfg.PITY_MID_AT} lần, Thượng Phẩm sau {cfg.PITY_HIGH_AT} lần "
                       f"(đang {state['pity_mid']}/{state['pity_high']})")
            can = (idx >= recipe["min_idx"] and state["ls"] >= cost and not core.missing_materials(state, mats))
            st.button("🔨 Chế tạo", key="craft_go", type="primary", on_click=_cb_craft,
                      args=(code, idx, "craft_pill"), disabled=not can)
            if idx < recipe["min_idx"]:
                st.warning("Chưa đủ cảnh giới để chế tạo.")
        st.divider()
        st.button(f"Mua 💊 Tụ Phẩm Đan — {core.pill_price(idx):,} 💎", key="buy_pill", on_click=_cb_pill, args=(idx,),
                  disabled=state["ls"] < core.pill_price(idx))
    with t_art:
        if not state["artifacts"]:
            st.info("Chưa có pháp bảo nào.")
        for art in reversed(state["artifacts"]):
            recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
            tier = cfg.ARTIFACT_TIERS[recipe["tier"]]
            atk, hp = core.artifact_bonus(recipe, art["quality"], art["upgrade"])
            c1, c2, c3 = st.columns([1, 4, 3])
            with c1:
                game_ui.show_image_or_emoji("artifacts", recipe["code"], tier["emoji"], 70)
            equipped = art["id"] == state["equipped"]
            c2.markdown(f"**{cfg.QUALITY_NAMES[art['quality']]} {recipe['name']} +{art['upgrade']}**"
                        f"{' · ✅ đang dùng' if equipped else ''}  \n{tier['name']} · +{atk:.0f} công · +{hp:.0f} HP")
            if equipped:
                c3.button("Gỡ", key=f"unequip_{art['id']}", on_click=_cb_equip, args=(None, idx))
            else:
                c3.button("Trang bị", key=f"equip_{art['id']}", on_click=_cb_equip, args=(art["id"], idx),
                          disabled=idx < recipe["min_idx"])
            if art["upgrade"] < cfg.UPGRADE_MAX:
                ls, mats = core.upgrade_cost(recipe, art["upgrade"])
                c3.caption(f"Nâng +{art['upgrade'] + 1}: {ls:,} 💎 · {_items_text(mats, state['inventory'])} · "
                           f"{int(core.upgrade_chance(art['upgrade']) * 100)}%")
                c3.button("⬆️ Nâng cấp", key=f"upg_{art['id']}", on_click=_cb_upgrade, args=(art["id"],),
                          disabled=state["ls"] < ls or bool(core.missing_materials(state, mats)))
    with t_inv:
        if not state["inventory"]:
            st.info("Kho đồ trống. Hãy đi săn yêu thú để thu thập nguyên liệu.")
        for code, qty in sorted(state["inventory"].items()):
            item = cfg.ITEMS[code]
            rarity = cfg.RARITY_LABEL.get(item["rarity"], "Đặc biệt")
            st.markdown(f"{item['emoji']} **{item['name']}** ×{qty} · {rarity}")


def _render_badges(state, ctx):
    st.markdown("### 🏅 Huy Hiệu & Danh Hiệu")
    titles = core.all_titles()
    unlocked = [c for c in titles if c in state["achievements"]]
    if unlocked:
        current = state["title"] if state["title"] in unlocked else None
        choice = st.selectbox("Danh hiệu đang đeo", [None] + unlocked, index=([None] + unlocked).index(current),
                              format_func=lambda c: "— không đeo —" if c is None else titles[c], key="title_pick",
                              on_change=lambda: core.equip_title(st.session_state.title_pick))
    for line in cfg.BADGE_LINES:
        value = core.counter_value(state, line["counter"], ctx["words"])
        reached = sum(1 for need in line["tiers"] if value >= need)
        nxt = line["tiers"][reached] if reached < 3 else None
        icons = "".join(cfg.BADGE_TIER_ICONS[t] if achievement in state["achievements"] else "⚪"
                        for t, achievement in enumerate(core.achievement_code(line["base"], t) for t in range(3)))
        name = line["names"][reached - 1] if reached else "Chưa đạt"
        st.markdown(f"**{icons} {name}** — {value} {line['label']}" + (f" (mốc tiếp theo: {nxt})" if nxt else " ✔ tối đa"))
        if nxt:
            st.progress(min(1.0, value / nxt))
    st.markdown("**Huy hiệu ẩn**")
    for hidden in cfg.HIDDEN_BADGES:
        if hidden["code"] in state["achievements"]:
            st.markdown(f"🌟 **{hidden['name']}** — {hidden['desc']}")
        else:
            st.markdown("🔒 ??? — bí ẩn")


@st.fragment
def _body(user, learned_day):
    state = core.get_state()
    pool = gq.load_pool(learned_day)
    words = len(pool)
    realm = core.realm_info(words)
    ctx = {"pool": pool, "words": words, "realm": realm, "idx": realm["idx"], "mastery": {},
           "grammar": _unlocked("grammar_battle", realm["idx"], words)}
    page = st.radio("Điều hướng", list(NAV), format_func=lambda k: NAV[k], horizontal=True, key="game_nav",
                    label_visibility="collapsed")
    if page in UNLOCK_KEY and not _unlocked(UNLOCK_KEY[page], realm["idx"], words):
        st.info(f"🔒 {_unlock_text(UNLOCK_KEY[page])} Hiện có {words} từ.")
        return
    if page in ("fortune", "match", "sentence", "hunt"):
        ctx["mastery"] = _mastery()
    if page == "home":
        _render_home(state, ctx, user)
    elif page == "fortune":
        game_minigames.render_fortune(ctx)
    elif page == "match":
        game_minigames.render_match(ctx)
    elif page == "sentence":
        game_minigames.render_sentence(ctx)
    elif page == "hunt":
        game_hunt.render_hunt(ctx)
    elif page == "market":
        _render_market(state, ctx)
    else:
        _render_badges(state, ctx)


def render_cultivation(user, learned_day):
    if learned_day < 1:
        st.info("Hãy học những từ đầu tiên rồi quay lại Động Phủ.")
        return
    if len(gq.load_pool(learned_day)) < 4:
        st.info("Cần học ít nhất 4 từ để mở các hoạt động tu tiên.")
        return
    _body(user, learned_day)
