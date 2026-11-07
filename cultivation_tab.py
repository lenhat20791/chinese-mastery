"""Tab Động Phủ: trang chủ tu tiên, các trò chơi ôn tập, phường thị và danh hào."""
import base64
import time
from pathlib import Path

import streamlit as st

import game_config as cfg
import game_core as core
import game_hunt
import game_minigames
import game_questions as gq
import game_ui
import techniques_ui
import danh_hao_ui
from database import _demon_rows

NAV = {
    "home": "🏯 Động Phủ", "fortune": "🔮 Quẻ Bói", "match": "🃏 Lật Bài",
    "hunt": "🗺️ Săn Yêu Thú", "alchemy": "⚗️ Luyện Đan", "talisman": "🪬 Vẽ Phù", 
    "market": "🏪 Phường Thị", "techniques": "📜 Công Pháp Các", "danh_hao": "🏅 Danh Hào",
}
UNLOCK_KEY = {"fortune": "fortune", "match": "match", "hunt": "hunt", "alchemy": "hunt", "talisman": "hunt"}


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
    path = Path(__file__).parent / "assets" / "hinh tu luyen" / "avatar_web.webp"
    if path.exists():
        st.image(str(path), use_container_width=True)
        return
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
        arts = core.equipped_artifacts(state)
        for n in range(cfg.ARTIFACT_SLOTS):
            if n < len(state["equipped"]) and state["equipped"][n]:
                art = next(a for a in arts if a["id"] == state["equipped"][n])
                recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
                st.markdown(f"**Pháp bảo {n + 1}:** {cfg.QUALITY_NAMES[art['quality']]} {recipe['name']} "
                            f"+{art['upgrade']} ({cfg.KIND_LABEL[recipe['kind']]})")
            else:
                st.caption(f"Ô pháp bảo {n + 1}: trống" + (" — ghé Phường Thị để mua bí phương." if n == 0 else ""))
        buff = core.active_buff(state)
        if buff:
            name, desc, _, _ = cfg.FORTUNE_BUFFS[buff[0]]
            st.caption(f"✨ {name}: {desc.format(v=buff[1])}")
    stats = core.player_stats(ctx["idx"], core.equipped_artifacts(state), ctx["bonuses"],
                              core.get_techniques_inventory(core.current_user_id()))
    demons = len(_demon_rows())
    bn = ctx["bonuses"]
    c = st.columns(4)
    c[0].metric("💎 Linh Thạch", f"{state['ls']:,}")
    c[1].metric("⚔️ Công kích", f"{stats['atk']:.0f}", f"+{bn['atk'] * 100:.1f}% căn cơ / danh hào")
    c[2].metric("❤️ Sinh lực", f"{stats['hp']:.0f}", f"+{bn['hp'] * 100:.1f}% căn cơ / danh hào")
    c[3].metric("📖 Căn cơ (từ đã học)", ctx["words"])
    c = st.columns(4)
    answers = state["counters"].get("answers_correct", 0)
    c[0].metric("🧠 Ngộ tính (đáp đúng)", answers, f"chí mạng {bn['crit'] * 100:.1f}%")
    c[1].metric("🔥 Đạo tâm (chuỗi ngày)", user.get("consecutive_streak", 0),
                f"giảm sát thương Tâm Ma Kiếp {bn['dao_tam'] * 100:.1f}%")
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


def _cb_equip(artifact_id, idx, slot=None):
    _toast_result(core.equip(artifact_id, idx, slot))


def _cb_unequip(slot):
    _toast_result(core.unequip(slot))


def _cb_sell(artifact_id):
    _toast_result(core.sell_artifact(artifact_id))

def _cb_discard(code):
    _toast_result(core.discard_item(code))


