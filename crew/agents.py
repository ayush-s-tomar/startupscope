import os
import re
import time

import litellm
from dotenv import load_dotenv

load_dotenv()


def get_secret(key):
    """Reads config purely from environment variables / .env file.
    Set GROQ_API_KEY and SERPER_API_KEY in the Render dashboard's
    Environment tab (or in a local .env file for development)."""
    return os.getenv(key, "")


PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "groq/openai/gpt-oss-20b"

# Both models share ONE 8000 TPM pool at the org level on Groq's free tier.
# Capped hard so a single completion can never eat most of that budget.
MAX_OUTPUT_TOKENS = 900

# Default retry count, overridable via the MAX_RETRIES env var (set in the
# Render dashboard / render.yaml) without touching code.
DEFAULT_MAX_RETRIES = int(os.getenv("MAX_RETRIES", "4"))

# Hard ceiling on how long a single litellm.completion() call is allowed to
# block, in seconds. Without this, litellm has NO default timeout -- if the
# underlying HTTP connection to Groq stalls, the call just sits there
# indefinitely. Setting a timeout turns a silent infinite hang into a real,
# retryable TimeoutError.
REQUEST_TIMEOUT_SECONDS = 45


def call_llm(prompt, model=None, system=None, max_tokens=None):
    """
    ONE flat completion call. No agent loop, no tool-calling, no growing
    conversation history -- keeps token cost flat and predictable.
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = litellm.completion(
        model=model or PRIMARY_MODEL,
        messages=messages,
        api_key=get_secret("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=max_tokens or MAX_OUTPUT_TOKENS,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    text = response.choices[0].message.content
    usage = getattr(response, "usage", None)
    if usage:
        print(
            "[llm] model=" + (model or PRIMARY_MODEL)
            + " prompt_tokens=" + str(getattr(usage, "prompt_tokens", "?"))
            + " completion_tokens=" + str(getattr(usage, "completion_tokens", "?"))
            + " total_tokens=" + str(getattr(usage, "total_tokens", "?"))
        )

    if not text or not text.strip():
        finish_reason = None
        try:
            finish_reason = response.choices[0].finish_reason
        except Exception:  # noqa: BLE001, S110
            pass
        raise RuntimeError(
            "Empty completion content from " + (model or PRIMARY_MODEL)
            + " (finish_reason=" + str(finish_reason) + ") -- the model likely "
            "spent its entire token budget on internal reasoning and never "
            "wrote an answer. Needs a larger max_tokens."
        )

    return text


def call_llm_with_retry(prompt, system=None, max_retries=None, max_tokens=None):
    """
    Retries a single flat call across primary -> fallback model on
    rate_limit/quota/timeout errors.
    """
    if max_retries is None:
        max_retries = DEFAULT_MAX_RETRIES

    current_model = PRIMARY_MODEL
    current_max_tokens = max_tokens or MAX_OUTPUT_TOKENS
    last_error = None

    for attempt in range(1, max_retries + 2):
        try:
            return call_llm(prompt, model=current_model, system=system, max_tokens=current_max_tokens)
        except Exception as e:
            last_error = e
            msg = str(e).lower()

            is_quota = any(s in msg for s in ("tokens per day", "requests per day", "tpd)", "rpd)"))
            is_rate_limit = any(s in msg for s in ("rate_limit_exceeded", "429", "too many requests"))
            is_empty_completion = "empty completion content" in msg
            is_timeout = "timeout" in msg or "timed out" in msg

            if is_quota:
                min_match = re.search(r"try again in\s+([\d.]+)m\s*([\d.]+)?s", msg)
                if min_match:
                    mins = float(min_match.group(1))
                    secs = float(min_match.group(2) or 0)
                    quota_wait = mins * 60 + secs
                    raise RuntimeError(
                        "Groq's daily free-tier token quota is exhausted for "
                        "this account (used on both the primary and fallback "
                        "models, which share one pool). It resets in about "
                        + str(int(quota_wait // 60)) + "m. Please try again "
                        "after that, or upgrade the Groq plan at "
                        "https://console.groq.com/settings/billing."
                    ) from e

            wait = min(3 * attempt, 30)

            if is_empty_completion:
                bumped = int(current_max_tokens * 1.6)
                print(
                    "[llm] empty completion from " + current_model
                    + " -- bumping max_tokens " + str(current_max_tokens)
                    + " -> " + str(bumped)
                )
                current_max_tokens = bumped
                wait = 2

            if is_timeout:
                print(
                    "[llm] request to " + current_model + " timed out after "
                    + str(REQUEST_TIMEOUT_SECONDS) + "s -- retrying"
                )
                wait = 3

            if is_quota and current_model != FALLBACK_MODEL:
                print("[llm] quota exhausted on " + current_model + " -- switching to " + FALLBACK_MODEL)
                current_model = FALLBACK_MODEL
                wait = 2
            elif is_rate_limit:
                s_match = re.search(r"try again in\s+([\d.]+)s", msg)
                ms_match = re.search(r"try again in\s+([\d.]+)ms", msg)
                if s_match:
                    wait = float(s_match.group(1)) + 3
                elif ms_match:
                    wait = max(float(ms_match.group(1)) / 1000.0 + 5, 8)
                else:
                    wait = min(20 * attempt, 65)

            if attempt <= max_retries:
                print("[llm] attempt " + str(attempt) + " failed (" + str(e)[:120] + ") -- retrying in " + str(round(wait)) + "s")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    "LLM call failed after " + str(attempt) + " attempt(s). Last error: " + str(last_error)
                ) from last_error