"""
Basic/general commands: start, help, permission list, current settings,
and admin/owner listings.
"""

from pyrogram import filters

from main import app
from db import (
    MAIN_OWNER_ID,
    is_main_owner,
    is_owner,
    list_owners,
    list_admins,
    get_all_settings,
)

START_TEXT = (
    "👋 **أهلاً بك!**\n\n"
    "أنا بوت إدارة مجموعات. أضفني كمشرف في مجموعتك وامنحني صلاحية "
    "حذف الرسائل، حظر الأعضاء، وتقييد الأعضاء حتى أعمل بشكل صحيح.\n\n"
    "أرسل **مساعدة** لرؤية كل الأوامر المتاحة."
)

HELP_TEXT = (
    "📖 **قائمة الأوامر**\n\n"
    "**رفع وتنزيل الرتب:**\n"
    "`رفع_مشرف` / `رفع_ادمن` — رفع عضو كمشرف (رد على رسالته)\n"
    "`رفع_مدير` — رفع عضو كمدير\n"
    "`رفع_مالك` — رفع عضو كمالك (المالك الأساسي فقط)\n"
    "`تنزيل_مشرف` / `تنزيل_ادمن` — تنزيل مشرف\n"
    "`تنزيل_مدير` — تنزيل مدير\n"
    "`تنزيل_مالك` — تنزيل مالك (المالك الأساسي فقط)\n\n"
    "**الحظر والطرد والكتم:**\n"
    "`حظر` / `ban` — حظر عضو (رد على رسالته)\n"
    "`فك_حظر` / `unban` — فك الحظر\n"
    "`طرد` / `kick` — طرد عضو\n"
    "`فك_طرد` — فك الطرد\n"
    "`كتم` / `mute` — كتم عضو\n"
    "`فك_كتم` / `unmute` — فك الكتم\n"
    "`تقييد` / `restrict` — منع عضو من إرسال أي شيء\n"
    "`فك_تقييد` / `unrestrict` — فك التقييد\n"
    "`حظر_مؤقت [دقائق]` — حظر مؤقت (افتراضي 60 دقيقة)\n"
    "`كتم_مؤقت [دقائق]` — كتم مؤقت (افتراضي 60 دقيقة)\n"
    "`طرد_صامت` — طرد بدون رسالة\n"
    "`حظر_صامت` — حظر بدون رسالة\n\n"
    "**القفل والفتح:**\n"
    "`قفل` / `فتح` — قفل أو فتح المجموعة بالكامل\n"
    "`قفل_الروابط` / `فتح_الروابط`\n"
    "`قفل_الصور` / `فتح_الصور`\n"
    "`قفل_الفيديو` / `فتح_الفيديو`\n"
    "`قفل_الملصقات` / `فتح_الملصقات`\n"
    "`قفل_المعاينة` / `فتح_المعاينة`\n"
    "`قفل_التوجيه` / `فتح_التوجيه`\n"
    "`قفل_البوتات` / `فتح_البوتات`\n"
    "`قفل_المنشن` / `فتح_المنشن`\n"
    "`قفل_الدعوات` / `فتح_الدعوات`\n"
    "`قفل_الحسابات_الجديدة` / `فتح_الحسابات_الجديدة`\n"
    "`قفل_التكرار` / `فتح_التكرار`\n"
    "`قفل_السبام` / `فتح_السبام`\n\n"
    "**الحماية الذكية (ذكاء اصطناعي حقيقي):**\n"
    "`تفعيل_الحماية_الذكية` — فحص كل رسالة فعليًا عبر OpenAI (سبام/احتيال/إساءة) وحذفها تلقائيًا\n"
    "`ايقاف_الحماية_الذكية` — إيقاف الفحص الذكي\n\n"
    "**معلومات:**\n"
    "`الاعدادات` — عرض إعدادات الحماية الحالية للمجموعة\n"
    "`المشرفين` — عرض قائمة المشرفين المسجلين في المجموعة\n"
    "`الملاك` — عرض قائمة ملاك البوت\n"
    "`تقرير` — تقرير حالة البوت الحالي (خاص فقط، المالك الأساسي)\n\n"
    "**التفعيل:**\n"
    "`توثيق` — تفعيل البوت في هذه المجموعة (المالك الأساسي فقط)\n"
    "`الغاء_التوثيق` — إيقاف البوت في هذه المجموعة (المالك الأساسي فقط)\n\n"
    "⚠️ ملاحظة: لن يستجيب البوت لأي أمر إشراف في مجموعة جديدة حتى يقوم "
    "المالك الأساسي بإرسال `توثيق` فيها أولاً."
)


@app.on_message(filters.command(["start", "بداية"], prefixes=None) & filters.private)
async def start_command(client, message):
    await message.reply(START_TEXT)


@app.on_message(filters.command(["help", "مساعدة", "الاوامر"], prefixes=None))
async def help_command(client, message):
    await message.reply(HELP_TEXT)


def _status_line(label: str, enabled) -> str:
    icon = "🔒" if enabled else "🔓"
    return f"{icon} {label}: {'مفعّل' if enabled else 'معطّل'}"


@app.on_message(filters.command(["الاعدادات", "settings"], prefixes=None) & filters.group)
async def settings_command(client, message):
    chat_id = message.chat.id
    s = get_all_settings(chat_id)

    lines = [
        "⚙️ **إعدادات الحماية الحالية**\n",
        _status_line("الروابط", s["protect_links"]),
        _status_line("الصور", s["protect_photo"]),
        _status_line("الفيديو", s["protect_video"]),
        _status_line("الملصقات", s["protect_sticker"]),
        _status_line("المنشن", s["protect_mentions"]),
        _status_line("روابط الدعوة", s["protect_invites"]),
        _status_line("إضافة البوتات", s["protect_add_bots"]),
        _status_line("الحسابات الجديدة", s["protect_new_accounts"]),
        _status_line("مانع التكرار", s["anti_flood"]),
        _status_line("مانع السبام", s["anti_spam"]),
        _status_line("الحماية الذكية (AI)", s["ai_protection"]),
    ]
    await message.reply("\n".join(lines))


@app.on_message(filters.command(["المشرفين"], prefixes=None) & filters.group)
async def list_admins_command(client, message):
    admins = list_admins(message.chat.id)
    if not admins:
        await message.reply("لا يوجد مشرفون مسجلون في هذه المجموعة بعد.")
        return

    lines = ["👮 **مشرفو المجموعة:**\n"]
    for user_id, title, level in admins:
        lines.append(f"• `{user_id}` — {title} ({level})")
    await message.reply("\n".join(lines))


@app.on_message(filters.command(["الملاك"], prefixes=None))
async def list_owners_command(client, message):
    owners = list_owners()
    lines = ["👑 **ملاك البوت:**\n"]
    for user_id, title, level in owners:
        marker = " (المالك الأساسي)" if user_id == MAIN_OWNER_ID else ""
        lines.append(f"• `{user_id}` — {title}{marker}")
    await message.reply("\n".join(lines))
