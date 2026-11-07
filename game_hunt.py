"""Săn yêu thú: bản đồ có nút bấm, chiến đấu theo lượt (mỗi lượt một câu ôn từ vựng), rơi vật phẩm theo khu."""
import base64
import math
import random
from functools import lru_cache
from pathlib import Path

import streamlit as st

import game_config as cfg
import game_core as core
import game_questions as gq
import game_ui

MAP_FILE = Path(__file__).parent / "assets" / "map" / "map_web.jpg"


# ---------------------------------------------------------------------------
# Hàm thuần của chiến đấu
# ---------------------------------------------------------------------------

def depth_mult(wins):
    return min(cfg.DEPTH_MAX, 1 + cfg.DEPTH_STEP * wins)


def monster_stats(realm_idx, kind="normal", wins=0):
    """(sức công, HP) của quái ở khu thuộc cảnh giới realm_idx; wins = số trận đã thắng trong lượt vào khu."""
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** realm_idx
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** realm_idx
    if kind == "boss":
        return base_hp * cfg.BOSS_ATK_RATIO, base_atk * cfg.BOSS_HITS
    atk, hp = base_hp * cfg.MONSTER_ATK_RATIO, base_atk * cfg.MONSTER_HITS
    if kind == "elite":
        atk, hp = atk * cfg.ELITE_ATK_MULT, hp * cfg.ELITE_HP_MULT
    d = depth_mult(wins)
    return atk * d, hp * d


def hit_damage(atk, combo, max_hp, min_hits, rng=random, crit=0.0):
    raw = atk * (1 + cfg.COMBO_STEP * min(combo, cfg.COMBO_MAX)) * rng.uniform(0.9, 1.1)
    is_crit = rng.random() < crit
    if is_crit:
        raw *= cfg.CRIT_MULT
    return min(raw, math.ceil(max_hp / min_hits)), is_crit


def roll_loot(item_set, kind, rng=random):
    """Vật phẩm rơi khi hạ quái / tinh anh / boss (số lượng thô, chưa giảm theo lượt chơi)."""
    loot = {}

    def add(code, qty):
        loot[code] = loot.get(code, 0) + qty

    commons = [f"r{item_set}_{i}" for i in range(3)]
    rares = [f"r{item_set}_3", f"r{item_set}_4"]
    d = {"normal": cfg.DROP_NORMAL, "elite": cfg.DROP_ELITE, "boss": cfg.DROP_BOSS}[kind]
    for _ in range(d["common_rolls"]):
        add(rng.choice(commons), rng.randint(*d["common_qty"]))
    if kind == "elite" and rng.random() < d["rare_chance"]:
        add(rng.choice(rares), 1)
    if kind == "boss":
        for _ in range(d["rare_rolls"]):
            add(rng.choice(rares), rng.randint(*d["rare_qty"]))
    if kind != "normal" and rng.random() < d["precious_chance"]:
        add(f"r{item_set}_5", 1)
    return loot


def scale_loot(loot, factor, rng=random):
    scaled = {code: core.stochastic_round(qty * factor, rng) for code, qty in loot.items()}
    return {code: qty for code, qty in scaled.items() if qty > 0}


def loot_text(loot):
    return ", ".join(f"{cfg.ITEMS[c]['emoji']} {cfg.ITEMS[c]['name']} ×{q}" for c, q in loot.items()) or "không có"


def area_unlocked(area, idx):
    return area["realm"] <= idx


def area_tooltip(area):
    codes = range(3) if area["kind"] == "normal" else range(6)
    drops = [cfg.ITEMS[f"r{area['item_set']}_{i}"] for i in codes]
    lines = [f"{area['name']} — {cfg.AREA_KIND_LABEL[area['kind']]}",
             f"Cảnh giới: {cfg.MAJOR_REALMS[area['realm']]} ({cfg.world_of(area['realm'])})",
             "Vật phẩm rơi: " + ", ".join(f"{d['emoji']} {d['name']}" for d in drops)]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Trận đánh
# ---------------------------------------------------------------------------

