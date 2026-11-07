"""Lõi trò chơi tu tiên: trạng thái người chơi (lưu DB, cache trong session), kinh tế, chế tạo, huy hiệu, quẻ bói."""
import bisect
import datetime
import json
import math
import random

import streamlit as st

import game_config as cfg
from database import current_user_id
from userdb import get_user_db

STATE_KEY = "game_state"


# ---------------------------------------------------------------------------
# Hàm thuần (dễ kiểm thử)
# ---------------------------------------------------------------------------

def today():
    now = datetime.datetime.utcnow() + datetime.timedelta(hours=cfg.TZ_OFFSET_HOURS)
    return now.date().isoformat()


def local_hour():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=cfg.TZ_OFFSET_HOURS)).hour


def realm_info(words_learned):
    """Cảnh giới theo số từ đã học."""
    stage = max(0, bisect.bisect_right(cfg.SUB_THRESHOLDS, words_learned) - 1)
    major, sub = divmod(stage, 3)
    next_need = cfg.SUB_THRESHOLDS[stage + 1] if stage + 1 < len(cfg.SUB_THRESHOLDS) else None
    start = cfg.SUB_THRESHOLDS[stage]
    progress = 1.0 if next_need is None else (words_learned - start) / max(1, next_need - start)
    return {
        "stage": stage, "idx": major, "sub": sub,
        "name": f"{cfg.MAJOR_REALMS[major]} · {cfg.SUB_REALMS[sub]}",
        "major_name": cfg.MAJOR_REALMS[major],
        "next_need": next_need, "progress": max(0.0, min(1.0, progress)),
    }


def scale(idx):
    return cfg.ECON_SCALE ** idx


def stochastic_round(value, rng=random):
    base = math.floor(value)
    return base + (1 if rng.random() < value - base else 0)


def recipe_craft_cost(recipe):
    return round(cfg.ARTIFACT_TIERS[recipe["tier"]]["days"] * cfg.BASE_DAY_INCOME * scale(recipe["min_idx"]))


def recipe_price(recipe):
    return round(cfg.RECIPE_PRICE_DAYS * cfg.BASE_DAY_INCOME * scale(recipe["min_idx"]))


def pill_price(idx):
    return round(cfg.PILL_PRICE_DAYS * cfg.BASE_DAY_INCOME * scale(idx))


def recipe_materials(recipe):
    """[(mã vật phẩm, số lượng)] cần cho một lần chế."""
    need = cfg.ARTIFACT_TIERS[recipe["tier"]]["need"]
    region = recipe["region"]
    mats = [(f"r{region}_{i}", q) for i, q in enumerate(need["common"]) if q]
    mats += [(f"r{region}_{3 + i}", q) for i, q in enumerate(need["rare"]) if q]
    if need["precious"]:
        mats.append((f"r{region}_5", need["precious"]))
    return mats


def roll_quality(odds, pity_mid, pity_high, rng=random):
    """Trả về (phẩm 0-2, pity_mid mới, pity_high mới). Có bảo hiểm sau nhiều lần xui."""
    if pity_high + 1 >= cfg.PITY_HIGH_AT:
        quality = 2
    elif pity_mid + 1 >= cfg.PITY_MID_AT:
        quality = rng.choices([1, 2], weights=[odds[1], odds[2]], k=1)[0]
    else:
        quality = rng.choices([0, 1, 2], weights=list(odds), k=1)[0]
    return quality, (0 if quality >= 1 else pity_mid + 1), (0 if quality == 2 else pity_high + 1)


def artifact_bonus(recipe, quality, upgrade):
    """(cộng thẳng, cộng % trên chỉ số gốc của người chơi). Pháp bảo công -> sức công, thủ -> HP."""
    mult = cfg.QUALITY_MULT[quality] * (1 + cfg.UPGRADE_STAT_STEP * upgrade)
    if recipe["kind"] == "atk":
        base, ratio = cfg.PLAYER_BASE_ATK, cfg.ARTIFACT_ATK_RATIO
    else:
        base, ratio = cfg.PLAYER_BASE_HP, cfg.ARTIFACT_HP_RATIO
    flat = base * cfg.POWER_PER_REALM ** recipe["min_idx"] * ratio * mult
    pct = cfg.ARTIFACT_PCT_PER_TIER * (cfg.ARTIFACT_TIERS[recipe["tier"]]["order"] + 1) * mult
    return flat, pct


def diminishing(points, cap, k):
    """Lợi suất giảm dần: cap × p / (p + k)."""
    points = max(0, points or 0)
    return cap * points / (points + k)


def play_multiplier(plays):
    """Hệ số phần thưởng. Luôn trả về 100% (không giới hạn lượt chơi)."""
    return 1.0


def cultivation_boost(idx):
    """Boost chỉ số cơ bản theo tu vi: +5% ATK và +5% HP mỗi cấp. Trả về (atk_pct, hp_pct)."""
    atk_pct = (cfg.CULTIVATION_BOOST_ATK_PCT / 100.0) * idx
    hp_pct = (cfg.CULTIVATION_BOOST_HP_PCT / 100.0) * idx
    return atk_pct, hp_pct


def stat_bonuses(words=0, answers=0, streak=0, honor_code=None):
    """Hiệu ứng của Căn cơ (từ đã học), Ngộ tính (đáp đúng), Đạo tâm (chuỗi ngày), và Danh hào."""
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



def player_stats(idx, artifacts=None, bonuses=None):
    # Chỉ số cơ bản theo tu vi
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
    
    # Boost chỉ số cơ bản theo cultivation level (5% mỗi cấp tu vi)
    cult_atk_pct, cult_hp_pct = cultivation_boost(idx)
    boosted_base_atk = base_atk * (1 + cult_atk_pct)
    boosted_base_hp = base_hp * (1 + cult_hp_pct)
    
    atk, hp = boosted_base_atk, boosted_base_hp
    
    # Cộng pháp bảo (tính % trên chỉ số cơ bản đã được boost)
    for art in artifacts or []:
        recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
        flat, pct = artifact_bonus(recipe, art["quality"], art["upgrade"])
        if recipe["kind"] == "atk":
            atk += flat + boosted_base_atk * pct
        else:
            hp += flat + boosted_base_hp * pct
    
    # Cộng bonus từ các yếu tố khác (Căn cơ, Danh hào, Đạo tâm)
    # KHÔNG cộng dồn cultivation boost lại
    b = bonuses or {}
    return {"atk": atk * (1 + b.get("atk", 0)), "hp": hp * (1 + b.get("hp", 0)), "crit": b.get("crit", 0.0)}


def upgrade_cost(recipe, level):
    ls = round(cfg.UPGRADE_LS_RATIO * recipe_craft_cost(recipe) * (1 + 0.4 * level))
    qty = cfg.UPGRADE_BASE_MATERIALS + level
    mats = [(f"r{recipe['region']}_0", qty), (f"r{recipe['region']}_1", qty)]
    return ls, mats


def upgrade_chance(level):
    return max(0.5, 0.95 - 0.05 * level)


def parse_buff(text):
    if not text or ":" not in text:
        return None
    code, value = text.split(":", 1)
    return (code, int(value)) if code in cfg.FORTUNE_BUFFS else None


def achievement_code(base, tier):
    return f"{base}_{tier}"


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


def available_honors(idx):
    """Trả về danh sách mã danh hào có thể đạt ở cảnh giới hiện tại."""
    return [h["code"] for h in cfg.HONOR_TITLES if h["realm_idx"] <= idx]


