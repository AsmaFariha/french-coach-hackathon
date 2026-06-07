import spacy

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("fr_core_news_sm")
    return _nlp


def annotate(text: str) -> dict:
    """Run spaCy annotation. Returns annotation dict matching DB JSONB schema."""
    doc = get_nlp()(text)
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
    return {"tokens": tokens, "meanings": {}}


MASC_COLOR = "#4A90D9"
FEM_COLOR  = "#D96B8A"


def render_html(annotations: dict, colors_on: bool) -> str:
    tokens = annotations.get("tokens", [])
    parts  = []
    for tok in tokens:
        if tok["is_space"]:
            parts.append(tok.get("whitespace", " "))
            continue
        text   = tok["text"]
        gender = tok.get("gender")
        pos    = tok.get("pos", "")
        lemma  = tok.get("lemma", text)

        styles = ["cursor:pointer", "padding:1px 3px", "border-radius:3px"]
        if colors_on and pos == "NOUN":
            if gender == "Masc":
                styles += [f"background:{MASC_COLOR}1A", f"border-bottom:2px solid {MASC_COLOR}"]
            elif gender == "Fem":
                styles += [f"background:{FEM_COLOR}1A", f"border-bottom:2px solid {FEM_COLOR}"]

        safe = lambda s: (s or "").replace('"', "&quot;")
        parts.append(
            f'<span class="tok" style="{";".join(styles)}" '
            f'data-token="1" data-text="{safe(text)}" '
            f'data-gender="{safe(gender)}" data-pos="{safe(pos)}" '
            f'data-lemma="{safe(lemma)}">{text}</span>'
        )
        if tok.get("whitespace"):
            parts.append(tok["whitespace"])

    return (
        '<div id="fc-text" style="font-size:1.15rem;line-height:2;font-family:Georgia,serif;'
        'padding:12px;border:1px solid #e0e0e0;border-radius:6px;background:#fffef9;min-height:80px">'
        + "".join(parts)
        + "</div>"
        + (_legend(colors_on))
    )


def _legend(colors_on: bool) -> str:
    if not colors_on:
        return ""
    return (
        f'<div style="margin-top:8px;font-size:0.8rem;color:#888">'
        f'<span style="border-bottom:2px solid {MASC_COLOR};padding:0 4px">masc.</span>'
        f'&nbsp;&nbsp;'
        f'<span style="border-bottom:2px solid {FEM_COLOR};padding:0 4px">fém.</span>'
        f'</div>'
    )
