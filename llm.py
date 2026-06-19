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
import re
import time
from dotenv import load_dotenv
import prompts

load_dotenv()
logger = logging.getLogger(__name__)

BACKEND           = os.environ.get("LLM_BACKEND", "huggingface_inference")
HF_MODEL          = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-7B-Instruct")
HF_FALLBACK_MODEL = os.environ.get("HF_FALLBACK_MODEL", "Qwen/Qwen2.5-7B-Instruct")
HF_TOKEN          = os.environ.get("HF_TOKEN")

# ── Backend 1: HF InferenceClient (local dev) ─────────────────────────────────

_hf_clients: dict[str, object] = {}

def _hf(model: str):
    if model not in _hf_clients:
        from huggingface_hub import InferenceClient
        _hf_clients[model] = InferenceClient(model=model, token=HF_TOKEN)
    return _hf_clients[model]


def _hf_call(model: str, messages: list[dict], stream: bool, max_tokens: int):
    """Single attempt. Raises on any error including empty content."""
    resp = _hf(model).chat_completion(
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
    content = resp.choices[0].message.content
    if not content:
        raise ValueError("empty completion from model")
    return content


def _hf_chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    """Try HF_MODEL; if it fails, try HF_FALLBACK_MODEL; then return error msg."""
    models = list(dict.fromkeys([HF_MODEL, HF_FALLBACK_MODEL]))
    last_err = None
    for model in models:
        try:
            return _hf_call(model, messages, stream, max_tokens)
        except Exception as e:
            logger.warning("HF model %s failed: %s", model, e)
            last_err = e
    logger.error("All HF models failed. Last error: %s", last_err)
    msg = "⚠ LLM unavailable — please try again in a moment."
    return (x for x in [msg]) if stream else msg


# ── Backend 2: ZeroGPU (HF Space deploy only) ────────────────────────────────
# The @spaces.GPU function lives in app_custom.py (the HF app_file) because
# the ZeroGPU static scan only inspects app_file, not imported modules.
# app_custom.py calls register_gpu_fn() at startup to wire it in.

_zerogpu_fn = None


def register_gpu_fn(fn):
    """Called by app_custom.py to inject the @spaces.GPU generate function."""
    global _zerogpu_fn
    _zerogpu_fn = fn
    logger.info("ZeroGPU generate function registered: %s", fn.__name__)


def _zerogpu_chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    if _zerogpu_fn is None:
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


# ── Backend 3: OpenBMB free API ───────────────────────────────────────────────

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
        logger.warning("OpenBMB API unreachable (%s) — falling back to HF Inference", e)
        return _hf_chat(messages, stream, max_tokens)


# ── Public API ─────────────────────────────────────────────────────────────────

def chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    """Route to the active LLM backend. Returns str or generator of str chunks."""
    if BACKEND == "huggingface_inference":
        return _hf_chat(messages, stream, max_tokens)
    elif BACKEND == "zerogpu":
        return _zerogpu_chat(messages, stream, max_tokens)
    else:
        return _openbmb_chat(messages, stream, max_tokens)


def _try_parse_json(raw: str) -> dict | None:
    """Try several strategies to extract a JSON dict from an LLM response."""
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        text = parts[1].lstrip("json").strip() if len(parts) > 1 else text

    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
    except Exception:
        pass

    m = re.search(r'\{[^{}]*\}', text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group())
            if isinstance(result, dict):
                return result
        except Exception:
            pass

    result = {}
    for line in text.splitlines():
        line = line.strip()
        if ":" in line:
            k, _, v = line.partition(":")
            k = k.strip().strip('"').strip("'")
            v = v.strip().strip('"').strip("'")
            if k and v:
                result[k] = v
    if len(result) >= 1:
        return result

    return None


def chat_json(system: str, user: str, fallback: dict | None = None, max_tokens: int = 512) -> dict:
    """Call LLM and parse JSON response. Retries once on failure."""
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    for attempt in range(2):
        if attempt > 0:
            time.sleep(1.5)
        raw = chat(messages, max_tokens=max_tokens)
        if isinstance(raw, str) and raw.startswith("⚠"):
            continue
        result = _try_parse_json(raw)
        if result is not None:
            return result
        logger.error("JSON parse error (attempt %d)\nRaw: %.300s", attempt + 1, raw)
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


def get_gender_check(word: str, pos: str) -> dict:
    return chat_json(
        prompts.GENDER_CHECK_SYSTEM,
        prompts.gender_check_user(word, pos),
        fallback={
            "gender": None, "article": "", "indefinite_article": "",
            "example": "", "example_translation": "",
            "pattern_note": "(API offline — try again later)",
        },
    )


def translate_text(text: str, direction: str, lesson_text: str = "") -> dict:
    return chat_json(
        prompts.TRANSLATE_SYSTEM,
        prompts.translate_user(text, direction, lesson_text),
        fallback={"translation": "(API offline — try again later)", "alternatives": [], "example_fr": "", "example_en": ""},
    )