# ---------------------------------------------------------------------------
# Trạng thái lưu DB
# ---------------------------------------------------------------------------

def _load(uid):
    conn = get_user_db()
    conn.execute("INSERT OR IGNORE INTO game_profile (user_id) VALUES (?)", (uid,))
    day = today()
    cursors = conn.execute_many([
        ("SELECT linh_thach, equipped_artifact, equipped_title, pity_mid, pity_high, fortune_streak, "
         "fortune_last_day FROM game_profile WHERE user_id = ?", (uid,)),
        ("SELECT plays FROM game_daily WHERE user_id = ? AND day = ?", (uid, day)),
        ("SELECT item_code, qty FROM game_inventory WHERE user_id = ?", (uid,)),
        ("SELECT recipe_code FROM game_recipes WHERE user_id = ?", (uid,)),
        ("SELECT id, recipe_code, quality, upgrade FROM game_artifacts WHERE user_id = ? ORDER BY id", (uid,)),
        ("SELECT vocab_id, tier, status, buff FROM game_fortune WHERE user_id = ? AND day = ?", (uid, day)),
        ("SELECT code FROM game_achievements WHERE user_id = ?", (uid,)),
        ("SELECT key, value FROM game_counters WHERE user_id = ?", (uid,)),
        ("SELECT ts, kind, text FROM game_log WHERE user_id = ? ORDER BY id DESC LIMIT 40", (uid,)),
    ])
    p = cursors[0].fetchone()
    plays = cursors[1].fetchone()
    fortune = cursors[5].fetchone()
    legacy = cfg.LEGACY_RECIPE_CODES
    artifacts = [{"id": r[0], "recipe_code": legacy.get(r[1], r[1]), "quality": r[2], "upgrade": r[3]}
                 for r in cursors[4].fetchall()]
    artifacts = [a for a in artifacts if a["recipe_code"] in cfg.RECIPE_BY_CODE]
    counters = {r[0]: r[1] for r in cursors[7].fetchall()}
    if "equip_1" in counters or "equip_2" in counters:
        slots = [counters.get("equip_1") or None, counters.get("equip_2") or None]
    else:
        slots = [p[1], None]
    owned_ids = {a["id"] for a in artifacts}
    slots = [s if s in owned_ids else None for s in slots]
    return {
        "uid": uid, "day": day,
        "ls": p[0], "equipped": slots, "title": p[2], "pity_mid": p[3], "pity_high": p[4],
        "streak": p[5], "streak_day": p[6],
        "plays": plays[0] if plays else 0,
        "inventory": {r[0]: r[1] for r in cursors[2].fetchall() if r[1] > 0},
        "recipes": {legacy.get(r[0], r[0]) for r in cursors[3].fetchall()},
        "artifacts": artifacts,
        "fortune": ({"vocab_id": fortune[0], "tier": fortune[1], "status": fortune[2], "buff": fortune[3]}
                    if fortune else None),
        "achievements": {r[0] for r in cursors[6].fetchall()},
        "counters": counters,
        "log": [{"ts": r[0], "kind": r[1], "text": r[2]} for r in cursors[8].fetchall()],
    }


def get_state(force=False):
    uid = current_user_id()
    state = st.session_state.get(STATE_KEY)
    if force or state is None or state["uid"] != uid or state["day"] != today():
        state = _load(uid)
        st.session_state[STATE_KEY] = state
    return state


def equipped_artifacts(state):
    """Danh sách pháp bảo đang mang (tối đa ARTIFACT_SLOTS)."""
    by_id = {a["id"]: a for a in state["artifacts"]}
    return [by_id[i] for i in state["equipped"] if i in by_id]


def active_buff(state):
    fortune = state["fortune"]
    if fortune and fortune["status"] == "ok":
        return parse_buff(fortune["buff"])
    return None


def buff_value(state, code):
    buff = active_buff(state)
    return buff[1] if buff and buff[0] == code else 0


def apply_changes(ls=0, items=None, incr=None, maxes=None, log=None, plays=0, extra=None):
    """Ghi một lượt thay đổi nguyên tử rồi nạp lại trạng thái. items: {mã: ±số lượng}."""
    state = get_state()
    uid = state["uid"]
    statements = []
    if ls:
        statements.append(("UPDATE game_profile SET linh_thach = MAX(0, linh_thach + ?) WHERE user_id = ?", (ls, uid)))
        if ls > 0:
            incr = {**(incr or {}), "ls_earned": (incr or {}).get("ls_earned", 0) + ls}
    for code, qty in (items or {}).items():
        statements.append((
            "INSERT INTO game_inventory (user_id, item_code, qty) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, item_code) DO UPDATE SET qty = qty + excluded.qty", (uid, code, qty)))
    if items:
        statements.append(("DELETE FROM game_inventory WHERE user_id = ? AND qty <= 0", (uid,)))
    for key, amount in (incr or {}).items():
        if amount:
            statements.append((
                "INSERT INTO game_counters (user_id, key, value) VALUES (?, ?, ?) "
                "ON CONFLICT (user_id, key) DO UPDATE SET value = value + excluded.value", (uid, key, amount)))
    for key, value in (maxes or {}).items():
        statements.append((
            "INSERT INTO game_counters (user_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, key) DO UPDATE SET value = MAX(value, excluded.value)", (uid, key, value)))
    if plays:
        statements.append((
            "INSERT INTO game_daily (user_id, day, plays) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, day) DO UPDATE SET plays = plays + excluded.plays", (uid, state["day"], plays)))
    for kind, text in ([log] if isinstance(log, tuple) else (log or [])):
        statements.append(("INSERT INTO game_log (user_id, kind, text) VALUES (?, ?, ?)", (uid, kind, text)))
    if log:
        statements.append((
            "DELETE FROM game_log WHERE user_id = ? AND id <= "
            "(SELECT MAX(id) FROM game_log WHERE user_id = ?) - 300", (uid, uid)))
    statements.extend(extra or [])
    if statements:
        get_user_db().batch(statements)
    return get_state(force=True)


def add_log(kind, text):
    apply_changes(log=(kind, text))


def reward_ls(base, mult, state, idx_scale=1.0):
    """Linh Thạch thực nhận: cơ bản x hệ số cảnh giới x giảm theo lượt trong ngày x buff."""
    bonus = 1 + buff_value(state, "ls") / 100
    return max(1, round(base * idx_scale * mult * bonus))


# ---------------------------------------------------------------------------
# Quẻ bói
# ---------------------------------------------------------------------------

def draw_fortune(pool, mastery, pick_words):
    """Quẻ hôm nay (xác định theo user + ngày). Trả về (từ, tên quẻ)."""
    state = get_state()
    rng = random.Random(f"{state['uid']}:{state['day']}")
    names = [t[0] for t in cfg.FORTUNE_TIERS]
    tier = rng.choices(names, weights=[t[1] for t in cfg.FORTUNE_TIERS], k=1)[0]
    word = pick_words(pool, mastery, 1, rng=rng)[0]
    return word, tier


def start_fortune(vocab_id, tier):
    state = get_state()
    get_user_db().execute(
        "INSERT OR IGNORE INTO game_fortune (user_id, day, vocab_id, tier, status) VALUES (?, ?, ?, ?, 'pending')",
        (state["uid"], state["day"], vocab_id, tier))
    return get_state(force=True)


