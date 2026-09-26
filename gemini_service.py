"""
Single configuration point for all Gemini / LangChain LLM access.

Every agent asks this module for a structured LLM bound to its own
Pydantic schema, so model name, temperature and API-key handling only
ever live in one place.
"""
import logging
import random
import re
import time

from pydantic import ValidationError

logger = logging.getLogger("boardroom.gemini")


class GeminiConfigError(Exception):
    """Raised when the Gemini API key is missing or invalid."""


class GeminiCallError(Exception):
    """Raised when the Gemini API call itself fails (network, rate limit, etc)."""


# Free-tier Gemini quotas are per-minute. The boardroom fires Finance,
# Marketing and Operations as a true parallel burst (three calls in the same
# instant), then Risk right after — five calls inside a couple of seconds is
# enough to trip a 10-15 RPM free-tier limit even though the app itself is
# nowhere near its real workload. These are the substrings Google's client
# raises when that happens, across the different exception shapes it can take.
_RATE_LIMIT_MARKERS = (
    "429", "resource_exhausted", "resource exhausted", "rate limit",
    "rate_limit", "quota", "too many requests",
)


def _is_rate_limited(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def _extract_retry_delay(exc: Exception):
    """Attempt to parse Google's recommended retry delay (e.g. 'retry in 16.5s' or 'retryDelay': '16s')."""
    text = str(exc)
    m = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)\s*s", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    m = re.search(r"['\"]?retryDelay['\"]?\s*:\s*['\"]?([0-9]+(?:\.[0-9]+)?)\s*s?['\"]?", text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return None


def _get_api_key():
    from flask import current_app
    key = current_app.config.get("GEMINI_API_KEY")
    if not key:
        raise GeminiConfigError(
            "GEMINI_API_KEY is not set. Add it to your .env file (see .env.example)."
        )
    return key


def _is_daily_limit(exc: Exception) -> bool:
    text = str(exc).lower()
    return "perday" in text or "per day" in text or "generaterequestsperday" in text


def _get_candidate_models():
    from flask import current_app
    primary = current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash")
    fallbacks = [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-3-flash-preview",
        "gemini-3.1-flash-lite",
    ]
    candidates = [primary]
    for fb in fallbacks:
        if fb not in candidates:
            candidates.append(fb)
    return candidates


def get_structured_llm(schema, temperature: float = 0.4, model_override: str = None):
    """Return a LangChain ChatGoogleGenerativeAI client bound to `schema`."""
    from flask import current_app
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = _get_api_key()
    model_name = model_override or current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    thinking_budget = current_app.config.get("GEMINI_THINKING_BUDGET", 0)

    llm_kwargs = {
        "model": model_name,
        "google_api_key": api_key,
        "temperature": temperature,
        "max_retries": 0,
        "timeout": 30.0,
    }
    if thinking_budget is not None:
        llm_kwargs["thinking_budget"] = int(thinking_budget)

    llm = ChatGoogleGenerativeAI(**llm_kwargs)
    return llm.with_structured_output(schema)


def invoke_structured(schema, system_prompt: str, user_prompt: str, temperature: float = 0.4,
                      max_attempts: int = 3):
    """
    Call Gemini with a system + user prompt, force structured output matching
    `schema`, and validate it. Raises GeminiCallError / GeminiConfigError on
    final failure.

    Optimized for SPEED: only 3 attempts with short backoff (max 2s).
    Iterates through candidate models. Because Google assigns independent quotas
    per model, if one model hits a 429 rate limit or daily limit, the pipeline
    instantly fails over to the next candidate model without sleeping.
    """
    candidates = _get_candidate_models()
    last_exc = None

    for model_idx, model_name in enumerate(candidates):
        try:
            structured_llm = get_structured_llm(schema, temperature=temperature, model_override=model_name)
        except Exception as e:
            logger.warning("Could not initialize model %s: %s", model_name, e)
            last_exc = e
            continue

        messages = [
            ("system", system_prompt),
            ("human", user_prompt + (
                "\n\nIMPORTANT: Respond ONLY with data matching the required schema exactly. "
                "Every required field must be present and within its valid range. "
                "Keep ALL text fields SHORT and CRISP — 1-2 sentences per list item, "
                "3-4 sentences max for reasoning fields. No filler or boilerplate."
            )),
        ]

        for attempt in range(1, max_attempts + 1):
            try:
                result = structured_llm.invoke(messages)
                if isinstance(result, schema):
                    return result
                return schema.model_validate(result)
            except GeminiConfigError:
                raise
            except (ValidationError, Exception) as e:
                last_exc = e
                err_text = str(e).lower()

                # If daily quota, 503 unavailable, or permanent error, instantly switch model
                is_unavailable = "503" in err_text or "unavailable" in err_text or "high demand" in err_text or "overloaded" in err_text
                if _is_daily_limit(e) or is_unavailable or "invalid_argument" in err_text or "not_found" in err_text or "not found" in err_text:
                    logger.warning(
                        "Model %s encountered %s; failing over to next candidate model immediately",
                        model_name, e,
                    )
                    break

                # If rate-limited (429), instantly fail over to the next candidate model
                if _is_rate_limited(e):
                    logger.warning(
                        "Gemini %s rate-limited (attempt %s/%s), failing over to next model immediately: %s",
                        model_name, attempt, max_attempts, e,
                    )
                    break
                else:
                    if attempt < max_attempts:
                        # Short backoff — capped at 2s for speed
                        backoff = min(2.0, 0.3 * (2 ** attempt)) + random.uniform(0, 0.3)
                        logger.warning("Gemini %s returned transient error, sleeping %.1fs: %s", model_name, backoff, e)
                        time.sleep(backoff)

    if _is_rate_limited(last_exc):
        raise GeminiCallError(
            f"Gemini rate limit hit after trying candidate models: {last_exc}"
        )
    raise GeminiCallError(f"Gemini structured call failed: {last_exc}")

