import os
import json
import gradio as gr
from dotenv import load_dotenv

import nlp
import llm
import prompts
import notebook as nb
import exercises as ex
import gamify

load_dotenv()

IS_SPACE = bool(os.environ.get("SPACE_ID"))

SAMPLE_TEXT = (
    "Le petit chat noir dort sur la grande table. "
    "La femme mange une pomme délicieuse avec son ami. "
    "Le livre est ouvert sur le bureau."
)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_user_id(profile: gr.OAuthProfile | None) -> str | None:
    if profile is not None:
        return profile.username
    return None if IS_SPACE else "dev_user"


def _login_prompt() -> str:
    return (
        '<div style="padding:32px;text-align:center;color:#666;'
        'border:1px dashed #ccc;border-radius:8px">'
        '<div style="font-size:1.4rem">🔒</div>'
        '<div>Please sign in with your Hugging Face account to use French Coach.</div>'
        '</div>'
    )

def _empty_card() -> str:
    return '<div style="color:#aaa;padding:18px">Click any word to see its gender, lemma, and part of speech.</div>'

# ── Notebook tab handlers ─────────────────────────────────────────────────────

def process_text(text: str, colors_on: bool, user_id: str):
    if not user_id:
        return _login_prompt(), ""
    ann  = nlp.annotate(text)
    html = nlp.render_html(ann, colors_on)
    return html, json.dumps(ann, ensure_ascii=False)


def toggle_colors(ann_json: str, colors_on: bool, user_id: str):
    if not ann_json or not user_id:
        return ""
    return nlp.render_html(json.loads(ann_json), colors_on)


def show_word_card(click_data: str, ann_json: str, user_id: str):
    """Generator: yields basic card instantly, then LLM-enriched card."""
    if not user_id:
        yield _login_prompt(), ann_json
        return
    if not click_data:
        yield _empty_card(), ann_json
        return
    try:
        d = json.loads(click_data)
    except Exception:
        yield _empty_card(), ann_json
        return

    text   = d.get("text", "")
    gender = d.get("gender") or ""
    pos    = d.get("pos", "")
    lemma  = d.get("lemma", text)

    # Instant basic card
    yield _basic_card(text, lemma, pos, gender), ann_json

    # Check meaning cache in ann_state
    ann       = json.loads(ann_json) if ann_json else {"tokens": [], "meanings": {}}
    meanings  = ann.get("meanings", {})
    cache_key = lemma or text

    if cache_key not in meanings:
        meanings[cache_key] = llm.get_word_meaning(text, lemma, pos, gender)
        ann["meanings"] = meanings
        ann_json = json.dumps(ann, ensure_ascii=False)
        try:
            gamify.add_points(user_id, "word_explored")
        except Exception:
            pass

    yield _enriched_card(text, lemma, pos, gender, meanings[cache_key]), ann_json


def _basic_card(text, lemma, pos, gender) -> str:
    color = {"Masc": nlp.MASC_COLOR, "Fem": nlp.FEM_COLOR}.get(gender, "#888")
    gender_label = {"Masc": "Masculine ♂", "Fem": "Feminine ♀"}.get(gender, "—")
    pos_label = {"NOUN":"Noun","VERB":"Verb","ADJ":"Adjective","ADV":"Adverb",
                 "DET":"Determiner","PRON":"Pronoun","ADP":"Preposition",
                 "CCONJ":"Conjunction","PART":"Particle","PUNCT":"Punctuation"}.get(pos, pos)
    return (
        f'<div style="border:1px solid #ddd;border-radius:10px;padding:18px;background:#fff;box-shadow:0 2px 8px #0001">'
        f'<div style="font-size:1.8rem;font-weight:700;color:{color};margin-bottom:8px">{text}</div>'
        f'<table style="font-size:0.92rem;border-collapse:collapse;width:100%">'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Lemma</td><td style="font-weight:600">{lemma}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Gender</td><td style="color:{color};font-weight:600">{gender_label}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Part of speech</td><td>{pos_label}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Meaning</td><td style="color:#aaa;font-style:italic">Loading…</td></tr>'
        f'</table>'
        f'<button data-speak="{text}" style="margin-top:12px;padding:7px 16px;border:1px solid #ccc;'
        f'border-radius:6px;background:#f5f5f5;cursor:pointer">🔊 Hear it</button>'
        f'</div>'
    )