def resolve_fortune(correct, idx):
    """Chốt quẻ: đúng -> nhận buff + Linh Thạch; sai -> Hung. Chỉ chốt một lần mỗi ngày."""
    state = get_state()
    fortune = state["fortune"]
    if not fortune or fortune["status"] != "pending":
        return state
    uid, day = state["uid"], state["day"]
    yesterday = (datetime.date.fromisoformat(day) - datetime.timedelta(days=1)).isoformat()
    streak = state["streak"] + 1 if state["streak_day"] == yesterday else 1
    rng = random.Random(f"{uid}:{day}:buff")
    buff = None
    if correct:
        code = rng.choice(list(cfg.FORTUNE_BUFFS))
        name, _, normal, great = cfg.FORTUNE_BUFFS[code]
        buff = f"{code}:{great if fortune['tier'] == 'Đại Cát' else normal}"
    extra = [
        ("UPDATE game_fortune SET status = ?, buff = ? WHERE user_id = ? AND day = ?",
         ("ok" if correct else "fail", buff, uid, day)),
        ("UPDATE game_profile SET fortune_streak = ?, fortune_last_day = ? WHERE user_id = ?", (streak, day, uid)),
    ]
    ls = round(cfg.FORTUNE_REWARD * scale(idx)) if correct else 0
    text = (f"Quẻ {fortune['tier']}: ngộ ra chữ cổ, nhận buff {cfg.FORTUNE_BUFFS[buff.split(':')[0]][0]}."
            if correct else "Quẻ Hung: chữ này còn chưa vững, tâm ma nhân cơ hội xâm nhập.")
    return apply_changes(ls=ls, maxes={"fortune_streak_best": streak}, log=("fortune", text), extra=extra)


# ---------------------------------------------------------------------------
# Phường thị, chế tạo, nâng cấp
# ---------------------------------------------------------------------------

def buy_recipe(code, idx):
    state = get_state()
    recipe = cfg.RECIPE_BY_CODE[code]
    price = recipe_price(recipe)
    if code in state["recipes"]:
        return False, "Đã sở hữu bí phương này."
    if state["ls"] < price:
        return False, "Không đủ Linh Thạch."
    apply_changes(ls=-price, log=("market", f"Mua bí phương {recipe['name']} với {price} Linh Thạch."),
                  extra=[("INSERT OR IGNORE INTO game_recipes (user_id, recipe_code) VALUES (?, ?)",
                          (state["uid"], code))])
    return True, f"Đã mua bí phương {recipe['name']}."


def buy_pill(idx):
    state = get_state()
    price = pill_price(idx)
    if state["ls"] < price:
        return False, "Không đủ Linh Thạch."
    apply_changes(ls=-price, items={"pham_dan": 1}, log=("market", f"Mua Tụ Phẩm Đan với {price} Linh Thạch."))
    return True, "Đã mua Tụ Phẩm Đan."


def missing_materials(state, mats):
    return [(code, qty, state["inventory"].get(code, 0)) for code, qty in mats
            if state["inventory"].get(code, 0) < qty]


def craft(code, idx, use_pill=False, rng=random):
    state = get_state()
    recipe = cfg.RECIPE_BY_CODE[code]
    if code not in state["recipes"]:
        return False, "Chưa có bí phương này.", None
    if idx < recipe["min_idx"]:
        return False, f"Cần đạt {cfg.MAJOR_REALMS[recipe['min_idx']]} để chế tạo.", None
    cost = recipe_craft_cost(recipe)
    if state["ls"] < cost:
        return False, "Không đủ Linh Thạch.", None
    mats = recipe_materials(recipe)
    if missing_materials(state, mats):
        return False, "Thiếu nguyên liệu.", None
    if use_pill and state["inventory"].get("pham_dan", 0) < 1:
        return False, "Không có Tụ Phẩm Đan.", None
    odds = cfg.QUALITY_ODDS_PILL if use_pill else cfg.QUALITY_ODDS
    quality, pity_mid, pity_high = roll_quality(odds, state["pity_mid"], state["pity_high"], rng)
    items = {c: -q for c, q in mats}
    if use_pill:
        items["pham_dan"] = -1
    uid = state["uid"]
    name = f"{cfg.QUALITY_NAMES[quality]} {recipe['name']}"
    apply_changes(
        ls=-cost, items=items, incr={"crafts": 1},
        log=("craft", f"Luyện thành công {name} ({cfg.ARTIFACT_TIERS[recipe['tier']]['name']}), tốn {cost} Linh Thạch."),
        extra=[
            ("INSERT INTO game_artifacts (user_id, recipe_code, quality) VALUES (?, ?, ?)", (uid, code, quality)),
            ("UPDATE game_profile SET pity_mid = ?, pity_high = ? WHERE user_id = ?", (pity_mid, pity_high, uid)),
        ])
    return True, f"Chế tạo thành công: {name}!", quality


def _slot_statements(uid, slots):
    """Ghi 2 ô pháp bảo vào game_counters (equip_1, equip_2); 0 = ô trống."""
    statements = [("UPDATE game_profile SET equipped_artifact = NULL WHERE user_id = ?", (uid,))]
    for number, artifact_id in enumerate(slots, 1):
        statements.append((
            "INSERT INTO game_counters (user_id, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT (user_id, key) DO UPDATE SET value = excluded.value", (uid, f"equip_{number}", artifact_id or 0)))
    return statements


def equip(artifact_id, idx, slot=None):
    """Trang bị pháp bảo vào ô slot (0/1); không chỉ định ô thì dùng ô trống đầu tiên."""
    state = get_state()
    art = next((a for a in state["artifacts"] if a["id"] == artifact_id), None)
    if art is None:
        return False, "Không tìm thấy pháp bảo."
    recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
    if idx < recipe["min_idx"]:
        return False, f"Cần đạt {cfg.MAJOR_REALMS[recipe['min_idx']]} để dùng pháp bảo này."
    slots = list(state["equipped"])
    if artifact_id in slots:
        return False, "Pháp bảo này đã được trang bị."
    if slot is None:
        slot = next((i for i, s in enumerate(slots) if s is None), None)
        if slot is None:
            return False, "Cả 2 ô đã đầy, hãy chọn ô để thay thế."
    slots[slot] = artifact_id
    apply_changes(extra=_slot_statements(state["uid"], slots))
    return True, "Đã trang bị pháp bảo."


def unequip(slot):
    state = get_state()
    slots = list(state["equipped"])
    slots[slot] = None
    apply_changes(extra=_slot_statements(state["uid"], slots))
    return True, "Đã tháo pháp bảo."


def sell_artifact(artifact_id):
    """Bán pháp bảo, hoàn một phần Linh Thạch chế tạo (không tính nâng cấp)."""
    state = get_state()
    art = next((a for a in state["artifacts"] if a["id"] == artifact_id), None)
    if art is None:
        return False, "Không tìm thấy pháp bảo."
    recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
    refund = round(recipe_craft_cost(recipe) * cfg.SELL_REFUND_RATIO)
    slots = [None if s == artifact_id else s for s in state["equipped"]]
    name = f"{cfg.QUALITY_NAMES[art['quality']]} {recipe['name']} +{art['upgrade']}"
    uid = state["uid"]
    apply_changes(
        ls=refund, log=("market", f"Bán {name}, thu hồi {refund} Linh Thạch."),
        extra=[("DELETE FROM game_artifacts WHERE id = ? AND user_id = ?", (artifact_id, uid))]
        + _slot_statements(uid, slots))
    return True, f"Đã bán {name}, nhận {refund} 💎."

