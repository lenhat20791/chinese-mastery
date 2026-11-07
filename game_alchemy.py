"""Ghép Hán tự, pinyin và nghĩa để tạo nguyên liệu luyện đan."""
import random
from pathlib import Path

import streamlit as st

import game_config as cfg
import game_core as core
import game_questions as gq
import game_ui
from course_config import get_config
from database import active_variant, get_db


@st.cache_data(show_spinner=False)
def all_words(variant):
    db = get_db(variant)
    try:
        return [dict(row) for row in db.execute("SELECT * FROM vocab").fetchall()]
    finally:
        db.close()


def build_board(learned, vocabulary, rng=random):
    def valid(word):
        return bool(word.get("hanzi") and word.get("pinyin") and gq.short_meaning(word))

    learned = [w for w in learned if valid(w)]
    learned_ids = {w["id"] for w in learned}
    unlearned = [w for w in vocabulary if w["id"] not in learned_ids and valid(w)]
    selected = rng.sample(learned, min(len(learned), cfg.ALCHEMIST_BOARD_WORDS))
    count = min(len(unlearned), cfg.ALCHEMIST_BOARD_WORDS - len(selected))
    selected += rng.sample(unlearned, count)
    if not selected:
        raise ValueError("Kho từ không có từ đủ Hán tự, pinyin và nghĩa để luyện đan.")
    cards = []
    for word in selected:
        for kind, text in (("hanzi", word["hanzi"]), ("pinyin", word["pinyin"]),
                           ("meaning", gq.short_meaning(word))):
            cards.append({"kind": kind, "text": text, "status": "idle"})
    rng.shuffle(cards)
    answers = [{kind: text for kind, text in (("hanzi", w["hanzi"]), ("pinyin", w["pinyin"]),
                                                ("meaning", gq.short_meaning(w)))} for w in selected]
    return {"cards": cards, "answers": answers, "selected": []}


def board_has_match(board):
    available = {kind: {c["text"] for c in board["cards"] if c["kind"] == kind and c["status"] == "idle"}
                 for kind in ("hanzi", "pinyin", "meaning")}
    return any(all(answer[kind] in available[kind] for kind in available) for answer in board["answers"])


def choose_card(game, index):
    board = game["board"]
    card = board["cards"][index]
    if card["status"] != "idle":
        return
    card["status"] = "sel"
    board["selected"].append(index)
    if len(board["selected"]) < 3:
        return
    selected = [board["cards"][i] for i in board["selected"]]
    values = {c["kind"]: c["text"] for c in selected}
    correct = len(values) == 3 and values in board["answers"]
    for selected_card in selected:
        selected_card["status"] = "done" if correct else "bad"
    if correct:
        game["ingredients"] += 1
    board["selected"] = []


def _start(recipe_code, ctx):
    ok, reason = core.can_craft_pill(recipe_code, core.current_user_id(), ctx["idx"])
    if not ok:
        st.toast(reason, icon="⚠️")
        return
    try:
        board = build_board(ctx["pool"], all_words(active_variant()))
    except ValueError as exc:
        st.toast(str(exc), icon="⚠️")
        return
    st.session_state["alchemy_game"] = {
        "user": core.current_user_id(), "variant": active_variant(), "recipe": recipe_code,
        "ingredients": 0, "board": board, "round": 0,
    }


def _new_board(ctx):
    game = st.session_state["alchemy_game"]
    try:
        board = build_board(ctx["pool"], all_words(active_variant()))
    except ValueError as exc:
        st.toast(str(exc), icon="⚠️")
        return
    game["board"] = board
    game["round"] += 1


@st.dialog("⚗️ Kết quả luyện đan")
def _result_dialog(success, message):
    (st.success if success else st.error)(message)
    if st.button("Đóng", key="alchemy_result_close"):
        st.rerun()