def _farm_text(recipe):
    s = recipe["region"]
    names = [cfg.AREAS[i]["name"] for i in range(4 * s, 4 * s + 4)]
    return (f"Nguyên liệu thường: {names[0]}, {names[2]} · hiếm/quý: {names[1]}, {names[3]}")


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
        recipes_list = cfg.RECIPES
        page_size = 3
        total_recipes = len(recipes_list)
        total_pages = max(1, (total_recipes + page_size - 1) // page_size)
        
        if "market_recipe_page" not in st.session_state:
            st.session_state.market_recipe_page = 0
        if st.session_state.market_recipe_page >= total_pages:
            st.session_state.market_recipe_page = 0

        c_prev, c_lbl, c_next = st.columns([1, 2, 1])
        if c_prev.button("◀ Trang trước", key="m_recipe_prev", disabled=st.session_state.market_recipe_page <= 0):
            st.session_state.market_recipe_page -= 1
            st.rerun()
        c_lbl.markdown(f"<div style='text-align:center; font-weight:600; padding-top:4px;'>Trang {st.session_state.market_recipe_page + 1} / {total_pages}</div>", unsafe_allow_html=True)
        if c_next.button("Trang sau ▶", key="m_recipe_next", disabled=st.session_state.market_recipe_page >= total_pages - 1):
            st.session_state.market_recipe_page += 1
            st.rerun()

        start_idx = st.session_state.market_recipe_page * page_size
        end_idx = start_idx + page_size
        current_recipes = recipes_list[start_idx:end_idx]

        for recipe in current_recipes:
            tier = cfg.ARTIFACT_TIERS[recipe["tier"]]
            c1, c2, c3 = st.columns([1, 4, 2])
            with c1:
                game_ui.show_image_or_emoji("artifacts", recipe["code"], tier["emoji"], 60)
            c2.markdown(f"**{recipe['name']}** · {tier['name']} · {cfg.KIND_LABEL[recipe['kind']]}  \n"
                        f"Cần {cfg.MAJOR_REALMS[recipe['min_idx']]} · bộ nguyên liệu {cfg.ITEM_SETS[recipe['region']]['name']}  \n"
                        f"{_farm_text(recipe)}")
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
            flat, pct = core.artifact_bonus(recipe, art["quality"], art["upgrade"])
            stat = "công" if recipe["kind"] == "atk" else "HP"
            c1, c2, c3 = st.columns([1, 4, 3])
            with c1:
                game_ui.show_image_or_emoji("artifacts", recipe["code"], tier["emoji"], 70)
            slot = state["equipped"].index(art["id"]) if art["id"] in state["equipped"] else None
            c2.markdown(f"**{cfg.QUALITY_NAMES[art['quality']]} {recipe['name']} +{art['upgrade']}**"
                        f"{f' · ✅ ô {slot + 1}' if slot is not None else ''}  \n"
                        f"{tier['name']} · {cfg.KIND_LABEL[recipe['kind']]} · +{flat:.0f} {stat} · +{pct * 100:.0f}% {stat} gốc")
            if slot is not None:
                c3.button("Tháo", key=f"unequip_{art['id']}", on_click=_cb_unequip, args=(slot,))
            else:
                free = state["equipped"].count(None)
                if free:
                    c3.button("Trang bị", key=f"equip_{art['id']}", on_click=_cb_equip, args=(art["id"], idx),
                              disabled=idx < recipe["min_idx"])
                else:
                    for n in range(cfg.ARTIFACT_SLOTS):
                        c3.button(f"Thay ô {n + 1}", key=f"equip_{art['id']}_{n}", on_click=_cb_equip,
                                  args=(art["id"], idx, n), disabled=idx < recipe["min_idx"])
            refund = round(core.recipe_craft_cost(recipe) * cfg.SELL_REFUND_RATIO)
            c3.button(f"Bán (+{refund:,} 💎)", key=f"sell_{art['id']}", on_click=_cb_sell, args=(art["id"],))
            if art["upgrade"] < cfg.UPGRADE_MAX:
                ls, mats = core.upgrade_cost(recipe, art["upgrade"])
                c3.caption(f"Nâng +{art['upgrade'] + 1}: {ls:,} 💎 · {_items_text(mats, state['inventory'])} · "
                           f"{int(core.upgrade_chance(art['upgrade']) * 100)}%")
                c3.button("⬆️ Nâng cấp", key=f"upg_{art['id']}", on_click=_cb_upgrade, args=(art["id"],),
                          disabled=state["ls"] < ls or bool(core.missing_materials(state, mats)))
    with t_inv:
        if not state["inventory"]:
            st.info("Kho đồ trống. Hãy đi săn yêu thú để thu thập nguyên liệu.")
        else:
            items_list = sorted(state["inventory"].items())
            cols_per_row = 5
            for i in range(0, len(items_list), cols_per_row):
                cols = st.columns(cols_per_row)
                for j in range(cols_per_row):
                    idx_item = i + j
                    if idx_item < len(items_list):
                        code, qty = items_list[idx_item]
                        item = cfg.ITEMS[code]
                        with cols[j]:
                            img_path = game_ui.find_image(item["folder"], item["img_code"])
                            if img_path:
                                img_b64 = game_ui.get_cached_image_b64(img_path)
                                img_html = f'<img src="data:image/jpeg;base64,{img_b64}" width="42" title="{item["name"]} (×{qty})" style="display:block; margin:0 auto; object-fit:contain;" />'
                            else:
                                img_html = f'<div title="{item["name"]} (×{qty})" style="font-size:32px; text-align:center;">{item["emoji"]}</div>'

                            st.markdown(f"""
                            <div style="border: 2px dashed #c9a24b; border-radius: 12px; padding: 8px; text-align: center; background: rgba(27,20,36,0.7); height: 105px; display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; margin-bottom: 2px;">
                                {img_html}
                                <div style="position: absolute; bottom: 3px; right: 5px; background: #c9a24b; color: #000; font-weight: 700; font-size: 0.7rem; padding: 0px 4px; border-radius: 4px;">×{qty}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            st.markdown(f"<div style='font-size:0.75rem; font-weight:600; text-align:center; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:2px;' title='{item['name']}'>{item['name']}</div>", unsafe_allow_html=True)
                            st.button(f"🗑️ Vứt", key=f"discard_{code}", on_click=_cb_discard, args=(code,), use_container_width=True)

def _render_techniques(state, ctx):
    """Phiên 11: Giao diện công pháp redesign - Layout 2 cột với auto-placement."""
    st.markdown("### 📜 Công Pháp Các")
    st.caption("Chọn công pháp để sử dụng, hệ thống sẽ tự động đặt vào khung Đan Điền.")
    techniques_ui.render_techniques_tab()


@st.fragment
def _body(user, learned_day):
    # Đảm bảo user_id được lưu trong session state cho các component cần dùng
    st.session_state.user_id = user.get("id")
    
    state = core.get_state()
    pool = gq.load_pool(learned_day)
    words = len(pool)
    realm = core.realm_info(words)
    ctx = {"pool": pool, "words": words, "realm": realm, "idx": realm["idx"], "mastery": {},
           "grammar": _unlocked("grammar_battle", realm["idx"], words),
           "bonuses": core.stat_bonuses(words, state["counters"].get("answers_correct", 0),
                                        user.get("consecutive_streak", 0), state.get("title"))}
    page = st.radio("Điều hướng", list(NAV), format_func=lambda k: NAV[k], horizontal=True, key="game_nav",
                    label_visibility="collapsed")
    talisman_unlocked = bool(state["counters"].get("talisman_unlocked"))
    if words >= 4 and not talisman_unlocked:
        core.apply_changes(incr={"talisman_unlocked": 1})
        talisman_unlocked = True
    if page in UNLOCK_KEY and not (page == "talisman" and talisman_unlocked) and not _unlocked(UNLOCK_KEY[page], realm["idx"], words):
        st.info(f"🔒 {_unlock_text(UNLOCK_KEY[page])} Hiện có {words} từ.")
        return
    if page in ("fortune", "match", "hunt", "alchemy", "talisman"):
        ctx["mastery"] = _mastery()
    if page == "home":
        _render_home(state, ctx, user)
    elif page == "fortune":
        game_minigames.render_fortune(ctx)
    elif page == "match":
        game_minigames.render_match(ctx)
    elif page == "hunt":
        game_hunt.render_hunt(ctx)
    elif page == "alchemy":
        game_minigames.render_alchemy(ctx)
    elif page == "talisman":
        game_minigames.render_talisman(ctx)
    elif page == "market":
        _render_market(state, ctx)
    elif page == "techniques":
        _render_techniques(state, ctx)
    elif page == "danh_hao":
        danh_hao_ui.render_danh_hao_tab()


def render_cultivation(user, learned_day):
    if learned_day < 1:
        st.info("Hãy học những từ đầu tiên rồi quay lại Động Phủ.")
        return
    if len(gq.load_pool(learned_day)) < 4:
        st.info("Cần học ít nhất 4 từ để mở các hoạt động tu tiên.")
        return
    _body(user, learned_day)