def discard_item(code):
    """Vứt bỏ toàn bộ stack của 1 loại vật phẩm trong kho."""
    state = get_state()
    qty = state["inventory"].get(code, 0)
    if qty <= 0:
        return False, "Vật phẩm không tồn tại trong kho."
    item = cfg.ITEMS.get(code, {"name": code})
    uid = state["uid"]
    apply_changes(
        items={code: -qty},
        log=("market", f"Vứt bỏ {qty} {item['name']}.")
    )
    return True, f"Đã vứt bỏ {qty} {item['name']}."


def upgrade(artifact_id, rng=random):
    state = get_state()
    art = next((a for a in state["artifacts"] if a["id"] == artifact_id), None)
    if art is None:
        return False, "Không tìm thấy pháp bảo."
    if art["upgrade"] >= cfg.UPGRADE_MAX:
        return False, "Đã đạt cấp nâng tối đa."
    recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
    ls, mats = upgrade_cost(recipe, art["upgrade"])
    if state["ls"] < ls or missing_materials(state, mats):
        return False, "Không đủ Linh Thạch hoặc nguyên liệu."
    success = rng.random() < upgrade_chance(art["upgrade"])
    uid = state["uid"]
    items = {c: -q for c, q in mats}
    name = recipe["name"]
    if success:
        apply_changes(
            ls=-ls, items=items, incr={"upgrades": 1},
            log=("craft", f"Tinh luyện {name} lên +{art['upgrade'] + 1}."),
            extra=[("UPDATE game_artifacts SET upgrade = upgrade + 1 WHERE id = ? AND user_id = ?",
                    (artifact_id, uid))])
        return True, f"Thành công! {name} lên +{art['upgrade'] + 1}."
    apply_changes(items=items, log=("craft", f"Tinh luyện {name} thất bại, nguyên liệu tan biến."))
    return False, "Thất bại, nguyên liệu bị tiêu hao (Linh Thạch được hoàn lại)."


def upgrade(artifact_id, rng=random):
    state = get_state()
    art = next((a for a in state["artifacts"] if a["id"] == artifact_id), None)
    if art is None:
        return False, "Không tìm thấy pháp bảo."
    if art["upgrade"] >= cfg.UPGRADE_MAX:
        return False, "Đã đạt cấp nâng tối đa."
    recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
    ls, mats = upgrade_cost(recipe, art["upgrade"])
    if state["ls"] < ls or missing_materials(state, mats):
        return False, "Không đủ Linh Thạch hoặc nguyên liệu."
    success = rng.random() < upgrade_chance(art["upgrade"])
    uid = state["uid"]
    items = {c: -q for c, q in mats}
    name = recipe["name"]
    if success:
        apply_changes(
            ls=-ls, items=items, incr={"upgrades": 1},
            log=("craft", f"Tinh luyện {name} lên +{art['upgrade'] + 1}."),
            extra=[("UPDATE game_artifacts SET upgrade = upgrade + 1 WHERE id = ? AND user_id = ?",
                    (artifact_id, uid))])
        return True, f"Thành công! {name} lên +{art['upgrade'] + 1}."
    apply_changes(items=items, log=("craft", f"Tinh luyện {name} thất bại, nguyên liệu tan biến."))
    return False, "Thất bại, nguyên liệu bị tiêu hao (Linh Thạch được hoàn lại)."


def settle(base_ls, idx_scale, words_learned, results=(), incr=None, maxes=None, items=None, log=None,
           count_play=True, record=True):
    """Chốt một lượt chơi: tính Linh Thạch, ghi kết quả ôn, huy hiệu. Trả về (ls, mult, huy hiệu mới)."""
    from database import record_review_batch

    state = get_state()
    mult = 1.0  # Always 100% multiplier
    ls = reward_ls(base_ls, mult, state, idx_scale) if base_ls > 0 else 0
    if record and results:
        record_review_batch(list(results))
    incr = dict(incr or {})
    hour = local_hour()
    if hour >= cfg.NIGHT_HOUR or hour < 4:
        incr["night_plays"] = 1
    apply_changes(ls=ls, items=items, incr=incr, maxes=maxes, log=log, plays=0)
    return ls, mult, check_achievements(words_learned)


def equip_title(code):
    state = get_state()
    realm = realm_info(state["counters"].get("words_learned", 0))
    idx = realm["idx"]
    available = available_honors(idx)
    
    # Chỉ cho phép trang bị danh hào có sẵn (hoặc None để tháo)
    if code is not None and code not in available:
        return
    
    apply_changes(extra=[("UPDATE game_profile SET equipped_title = ? WHERE user_id = ?", (code, state["uid"]))])


# ---------------------------------------------------------------------------
# Huy hiệu
# ---------------------------------------------------------------------------

def counter_value(state, counter, words_learned):
    if counter == "words_learned":
        return words_learned
    return state["counters"].get(counter, 0)


def check_achievements(words_learned):
    """Mở khóa huy hiệu đủ điều kiện; trả về danh sách thông báo mới."""
    state = get_state()
    unlocked = state["achievements"]
    new, reward, logs, extra = [], 0, [], []
    uid = state["uid"]

    def unlock(code, name, ls=0):
        nonlocal reward
        extra.append(("INSERT OR IGNORE INTO game_achievements (user_id, code) VALUES (?, ?)", (uid, code)))
        reward += ls
        logs.append(("badge", f"Đạt danh hiệu «{name}»" + (f", thưởng {ls} Linh Thạch." if ls else ".")))
        new.append(name)

    for line in cfg.BADGE_LINES:
        value = counter_value(state, line["counter"], words_learned)
        for tier, need in enumerate(line["tiers"]):
            code = achievement_code(line["base"], tier)
            if value >= need and code not in unlocked:
                unlock(code, line["names"][tier], cfg.BADGE_REWARD_LS[tier])
    for hidden in cfg.HIDDEN_BADGES:
        if hidden["code"] not in unlocked and state["counters"].get(hidden["counter"], 0) >= hidden["need"]:
            unlock(hidden["code"], hidden["name"])
    if new:
        apply_changes(ls=reward, log=logs, extra=extra)
    return new
# ---------------------------------------------------------------------------
# Phiên 4: Luyện Đan (Alchemy System)
# ---------------------------------------------------------------------------

def get_inventory_qty(user_id, item_code):
    """Lấy số lượng vật phẩm trong kho."""
    db = get_user_db()
    row = db.execute(
        "SELECT qty FROM game_inventory WHERE user_id = ? AND item_code = ?",
        (user_id, item_code)
    ).fetchone()
    return row[0] if row else 0


def set_inventory_qty(user_id, item_code, qty):
    """Cập nhật số lượng vật phẩm."""
    db = get_user_db()
    if qty <= 0:
        db.execute("DELETE FROM game_inventory WHERE user_id = ? AND item_code = ?", (user_id, item_code))
    else:
        db.execute(
            "INSERT OR REPLACE INTO game_inventory (user_id, item_code, qty) VALUES (?, ?, ?)",
            (user_id, item_code, qty)
        )
    db.commit()


def add_inventory(user_id, item_code, qty):
    """Thêm vật phẩm vào kho."""
    current = get_inventory_qty(user_id, item_code)
    set_inventory_qty(user_id, item_code, current + qty)


def consume_inventory(user_id, item_code, qty):
    """Tiêu hao vật phẩm từ kho."""
    current = get_inventory_qty(user_id, item_code)
    if current < qty:
        return False
    set_inventory_qty(user_id, item_code, current - qty)
    return True


def get_pills_inventory(user_id):
    """Lấy danh sách đan dược trong kho."""
    remove_legacy_pills(user_id)
    db = get_user_db()
    rows = db.execute(
        "SELECT pill_code, qty FROM game_pills WHERE user_id = ? AND qty > 0 ORDER BY pill_code",
        (user_id,)
    ).fetchall()
    result = []
    for code, qty in rows:
        if code in cfg.PILL_RECIPES_BY_CODE:
            recipe = cfg.PILL_RECIPES_BY_CODE[code]
            result.append({**recipe, "qty": qty})
    return result


