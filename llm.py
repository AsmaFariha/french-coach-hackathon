"""
LLM backend router — controlled by LLM_BACKEND env var:

  huggingface_inference  HF InferenceClient (local dev, uses HF_TOKEN)
  zerogpu                @spaces.GPU + transformers (HF Space deploy only)
  openbmb                OpenBMB free API via OpenAI client (legacy / fallback)

Vision always uses the OpenBMB vision endpoint (MiniCPM-V not yet on HF Inference).
"""
import os
import json
import logging
from dotenv import load_dotenv
import prompts

load_dotenv()
logger = logging.getLogger(__name__)

BACKEND  = os.environ.get("LLM_BACKEND", "huggingface_inference")
HF_MODEL = os.environ.get("HUGGINGFACE_MODEL", "openbmb/MiniCPM4.1-8B-Instruct")
HF_TOKEN = os.environ.get("HF_TOKEN")

# ── Backend 1: HF InferenceClient (local dev) ─────────────────────────────────

_hf_client = None

def _hf():
    global _hf_client
    if _hf_client is None:
        from huggingface_hub import InferenceClient   # huggingface_hub>=0.21
        _hf_client = InferenceClient(model=HF_MODEL, token=HF_TOKEN)
    return _hf_client


def _hf_chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    try:
        resp = _hf().chat_completion(
            messages=messages, max_tokens=max_tokens,
            stream=stream, temperature=0.7,
        )
        if stream:
            def _gen():
                for chunk in resp:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield delta
            return _gen()
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("HF InferenceClient error: %s", e)
        msg = f"⚠ HF Inference unavailable ({e})"
        return (x for x in [msg]) if stream else msg


# ── Backend 2: ZeroGPU (HF Space deploy only) ────────────────────────────────
# The @spaces.GPU decorator must be applied at module load time, so we try to
# set it up eagerly when BACKEND=zerogpu. On local dev this import will fail
# gracefully and we fall back to openbmb.

_zerogpu_fn = None

if BACKEND == "zerogpu":
    try:
        import spaces                                          # only on HF Space
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        _zgpu_tok   = None
        _zgpu_model = None

        @spaces.GPU
        def _zgpu_generate(messages_json: str, max_tokens: int) -> str:
            """Runs on GPU. messages_json is JSON string to avoid pickling issues."""
            global _zgpu_tok, _zgpu_model
            if _zgpu_model is None:
                _zgpu_tok   = AutoTokenizer.from_pretrained(HF_MODEL, trust_remote_code=True)
                _zgpu_model = AutoModelForCausalLM.from_pretrained(
                    HF_MODEL, trust_remote_code=True,
                    torch_dtype=torch.bfloat16,
                ).eval()
            msgs    = json.loads(messages_json)
            text    = _zgpu_tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            inputs  = _zgpu_tok(text, return_tensors="pt").to(_zgpu_model.device)
            with torch.no_grad():
                out = _zgpu_model.generate(
                    **inputs, max_new_tokens=max_tokens,
                    do_sample=True, temperature=0.7,
                )
            return _zgpu_tok.decode(
                out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True
            )

        _zerogpu_fn = _zgpu_generate
        logger.info("ZeroGPU backend initialised for model %s", HF_MODEL)

    except ImportError as e:
        logger.warning("ZeroGPU setup failed (not on HF Space?): %s — falling back to openbmb", e)


def _zerogpu_chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    if _zerogpu_fn is None:
        # Graceful fallback when not on a Space
        return _openbmb_chat(messages, stream, max_tokens)
    try:
        result = _zerogpu_fn(json.dumps(messages), max_tokens)
        if stream:
            return (x for x in [result])
        return result
    except Exception as e:
        logger.error("ZeroGPU error: %s", e)
        msg = f"⚠ ZeroGPU error ({e})"
        return (x for x in [msg]) if stream else msg


# ── Backend 3: OpenBMB legacy (original free API) ─────────────────────────────

_openbmb_text_client = None

def _openbmb_text():
    global _openbmb_text_client
    if _openbmb_text_client is None:
        from openai import OpenAI
        _openbmb_text_client = OpenAI(
            api_key=os.environ.get("MINICPM_API_KEY", "sk-no-key"),
            base_url=os.environ.get("MINICPM_API_BASE", "http://35.203.155.71:8001/v1"),
        )
    return _openbmb_text_client


def _openbmb_chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    client = _openbmb_text()
    model  = os.environ.get("MINICPM_MODEL", "MiniCPM4-8B")
    try:
        resp = client.chat.completions.create(
            model=model, messages=messages,
            stream=stream, temperature=0.7, max_tokens=max_tokens,
        )
        if stream:
            def _gen():
                for chunk in resp:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            return _gen()
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("OpenBMB error: %s", e)
        msg = f"⚠ OpenBMB API unavailable ({e})"
        return (x for x in [msg]) if stream else msg


# ── Public API ─────────────────────────────────────────────────────────────────

def chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    """Route to the active LLM backend. Returns str or generator of str chunks."""
    if BACKEND == "huggingface_inference":
        return _hf_chat(messages, stream, max_tokens)
    elif BACKEND == "zerogpu":
        return _zerogpu_chat(messages, stream, max_tokens)
    else:
        return _openbmb_chat(messages, stream, max_tokens)


def chat_json(system: str, user: str, fallback: dict | None = None) -> dict:
    """Call LLM and parse JSON response. Returns fallback dict on any error."""
    raw = chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    if isinstance(raw, str) and raw.startswith("⚠"):
        return fallback or {}
    try:
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```")
            text  = parts[1].lstrip("json").strip() if len(parts) > 1 else text
        return json.loads(text)
    except Exception as e:
        logger.error("JSON parse error: %s\nRaw: %.200s", e, raw)
        return fallback or {}


# ── Vision (stays on OpenBMB — MiniCPM-V not yet on HF Inference) ─────────────

_vision_client = None

def _vision():
    global _vision_client
    if _vision_client is None:
        from openai import OpenAI
        _vision_client = OpenAI(
            api_key=os.environ.get("MINICPM_API_KEY", "sk-no-key"),
            base_url=os.environ.get("MINICPM_VISION_BASE", "http://35.203.155.71:8003/v1"),
        )
    return _vision_client


def vision_chat(image_b64: str, prompt: str) -> str:
    """Send image + prompt to vision LLM. Returns description string."""
    client = _vision()
    model  = os.environ.get("MINICPM_VISION_MODEL", "MiniCPM-V-4.6")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                {"type": "text", "text": prompt},
            ]}],
            max_tokens=512,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("Vision LLM error: %s", e)
        return f"⚠ Vision API unavailable ({e}). Check the OpenBMB vision endpoint."


# ── Convenience wrappers ───────────────────────────────────────────────────────

def get_word_meaning(text: str, lemma: str, pos: str, gender: str) -> dict:
    return chat_json(
        prompts.WORD_MEANING_SYSTEM,
        prompts.word_meaning_user(text, lemma, pos, gender),
        fallback={"meaning": "(API offline — try again later)", "grammar": ""},
    )


def generate_page_title(snippet: str) -> str:
    result = chat([
        {"role": "system", "content": prompts.PAGE_TITLE_SYSTEM},
        {"role": "user",   "content": snippet[:300]},
    ])
    if isinstance(result, str) and result.startswith("⚠"):
        return snippet.split("\n")[0][:60] or "Untitled Lesson"
    return (result or "Untitled Lesson").strip()[:80]
