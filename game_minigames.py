"""Ba trò chơi ôn tập theo lượt: Quẻ Bói, Ghép Bài, Sắp Xếp Câu."""
import random

import streamlit as st

import game_config as cfg
import game_core as core
import game_questions as gq
import game_ui
from course_config import get_config
from database import get_vocab_by_ids, record_review_batch


def _toast_new(badges):
    for name in badges:
        st.toast(f"🏅 Danh hiệu mới: {name}")


def _remaining_plays_note(state):
    plays = state["plays"]
    mult = core.play_multiplier(plays)
    if mult >= 1:
        return f"Hôm nay đã chơi {plays} lượt · còn {cfg.DAILY_FULL_PLAYS - plays} lượt nhận đủ Linh Thạch."
    return f"Hôm nay đã chơi {plays} lượt · Linh Thạch hiện nhận {int(mult * 100)}%."


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
    "hm": "Hán ↔ nghĩa", "hp": "Hán ↔ pinyin", "ap": "Nghe ↔ pinyin", "ah": "Nghe ↔ Hán", "am": "Nghe ↔ nghĩa",
}


AUDIO_MODES = ("ap", "ah", "am")


def _right_face(word, mode):
    if mode in ("hm", "am"):
        return gq.short_meaning(word, 40)
    if mode in ("hp", "ap"):
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
            options = ["ap", "ah"] if i in audio_slots else ["hm", "hp"]
        rng.shuffle(options)
        options.append("hm")
        for mode in options:
            if mode == "ap" and not word.get("pinyin"):
                continue
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
        modes_note = "Hán ↔ nghĩa, Hán ↔ pinyin, 🔊 nghe ↔ pinyin/Hán"
    else:
        modes_note = "từ tiếng Anh ↔ nghĩa tiếng Việt, 🔊 phát âm ↔ nghĩa tiếng Việt"
    st.caption(f"Mỗi ván 4 cặp, trộn nhiều thể thức: {modes_note} (tối đa 2 cặp nghe). "
               "Bấm nút 🔊 để nghe, rồi chọn mặt khớp ở cột phải. Ghép sai sẽ khóa cả hai nút. "
               + _remaining_plays_note(state))
    m = st.session_state.get("g_match")
    if m is None:
        st.button("▶️ Bắt đầu ván mới", key="match_start", type="primary", on_click=start_match, args=(ctx,))
        return
    colors = {}
    for i in m["words"]:
        colors[f"ml_{i}"] = m["status"][f"L{i}"]
        colors[f"mr_{i}"] = m["status"][f"R{i}"]
    st.markdown(game_ui.color_buttons_css(colors), unsafe_allow_html=True)
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
# Sắp xếp câu / điền chữ
# ---------------------------------------------------------------------------

def start_sentence(ctx):
    pool = ctx["pool"]
    with_examples = [w for w in pool if w.get("example_zh")]
    chosen = gq.pick_words(with_examples, ctx["mastery"], cfg.SENTENCE_ROUNDS)
    vocab_hanzi = gq.all_hanzi()
    rounds = []
    for word in chosen:
        tokens = gq.tokenize_sentence(word["example_zh"], vocab_hanzi)
        can_arrange = 4 <= len(tokens) <= 12
        can_cloze = gq.has_cloze(word)
        if can_arrange and (not can_cloze or random.random() < 0.6):
            shuffled = tokens[:]
            for _ in range(5):
                random.shuffle(shuffled)
                if shuffled != tokens:
                    break
            rounds.append({"type": "arrange", "word": word, "tokens": shuffled, "target": gq.join_tokens(tokens),
                           "picked": [], "result": None})
        elif can_cloze:
            rounds.append({"type": "cloze", "question": gq.make_question(word, pool, "cloze"),
                           "word": word, "result": None})
    st.session_state.g_sent = {"rounds": rounds, "idx": 0, "done": None}


def _sent_pick(i):
    m = st.session_state.g_sent
    rnd = m["rounds"][m["idx"]]
    if rnd["result"] is None and i not in rnd["picked"]:
        rnd["picked"].append(i)


def _sent_undo():
    rnd = st.session_state.g_sent["rounds"][st.session_state.g_sent["idx"]]
    if rnd["result"] is None and rnd["picked"]:
        rnd["picked"].pop()


def _sent_check():
    rnd = st.session_state.g_sent["rounds"][st.session_state.g_sent["idx"]]
    rnd["result"] = gq.join_tokens([rnd["tokens"][i] for i in rnd["picked"]]) == rnd["target"]


def _sent_cloze(choice):
    rnd = st.session_state.g_sent["rounds"][st.session_state.g_sent["idx"]]
    if rnd["result"] is None:
        rnd["result"] = gq.evaluate(rnd["question"], choice)