def get_pill_inventory_qty(user_id, pill_code):
    row = get_user_db().execute(
        "SELECT qty FROM game_pills WHERE user_id = ? AND pill_code = ?", (user_id, pill_code)
    ).fetchone()
    return row[0] if row else 0


def consume_pill(user_id, pill_code, qty):
    if qty <= 0:
        raise ValueError("Số lượng đan phải lớn hơn 0")
    db = get_user_db()
    updated = db.execute(
        "UPDATE game_pills SET qty = qty - ? WHERE user_id = ? AND pill_code = ? AND qty >= ?",
        (qty, user_id, pill_code, qty),
    )
    if updated.rowcount != 1:
        return False
    db.execute("DELETE FROM game_pills WHERE user_id = ? AND pill_code = ? AND qty = 0", (user_id, pill_code))
    db.commit()
    return True


def can_craft_pill(recipe_code, user_id, realm_idx):
    """Kiểm tra điều kiện luyện đan.
    
    Trả về (ok, reason_if_not_ok)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại"
    
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    db = get_user_db()
    
    # 1. Kiểm tra có công thức
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if not has_recipe:
        return False, "Chưa mua công thức này"
    
    # 2. Kiểm tra tu vi
    if realm_idx < recipe["min_realm"]:
        need_words = cfg.SUB_THRESHOLDS[recipe["min_realm"] * 3]
        return False, f"Cần tu vi {cfg.MAJOR_REALMS[recipe['min_realm']]} (≈ {need_words} từ)"
    
    return True, None


def craft_pill(recipe_code, user_id, realm_idx, ingredients, rng=random):
    """Luyện một viên đan sau khi ghép đủ nguyên liệu."""
    # Kiểm tra điều kiện
    ok, reason = can_craft_pill(recipe_code, user_id, realm_idx)
    if not ok:
        return False, reason
    
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    
    if ingredients < recipe["ingredients"]:
        return False, f"Cần {recipe['ingredients']} nguyên liệu."
    
    # Tính toán thành công
    roll = rng.random()
    success = roll < recipe["success_rate"]
    
    if success:
        # Thêm đan vào kho
        add_pill(user_id, recipe_code, 1)
        message = f"✅ Luyện đan thành công! Nhận 1x {recipe['name']}"
    else:
        message = f"❌ Luyện đan thất bại. Nguyên liệu đã bị tiêu hao."
    
    return success, message


def add_pill(user_id, pill_code, qty):
    """Thêm đan dược vào kho."""
    db = get_user_db()
    db.execute(
        "INSERT INTO game_pills (user_id, pill_code, qty) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, pill_code) DO UPDATE SET qty = qty + excluded.qty",
        (user_id, pill_code, qty)
    )
    db.commit()


def buy_pill_recipe(recipe_code, user_id, linh_thach):
    """Mua công thức luyện đan.
    
    Trả về (success, message, linh_thach_after)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại", linh_thach
    
    db = get_user_db()
    profile = db.execute("SELECT linh_thach FROM game_profile WHERE user_id = ?", (user_id,)).fetchone()
    if not profile:
        return False, "Không tìm thấy tài khoản trò chơi", linh_thach
    linh_thach = profile[0]
    
    # Kiểm tra đã mua chưa
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if has_recipe:
        return False, "Đã mua công thức này rồi", linh_thach
    
    # Kiểm tra có đủ tiền
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    price = cfg.PILL_RECIPE_PRICES.get(recipe_code, 0)
    
    if linh_thach < price:
        missing = price - linh_thach
        return False, f"Thiếu Linh Thạch: cần {price}, có {linh_thach} (thiếu {missing})", linh_thach
    
    # Mua công thức
    db.batch([
        ("UPDATE game_profile SET linh_thach = linh_thach - ? WHERE user_id = ? AND linh_thach >= ?",
         (price, user_id, price)),
        ("INSERT INTO game_pill_recipes (user_id, recipe_code) SELECT ?, ? WHERE changes() = 1",
         (user_id, recipe_code)),
    ])
    if not db.execute("SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
                      (user_id, recipe_code)).fetchone():
        return False, "Không đủ Linh Thạch để mua công thức", linh_thach
    
    linh_thach_after = linh_thach - price
    return True, f"✅ Mua công thức {recipe['name']} thành công!", linh_thach_after


def get_pill_recipes_owned(user_id):
    """Lấy danh sách công thức mà người chơi đã mua."""
    remove_legacy_pills(user_id)
    db = get_user_db()
    rows = db.execute(
        "SELECT recipe_code FROM game_pill_recipes WHERE user_id = ? ORDER BY recipe_code",
        (user_id,)
    ).fetchall()
    result = []
    for (code,) in rows:
        if code in cfg.PILL_RECIPES_BY_CODE:
            result.append(cfg.PILL_RECIPES_BY_CODE[code])
    return result


def remove_legacy_pills(user_id):
    db = get_user_db()
    codes = tuple(f"pill_{i}" for i in range(1, 6))
    placeholders = ", ".join("?" for _ in codes)
    for table, column in (("game_pill_recipes", "recipe_code"), ("game_pills", "pill_code")):
        db.execute(f"DELETE FROM {table} WHERE user_id = ? AND {column} IN ({placeholders})", (user_id, *codes))
    db.commit()


