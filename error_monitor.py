"""
Real error/exception monitoring: forwards any ERROR-level log record (this
includes exceptions Pyrogram catches internally inside message handlers) to
the main owner as an instant Telegram DM.

This is the honest version of "detects problems automatically" — it does not
patch code by itself (an autonomous process rewriting its own source is a
security risk in itself), but it gives a real, immediate signal the moment
something breaks so it can be fixed fast.
"""

import asyncio
import logging

from db import MAIN_OWNER_ID

_installed = False


class _TelegramAlertHandler(logging.Handler):
    def __init__(self, app):
        super().__init__(level=logging.ERROR)
        self.app = app

    def emit(self, record):
        try:
            msg = self.format(record)
        except Exception:
            return

        loop = getattr(self.app, "loop", None)
        if loop is None or not loop.is_running():
            return

        text = f"⚠️ **خطأ تلقائي مكتشف بالبوت**\n\n`{msg[:3500]}`"
        try:
            asyncio.run_coroutine_threadsafe(self._send(text), loop)
        except Exception:
            pass

    async def _send(self, text):
        try:
            await self.app.send_message(MAIN_OWNER_ID, text)
        except Exception:
            pass


def install(app):
    """Idempotent: safe to call more than once (e.g. after a reconnect)."""
    global _installed
    if _installed:
        return
    handler = _TelegramAlertHandler(app)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
    logging.getLogger("pyrogram").addHandler(handler)
    logging.getLogger().addHandler(handler)
    _installed = True