def _next_question(b, ctx):
    last = b.get("last_word")
    pool = [w for w in ctx["pool"] if w["id"] != last] if len(ctx["pool"]) > 1 else ctx["pool"]
    word = gq.pick_words(pool, ctx["mastery"], 1)[0]
    b["q"] = gq.make_question(word, ctx["pool"], allow_cloze=ctx["grammar"])
    b["last_word"] = word["id"]
    b["turn"] += 1


def start_battle(area_i, kind, ctx):
    """kind: normal | elite | boss. Vào khu từ bản đồ thì gọi enter_area để reset độ sâu."""
    state = core.get_state()
    area = cfg.AREAS[area_i]
    run = st.session_state.get("g_run")
    wins = run["wins"] if run and run["area"] == area_i else 0
    stats = core.player_stats(ctx["idx"], core.equipped_artifacts(state), ctx.get("bonuses"))
    b = {
        "kind": kind, "area": area_i, "wins": wins, "pmax": stats["hp"], "php": stats["hp"], "patk": stats["atk"],
        "crit": stats["crit"],
        "combo": 0, "shield": core.buff_value(state, "shield"), "taken": 0, "correct": 0, "total": 0,
        "log": [], "results": [], "loot": {}, "ls_base": 0, "over": None, "settled": None, "turn": 0,
        "events_left": cfg.SPECIAL_EVENTS if kind == "boss" else 0,
        "stage": "explore" if kind == "boss" else "fight", "monster": None, "trap": None,
    }
    if kind == "boss":
        b["log"].append(f"🏯 Bạn tiến sâu vào trung tâm **{area['name']}**. Cẩn thận cơ quan phía trước...")
        b["trap"] = random.choice(cfg.TRAPS)
    else:
        code, name, emoji = random.choice(area["monsters"])
        atk, hp = monster_stats(area["realm"], kind, wins)
        b["monster"] = {"id": code, "name": name, "emoji": emoji, "hp": hp, "max": hp, "atk": atk,
                        "boss": False, "folder": "monsters"}
        tag = "tinh anh " if kind == "elite" else ""
        b["log"].append(f"⚔️ {tag}**{name}** xuất hiện ở {area['name']}!")
        if wins:
            b["log"].append(f"🌲 Bạn đã đi sâu vào khu vực qua {wins} trận thắng (quái ×{depth_mult(wins):.2f}).")
    _next_question(b, ctx)
    st.session_state.g_battle = b


def enter_area(area_i, kind, ctx):
    st.session_state.g_run = {"area": area_i, "wins": 0}
    start_battle(area_i, kind, ctx)


def _boss_appears(b):
    area = cfg.AREAS[b["area"]]
    code, name, emoji = area["boss"]
    atk, hp = monster_stats(area["realm"], "boss")
    b["monster"] = {"id": code, "name": name, "emoji": emoji, "hp": hp, "max": hp, "atk": atk,
                    "boss": True, "folder": "boss"}
    b["stage"] = "fight"
    b["log"].append(f"👹 **{name}** hiện thân! Đây là trận chiến quyết định.")


def _monster_strikes(b, dmg, source):
    if b["shield"] > 0:
        b["shield"] -= 1
        b["log"].append(f"🛡️ Hộ Thân Phù chắn đòn của {source}.")
        return
    b["php"] = max(0.0, b["php"] - dmg)
    b["taken"] += dmg
    b["log"].append(f"💥 {source} đánh trúng bạn, mất **{dmg:.0f}** HP.")


def _answer(choice, ctx, pin_key=None):
    b = st.session_state.get("g_battle")
    if not b or b["over"]:
        return
    if pin_key is not None:
        choice = st.session_state.get(pin_key, "")
    q = b["q"]
    word = q["word"]
    b["confirm_retreat"] = False
    ok = gq.evaluate(q, choice)
    b["total"] += 1
    b["results"].append((word["id"], ok))
    if ok:
        b["correct"] += 1
    answer_note = f"{word['hanzi']} ({word.get('pinyin') or ''}) = {gq.short_meaning(word, 50)}"
    if b["stage"] == "explore":
        _explore_turn(b, ok, answer_note)
    else:
        _fight_turn(b, ok, answer_note)
    if not b["over"]:
        _next_question(b, ctx)
    else:
        _settle_battle(b, ctx)


