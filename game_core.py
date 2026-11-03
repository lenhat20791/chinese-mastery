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


def play_multiplier(plays_before):
    if plays_before < cfg.DAILY_FULL_PLAYS:
        return 1.0
    if plays_before < cfg.DAILY_MID_PLAYS:
        return cfg.MULT_MID
    return cfg.MULT_LOW


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
    """(cộng công, cộng HP) của pháp bảo."""
    mult = cfg.QUALITY_MULT[quality] * (1 + cfg.UPGRADE_STAT_STEP * upgrade)
    base_atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** recipe["min_idx"]
    base_hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** recipe["min_idx"]
    return base_atk * cfg.ARTIFACT_ATK_RATIO * mult, base_hp * cfg.ARTIFACT_HP_RATIO * mult


def player_stats(idx, artifact=None):
    atk = cfg.PLAYER_BASE_ATK * cfg.POWER_PER_REALM ** idx
    hp = cfg.PLAYER_BASE_HP * cfg.POWER_PER_REALM ** idx
    if artifact:
        bonus_atk, bonus_hp = artifact_bonus(cfg.RECIPE_BY_CODE[artifact["recipe_code"]],
                                             artifact["quality"], artifact["upgrade"])
        atk += bonus_atk
        hp += bonus_hp
    return {"atk": atk, "hp": hp}


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
    return titles


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
    return {
        "uid": uid, "day": day,
        "ls": p[0], "equipped": p[1], "title": p[2], "pity_mid": p[3], "pity_high": p[4],
        "streak": p[5], "streak_day": p[6],
        "plays": plays[0] if plays else 0,
        "inventory": {r[0]: r[1] for r in cursors[2].fetchall() if r[1] > 0},
        "recipes": {r[0] for r in cursors[3].fetchall()},
        "artifacts": [{"id": r[0], "recipe_code": r[1], "quality": r[2], "upgrade": r[3]}
                      for r in cursors[4].fetchall()],
        "fortune": ({"vocab_id": fortune[0], "tier": fortune[1], "status": fortune[2], "buff": fortune[3]}
                    if fortune else None),
        "achievements": {r[0] for r in cursors[6].fetchall()},
        "counters": {r[0]: r[1] for r in cursors[7].fetchall()},
        "log": [{"ts": r[0], "kind": r[1], "text": r[2]} for r in cursors[8].fetchall()],
    }


def get_state(force=False):
    uid = current_user_id()
    state = st.session_state.get(STATE_KEY)
    if force or state is None or state["uid"] != uid or state["day"] != today():
        state = _load(uid)
        st.session_state[STATE_KEY] = state
    return state


def equipped_artifact(state):
    return next((a for a in state["artifacts"] if a["id"] == state["equipped"]), None)


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


def equip(artifact_id, idx):
    state = get_state()
    if artifact_id is not None:
        art = next((a for a in state["artifacts"] if a["id"] == artifact_id), None)
        if art is None:
            return False, "Không tìm thấy pháp bảo."
        recipe = cfg.RECIPE_BY_CODE[art["recipe_code"]]
        if idx < recipe["min_idx"]:
            return False, f"Cần đạt {cfg.MAJOR_REALMS[recipe['min_idx']]} để dùng pháp bảo này."
    apply_changes(extra=[("UPDATE game_profile SET equipped_artifact = ? WHERE user_id = ?",
                          (artifact_id, state["uid"]))])
    return True, "Đã thay đổi pháp bảo trang bị."


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


def current_multiplier():
    return play_multiplier(get_state()["plays"])


def settle(base_ls, idx_scale, words_learned, results=(), incr=None, maxes=None, items=None, log=None,
           count_play=True, record=True):
    """Chốt một lượt chơi: tính Linh Thạch theo lượt trong ngày, ghi kết quả ôn, huy hiệu. Trả về (ls, mult, huy hiệu mới)."""
    from database import record_review_batch

    state = get_state()
    mult = play_multiplier(state["plays"])
    ls = reward_ls(base_ls, mult, state, idx_scale) if base_ls > 0 else 0
    if record and results:
        record_review_batch(list(results))
    incr = dict(incr or {})
    hour = local_hour()
    if hour >= cfg.NIGHT_HOUR or hour < 4:
        incr["night_plays"] = 1
    apply_changes(ls=ls, items=items, incr=incr, maxes=maxes, log=log, plays=1 if count_play else 0)
    return ls, mult, check_achievements(words_learned)


def equip_title(code):
    state = get_state()
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
