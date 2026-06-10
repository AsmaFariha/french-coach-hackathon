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

CUSTOM_CSS = """
/* ── French Coach — custom theme ────────────────────────────────────────── */

/* Warm paper background */
.gradio-container { background: #FDFAF3 !important; max-width: 1280px !important; margin: 0 auto !important; }

/* Hidden JS-bridge textbox — must stay in the DOM so JS can find it */
#word-click-data    { display: none !important; }

/* Lesson items must be pointer-interactive regardless of Gradio prose styles */
.fc-lesson-item { cursor: pointer !important; }

/* Thin scrollbars for the scrollable lesson lists in the sidebar */
#fc-date-list::-webkit-scrollbar, #fc-topic-list::-webkit-scrollbar { width: 6px; }
#fc-date-list::-webkit-scrollbar-thumb, #fc-topic-list::-webkit-scrollbar-thumb {
    background: #ccc; border-radius: 3px;
}

/* Resources tab — link cards + book list */
.fc-resources { display: flex; flex-direction: column; gap: 20px; }
.fc-resource-section {
    background: #fff; border: 1px solid #eee; border-radius: 12px;
    padding: 16px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
.fc-resource-title { margin: 0 0 12px; font-size: 1.05rem; color: #002395; font-weight: 700; }
.fc-link-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px;
}
.fc-link-card {
    display: flex; align-items: center; gap: 10px; padding: 10px 12px;
    border: 1px solid #eee; border-radius: 8px; text-decoration: none !important;
    color: inherit; background: #FDFAF3; transition: border-color .15s, box-shadow .15s;
}
.fc-link-card:hover { border-color: #002395; box-shadow: 0 2px 8px rgba(0,35,149,0.10); }
.fc-link-favicon { width: 20px; height: 20px; border-radius: 4px; flex-shrink: 0; }
.fc-link-text { display: flex; flex-direction: column; min-width: 0; }
.fc-link-label {
    font-weight: 600; font-size: 0.86rem; color: #111; line-height: 1.3;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.fc-link-domain { font-size: 0.74rem; color: #888; margin-top: 1px; }
.fc-book-list { margin-top: 14px; display: flex; flex-direction: column; gap: 8px; }
.fc-book-row {
    display: flex; align-items: flex-start; gap: 10px; padding: 8px 12px;
    border-radius: 8px; background: #FDFAF3;
}
.fc-book-icon { font-size: 1.05rem; line-height: 1.5; }
.fc-book-title { font-weight: 600; font-size: 0.86rem; color: #111; display: block; }
.fc-book-meta {
    font-size: 0.76rem; color: #888; display: block; margin-top: 1px; text-transform: capitalize;
}

/* ── Header banner ──────────────────────────────────────────────────────── */
#app-header {
    background: linear-gradient(135deg, #001a6e 0%, #002395 55%, #1f4fd6 100%);
    border-radius: 16px;
    padding: 18px 24px 16px;
    margin-bottom: 0;
    box-shadow: 0 4px 14px rgba(0,35,149,0.22);
}
#app-header .block { background: transparent !important; border: none !important; box-shadow: none !important; }
#app-title h1 {
    color: #ffffff !important;
    font-size: 2.1rem;
    font-weight: 700;
    margin: 0;
    border: none;
    padding: 0;
}
#app-subtitle p { color: #d6e0ff !important; font-size: 0.92rem; margin: 4px 0 0; }
#app-header .prose, #app-header .prose * { color: #ffffff; }
#app-subtitle.prose p, #app-subtitle .prose p { color: #d6e0ff !important; }

/* Tricolor accent bar under the header */
.fc-tricolor-bar {
    height: 5px;
    border-radius: 0 0 6px 6px;
    margin: 0 0 18px;
    background: linear-gradient(90deg, #002395 0 33.33%, #ffffff 33.33% 66.66%, #ED2939 66.66% 100%);
}

/* Card spacing polish */
.gradio-container .tabitem { padding-top: 10px; }

/* Tab selected indicator */
.tabs > div > .tab-nav button.selected {
    color: #002395 !important;
    border-bottom-color: #ED2939 !important;
    font-weight: 700;
}
.tabs > div > .tab-nav button { font-size: 0.95rem; letter-spacing: 0.01em; }

/* Pages sidebar accent */
#pages-sidebar > .block { border-top: 3px solid #002395 !important; border-radius: 0 0 8px 8px; }

/* Delete confirm bar */
#delete-confirm-row {
    background: #fff8e1 !important;
    border: 1px solid #f0c040 !important;
    border-radius: 8px !important;
    padding: 4px 12px !important;
    align-items: center !important;
}

/* Word card area */
#word-card-area > .block { background: #f7f9ff; border-top: 3px solid #4A90D9 !important; border-radius: 0 0 8px 8px; }

/* Annotated text tokens */
span[data-token] { cursor: pointer; transition: filter 0.12s; }
span[data-token]:hover { filter: brightness(0.85); }

/* Gender legend pills */
.gender-legend span { border-radius: 12px; padding: 2px 10px; font-size: 0.82rem; font-weight: 600; }
"""