def _sent_next(ctx):
    m = st.session_state.g_sent
    if m["idx"] + 1 < len(m["rounds"]):
        m["idx"] += 1
        return
    correct = sum(1 for r in m["rounds"] if r["result"])
    total = len(m["rounds"])
    perfect = correct == total
    base = correct * cfg.SENTENCE_REWARD + (cfg.SENTENCE_PERFECT_BONUS if perfect else 0)
    results = [(r["word"]["id"], bool(r["result"])) for r in m["rounds"]]
    ls, mult, badges = core.settle(
        base, core.scale(ctx["idx"]), ctx["words"], results=results,
        incr={"sentences_ok": correct, "answers_correct": correct},
        log=("sentence", f"Sắp xếp câu: đúng {correct}/{total} câu."))
    m["done"] = {"ls": ls, "mult": mult, "correct": correct, "total": total}
    _toast_new(badges)


def render_sentence(ctx):
    state = core.get_state()
    st.markdown("### 📜 Đối Câu Luận Đạo")
    st.caption("Ghép các cụm thành câu đúng hoặc điền chữ còn thiếu. " + _remaining_plays_note(state))
    m = st.session_state.get("g_sent")
    if m is None or (m["done"] is None and not m["rounds"]):
        st.button("▶️ Bắt đầu", key="sent_start", type="primary", on_click=start_sentence, args=(ctx,))
        if m is not None:
            st.warning("Chưa có đủ câu ví dụ để chơi. Hãy học thêm từ mới.")
        return
    if m["done"]:
        d = m["done"]
        st.success(f"Hoàn thành: đúng {d['correct']}/{d['total']} câu · +{d['ls']} 💎 Linh Thạch"
                   + (f" (hệ số {int(d['mult'] * 100)}%)" if d["mult"] < 1 else ""))
        st.button("🔁 Chơi lượt khác", key="sent_again", type="primary", on_click=start_sentence, args=(ctx,))
        return
    rnd = m["rounds"][m["idx"]]
    word = rnd["word"]
    st.progress(m["idx"] / len(m["rounds"]), text=f"Câu {m['idx'] + 1}/{len(m['rounds'])}")
    if rnd["type"] == "arrange":
        st.write(f"Nghĩa: *{word.get('example_vi') or gq.short_meaning(word)}*")
        picked = gq.join_tokens([rnd["tokens"][i] for i in rnd["picked"]]) or "…"
        st.markdown(f"<div class='quiz-prompt' style='font-size:30px'>{picked}</div>", unsafe_allow_html=True)
        for row_start in range(0, len(rnd["tokens"]), 6):
            cols = st.columns(6)
            for offset, token in enumerate(rnd["tokens"][row_start:row_start + 6]):
                i = row_start + offset
                cols[offset].button(token, key=f"sent_tok_{m['idx']}_{i}", use_container_width=True,
                                    on_click=_sent_pick, args=(i,),
                                    disabled=rnd["result"] is not None or i in rnd["picked"])
        if rnd["result"] is None:
            c1, c2 = st.columns(2)
            c1.button("↩️ Xóa chữ cuối", key=f"sent_undo_{m['idx']}", on_click=_sent_undo, use_container_width=True)
            c2.button("✔️ Kiểm tra", key=f"sent_check_{m['idx']}", on_click=_sent_check, type="primary",
                      use_container_width=True, disabled=not rnd["picked"])
        else:
            (st.success if rnd["result"] else st.error)(
                "Chính xác!" if rnd["result"] else f"Chưa đúng. Đáp án: {rnd['target']}")
    else:
        q = rnd["question"]
        st.write(f"Nghĩa: *{word.get('example_vi') or gq.short_meaning(word)}*")
        st.markdown(f"<div class='quiz-prompt' style='font-size:30px'>{q['prompt']}</div>", unsafe_allow_html=True)
        for i, option in enumerate(q["options"]):
            st.button(option["label"], key=f"sent_opt_{m['idx']}_{i}", use_container_width=True,
                      on_click=_sent_cloze, args=(i,), disabled=rnd["result"] is not None)
        if rnd["result"] is not None:
            (st.success if rnd["result"] else st.error)(
                "Chính xác!" if rnd["result"] else f"Chưa đúng. Đáp án: {gq.correct_label(q)}")
    if rnd["result"] is not None:
        st.button("Tiếp theo ➡️" if m["idx"] + 1 < len(m["rounds"]) else "Hoàn thành 🏁",
                  key=f"sent_next_{m['idx']}", on_click=_sent_next, args=(ctx,), type="primary")
