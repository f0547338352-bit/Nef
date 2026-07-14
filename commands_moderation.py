"""
Moderation commands: promote/demote roles, ban/kick/mute/restrict,
temporary and silent variants, and chat-wide lock/unlock toggles.

Registers its handlers on the shared `app` Client from main.py.
"""

from datetime import datetime, timedelta

from pyrogram import filters
from pyrogram.types import ChatPermissions

from main import app
from db import (
    c,
    conn,
    is_main_owner,
    is_owner,
    add_owner,
    remove_owner,
    add_admin,
    remove_admin,
    can_use_command,
    log_event,
    update_setting,
)
import ai_moderation

# ============================================
# الأوامر الإضافية - رفع/تنزيل الرتب - حظر/كتم - قفل/فتح
# ============================================

# ============================================
# أوامر رفع وتنزيل الرتب
# ============================================

@app.on_message(filters.command(["رفع_مشرف", "رفع_ادمن"], prefixes=None) & filters.group)
async def promote_admin(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # التحقق من الصلاحيات
    if not is_main_owner(user_id) and not is_owner(user_id):
        await message.reply("❌ **ليس لديك صلاحية لرفع المشرفين!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن رفع المالك الأساسي!**")
        return
    
    try:
        await app.promote_chat_member(
            chat_id, target_id,
            can_manage_chat=False,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False
        )
        
        add_admin(target_id, chat_id, "مشرف", "basic", user_id)
        log_event(chat_id, "رفع مشرف", user_id, target_id)
        
        await message.reply(
            f"✅ **تم رفع العضو كمشرف!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"📊 الرتبة: مشرف\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["رفع_مدير"], prefixes=None) & filters.group)
async def promote_manager(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_main_owner(user_id) and not is_owner(user_id):
        await message.reply("❌ **ليس لديك صلاحية لرفع المديرين!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن رفع المالك الأساسي!**")
        return
    
    try:
        await app.promote_chat_member(
            chat_id, target_id,
            can_manage_chat=True,
            can_delete_messages=True,
            can_restrict_members=True,
            can_promote_members=False,
            can_change_info=True,
            can_invite_users=True,
            can_pin_messages=True
        )
        
        add_admin(target_id, chat_id, "مدير", "manager", user_id)
        log_event(chat_id, "رفع مدير", user_id, target_id)
        
        await message.reply(
            f"✅ **تم رفع العضو كمدير!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"📊 الرتبة: مدير\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["رفع_مالك"], prefixes=None) & filters.group)