# ── Custom French theme ─────────────────────────────────────────────────────
# Palette taken from the French flag (bleu #002395 / rouge #ED2939) on a warm
# "paper" background — distinct from Gradio's default Soft look (Off-Brand badge).

FRENCH_BLUE = gr.themes.Color(
    c50="#eef1fc", c100="#dbe2f9", c200="#b8c6f3", c300="#94aaed",
    c400="#5a7de2", c500="#1f4fd6", c600="#002395", c700="#001b73",
    c800="#001452", c900="#000d35", c950="#00071d", name="frenchblue",
)
FRENCH_RED = gr.themes.Color(
    c50="#fdeced", c100="#fbd9db", c200="#f7b3b8", c300="#f38d94",
    c400="#f06771", c500="#ED2939", c600="#c91f2d", c700="#a01923",
    c800="#77131a", c900="#4e0c11", c950="#270609", name="frenchred",
)

FC_THEME = gr.themes.Soft(
    primary_hue=FRENCH_BLUE,
    secondary_hue=FRENCH_RED,
    neutral_hue=gr.themes.colors.slate,
    spacing_size=gr.themes.sizes.spacing_lg,
    radius_size=gr.themes.sizes.radius_lg,
    font=[gr.themes.GoogleFont("Poppins"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill="#FDFAF3",
    body_background_fill_dark="#11142b",
    block_background_fill="#ffffff",
    block_shadow="0 1px 4px rgba(0,35,149,0.06)",
    button_primary_background_fill="*primary_600",
    button_primary_background_fill_hover="*primary_700",
    button_primary_text_color="#ffffff",
    link_text_color="*primary_600",
    block_title_text_color="*primary_700",
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

    yield _basic_card(text, lemma, pos, gender), ann_json

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


def _safe_attr(s: str) -> str:
    """Escape a string for use inside an HTML attribute value."""
    return (s or "").replace("&", "&amp;").replace('"', "&quot;").replace("'", "&#39;").replace("\n", " ")


def _safe_html(s: str) -> str:
    """Escape a string for use as HTML text content."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _render_sidebar_html(user_id: str) -> str:
    """Build the full collapsible lesson-browser sidebar HTML."""
    if not user_id:
        return (
            '<div style="color:#aaa;padding:14px;font-size:0.88rem">'
            'Sign in to see your lessons.</div>'
        )
    try:
        pages = nb.list_pages(user_id)
    except Exception as exc:
        return f'<div style="color:#c00;padding:12px;font-size:0.85rem">⚠ Could not load lessons: {exc}</div>'

    # Resource-only pages (link/book lists) live in the Resources tab, not the lecture browser.
    pages = [p for p in pages if p.get("page_type") != "resource"]

    if not pages:
        return (
            '<div style="color:#aaa;padding:14px;font-size:0.88rem">'
            'No lessons saved yet.<br>Paste French text above and click 💾 Save.</div>'
        )

    import nlp as _nlp

    def _lesson_item(p: dict, extra_style: str = "") -> str:
        pid    = p["id"]
        title  = (p.get("title") or "Untitled")
        date   = p.get("date", "")
        prev   = _safe_attr(p.get("preview", ""))
        t_safe = _safe_attr(title)
        short  = title[:42] + ("…" if len(title) > 42 else "")
        return (
            f'<div class="fc-lesson-item" data-page-id="{pid}" '
            f'data-title="{t_safe}" data-date="{date}" data-preview="{prev}" '
            f'style="padding:7px 10px;margin:2px 0;border-radius:6px;cursor:pointer;'
            f'border:1px solid transparent;transition:background 0.12s,border-color 0.12s;{extra_style}">'
            f'<div style="font-weight:600;font-size:0.84rem;color:#111;line-height:1.35;pointer-events:none">{short}</div>'
            f'<div style="font-size:0.74rem;color:#888;margin-top:2px;pointer-events:none">{date}</div>'
            f'</div>'
        )

    def _group_header(label: str, count: int, open_attr: str, items: str) -> str:
        return (
            f'<details {open_attr} style="margin-bottom:2px">'
            f'<summary style="cursor:pointer;padding:4px 8px;font-size:0.74rem;'
            f'font-weight:700;text-transform:uppercase;letter-spacing:0.06em;'
            f'color:#888;user-select:none;list-style:none;'
            f'display:flex;align-items:center;gap:5px">'
            f'{label}&thinsp;<span style="font-weight:400">({count})</span>'
            f'</summary>'
            f'{items}'
            f'</details>'
        )

    # ── By Date — grouped into collapsible per-date sections ──────────────────
    date_groups = _nlp.group_by_date(pages)
    date_html = ""
    for i, (d, d_pages) in enumerate(date_groups.items()):
        items = "".join(_lesson_item(p) for p in d_pages)
        date_html += _group_header(_nlp.format_date_header(d), len(d_pages), "open" if i == 0 else "", items)

    # ── By Topic ─────────────────────────────────────────────────────────────
    grouped = _nlp.get_lesson_categories(pages)
    topic_html = ""
    for cat, cat_pages in grouped.items():
        items = "".join(_lesson_item(p) for p in cat_pages)
        topic_html += _group_header(cat, len(cat_pages), "", items)

    return (
        f'<div id="fc-sidebar-panel" style="font-family:system-ui,sans-serif">'
        # Search box
        f'<div style="margin-bottom:8px">'
        f'<input id="fc-search" type="text" placeholder="🔍 Search lessons…" '
        f'style="width:100%;box-sizing:border-box;padding:7px 10px;'
        f'border:1px solid #ddd;border-radius:6px;font-size:0.86rem;'
        f'background:#fff;outline:none;color:#111" />'
        f'</div>'
        # By Date section (open by default)
        f'<details open style="margin-bottom:6px">'
        f'<summary style="cursor:pointer;padding:5px 2px;font-weight:700;'
        f'font-size:0.84rem;color:#002395;user-select:none;list-style:none;'
        f'display:flex;align-items:center;gap:5px">'
        f'📅 By Date <span style="font-weight:400;font-size:0.75rem;color:#888">({len(pages)})</span>'
        f'</summary>'
        f'<div id="fc-date-list" style="margin-top:3px;max-height:340px;'
        f'overflow-y:auto;padding-right:4px">{date_html}</div>'
        f'</details>'
        # By Topic section (collapsed by default)
        f'<details>'
        f'<summary style="cursor:pointer;padding:5px 2px;font-weight:700;'
        f'font-size:0.84rem;color:#002395;user-select:none;list-style:none;'
        f'display:flex;align-items:center;gap:5px">'
        f'🏷️ By Topic'
        f'</summary>'
        f'<div id="fc-topic-list" style="margin-top:3px;max-height:340px;'
        f'overflow-y:auto;padding-right:4px">{topic_html}</div>'
        f'</details>'
        # Hover preview tooltip (positioned by JS)
        f'<div id="fc-preview-tip" style="display:none;position:fixed;z-index:9999;'
        f'max-width:280px;background:#1e2430;color:#e8eaf0;font-size:0.8rem;'
        f'padding:8px 12px;border-radius:7px;pointer-events:none;line-height:1.55;'
        f'box-shadow:0 4px 16px rgba(0,0,0,0.28)"></div>'
        f'</div>'
    )


def _domain(url: str) -> str:
    import urllib.parse
    try:
        netloc = urllib.parse.urlparse(url).netloc
        return netloc[4:] if netloc.startswith("www.") else netloc
    except ValueError:
        return url


def _render_resources_html(user_id: str) -> str:
    """Build a beautiful card layout for link/book resources pulled out of the notebook."""
    if not user_id:
        return '<div style="color:#aaa;padding:14px;font-size:0.9rem">Sign in to see your resources.</div>'
    try:
        pages = nb.list_resources(user_id)
    except Exception as exc:
        return f'<div style="color:#c00;padding:12px;font-size:0.9rem">⚠ Could not load resources: {exc}</div>'

    pages = [p for p in pages if p.get("links") or p.get("books")]
    if not pages:
        return (
            '<div style="color:#aaa;padding:14px;font-size:0.9rem">'
            'No resources yet. Save a page that\'s mostly links or book recommendations '
            '(e.g. "Online Resources", "Books to Read") and it\'ll show up here, '
            'beautifully laid out and out of your lecture notes.</div>'
        )

    sections = ""
    for page in pages:
        title = _safe_html(page.get("title") or "Resources")

        cards = ""
        for link in page.get("links") or []:
            url    = link.get("url", "")
            label  = _safe_html(link.get("label") or url)
            domain = _domain(url)
            cards += (
                f'<a class="fc-link-card" href="{_safe_attr(url)}" target="_blank" rel="noopener noreferrer">'
                f'<img class="fc-link-favicon" alt="" '
                f'src="https://www.google.com/s2/favicons?domain={_safe_attr(domain)}&sz=32" />'
                f'<span class="fc-link-text">'
                f'<span class="fc-link-label">{label}</span>'
                f'<span class="fc-link-domain">{_safe_html(domain)}</span>'
                f'</span></a>'
            )

        books = ""
        for book in page.get("books") or []:
            b_title = _safe_html(book.get("title", ""))
            meta    = " · ".join(x for x in [book.get("author", ""), book.get("note", "")] if x)
            books += (
                f'<div class="fc-book-row">'
                f'<span class="fc-book-icon">📖</span>'
                f'<span><span class="fc-book-title">{b_title}</span>'
                + (f'<span class="fc-book-meta">{_safe_html(meta)}</span>' if meta else "")
                + '</span></div>'
            )

        body = ""
        if cards:
            body += f'<div class="fc-link-grid">{cards}</div>'
        if books:
            body += f'<div class="fc-book-list">{books}</div>'

        sections += f'<div class="fc-resource-section"><h3 class="fc-resource-title">📚 {title}</h3>{body}</div>'

    return f'<div class="fc-resources">{sections}</div>'


def _page_btns_hidden():
    """Return gr.update calls to hide update/delete buttons and confirm row."""
    return gr.update(visible=False), gr.update(visible=False), gr.update(visible=False)


def _page_btns_visible():
    """Return gr.update calls to show update/delete buttons, hide confirm row."""
    return gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)


def save_page_handler(text: str, ann_json: str, user_id: str):
    if not user_id:
        return "Please sign in first.", _render_sidebar_html(user_id), None, "", gr.update(visible=False), *_page_btns_hidden()
    if not text.strip():
        return "Nothing to save — type or paste some French text first.", _render_sidebar_html(user_id), None, "", gr.update(visible=False), *_page_btns_hidden()
    try:
        ann = json.loads(ann_json) if ann_json else {}
        page_id, title = nb.save_page(user_id, text, ann)
        gamify.add_points(user_id, "saved_lesson")
        return f"✅ Saved as **{title}**", _render_sidebar_html(user_id), page_id, title, gr.update(visible=True), *_page_btns_visible()
    except Exception as e:
        return f"⚠ Could not save: {e}", _render_sidebar_html(user_id), None, "", gr.update(visible=False), *_page_btns_hidden()


def load_pages_list(user_id: str):
    return _render_sidebar_html(user_id)


def load_page_handler(page_id: str, colors_on: bool, user_id: str):
    if not page_id or not user_id:
        return "", "", "", None, "", gr.update(visible=False), *_page_btns_hidden()
    try:
        page = nb.get_page(page_id, user_id)
        if not page:
            return "", "", "", None, "", gr.update(visible=False), *_page_btns_hidden()
        ann = page.get("annotations") or {}
        if isinstance(ann, str):
            ann = json.loads(ann)
        html = nlp.render_html(ann, colors_on)
        return (page["raw_text"], html, json.dumps(ann, ensure_ascii=False), page_id,
                page["title"], gr.update(visible=True), *_page_btns_visible())
    except Exception as e:
        return "", f"⚠ Could not load page: {e}", "", None, "", gr.update(visible=False), *_page_btns_hidden()


def update_page_handler(text: str, ann_json: str, page_id: str, user_id: str):
    if not page_id or not user_id:
        return "⚠ No page loaded to update.", _render_sidebar_html(user_id)
    if not text.strip():
        return "Nothing to save.", _render_sidebar_html(user_id)
    try:
        ann = json.loads(ann_json) if ann_json else {}
        title = nb.update_page(page_id, user_id, text, ann)
        return f"✅ Updated **{title}**", _render_sidebar_html(user_id)
    except Exception as e:
        return f"⚠ Could not update: {e}", _render_sidebar_html(user_id)


def rename_page_handler(title: str, page_id: str, user_id: str):
    if not page_id or not user_id:
        return "⚠ No page loaded to rename.", _render_sidebar_html(user_id)
    if not title.strip():
        return "⚠ Title can't be empty.", _render_sidebar_html(user_id)
    try:
        new_title = nb.update_title(page_id, user_id, title)
        return f"✅ Renamed to **{new_title}**", _render_sidebar_html(user_id)
    except Exception as e:
        return f"⚠ Could not rename: {e}", _render_sidebar_html(user_id)


def delete_page_handler(page_id: str, user_id: str):
    if not page_id or not user_id:
        return "⚠ No page selected.", _render_sidebar_html(user_id), "", "", "", None, "", gr.update(visible=False), *_page_btns_hidden()
    try:
        nb.delete_page(page_id, user_id)
        return (
            "🗑️ Page deleted.",
            _render_sidebar_html(user_id),
            "", "", "",
            None,
            "", gr.update(visible=False),
            *_page_btns_hidden(),
        )
    except Exception as e:
        return (f"⚠ Could not delete: {e}", _render_sidebar_html(user_id), "", "", "", page_id,
                gr.update(), gr.update(), *_page_btns_visible())

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
        return None, gr.Markdown(visible=False), _login_prompt(), "", _render_sidebar_html(None), _render_resources_html(None)

    label   = f"👤 **{user_id}**" if user_id != "dev_user" else "🛠 *local dev*"
    html, ann = process_text(SAMPLE_TEXT, True, user_id)
    return (user_id, gr.Markdown(label, visible=True), html, ann,
            _render_sidebar_html(user_id), _render_resources_html(user_id))

# ── Sidebar click handler (gr.HTML.click + js_on_load trigger) ───────────────

def sidebar_click_handler(colors_on: bool, user_id: str, evt: gr.EventData):
    """Called by pages_sidebar_html.click(); evt.page_id comes from trigger()."""
    try:
        page_id = evt.page_id
    except (AttributeError, KeyError, TypeError):
        page_id = None
    return load_page_handler(page_id, colors_on, user_id)


# js_on_load runs inside the gr.HTML Svelte component context.
# `element` = the component root DOM node; `trigger` = Gradio event dispatcher.
# Event delegation on `element` survives value re-renders because the listeners
# live on the container, not on individual lesson items.
SIDEBAR_JS_ON_LOAD = """
element.addEventListener('click', function(e) {
    var item = e.target.closest('.fc-lesson-item');
    if (!item) return;
    e.stopPropagation();
    element.querySelectorAll('.fc-lesson-item').forEach(function(el) {
        el.style.background = '';
        el.style.borderColor = 'transparent';
    });
    item.style.background  = 'rgba(0,35,149,0.08)';
    item.style.borderColor = 'rgba(0,35,149,0.28)';
    var tip = element.querySelector('#fc-preview-tip');
    if (tip) tip.style.display = 'none';
    trigger('click', {page_id: item.getAttribute('data-page-id')});
});
element.addEventListener('input', function(e) {
    if (!e.target || e.target.id !== 'fc-search') return;
    var q = (e.target.value || '').toLowerCase().trim();
    element.querySelectorAll('.fc-lesson-item').forEach(function(el) {
        var title = (el.getAttribute('data-title') || '').toLowerCase();
        el.style.display = (!q || title.includes(q)) ? '' : 'none';
    });
});
element.addEventListener('mouseover', function(e) {
    var item = e.target.closest('.fc-lesson-item');
    var tip  = element.querySelector('#fc-preview-tip');
    if (!tip) return;
    if (item) {
        var prev = item.getAttribute('data-preview') || '';
        if (prev) { tip.textContent = prev; tip.style.display = 'block'; }
    } else if (!e.target.closest('#fc-preview-tip')) {
        tip.style.display = 'none';
    }
});
element.addEventListener('mousemove', function(e) {
    var tip = element.querySelector('#fc-preview-tip');
    if (tip && tip.style.display !== 'none') {
        tip.style.left = Math.min(e.clientX + 16, window.innerWidth - 296) + 'px';
        tip.style.top  = (e.clientY - 8) + 'px';
    }
});
element.addEventListener('mouseout', function(e) {
    if (!e.target.closest) return;
    if (e.target.closest('.fc-lesson-item') &&
            !(e.relatedTarget && e.relatedTarget.closest && e.relatedTarget.closest('.fc-lesson-item'))) {
        var tip = element.querySelector('#fc-preview-tip');
        if (tip) tip.style.display = 'none';
    }
});
"""

# ── Page-load JS ──────────────────────────────────────────────────────────────

PAGE_JS = """
() => {
    function setup() {
        // ── Document click: TTS buttons + word tokens ─────────────────────────
        // Sidebar lesson clicks are handled inside SIDEBAR_JS_ON_LOAD via trigger().
        document.addEventListener('click', function(e) {

            // TTS speak button
            const ttsBtn = e.target.closest('[data-speak]');
            if (ttsBtn) {
                e.stopPropagation();
                const u = new SpeechSynthesisUtterance(ttsBtn.getAttribute('data-speak'));
                u.lang = 'fr-FR';
                window.speechSynthesis.cancel();
                window.speechSynthesis.speak(u);
                return;
            }

            // Word token click → TTS + word card
            const tok = e.target.closest('[data-token]');
            if (!tok) return;
            const u = new SpeechSynthesisUtterance(tok.getAttribute('data-text'));
            u.lang = 'fr-FR';
            window.speechSynthesis.cancel();
            window.speechSynthesis.speak(u);
            const payload = JSON.stringify({
                text: tok.getAttribute('data-text'), gender: tok.getAttribute('data-gender'),
                pos:  tok.getAttribute('data-pos'),  lemma:  tok.getAttribute('data-lemma'),
            });
            const wrapper = document.getElementById('word-click-data');
            if (!wrapper) return;
            const ta = wrapper.querySelector('textarea') || wrapper.querySelector('input');
            if (!ta) return;
            const proto  = ta.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
            const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set;
            if (setter) setter.call(ta, payload);
            ta.dispatchEvent(new InputEvent('input', { bubbles: true }));
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
    user_id_state       = gr.State(None)
    ann_state           = gr.State("")
    exercise_state      = gr.State("")
    dialogue_state      = gr.State("{}")
    pron_target_state   = gr.State("{}")
    current_page_id     = gr.State(None)   # page currently loaded in the editor

    # ── Header ───────────────────────────────────────────────────────────────
    with gr.Row(equal_height=True, elem_id="app-header"):
        with gr.Column(scale=5, elem_id="app-title"):
            gr.Markdown("# 🇫🇷 French Coach")
            gr.Markdown(
                "Your daily French notebook — notes, gender at a glance, "
                "and practice from today's lesson.",
                elem_id="app-subtitle",
            )
        with gr.Column(scale=1, min_width=180):
            user_display = gr.Markdown(visible=False)
        if IS_SPACE:
            with gr.Column(scale=0, min_width=130):
                gr.LoginButton(min_width=120)
            with gr.Column(scale=0, min_width=110):
                gr.LogoutButton(min_width=100)
    gr.HTML('<div class="fc-tricolor-bar"></div>')

    # ── Tabs ─────────────────────────────────────────────────────────────────
    with gr.Tabs():

        # ── Tab 1: Notebook ───────────────────────────────────────────────────
        with gr.Tab("📓 Notebook"):
            with gr.Row():

                # Left sidebar — smart lesson browser
                with gr.Column(scale=1, min_width=260, elem_id="pages-sidebar"):
                    gr.Markdown("### 📄 Lessons")
                    pages_sidebar_html = gr.HTML(
                        value='<div style="color:#aaa;padding:14px;font-size:0.88rem">Loading…</div>',
                        js_on_load=SIDEBAR_JS_ON_LOAD,
                    )
                    refresh_sidebar_btn = gr.Button("↻ Refresh", size="sm")

                # Main editing area
                with gr.Column(scale=4):
                    # Title — auto-generated on save, editable afterward
                    with gr.Row():
                        title_input = gr.Textbox(
                            label="📝 Title", value="",
                            placeholder="A title is generated automatically when you save…",
                            scale=4, container=True,
                        )
                        rename_btn = gr.Button("✏️ Rename", visible=False, scale=1, min_width=100)

                    text_input = gr.Textbox(
                        label="French text", value=SAMPLE_TEXT, lines=4,
                        placeholder="Paste your French class notes here…",
                    )

                    # Primary actions row
                    with gr.Row():
                        annotate_btn  = gr.Button("Annotate", variant="primary")
                        save_btn      = gr.Button("💾 Save as new page")
                        colors_toggle = gr.Checkbox(label="Gender colors", value=True)

                    # Page management row — only visible when a saved page is loaded
                    with gr.Row():
                        update_btn = gr.Button("✏️ Update page", visible=False, variant="secondary")
                        delete_btn = gr.Button("🗑️ Delete page", visible=False)

                    # Delete confirmation bar (hidden until delete clicked)
                    with gr.Row(visible=False, elem_id="delete-confirm-row") as delete_confirm_row:
                        gr.Markdown("⚠️ **Delete this page?** All exercises saved to it will also be removed.")
                        confirm_delete_btn = gr.Button("Yes, delete", variant="stop", scale=0, min_width=110)
                        cancel_delete_btn  = gr.Button("Cancel", scale=0, min_width=80)

                    save_status = gr.Markdown("")
                    html_out    = gr.HTML(value=_empty_card())

            # Word card row
            with gr.Row():
                with gr.Column(scale=2, elem_id="word-card-area"):
                    gr.Markdown("### 🔤 Word card")
                    word_card  = gr.HTML(value=_empty_card())
                    click_data = gr.Textbox(elem_id="word-click-data", visible=True, label="click-data")

        # ── Tab 2: Resources ──────────────────────────────────────────────────
        with gr.Tab("📚 Resources"):
            gr.Markdown(
                "Links and book recommendations from your notebook, kept separate "
                "from your lesson notes."
            )
            refresh_resources_btn = gr.Button("↻ Refresh", size="sm")
            resources_display = gr.HTML(value="")

        # ── Tab 3: Chat Coach ─────────────────────────────────────────────────
        with gr.Tab("💬 Chat Coach"):
            chatbot   = gr.Chatbot(height=380, label="French Coach")
            with gr.Row():
                chat_input = gr.Textbox(
                    placeholder="Ask anything about French — grammar, vocabulary, pronunciation…",
                    label="Your question", lines=2, scale=4,
                )
                send_btn = gr.Button("Send →", variant="primary", scale=1)
            clear_btn = gr.Button("Clear conversation", size="sm")

        # ── Tab 4: Exercises ──────────────────────────────────────────────────
        with gr.Tab("🏋️ Exercises"):
            with gr.Tabs():

                with gr.Tab("📝 Text"):
                    gen_ex_btn      = gr.Button("Generate exercise from current lesson", variant="primary")
                    text_ex_display = gr.HTML()
                    with gr.Row():
                        text_ex_answer = gr.Textbox(label="Your answer", scale=3)
                        check_ex_btn   = gr.Button("Check answer", scale=1)
                    text_ex_feedback = gr.HTML()

                with gr.Tab("🗣 Dialogue"):
                    gen_dial_btn     = gr.Button("Start dialogue from current lesson", variant="primary")
                    dial_transcript  = gr.HTML()
                    dial_hint        = gr.Markdown("")
                    dial_input       = gr.Textbox(label="Your reply (French)", lines=2)
                    send_dial_btn    = gr.Button("Send reply →", variant="primary")
                    dial_feedback    = gr.HTML()

                with gr.Tab("📷 Visual"):
                    gr.Markdown("Upload a real photo — café menu, street sign, recipe — and get French exercises from it.")
                    image_input      = gr.Image(type="pil", label="Upload photo")
                    gen_visual_btn   = gr.Button("Generate exercises from photo", variant="primary")
                    visual_display   = gr.HTML()

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

        # ── Tab 5: Daily Summary ──────────────────────────────────────────────
        with gr.Tab("⭐ Summary"):
            refresh_summary_btn = gr.Button("Refresh summary")
            summary_display     = gr.Markdown("")
            points_display      = gr.Markdown("")

    # ── Event wiring ─────────────────────────────────────────────────────────

    # Page load
    demo.load(
        fn=on_load,
        outputs=[user_id_state, user_display, html_out, ann_state, pages_sidebar_html, resources_display],
    )

    # Resources tab
    refresh_resources_btn.click(
        fn=_render_resources_html,
        inputs=[user_id_state],
        outputs=[resources_display],
    )

    # Notebook — annotate + toggle
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
    click_data.input(
        fn=show_word_card,
        inputs=[click_data, ann_state, user_id_state],
        outputs=[word_card, ann_state],
    )

    # Notebook — save as new page
    save_btn.click(
        fn=save_page_handler,
        inputs=[text_input, ann_state, user_id_state],
        outputs=[save_status, pages_sidebar_html, current_page_id, title_input, rename_btn,
                 update_btn, delete_btn, delete_confirm_row],
    )

    # Notebook — update existing page
    update_btn.click(
        fn=update_page_handler,
        inputs=[text_input, ann_state, current_page_id, user_id_state],
        outputs=[save_status, pages_sidebar_html],
    )

    # Notebook — rename (edit auto-generated title)
    rename_btn.click(
        fn=rename_page_handler,
        inputs=[title_input, current_page_id, user_id_state],
        outputs=[save_status, pages_sidebar_html],
    )

    # Notebook — delete flow (two-step)
    delete_btn.click(
        fn=lambda: (gr.update(visible=True), gr.update(visible=False)),
        outputs=[delete_confirm_row, delete_btn],
    )
    cancel_delete_btn.click(
        fn=lambda: (gr.update(visible=False), gr.update(visible=True)),
        outputs=[delete_confirm_row, delete_btn],
    )
    confirm_delete_btn.click(
        fn=delete_page_handler,
        inputs=[current_page_id, user_id_state],
        outputs=[save_status, pages_sidebar_html, text_input, html_out, ann_state,
                 current_page_id, title_input, rename_btn, update_btn, delete_btn, delete_confirm_row],
    )

    # Notebook — sidebar refresh button
    refresh_sidebar_btn.click(
        fn=load_pages_list,
        inputs=[user_id_state],
        outputs=[pages_sidebar_html],
    )
    # Sidebar lesson click — js_on_load calls trigger('click', {page_id}); Python reads evt.page_id
    pages_sidebar_html.click(
        fn=sidebar_click_handler,
        inputs=[colors_toggle, user_id_state],
        outputs=[text_input, html_out, ann_state, current_page_id, title_input, rename_btn,
                 update_btn, delete_btn, delete_confirm_row],
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
    demo.launch(server_name="0.0.0.0", js=PAGE_JS, css=CUSTOM_CSS, theme=FC_THEME)
