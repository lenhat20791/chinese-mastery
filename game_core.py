"""Lõi trò chơi tu tiên: trạng thái người chơi (lưu DB, cache trong session), kinh tế, chế tạo, huy hiệu, quẻ bói."""
import bisect
import datetime
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
    db = get_user_db()
    rows = db.execute(
        "SELECT pill_code, qty FROM game_pills WHERE user_id = ? AND qty > 0 ORDER BY pill_code",
        (user_id,)
    ).fetchall()
    result = []
    for code, qty in rows:
        if code in cfg.PILL_RECIPES_BY_CODE:
            recipe = cfg.PILL_RECIPES_BY_CODE[code]
            result.append({"code": code, "name": recipe["name"], "qty": qty, "bonus": recipe["bonus_atk_pct"]})
    return result


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
        need_words = cfg.SUB_THRESHOLDS[recipe["min_realm"] * 3] if recipe["min_realm"] * 3 < len(cfg.SUB_THRESHOLDS) else 2500
        return False, f"Cần tu vi Realm {recipe['min_realm']} (≈ {need_words} từ)"
    
    # 3. Kiểm tra nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        qty_have = get_inventory_qty(user_id, mat_code)
        if qty_have < qty_need:
            mat_name = cfg.ITEM_NAMES.get(mat_code, mat_code)
            return False, f"Thiếu {mat_name}: cần {qty_need}, có {qty_have}"
    
    return True, None


def craft_pill(recipe_code, user_id, realm_idx, rng=random):
    """Luyện một viên đan.
    
    1. Kiểm tra điều kiện
    2. Tiêu hao nguyên liệu
    3. Tính xác suất thành công
    4. Cập nhật kho
    
    Trả về (success, message)
    """
    # Kiểm tra điều kiện
    ok, reason = can_craft_pill(recipe_code, user_id, realm_idx)
    if not ok:
        return False, reason
    
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    
    # Tiêu hao nguyên liệu
    for mat_code, qty_need in recipe["materials"]:
        if not consume_inventory(user_id, mat_code, qty_need):
            return False, f"Lỗi: không thể tiêu hao {cfg.ITEM_NAMES.get(mat_code, mat_code)}"
    
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
    current = db.execute(
        "SELECT qty FROM game_pills WHERE user_id = ? AND pill_code = ?",
        (user_id, pill_code)
    ).fetchone()
    
    new_qty = (current[0] if current else 0) + qty
    db.execute(
        "INSERT OR REPLACE INTO game_pills (user_id, pill_code, qty) VALUES (?, ?, ?)",
        (user_id, pill_code, new_qty)
    )
    db.commit()


def buy_pill_recipe(recipe_code, user_id, linh_thach):
    """Mua công thức luyện đan.
    
    Trả về (success, message, linh_thach_after)
    """
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại", linh_thach
    
    db = get_user_db()
    
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
    db.execute(
        "INSERT INTO game_pill_recipes (user_id, recipe_code) VALUES (?, ?)",
        (user_id, recipe_code)
    )
    db.commit()
    
    linh_thach_after = linh_thach - price
    return True, f"✅ Mua công thức {recipe['name']} thành công!", linh_thach_after


def get_pill_recipes_owned(user_id):
    """Lấy danh sách công thức mà người chơi đã mua."""
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


