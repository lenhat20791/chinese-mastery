"""Tiện ích giao diện chung của trò chơi: ảnh, âm thanh, CSS tô màu nút."""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ASSETS = Path(__file__).parent / "assets"
IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg")


def find_image(folder, code):
    for ext in IMAGE_EXTS:
        path = ASSETS / folder / f"{code}{ext}"
        if path.exists():
            return str(path)
    return None


def show_image_or_emoji(folder, code, emoji, width=150):
    path = find_image(folder, code)
    if path:
        st.image(path, width=width)
    else:
        st.markdown(f"<div style='font-size:{int(width * 0.6)}px;line-height:1.1;text-align:center'>{emoji}</div>",
                    unsafe_allow_html=True)


def speak(text, autoplay=False, label="🔊 Nghe"):
    """Nút phát âm Web Speech (zh-CN); autoplay thử phát ngay khi câu hỏi mới hiện (trình duyệt có thể chặn)."""
    payload = json.dumps(text)
    rate = float(st.session_state.get("speech_rate", 1.0))
    html = f"""
    <button id="b" style="font-size:16px;padding:6px 14px;border-radius:8px;border:1px solid #c9a24b;
      background:#fff8e6;cursor:pointer">{label}</button>
    <script>
    function say() {{
      const t = {payload};
      const u = new SpeechSynthesisUtterance(t); u.lang = 'zh-CN'; u.rate = {rate} * (t.length <= 6 ? 0.55 : 0.85);
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    }}
    document.getElementById('b').onclick = say;
    {"setTimeout(say, 300);" if autoplay else ""}
    </script>"""
    components.html(html, height=48)


def audio_listener(mapping):
    """mapping: {khóa nút: văn bản}. Bấm nút có khóa đó sẽ phát âm (listener gắn vào trang cha để trình duyệt cho phép)."""
    rate = float(st.session_state.get("speech_rate", 1.0))
    payload = json.dumps(mapping)
    components.html(f"""<script>
    const P = window.parent; const D = P.document;
    P.__zhMap = {payload}; P.__zhRate = {rate};
    if (!P.__zhBound) {{
      P.__zhBound = true;
      D.addEventListener('click', function (e) {{
        const btn = e.target.closest('button'); if (!btn) return;
        for (const k in P.__zhMap) {{
          if (btn.closest('.st-key-' + k)) {{
            const t = P.__zhMap[k];
            const u = new P.SpeechSynthesisUtterance(t); u.lang = 'zh-CN';
            u.rate = P.__zhRate * (t.length <= 6 ? 0.55 : 0.85);
            P.speechSynthesis.cancel(); P.speechSynthesis.speak(u); break;
          }}
        }}
      }}, true);
    }}
    </script>""", height=0)


STATE_COLORS = {
    "sel": ("#f5c542", "#3b2a00"),
    "done": ("#2e9e5b", "#ffffff"),
    "bad": ("#d64545", "#ffffff"),
}


def color_buttons_css(key_states):
    """key_states: {khóa nút: 'sel'|'done'|'bad'} -> thẻ <style> tô màu từng nút theo khóa."""
    rules = []
    for key, state in key_states.items():
        if state in STATE_COLORS:
            bg, fg = STATE_COLORS[state]
            rules.append(f".st-key-{key} button {{ background:{bg} !important; color:{fg} !important;"
                         f" border-color:{bg} !important; opacity:1 !important; }}"
                         f".st-key-{key} button p {{ color:{fg} !important; }}")
    return f"<style>{''.join(rules)}</style>" if rules else ""