async def promote_owner(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # فقط المالك الأساسي يستطيع رفع مالك
    if not is_main_owner(user_id):
        await message.reply("❌ **المالك الأساسي فقط يستطيع رفع مالك!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن رفع المالك الأساسي!**")
        return
    
    # التحقق من عدد الملاك
    c.execute("SELECT COUNT(*) FROM owners")
    count = c.fetchone()[0]
    
    if count >= 3:
        await message.reply("❌ **لا يمكن إضافة أكثر من 3 ملاك!**")
        return
    
    try:
        add_owner(target_id, "مالك", 0, user_id)
        add_admin(target_id, chat_id, "مالك", "all", user_id)
        log_event(chat_id, "رفع مالك", user_id, target_id)
        
        await message.reply(
            f"✅ **تم رفع العضو كمالك!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"📊 الرتبة: مالك\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر تنزيل الرتب
# ============================================

@app.on_message(filters.command(["تنزيل_مشرف", "تنزيل_ادمن"], prefixes=None) & filters.group)
async def demote_admin(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_main_owner(user_id) and not is_owner(user_id):
        await message.reply("❌ **ليس لديك صلاحية لتنزيل المشرفين!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن تنزيل المالك الأساسي!**")
        return
    
    try:
        await app.promote_chat_member(
            chat_id, target_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        remove_admin(target_id, chat_id)
        log_event(chat_id, "تنزيل مشرف", user_id, target_id)
        
        await message.reply(
            f"✅ **تم تنزيل العضو من الإشراف!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["تنزيل_مدير"], prefixes=None) & filters.group)
async def demote_manager(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not is_main_owner(user_id) and not is_owner(user_id):
        await message.reply("❌ **ليس لديك صلاحية لتنزيل المديرين!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن تنزيل المالك الأساسي!**")
        return
    
    try:
        await app.promote_chat_member(
            chat_id, target_id,
            can_manage_chat=False,
            can_delete_messages=False,
            can_restrict_members=False,
            can_promote_members=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        remove_admin(target_id, chat_id)
        log_event(chat_id, "تنزيل مدير", user_id, target_id)
        
        await message.reply(
            f"✅ **تم تنزيل العضو من المديرين!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["تنزيل_مالك"], prefixes=None) & filters.group)
async def demote_owner(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    # فقط المالك الأساسي يستطيع تنزيل مالك
    if not is_main_owner(user_id):
        await message.reply("❌ **المالك الأساسي فقط يستطيع تنزيل مالك!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن تنزيل المالك الأساسي!**")
        return
    
    try:
        remove_owner(target_id)
        remove_admin(target_id, chat_id)
        log_event(chat_id, "تنزيل مالك", user_id, target_id)
        
        await message.reply(
            f"✅ **تم تنزيل العضو من الملاك!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر الحظر والطرد والكتم
# ============================================

@app.on_message(filters.command(["حظر", "ban"], prefixes=None) & filters.group)
async def ban_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "ban"):
        await message.reply("❌ **ليس لديك صلاحية للحظر!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن حظر المالك الأساسي!**")
        return
    
    reason = "بدون سبب"
    parts = message.text.split()
    if len(parts) > 1:
        reason = " ".join(parts[1:])
    
    try:
        await app.ban_chat_member(chat_id, target_id)
        c.execute("INSERT INTO ban_log (chat_id, admin_id, user_id, reason, time) VALUES (?, ?, ?, ?, ?)",
                  (chat_id, user_id, target_id, reason, datetime.now().isoformat()))
        conn.commit()
        log_event(chat_id, "حظر", user_id, target_id, reason)
        
        await message.reply(
            f"✅ **تم حظر العضو!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"📝 السبب: {reason}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["فك_حظر", "unban"], prefixes=None) & filters.group)
async def unban_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "unban"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        await app.unban_chat_member(chat_id, target_id)
        log_event(chat_id, "فك حظر", user_id, target_id)
        
        await message.reply(
            f"✅ **تم فك الحظر عن العضو!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["طرد", "kick"], prefixes=None) & filters.group)
async def kick_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "kick"):
        await message.reply("❌ **ليس لديك صلاحية للطرد!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن طرد المالك الأساسي!**")
        return
    
    try:
        await app.ban_chat_member(chat_id, target_id)
        await app.unban_chat_member(chat_id, target_id)
        log_event(chat_id, "طرد", user_id, target_id)
        
        await message.reply(
            f"✅ **تم طرد العضو!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["فك_طرد"], prefixes=None) & filters.group)
async def unkick_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "unban"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        await app.unban_chat_member(chat_id, target_id)
        log_event(chat_id, "فك طرد", user_id, target_id)
        
        await message.reply(
            f"✅ **تم فك الطرد عن العضو!**\n\n"
            f"👤 {target_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["كتم", "mute"], prefixes=None) & filters.group)
async def mute_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "mute"):
        await message.reply("❌ **ليس لديك صلاحية للكتم!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن كتم المالك الأساسي!**")
        return
    
    try:
        await app.restrict_chat_member(
            chat_id, target_id,
            ChatPermissions(can_send_messages=False)
        )
        log_event(chat_id, "كتم", user_id, target_id)
        
        await message.reply(
            f"✅ **تم كتم العضو!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["فك_كتم", "unmute"], prefixes=None) & filters.group)
async def unmute_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "unmute"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        await app.restrict_chat_member(
            chat_id, target_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        log_event(chat_id, "فك كتم", user_id, target_id)
        
        await message.reply(
            f"✅ **تم فك الكتم عن العضو!**\n\n"
            f"👤 {target_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر التقييد
# ============================================

@app.on_message(filters.command(["تقييد", "restrict"], prefixes=None) & filters.group)
async def restrict_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "mute"):
        await message.reply("❌ **ليس لديك صلاحية للتقييد!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن تقييد المالك الأساسي!**")
        return
    
    try:
        await app.restrict_chat_member(
            chat_id, target_id,
            ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            )
        )
        log_event(chat_id, "تقييد", user_id, target_id)
        
        await message.reply(
            f"✅ **تم تقييد العضو!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"📊 لا يستطيع إرسال أي شيء\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["فك_تقييد", "unrestrict"], prefixes=None) & filters.group)
async def unrestrict_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "unmute"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    try:
        await app.restrict_chat_member(
            chat_id, target_id,
            ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        log_event(chat_id, "فك تقييد", user_id, target_id)
        
        await message.reply(
            f"✅ **تم فك التقييد عن العضو!**\n\n"
            f"👤 {target_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر الحظر المؤقت والكتم المؤقت
# ============================================

@app.on_message(filters.command(["حظر_مؤقت"], prefixes=None) & filters.group)
async def temp_ban_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "ban"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن حظر المالك الأساسي!**")
        return
    
    # استخراج المدة (بالدقائق)
    parts = message.text.split()
    duration = 60  # افتراضي 60 دقيقة
    
    if len(parts) > 1:
        try:
            duration = int(parts[1])
        except:
            pass
    
    try:
        until_date = datetime.now() + timedelta(minutes=duration)
        await app.ban_chat_member(chat_id, target_id, until_date=until_date)
        log_event(chat_id, "حظر مؤقت", user_id, target_id, f"{duration} دقيقة")
        
        await message.reply(
            f"✅ **تم حظر العضو مؤقتاً!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"⏱️ المدة: {duration} دقيقة\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["كتم_مؤقت"], prefixes=None) & filters.group)
async def temp_mute_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "mute"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن كتم المالك الأساسي!**")
        return
    
    # استخراج المدة (بالدقائق)
    parts = message.text.split()
    duration = 60  # افتراضي 60 دقيقة
    
    if len(parts) > 1:
        try:
            duration = int(parts[1])
        except:
            pass
    
    try:
        until_date = datetime.now() + timedelta(minutes=duration)
        await app.restrict_chat_member(
            chat_id, target_id,
            ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        log_event(chat_id, "كتم مؤقت", user_id, target_id, f"{duration} دقيقة")
        
        await message.reply(
            f"✅ **تم كتم العضو مؤقتاً!**\n\n"
            f"👤 {target_user.first_name}\n"
            f"⏱️ المدة: {duration} دقيقة\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر الطرد الصامت والحظر الصامت
# ============================================

@app.on_message(filters.command(["طرد_صامت"], prefixes=None) & filters.group)
async def silent_kick_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "kick"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن طرد المالك الأساسي!**")
        return
    
    try:
        await app.ban_chat_member(chat_id, target_id)
        await app.unban_chat_member(chat_id, target_id)
        log_event(chat_id, "طرد صامت", user_id, target_id)
        
        # لا نرسل أي رسالة (طرد صامت)
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["حظر_صامت"], prefixes=None) & filters.group)
async def silent_ban_user(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "ban"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    if not message.reply_to_message:
        await message.reply("⚠️ **الرجاء الرد على رسالة العضو!**")
        return
    
    target_user = message.reply_to_message.from_user
    target_id = target_user.id
    
    if is_main_owner(target_id):
        await message.reply("❌ **لا يمكن حظر المالك الأساسي!**")
        return
    
    try:
        await app.ban_chat_member(chat_id, target_id)
        log_event(chat_id, "حظر صامت", user_id, target_id)
        
        # لا نرسل أي رسالة (حظر صامت)
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر القفل والفتح
# ============================================

@app.on_message(filters.command(["قفل"], prefixes=None) & filters.group)
async def lock_chat(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    try:
        await app.set_chat_permissions(chat_id, ChatPermissions())
        log_event(chat_id, "قفل", user_id)
        
        await message.reply(
            "🔒 **تم قفل المجموعة!**\n\n"
            "جميع الأعضاء ممنوعون من الإرسال\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

@app.on_message(filters.command(["فتح"], prefixes=None) & filters.group)
async def unlock_chat(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    try:
        await app.set_chat_permissions(chat_id, ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        ))
        log_event(chat_id, "فتح", user_id)
        
        await message.reply(
            "🔓 **تم فتح المجموعة!**\n\n"
            "جميع الأعضاء يستطيعون الإرسال\n"
            f"👤 بواسطة: {message.from_user.first_name}"
        )
        
    except Exception as e:
        await message.reply(f"❌ **خطأ:** {e}")

# ============================================
# أوامر قفل وفتح الأنواع المختلفة
# ============================================

@app.on_message(filters.command(["قفل_الروابط"], prefixes=None) & filters.group)
async def lock_links(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_links", 1)
    log_event(chat_id, "قفل الروابط", user_id)
    await message.reply("🔒 **تم قفل الروابط!**\n\nسيتم حذف أي رابط يتم إرساله.")

@app.on_message(filters.command(["فتح_الروابط"], prefixes=None) & filters.group)
async def unlock_links(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_links", 0)
    log_event(chat_id, "فتح الروابط", user_id)
    await message.reply("🔓 **تم فتح الروابط!**\n\nيمكن للأعضاء إرسال الروابط.")

@app.on_message(filters.command(["قفل_الصور"], prefixes=None) & filters.group)
async def lock_photos(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_photo", 1)
    log_event(chat_id, "قفل الصور", user_id)
    await message.reply("🔒 **تم قفل الصور!**\n\nسيتم حذف أي صورة يتم إرسالها.")

@app.on_message(filters.command(["فتح_الصور"], prefixes=None) & filters.group)
async def unlock_photos(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_photo", 0)
    log_event(chat_id, "فتح الصور", user_id)
    await message.reply("🔓 **تم فتح الصور!**\n\nيمكن للأعضاء إرسال الصور.")

@app.on_message(filters.command(["قفل_الفيديو"], prefixes=None) & filters.group)
async def lock_videos(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_video", 1)
    log_event(chat_id, "قفل الفيديو", user_id)
    await message.reply("🔒 **تم قفل الفيديو!**\n\nسيتم حذف أي فيديو يتم إرساله.")

@app.on_message(filters.command(["فتح_الفيديو"], prefixes=None) & filters.group)
async def unlock_videos(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_video", 0)
    log_event(chat_id, "فتح الفيديو", user_id)
    await message.reply("🔓 **تم فتح الفيديو!**\n\nيمكن للأعضاء إرسال الفيديو.")

@app.on_message(filters.command(["قفل_الملصقات"], prefixes=None) & filters.group)
async def lock_stickers(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_sticker", 1)
    log_event(chat_id, "قفل الملصقات", user_id)
    await message.reply("🔒 **تم قفل الملصقات!**\n\nسيتم حذف أي ملصق يتم إرساله.")

@app.on_message(filters.command(["فتح_الملصقات"], prefixes=None) & filters.group)
async def unlock_stickers(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_sticker", 0)
    log_event(chat_id, "فتح الملصقات", user_id)
    await message.reply("🔓 **تم فتح الملصقات!**\n\nيمكن للأعضاء إرسال الملصقات.")

@app.on_message(filters.command(["قفل_المعاينة"], prefixes=None) & filters.group)
async def lock_preview(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    await app.set_chat_permissions(chat_id, ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=False
    ))
    log_event(chat_id, "قفل المعاينة", user_id)
    await message.reply("🔒 **تم قفل المعاينة!**\n\nلن تظهر معاينة الروابط.")

@app.on_message(filters.command(["فتح_المعاينة"], prefixes=None) & filters.group)
async def unlock_preview(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    await app.set_chat_permissions(chat_id, ChatPermissions(
        can_send_messages=True,
        can_send_media_messages=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True
    ))
    log_event(chat_id, "فتح المعاينة", user_id)
    await message.reply("🔓 **تم فتح المعاينة!**\n\nستظهر معاينة الروابط.")

@app.on_message(filters.command(["قفل_التوجيه"], prefixes=None) & filters.group)
async def lock_forward(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    try:
        await app.set_chat_permissions(chat_id, ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=False,
            can_add_web_page_previews=True
        ))
        log_event(chat_id, "قفل التوجيه", user_id)
        await message.reply("🔒 **تم قفل التوجيه!**\n\nلا يمكن للأعضاء إعادة توجيه الرسائل.")
    except:
        await message.reply("❌ **لا يمكن قفل التوجيه في هذه المجموعة!**")

@app.on_message(filters.command(["فتح_التوجيه"], prefixes=None) & filters.group)
async def unlock_forward(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    try:
        await app.set_chat_permissions(chat_id, ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        ))
        log_event(chat_id, "فتح التوجيه", user_id)
        await message.reply("🔓 **تم فتح التوجيه!**\n\nيمكن للأعضاء إعادة توجيه الرسائل.")
    except:
        await message.reply("❌ **لا يمكن فتح التوجيه في هذه المجموعة!**")

@app.on_message(filters.command(["قفل_البوتات"], prefixes=None) & filters.group)
async def lock_bots(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_add_bots", 1)
    log_event(chat_id, "قفل البوتات", user_id)
    await message.reply("🔒 **تم قفل إضافة البوتات!**\n\nلا يمكن للأعضاء إضافة بوتات جديدة.")

@app.on_message(filters.command(["فتح_البوتات"], prefixes=None) & filters.group)
async def unlock_bots(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_add_bots", 0)
    log_event(chat_id, "فتح البوتات", user_id)
    await message.reply("🔓 **تم فتح إضافة البوتات!**\n\nيمكن للأعضاء إضافة بوتات جديدة.")

# ============================================
# أوامر الحماية الإضافية
# ============================================

@app.on_message(filters.command(["قفل_المنشن"], prefixes=None) & filters.group)
async def lock_mentions(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_mentions", 1)
    log_event(chat_id, "قفل المنشن", user_id)
    await message.reply("🔒 **تم قفل المنشن!**\n\nسيتم حذف أي منشن غير مرغوب.")

@app.on_message(filters.command(["فتح_المنشن"], prefixes=None) & filters.group)
async def unlock_mentions(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_mentions", 0)
    log_event(chat_id, "فتح المنشن", user_id)
    await message.reply("🔓 **تم فتح المنشن!**")

@app.on_message(filters.command(["قفل_الدعوات"], prefixes=None) & filters.group)
async def lock_invites(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_invites", 1)
    log_event(chat_id, "قفل الدعوات", user_id)
    await message.reply("🔒 **تم قفل روابط الدعوات!**\n\nسيتم حذف أي رابط دعوة يتم إرساله.")

@app.on_message(filters.command(["فتح_الدعوات"], prefixes=None) & filters.group)
async def unlock_invites(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_invites", 0)
    log_event(chat_id, "فتح الدعوات", user_id)
    await message.reply("🔓 **تم فتح روابط الدعوات!**")

@app.on_message(filters.command(["قفل_الحسابات_الجديدة"], prefixes=None) & filters.group)
async def lock_new_accounts(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_new_accounts", 1)
    log_event(chat_id, "قفل الحسابات الجديدة", user_id)
    await message.reply("🔒 **تم قفل الحسابات الجديدة!**\n\nسيتم حظر أي حساب عمره أقل من 7 أيام.")

@app.on_message(filters.command(["فتح_الحسابات_الجديدة"], prefixes=None) & filters.group)
async def unlock_new_accounts(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "protect_new_accounts", 0)
    log_event(chat_id, "فتح الحسابات الجديدة", user_id)
    await message.reply("🔓 **تم فتح الحسابات الجديدة!**")

@app.on_message(filters.command(["قفل_التكرار"], prefixes=None) & filters.group)
async def lock_flood(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "anti_flood", 3)
    log_event(chat_id, "قفل التكرار", user_id)
    await message.reply("🔒 **تم قفل التكرار!**\n\nسيتم حظر أي عضو يرسل أكثر من 3 رسائل في 10 ثوان.")

@app.on_message(filters.command(["فتح_التكرار"], prefixes=None) & filters.group)
async def unlock_flood(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "anti_flood", 0)
    log_event(chat_id, "فتح التكرار", user_id)
    await message.reply("🔓 **تم فتح التكرار!**\n\nلن يتم حظر الأعضاء بسبب التكرار.")

@app.on_message(filters.command(["قفل_السبام"], prefixes=None) & filters.group)
async def lock_spam(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "anti_spam", 1)
    log_event(chat_id, "قفل السبام", user_id)
    await message.reply("🔒 **تم قفل السبام!**\n\nسيتم حظر أي عضو يرسل رسائل سبام.")

@app.on_message(filters.command(["فتح_السبام"], prefixes=None) & filters.group)
async def unlock_spam(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return
    
    update_setting(chat_id, "anti_spam", 0)
    log_event(chat_id, "فتح السبام", user_id)
    await message.reply("🔓 **تم فتح السبام!**")

# ============================================
# الحماية الذكية (فحص فعلي بالذكاء الاصطناعي)
# ============================================

@app.on_message(filters.command(["تفعيل_الحماية_الذكية"], prefixes=None) & filters.group)
async def enable_ai_protection(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return

    if not ai_moderation.is_configured():
        await message.reply(
            "⚠️ **الحماية الذكية غير مفعّلة على مستوى البوت.**\n\nمفتاح OpenAI غير موجود، تواصل مع مطور البوت."
        )
        return

    update_setting(chat_id, "ai_protection", 1)
    log_event(chat_id, "تفعيل الحماية الذكية", user_id)
    await message.reply(
        "🧠 **تم تفعيل الحماية الذكية!**\n\nكل رسالة نصية الحين تُفحص فعليًا بالذكاء الاصطناعي (سبام / احتيال / إساءة) وتُحذف تلقائيًا إذا كانت مخالفة."
    )

@app.on_message(filters.command(["ايقاف_الحماية_الذكية"], prefixes=None) & filters.group)
async def disable_ai_protection(client, message):
    chat_id = message.chat.id
    user_id = message.from_user.id

    if not can_use_command(user_id, chat_id, "settings"):
        await message.reply("❌ **ليس لديك صلاحية!**")
        return

    update_setting(chat_id, "ai_protection", 0)
    log_event(chat_id, "ايقاف الحماية الذكية", user_id)
    await message.reply("🔕 **تم إيقاف الحماية الذكية.**")

# ============================================
# قائمة الأوامر الكاملة
# ============================================

# الأوامر المتاحة:
# 
# رفع وتنزيل الرتب:
# رفع_مشرف, رفع_ادمن, رفع_مدير, رفع_مالك
# تنزيل_مشرف, تنزيل_ادمن, تنزيل_مدير, تنزيل_مالك
# 
# الحظر والطرد والكتم:
# حظر, فك_حظر, طرد, فك_طرد, كتم, فك_كتم, تقييد, فك_تقييد
# حظر_مؤقت, كتم_مؤقت, طرد_صامت, حظر_صامت
# 
# القفل والفتح:
# قفل, فتح
# قفل_الروابط, فتح_الروابط
# قفل_الصور, فتح_الصور
# قفل_الفيديو, فتح_الفيديو
# قفل_الملصقات, فتح_الملصقات
# قفل_المعاينة, فتح_المعاينة
# قفل_التوجيه, فتح_التوجيه
# قفل_البوتات, فتح_البوتات
# قفل_المنشن, فتح_المنشن
# قفل_الدعوات, فتح_الدعوات
# قفل_الحسابات_الجديدة, فتح_الحسابات_الجديدة
# قفل_التكرار, فتح_التكرار
# قفل_السبام, فتح_السبام