def _explore_turn(b, ok, note):
    name = b["trap"][0]
    item_set = cfg.AREAS[b["area"]]["item_set"]
    if ok:
        b["ls_base"] += cfg.HUNT_EVENT_REWARD
        if random.random() < cfg.DROP_EVENT["common_chance"]:
            code = f"r{item_set}_{random.randint(0, 2)}"
            qty = random.randint(*cfg.DROP_EVENT["common_qty"])
            b["loot"][code] = b["loot"].get(code, 0) + qty
            b["log"].append(f"✅ Giải được **{name}**! Nhặt được {cfg.ITEMS[code]['emoji']} {cfg.ITEMS[code]['name']} ×{qty}.")
        else:
            b["log"].append(f"✅ Giải được **{name}**! Bên trong chỉ có chút linh khí.")
    else:
        b["log"].append(f"❌ Giải sai **{name}**! Đáp án: {note}")
        _monster_strikes(b, b["pmax"] * 0.08, "Cơ quan")
        b["php"] = max(b["php"], 1.0)
    b["events_left"] -= 1
    if b["events_left"] <= 0:
        _boss_appears(b)
    else:
        b["trap"] = random.choice(cfg.TRAPS)
        b["log"].append(f"🔍 Tiếp tục thăm dò... {b['trap'][1]}")


def _fight_turn(b, ok, note):
    m = b["monster"]
    if ok:
        min_hits = cfg.BOSS_HITS if m["boss"] else cfg.MONSTER_MIN_HITS
        dmg, is_crit = hit_damage(b["patk"], b["combo"], m["max"], min_hits, crit=b.get("crit", 0.0))
        b["combo"] += 1
        m["hp"] = max(0.0, m["hp"] - dmg)
        crit_tag = " 💥 **Chí mạng!**" if is_crit else ""
        b["log"].append(f"✅ Bạn sử dụng tuyệt kỹ +{cfg.SKILL_NAME} tấn công **{m['name']}**, "
                        f"gây **{dmg:.0f}** sát thương + combo {b['combo']}{crit_tag}")
        if m["hp"] <= 0:
            b["over"] = "win"
            b["log"].append(f"🏆 Hạ được **{m['name']}**!")
    else:
        b["combo"] = 0
        b["log"].append(f"❌ Sai rồi! Đáp án: {note}")
        _monster_strikes(b, m["atk"] * random.uniform(0.9, 1.1), m["name"])
        if b["php"] <= 0:
            b["over"] = "lose"
            b["log"].append("☠️ Bạn trọng thương, buộc phải rút lui.")


def _set_confirm(value):
    b = st.session_state.get("g_battle")
    if b:
        b["confirm_retreat"] = value


def _retreat(ctx):
    b = st.session_state.get("g_battle")
    if b and not b["over"]:
        b["over"] = "retreat"
        b["log"].append("🏃 Bạn rút lui an toàn.")
        _settle_battle(b, ctx)


