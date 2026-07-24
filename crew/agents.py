import os
import re
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

# Hard ceiling on how long a single litellm.completion() call is allowed to
# block, in seconds. Without this, litellm has NO default timeout -- if the
# underlying HTTP connection to Groq stalls (slow network, a hung TCP
# connection, a provider-side stall that never returns and never errors),
# the call just sits there indefinitely. It never raises an exception, so
# call_llm_with_retry's retry loop never even triggers, and the background
# thread in app.py's run_with_progress never finishes OR errors -- which is
# exactly what was showing up as the UI freezing forever on "Finalising and
# formatting output..." with no error ever surfacing. Setting a timeout
# turns a silent infinite hang into a real, retryable TimeoutError.
REQUEST_TIMEOUT_SECONDS = 45


def call_llm(prompt, model=None, system=None, max_tokens=None):
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

    # gpt-oss-120b/20b are reasoning models: part of the completion-token
    # budget goes to an internal reasoning trace before the model writes
    # its actual answer. If max_tokens is too tight, the model can spend
    # its entire budget "thinking" and never emit any answer text at all --
    # response.choices[0].message.content comes back as "" (or None), not
    # as an API error, so this was previously treated as a *successful*
    # call that just happened to return nothing. That blank string then
    # flowed silently through every downstream stage, which is why the
    # final report came back with real search results but a totally empty
    # research stage and no visible error anywhere. Raising here turns
    # that silent failure into a real, retryable error.
    if not text or not text.strip():
        finish_reason = None
        try:
            finish_reason = response.choices[0].finish_reason
        except Exception:
            pass
        raise RuntimeError(
            "Empty completion content from " + (model or PRIMARY_MODEL)
            + " (finish_reason=" + str(finish_reason) + ") -- the model likely "
            "spent its entire token budget on internal reasoning and never "
            "wrote an answer. Needs a larger max_tokens."
        )

    return text


def call_llm_with_retry(prompt, system=None, max_retries=4, max_tokens=None):
    """
    Retries a single flat call across primary -> fallback model on
    rate_limit/quota/timeout errors. Because each call is flat-cost (no
    compounding loop), a real wait actually clears the window -- no
    throttling needed between iterations because there ARE no iterations.
    """
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
            # litellm raises its own Timeout exception type on a timed-out
            # call, and also generally includes "timeout" in the message
            # text regardless of the underlying provider/transport that
            # raised it -- catching on the message keeps this robust to
            # whichever specific exception class litellm surfaces.
            is_timeout = "timeout" in msg or "timed out" in msg

            # Daily token/request quota errors (TPD/RPD) come with a
            # "try again in Xm Ys" wait time that can be tens of minutes --
            # far longer than any reasonable in-request retry window, and
            # the SAME across both PRIMARY_MODEL and FALLBACK_MODEL since
            # they share one org-level daily pool (switching models does
            # nothing once both are already exhausted). Retrying against
            # this is pure wasted time that just delays showing the user
            # the one thing they actually need to know: how long to wait.
            # Parsed here (not just relying on the generic 's'/'ms' regex
            # below) because Groq's TPD messages use an "Xm Ys" format that
            # the old parsing never matched, silently falling through to a
            # useless 20s backoff and burning all retry attempts first.
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

            wait = min(3 * attempt, 30)  # default fallback, overridden below

            if is_empty_completion:
                # Retrying with the same max_tokens would just fail the
                # same way again -- the model needs more room to finish
                # its reasoning trace AND write the answer. Grow the
                # budget each time this specific failure happens.
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