def _enriched_card(text, lemma, pos, gender, meaning_data: dict) -> str:
    color = {"Masc": nlp.MASC_COLOR, "Fem": nlp.FEM_COLOR}.get(gender, "#888")
    gender_label = {"Masc": "Masculine ♂", "Fem": "Feminine ♀"}.get(gender, "—")
    pos_label = {"NOUN":"Noun","VERB":"Verb","ADJ":"Adjective","ADV":"Adverb",
                 "DET":"Determiner","PRON":"Pronoun","ADP":"Preposition",
                 "CCONJ":"Conjunction","PART":"Particle","PUNCT":"Punctuation"}.get(pos, pos)
    meaning = meaning_data.get("meaning", "")
    grammar = meaning_data.get("grammar", "")
    return (
        f'<div style="border:1px solid #ddd;border-radius:10px;padding:18px;background:#fff;box-shadow:0 2px 8px #0001">'
        f'<div style="font-size:1.8rem;font-weight:700;color:{color};margin-bottom:8px">{text}</div>'
        f'<table style="font-size:0.92rem;border-collapse:collapse;width:100%">'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Lemma</td><td style="font-weight:600">{lemma}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Gender</td><td style="color:{color};font-weight:600">{gender_label}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Part of speech</td><td>{pos_label}</td></tr>'
        f'<tr><td style="color:#888;padding:3px 8px 3px 0">Meaning</td><td>{meaning}</td></tr>'
        f'{"<tr><td style=&quot;color:#888;padding:3px 8px 3px 0&quot;>Grammar</td><td style=&quot;font-style:italic&quot;>" + grammar + "</td></tr>" if grammar else ""}'
        f'</table>'
        f'<button data-speak="{text}" style="margin-top:12px;padding:7px 16px;border:1px solid #ccc;'
        f'border-radius:6px;background:#f5f5f5;cursor:pointer">🔊 Hear it</button>'
        f'</div>'
    )


def save_page_handler(text: str, ann_json: str, user_id: str):
    if not user_id:
        return "Please sign in first.", gr.Dropdown(choices=[])
    if not text.strip():
        return "Nothing to save — type or paste some French text first.", gr.Dropdown()
    try:
        ann = json.loads(ann_json) if ann_json else {}
        page_id, title = nb.save_page(user_id, text, ann)
        gamify.add_points(user_id, "saved_lesson")
        choices = _page_choices(user_id)
        return f"✅ Saved as **{title}**", gr.Dropdown(choices=choices, value=page_id)
    except Exception as e:
        return f"⚠ Could not save: {e}", gr.Dropdown()


def load_pages_list(user_id: str):
    if not user_id:
        return gr.Dropdown(choices=[])
    return gr.Dropdown(choices=_page_choices(user_id))


def load_page_handler(page_id: str, colors_on: bool, user_id: str):
    if not page_id or not user_id:
        return "", "", ""
    try:
        page = nb.get_page(page_id, user_id)
        if not page:
            return "", "", ""
        ann = page.get("annotations") or {}
        if isinstance(ann, str):
            ann = json.loads(ann)
        html = nlp.render_html(ann, colors_on)
        return page["raw_text"], html, json.dumps(ann, ensure_ascii=False)
    except Exception as e:
        return "", f"⚠ Could not load page: {e}", ""


def _page_choices(user_id: str) -> list[tuple[str, str]]:
    try:
        pages = nb.list_pages(user_id)
        return [(f"{p['title']} ({p['date']})", p["id"]) for p in pages]
    except Exception:
        return []

# ── Chat tab handlers ─────────────────────────────────────────────────────────