def _settle_battle(b, ctx):
    state = core.get_state()
    mult = core.play_multiplier(state["plays"])
    drop_factor = mult * (1 + core.buff_value(state, "drop") / 100)
    area = cfg.AREAS[b["area"]]
    kind, m = b["kind"], b["monster"]
    loot = dict(b["loot"])
    incr = {"answers_correct": b["correct"]}
    base = b["ls_base"]
    run = st.session_state.get("g_run")
    if b["over"] == "win":
        base += {"normal": cfg.HUNT_NORMAL_REWARD, "elite": cfg.HUNT_ELITE_REWARD, "boss": cfg.HUNT_BOSS_REWARD}[kind]
        for code, qty in roll_loot(area["item_set"], kind).items():
            loot[code] = loot.get(code, 0) + qty
        incr["bosses_killed" if kind == "boss" else "monsters_killed"] = 1
        if kind == "elite":
            incr[f"elite_r{area['realm']}"] = 1
        if kind == "boss" and b["taken"] == 0:
            incr["flawless_boss"] = 1
        
        # Phiên 8: Boss rơi công pháp
        if kind == "boss":
            technique_code, grade = core.roll_technique(area["realm"])
            if technique_code:
                technique_id = core.add_technique(core.current_user_id(), technique_code)
                if technique_id > 0:
                    technique = cfg.TECHNIQUE_BY_CODE[technique_code]
                    b["technique_drop"] = {
                        "code": technique_code,
                        "name": technique["name"],
                        "grade": grade,
                        "emoji": technique["emoji"],
                    }
                    b["log"].append(f"✨ **{technique['name']}** rơi! (Cấp: {cfg.TECHNIQUE_GRADES[grade]})")
        
        if kind != "boss" and run:
            run["wins"] += 1
            if run["wins"] % cfg.DEPTH_EVERY == 0:
                b["log"].append("🌲 Bạn đã đi sâu vào khu vực, bắt đầu gặp quái mạnh hơn!")
    else:
        st.session_state.g_run = None
    if kind == "boss":
        st.session_state.g_run = None
    items = scale_loot(loot, drop_factor)
    outcome = {"win": "Hạ", "lose": "Bại trận trước", "retreat": "Rút lui khỏi"}[b["over"]]
    target = m["name"] if m else area["name"]
    ls, mult, badges = core.settle(
        base, core.scale(area["realm"]), ctx["words"], results=b["results"], incr=incr, items=items,
        log=("hunt", f"{outcome} {target} ({area['name']}), vật phẩm thu được: {loot_text(items)}."))
    b["settled"] = {"ls": ls, "mult": mult, "items": items, "badges": badges}


def _close_battle():
    st.session_state.g_battle = None
    st.session_state.g_run = None


def _again(ctx):
    b = st.session_state.g_battle
    start_battle(b["area"], b["kind"], ctx)


def _pick_area(i):
    st.session_state["hunt_pick"] = i


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------

def _hp_bar(label, value, maximum):
    st.progress(max(0.0, min(1.0, value / maximum)), text=f"{label}: {value:.0f} / {maximum:.0f}")


def render_battle(ctx):
    b = st.session_state.g_battle
    m = b["monster"]
    area = cfg.AREAS[b["area"]]
    left, right = st.columns([1, 2])
    with left:
        if m:
            game_ui.show_image_or_emoji(m["folder"], m["id"], m["emoji"], 150)
            tag = " 👑 Boss" if m["boss"] else (" 🔱 Tinh anh" if b["kind"] == "elite" else "")
            st.markdown(f"**{m['name']}**{tag}")
            _hp_bar("HP yêu thú", m["hp"], m["max"])
        else:
            st.markdown("<div style='font-size:90px;text-align:center'>🏯</div>", unsafe_allow_html=True)
            st.markdown(f"**{area['name']}**")
            st.caption(f"Còn {b['events_left']} cơ quan trước khi gặp boss")
        _hp_bar("HP của bạn", b["php"], b["pmax"])
        if b["shield"]:
            st.caption(f"🛡️ Hộ Thân Phù còn {b['shield']} lần chắn")
    with right:
        with st.container(height=230, border=True):
            st.markdown("<br>".join(reversed(b["log"][-14:])), unsafe_allow_html=True)
    if b["over"]:
        s = b["settled"]
        verdict = {"win": "🏆 Thắng lợi!", "lose": "☠️ Bại trận", "retreat": "🏃 Đã rút lui"}[b["over"]]
        (st.success if b["over"] == "win" else st.warning)(
            f"{verdict} · +{s['ls']} 💎 Linh Thạch"
            + (f" (hệ số {int(s['mult'] * 100)}%)" if s["mult"] < 1 else "") + f" · Vật phẩm: {loot_text(s['items'])}")
        
        # Phiên 8: Hiển thị công pháp rơi
        if b.get("technique_drop"):
            tech_drop = b["technique_drop"]
            tech_color = game_ui.technique_color(tech_drop["grade"])
            st.markdown(f"""
            <div style="background:linear-gradient(135deg, {tech_color}25, {tech_color}05); 
                        border:2px solid {tech_color}; border-radius:8px; padding:12px; 
                        margin:8px 0; text-align:center; color:{tech_color}; font-weight:bold;">
                <div style="font-size:40px;">{tech_drop["emoji"]}</div>
                <div style="font-size:16px;">{tech_drop["name"]}</div>
                <div style="font-size:12px;">Cấp: {cfg.TECHNIQUE_GRADES[tech_drop["grade"]]}</div>
            </div>
            """, unsafe_allow_html=True)
        
        for name in s["badges"]:
            st.toast(f"🏅 Danh hiệu mới: {name}")
        c1, c2 = st.columns(2)
        if b["kind"] != "boss" and b["over"] == "win":
            c1.button("⚔️ Săn tiếp", key="battle_again", on_click=_again, args=(ctx,), type="primary",
                      use_container_width=True)
        c2.button("🗺️ Về bản đồ", key="battle_close", on_click=_close_battle, use_container_width=True)
        return
    q = b["q"]
    if b["stage"] == "explore":
        st.info(f"**{b['trap'][0]}** — {b['trap'][1]}")
    st.markdown(f"<div class='quiz-prompt' style='text-align:center;font-size:40px'>{q['prompt']}</div>",
                unsafe_allow_html=True)
    st.caption(q["hint"])
    if q["type"] == "audio":
        game_ui.speak(q["audio"], autoplay=True)
    if q["options"] is None:
        key = f"pin_{b['turn']}"
        with st.form(f"pin_form_{b['turn']}", clear_on_submit=False):
            st.text_input("Pinyin", key=key, placeholder="ví dụ: nihao hoặc nǐ hǎo")
            st.form_submit_button("⚔️ Tấn công", on_click=_answer, args=(None, ctx, key), type="primary")
    else:
        for i, option in enumerate(q["options"]):
            st.button(option["label"], key=f"opt_{b['turn']}_{i}", use_container_width=True,
                      on_click=_answer, args=(i, ctx))
    if b.get("confirm_retreat"):
        st.warning("Rút lui sẽ đặt lại độ sâu khu vực, quái trở về sức mạnh ban đầu. Chắc chắn chứ?")
        c1, c2 = st.columns(2)
        c1.button("🏃 Xác nhận rút lui", key="battle_retreat_yes", on_click=_retreat, args=(ctx,))
        c2.button("⚔️ Tiếp tục chiến đấu", key="battle_retreat_no", on_click=_set_confirm, args=(False,),
                  type="primary")
    else:
        st.button("🏃 Rút lui", key="battle_retreat", on_click=_set_confirm, args=(True,))


