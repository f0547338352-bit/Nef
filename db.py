"""
Database layer for the moderation bot.

Uses a single SQLite database file (data.sqlite3) stored alongside this
module. Exposes a shared connection/cursor (`conn`, `c`) plus small helper
functions used by the command modules to check permissions, track admins
and owners, and read/write per-chat settings.
"""

import os
import sqlite3
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "data.sqlite3")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# The single main owner of the bot (full control everywhere, cannot be
# demoted/banned/muted by anyone). Provided by the bot's operator.
MAIN_OWNER_ID = int(os.environ.get("MAIN_OWNER_ID", "8495832936"))

# Default settings applied to any chat that hasn't customized them yet.
DEFAULT_SETTINGS = {
    "protect_links": 0,
    "protect_photo": 0,
    "protect_video": 0,
    "protect_sticker": 0,
    "protect_mentions": 0,
    "protect_invites": 0,
    "protect_add_bots": 0,
    "protect_new_accounts": 0,
    "anti_flood": 0,  # 0 = off, otherwise max messages allowed in the flood window
    "anti_spam": 0,
    "authorized": 0,  # 0 = bot ignores moderation commands in this chat until the main owner authorizes it
    "ai_protection": 0,  # 0 = off, 1 = messages are screened by a real AI model (see ai_moderation.py)
}


def init_db():
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS owners (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            level INTEGER DEFAULT 0,
            added_by INTEGER,
            added_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER,
            chat_id INTEGER,
            title TEXT,
            level TEXT,
            added_by INTEGER,
            added_at TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER,
            key TEXT,
            value INTEGER,
            PRIMARY KEY (chat_id, key)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS ban_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            admin_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            time TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            action TEXT,
            admin_id INTEGER,
            target_id INTEGER,
            reason TEXT,
            time TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS flood_tracker (
            chat_id INTEGER,
            user_id INTEGER,
            count INTEGER,
            window_start TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
        """
    )
    conn.commit()

    # Make sure the main owner is always registered as an owner.
    c.execute("SELECT 1 FROM owners WHERE user_id = ?", (MAIN_OWNER_ID,))
    if not c.fetchone():
        c.execute(
            "INSERT INTO owners (user_id, title, level, added_by, added_at) VALUES (?, ?, ?, ?, ?)",
            (MAIN_OWNER_ID, "المالك الأساسي", 0, MAIN_OWNER_ID, datetime.now().isoformat()),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Owners
# ---------------------------------------------------------------------------

def is_main_owner(user_id: int) -> bool:
    return user_id == MAIN_OWNER_ID


def is_owner(user_id: int) -> bool:
    c.execute("SELECT 1 FROM owners WHERE user_id = ?", (user_id,))
    return c.fetchone() is not None


def add_owner(user_id: int, title: str, level: int, added_by: int):
    c.execute(
        "INSERT OR REPLACE INTO owners (user_id, title, level, added_by, added_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, level, added_by, datetime.now().isoformat()),
    )
    conn.commit()


def remove_owner(user_id: int):
    c.execute("DELETE FROM owners WHERE user_id = ?", (user_id,))
    conn.commit()


def list_owners():
    c.execute("SELECT user_id, title, level FROM owners")
    return c.fetchall()


# ---------------------------------------------------------------------------
# Admins
# ---------------------------------------------------------------------------

def add_admin(user_id: int, chat_id: int, title: str, level: str, added_by: int):
    c.execute(
        "INSERT OR REPLACE INTO admins (user_id, chat_id, title, level, added_by, added_at) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, chat_id, title, level, added_by, datetime.now().isoformat()),
    )
    conn.commit()


def remove_admin(user_id: int, chat_id: int):
    c.execute("DELETE FROM admins WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    conn.commit()


def get_admin(user_id: int, chat_id: int):
    c.execute(
        "SELECT user_id, chat_id, title, level FROM admins WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    )
    return c.fetchone()


def list_admins(chat_id: int):
    c.execute("SELECT user_id, title, level FROM admins WHERE chat_id = ?", (chat_id,))
    return c.fetchall()


# Permission levels, from least to most powerful.
_LEVEL_RANK = {"basic": 1, "manager": 2, "all": 3}

# Which minimum admin level each action requires.
_ACTION_MIN_LEVEL = {
    "ban": "basic",
    "unban": "basic",
    "kick": "basic",
    "mute": "basic",
    "unmute": "basic",
    "settings": "manager",
}


def can_use_command(user_id: int, chat_id: int, action: str) -> bool:
    """Check whether a user is allowed to run a given moderation action in a chat."""
    if is_main_owner(user_id) or is_owner(user_id):
        return True

    admin = get_admin(user_id, chat_id)
    if not admin:
        return False

    level = admin[3]
    if level == "مالك" or level == "all":
        return True

    required = _ACTION_MIN_LEVEL.get(action, "all")
    return _LEVEL_RANK.get(level, 0) >= _LEVEL_RANK.get(required, 99)


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_setting(chat_id: int, key: str):
    c.execute("SELECT value FROM settings WHERE chat_id = ? AND key = ?", (chat_id, key))
    row = c.fetchone()
    if row is not None:
        return row[0]
    return DEFAULT_SETTINGS.get(key, 0)


def get_all_settings(chat_id: int):
    result = dict(DEFAULT_SETTINGS)
    c.execute("SELECT key, value FROM settings WHERE chat_id = ?", (chat_id,))
    for key, value in c.fetchall():
        result[key] = value
    return result


def update_setting(chat_id: int, key: str, value):
    c.execute(
        "INSERT OR REPLACE INTO settings (chat_id, key, value) VALUES (?, ?, ?)",
        (chat_id, key, value),
    )
    conn.commit()


# ---------------------------------------------------------------------------
# Chat authorization
# ---------------------------------------------------------------------------
# A group must be explicitly authorized by the main owner before the bot will
# act on any moderation command or protection setting in it. This lets the
# main owner control exactly which groups the bot is "trusted" in.

def is_chat_authorized(chat_id: int) -> bool:
    return bool(get_setting(chat_id, "authorized"))


def authorize_chat(chat_id: int, by: int):
    update_setting(chat_id, "authorized", 1)
    log_event(chat_id, "توثيق القروب", by)


def revoke_chat_authorization(chat_id: int, by: int):
    update_setting(chat_id, "authorized", 0)
    log_event(chat_id, "الغاء توثيق القروب", by)


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def log_event(chat_id: int, action: str, admin_id: int, target_id: int = None, reason: str = None):
    c.execute(
        "INSERT INTO events (chat_id, action, admin_id, target_id, reason, time) VALUES (?, ?, ?, ?, ?, ?)",
        (chat_id, action, admin_id, target_id, reason, datetime.now().isoformat()),
    )
    conn.commit()
