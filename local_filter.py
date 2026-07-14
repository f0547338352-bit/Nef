"""
Free, offline keyword/regex heuristic filter — NOT AI.

This scores message text using fixed rules (bad-word list, links, all-latin
text, message length, phone numbers). It has no understanding of context and
cannot "learn" — it is a rule-based spam/abuse filter, same category as the
old SPAM_RE check in protection.py, just more thorough. It runs for free and
instantly, unlike ai_moderation.py (real LLM call, needs OpenAI credit).

Kept separate from ai_moderation.py so it's clear which layer is "real AI"
(LLM-based, costs API credit, understands meaning) and which is "rules"
(free, instant, keyword-based, no understanding).
"""

import re

BAD_WORDS = [
    "كس", "قحبة", "منيك", "نياكة", "طيز", "زب", "شرموطة", "عرص",
    "جنس", "سكس", "بورن", "عاهرة", "دعارة", "لواط", "مثلية",
    "زنا", "فساد", "فاحشة", "رذيلة", "فحش", "بذيء",
]

_LINK_RE = re.compile(r"https?://[^\s]+")
_LATIN_RE = re.compile(r"[a-zA-Z]{4,}")
_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_PHONE_RE = re.compile(r"\+?[0-9]{10,}")


def analyze_text(text: str) -> dict:
    if not text:
        return {"flagged": False, "score": 0, "reasons": []}

    lowered = text.lower()
    score = 0
    reasons = []

    found = [w for w in BAD_WORDS if w in lowered]
    if found:
        score += 30
        reasons.append(f"كلمات بذيئة: {', '.join(found[:3])}")

    if _LINK_RE.search(text):
        score += 20
        reasons.append("رابط خارجي")

    if _LATIN_RE.search(text) and not _ARABIC_RE.search(text):
        score += 20
        reasons.append("نص إنجليزي بالكامل")

    if len(text) > 500:
        score += 15
        reasons.append("رسالة طويلة جدًا")

    if _PHONE_RE.search(text):
        score += 10
        reasons.append("رقم هاتف")

    score = min(score, 100)
    return {"flagged": score >= 40, "score": score, "reasons": reasons}
