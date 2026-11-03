"""Săn yêu thú: bản đồ SVG, chiến đấu theo lượt (mỗi lượt một câu ôn từ vựng), rơi vật phẩm."""
import base64
import math
import random

import streamlit as st

import game_config as cfg
import game_core as core
import game_questions as gq
import game_ui

MAP_W, MAP_H = 800, 400
REGION_COLORS = ["#e8d9a8", "#e6c9a0", "#d9d6b0", "#d4c39a", "#e2cfb0", "#d8cba0", "#e5d6ae", "#dcc9a6"]


# ---------------------------------------------------------------------------
# Bản đồ
# ---------------------------------------------------------------------------

def region_cell(r):
    """(cột, hàng) của vùng r trên lưới 4x2; hàng dưới đi ngược chiều để thành đường rắn."""
    return (r, 0) if r < 4 else (7 - r, 1)


def build_map_svg(unlocked, selected):
    rng = random.Random(11)
    verts = {}
    for c in range(5):
        for rw in range(3):
            x, y = c * MAP_W / 4, rw * MAP_H / 2
            if 0 < c < 4:
                x += rng.uniform(-28, 28)
            if 0 < rw < 2:
                y += rng.uniform(-28, 28)
            verts[(c, rw)] = (x, y)
    mids = {}

    def mid(a, b):
        key = tuple(sorted((a, b)))
        if key not in mids:
            (x1, y1), (x2, y2) = verts[a], verts[b]
            mids[key] = ((x1 + x2) / 2 + rng.uniform(-12, 12), (y1 + y2) / 2 + rng.uniform(-12, 12))
        return mids[key]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {MAP_W} {MAP_H}" width="{MAP_W}" height="{MAP_H}">',
             f'<rect width="{MAP_W}" height="{MAP_H}" fill="#f3e7c4"/>']
    labels = []
    for r in range(cfg.REGION_COUNT):
        c, rw = region_cell(r)
        corners = [(c, rw), (c + 1, rw), (c + 1, rw + 1), (c, rw + 1)]
        points = []
        for i, a in enumerate(corners):
            b = corners[(i + 1) % 4]
            points += [verts[a], mid(a, b)]
        pts = " ".join(f"{x:.0f},{y:.0f}" for x, y in points)
        locked = r not in unlocked
        fill = "#bdb7a8" if locked else REGION_COLORS[r]
        stroke, width = ("#d99a00", 5) if r == selected else ("#6b4f2a", 2)
        parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" '
                     f'stroke-linejoin="round"/>')
        cx = sum(p[0] for p in points) / len(points)
        cy = sum(p[1] for p in points) / len(points)
        for k in range(3):  # núi
            mx, my = cx + (k - 1) * 34 + rng.uniform(-6, 6), cy - 38 + rng.uniform(-6, 6)
            parts.append(f'<polygon points="{mx - 16:.0f},{my + 16:.0f} {mx:.0f},{my - 14:.0f} {mx + 16:.0f},{my + 16:.0f}" '
                         f'fill="{"#9a9588" if locked else "#a98c5d"}" stroke="#5a4426" stroke-width="1"/>')
        name = ("🔒 " if locked else "") + cfg.REGIONS[r]["name"]
        labels.append(f'<text x="{cx:.0f}" y="{cy + 22:.0f}" text-anchor="middle" font-size="15" font-weight="bold" '
                      f'font-family="serif" fill="#3a2a12">{name}</text>')
        labels.append(f'<text x="{cx:.0f}" y="{cy + 40:.0f}" text-anchor="middle" font-size="12" font-family="serif" '
                      f'fill="#5a4426">{cfg.MAJOR_REALMS[2 * r]} – {cfg.MAJOR_REALMS[2 * r + 1]}</text>')
    parts.append(f'<path d="M0,215 C120,170 220,260 340,205 S560,150 680,215 S780,190 {MAP_W},180" fill="none" '
                 f'stroke="#6aa7c9" stroke-width="9" stroke-linecap="round" opacity="0.85"/>')
    parts += labels
    parts.append("</svg>")
    return "".join(parts)


