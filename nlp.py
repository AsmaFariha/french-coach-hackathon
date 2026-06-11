import datetime
import spacy

_nlp = None

def get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("fr_core_news_sm")
    return _nlp


def word_info(word: str) -> dict:
    """Lemma + POS for a single word (instant, offline) — used by the Gender
    Checker tool (Day 5) to give the LLM a starting point. Gender itself is
    NOT reliable from spaCy on an isolated word (no determiner/agreement
    context to disambiguate, e.g. "pomme" alone tags Masc though it's
    feminine), so gender/articles are determined by the LLM instead."""
    word = word.strip()
    doc = get_nlp()(word)
    tok = next((t for t in doc if not t.is_space), None)
    if tok is None:
        return {"word": word, "lemma": word, "pos": None}
    return {"word": tok.text, "lemma": tok.lemma_, "pos": tok.pos_}


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


# ── Category detection ────────────────────────────────────────────────────────

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Greetings": [
        "bonjour", "salut", "bonsoir", "bonne nuit", "au revoir", "à bientôt",
        "enchanté", "bienvenue", "merci", "s'il vous plaît", "excusez", "pardon",
        "comment allez", "comment vas", "je m'appelle", "présentations",
    ],
    "Numbers": [
        "zéro", "un ", "deux", "trois", "quatre", "cinq", "six", "sept", "huit",
        "neuf", "dix", "vingt", "trente", "cent", "mille", "nombre", "chiffre",
        "numéro", "combien", "compter", "premier", "deuxième",
    ],
    "Grammar": [
        "verbe", "nom ", "adjectif", "adverbe", "conjugaison", "accord",
        "pluriel", "singulier", "genre", "article", "pronom", "préposition",
        "infinitif", "participe", "subjonctif", "imparfait", "passé composé",
        "futur", "conditionnel", "être", "avoir", "aller", "faire",
        "féminin", "masculin", "accord",
    ],
    "Food & Dining": [
        "manger", "restaurant", "café", "menu", "plat", "entrée", "dessert",
        "boisson", "cuisine", "repas", "boire", "faim", "soif", "commander",
        "addition", "boulangerie", "pain", "fromage", "vin", "eau", "salade",
        "viande", "poisson", "légume", "fruit",
    ],
    "Transportation": [
        "bus", "métro", "train", "voiture", "vélo", "taxi", "avion",
        "gare", "aéroport", "route", "voyager", "billet", "station",
        "conduire", "prendre", "ligne", "direction", "quai", "arrêt",
    ],
    "Family": [
        "famille", "mère", "père", "frère", "sœur", "enfant", "parent",
        "grand-mère", "grand-père", "fils", "fille", "mari", "femme",
        "oncle", "tante", "cousin", "neveu", "nièce", "bébé",
    ],
    "Time & Calendar": [
        "heure", "minute", "seconde", "jour", "semaine", "mois", "année",
        "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche",
        "janvier", "février", "mars", "avril", "mai", "juin",
        "aujourd'hui", "demain", "hier", "maintenant", "matin", "soir", "midi",
    ],
    "Shopping": [
        "acheter", "magasin", "prix", "argent", "euro", "boutique", "marché",
        "vêtement", "soldes", "payer", "cher", "bon marché", "taille",
        "coûter", "centimes", "monnaie", "caisse", "vendeur",
    ],
    "Weather": [
        "temps", "pluie", "pleuvoir", "soleil", "ensoleillé", "nuage",
        "froid", "chaud", "neige", "neiger", "vent", "température",
        "météo", "saison", "orage", "brouillard", "degré",
    ],
    "Daily Life": [
        "maison", "appartement", "chambre", "salon", "salle de bain",
        "dormir", "travailler", "école", "bureau", "quotidien",
        "matin", "réveiller", "habiter", "vivre", "routine",
    ],
    "Health": [
        "santé", "médecin", "docteur", "hôpital", "pharmacie", "médicament",
        "malade", "douleur", "mal", "fièvre", "rhume", "allergie",
        "rendez-vous", "symptôme", "corps",
    ],
    "Places & Directions": [
        "tout droit", "tournez à droite", "tournez à gauche", "prenez la rue",
        "à droite", "à gauche", "rue ", "avenue ", "boulevard", "arrondissement",
        "carte routière", "plan de ville", "itinéraire", "carrefour",
        "code postal", "adresse postale",
    ],
    "Hobbies & Leisure": [
        "sport", "musique", "cinéma", "lecture", "voyager", "jouer",
        "regarder", "écouter", "aimer", "loisir", "vacances", "week-end",
        "danse", "peinture", "jardinage",
    ],
}

_NER_TO_CATEGORY = {
    "LOC": "Places & Directions",
    "GPE": "Places & Directions",
    "FAC": "Places & Directions",
}


def detect_category(text: str) -> str:
    """Return the most likely topic category for a French lesson excerpt.

    Combines keyword scoring with a light spaCy NER pass.  Runs in <5 ms
    on a 300-char snippet because the model is already loaded.
    """
    if not text:
        return "General"
    text_lower = text.lower()
    scores: dict[str, int] = {}

    # Keyword scoring
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score:
            scores[cat] = score

    # NER reinforcement: only boost a category that already has keyword matches.
    # This prevents NER alone from overriding clear keyword signals.
    try:
        doc = get_nlp()(text[:200])
        for ent in doc.ents:
            bonus_cat = _NER_TO_CATEGORY.get(ent.label_)
            if bonus_cat and bonus_cat in scores:
                scores[bonus_cat] += 1
    except Exception:
        pass

    if not scores:
        return "General"
    return max(scores, key=scores.__getitem__)


def get_lesson_categories(pages: list[dict]) -> dict[str, list[dict]]:
    """Group a list of page dicts by their detected category.

    Each page dict must have at least {id, title, date, category}.
    Returns an ordered dict (alphabetical by category name) mapping
    category → [page, ...].
    """
    groups: dict[str, list[dict]] = {}
    for page in pages:
        cat = page.get("category") or "General"
        groups.setdefault(cat, []).append(page)
    return dict(sorted(groups.items()))


def group_by_date(pages: list[dict]) -> dict[str, list[dict]]:
    """Group a list of page dicts by their date (most recent first).

    Each page dict must have at least {id, title, date}. Pages are assumed
    to already be ordered newest-first within each date group.
    """
    groups: dict[str, list[dict]] = {}
    for page in pages:
        d = page.get("date") or "Undated"
        groups.setdefault(d, []).append(page)
    return dict(sorted(groups.items(), key=lambda kv: kv[0], reverse=True))


def format_date_header(date_str: str) -> str:
    """Render an ISO date string ('2026-06-09') as a friendly header ('Mon, Jun 9, 2026')."""
    try:
        d = datetime.date.fromisoformat(date_str)
        return d.strftime("%a, %b %-d, %Y")
    except (ValueError, TypeError):
        return date_str or "Undated"
