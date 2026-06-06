import gradio as gr
import spacy
from dotenv import load_dotenv

load_dotenv()
nlp = spacy.load("fr_core_news_sm")

def analyse(text):
    doc = nlp(text)
    out = []
    for tok in doc:
        gender = tok.morph.get("Gender")
        out.append(f"{tok.text} — {tok.pos_} — gender: {gender or '—'}")
    return "\n".join(out)

with gr.Blocks() as demo:
    gr.Markdown("# French Coach — smoke test")
    inp = gr.Textbox(label="French text", value="Le chat noir dort sur la table.")
    out = gr.Textbox(label="Analysis", lines=8)
    gr.Button("Analyse").click(analyse, inp, out)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0")
