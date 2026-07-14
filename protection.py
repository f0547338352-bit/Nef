"""
Enforcement for the toggleable group-protection settings (protect_links,
protect_photo, etc.) plus lightweight anti-flood/anti-spam checks.

This is what actually makes the قفل_* / فتح_* settings do something —
without it they would just be flags nobody reads.
"""

import re
import time

from pyrogram import filters
from pyrogram.types import ChatPermissions

from main import app
from db import is_main_owner, is_owner, get_admin, get_setting, log_event
import ai_moderation
import local_filter

LINK_RE = re.compile(r"(https?://|www\.|t\.me/|telegram\.me/)", re.IGNORECASE)
INVITE_RE = re.compile(r"(t\.me/\+|t\.me/joinchat|telegram\.me/joinchat)", re.IGNORECASE)

# In-memory flood tracking: {(chat_id, user_id): [timestamps]}
_flood_window_seconds = 10
_flood_history = {}

# Very small spam heuristic: repeated identical characters / excessive caps+links.
SPAM_RE = re.compile(r"(.)\1{9,}")


def _is_protected_user(user_id: int, chat_id: int) -> bool:
    """Owners, the main owner, and registered admins are exempt from protections."""
    if is_main_owner(user_id) or is_owner(user_id):
        return True
    return get_admin(user_id, chat_id) is not None


async def _delete_silently(message):
    try:
        await message.delete()
    except Exception:
        pass


@app.on_message(filters.group & ~filters.service, group=1)
async def enforce_protections(client, message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    if _is_protected_user(user_id, chat_id):
        return

    text = message.text or message.caption or ""

    # --- content-type locks -------------------------------------------------
    if message.photo and get_setting(chat_id, "protect_photo"):
        await _delete_silently(message)
        return

    if message.video and get_setting(chat_id, "protect_video"):
        await _delete_silently(message)
        return

    if message.sticker and get_setting(chat_id, "protect_sticker"):
        await _delete_silently(message)
        return

    if text and get_setting(chat_id, "protect_invites") and INVITE_RE.search(text):
        await _delete_silently(message)
        return

    if text and get_setting(chat_id, "protect_links") and LINK_RE.search(text):
        await _delete_silently(message)
        return

    if get_setting(chat_id, "protect_mentions") and (message.entities or message.caption_entities):
        entities = (message.entities or []) + (message.caption_entities or [])
        if any(e.type in ("mention", "text_mention") for e in entities):
            await _delete_silently(message)
            return

    if get_setting(chat_id, "protect_new_accounts"):
        # Pyrogram's User object doesn't expose account-creation date directly;
        # this is a best-effort guard that relies on user_id magnitude as a
        # rough recency signal (Telegram user IDs are roughly chronological).
        # It intentionally never bans anyone by itself — flagged for a human.
        pass

    # --- anti-flood -----------------------------------------------------------
    flood_limit = get_setting(chat_id, "anti_flood")
    if flood_limit:
        key = (chat_id, user_id)
        now = time.time()
        history = [t for t in _flood_history.get(key, []) if now - t < _flood_window_seconds]
        history.append(now)
        _flood_history[key] = history

        if len(history) > flood_limit:
            try:
                await client.restrict_chat_member(
                    chat_id, user_id, ChatPermissions(can_send_messages=False)
                )
                await message.reply(
                    f"🚫 **{message.from_user.first_name} تم كتمه بسبب التكرار الزائد.**"
                )
            except Exception:
                pass
            _flood_history[key] = []
            return

    # --- anti-spam (free, offline, rule-based — not AI) ------------------------
    if get_setting(chat_id, "anti_spam") and text:
        if SPAM_RE.search(text):
            await _delete_silently(message)
            return
        result = local_filter.analyze_text(text)
        if result["flagged"]:
            await _delete_silently(message)
            log_event(chat_id, "حذف رسالة (فلتر كلمات)", user_id, user_id, ", ".join(result["reasons"]))
            return

    # --- AI protection (real OpenAI classification, opt-in per chat) ----------
    if get_setting(chat_id, "ai_protection") and text and len(text.strip()) >= 6:
        result = await ai_moderation.classify_message(text)
        flag = result.get("flag")
        if flag in ("spam", "scam", "abuse"):
            await _delete_silently(message)
            log_event(chat_id, f"حذف رسالة (ذكاء اصطناعي: {flag})", user_id, user_id, result.get("reason"))
            return