def get_words_learned_count(user_id):
    """Lấy số từ đã học (status = MASTERED hoặc REVIEW)."""
    db = get_user_db()
    row = db.execute(
        "SELECT COUNT(*) FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchone()
    return row[0] if row else 0
# ---------------------------------------------------------------------------
# Phiên 5: Mini-game Luyện Đan
# ---------------------------------------------------------------------------

def build_alchemist_pool(user_id, recipe_code):
    """Tạo pool từ cho mini-game luyện đan.
    
    Ưu tiên từ đã học; nếu > 30 từ đã học, giữ tất cả; bổ sung từ chưa học.
    
    Trả về: [vocab_id, ...]
    """
    # Lấy số từ đã học
    db = get_user_db()
    learned = db.execute(
        "SELECT vocab_id FROM word_mastery WHERE user_id = ? AND last_status IN ('MASTERED', 'REVIEW')",
        (user_id,)
    ).fetchall()
    learned_ids = [row[0] for row in learned]
    
    # Lấy cần bao nhiêu từ từ công thức
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    pairs_needed = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    words_needed = pairs_needed
    
    # Tạo pool
    pool = []
    
    if len(learned_ids) >= words_needed:
        # Đủ từ đã học, lấy words_needed từ đầu tiên
        pool = learned_ids[:words_needed]
    else:
        # Chưa đủ, lấy tất cả từ đã học + bổ sung từ chưa học
        pool = learned_ids[:]
        
        # Lấy từ chưa học
        unlearned = db.execute(
            "SELECT vocab_id FROM word_mastery WHERE user_id = ? AND last_status NOT IN ('MASTERED', 'REVIEW')",
            (user_id,)
        ).fetchall()
        unlearned_ids = [row[0] for row in unlearned]
        
        # Bổ sung
        needed_more = words_needed - len(pool)
        if needed_more > 0:
            pool.extend(unlearned_ids[:needed_more])
    
    return pool[:words_needed]


def start_alchemist_game(user_id, recipe_code):
    """Bắt đầu mini-game luyện đan."""
    if recipe_code not in cfg.PILL_RECIPES_BY_CODE:
        return False, "Công thức không tồn tại"
    
    # Kiểm tra có công thức
    db = get_user_db()
    has_recipe = db.execute(
        "SELECT 1 FROM game_pill_recipes WHERE user_id = ? AND recipe_code = ?",
        (user_id, recipe_code)
    ).fetchone()
    if not has_recipe:
        return False, "Không có công thức này"
    
    # Xây dựng pool từ
    pool = build_alchemist_pool(user_id, recipe_code)
    
    if not pool:
        return False, "Không đủ từ để chơi"
    
    # Lưu trạng thái game
    state = get_state()
    state["alchemist"] = {
        "recipe": recipe_code,
        "pool": pool,
        "matched": [],
    }
    set_state(state)
    
    return True, "Bắt đầu mini-game"


def match_alchemist_word(user_id, pair_index):
    """Xử lý khi người chơi ghép một cặp từ.
    
    pair_index: chỉ số cặp từ đã ghép
    """
    state = get_state()
    if state["alchemist"] is None:
        return False, "Không có game đang chơi"
    
    alchemist = state["alchemist"]
    recipe_code = alchemist["recipe"]
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    pairs_needed = cfg.ALCHEMIST_PAIRS_PER_RECIPE.get(recipe_code, 3)
    
    # Thêm vào matched
    if pair_index not in alchemist["matched"]:
        alchemist["matched"].append(pair_index)
    
    set_state(state)
    
    # Kiểm tra hoàn thành
    if len(alchemist["matched"]) >= pairs_needed:
        return True, f"✅ Ghép xong {pairs_needed} từ! Tiêu hao nguyên liệu và luyện đan..."
    else:
        remain = pairs_needed - len(alchemist["matched"])
        return None, f"Còn cần {remain} cặp từ"


def finish_alchemist_game(user_id, recipe_code):
    """Kết thúc mini-game luyện đan.
    
    1. Tiêu hao nguyên liệu
    2. Gọi craft_pill (Phiên 4)
    3. Làm sạch state
    """
    recipe = cfg.PILL_RECIPES_BY_CODE[recipe_code]
    words_learned = get_words_learned_count(user_id)
    realm_info_data = realm_info(words_learned)
    realm_idx = realm_info_data["idx"]
    
    # Luyện đan
    success, message = craft_pill(recipe_code, user_id, realm_idx)
    
    # Làm sạch game state
    state = get_state()
    state["alchemist"] = None
    set_state(state)
    
    return success, message


def reset_alchemist_game(user_id):
    """Reset mini-game (người chơi chọn công thức khác)."""
    state = get_state()
    state["alchemist"] = None
    set_state(state)