@lru_cache(maxsize=1)
def _map_b64():
    return base64.b64encode(MAP_FILE.read_bytes()).decode() if MAP_FILE.exists() else ""


def _map_css(idx, selected):
    bg_image = f"background-image:url(data:image/jpeg;base64,{_map_b64()});" if _map_b64() else ""
    rules = [f".st-key-hunt_map{{position:relative;width:100%;aspect-ratio:{cfg.MAP_W}/{cfg.MAP_H};"
             "border-radius:10px;border:2px solid #6b4f2a;overflow:hidden;"
             f"background:#e9dcb8 center/100% 100% no-repeat;{bg_image}}}"]
    for i, area in enumerate(cfg.AREAS):
        left = area["x"] / cfg.MAP_W * 100
        top = (area["y"] + cfg.MAP_ICON_OFFSET_Y) / cfg.MAP_H * 100
        locked = not area_unlocked(area, idx)
        bg = "#7d7d7d" if locked else ("#c0392b" if area["kind"] == "elite" else "#2e7d32")
        ring = "box-shadow:0 0 0 3px #ffd54f,0 0 14px 4px #ffb300;" if i == selected else ""
        rules.append(
            f".st-key-mapbtn_{i}{{position:absolute;left:{left:.2f}%;top:{top:.2f}%;"
            f"transform:translate(-50%,-50%);width:auto !important;z-index:2;}}"
            f".st-key-mapbtn_{i} button{{min-height:0;padding:2px 8px;border-radius:999px;background:{bg} !important;"
            f"border:2px solid #fff !important;{ring}}}"
            f".st-key-mapbtn_{i} button p{{color:#fff !important;font-size:15px;line-height:1.2;}}")
    return f"<style>{''.join(rules)}</style>"


