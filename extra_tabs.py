"""Giao diện các tab phụ: Sổ tay, Tập phát âm, Bộ thủ."""
import html
import json
import math

import streamlit as st
import streamlit.components.v1 as components

from database import count_learned_words, get_learned_words
from reference_data import FINAL_GROUPS, INITIAL_GROUPS, TONES, radicals_by_strokes

PAGE_SIZE = 20

IFRAME_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@600;900&family=Be+Vietnam+Pro:wght@400;500;600;700&display=swap');
* { box-sizing: border-box; }
body { margin: 0; font-family: 'Be Vietnam Pro', 'Segoe UI', sans-serif; color: #f4eef7; background: transparent; }
h4 { margin: 18px 0 8px; font-size: 0.95rem; font-weight: 600; color: #f0b95b; }
h4:first-child { margin-top: 4px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 10px; }
.cell {
    display: flex; flex-direction: column; align-items: center; gap: 4px;
    padding: 12px 6px; border-radius: 14px; cursor: pointer;
    background: #1b1424; border: 1px solid #3a2d48; color: inherit;
    font-family: inherit; transition: transform .12s, border-color .12s, background .12s;
}
.cell:hover { transform: translateY(-2px); border-color: #c46bd1; background: #261a33; }
.cell:active { background: #3a2450; }
.cell .sym { font-size: 1.7rem; font-weight: 700; color: #e9a8f0; }
.cell .ex { font-family: 'Noto Serif SC', serif; font-size: 0.95rem; color: #b3a6c0; }
.cell .ico { font-size: 0.8rem; opacity: .7; }
.head { display: flex; align-items: center; gap: 14px; justify-content: center; }
.hz { font-family: 'Noto Serif SC', serif; font-size: 3.6rem; font-weight: 900; letter-spacing: .12em; }
.spk {
    width: 46px; height: 46px; border-radius: 50%; border: 1px solid #c46bd1; cursor: pointer;
    background: #2b1a36; font-size: 1.3rem; color: #fff; transition: transform .12s, background .12s;
}
.spk:hover { background: #8a0f8f; transform: scale(1.08); }
.py { text-align: center; font-size: 1.4rem; color: #e9a8f0; font-weight: 600; margin-top: 2px; }
"""

SPEAK_SCRIPT = """
const rate = %s;
function speak(text) {
    const s = window.speechSynthesis;
    if (!s || !text) return;
    s.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = 'zh-CN';
    u.rate = rate * 0.85;
    s.speak(u);
}
document.querySelectorAll('[data-say]').forEach(b => b.addEventListener('click', () => speak(b.dataset.say)));
function fit() {
    if (window.frameElement) window.frameElement.style.height = document.documentElement.scrollHeight + 'px';
}
new ResizeObserver(fit).observe(document.body);
fit();
"""


def _speech_frame(body_html, height=120):
    """Iframe chứa các nút loa (data-say) phát âm bằng Web Speech API, tự co giãn chiều cao."""
    rate = float(st.session_state.get("speech_rate", 1.0))
    doc = f"<style>{IFRAME_CSS}</style>{body_html}<script>{SPEAK_SCRIPT % rate}</script>"
    components.html(doc, height=height)


def render_chiet_tu(chiet_tu_data):
    """Hiển thị bộ thủ & câu chuyện gợi nhớ. Trả về False nếu dữ liệu không hợp lệ."""
    try:
        data = json.loads(chiet_tu_data) if isinstance(chiet_tu_data, str) else chiet_tu_data
        for comp in data.get("components", []):
            st.markdown(f"🔹 **{comp.get('radical', '')}** ({comp.get('name', '')}): {comp.get('meaning', '')}")
        st.info(f"📖 **Gợi nhớ:** {data.get('story', '')}")
        return True
    except (ValueError, AttributeError, TypeError):
        return False


@st.dialog("📖 Chi tiết từ vựng")
def show_word_dialog(word):
    hanzi = html.escape(word["hanzi"])
    _speech_frame(
        f"<div class='head'><span class='hz'>{hanzi}</span>"
        f"<button class='spk' title='Nghe phát âm' data-say='{html.escape(word['hanzi'], quote=True)}'>🔊</button></div>"
        f"<div class='py'>{html.escape(word['pinyin'])}</div>",
        height=130,
    )
    st.markdown(
        f"<div style='text-align:center'><span class='hanviet-badge'>Âm Hán Việt: {html.escape(word['hanviet'] or '')}</span>"
        f"<div class='meaning-display'>{html.escape(word['meaning_vi'] or '')}</div></div>",
        unsafe_allow_html=True,
    )
    if word.get("chiet_tu"):
        st.markdown("**💡 Mẹo nhớ Hán tự**")
        if not render_chiet_tu(word["chiet_tu"]):
            st.caption("Dữ liệu chiết tự đang được cập nhật...")
    if word.get("example_zh"):
        st.markdown(
            "<div class='example-box'>"
            f"<div class='example-zh'>📌 {html.escape(word['example_zh'])}</div>"
            f"<div class='example-pinyin'>{html.escape(word.get('example_pinyin') or '')}</div>"
            f"<div class='example-vi'>{html.escape(word.get('example_vi') or '')}</div>"
            "</div>",
            unsafe_allow_html=True,
        )


def _set_page(page):
    st.session_state.notebook_page = page


def _jump_page():
    st.session_state.notebook_page = int(st.session_state.notebook_jump)


def render_notebook(current_day):
    """Sổ tay: từ vựng đã/đang học, 20 từ mỗi trang, có điều hướng trang."""
    total = count_learned_words(current_day)
    st.subheader("📒 Sổ Tay Từ Vựng")
    if total == 0:
        st.info("Chưa có từ vựng nào trong sổ tay.")
        return

    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(int(st.session_state.get("notebook_page", 1)), 1), pages)
    st.session_state.notebook_page = page
    st.session_state.notebook_jump = page

    st.caption(f"Tổng {total} từ · bấm vào chữ Hán để xem phiên âm, nghe phát âm và mẹo nhớ · Trang {page}/{pages}")

    words = get_learned_words(current_day, PAGE_SIZE, (page - 1) * PAGE_SIZE)
    for word in words:
        col_hz, col_info = st.columns([1.3, 4.7], vertical_alignment="center")
        with col_hz:
            if st.button(word["hanzi"], key=f"nbw_{word['id']}", use_container_width=True):
                show_word_dialog(word)
        with col_info:
            st.markdown(
                f"<span class='hanviet-badge' style='margin:0 8px 0 0; padding:3px 12px; font-size:.95rem'>{html.escape(word['hanviet'] or '')}</span>"
                f"<b>{html.escape(word['meaning_vi'] or '')}</b> "
                f"<span style='color:#b3a6c0; font-size:.85rem'>· Ngày {word['study_day']}</span>",
                unsafe_allow_html=True,
            )

    st.divider()
    first = min(max(page - 2, 1), max(pages - 4, 1))
    window = list(range(first, min(first + 5, pages + 1)))

    nav = st.columns([1.2] + [0.8] * len(window) + [1.2])
    with nav[0]:
        st.button("◀ Trước", key="nb_prev", disabled=page <= 1, use_container_width=True,
                  on_click=_set_page, args=(page - 1,))
    for col, p in zip(nav[1:-1], window):
        with col:
            st.button(str(p), key=f"nb_pg_{p}", use_container_width=True,
                      type="primary" if p == page else "secondary",
                      on_click=_set_page, args=(p,))
    with nav[-1]:
        st.button("Sau ▶", key="nb_next", disabled=page >= pages, use_container_width=True,
                  on_click=_set_page, args=(page + 1,))

    jump_col, _ = st.columns([1.2, 3])
    with jump_col:
        st.number_input("Nhảy tới trang (gõ số rồi Enter)", min_value=1, max_value=pages, step=1,
                        key="notebook_jump", on_change=_jump_page)


def _sound_grid(groups):
    parts = []
    for label, items in groups:
        cells = "".join(
            f"<button class='cell' data-say='{html.escape(char, quote=True)}'>"
            f"<span class='sym'>{html.escape(sym)}</span>"
            f"<span class='ex'>{html.escape(char)} {html.escape(py)}</span>"
            f"<span class='ico'>🔊</span></button>"
            for sym, char, py in items
        )
        parts.append(f"<h4>{html.escape(label)}</h4><div class='grid'>{cells}</div>")
    return "".join(parts)


def render_pronunciation():
    """Tập phát âm: thanh mẫu, vận mẫu và thanh điệu, mỗi ô có nút nghe."""
    st.subheader("🗣️ Tập Phát Âm")
    st.caption("Bấm vào từng ô để nghe. Mỗi âm được đọc qua một chữ Hán mẫu có chứa âm đó.")

    st.markdown("### Thanh mẫu (声母 - phụ âm đầu)")
    _speech_frame(_sound_grid(INITIAL_GROUPS), height=500)

    st.markdown("### Vận mẫu (韵母 - vần)")
    _speech_frame(_sound_grid(FINAL_GROUPS), height=700)

    st.markdown("### Thanh điệu (声调)")
    tones = [(label, [(mark, char, py)]) for label, mark, char, py in TONES]
    cells = "".join(
        f"<button class='cell' data-say='{html.escape(char, quote=True)}'>"
        f"<span class='sym'>{html.escape(mark)}</span>"
        f"<span class='ex'>{html.escape(label)} · {html.escape(char)} {html.escape(py)}</span>"
        f"<span class='ico'>🔊</span></button>"
        for label, [(mark, char, py)] in tones
    )
    _speech_frame(f"<div class='grid'>{cells}</div>", height=140)


def render_radicals():
    """214 bộ thủ Khang Hy, nhóm theo số nét, có ô tìm kiếm."""
    st.subheader("🧩 214 Bộ Thủ")
    query = st.text_input("🔍 Tìm bộ thủ (chữ, tên Hán Việt hoặc nghĩa)", key="radical_search").strip().lower()

    shown = 0
    for strokes, items in radicals_by_strokes():
        cards = []
        for num, char, variants, name, meaning in items:
            haystack = f"{char} {variants} {name} {meaning}".lower()
            if query and query not in haystack:
                continue
            variant_html = f"<div class='rad-var'>{html.escape(variants)}</div>" if variants else ""
            cards.append(
                "<div class='rad-card'>"
                f"<div class='rad-num'>{num}</div>"
                f"<div class='rad-char'>{html.escape(char)}</div>{variant_html}"
                f"<div class='rad-name'>{html.escape(name)}</div>"
                f"<div class='rad-mean'>{html.escape(meaning)}</div>"
                "</div>"
            )
        if cards:
            shown += len(cards)
            st.markdown(
                f"<div class='rad-title'>{strokes} nét <span>· {len(cards)} bộ</span></div>"
                f"<div class='rad-grid'>{''.join(cards)}</div>",
                unsafe_allow_html=True,
            )
    if shown == 0:
        st.info("Không tìm thấy bộ thủ phù hợp.")
    else:
        st.caption(f"Hiển thị {shown} bộ thủ.")
