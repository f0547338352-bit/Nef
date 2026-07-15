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

def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None and os.environ.get("GEMINI_API_KEY"):
        from google import genai
        _gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return _gemini_client

def _parse_flag(raw: str) -> dict:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            raise
        data = json.loads(match.group(0))
    if data.get("flag") not in ("spam", "scam", "abuse", "safe"):
        data["flag"] = "safe"
    return data

def _classify_gemini_sync(text: str) -> dict:
    client = _get_gemini_client()
    if not client:
        return {"flag": "safe", "reason": "gemini_not_configured"}
    last_error = None
    for attempt in range(3):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
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
            time.sleep(1.5 * (attempt + 1))
    return {"flag": "safe", "reason": f"gemini_error: {last_error}"}

def _classify_sync(text: str) -> dict:
    if os.environ.get("GEMINI_API_KEY"):
        try:
            return _classify_gemini_sync(text)
        except Exception as e:
            return {"flag": "safe", "reason": f"gemini_error: {e}"}
    return {"flag": "safe", "reason": "no_api_key"}

async def classify_message(text: str) -> dict:
    return await asyncio.to_thread(_classify_sync, text)

def is_configured() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY"))

def active_provider() -> str:
    return "Gemini" if os.environ.get("GEMINI_API_KEY") else "none"
