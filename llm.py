"""
LLM calls — text (MiniCPM4.1-8B) and vision (MiniCPM-V 4.6) via OpenBMB free API.
Falls back gracefully if the API is unreachable.
"""
import os
import json
import logging
from openai import OpenAI
from dotenv import load_dotenv
import prompts

load_dotenv()
logger = logging.getLogger(__name__)

_text_client  = None
_vision_client = None


def _text():
    global _text_client
    if _text_client is None:
        _text_client = OpenAI(
            api_key=os.environ.get("MINICPM_API_KEY", "sk-no-key"),
            base_url=os.environ.get("MINICPM_API_BASE", "http://35.203.155.71:8001/v1"),
        )
    return _text_client


def _vision():
    global _vision_client
    if _vision_client is None:
        _vision_client = OpenAI(
            api_key=os.environ.get("MINICPM_API_KEY", "sk-no-key"),
            base_url=os.environ.get("MINICPM_VISION_BASE", "http://35.203.155.71:8003/v1"),
        )
    return _vision_client


def _model_name(client, env_var: str, fallback: str) -> str:
    name = os.environ.get(env_var)
    if name:
        return name
    try:
        models = client.models.list()
        if models.data:
            return models.data[0].id
    except Exception:
        pass
    return fallback


def chat(messages: list[dict], stream: bool = False, max_tokens: int = 512):
    """Send to text LLM. Returns str or generator of str chunks."""
    client = _text()
    model  = _model_name(client, "MINICPM_MODEL", "MiniCPM4-8B")
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
        logger.error("Text LLM error: %s", e)
        if stream:
            def _err():
                yield f"⚠ Language model unavailable ({e}). Check the OpenBMB API."
            return _err()
        return f"⚠ Language model unavailable ({e}). Check the OpenBMB API."


def chat_json(system: str, user: str, fallback: dict | None = None) -> dict:
    """Call LLM and parse JSON response. Returns fallback dict on any error."""
    raw = chat([{"role": "system", "content": system}, {"role": "user", "content": user}])
    if raw.startswith("⚠"):
        return fallback or {}
    try:
        text = raw.strip()
        # Strip markdown code fences if the model wraps JSON
        if text.startswith("```"):
            parts = text.split("```")
            text = parts[1].lstrip("json").strip() if len(parts) > 1 else text
        return json.loads(text)
    except Exception as e:
        logger.error("JSON parse error: %s\nRaw: %.200s", e, raw)
        return fallback or {}


def vision_chat(image_b64: str, prompt: str) -> str:
    """Send image + text prompt to vision LLM. Returns description string."""
    client = _vision()
    model  = _model_name(client, "MINICPM_VISION_MODEL", "MiniCPM-V-4.6")
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}},
                    {"type": "text", "text": prompt},
                ],
            }],
            max_tokens=512,
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        logger.error("Vision LLM error: %s", e)
        return f"⚠ Could not analyse the image ({e}). Check the OpenBMB vision API."


def get_word_meaning(text: str, lemma: str, pos: str, gender: str) -> dict:
    """Fetch English meaning + grammar note for a French word. Cached by caller."""
    return chat_json(
        prompts.WORD_MEANING_SYSTEM,
        prompts.word_meaning_user(text, lemma, pos, gender),
        fallback={"meaning": "(meaning unavailable — API offline)", "grammar": ""},
    )


def generate_page_title(snippet: str) -> str:
    result = chat([
        {"role": "system", "content": prompts.PAGE_TITLE_SYSTEM},
        {"role": "user", "content": snippet[:300]},
    ])
    if result.startswith("⚠"):
        return snippet.split("\n")[0][:60] or "Untitled Lesson"
    return result.strip()[:80]