def render_map(idx, selected):
    st.markdown(_map_css(idx, selected), unsafe_allow_html=True)
    with st.container(key="hunt_map"):
        for i, area in enumerate(cfg.AREAS):
            icon = "🔒" if not area_unlocked(area, idx) else ("👑" if area["kind"] == "elite" else "⚔️")
            st.button(icon, key=f"mapbtn_{i}", help=area_tooltip(area), on_click=_pick_area, args=(i,))


def render_area_panel(area_i, ctx):
    state = core.get_state()
    area = cfg.AREAS[area_i]
    st.markdown(f"#### {area['name']} · {cfg.AREA_KIND_LABEL[area['kind']]}")
    st.caption(f"{cfg.world_of(area['realm'])} · cảnh giới {cfg.MAJOR_REALMS[area['realm']]}")
    if not area_unlocked(area, ctx["idx"]):
        st.warning(f"Cần đạt **{cfg.MAJOR_REALMS[area['realm']]}** để vào {area['name']}.")
        return
    mult = core.play_multiplier(state["plays"])
    st.caption(f"Phần thưởng Linh Thạch/vật phẩm hiện nhận {int(mult * 100)}% (hôm nay đã chơi {state['plays']} lượt). "
               "Mỗi lượt đánh là một câu ôn từ vựng; trả lời sai sẽ bị yêu thú phản công. "
               f"Cứ {cfg.DEPTH_EVERY} trận thắng liên tiếp quái mạnh dần; rút lui rồi vào lại thì quái trở về ban đầu.")
    cols = st.columns(len(area["monsters"]))
    for col, (code, name, emoji) in zip(cols, area["monsters"]):
        with col:
            game_ui.show_image_or_emoji("monsters", code, emoji, 90)
            st.caption(name)
    drops = [cfg.ITEMS[f"r{area['item_set']}_{i}"] for i in (range(3) if area["kind"] == "normal" else range(6))]
    st.caption("Vật phẩm rơi: " + " · ".join(
        f"{d['emoji']} {d['name']} ({cfg.RARITY_LABEL[d['rarity']]})" for d in drops))
    if area["kind"] == "normal":
        st.button("⚔️ Vào săn", key=f"enter_{area_i}", type="primary", use_container_width=True,
                  on_click=enter_area, args=(area_i, "normal", ctx))
        return
    st.button("🔱 Săn tinh anh", key=f"enter_{area_i}", type="primary", use_container_width=True,
              on_click=enter_area, args=(area_i, "elite", ctx))
    kills = state["counters"].get(f"elite_r{area['realm']}", 0)
    boss = area["boss"]
    game_ui.show_image_or_emoji("boss", boss[0], boss[2], 120)
    st.markdown(f"**Boss khu vực:** {boss[1]}")
    if kills < cfg.SPECIAL_MIN_KILLS:
        st.caption(f"🔒 Cần hạ {cfg.SPECIAL_MIN_KILLS} tinh anh trong khu để mở thách đấu ({kills}/{cfg.SPECIAL_MIN_KILLS}).")
    else:
        st.button(f"👑 Khiêu chiến {boss[1]}", key=f"boss_{area_i}", use_container_width=True,
                  on_click=enter_area, args=(area_i, "boss", ctx))


def render_hunt(ctx):
    st.markdown("### 🗺️ Săn Yêu Thú")
    if st.session_state.get("g_battle"):
        render_battle(ctx)
        return
    idx = ctx["idx"]
    st.session_state.setdefault("hunt_pick", 2 * idx)
    selected = st.session_state["hunt_pick"]
    st.caption("Bấm vào biểu tượng trên bản đồ (⚔️ khu thường · 👑 khu tinh anh & boss · 🔒 chưa mở); "
               "rê chuột/chạm giữ để xem tên khu và vật phẩm rơi.")
    render_map(idx, selected)
    st.selectbox("Hoặc chọn từ bảng địa danh", range(len(cfg.AREAS)), key="hunt_pick",
                 format_func=lambda i: ("🔒 " if not area_unlocked(cfg.AREAS[i], idx) else "")
                 + f"{cfg.AREAS[i]['name']} ({cfg.AREA_KIND_LABEL[cfg.AREAS[i]['kind']]})")
    render_area_panel(st.session_state["hunt_pick"], ctx)
