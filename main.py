"""
Entry point for the group-moderation Telegram bot.

Sets up the Pyrogram Client, initializes the database, then imports the
command modules so their `@app.on_message` handlers register themselves.
Also runs a background loop that DMs the main owner a status report every
24 hours (see reports.py) so there is a real, verifiable signal that the
bot is alive — rather than a vague "self-improves" claim.
"""

import asyncio
import os

from pyrogram import Client, idle

from db import init_db, MAIN_OWNER_ID

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

app = Client(
    "moderation_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir=os.path.dirname(__file__),
)

init_db()

# Import command/handler modules AFTER `app` exists so their decorators can
# attach to it. These imports have side effects (handler registration) —
# do not remove them even though they look unused.
import commands_basic  # noqa: E402,F401
import authorization  # noqa: E402,F401
import commands_moderation  # noqa: E402,F401
import protection  # noqa: E402,F401
import reports  # noqa: E402,F401

import error_monitor  # noqa: E402,F401

DAILY_REPORT_SECONDS = 24 * 60 * 60


async def _daily_report_loop():
    while True:
        await asyncio.sleep(DAILY_REPORT_SECONDS)
        try:
            await reports.send_report(MAIN_OWNER_ID)
        except Exception as e:
            print(f"[daily report] failed to send: {e}")


async def _run_once():
    """Starts the client, runs until a stop signal, then cleans up.

    Returns True if this was a clean shutdown (stop signal received) and
    False if `app.start()` itself blew up (e.g. a transient network/auth
    error), so the caller knows whether to retry.
    """
    try:
        await app.start()
    except Exception as e:
        print(f"[startup] app.start() failed: {e}")
        return False

    print("Bot connected to Telegram and is listening for messages.")
    error_monitor.install(app)  # forwards any error-level log (incl. handler exceptions) to the main owner

    try:
        await app.send_message(
            MAIN_OWNER_ID,
            "✅ **تم تشغيل البوت.**\n\nأرسل لي `تقرير` بالخاص في أي وقت عشان أعطيك حالة البوت الحالية.",
        )
    except Exception as e:
        print(f"[startup] could not DM main owner: {e}")

    report_task = app.loop.create_task(_daily_report_loop())
    try:
        await idle()
    finally:
        report_task.cancel()
        await app.stop()
    return True


async def _main():
    # Keep retrying with backoff if the connection setup itself fails, so the
    # bot stays up as reliably as this environment allows. `idle()` only
    # returns on a real stop signal (e.g. workflow restart), at which point
    # we exit cleanly instead of looping.
    while True:
        clean_shutdown = await _run_once()
        if clean_shutdown:
            break
        await asyncio.sleep(10)


if __name__ == "__main__":
    print("Bot is starting...")
    app.run(_main())
