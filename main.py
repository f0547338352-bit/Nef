#!/usr/bin/env python3
import os
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from db import init_db, get_main_owner, is_main_owner, log_event
from commands_basic import start_command, help_command, settings_command, list_admins_command, list_owners_command
from commands_moderation import (
    promote_admin, promote_manager, promote_owner,
    demote_admin, demote_manager, demote_owner,
    ban_user, unban_user, kick_user,
    mute_user, unmute_user, restrict_user, unrestrict_user,
    lock_chat, unlock_chat,
    lock_links, unlock_links,
    lock_photos, unlock_photos,
    lock_videos, unlock_videos,
    lock_stickers, unlock_stickers,
    lock_preview, unlock_preview,
    lock_mentions, unlock_mentions,
    lock_invites, unlock_invites,
    lock_new_accounts, unlock_new_accounts
)
from authorization import authorize_chat_command, revoke_chat_command, authorization_gate
from protection import handle_message as protection_handle_message
from ai_moderation import classify_message, is_configured, active_provider
from error_monitor import install as install_error_monitor
from reports import send_report
from local_filter import analyze_text

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود")

init_db()
MAIN_OWNER_ID = get_main_owner()

logging.basicConfig(level=logging.INFO)

app = Application.builder().token(BOT_TOKEN).build()
install_error_monitor(app.bot)

app.add_handler(CommandHandler("start", start_command))
app.add_handler(CommandHandler("بداية", start_command))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("مساعدة", help_command))
app.add_handler(CommandHandler("الاوامر", help_command))
app.add_handler(CommandHandler("الاعدادات", settings_command))
app.add_handler(CommandHandler("settings", settings_command))
app.add_handler(CommandHandler("المشرفين", list_admins_command))
app.add_handler(CommandHandler("الملاك", list_owners_command))

app.add_handler(CommandHandler("توثيق", authorize_chat_command))
app.add_handler(CommandHandler("الغاء_التوثيق", revoke_chat_command))

app.add_handler(CommandHandler("رفع_مشرف", promote_admin))
app.add_handler(CommandHandler("رفع_ادمن", promote_admin))
app.add_handler(CommandHandler("رفع_مدير", promote_manager))
app.add_handler(CommandHandler("رفع_مالك", promote_owner))
app.add_handler(CommandHandler("تنزيل_مشرف", demote_admin))
app.add_handler(CommandHandler("تنزيل_ادمن", demote_admin))
app.add_handler(CommandHandler("تنزيل_مدير", demote_manager))
app.add_handler(CommandHandler("تنزيل_مالك", demote_owner))

app.add_handler(CommandHandler("حظر", ban_user))
app.add_handler(CommandHandler("ban", ban_user))
app.add_handler(CommandHandler("فك_حظر", unban_user))
app.add_handler(CommandHandler("unban", unban_user))
app.add_handler(CommandHandler("طرد", kick_user))
app.add_handler(CommandHandler("kick", kick_user))
app.add_handler(CommandHandler("كتم", mute_user))
app.add_handler(CommandHandler("mute", mute_user))
app.add_handler(CommandHandler("فك_كتم", unmute_user))
app.add_handler(CommandHandler("unmute", unmute_user))
app.add_handler(CommandHandler("تقييد", restrict_user))
app.add_handler(CommandHandler("restrict", restrict_user))
app.add_handler(CommandHandler("فك_تقييد", unrestrict_user))
app.add_handler(CommandHandler("unrestrict", unrestrict_user))

app.add_handler(CommandHandler("قفل", lock_chat))
app.add_handler(CommandHandler("فتح", unlock_chat))
app.add_handler(CommandHandler("قفل_الروابط", lock_links))
app.add_handler(CommandHandler("فتح_الروابط", unlock_links))
app.add_handler(CommandHandler("قفل_الصور", lock_photos))
app.add_handler(CommandHandler("فتح_الصور", unlock_photos))
app.add_handler(CommandHandler("قفل_الفيديو", lock_videos))
app.add_handler(CommandHandler("فتح_الفيديو", unlock_videos))
app.add_handler(CommandHandler("قفل_الملصقات", lock_stickers))
app.add_handler(CommandHandler("فتح_الملصقات", unlock_stickers))
app.add_handler(CommandHandler("قفل_المعاينة", lock_preview))
app.add_handler(CommandHandler("فتح_المعاينة", unlock_preview))
app.add_handler(CommandHandler("قفل_المنشن", lock_mentions))
app.add_handler(CommandHandler("فتح_المنشن", unlock_mentions))
app.add_handler(CommandHandler("قفل_الدعوات", lock_invites))
app.add_handler(CommandHandler("فتح_الدعوات", unlock_invites))
app.add_handler(CommandHandler("قفل_الحسابات_الجديدة", lock_new_accounts))
app.add_handler(CommandHandler("فتح_الحسابات_الجديدة", unlock_new_accounts))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, protection_handle_message))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, authorization_gate), group=-1)

async def daily_report():
    while True:
        await asyncio.sleep(24 * 60 * 60)
        try:
            await send_report(app.bot, MAIN_OWNER_ID)
        except Exception as e:
            print(f"[daily report] failed: {e}")

async def main():
    try:
        await app.bot.send_message(MAIN_OWNER_ID, "✅ **تم تشغيل البوت.**")
    except Exception as e:
        print(f"[startup] could not DM main owner: {e}")
    asyncio.create_task(daily_report())
    print("🚀 البوت يعمل الآن!")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
