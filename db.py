import os
import sqlite3
from datetime import datetime

# تحديد مسار قاعدة البيانات بجانب ملف الكود
DB_PATH = os.path.join(os.path.dirname(__file__), "data.sqlite3")

# الاتصال بقاعدة البيانات مع تفعيل التزامن المتعدد
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
c = conn.cursor()

# جلب معرف المالك الأساسي للبوت من متغيرات البيئة أو استخدام الافتراضي المكتوب في الكود
MAIN_OWNER_ID = int(os.environ.get("MAIN_OWNER_ID", "8495832936"))

# الإعدادات الافتراضية لأي مجموعة جديدة
DEFAULT_SETTINGS = {
    "protect_links": 0,
    "protect_photo": 0,
    "protect_invites": 0,
    "protect_add_bots": 0,
    "protect_new_accounts": 0,
    "anti_flood": 0,
    "anti_spam": 0,
    "authorized": 0,
    "ai_protection": 0
}

# مستويات صلاحيات المسؤولين وترتيبها وقيمتها
_LEVEL_RANK = {
    "basic": 1,
    "manager": 2,
    "all": 3
}

# الحد الأدنى المطلوب من الصلاحية لكل إجراء مشرف
_ACTION_MIN_LEVEL = {
    "ban": "basic",
    "unban": "basic",
    "settings": "manager",
}

def init_db():
    """تهيئة جداول قاعدة البيانات عند تشغيل البوت لأول مرة"""
    # 1. جدول الملاك (owners)
    c.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            user_id INTEGER PRIMARY KEY,
            title TEXT,
            level INTEGER DEFAULT 0,
            added_by INTEGER,
            added_at TEXT
        )
    """)
    
    # 2. جدول المشرفين (admins)
    c.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER,
            chat_id INTEGER,
            title TEXT,
            level TEXT,
            added_by INTEGER,
            added_at TEXT,
            PRIMARY KEY (user_id, chat_id)
        )
    """)
    
    # 3. جدول الإعدادات للمجموعات (settings)
    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            chat_id INTEGER,
            key TEXT,
            value INTEGER,
            PRIMARY KEY (chat_id, key)
        )
    """)
    
    # 4. جدول سجل الحظر العقوبات (ban_log)
    c.execute("""
        CREATE TABLE IF NOT EXISTS ban_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            user_id INTEGER,
            reason TEXT,
            time TEXT
        )
    """)
    
    # 5. جدول الأحداث والتقارير (event_log)
    c.execute("""
        CREATE TABLE IF NOT EXISTS event_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER,
            event_type TEXT,
            description TEXT,
            time TEXT
        )
    """)
    conn.commit()

# ==========================================
# == صلاحيات الملاك والمشرفين ==
# ==========================================

def get_main_owner() -> int:
    """الحصول على معرف المالك الأساسي للبوت"""
    return MAIN_OWNER_ID

def is_main_owner(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم هو المالك الأساسي"""
    return user_id == MAIN_OWNER_ID

def is_owner(user_id: int) -> bool:
    """التحقق مما إذا كان المستخدم مسجلاً كمالك فرعي أو أساسي"""
    if is_main_owner(user_id):
        return True
    c.execute("SELECT 1 FROM owners WHERE user_id = ?", (user_id,))
    return c.fetchone() is not None

def get_admin(user_id: int, chat_id: int):
    """جلب بيانات المشرف وصلاحياته من قاعدة البيانات"""
    c.execute("SELECT user_id, chat_id, title, level FROM admins WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
    return c.fetchone()

def is_admin(user_id: int, chat_id: int) -> bool:
    """التحقق السريع مما إذا كان المستخدم مشرفاً أو مالكاً"""
    if is_owner(user_id):
        return True
    return get_admin(user_id, chat_id) is not None

def list_admins(chat_id: int):
    """جلب قائمة جميع المشرفين في مجموعة محددة"""
    c.execute("SELECT user_id, title, level FROM admins WHERE chat_id = ?", (chat_id,))
    return c.fetchall()

def can_use_command(user_id: int, chat_id: int, action: str) -> bool:
    """التحقق من قدرة المستخدم على تنفيذ إجراء إشرافي معين بناءً على مستواه"""
    if is_main_owner(user_id) or is_owner(user_id):
        return True
        
    admin = get_admin(user_id, chat_id)
    if not admin:
        return False
        
    level = admin[3] # حقل level من جدول المشرفين
    if level == "مالك" or level == "all":
        return True
        
    required = _ACTION_MIN_LEVEL.get(action, "manager")
    
    # مقارنة الرتبة الحالية بالرتبة المطلوبة للإجراء
    user_rank = _LEVEL_RANK.get(level, 0)
    req_rank = _LEVEL_RANK.get(required, 99)
    
    return user_rank >= req_rank

# ==========================================
# == الإعدادات والتحكم بالمجموعات ==
# ==========================================

def get_setting(chat_id: int, key: str) -> int:
    """جلب قيمة إعداد معين لمجموعة معينة"""
    c.execute("SELECT value FROM settings WHERE chat_id = ? AND key = ?", (chat_id, key))
    row = c.fetchone()
    if row is not None:
        return row[0]
    return DEFAULT_SETTINGS.get(key, 0)

def get_all_settings(chat_id: int) -> dict:
    """جلب جميع الإعدادات الحالية لجروب معين دفعة واحدة"""
    result = dict(DEFAULT_SETTINGS)
    c.execute("SELECT key, value FROM settings WHERE chat_id = ?", (chat_id,))
    for key, value in c.fetchall():
        result[key] = value
    return result

def update_setting(chat_id: int, key: str, value: int):
    """تحديث قيمة إعداد معين"""
    c.execute("""
        INSERT OR REPLACE INTO settings (chat_id, key, value)
        VALUES (?, ?, ?)
    """, (chat_id, key, value))
    conn.commit()

# ==========================================
# == توثيق وتنشيط المجموعات ==
# ==========================================

def is_chat_authorized(chat_id: int) -> bool:
    """التحقق مما إذا كان القروب موثقاً من المالك الأساسي"""
    return bool(get_setting(chat_id, "authorized"))

def authorize_chat(chat_id: int, by: int):
    """توثيق القروب وتفعيله"""
    update_setting(chat_id, "authorized", 1)
    log_event(chat_id, "توثيق القروب", by)

def revoke_chat_authorization(chat_id: int, by: int):
    """إلغاء توثيق وتنشيط القروب"""
    update_setting(chat_id, "authorized", 0)
    log_event(chat_id, "إلغاء توثيق القروب", by)

# ==========================================
# == نظام السجلات والتقارير ==
# ==========================================

def log_event(chat_id: int, event_type: str, description_or_by: int):
    """تسجيل الأحداث الهامة في قاعدة البيانات"""
    try:
        desc = f"بواسطة المالك أو المشرف ذو الأيدي: {description_or_by}"
        c.execute(
            "INSERT INTO event_log (chat_id, event_type, description, time) VALUES (?, ?, ?, ?)",
            (chat_id, event_type, desc, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging event: {e}")
