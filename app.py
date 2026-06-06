import os
import gradio as gr
import spacy
import json
from dotenv import load_dotenv

load_dotenv()
nlp = spacy.load("fr_core_news_sm")

# True when running as a HF Space; False on local Docker dev
IS_SPACE = bool(os.environ.get("SPACE_ID"))

# Annotation JSON schema (locked Day 1):
# { "tokens": [{ "idx": int, "text": str, "pos": str, "gender": str|null,
#               "lemma": str, "is_space": bool, "whitespace": str }] }

MASC_COLOR = "#4A90D9"   # blue
FEM_COLOR  = "#D96B8A"   # rose

SAMPLE_TEXT = (
    "Le petit chat noir dort sur la grande table. "
    "La femme mange une pomme délicieuse avec son ami. "
    "Le livre est ouvert sur le bureau."
)

# ---------- Auth helpers ----------

def get_user_id(profile: gr.OAuthProfile | None) -> str | None:
    """
    Returns the active user_id string, or None if unauthenticated on Space.
    Locally always returns 'dev_user' so the app works without HF OAuth.
    """
    if profile is not None:
        return profile.username
    return None if IS_SPACE else "dev_user"


def _login_prompt() -> str:
    return (
        '<div style="padding:32px;text-align:center;color:#666;'
        'border:1px dashed #ccc;border-radius:8px;margin-top:16px">'
        '<div style="font-size:1.4rem;margin-bottom:8px">🔒</div>'
        '<div style="font-size:1rem">Please sign in with your Hugging Face account to use French Coach.</div>'
        '</div>'
    )

# ---------- NLP helpers ----------

def annotate(text: str) -> dict:
    doc = nlp(text)
    tokens = []
    for tok in doc:
        gender = tok.morph.get("Gender")
        tokens.append({
            "idx": tok.i,
            "text": tok.text,
            "pos": tok.pos_,
            "gender": gender[0] if gender else None,
            "lemma": tok.lemma_,
            "is_space": tok.is_space,
            "whitespace": tok.whitespace_,
        })
    return {"tokens": tokens}


def render_html(annotations: dict, colors_on: bool) -> str:
    tokens = annotations.get("tokens", [])
    parts = []
    for tok in tokens:
        if tok["is_space"]:
            parts.append(tok.get("whitespace", " "))
            continue

        text   = tok["text"]
        gender = tok.get("gender")
        pos    = tok.get("pos", "")
        lemma  = tok.get("lemma", text)

        style_parts = ["cursor:pointer", "padding:1px 3px", "border-radius:3px"]
        if colors_on and pos == "NOUN":
            if gender == "Masc":
                style_parts += [
                    f"background:{MASC_COLOR}1A",
                    f"border-bottom:2px solid {MASC_COLOR}",
                ]
            elif gender == "Fem":
                style_parts += [
                    f"background:{FEM_COLOR}1A",
                    f"border-bottom:2px solid {FEM_COLOR}",
                ]

        style = ";".join(style_parts)
        safe  = lambda s: (s or "").replace('"', "&quot;")

        parts.append(
            f'<span class="tok" style="{style}" '
            f'data-token="1" '
            f'data-text="{safe(text)}" '
            f'data-gender="{safe(gender)}" '
            f'data-pos="{safe(pos)}" '
            f'data-lemma="{safe(lemma)}">'
            f'{text}</span>'
        )
        if tok.get("whitespace"):
            parts.append(tok["whitespace"])

    return (
        '<div id="fc-text" style="'
        'font-size:1.15rem;line-height:2;font-family:Georgia,serif;'
        'padding:12px;border:1px solid #e0e0e0;border-radius:6px;'
        'background:#fffef9;min-height:80px">'
        + "".join(parts)
        + "</div>"
        + _legend_html(colors_on)
    )


def _legend_html(colors_on: bool) -> str:
    if not colors_on:
        return ""
    return (
        '<div style="margin-top:8px;font-size:0.8rem;color:#888">'
        f'<span style="border-bottom:2px solid {MASC_COLOR};padding:0 4px">masc.</span>'
        "&nbsp;&nbsp;"
        f'<span style="border-bottom:2px solid {FEM_COLOR};padding:0 4px">fém.</span>'
        "</div>"
    )


def _empty_card() -> str:
    return (
        '<div style="color:#aaa;padding:18px;font-size:0.95rem">'
        "Click any word to see its gender, lemma, and part of speech."
        "</div>"
    )

# ---------- Event handlers (all accept profile for auth) ----------

def on_load(profile: gr.OAuthProfile | None):
    """Fires on page load. Returns (user_display_md, html_out, ann_state)."""
    user_id = get_user_id(profile)
    if user_id is None:
        return (
            gr.Markdown(visible=False),
            _login_prompt(),
            "",
        )
    label = f"👤 **{user_id}**" if user_id != "dev_user" else "🛠 *local dev*"
    html, ann = process_text(SAMPLE_TEXT, True, profile)
    return gr.Markdown(label, visible=True), html, ann


def process_text(text: str, colors_on: bool, profile: gr.OAuthProfile | None):
    if get_user_id(profile) is None:
        return _login_prompt(), ""
    ann  = annotate(text)
    html = render_html(ann, colors_on)
    return html, json.dumps(ann, ensure_ascii=False)


def toggle_colors(ann_json: str, colors_on: bool, profile: gr.OAuthProfile | None):
    if not ann_json or get_user_id(profile) is None:
        return ""
    return render_html(json.loads(ann_json), colors_on)