def chat_fn(message: str, history: list, user_id: str, lesson_text: str):
    if not user_id:
        yield history + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": "Please sign in to chat with your French coach."},
        ]
        return
    if not message.strip():
        yield history
        return

    system = prompts.CHAT_SYSTEM
    if lesson_text and lesson_text.strip():
        system += f"\n\nCurrent lesson context:\n{lesson_text[:500]}"

    messages = [{"role": "system", "content": system}]
    for item in history:
        if isinstance(item, dict):
            messages.append({"role": item["role"], "content": item["content"]})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            if item[0]:
                messages.append({"role": "user", "content": item[0]})
            if item[1]:
                messages.append({"role": "assistant", "content": item[1]})
    messages.append({"role": "user", "content": message})

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    for chunk in llm.chat(messages, stream=True, max_tokens=600):
        history[-1]["content"] += chunk
        yield history

# ── Text exercise handlers ────────────────────────────────────────────────────

def gen_text_exercise(lesson_text: str, user_id: str):
    if not user_id:
        return _login_prompt(), gr.State("")
    exercise = ex.generate_text_exercise(lesson_text, user_id)
    return ex.render_text_exercise(exercise), json.dumps(exercise)


def check_text_answer(user_answer: str, exercise_json: str, user_id: str):
    if not exercise_json:
        return ""
    exercise = json.loads(exercise_json)
    answer   = exercise.get("answer", "").strip().lower()
    correct  = user_answer.strip().lower() == answer
    if user_id:
        gamify.add_points(user_id, "exercise_done")
    return ex.render_exercise_feedback(correct, exercise.get("answer",""), exercise.get("explanation",""))

# ── Dialogue handlers ─────────────────────────────────────────────────────────

def gen_dialogue(lesson_text: str, user_id: str):
    if not user_id:
        return _login_prompt(), "", "{}"
    dialogue    = ex.generate_dialogue(lesson_text, user_id)
    state       = {"dialogue": dialogue, "replies": []}
    hint        = ex.get_next_user_hint(dialogue, 0)
    transcript  = ex.render_dialogue(dialogue, [])
    return transcript, f"💬 Your turn: *{hint}*", json.dumps(state)


def send_dialogue_reply(reply: str, state_json: str, user_id: str):
    if not reply.strip() or not state_json or not user_id:
        return "", "", state_json, ""
    state    = json.loads(state_json)
    dialogue = state["dialogue"]
    replies  = state["replies"]
    hint     = ex.get_next_user_hint(dialogue, len(replies))

    # Get feedback
    fb_data  = ex.dialogue_feedback(reply, hint, dialogue.get("scene",""), user_id)
    feedback = fb_data.get("feedback","")
    natural  = fb_data.get("natural_version","")
    fb_html  = (
        f'<div style="border-left:4px solid #4A90D9;padding:10px 14px;'
        f'background:#4A90D91A;border-radius:0 8px 8px 0;font-size:0.92rem">'
        f'{feedback}'
        + (f'<br><span style="color:#4A90D9;font-style:italic">💡 {natural}</span>' if natural else "")
        + '</div>'
    )

    replies.append(reply)
    state["replies"] = replies
    transcript = ex.render_dialogue(dialogue, replies)

    next_hint = ex.get_next_user_hint(dialogue, len(replies))
    hint_md   = f"💬 Your turn: *{next_hint}*" if next_hint else "🎉 Dialogue complete! Great work!"

    return transcript, hint_md, json.dumps(state), fb_html

# ── Visual exercise handlers ──────────────────────────────────────────────────

def gen_visual_exercise(image, user_id: str):
    if image is None:
        return '<div style="color:#888;padding:12px">Upload a photo to generate exercises.</div>'
    if not user_id:
        return _login_prompt()
    result = ex.generate_visual_exercise(image, user_id)
    gamify.add_points(user_id, "photo_exercise")
    return ex.render_visual_exercises(result)

# ── Pronunciation handlers ────────────────────────────────────────────────────

