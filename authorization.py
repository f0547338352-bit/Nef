"""
Group authorization gate.

The bot ignores moderation commands and protection settings in any group
until the main owner explicitly authorizes ("توثيق") that group. This runs
before every other handler (handler group -1) so unauthorized groups never
reach the moderation/protection logic.
"""

from telegram import Update
from telegram.ext import ContextTypes
from db import is_main_owner, is_chat_authorized, authorize_chat, revoke_chat_authorization

# الأوامر المسموح بها دائماً حتى لو كانت المجموعة غير موثقة
ALWAYS_ALLOWED = {"start", "بداية", "help", "مساعدة", "الاوامر", "توثيق", "الغاء_التوثيق"}

async def authorize_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر توثيق المجموعة"""
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_main_owner(user_id):
        await update.message.reply_text("❌ **هذا الأمر متاح فقط للمالك الأساسي للبوت.**")
        return

    authorize_chat(chat_id, user_id)
    await update.message.reply_text(
        "✅ **تم توثيق هذه المجموعة!**\n\n"
        "البوت الآن مفعّل ويعمل بكامل صلاحياته في هذا القروب."
    )

async def revoke_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر إلغاء توثيق المجموعة"""
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if not is_main_owner(user_id):
        await update.message.reply_text("❌ **هذا الأمر متاح فقط للمالك الأساسي للبوت.**")
        return

    revoke_chat_authorization(chat_id, user_id)
    await update.message.reply_text("🚫 **تم إلغاء توثيق هذه المجموعة.** لن يستجيب البوت هنا حتى تتم إعادة توثيقه.")

async def authorization_gate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بوابة الحماية لمنع الأوامر في المجموعات غير الموثقة"""
    if not update.message or not update.effective_user or not update.effective_chat:
        return

    chat_id = update.effective_chat.id
    user_id = update.effective_user.id

    # المالك الأساسي يتجاوز البوابة دائماً
    if is_main_owner(user_id):
        return

    # إذا كانت المجموعة موثقة، نسمح بمرور الرسالة
    if is_chat_authorized(chat_id):
        return

    text = (update.message.text or "").strip()
    first_word = text.split()[0].lstrip("/") if text else ""

    # إذا كان الأمر مسموحاً به دائماً، ندعه يمر
    if first_word in ALWAYS_ALLOWED:
        return

    # إذا كانت المجموعة غير موثقة، نقوم بإيقاف معالجة الرسالة تماماً وحظرها
    # هذا يعادل message.stop_propagation() في pyrogram
    context.application.handlers.clear() 