def render(ctx):
    user_id = core.current_user_id()
    state = core.get_state()
    st.markdown("### ⚗️ Luyện Đan")
    if not get_config()["has_pinyin"]:
        st.info("Luyện đan ghép Hán tự – pinyin – nghĩa chỉ dành cho khóa tiếng Trung.")
        return
    if len(ctx["pool"]) < cfg.ALCHEMIST_MIN_WORDS:
        st.info("🔒 Hãy hoàn thành bài học ít nhất 4 từ vựng rồi quay lại.")
        return
    st.caption("Mua công thức, chọn ba mảnh Hán tự – pinyin – nghĩa khớp nhau để gom nguyên liệu.")
    image = Path(__file__).parent / "assets" / "hinh tu luyen" / "lo_dan.png"
    if image.exists():
        _, col = st.columns([2, 1])
        col.image(str(image), use_container_width=True, caption="Lò Luyện Đan")
    tab_recipes, tab_craft, tab_inventory = st.tabs(["📜 Công Thức", "⚗️ Luyện Viên", "🧪 Kho Đan"])
    with tab_recipes:
        owned = {r["code"] for r in core.get_pill_recipes_owned(user_id)}
        for recipe in cfg.PILL_RECIPES:
            left, right = st.columns([4, 1])
            left.markdown(f"{recipe['emoji']} **{recipe['name']}** · {cfg.MAJOR_REALMS[recipe['min_realm']]} trở lên  \n"
                          f"{recipe['description']} · {recipe['ingredients']} nguyên liệu · "
                          f"thành công {recipe['success_rate']:.0%}")
            if recipe["code"] in owned:
                right.success("✅ Sở hữu")
            elif right.button(f"Mua ({cfg.PILL_RECIPE_PRICES[recipe['code']]} 💎)", key=f"buy_pill_{recipe['code']}"):
                ok, msg, _ = core.buy_pill_recipe(recipe["code"], user_id, state["ls"])
                if ok:
                    core.get_state(force=True)
                    st.toast(msg)
                    st.rerun()
                st.error(msg)
    with tab_craft:
        st.markdown("#### Luyện Viên Đan")
        st.info("Chọn công thức rồi bắt đầu. Chọn 3 mảnh khớp nhau: đúng được 1 nguyên liệu, "
                "sai cả 3 mảnh bị khóa đỏ. Khi không còn bộ ghép được, mở bảng mới; "
                "đủ nguyên liệu mới được bấm Luyện đan.")
        owned = core.get_pill_recipes_owned(user_id)
        if not owned:
            st.info("Hãy mua công thức trước khi luyện đan.")
        else:
            code = st.selectbox("Chọn công thức", [r["code"] for r in owned],
                                format_func=lambda value: cfg.PILL_RECIPES_BY_CODE[value]["name"],
                                key="pill_recipe_select")
            recipe = cfg.PILL_RECIPES_BY_CODE[code]
            st.caption(f"{recipe['description']} · {recipe['ingredients']} nguyên liệu · "
                       f"{recipe['success_rate']:.0%} thành công · {cfg.MAJOR_REALMS[recipe['min_realm']]} trở lên")
            game = st.session_state.get("alchemy_game")
            if game and (game["user"], game["variant"], game["recipe"]) != (user_id, active_variant(), code):
                game = None
                st.session_state.pop("alchemy_game", None)
            if not game:
                st.button("▶️ Bắt đầu", on_click=_start, args=(code, ctx), key="alchemy_start",
                          disabled=ctx["idx"] < recipe["min_realm"])
            else:
                board = game["board"]
                if len(board["cards"]) < cfg.ALCHEMIST_BOARD_WORDS * 3:
                    st.warning(f"Kho từ chỉ có {len(board['cards']) // 3} từ đủ Hán tự, pinyin và nghĩa; "
                               "bảng này có ít hơn 30 mảnh.")
                st.progress(min(1.0, game["ingredients"] / recipe["ingredients"]),
                            text=f"Nguyên liệu: {game['ingredients']}/{recipe['ingredients']}")
                keys = [f"alchemy_card_{game['round']}_{i}" for i in range(len(board["cards"]))]
                st.markdown(game_ui.color_buttons_css({key: card["status"] for key, card in zip(keys, board["cards"])}),
                            unsafe_allow_html=True)
                columns = st.columns(3)
                for i, card in enumerate(board["cards"]):
                    columns[i % 3].button(card["text"], key=keys[i], use_container_width=True,
                                          disabled=card["status"] != "idle",
                                          on_click=choose_card, args=(game, i))
                if not board["selected"] and not board_has_match(board):
                    st.warning("Không còn bộ ghép được. Hãy mở bảng nguyên liệu mới.")
                    st.button("🔄 Bảng mới", key="alchemy_next", on_click=_new_board, args=(ctx,))
                if st.button("⚗️ Luyện đan", key="alchemy_craft", type="primary",
                             disabled=game["ingredients"] < recipe["ingredients"] or ctx["idx"] < recipe["min_realm"]):
                    ok, msg = core.craft_pill(code, user_id, ctx["idx"], game["ingredients"])
                    st.session_state.pop("alchemy_game", None)
                    _result_dialog(ok, msg)
    with tab_inventory:
        inventory = core.get_pills_inventory(user_id)
        if not inventory:
            st.info("Kho đan trống. Hãy luyện đan để tích lũy.")
        for pill in inventory:
            st.write(f"{pill['emoji']} **{pill['name']} ×{pill['qty']}** — {pill['description']}")
