"""Tiện ích giao diện chung của trò chơi: ảnh, âm thanh, CSS tô màu nút."""
import json
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from course_config import get_config
ASSETS = Path(__file__).parent / "assets"
IMAGE_EXTS = (".png", ".webp", ".jpg", ".jpeg")


def find_image(folder, code):
    for ext in IMAGE_EXTS:
        path = ASSETS / folder / f"{code}{ext}"
        if path.exists():
            return str(path)
    return None


def show_image_or_emoji(folder, code, emoji, width=150, tooltip=""):
    path = find_image(folder, code)
    title_attr = f'title="{tooltip}"' if tooltip else ""
    if path:
        import base64
        b64 = base64.b64encode(Path(path).read_bytes()).decode()
        st.markdown(f'<div style="text-align:center;"><img src="data:image/png;base64,{b64}" width="{width}" {title_attr} style="display:inline-block;max-width:100%;object-fit:contain;"/></div>', unsafe_allow_html=True)
    else:
        st.markdown(f"<div {title_attr} style='font-size:{int(width * 0.6)}px;line-height:1.1;text-align:center;cursor:pointer;'>{emoji}</div>",
                    unsafe_allow_html=True)



def _tts_params():
    cfg = get_config()
    rate = float(st.session_state.get("speech_rate", 1.0))
    return cfg["tts_lang"], rate, cfg["tts_rate_short_factor"], cfg["tts_rate_sentence_factor"]


def speak(text, autoplay=False, label="🔊 Nghe"):
    """Nút phát âm Web Speech (ngôn ngữ theo khóa học); autoplay thử phát ngay khi câu hỏi mới hiện (trình duyệt có thể chặn)."""
    payload = json.dumps(text)
    lang, rate, short_f, long_f = _tts_params()
    html = f"""
    <button id="b" style="font-size:16px;padding:6px 14px;border-radius:8px;border:1px solid #c9a24b;
      background:#fff8e6;cursor:pointer">{label}</button>
    <script>
    function say() {{
      const t = {payload};
      const u = new SpeechSynthesisUtterance(t); u.lang = '{lang}'; u.rate = {rate} * (t.length <= 6 ? {short_f} : {long_f});
      speechSynthesis.cancel(); speechSynthesis.speak(u);
    }}
    document.getElementById('b').onclick = say;
    {"setTimeout(say, 300);" if autoplay else ""}
    </script>"""
    components.html(html, height=48)


def audio_listener(mapping):
    """mapping: {khóa nút: văn bản}. Bấm nút có khóa đó sẽ phát âm (listener gắn vào trang cha để trình duyệt cho phép).

    Mỗi lần iframe nạp lại phải gỡ listener cũ rồi gắn lại: listener cũ thuộc iframe đã bị xóa nên không còn chạy
    (nguyên nhân thẻ âm thanh câm từ ván thứ hai).
    """
    lang, rate, short_f, long_f = _tts_params()
    payload = json.dumps({"map": mapping, "lang": lang, "rate": rate, "short": short_f, "long": long_f})
    components.html(f"""<script>
    const P = window.parent; const D = P.document;
    P.__ttsCfg = {payload};
    if (P.__ttsHandler) D.removeEventListener('click', P.__ttsHandler, true);
    P.__ttsHandler = function (e) {{
      const btn = e.target.closest('button'); if (!btn) return;
      const c = P.__ttsCfg;
      for (const k in c.map) {{
        if (btn.closest('.st-key-' + k)) {{
          const t = c.map[k];
          const u = new P.SpeechSynthesisUtterance(t); u.lang = c.lang;
          u.rate = c.rate * (t.length <= 6 ? c.short : c.long);
          P.speechSynthesis.cancel(); P.speechSynthesis.speak(u); break;
        }}
      }}
    }};
    D.addEventListener('click', P.__ttsHandler, true);
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