def show_map(unlocked, selected):
    svg = build_map_svg(unlocked, selected)
    encoded = base64.b64encode(svg.encode()).decode()
    st.markdown(f'<img src="data:image/svg+xml;base64,{encoded}" style="width:100%;border-radius:10px;'
                f'border:2px solid #6b4f2a"/>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hàm thuần của chiến đấu
# ---------------------------------------------------------------------------

def monster_stats(region, boss=False):
    idx = 2 * region
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
    if boss:
        return base_atk * cfg.BOSS_HITS, base_hp * cfg.BOSS_ATK_RATIO
    return base_atk * cfg.MONSTER_HITS, base_hp * cfg.MONSTER_ATK_RATIO


def hit_damage(atk, combo, max_hp, min_hits, rng=random):
    raw = atk * (1 + cfg.COMBO_STEP * min(combo, cfg.COMBO_MAX)) * rng.uniform(0.9, 1.1)
    return min(raw, math.ceil(max_hp / min_hits))


def roll_loot(region, boss, rng=random):
    """Vật phẩm rơi khi hạ yêu thú / boss (số lượng thô, chưa giảm theo lượt chơi)."""
    loot = {}

    def add(code, qty):
        loot[code] = loot.get(code, 0) + qty

    commons = [f"r{region}_{i}" for i in range(3)]
    rares = [f"r{region}_3", f"r{region}_4"]
    if boss:
        d = cfg.DROP_BOSS
        for _ in range(d["common_rolls"]):
            add(rng.choice(commons), rng.randint(*d["common_qty"]))
        for _ in range(d["rare_rolls"]):
            add(rng.choice(rares), rng.randint(*d["rare_qty"]))
        if rng.random() < d["precious_chance"]:
            add(f"r{region}_5", 1)
    else:
        d = cfg.DROP_NORMAL
        for _ in range(d["common_rolls"]):
            add(rng.choice(commons), rng.randint(*d["common_qty"]))
        if rng.random() < d["rare_chance"]:
            add(rng.choice(rares), 1)
    return loot


def scale_loot(loot, factor, rng=random):
    scaled = {code: core.stochastic_round(qty * factor, rng) for code, qty in loot.items()}
    return {code: qty for code, qty in scaled.items() if qty > 0}


def loot_text(loot):
    return ", ".join(f"{cfg.ITEMS[c]['emoji']} {cfg.ITEMS[c]['name']} ×{q}" for c, q in loot.items()) or "không có"


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


def start_battle(region, kind, zone, ctx):
    state = core.get_state()
    stats = core.player_stats(ctx["idx"], core.equipped_artifact(state))
    b = {
        "kind": kind, "region": region, "zone": zone, "pmax": stats["hp"], "php": stats["hp"], "patk": stats["atk"],
        "combo": 0, "shield": core.buff_value(state, "shield"), "taken": 0, "correct": 0, "total": 0,
        "log": [], "results": [], "loot": {}, "ls_base": 0, "over": None, "settled": None, "turn": 0,
        "events_left": cfg.SPECIAL_EVENTS if kind == "special" else 0,
        "stage": "explore" if kind == "special" else "fight", "monster": None, "trap": None,
    }
    reg = cfg.REGIONS[region]
    if kind == "normal":
        _, monsters = reg["zones"][zone]
        code, name, emoji = random.choice(monsters)
        hp, atk = monster_stats(region)
        b["monster"] = {"id": code, "name": name, "emoji": emoji, "hp": hp, "max": hp, "atk": atk, "boss": False}
        b["log"].append(f"⚔️ **{name}** xuất hiện ở {reg['zones'][zone][0]}!")
    else:
        b["log"].append(f"🏯 Bạn tiến vào **{reg['special'][0]}**. Cẩn thận cơ quan phía trước...")
        b["trap"] = random.choice(cfg.TRAPS)
    _next_question(b, ctx)
    st.session_state.g_battle = b


def _boss_appears(b, ctx):
    code, name, emoji = cfg.REGIONS[b["region"]]["special"][2]
    hp, atk = monster_stats(b["region"], boss=True)
    b["monster"] = {"id": code, "name": name, "emoji": emoji, "hp": hp, "max": hp, "atk": atk, "boss": True}
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
    ok = gq.evaluate(q, choice)
    b["total"] += 1
    b["results"].append((word["id"], ok))
    if ok:
        b["correct"] += 1
    answer_note = f"{word['hanzi']} ({word.get('pinyin') or ''}) = {gq.short_meaning(word, 50)}"
    if b["stage"] == "explore":
        _explore_turn(b, ok, answer_note, ctx)
    else:
        _fight_turn(b, ok, answer_note)
    if not b["over"]:
        _next_question(b, ctx)
    else:
        _settle_battle(b, ctx)


def _explore_turn(b, ok, note, ctx):
    name = b["trap"][0]
    region = b["region"]
    if ok:
        b["ls_base"] += cfg.HUNT_EVENT_REWARD
        if random.random() < cfg.DROP_EVENT["common_chance"]:
            code = f"r{region}_{random.randint(0, 2)}"
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
        _boss_appears(b, ctx)
    else:
        b["trap"] = random.choice(cfg.TRAPS)
        b["log"].append(f"🔍 Tiếp tục thăm dò... {b['trap'][1]}")


def _fight_turn(b, ok, note):
    m = b["monster"]
    if ok:
        min_hits = cfg.BOSS_HITS if m["boss"] else cfg.MONSTER_MIN_HITS
        dmg = hit_damage(b["patk"], b["combo"], m["max"], min_hits)
        b["combo"] += 1
        m["hp"] = max(0.0, m["hp"] - dmg)
        combo = f" · combo ×{b['combo']}" if b["combo"] > 1 else ""
        b["log"].append(f"✅ **{random.choice(cfg.SKILLS)}** trúng {m['name']}, gây **{dmg:.0f}** sát thương{combo}.")
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
    region, m = b["region"], b["monster"]
    loot = dict(b["loot"])
    incr = {"answers_correct": b["correct"]}
    base = b["ls_base"]
    if b["over"] == "win":
        boss = m["boss"]
        base += cfg.HUNT_BOSS_REWARD if boss else cfg.HUNT_NORMAL_REWARD
        for code, qty in roll_loot(region, boss).items():
            loot[code] = loot.get(code, 0) + qty
        incr["bosses_killed" if boss else "monsters_killed"] = 1
        incr[f"kills_r{region}"] = 1
        if boss and b["taken"] == 0:
            incr["flawless_boss"] = 1
    items = scale_loot(loot, drop_factor)
    outcome = {"win": "Hạ", "lose": "Bại trận trước", "retreat": "Rút lui khỏi"}[b["over"]]
    target = m["name"] if m else cfg.REGIONS[region]["special"][0]
    ls, mult, badges = core.settle(
        base, core.scale(2 * region), ctx["words"], results=b["results"], incr=incr, items=items,
        log=("hunt", f"{outcome} {target}, vật phẩm thu được: {loot_text(items)}."))
    b["settled"] = {"ls": ls, "mult": mult, "items": items, "badges": badges}


def _close_battle():
    st.session_state.g_battle = None


def _again(ctx):
    b = st.session_state.g_battle
    start_battle(b["region"], b["kind"], b["zone"], ctx)


# ---------------------------------------------------------------------------
# Giao diện
# ---------------------------------------------------------------------------

def _hp_bar(label, value, maximum):
    st.progress(max(0.0, min(1.0, value / maximum)), text=f"{label}: {value:.0f} / {maximum:.0f}")


def render_battle(ctx):
    b = st.session_state.g_battle
    m = b["monster"]
    reg = cfg.REGIONS[b["region"]]
    left, right = st.columns([1, 2])
    with left:
        if m:
            game_ui.show_image_or_emoji("monsters", m["id"], m["emoji"], 150)
            st.markdown(f"**{m['name']}**" + (" 👑 Boss" if m["boss"] else ""))
            _hp_bar("HP yêu thú", m["hp"], m["max"])
        else:
            st.markdown("<div style='font-size:90px;text-align:center'>🏯</div>", unsafe_allow_html=True)
            st.markdown(f"**{reg['special'][0]}**")
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
        for name in s["badges"]:
            st.toast(f"🏅 Danh hiệu mới: {name}")
        c1, c2 = st.columns(2)
        if b["kind"] == "normal":
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
    st.button("🏃 Rút lui", key="battle_retreat", on_click=_retreat, args=(ctx,))


def render_hunt(ctx):
    st.markdown("### 🗺️ Săn Yêu Thú")
    if st.session_state.get("g_battle"):
        render_battle(ctx)
        return
    state = core.get_state()
    idx = ctx["idx"]
    unlocked = [r for r in range(cfg.REGION_COUNT) if 2 * r <= idx]
    st.session_state.setdefault("hunt_region", unlocked[-1])
    selected = st.selectbox(
        "Chọn vùng đất", range(cfg.REGION_COUNT), key="hunt_region",
        format_func=lambda r: ("" if r in unlocked else "🔒 ") + cfg.REGIONS[r]["name"])
    show_map(unlocked, selected)
    reg = cfg.REGIONS[selected]
    if selected not in unlocked:
        st.warning(f"Cần đạt **{cfg.MAJOR_REALMS[2 * selected]}** để vào {reg['name']}.")
        return
    mult = core.play_multiplier(state["plays"])
    st.caption(f"Phần thưởng Linh Thạch/vật phẩm hiện nhận {int(mult * 100)}% (hôm nay đã chơi {state['plays']} lượt). "
               "Mỗi lượt đánh là một câu ôn từ vựng; trả lời sai sẽ bị yêu thú phản công.")
    cols = st.columns(len(reg["zones"]))
    for z, (zone_name, monsters) in enumerate(reg["zones"]):
        with cols[z]:
            st.markdown(f"**{zone_name}**")
            st.caption(" ".join(f"{e} {n}" for _, n, e in monsters))
            st.button("⚔️ Vào săn", key=f"hunt_zone_{selected}_{z}", use_container_width=True,
                      on_click=start_battle, args=(selected, "normal", z, ctx))
    kills = state["counters"].get(f"kills_r{selected}", 0)
    name, kind, _ = reg["special"]
    st.markdown(f"**{name}** ({kind}) — boss: {reg['special'][2][1]}")
    if kills < cfg.SPECIAL_MIN_KILLS:
        st.caption(f"🔒 Cần hạ {cfg.SPECIAL_MIN_KILLS} yêu thú trong vùng để mở ({kills}/{cfg.SPECIAL_MIN_KILLS}).")
    else:
        st.button(f"🏯 Khám phá {name}", key=f"hunt_special_{selected}", type="primary",
                  on_click=start_battle, args=(selected, "special", None, ctx))
    drops = [cfg.ITEMS[f"r{selected}_{i}"] for i in range(6)]
    st.caption("Vật phẩm vùng này: " + " · ".join(
        f"{d['emoji']} {d['name']} ({cfg.RARITY_LABEL[d['rarity']]})" for d in drops))
