"""
Group authorization gate.

The bot ignores moderation commands and protection settings in any group
until the main owner explicitly authorizes ("توثيق") that group. This runs
before every other handler (handler group -1) so unauthorized groups never
reach the moderation/protection logic.
"""

from pyrogram import filters

from main import app
from db import is_main_owner, is_chat_authorized, authorize_chat, revoke_chat_authorization

# Commands that should keep working even in unauthorized groups, so members
# can at least see what the bot is / ask the owner to authorize it.
ALWAYS_ALLOWED = {"start", "بداية", "help", "مساعدة", "الاوامر", "توثيق", "الغاء_التوثيق"}


@app.on_message(filters.command(["توثيق"], prefixes=None) & filters.group)
async def authorize_chat_command(client, message):
    if not is_main_owner(message.from_user.id):
        await message.reply("❌ **هذا الأمر متاح فقط للمالك الأساسي للبوت.**")
        return

    authorize_chat(message.chat.id, message.from_user.id)
    await message.reply(
        "✅ **تم توثيق هذه المجموعة!**\n\n"
        "البوت الآن مفعّل ويعمل بكامل صلاحياته في هذا القروب."
    )


@app.on_message(filters.command(["الغاء_التوثيق"], prefixes=None) & filters.group)
async def revoke_chat_command(client, message):
    if not is_main_owner(message.from_user.id):
        await message.reply("❌ **هذا الأمر متاح فقط للمالك الأساسي للبوت.**")
        return

    revoke_chat_authorization(message.chat.id, message.from_user.id)
    await message.reply("🚫 **تم إلغاء توثيق هذه المجموعة.** لن يستجيب البوت هنا حتى تتم إعادة توثيقه.")


@app.on_message(filters.group & filters.text, group=-1)
async def authorization_gate(client, message):
    if not message.from_user:
        return

    chat_id = message.chat.id
    user_id = message.from_user.id

    # Main owner always works, everywhere, including running توثيق itself.
    if is_main_owner(user_id):
        return

    if is_chat_authorized(chat_id):
        return

    text = (message.text or "").strip()
    first_word = text.split()[0].lstrip("/") if text else ""

    if first_word in ALWAYS_ALLOWED:
        return

    # Unauthorized group: silently block every other command/handler
    # (moderation actions, protection enforcement, settings, etc.)
    message.stop_propagation()