def get_words_learned_count(user_id):
    """Lấy số từ đã học (status = MASTERED hoặc REVIEW)."""
    db = get_user_db()
    row = db.execute(
        "SELECT COUNT(*) FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchone()
    return row[0] if row else 0

# ---------------------------------------------------------------------------
# Phiên 6: Vẽ Phù (Talisman System)
# ---------------------------------------------------------------------------

def buy_talisman_recipe(user_id, recipe_code):
    """Mua công thức phù (một lần duy nhất)."""
    if recipe_code not in cfg.TALISMAN_RECIPES_BY_CODE:
        return False, "Công thức phù không tồn tại!", 0
    
    recipe = cfg.TALISMAN_RECIPES_BY_CODE[recipe_code]
    price = cfg.TALISMAN_RECIPE_PRICES.get(recipe_code, 0)
    
    db = get_user_db()
    
    # Kiểm tra đã sở hữu công thức chưa
    existing = db.execute(
        "SELECT recipe_code FROM game_talisman_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    
    if existing:
        return False, f"Bạn đã mua công thức {recipe['name']} rồi!", 0
    
    # Lấy Linh Thạch hiện tại
    profile = db.execute(
        "SELECT linh_thach FROM game_profile WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    linh_thach = profile[0] if profile else 0
    
    if linh_thach < price:
        return False, f"Không đủ Linh Thạch! Cần {price}, có {linh_thach}.", linh_thach
    
    # Trừ tiền và lưu công thức
    db.batch([
        ("UPDATE game_profile SET linh_thach = linh_thach - ? WHERE user_id = ? AND linh_thach >= ?",
         (price, user_id, price)),
        ("INSERT INTO game_talisman_recipes (user_id, recipe_code) SELECT ?, ? WHERE changes() = 1",
         (user_id, recipe_code)),
    ])
    if not db.execute("SELECT 1 FROM game_talisman_recipes WHERE user_id = ? AND recipe_code = ?",
                      (user_id, recipe_code)).fetchone():
        return False, "Không đủ Linh Thạch để mua công thức", linh_thach
    
    linh_thach_after = linh_thach - price
    return True, f"✅ Mua công thức {recipe['name']} thành công!", linh_thach_after


def get_talisman_recipes_owned(user_id):
    """Lấy danh sách công thức phù đã mua."""
    remove_legacy_talismans(user_id)
    db = get_user_db()
    rows = db.execute(
        "SELECT recipe_code FROM game_talisman_recipes WHERE user_id = ? ORDER BY recipe_code",
        (user_id,)
    ).fetchall()
    result = []
    for (code,) in rows:
        if code in cfg.TALISMAN_RECIPES_BY_CODE:
            result.append(cfg.TALISMAN_RECIPES_BY_CODE[code])
    return result


def get_talismans_inventory(user_id):
    """Lấy kho phù."""
    remove_legacy_talismans(user_id)
    db = get_user_db()
    rows = db.execute(
        "SELECT talisman_code, qty FROM game_talismans WHERE user_id = ? AND qty > 0 ORDER BY talisman_code",
        (user_id,)
    ).fetchall()
    result = []
    for code, qty in rows:
        if code in cfg.TALISMAN_RECIPES_BY_CODE:
            talisman = cfg.TALISMAN_RECIPES_BY_CODE[code]
            result.append({**talisman, "qty": qty})
    return result


def remove_legacy_talismans(user_id):
    """Xóa công thức và phù của hệ thống cũ, không ảnh hưởng mã phù mới."""
    db = get_user_db()
    codes = tuple(f"talisman_{i}" for i in range(1, 7))
    placeholders = ", ".join("?" for _ in codes)
    for table, column in (("game_talisman_recipes", "recipe_code"), ("game_talismans", "talisman_code")):
        db.execute(f"DELETE FROM {table} WHERE user_id = ? AND {column} IN ({placeholders})", (user_id, *codes))
    db.commit()


def talisman_word(user_id, course, pool, advance=False, rng=random):
    """Duy trì vòng từ đã học riêng cho người chơi và khóa học."""
    if not pool:
        raise ValueError("Kho từ đã học đang trống")
    db = get_user_db()
    row = db.execute("SELECT data FROM game_talisman_words WHERE user_id = ? AND course = ?",
                     (user_id, course)).fetchone()
    data = json.loads(row[0]) if row else {"remaining": [], "seen": []}
    words = {word["id"]: word for word in pool}
    remaining = [wid for wid in data["remaining"] if wid in words]
    seen = [wid for wid in data["seen"] if wid in words]
    if advance and remaining:
        seen.append(remaining.pop(0))
    known = set(remaining) | set(seen)
    added = [wid for wid in words if wid not in known]
    rng.shuffle(added)
    remaining.extend(added)
    if not remaining:
        remaining = list(words)
        rng.shuffle(remaining)
        seen = []
    data = {"remaining": remaining, "seen": seen}
    db.execute(
        "INSERT INTO game_talisman_words (user_id, course, data) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, course) DO UPDATE SET data = excluded.data",
        (user_id, course, json.dumps(data)),
    )
    db.commit()
    return words[remaining[0]]


def craft_talisman(user_id, recipe_code, words_learned=None):
    """Xây dựng phù (sau khi hoàn thành mini-game)."""
    if recipe_code not in cfg.TALISMAN_RECIPES_BY_CODE:
        return {"success": False, "error": "INVALID_RECIPE", "message": "Công thức phù không tồn tại!"}
    
    recipe = cfg.TALISMAN_RECIPES_BY_CODE[recipe_code]
    db = get_user_db()
    
    # Kiểm tra sở hữu công thức
    owned = db.execute(
        "SELECT recipe_code FROM game_talisman_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    
    if not owned:
        return {"success": False, "error": "RECIPE_NOT_OWNED", "message": "Bạn chưa mua công thức này!"}
    
    # Kiểm tra tu vi
    if words_learned is None:
        words_learned = get_words_learned_count(user_id)
    realm = realm_info(words_learned)
    
    if realm["idx"] < recipe["min_realm"]:
        return {
            "success": False, 
            "error": "REALM_TOO_LOW",
            "message": f"Cần tu vi {cfg.MAJOR_REALMS[recipe['min_realm']]} trở lên!"
        }
    
    # Lưu phù vào kho
    db.execute(
        "INSERT INTO game_talismans (user_id, talisman_code, qty) VALUES (?, ?, 1) "
        "ON CONFLICT(user_id, talisman_code) DO UPDATE SET qty = qty + 1",
        (user_id, recipe_code)
    )
    
    # Cập nhật counter số lần gõ đúng
    db.execute(
        "INSERT INTO game_counters (user_id, key, value) VALUES (?, ?, ?) "
        "ON CONFLICT(user_id, key) DO UPDATE SET value = value + ?",
        (user_id, f"talisman_{recipe_code}_hits", recipe["correct_hits_needed"], recipe["correct_hits_needed"])
    )
    
    db.commit()
    
    return {
        "success": True,
        "talisman_code": recipe_code,
        "talisman_name": recipe["name"],
        "message": f"✅ Xây dựng phù {recipe['name']} thành công!"
    }


def get_talisman_inventory_qty(user_id, talisman_code):
    """Lấy số lượng phù trong kho."""
    db = get_user_db()
    row = db.execute(
        "SELECT qty FROM game_talismans WHERE user_id = ? AND talisman_code = ?",
        (user_id, talisman_code)
    ).fetchone()
    return row[0] if row else 0


def consume_talisman(user_id, talisman_code, qty=1):
    """Tiêu hao phù (khi sử dụng trong trận)."""
    if qty <= 0:
        raise ValueError("Số lượng phù phải lớn hơn 0")
    db = get_user_db()
    updated = db.execute(
        "UPDATE game_talismans SET qty = qty - ? WHERE user_id = ? AND talisman_code = ? AND qty >= ?",
        (qty, user_id, talisman_code, qty),
    )
    if updated.rowcount != 1:
        return False
    db.execute("DELETE FROM game_talismans WHERE user_id = ? AND talisman_code = ? AND qty = 0",
               (user_id, talisman_code))
    db.commit()
    return True


# ---------------------------------------------------------------------------
# Phiên 7: Sử dụng vật phẩm trong trận đấu
# ---------------------------------------------------------------------------

def get_usable_pills(user_id):
    """Lấy danh sách đan dược có thể sử dụng."""
    return get_pills_inventory(user_id)


def get_usable_talismans(user_id):
    """Lấy danh sách phù có thể sử dụng."""
    talismans = get_talismans_inventory(user_id)
    usable = []
    for talisman in talismans:
        if talisman["code"] in cfg.TALISMAN_RECIPES_BY_CODE:
            recipe = cfg.TALISMAN_RECIPES_BY_CODE[talisman["code"]]
            usable.append({
                "code": talisman["code"],
                "name": recipe["name"],
                "qty": talisman["qty"],
                "description": recipe["description"],
                "effects": recipe["effects"],
                "duration": 1
            })
    return usable


def use_pill_in_battle(battle_state, pill_code, user_id, realm_idx):
    """Sử dụng đan dược trong trận đấu."""
    recipe = cfg.PILL_RECIPES_BY_CODE.get(pill_code)
    if not recipe:
        return False, "Đan dược không tồn tại!"
    if battle_state.get("over") or battle_state.get("revive_pending") or battle_state["php"] <= 0:
        return False, "Không thể dùng đan lúc này."
    if realm_idx < recipe["min_realm"]:
        return False, f"Cần đạt {cfg.MAJOR_REALMS[recipe['min_realm']]}."
    if not recipe["heal"]:
        return False, "Đan hồi sinh chỉ dùng khi bị đánh bại."
    if battle_state["php"] >= battle_state["pmax"]:
        return False, "HP đã đầy."
    if not consume_pill(user_id, pill_code, 1):
        return False, "Không còn đan này trong kho."
    restored = min(recipe["heal"], battle_state["pmax"] - battle_state["php"])
    battle_state["php"] += restored
    return True, f"💊 {recipe['name']} hồi {restored:.0f} HP."


def talisman_battle_error(battle_state, talisman_code):
    recipe = cfg.TALISMAN_RECIPES_BY_CODE.get(talisman_code)
    if not recipe:
        return "Phù không tồn tại!"
    if battle_state.get("over") or battle_state.get("stage") != "fight" or not battle_state.get("monster"):
        return "Không thể sử dụng phù lúc này."
    if battle_state.get("talismans_used", 0) >= 2:
        return "Mỗi trận chỉ được dùng tối đa 2 phù."
    if recipe["effects"]["boss_only"] and not battle_state["monster"]["boss"]:
        return "Phù này chỉ dùng được với boss."
    return None


def use_talisman_in_battle(battle_state, talisman_code):
    """Gây một đòn phụ và thêm lượt chắn; việc tiêu hao được xử lý bởi người gọi."""
    error = talisman_battle_error(battle_state, talisman_code)
    if error:
        return False, error
    recipe = cfg.TALISMAN_RECIPES_BY_CODE[talisman_code]
    effects = recipe["effects"]
    battle_state["talismans_used"] = battle_state.get("talismans_used", 0) + 1
    battle_state["talisman_shield"] = battle_state.get("talisman_shield", 0) + effects["shield"]
    damage = battle_state["base_atk"] * effects["damage_pct"] / 100
    monster = battle_state["monster"]
    monster["hp"] = max(0.0, monster["hp"] - damage)
    return True, (f"🪬 {recipe['name']} gây **{damage:.2f}** sát thương"
                  + (" và chắn 1 đòn tiếp theo." if effects["shield"] else "."))


def get_active_item_effects(battle_state):
    """Lấy tất cả hiệu ứng từ vật phẩm hiện tại đang hoạt động."""
    effects = {
        "atk_bonus_pct": 0.0,
        "damage_reduction": 0.0,
        "hp_restore": 0.0,
        "reflect_damage": 0.0,
        "crit_bonus": 0.0,
    }
    
    active = battle_state.get("active_items", {})
    
    # Tính hiệu ứng đan
    for pill in active.get("pills", []):
        effects["atk_bonus_pct"] += pill.get("effects", 0)
    
    # Tính hiệu ứng phù
    for talisman in active.get("talismans", []):
        tali_effects = talisman.get("effects", {})
        effects["atk_bonus_pct"] += tali_effects.get("atk_bonus_pct", 0) / 100.0
        effects["damage_reduction"] += tali_effects.get("damage_reduction", 0) / 100.0
        effects["hp_restore"] += tali_effects.get("hp_restore_pct", 0) / 100.0
        effects["reflect_damage"] += tali_effects.get("reflect_damage_pct", 0) / 100.0
        effects["crit_bonus"] += tali_effects.get("crit_chance_bonus", 0) / 100.0
    
    return effects


# ---------------------------------------------------------------------------
# Phiên 7: Cửu chuyển hoàn hồn đan (Revival Pill)
# ---------------------------------------------------------------------------

def has_revival_pill(user_id):
    """Kiểm tra người chơi có Cửu chuyển hoàn hồn đan không."""
    qty = get_pill_inventory_qty(user_id, cfg.REVIVAL_PILL_CODE)
    return qty > 0


def use_revival_pill(user_id, battle_state):
    """Sử dụng Cửu chuyển hoàn hồn đan để hồi sinh."""
    if not has_revival_pill(user_id):
        return False, "Không có Cửu chuyển hoàn hồn đan!"
    
    # Tiêu hao 1 viên đan
    if not battle_state.get("revive_pending"):
        return False, "Chỉ có thể hồi sinh sau khi bị đánh bại!"
    if not consume_pill(user_id, cfg.REVIVAL_PILL_CODE, 1):
        return False, "Không thể sử dụng đan!"
    
    # Hồi sinh: hồi 50% HP và tiếp tục trận
    max_hp = battle_state.get("pmax", 100)
    restore_hp = max_hp * 0.5
    battle_state["php"] = restore_hp
    battle_state["revive_pending"] = False
    
    # Ghi chép hồi sinh
    battle_state["log"].append(f"✨ Cửu chuyển hoàn hồn đan kích hoạt! Hồi sinh với {restore_hp:.0f} HP!")
    
    return True, "Hồi sinh thành công!"

# ---------------------------------------------------------------------------
# Phiên 5: Mini-game Luyện Đan
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Phiên 8: Công Pháp (Tâm Pháp & Bí Pháp) - Rơi từ Boss
# ---------------------------------------------------------------------------

def roll_technique(realm_idx, rng=random):
    """Quay công pháp rơi từ boss theo cảnh giới.
    
    Trả về: (technique_code, technique_grade) hoặc (None, None) nếu không rơi.
    """
    # Lấy config rơi theo cảnh giới
    drop_config = cfg.TECHNIQUE_DROP_RATES.get(realm_idx, cfg.TECHNIQUE_DROP_RATES.get(15))
    drop_rate = drop_config["rate"]
    available_grades = drop_config["grades"]
    
    # Kiểm tra rơi
    if rng.random() > drop_rate:
        return None, None
    
    # Chọn cấp độ công pháp
    grade = rng.choice(available_grades)
    
    # Chọn loại công pháp (50% tâm pháp, 50% bí pháp)
    kind = rng.choice(["heart", "secret"])
    
    # Lấy danh sách công pháp theo loại + cấp
    techniques = [t for t in cfg.TECHNIQUES if t["kind"] == kind and t["grade"] == grade]
    if not techniques:
        return None, None
    
    technique = rng.choice(techniques)
    return technique["code"], grade


def add_technique(user_id, technique_code):
    """Thêm công pháp vào kho người chơi.
    
    Trả về: technique_id hoặc -1 nếu lỗi.
    """
    if technique_code not in cfg.TECHNIQUE_BY_CODE:
        return -1
    
    db = get_user_db()
    cursor = db.execute(
        "INSERT INTO game_techniques (user_id, technique_code) VALUES (?, ?)",
        (user_id, technique_code)
    )
    db.commit()
    return cursor.lastrowid


def get_techniques_inventory(user_id):
    """Lấy danh sách công pháp sở hữu (bao gồm vị trí đan điền nếu có)."""
    db = get_user_db()
    rows = db.execute(
        "SELECT id, technique_code, dantian_row, dantian_col, is_equipped FROM game_techniques WHERE user_id = ? ORDER BY acquired_at DESC",
        (user_id,)
    ).fetchall()
    
    techniques = []
    for row_id, code, row, col, equipped in rows:
        technique = cfg.TECHNIQUE_BY_CODE[code]
        techniques.append({
            "id": row_id,
            "code": code,
            "name": technique["name"],
            "kind": technique["kind"],
            "grade": technique["grade"],
            "emoji": technique["emoji"],
            "dantian_row": row,
            "dantian_col": col,
            "is_equipped": equipped,
            "hp_mult": technique["hp_mult"],
            "atk_mult": technique["atk_mult"],
        })
    return techniques


def place_technique_in_dantian(user_id, technique_id, dantian_row, dantian_col):
    """Đặt công pháp vào vị trí trong đan điền (grid-based inventory).
    
    Trả về: (success, message)
    """
    # Kiểm tra bounds
    if not (0 <= dantian_row < cfg.DANTIAN_ROWS and 0 <= dantian_col < cfg.DANTIAN_COLS):
        return False, "Vị trí không hợp lệ"
    
    # Kiểm tra sở hữu
    db = get_user_db()
    tech = db.execute(
        "SELECT technique_code FROM game_techniques WHERE id = ? AND user_id = ?",
        (technique_id, user_id)
    ).fetchone()
    if not tech:
        return False, "Công pháp không tồn tại"
    
    # Kiểm tra vị trí đã có công pháp chưa
    existing = db.execute(
        "SELECT id FROM game_techniques WHERE user_id = ? AND dantian_row = ? AND dantian_col = ? AND id != ?",
        (user_id, dantian_row, dantian_col, technique_id)
    ).fetchone()
    if existing:
        return False, "Ô này đã có công pháp khác"
    
    # Đặt công pháp
    db.execute(
        "UPDATE game_techniques SET dantian_row = ?, dantian_col = ? WHERE id = ? AND user_id = ?",
        (dantian_row, dantian_col, technique_id, user_id)
    )
    db.commit()
    
    return True, "Đặt công pháp thành công"


def remove_technique_from_dantian(user_id, technique_id):
    """Tháo công pháp khỏi đan điền."""
    db = get_user_db()
    db.execute(
        "UPDATE game_techniques SET dantian_row = -1, dantian_col = -1 WHERE id = ? AND user_id = ?",
        (technique_id, user_id)
    )
    db.commit()
    return True, "Tháo công pháp thành công"


def equip_technique(user_id, technique_id, slot):
    """Trang bị công pháp vào slot (1 hoặc 2).
    
    Trả về: (success, message)
    """
    if slot not in (1, 2):
        return False, "Slot không hợp lệ (1 hoặc 2)"
    
    # Kiểm tra sở hữu
    db = get_user_db()
    tech = db.execute(
        "SELECT technique_code FROM game_techniques WHERE id = ? AND user_id = ?",
        (technique_id, user_id)
    ).fetchone()
    if not tech:
        return False, "Công pháp không tồn tại"
    
    # Trang bị
    slot_key = f"technique_slot_{slot}"
    db.execute(
        "INSERT OR REPLACE INTO game_techniques_equipped (user_id, {}) VALUES (?, ?)".format(slot_key),
        (user_id, technique_id)
    )
    db.execute(
        "UPDATE game_techniques SET is_equipped = 1 WHERE id = ? AND user_id = ?",
        (technique_id, user_id)
    )
    db.commit()
    
    return True, f"Trang bị công pháp vào slot {slot}"


def unequip_technique(user_id, slot):
    """Tháo công pháp khỏi slot."""
    if slot not in (1, 2):
        return False, "Slot không hợp lệ"
    
    db = get_user_db()
    
    # Lấy technique_id hiện tại
    slot_key = f"technique_slot_{slot}"
    current = db.execute(
        "SELECT {} FROM game_techniques_equipped WHERE user_id = ?".format(slot_key),
        (user_id,)
    ).fetchone()
    
    if current and current[0]:
        tech_id = current[0]
        db.execute(
            "UPDATE game_techniques SET is_equipped = 0 WHERE id = ?",
            (tech_id,)
        )
    
    # Xóa trang bị
    db.execute(
        "UPDATE game_techniques_equipped SET {} = NULL WHERE user_id = ?".format(slot_key),
        (user_id,)
    )
    db.commit()
    
    return True, f"Tháo công pháp khỏi slot {slot}"


def get_equipped_techniques(user_id):
    """Lấy danh sách công pháp đang trang bị."""
    db = get_user_db()
    row = db.execute(
        "SELECT technique_slot_1, technique_slot_2 FROM game_techniques_equipped WHERE user_id = ?",
        (user_id,)
    ).fetchone()
    
    equipped = {"slot_1": None, "slot_2": None}
    if row:
        for slot_idx, tech_id in enumerate([row[0], row[1]], 1):
            if tech_id:
                tech = db.execute(
                    "SELECT technique_code FROM game_techniques WHERE id = ?",
                    (tech_id,)
                ).fetchone()
                if tech:
                    technique = cfg.TECHNIQUE_BY_CODE[tech[0]]
                    equipped[f"slot_{slot_idx}"] = {
                        "id": tech_id,
                        "code": tech[0],
                        "name": technique["name"],
                        "hp_mult": technique["hp_mult"],
                        "atk_mult": technique["atk_mult"],
                    }
    
    return equipped



def bin_pack_techniques(user_id):
    """Tự động sắp xếp công pháp gọn gàng vào đan điền."""
    from userdb import get_user_db
    db = get_user_db()
    
    # Lấy công pháp chưa đặt
    unplaced = db.execute("""
        SELECT id, technique_code FROM game_techniques 
        WHERE user_id = ? AND dantian_row = -1
        ORDER BY id
    """, (user_id,)).fetchall()
    
    if not unplaced:
        return True, "Không có công pháp chưa đặt"
    
    # Khởi tạo grid
    grid = [[-1 for _ in range(cfg.DANTIAN_COLS)] for _ in range(cfg.DANTIAN_ROWS)]
    
    # Đặt công pháp đã có
    placed = db.execute("""
        SELECT id, technique_code, dantian_row, dantian_col FROM game_techniques
        WHERE user_id = ? AND dantian_row >= 0
    """, (user_id,)).fetchall()
    
    for tech_id, tech_code, row, col in placed:
        size = cfg.TECHNIQUE_BY_CODE[tech_code]["size"]
        for r in range(row, row + size[0]):
            for c in range(col, col + size[1]):
                if 0 <= r < cfg.DANTIAN_ROWS and 0 <= c < cfg.DANTIAN_COLS:
                    grid[r][c] = tech_id
    
    # Xếp công pháp chưa đặt
    updated = 0
    for tech_id, tech_code in unplaced:
        size = cfg.TECHNIQUE_BY_CODE[tech_code]["size"]
        for row in range(cfg.DANTIAN_ROWS):
            for col in range(cfg.DANTIAN_COLS):
                if row + size[0] <= cfg.DANTIAN_ROWS and col + size[1] <= cfg.DANTIAN_COLS:
                    ok = all(grid[r][c] == -1 for r in range(row, row + size[0]) for c in range(col, col + size[1]))
                    if ok:
                        for r in range(row, row + size[0]):
                            for c in range(col, col + size[1]):
                                grid[r][c] = tech_id
                        db.execute("UPDATE game_techniques SET dantian_row = ?, dantian_col = ? WHERE id = ?", (row, col, tech_id))
                        db.commit()
                        updated += 1
                        break
            else:
                continue
            break
    
    return True, f"✅ Sắp xếp {updated} công pháp"



def calc_technique_bonus(user_id):
    """Tính tổng bonus từ công pháp trang bị (có tính kích thước)."""
    equipped = get_equipped_techniques(user_id)
    bonus = {"hp_mult": 0.0, "atk_mult": 0.0}
    
    for slot in ["slot_1", "slot_2"]:
        tech = equipped[slot]
        if tech:
            size = tech.get("size", (1, 1))
            size_mult = cfg.TECHNIQUE_SIZE_MULT.get(size, 1.0)
            bonus["hp_mult"] += tech["hp_mult"] * size_mult
            bonus["atk_mult"] += tech["atk_mult"] * size_mult
    
    return bonus
