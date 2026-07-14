"""
Status reporting for the main owner: an on-demand `تقرير` command plus the
data used by the daily background report in main.py.

This is the honest version of "the bot develops/checks on itself": it does
not rewrite its own code or patch security holes on its own, but it does
give the main owner a real, verifiable signal that it's alive and a summary
of what it has done.
"""

import time

from pyrogram import filters

from main import app
from db import c, is_main_owner

_started_at = time.monotonic()


def _uptime_str() -> str:
    seconds = int(time.monotonic() - _started_at)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days} يوم")
    if hours:
        parts.append(f"{hours} ساعة")
    parts.append(f"{minutes} دقيقة")
    return " ".join(parts)


def _counts():
    c.execute("SELECT COUNT(*) FROM settings WHERE key = 'authorized' AND value = 1")
    authorized_groups = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ban_log")
    total_bans = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM events")
    total_events = c.fetchone()[0]
    return authorized_groups, total_bans, total_events


async def build_report_text() -> str:
    authorized_groups, total_bans, total_events = _counts()
    me = await app.get_me()
    return (
        "📊 **تقرير حالة البوت**\n\n"
        "✅ الحالة: يعمل بشكل طبيعي\n"
        f"⏱️ مدة التشغيل المتواصل الحالية: {_uptime_str()}\n"
        f"🤖 البوت: @{me.username}\n"
        f"👥 عدد القروبات الموثقة: {authorized_groups}\n"
        f"🚫 إجمالي عمليات الحظر المسجلة: {total_bans}\n"
        f"📝 إجمالي الأحداث المسجلة: {total_events}"
    )


async def send_report(chat_id: int):
    await app.send_message(chat_id, await build_report_text())


@app.on_message(filters.command(["تقرير"], prefixes=None))
async def report_command(client, message):
    if not is_main_owner(message.from_user.id):
        return
    await message.reply(await build_report_text())