def show_word_card(click_data: str, profile: gr.OAuthProfile | None):
    if get_user_id(profile) is None:
        return _login_prompt()
    if not click_data:
        return _empty_card()
    try:
        d = json.loads(click_data)
    except Exception:
        return _empty_card()

    text   = d.get("text", "")
    gender = d.get("gender") or ""
    pos    = d.get("pos", "")
    lemma  = d.get("lemma", text)

    gender_label = {"Masc": "Masculine ♂", "Fem": "Feminine ♀"}.get(gender, "—")
    color        = {"Masc": MASC_COLOR, "Fem": FEM_COLOR}.get(gender, "#888")
    pos_labels   = {
        "NOUN": "Noun", "VERB": "Verb", "ADJ": "Adjective",
        "ADV": "Adverb", "DET": "Determiner", "PRON": "Pronoun",
        "ADP": "Preposition", "CCONJ": "Conjunction", "CONJ": "Conjunction",
        "PART": "Particle", "PUNCT": "Punctuation",
    }
    pos_label = pos_labels.get(pos, pos)

    return (
        f'<div style="border:1px solid #ddd;border-radius:10px;padding:18px;'
        f'background:#fff;box-shadow:0 2px 8px #0001">'
        f'<div style="font-size:1.8rem;font-weight:700;color:{color};margin-bottom:8px">'
        f'{text}</div>'
        f'<table style="font-size:0.92rem;border-collapse:collapse;width:100%">'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Lemma</td>'
        f'    <td style="font-weight:600">{lemma}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Gender</td>'
        f'    <td style="color:{color};font-weight:600">{gender_label}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Part of speech</td>'
        f'    <td>{pos_label}</td></tr>'
        f'</table>'
        f'<button data-speak="{text}" '
        f'style="margin-top:12px;padding:7px 16px;border:1px solid #ccc;'
        f'border-radius:6px;background:#f5f5f5;cursor:pointer;font-size:0.9rem">'
        f'🔊 Hear it</button>'
        f'</div>'
    )


# ---------- Page-load JS ----------
# ONE delegated listener on `document` survives gr.HTML re-renders.
# Handles word-token clicks (→ hidden textbox) and TTS button clicks.

PAGE_JS = """
() => {
    function setup() {
        document.addEventListener('click', function(e) {

            // TTS button (data-speak attribute on the word card button)
            const ttsBtn = e.target.closest('[data-speak]');
            if (ttsBtn) {
                e.stopPropagation();
                const u = new SpeechSynthesisUtterance(ttsBtn.getAttribute('data-speak'));
                u.lang = 'fr-FR';
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(u);
                return;
            }

            // Word token click
            const tok = e.target.closest('[data-token]');
            if (!tok) return;

            // Speak immediately
            const u = new SpeechSynthesisUtterance(tok.getAttribute('data-text'));
            u.lang = 'fr-FR';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);

            // Push click payload into hidden Gradio textbox to fire Python .change()
            const payload = JSON.stringify({
                text:   tok.getAttribute('data-text'),
                gender: tok.getAttribute('data-gender'),
                pos:    tok.getAttribute('data-pos'),
                lemma:  tok.getAttribute('data-lemma'),
            });
            const wrapper = document.getElementById('word-click-data');
            if (!wrapper) return;
            const ta = wrapper.querySelector('textarea') || wrapper.querySelector('input');
            if (!ta) return;
            const proto  = ta.tagName === 'TEXTAREA'
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            if (setter) setter.call(ta, payload);
            ta.dispatchEvent(new Event('input', { bubbles: true }));
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', setup);
    } else {
        setup();
    }
}
"""

# ---------- UI ----------

with gr.Blocks(title="French Coach") as demo:

    ann_state = gr.State("")

    # ── Header ──────────────────────────────────────────────────────────────
    with gr.Row(equal_height=True):
        with gr.Column(scale=4):
            gr.Markdown("## 🇫🇷 French Coach")
        with gr.Column(scale=1, min_width=160):
            user_display = gr.Markdown(visible=False)
        if IS_SPACE:
            with gr.Column(scale=0, min_width=130):
                gr.LoginButton(min_width=120)
            with gr.Column(scale=0, min_width=110):
                gr.LogoutButton(min_width=100)

    # ── Main workspace ───────────────────────────────────────────────────────
    with gr.Row():
        with gr.Column(scale=3):
            text_input = gr.Textbox(
                label="French text",
                value=SAMPLE_TEXT,
                lines=4,
                placeholder="Paste your French notes here…",
            )
            with gr.Row():
                annotate_btn  = gr.Button("Annotate", variant="primary")
                colors_toggle = gr.Checkbox(label="Gender colors", value=True)

            html_out = gr.HTML(value=_empty_card())

        with gr.Column(scale=2):
            gr.Markdown("### Word card")
            word_card = gr.HTML(value=_empty_card())
            # Hidden — receives click payloads from JS delegation
            click_data = gr.Textbox(
                elem_id="word-click-data",
                visible=False,
                label="click-data",
            )

    # ── Event wiring ─────────────────────────────────────────────────────────
    annotate_btn.click(
        fn=process_text,
        inputs=[text_input, colors_toggle],
        outputs=[html_out, ann_state],
    )
    colors_toggle.change(
        fn=toggle_colors,
        inputs=[ann_state, colors_toggle],
        outputs=[html_out],
    )
    click_data.change(
        fn=show_word_card,
        inputs=[click_data],
        outputs=[word_card],
    )
    demo.load(
        fn=on_load,
        outputs=[user_display, html_out, ann_state],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", js=PAGE_JS)
