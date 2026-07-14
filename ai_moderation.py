"""
Real AI-powered moderation. Sends message text to an LLM and asks for a
classification (spam / scam / abuse / safe).

Provider priority (first configured wins):
1. Gemini (GEMINI_API_KEY) — free tier via Google AI Studio, used by default
   since the user asked for a no-cost option.
2. OpenAI (OPENAI_API_KEY) — fallback if Gemini isn't configured.

This is intentionally narrow and honest about what it does: it classifies a
single message's text. It does NOT scan or patch the bot's own source code,
does not "learn" over time, and does not act without the group having
`ai_protection` explicitly enabled via `تفعيل_الحماية_الذكية`.
"""

import asyncio
import json
import os
import re
import time

SYSTEM_PROMPT = (
    "أنت مصنّف رسائل لمجموعة تيليجرام عربية. مهمتك الوحيدة تحديد إذا كانت "
    "الرسالة التالية سبام، احتيال/نصب، أو إساءة/سب، أو رسالة طبيعية آمنة. "
    "رد فقط بصيغة JSON بهذا الشكل بدون أي نص إضافي: "
    '{"flag": "spam" | "scam" | "abuse" | "safe", "reason": "سبب مختصر بالعربي"}'
)

_gemini_client = None
_openai_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None and os.environ.get("GEMINI_API_KEY"):
        from google import genai
        _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _gemini_client


def _get_openai_client():
    global _openai_client
    if _openai_client is None and os.environ.get("OPENAI_API_KEY"):
        from openai import OpenAI
        _openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    return _openai_client


def _parse_flag(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Occasionally the free-tier model wraps JSON in markdown fences or
        # adds stray text around it — pull out the first {...} block instead
        # of failing outright.
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    if data.get("flag") not in ("spam", "scam", "abuse", "safe"):
        data["flag"] = "safe"
    return data


def _classify_gemini_sync(text: str) -> dict:
    client = _get_gemini_client()
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-flash-latest",
                contents=text[:2000],
                config={
                    "system_instruction": SYSTEM_PROMPT,
                    "response_mime_type": "application/json",
                    "temperature": 0,
                },
            )
            return _parse_flag(response.text)
        except Exception as e:
            last_error = e
            # Free-tier Gemini occasionally returns transient 503/429s under
            # load — a couple of short retries smooth over most of those.
            time.sleep(1.5 * (attempt + 1))
    raise last_error


def _classify_openai_sync(text: str) -> dict:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text[:2000]},
        ],
        response_format={"type": "json_object"},
        temperature=0,
        max_tokens=100,
    )
    return _parse_flag(response.choices[0].message.content)


def _classify_sync(text: str) -> dict:
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return _classify_gemini_sync(text)
        except Exception as e:
            return {"flag": "safe", "reason": f"gemini_error: {e}"}

    if os.environ.get("OPENAI_API_KEY"):
        try:
            return _classify_openai_sync(text)
        except Exception as e:
            return {"flag": "safe", "reason": f"openai_error: {e}"}

    return {"flag": "safe", "reason": "no_api_key"}


async def classify_message(text: str) -> dict:
    """Runs the (blocking) API call in a thread so it doesn't stall the bot's event loop."""
    return await asyncio.to_thread(_classify_sync, text)


def is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def active_provider() -> str:
    if os.environ.get("GEMINI_API_KEY"):
        return "Gemini"
    if os.environ.get("OPENAI_API_KEY"):
        return "OpenAI"
    return "none"
