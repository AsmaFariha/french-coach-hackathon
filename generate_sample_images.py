"""
One-off script (FIVE_DAY_PLAN.md Day 4): generate a small set of sample
images for the "no-upload" visual exercise flow.

Run ONCE, locally or inside the app container (needs HF_TOKEN):
    docker compose exec app-custom python generate_sample_images.py

Generates ~15 images via FLUX.1-schnell (HF Inference API), one per topic
category (matching nlp.detect_category's categories), saves them to
frontend/public/sample_images/, and writes a manifest.json with a
hand-written description of each scene. The description is used directly
for exercise generation — no vision model runs at request time.
"""
import json
import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

OUT_DIR = os.path.join(os.path.dirname(__file__), "frontend", "public", "sample_images")
MODEL = "black-forest-labs/FLUX.1-schnell"

# id, topic (must match nlp._CATEGORY_KEYWORDS keys), image prompt, description
# (description grounds the Coach Agent's exercise generation — written to
# match what the prompt asks for, in plain English with French vocab cues).
IMAGES = [
    ("greetings", "Greetings",
     "Two friends greeting each other with a cheek kiss outside a Parisian "
     "café, warm morning light, photorealistic",
     "Two people greet each other (la bise) outside a French café in the "
     "morning. A small chalkboard sign by the door reads 'Bonjour!' and "
     "'Bienvenue'. Vocabulary: bonjour, bonsoir, bienvenue, la bise, le matin."),

    ("numbers", "Numbers",
     "A French bakery display case with handwritten chalk price tags in "
     "euros for croissants, baguettes and pastries, photorealistic",
     "A boulangerie display case with pastries, each on a small handwritten "
     "price tag in euros (e.g. 1,20 €, 2,50 €, 3,00 €). Vocabulary: le prix, "
     "combien, euro, centime, un croissant, une baguette, numbers 1-20."),

    ("food_dining", "Food & Dining",
     "A rustic French bistro chalkboard menu on a wall, listing dishes and "
     "prices in euros, wooden table with bread and a glass of wine in front, "
     "photorealistic",
     "A bistro chalkboard menu lists dishes like soupe à l'oignon, steak "
     "frites, salade verte, and crème brûlée with prices in euros. A wooden "
     "table in front holds a basket of bread and a glass of red wine. "
     "Vocabulary: la carte, le plat, l'entrée, le dessert, la boisson, "
     "commander, l'addition."),

    ("food_dining_2", "Food & Dining",
     "An open-air French market stall piled with fresh fruits and "
     "vegetables, each in a wooden crate with a small price sign in euros "
     "per kilo, photorealistic",
     "A market stall (marché) with crates of tomatoes, pommes (apples), "
     "oranges, carottes, and pommes de terre, each with a sign showing a "
     "price per kilo in euros. Vocabulary: le marché, le kilo, les fruits, "
     "les légumes, frais/fraîche, acheter."),

    ("transportation", "Transportation",
     "A Paris Métro station platform with blue and white French signage, "
     "a train arriving, directional signs to other lines, photorealistic",
     "A Métro platform with blue-and-white signs showing the line number "
     "and direction (e.g. 'Direction Nation'), a train pulling in, and an "
     "exit sign reading 'Sortie'. Vocabulary: le métro, la station, le "
     "billet, la ligne, monter, descendre, la sortie."),

    ("family", "Family",
     "A French family of four sharing a meal together at a dining table at "
     "home, warm and cozy lighting, photorealistic",
     "A family — parents, a son, and a daughter — eating dinner together at "
     "a home dining table, smiling and talking. Vocabulary: la famille, le "
     "père, la mère, le fils, la fille, le frère, la sœur, le dîner, en "
     "famille."),

    ("time_calendar", "Time & Calendar",
     "A cozy French kitchen with a wall clock showing the time and a paper "
     "calendar with the days of the week in French, photorealistic",
     "A kitchen wall clock shows the time, next to a paper wall calendar "
     "with the days of the week written in French (lundi, mardi, mercredi, "
     "jeudi, vendredi, samedi, dimanche). Vocabulary: l'heure, aujourd'hui, "
     "demain, hier, la semaine, le jour."),

    ("shopping", "Shopping",
     "A small French clothing boutique storefront window with mannequins "
     "wearing scarves and coats, price tags visible in euros, photorealistic",
     "A boutique window display with mannequins wearing un manteau, une "
     "écharpe, and des chaussures, each with a price tag in euros, and a "
     "'Soldes' (sale) sign. Vocabulary: le magasin, le prix, les soldes, "
     "porter, acheter, la taille."),

    ("weather", "Weather",
     "A rainy street in a French town, people walking with umbrellas, grey "
     "cloudy sky, photorealistic",
     "People walk along a French street holding umbrellas (des parapluies) "
     "under a grey, rainy sky. Vocabulary: il pleut, le temps, le nuage, le "
     "parapluie, froid, le ciel."),

    ("daily_life", "Daily Life",
     "A cozy French apartment breakfast scene: a cup of coffee, a croissant "
     "on a plate, a folded newspaper, morning light through the window, "
     "photorealistic",
     "A breakfast table with un café, un croissant on a plate, and a folded "
     "newspaper, with morning sunlight coming through a window. Vocabulary: "
     "le petit-déjeuner, se réveiller, le matin, prendre le petit-déjeuner."),

    ("daily_life_2", "Daily Life",
     "A French living room in the evening, a person reading a book on a "
     "sofa with a cup of tea, a lamp on, relaxed atmosphere, photorealistic",
     "A person relaxes on a sofa in the evening, reading a book and holding "
     "a cup of tea, with a lamp lit nearby. Vocabulary: le soir, lire, se "
     "détendre, le livre, le thé, le canapé."),

    ("health", "Health",
     "A French pharmacy storefront with an illuminated green cross sign and "
     "French text on the window, photorealistic",
     "A pharmacy (la pharmacie) storefront with a glowing green cross sign "
     "and French text on the window advertising medicines. Vocabulary: la "
     "pharmacie, le médicament, malade, la santé, avoir mal."),

    ("places_directions", "Places & Directions",
     "A Paris street corner with French street name signs and a "
     "directional signpost pointing to landmarks like the Louvre and the "
     "Eiffel Tower, photorealistic",
     "A street corner has blue street-name plaques (e.g. 'Rue de Rivoli') "
     "and a signpost with arrows pointing toward 'Le Louvre' and 'La Tour "
     "Eiffel'. Vocabulary: la rue, à droite, à gauche, tout droit, près de, "
     "loin de."),

    ("hobbies_leisure", "Hobbies & Leisure",
     "People relaxing in a French park on a sunny day, some reading books, "
     "two playing chess at a stone table, others jogging, photorealistic",
     "In a park, some people read books on benches, two play chess at a "
     "stone table, and a jogger runs past. Vocabulary: le parc, lire, jouer "
     "aux échecs, courir, le temps libre, le loisir."),

    ("grammar", "Grammar",
     "An open French grammar textbook on a desk, showing a verb conjugation "
     "table, with a notebook, pen, and cup of coffee nearby, photorealistic",
     "An open textbook shows a conjugation table for a French verb (columns "
     "for je, tu, il/elle, nous, vous, ils/elles), next to a notebook, pen, "
     "and a cup of coffee on a desk. Vocabulary: le verbe, conjuguer, le "
     "présent, le sujet, la phrase."),
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    token = os.environ.get("HF_TOKEN")
    client = InferenceClient(token=token)

    manifest = []
    for image_id, topic, prompt, description in IMAGES:
        filename = f"{image_id}.jpg"
        out_path = os.path.join(OUT_DIR, filename)
        if os.path.exists(out_path):
            print(f"skip {filename} (already exists)")
        else:
            print(f"generating {filename} ({topic})...")
            img = client.text_to_image(prompt, model=MODEL)
            img = img.convert("RGB")
            img.thumbnail((640, 640))
            img.save(out_path, "JPEG", quality=82)
            print(f"  saved {out_path} ({img.size[0]}x{img.size[1]})")
        manifest.append({
            "id": image_id,
            "topic": topic,
            "filename": filename,
            "description": description,
        })

    manifest_path = os.path.join(OUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"images": manifest}, f, ensure_ascii=False, indent=2)
    print(f"wrote {manifest_path} ({len(manifest)} images)")


if __name__ == "__main__":
    main()
