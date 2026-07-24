import os
import time
from dotenv import load_dotenv
import litellm

load_dotenv()


def get_secret(key):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, "")


PRIMARY_MODEL = "groq/openai/gpt-oss-120b"
FALLBACK_MODEL = "groq/openai/gpt-oss-20b"

# Both models share ONE 8000 TPM pool at the org level on Groq's free tier.
# Capped hard so a single completion can never eat most of that budget.
MAX_OUTPUT_TOKENS = 900


def call_llm(prompt, model=None, system=None):
    """
    ONE flat completion call. No agent loop, no tool-calling, no growing
    conversation history. This is the whole point of the rewrite:
    CrewAI's ReAct-style agent loop resends the entire conversation-so-far
    on every iteration, so token cost compounds within a single stage --
    that's what was blowing the 8000 TPM budget even with throttling.
    A single call has a flat, predictable token cost every time.
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
        max_tokens=MAX_OUTPUT_TOKENS
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
    return text


def call_llm_with_retry(prompt, system=None, max_retries=4):
    """
    Retries a single flat call across primary -> fallback model on
    rate_limit/quota errors. Because each call is flat-cost (no compounding
    loop), a real wait actually clears the window -- no throttling needed
    between iterations because there ARE no iterations.
    """
    current_model = PRIMARY_MODEL
    last_error = None

    for attempt in range(1, max_retries + 2):
        try:
            return call_llm(prompt, model=current_model, system=system)
        except Exception as e:
            last_error = e
            msg = str(e).lower()

            is_quota = any(s in msg for s in ("tokens per day", "requests per day", "tpd)", "rpd)"))
            is_rate_limit = any(s in msg for s in ("rate_limit_exceeded", "429", "too many requests"))

            if is_quota and current_model != FALLBACK_MODEL:
                print("[llm] quota exhausted on " + current_model + " -- switching to " + FALLBACK_MODEL)
                current_model = FALLBACK_MODEL
                wait = 2
            elif is_rate_limit:
                import re
                s_match = re.search(r"try again in\s+([\d.]+)s", msg)
                ms_match = re.search(r"try again in\s+([\d.]+)ms", msg)
                if s_match:
                    wait = float(s_match.group(1)) + 3
                elif ms_match:
                    wait = max(float(ms_match.group(1)) / 1000.0 + 5, 8)
                else:
                    wait = min(20 * attempt, 65)
            else:
                wait = min(3 * attempt, 30)

            if attempt <= max_retries:
                print("[llm] attempt " + str(attempt) + " failed (" + str(e)[:120] + ") -- retrying in " + str(round(wait)) + "s")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    "LLM call failed after " + str(attempt) + " attempt(s). Last error: " + str(last_error)
                ) from last_error