def get_pron_target(lesson_text: str, user_id: str):
    if not user_id:
        return _login_prompt(), "{}"
    target = ex.generate_pronunciation_target(lesson_text)
    html = (
        f'<div style="border:1px solid #e0e0e0;border-radius:8px;padding:16px;background:#fff">'
        f'<div style="font-size:1.4rem;font-family:Georgia,serif;margin-bottom:8px">'
        f'🎯 <strong>{target.get("phrase","")}</strong></div>'
        f'<div style="color:#666;margin-bottom:6px">{target.get("translation","")}</div>'
        f'<div style="color:#888;font-size:0.85rem;font-style:italic">💡 {target.get("tip","")}</div>'
        f'<button data-speak="{target.get("phrase","")}" '
        f'style="margin-top:10px;padding:6px 14px;border:1px solid #ccc;'
        f'border-radius:6px;background:#f5f5f5;cursor:pointer">🔊 Hear target phrase</button>'
        f'</div>'
    )
    return html, json.dumps(target)


def check_pronunciation(transcription: str, target_json: str, user_id: str):
    if not transcription.strip() or not target_json:
        return ""
    target  = json.loads(target_json)
    phrase  = target.get("phrase", "")
    fb_data = ex.get_pronunciation_feedback(phrase, transcription)
    if user_id:
        gamify.add_points(user_id, "pronunciation")
    return (
        f'<div style="border-left:4px solid #2e7d32;padding:12px 16px;'
        f'background:#2e7d3211;border-radius:0 8px 8px 0">'
        f'<div style="font-weight:600;margin-bottom:6px">🌟 {fb_data.get("feedback","")}</div>'
        f'<div style="font-size:0.9rem;color:#555">Focus: {fb_data.get("focus","")}</div>'
        f'<div style="font-size:0.9rem;color:#555">Tip: {fb_data.get("tip","")}</div>'
        f'</div>'
    )

# ── Daily summary handlers ────────────────────────────────────────────────────

def refresh_summary(user_id: str):
    if not user_id:
        return _login_prompt(), ""
    summary = gamify.get_daily_summary(user_id)
    total   = gamify.get_total_points(user_id)
    return summary, f"⭐ **{total} points** earned so far"

# ── Page-load handler ─────────────────────────────────────────────────────────

def on_load(profile: gr.OAuthProfile | None):
    user_id = get_user_id(profile)
    if user_id:
        try:
            gamify.try_daily_open(user_id)
        except Exception:
            pass

    if user_id is None:
        return None, gr.Markdown(visible=False), _login_prompt(), "", gr.Dropdown(choices=[])

    label   = f"👤 **{user_id}**" if user_id != "dev_user" else "🛠 *local dev*"
    html, ann = process_text(SAMPLE_TEXT, True, user_id)
    choices = _page_choices(user_id)
    return user_id, gr.Markdown(label, visible=True), html, ann, gr.Dropdown(choices=choices)

# ── Page-load JS ──────────────────────────────────────────────────────────────

PAGE_JS = """
() => {
    function setup() {
        document.addEventListener('click', function(e) {
            // TTS button
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
            const u = new SpeechSynthesisUtterance(tok.getAttribute('data-text'));
            u.lang = 'fr-FR';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
            const payload = JSON.stringify({
                text: tok.getAttribute('data-text'), gender: tok.getAttribute('data-gender'),
                pos: tok.getAttribute('data-pos'),   lemma: tok.getAttribute('data-lemma'),
            });
            const wrapper = document.getElementById('word-click-data');
            if (!wrapper) return;
            const ta = wrapper.querySelector('textarea') || wrapper.querySelector('input');
            if (!ta) return;
            const proto  = ta.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            if (setter) setter.call(ta, payload);
            ta.dispatchEvent(new Event('input', { bubbles: true }));
        });
    }
    document.readyState === 'loading'
        ? document.addEventListener('DOMContentLoaded', setup)
        : setup();
}
"""

# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(title="French Coach") as demo:

    # Shared state
    user_id_state    = gr.State(None)
    ann_state        = gr.State("")
    exercise_state   = gr.State("")
    dialogue_state   = gr.State("{}")
    pron_target_state = gr.State("{}")

    # ── Header ────────────────────────���───────────────────────────────────��───
    with gr.Row(equal_height=True):
        with gr.Column(scale=5):
            gr.Markdown("## 🇫🇷 French Coach")
        with gr.Column(scale=1, min_width=180):
            user_display = gr.Markdown(visible=False)
        if IS_SPACE:
            with gr.Column(scale=0, min_width=130):
                gr.LoginButton(min_width=120)
            with gr.Column(scale=0, min_width=110):
                gr.LogoutButton(min_width=100)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    with gr.Tabs():

        # ── Tab 1: Notebook ───────────────────────────────────────────────────
        with gr.Tab("📓 Notebook"):
            with gr.Row():
                with gr.Column(scale=1, min_width=200):
                    gr.Markdown("### Pages")
                    pages_dropdown = gr.Dropdown(
                        label="Saved pages", choices=[], interactive=True, show_label=False,
                    )
                    refresh_pages_btn = gr.Button("↻ Refresh list", size="sm")

                with gr.Column(scale=4):
                    text_input = gr.Textbox(
                        label="French text", value=SAMPLE_TEXT, lines=4,
                        placeholder="Paste your French class notes here…",
                    )
                    with gr.Row():
                        annotate_btn  = gr.Button("Annotate", variant="primary")
                        save_btn      = gr.Button("💾 Save page")
                        colors_toggle = gr.Checkbox(label="Gender colors", value=True)
                    save_status = gr.Markdown("")
                    html_out    = gr.HTML(value=_empty_card())

            with gr.Row():
                with gr.Column(scale=2):
                    gr.Markdown("### Word card")
                    word_card  = gr.HTML(value=_empty_card())
                    click_data = gr.Textbox(elem_id="word-click-data", visible=False, label="click-data")

        # ── Tab 2: Chat Coach ─────────────────────────────────────────────────
        with gr.Tab("💬 Chat Coach"):
            chatbot   = gr.Chatbot(height=380, label="French Coach")
            with gr.Row():
                chat_input = gr.Textbox(
                    placeholder="Ask anything about French — grammar, vocabulary, pronunciation…",
                    label="Your question", lines=2, scale=4,
                )
                send_btn = gr.Button("Send →", variant="primary", scale=1)
            clear_btn = gr.Button("Clear conversation", size="sm")

        # ── Tab 3: Exercises ──────────────────────────────────────────────────
        with gr.Tab("🏋️ Exercises"):
            with gr.Tabs():

                # Text exercise
                with gr.Tab("📝 Text"):
                    gen_ex_btn      = gr.Button("Generate exercise from current lesson", variant="primary")
                    text_ex_display = gr.HTML()
                    with gr.Row():
                        text_ex_answer = gr.Textbox(label="Your answer", scale=3)
                        check_ex_btn   = gr.Button("Check answer", scale=1)
                    text_ex_feedback = gr.HTML()

                # Dialogue exercise
                with gr.Tab("🗣 Dialogue"):
                    gen_dial_btn     = gr.Button("Start dialogue from current lesson", variant="primary")
                    dial_transcript  = gr.HTML()
                    dial_hint        = gr.Markdown("")
                    dial_input       = gr.Textbox(label="Your reply (French)", lines=2)
                    send_dial_btn    = gr.Button("Send reply →", variant="primary")
                    dial_feedback    = gr.HTML()

                # Visual exercise
                with gr.Tab("📷 Visual"):
                    gr.Markdown("Upload a real photo — café menu, street sign, recipe — and get French exercises from it.")
                    image_input      = gr.Image(type="pil", label="Upload photo")
                    gen_visual_btn   = gr.Button("Generate exercises from photo", variant="primary")
                    visual_display   = gr.HTML()

                # Pronunciation
                with gr.Tab("🎙 Pronunciation"):
                    get_pron_btn     = gr.Button("Get a phrase to practise", variant="primary")
                    pron_target_html = gr.HTML()
                    gr.Markdown("Read the phrase aloud, then type (or paste) what you said:")
                    pron_input       = gr.Textbox(
                        label="Your spoken text", lines=2,
                        elem_id="pronunciation-input",
                        placeholder="Type what you said…",
                    )
                    speak_btn        = gr.Button("🎙 Use microphone (Chrome/Edge)", size="sm")
                    check_pron_btn   = gr.Button("Check pronunciation", variant="primary")
                    pron_feedback    = gr.HTML()

        # ── Tab 4: Daily Summary ──────────────────────────────────────────────
        with gr.Tab("⭐ Summary"):
            refresh_summary_btn = gr.Button("Refresh summary")
            summary_display     = gr.Markdown("")
            points_display      = gr.Markdown("")

    # ── Event wiring ────────────────────────────��────────────────────────────

    # Page load
    demo.load(
        fn=on_load,
        outputs=[user_id_state, user_display, html_out, ann_state, pages_dropdown],
    )

    # Notebook
    annotate_btn.click(
        fn=process_text,
        inputs=[text_input, colors_toggle, user_id_state],
        outputs=[html_out, ann_state],
    )
    colors_toggle.change(
        fn=toggle_colors,
        inputs=[ann_state, colors_toggle, user_id_state],
        outputs=[html_out],
    )
    click_data.change(
        fn=show_word_card,
        inputs=[click_data, ann_state, user_id_state],
        outputs=[word_card, ann_state],
    )
    save_btn.click(
        fn=save_page_handler,
        inputs=[text_input, ann_state, user_id_state],
        outputs=[save_status, pages_dropdown],
    )
    refresh_pages_btn.click(
        fn=load_pages_list,
        inputs=[user_id_state],
        outputs=[pages_dropdown],
    )
    pages_dropdown.change(
        fn=load_page_handler,
        inputs=[pages_dropdown, colors_toggle, user_id_state],
        outputs=[text_input, html_out, ann_state],
    )

    # Chat
    send_btn.click(
        fn=chat_fn,
        inputs=[chat_input, chatbot, user_id_state, text_input],
        outputs=[chatbot],
    ).then(lambda: "", outputs=[chat_input])
    chat_input.submit(
        fn=chat_fn,
        inputs=[chat_input, chatbot, user_id_state, text_input],
        outputs=[chatbot],
    ).then(lambda: "", outputs=[chat_input])
    clear_btn.click(lambda: [], outputs=[chatbot])

    # Text exercise
    gen_ex_btn.click(
        fn=gen_text_exercise,
        inputs=[text_input, user_id_state],
        outputs=[text_ex_display, exercise_state],
    )
    check_ex_btn.click(
        fn=check_text_answer,
        inputs=[text_ex_answer, exercise_state, user_id_state],
        outputs=[text_ex_feedback],
    )

    # Dialogue
    gen_dial_btn.click(
        fn=gen_dialogue,
        inputs=[text_input, user_id_state],
        outputs=[dial_transcript, dial_hint, dialogue_state],
    )
    send_dial_btn.click(
        fn=send_dialogue_reply,
        inputs=[dial_input, dialogue_state, user_id_state],
        outputs=[dial_transcript, dial_hint, dialogue_state, dial_feedback],
    ).then(lambda: "", outputs=[dial_input])

    # Visual
    gen_visual_btn.click(
        fn=gen_visual_exercise,
        inputs=[image_input, user_id_state],
        outputs=[visual_display],
    )

    # Pronunciation
    get_pron_btn.click(
        fn=get_pron_target,
        inputs=[text_input, user_id_state],
        outputs=[pron_target_html, pron_target_state],
    )
    speak_btn.click(
        fn=None,
        js="""() => {
            const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
            if (!SR) { alert('Speech recognition requires Chrome or Edge.'); return; }
            const r = new SR(); r.lang = 'fr-FR'; r.interimResults = false;
            r.onresult = function(e) {
                const t = e.results[0][0].transcript;
                const w = document.getElementById('pronunciation-input');
                if (!w) return;
                const ta = w.querySelector('textarea') || w.querySelector('input');
                if (!ta) return;
                const proto = ta.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                const setter = Object.getOwnPropertyDescriptor(proto,'value')?.set;
                if (setter) setter.call(ta, t);
                ta.dispatchEvent(new Event('input',{bubbles:true}));
            };
            r.start();
        }""",
    )
    check_pron_btn.click(
        fn=check_pronunciation,
        inputs=[pron_input, pron_target_state, user_id_state],
        outputs=[pron_feedback],
    )

    # Summary
    refresh_summary_btn.click(
        fn=refresh_summary,
        inputs=[user_id_state],
        outputs=[summary_display, points_display],
    )

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", js=PAGE_JS, theme=gr.themes.Soft())
