import os
import sys
import asyncio 
import logging
import psutil
import speedtest
import platform
import subprocess
from datetime import datetime
from database import db, mongodb_version
from config import Config, temp
from platform import python_version
from translation import Translation
from utils.notifications import NotificationManager
from pyrogram import Client, filters, enums, __version__ as pyrogram_version
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaDocument

# Setup logging
logger = logging.getLogger(__name__)

main_buttons = [[
        InlineKeyboardButton('📜 sᴜᴘᴘᴏʀᴛ ɢʀᴏᴜᴘ ', url=Config.SUPPORT_GROUP),
        InlineKeyboardButton('🤖 ᴜᴘᴅᴀᴛᴇ ᴄʜᴀɴɴᴇʟ  ', url=Config.UPDATE_CHANNEL)
        ],[
        InlineKeyboardButton('📊 My Plan', callback_data='my_plan'),
        InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans')
        ],[
        InlineKeyboardButton('🙋‍♂️ ʜᴇʟᴘ', callback_data='help'),
        InlineKeyboardButton('💁‍♂️ ᴀʙᴏᴜᴛ ', callback_data='about')
        ],[
        InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ⚙️', callback_data='settings#main'),
        InlineKeyboardButton('📞 Contact Admin', callback_data='contact_admin')
        ]]

# Force subscribe buttons
force_sub_buttons = [[
        InlineKeyboardButton('📜 Join Support Group', url=Config.SUPPORT_GROUP),
        InlineKeyboardButton('🤖 Join Update Channel', url=Config.UPDATE_CHANNEL)
        ],[
        InlineKeyboardButton('✅ Check Subscription', callback_data='check_subscription')
        ]]


#===================Start Function===================#

@Client.on_message(filters.private & filters.command(['start']))
async def start(client, message):
    user = message.from_user
    logger.info(f"Start command from user {user.id} ({user.first_name})")
    
    try:
        if not await db.is_user_exist(user.id):
            await db.add_user(user.id, user.first_name)
            logger.info(f"New user added: {user.id}")
            
            # Notify about new user
            notify = NotificationManager(client)
            await notify.notify_user_action(user.id, "New User Registration", f"User: {user.first_name}")
        
        # Auto-grant premium to sudo users (owners and admins)
        if Config.is_sudo_user(user.id):
            if not await db.is_premium_user(user.id):
                from datetime import datetime, timedelta
                # Grant unlimited premium to sudo users (expires in 10 years)
                await db.add_premium_user(user.id, "pro", 3650, 0)
                logger.info(f"Auto-granted premium to sudo user: {user.id}")
        
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user.id):
            subscription_status = await db.check_force_subscribe(user.id, client)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await message.reply_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons),
                    quote=True
                )
        
        reply_markup = InlineKeyboardMarkup(main_buttons)
        jishubotz = await message.reply_sticker("CAACAgUAAxkBAAECEEBlLA-nYcsWmsNWgE8-xqIkriCWAgACJwEAAsiUZBTiPWKAkUSmmh4E")
        await asyncio.sleep(2)
        await jishubotz.delete()
        text=Translation.START_TXT.format(user.mention)
        await message.reply_text(
            text=text,
            reply_markup=reply_markup,
            quote=True
        )
        logger.info(f"Start message sent to user {user.id}")
    except Exception as e:
        logger.error(f"Error in start command for user {user.id}: {e}", exc_info=True)
        await message.reply_text(
            "❌ An error occurred. Please try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]])
        )

# Force subscribe callback handler
@Client.on_callback_query(filters.regex(r'^check_subscription$'))
async def check_subscription_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    try:
        # Check if user is now subscribed
        subscription_status = await db.check_force_subscribe(user_id, client)
        
        if subscription_status['all_subscribed']:
            await callback_query.answer("✅ Subscription verified! Welcome!", show_alert=True)
            
            # Show main menu
            reply_markup = InlineKeyboardMarkup(main_buttons)
            text = f"🎉 <b>Welcome {callback_query.from_user.first_name}!</b>\n\n" + Translation.START_TXT.format(callback_query.from_user.mention)
            
            await callback_query.message.edit_text(
                text=text,
                reply_markup=reply_markup
            )
        else:
            missing = []
            if not subscription_status['update_channel']:
                missing.append("Update Channel")
            if not subscription_status['support_group']:
                missing.append("Support Group")
                
            await callback_query.answer(f"❌ Please join: {', '.join(missing)}", show_alert=True)
            
    except Exception as e:
        await callback_query.answer("❌ Error checking subscription. Please try again.", show_alert=True)

# Premium plans callback handler
@Client.on_callback_query(filters.regex(r'^premium'))
async def premium_callback(client, callback_query):
    user_id = callback_query.from_user.id
    callback_data = callback_query.data
    
    if callback_data in ['premium_plans', 'premium#plans', 'premium#main']:
        # Get user's current plan
        current_plan = "FREE"
        plan_details = await db.get_premium_user_details(user_id)
        
        if plan_details:
            current_plan = plan_details.get('plan_type', 'FREE').upper()
        
        plans_text = (
            "💎 <b>Premium Plans</b>\n\n"
            f"👤 <b>Your Current Plan:</b> {current_plan}\n"
        )
        
        if plan_details and plan_details.get('expires_at'):
            from datetime import datetime
            expires_at = plan_details['expires_at']
            if expires_at > datetime.utcnow():
                plans_text += f"⏰ <b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        plans_text += (
            "\n📋 <b>Available Plans:</b>\n\n"
            "🆓 <b>FREE PLAN</b>\n"
            "• 5 forwarding processes per day\n"
            "• Basic features only\n"
            "• No FTM mode\n\n"
            
            "✨ <b>PLUS PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• All basic features\n"
            "• No FTM mode\n"
            "• 15 days: ₹199\n"
            "• 30 days: ₹299\n\n"
            
            "🏆 <b>PRO PLAN</b>\n"
            "• Unlimited forwarding processes\n"
            "• FTM mode enabled\n"
            "• Priority support\n"
            "• All premium features\n"
            "• 15 days: ₹299\n"
            "• 30 days: ₹549\n\n"
            
            "💳 <b>Payment:</b> UPI - 6354228145@axl\n"
            "📸 <b>After payment, send screenshot with /verify</b>"
        )
        
        plans_buttons = [
            [
                InlineKeyboardButton("✨ Plus 15 Days (₹199)", callback_data="buy_plus_15"),
                InlineKeyboardButton("✨ Plus 30 Days (₹299)", callback_data="buy_plus_30")
            ],
            [
                InlineKeyboardButton("🏆 Pro 15 Days (₹299)", callback_data="buy_pro_15"),
                InlineKeyboardButton("🏆 Pro 30 Days (₹549)", callback_data="buy_pro_30")
            ],
            [
                InlineKeyboardButton("📊 My Plan Details", callback_data="my_plan"),
                InlineKeyboardButton("🔙 Back", callback_data="back")
            ]
        ]
        
        await callback_query.message.edit_text(
            text=plans_text,
            reply_markup=InlineKeyboardMarkup(plans_buttons)
        )



#==================Restart Function==================#

@Client.on_message(filters.private & filters.command(['restart', "r"]) & filters.user(Config.OWNER_ID))
async def restart(client, message):
    msg = await message.reply_text(
        text="<i>Trying To Restarting.....</i>",
        quote=True
    )
    await asyncio.sleep(5)
    await msg.edit("<i>Server Restarted Successfully ✅</i>")
    os.execl(sys.executable, sys.executable, *sys.argv)
    


#==================Callback Functions==================#

#==================Help Command==================#

@Client.on_message(filters.private & filters.command(['help']))
async def help_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Help command from user {user_id}")
    
    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id):
            subscription_status = await db.check_force_subscribe(user_id, client)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await message.reply_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons),
                    quote=True
                )
        
        # Check if user is admin to show admin commands
        is_admin = Config.is_sudo_user(user_id)
        
        # Create help buttons
        buttons = [[
            InlineKeyboardButton('🛠️ How To Use Me 🛠️', callback_data='how_to_use')
        ],[
            InlineKeyboardButton('⚙️ Settings ⚙️', callback_data='settings#main'),
            InlineKeyboardButton('📊 Stats 📊', callback_data='status')
        ],[
            InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')
        ]]
        
        # Add admin commands button for admins only
        if is_admin:
            buttons.append([InlineKeyboardButton('👨‍💻 Admin Commands 👨‍💻', callback_data='admin_commands')])
        
        buttons.append([InlineKeyboardButton('🔙 Back', callback_data='back')])
        
        await message.reply_text(
            text=Translation.HELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        logger.debug(f"Help message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in help command for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred. Please try again.")

@Client.on_callback_query(filters.regex(r'^help$'))
async def helpcb(bot, query):
    user_id = query.from_user.id
    logger.info(f"Help callback from user {user_id}")
    
    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id):
            subscription_status = await db.check_force_subscribe(user_id, bot)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await query.message.edit_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons)
                )
        
        # Check if user is admin to show admin commands
        is_admin = Config.is_sudo_user(user_id)
        
        # Create help buttons
        buttons = [[
            InlineKeyboardButton('🛠️ How To Use Me 🛠️', callback_data='how_to_use')
        ],[
            InlineKeyboardButton('⚙️ Settings ⚙️', callback_data='settings#main'),
            InlineKeyboardButton('📊 Stats 📊', callback_data='status')
        ],[
            InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')
        ]]
        
        # Add admin commands button for admins only
        if is_admin:
            buttons.append([InlineKeyboardButton('👨‍💻 Admin Commands 👨‍💻', callback_data='admin_commands')])
        
        buttons.append([InlineKeyboardButton('🔙 Back', callback_data='back')])
        
        await query.message.edit_text(
            text=Translation.HELP_TXT,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        logger.debug(f"Help message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in help callback for user {user_id}: {e}", exc_info=True)


@Client.on_callback_query(filters.regex(r'^admin_commands$'))
async def admin_commands_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"Admin commands callback from user {user_id}")
    
    # Double-check admin status
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to access admin commands!", show_alert=True)
    
    try:
        admin_buttons = [[
            InlineKeyboardButton('💎 Add Premium', callback_data='admin_add_premium'),
            InlineKeyboardButton('❌ Remove Premium', callback_data='admin_remove_premium')
        ],[
            InlineKeyboardButton('👥 Premium Users', callback_data='admin_premium_users'),
            InlineKeyboardButton('💰 Change Price', callback_data='admin_change_price')
        ],[
            InlineKeyboardButton('💬 Start Chat', callback_data='admin_start_chat'),
            InlineKeyboardButton('📊 System Info', callback_data='admin_system')
        ],[
            InlineKeyboardButton('⚡ Speed Test', callback_data='admin_speedtest'),
            InlineKeyboardButton('🔄 Restart Bot', callback_data='admin_restart')
        ],[
            InlineKeyboardButton('🗑️ Reset All Users', callback_data='admin_resetall_info'),
            InlineKeyboardButton('🔙 Back to Help', callback_data='help')
        ]]
        
        await query.message.edit_text(
            text="<b>🔧 Admin Commands Panel</b>\n\n"
                 "<b>Select an admin command:</b>\n\n"
                 "• <b>Premium Management:</b> Add/remove premium users\n"
                 "• <b>System Tools:</b> Monitor server performance\n"
                 "• <b>User Support:</b> Direct chat with users\n"
                 "• <b>Bot Control:</b> Restart and configuration\n\n"
                 "<i>These commands are only visible to admins and owners.</i>",
            reply_markup=InlineKeyboardMarkup(admin_buttons)
        )
        logger.debug(f"Admin commands panel sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in admin commands callback for user {user_id}: {e}", exc_info=True)


@Client.on_callback_query(filters.regex(r'^how_to_use'))
async def how_to_use(bot, query):
    user_id = query.from_user.id
    logger.info(f"How to use callback from user {user_id}")
    
    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id):
            subscription_status = await db.check_force_subscribe(user_id, bot)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await query.message.edit_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons)
                )
        
        await query.message.edit_text(
            text=Translation.HOW_USE_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='help')]]),
            disable_web_page_preview=True
        )
        logger.debug(f"How to use message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in how_to_use callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^back'))
async def back(bot, query):
    user_id = query.from_user.id
    logger.info(f"Back callback from user {user_id}")
    
    try:
        reply_markup = InlineKeyboardMarkup(main_buttons)
        await query.message.edit_text(
           reply_markup=reply_markup,
           text=Translation.START_TXT.format(
                    query.from_user.first_name))
        logger.debug(f"Back to main menu for user {user_id}")
    except Exception as e:
        logger.error(f"Error in back callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^about'))
async def about(bot, query):
    user_id = query.from_user.id
    logger.info(f"About callback from user {user_id}")
    
    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id):
            subscription_status = await db.check_force_subscribe(user_id, bot)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await query.message.edit_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons)
                )
        
        await query.message.edit_text(
            text=Translation.ABOUT_TXT,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='back')]]),
            disable_web_page_preview=True,
            parse_mode=enums.ParseMode.HTML,
        )
        logger.debug(f"About message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in about callback for user {user_id}: {e}", exc_info=True)



@Client.on_callback_query(filters.regex(r'^status'))
async def status(bot, query):
    user_id = query.from_user.id
    logger.info(f"Status callback from user {user_id}")
    
    try:
        # Check force subscribe for non-sudo users
        if not Config.is_sudo_user(user_id):
            subscription_status = await db.check_force_subscribe(user_id, bot)
            if not subscription_status['all_subscribed']:
                force_sub_text = (
                    "🔒 <b>Subscribe Required!</b>\n\n"
                    "To use this bot, you must join our official channels:\n\n"
                    "📜 <b>Support Group:</b> Get help and updates\n"
                    "🤖 <b>Update Channel:</b> Latest features and announcements\n\n"
                    "After joining both channels, click '✅ Check Subscription' to continue."
                )
                return await query.message.edit_text(
                    text=force_sub_text,
                    reply_markup=InlineKeyboardMarkup(force_sub_buttons)
                )
        
        users_count, bots_count = await db.total_users_bots_count()
        total_channels = await db.total_channels()
        await query.message.edit_text(
            text=Translation.STATUS_TXT.format(users_count, bots_count, temp.forwardings, total_channels),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='help')]]),
            parse_mode=enums.ParseMode.HTML,
            disable_web_page_preview=True,
        )
        logger.debug(f"Status message sent to user {user_id}")
    except Exception as e:
        logger.error(f"Error in status callback for user {user_id}: {e}", exc_info=True)


#==================Speedtest Command==================#

@Client.on_message(filters.private & filters.command(['speedtest', 'speed']))
async def speed_test_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Speedtest command from user {user_id}")
    
    # Check if user is owner or admin
    if user_id not in Config.OWNER_ID:
        return await message.reply_text("❌ This command is only available for administrators.")
    
    status_msg = await message.reply_text("🔄 <b>Running Network Speed Test...</b>\n⏳ Please wait, this may take a moment.")
    
    try:
        # Initialize speedtest
        st = speedtest.Speedtest()
        
        # Update status
        await status_msg.edit_text("🔄 <b>Finding best server...</b>\n⏳ Please wait.")
        
        # Get best server
        st.get_best_server()
        
        # Update status
        await status_msg.edit_text("🔄 <b>Testing download speed...</b>\n⏳ Please wait.")
        
        # Test download speed
        download_speed = st.download()
        
        # Update status  
        await status_msg.edit_text("🔄 <b>Testing upload speed...</b>\n⏳ Please wait.")
        
        # Test upload speed
        upload_speed = st.upload()
        
        # Get ping
        ping = st.results.ping
        
        # Get server info
        server = st.get_best_server()
        
        # Convert bytes to Mbps
        download_mbps = download_speed / 1024 / 1024
        upload_mbps = upload_speed / 1024 / 1024
        
        # Format the result
        speed_text = f"""<b>🌐 Bot Server Network Speed Test</b>

<b>📡 Server Connection Info:</b>
├ <b>ISP:</b> <code>{server.get('sponsor', 'Unknown')}</code>
├ <b>Server Location:</b> <code>{server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}</code>
├ <b>Distance:</b> <code>{server.get('d', 0):.1f} km</code>

<b>🚀 Bot Server Speed Results:</b>
├ <b>📥 Download:</b> <code>{download_mbps:.2f} Mbps</code>
├ <b>📤 Upload:</b> <code>{upload_mbps:.2f} Mbps</code>
├ <b>📶 Ping:</b> <code>{ping:.1f} ms</code>

<b>📊 Test Information:</b>
├ <b>Test Date:</b> <code>{st.results.timestamp}</code>
├ <b>Note:</b> <code>Shows bot server network, not your location</code>
└ <b>Share URL:</b> <a href="{st.results.share()}">View Results</a>"""
        
        await status_msg.edit_text(speed_text, disable_web_page_preview=True)
        logger.info(f"Speedtest completed for user {user_id}")
        
    except Exception as e:
        error_msg = f"❌ <b>Speed Test Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg)
        logger.error(f"Speedtest error for user {user_id}: {e}", exc_info=True)


#==================System Info Command==================#

@Client.on_message(filters.private & filters.command(['system', 'sys', 'sysinfo']))
async def system_info_command(client, message):
    user_id = message.from_user.id
    logger.info(f"System info command from user {user_id}")
    
    # Check if user is owner or admin
    if user_id not in Config.OWNER_ID:
        return await message.reply_text("❌ This command is only available for administrators.")
    
    status_msg = await message.reply_text("🔄 <b>Gathering system information...</b>")
    
    try:
        # Get system info
        uname = platform.uname()
        
        # Get CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_freq = psutil.cpu_freq()
        
        # Get memory info
        memory = psutil.virtual_memory()
        memory_total = memory.total / (1024**3)  # GB
        memory_used = memory.used / (1024**3)   # GB
        memory_percent = memory.percent
        
        # Get disk info
        disk = psutil.disk_usage('/')
        disk_total = disk.total / (1024**3)  # GB
        disk_used = disk.used / (1024**3)    # GB
        disk_percent = (disk.used / disk.total) * 100
        
        # Get network info
        net_io = psutil.net_io_counters()
        bytes_sent = net_io.bytes_sent / (1024**2)  # MB
        bytes_recv = net_io.bytes_recv / (1024**2)  # MB
        
        # Get boot time
        boot_time = psutil.boot_time()
        
        # Get process info
        process_count = len(psutil.pids())
        
        # Get Python info
        python_ver = python_version()
        
        # Format uptime
        import datetime
        uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
        uptime_str = str(uptime).split('.')[0]
        
        # Get load average (Unix-like systems)
        try:
            load_avg = os.getloadavg()
            load_str = f"{load_avg[0]:.2f}, {load_avg[1]:.2f}, {load_avg[2]:.2f}"
        except:
            load_str = "Not Available"
        
        system_text = f"""<b>🖥️ Bot Server System Information</b>

<b>💻 Server System Details:</b>
├ <b>OS:</b> <code>{uname.system} {uname.release}</code>
├ <b>Architecture:</b> <code>{uname.machine}</code>
├ <b>Hostname:</b> <code>{uname.node}</code>
├ <b>Kernel:</b> <code>{uname.version}</code>

<b>🔧 Server Hardware Info:</b>
├ <b>CPU Cores:</b> <code>{cpu_count} cores</code>
├ <b>CPU Usage:</b> <code>{cpu_percent}%</code>
├ <b>CPU Frequency:</b> <code>{cpu_freq.current:.0f} MHz</code> (Max: <code>{cpu_freq.max:.0f} MHz</code>)
├ <b>Load Average:</b> <code>{load_str}</code>

<b>💾 Server Memory Info:</b>
├ <b>Total RAM:</b> <code>{memory_total:.2f} GB</code>
├ <b>Used RAM:</b> <code>{memory_used:.2f} GB ({memory_percent}%)</code>
├ <b>Available RAM:</b> <code>{(memory_total - memory_used):.2f} GB</code>

<b>💿 Server Storage Info:</b>
├ <b>Total Disk:</b> <code>{disk_total:.2f} GB</code>
├ <b>Used Disk:</b> <code>{disk_used:.2f} GB ({disk_percent:.1f}%)</code>
├ <b>Free Disk:</b> <code>{(disk_total - disk_used):.2f} GB</code>

<b>🌐 Server Network Usage:</b>
├ <b>Data Sent:</b> <code>{bytes_sent:.2f} MB</code>
├ <b>Data Received:</b> <code>{bytes_recv:.2f} MB</code>

<b>⚡ Bot Runtime Info:</b>
├ <b>Python Version:</b> <code>v{python_ver}</code>
├ <b>Pyrogram Version:</b> <code>v{pyrogram_version}</code>
├ <b>Active Processes:</b> <code>{process_count}</code>
├ <b>Server Uptime:</b> <code>{uptime_str}</code>
├ <b>Note:</b> <code>Shows bot server stats, not your device</code>
└ <b>Bot Status:</b> <code>Running ✅</code>"""
        
        await status_msg.edit_text(system_text)
        logger.info(f"System info sent to user {user_id}")
        
    except Exception as e:
        error_msg = f"❌ <b>System Info Failed</b>\n\n<b>Error:</b> <code>{str(e)}</code>"
        await status_msg.edit_text(error_msg)
        logger.error(f"System info error for user {user_id}: {e}", exc_info=True)


#==================Admin Callback Functions==================#

@Client.on_callback_query(filters.regex(r'^admin_change_price$'))
async def admin_change_price_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text=f"<b>💰 Current Premium Price</b>\n\n"
                 f"<b>Current Price:</b> ₹{Config.PREMIUM_PRICE}/month\n\n"
                 f"<b>To change the price:</b>\n"
                 f"1. Update the PREMIUM_PRICE environment variable\n"
                 f"2. Restart the bot to apply changes\n\n"
                 f"<i>Note: Price changes require bot restart</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_system$'))
async def admin_system_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    # Redirect to existing system info command logic
    await system_info_command(bot, query.message)

@Client.on_callback_query(filters.regex(r'^admin_speedtest$'))
async def admin_speedtest_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    # Redirect to existing speedtest command logic
    await speed_test_command(bot, query.message)

@Client.on_callback_query(filters.regex(r'^admin_restart$'))
async def admin_restart_callback(bot, query):
    user_id = query.from_user.id
    
    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can restart the bot!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>🔄 Bot Restart</b>\n\n"
                 "<b>⚠️ Are you sure you want to restart the bot?</b>\n\n"
                 "<i>This will stop all ongoing processes!</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('✅ Yes, Restart', callback_data='confirm_restart'),
                InlineKeyboardButton('❌ Cancel', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^confirm_restart$'))
async def confirm_restart_callback(bot, query):
    user_id = query.from_user.id
    
    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can restart the bot!", show_alert=True)
    
    await query.message.edit_text("🔄 <b>Restarting bot...</b>\n\n<i>Please wait...</i>")
    await restart(bot, query.message)

@Client.on_callback_query(filters.regex(r'^admin_add_premium$'))
async def admin_add_premium_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>💎 Add Premium User</b>\n\n"
                 "<b>How to add premium:</b>\n\n"
                 "1. Use command: <code>/add_premium [user_id] [days]</code>\n"
                 "2. Example: <code>/add_premium 123456789 30</code>\n\n"
                 "<b>Default:</b> 30 days if days not specified\n\n"
                 "<i>Use this command in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_remove_premium$'))
async def admin_remove_premium_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>❌ Remove Premium User</b>\n\n"
                 "<b>How to remove premium:</b>\n\n"
                 "1. Use command: <code>/remove_premium [user_id]</code>\n"
                 "2. Example: <code>/remove_premium 123456789</code>\n\n"
                 "<i>Use this command in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_premium_users$'))
async def admin_premium_users_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>👥 Premium Users List</b>\n\n"
                 "<b>How to view premium users:</b>\n\n"
                 "1. Use command: <code>/pusers</code>\n\n"
                 "<i>Use this command in chat for detailed list</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_start_chat$'))
async def admin_start_chat_callback(bot, query):
    user_id = query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await query.answer("❌ You don't have permission to use this command!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>💬 Start Admin Chat</b>\n\n"
                 "<b>How to start chat with user:</b>\n\n"
                 "1. Use command: <code>/chat [user_id]</code>\n"
                 "2. Example: <code>/chat 123456789</code>\n\n"
                 "<b>To end chat:</b> <code>/endchat</code>\n\n"
                 "<i>Use these commands in chat, not through buttons</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_resetall_info$'))
async def admin_resetall_info_callback(bot, query):
    user_id = query.from_user.id
    
    if user_id not in Config.OWNER_ID:
        return await query.answer("❌ Only owners can reset all users!", show_alert=True)
    
    try:
        await query.message.edit_text(
            text="<b>🗑️ Reset Commands Information</b>\n\n"
                 "<b>Available Reset Commands:</b>\n\n"
                 "<b>1. Individual User Reset:</b>\n"
                 "• Command: <code>/reset</code>\n"
                 "• Resets your own data only\n"
                 "• Available to all users\n\n"
                 "<b>2. Reset All Users (Owner Only):</b>\n"
                 "• Command: <code>/resetall</code>\n"
                 "• Resets ALL users' data\n"
                 "• Only available to owners\n\n"
                 "<b>⚠️ Warning:</b> Reset commands will permanently delete:\n"
                 "• All configurations\n"
                 "• All bot connections\n"
                 "• All channel settings\n"
                 "• All custom preferences\n\n"
                 "<b>❗ These actions cannot be undone!</b>\n\n"
                 "<i>Use these commands in chat for full functionality</i>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 Back to Admin', callback_data='admin_commands')
            ]])
        )
    except Exception as e:
        await query.answer(f"Error: {str(e)}", show_alert=True)

#==================Free Trial & Contact Handlers==================#

@Client.on_callback_query(filters.regex(r'^get_free_trial$'))
async def get_free_trial_callback(bot, query):
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    logger.info(f"Free trial requested by user {user_id} ({user_name})")
    
    try:
        # Check if user can use free trial (1 per month)
        can_process, reason = await db.can_user_process(user_id)
        
        if not can_process and reason == "monthly_limit_reached":
            await query.answer(
                "❌ You have already used your free trial this month!\n"
                "💎 Upgrade to Premium for unlimited access.",
                show_alert=True
            )
            return
        
        if await db.is_premium_user(user_id):
            await query.answer(
                "✅ You already have Premium access!\n"
                "No need for free trial - you have unlimited processes.",
                show_alert=True
            )
            return
        
        # Grant the free trial (increment usage)
        await db.increment_usage(user_id)
        
        # Send notification to admins
        try:
            notify = NotificationManager(bot)
            await notify.notify_free_trial_activity(
                user_id=user_id, 
                action="activated free trial", 
                remaining_usage=0  # After using 1 free trial, 0 remaining
            )
        except Exception as notify_err:
            logger.error(f"Failed to send free trial notification: {notify_err}")
        
        # Send confirmation message to user
        await query.message.edit_text(
            text="<b>🎉 Free Trial Activated!</b>\n\n"
                 "<b>✅ You have received 1 free forwarding process for this month!</b>\n\n"
                 "<b>📋 What you can do:</b>\n"
                 "• Use /forward to start forwarding messages\n"
                 "• Access all basic features\n"
                 "• Process one forwarding job\n\n"
                 "<b>🔒 Channel Lock:</b> Your channel will be locked during processing to ensure quality.\n\n"
                 "<b>💎 Want unlimited access?</b>\n"
                 "Upgrade to Premium for ₹200/month:\n"
                 "• Unlimited forwarding processes\n"
                 "• Priority support\n"
                 "• No monthly restrictions\n\n"
                 "<b>📊 Your current status:</b> 1/1 free processes used this month\n"
                 "<b>🗓️ Resets:</b> 1st of next month",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🚀 Start Forwarding', callback_data='settings#main')],
                [InlineKeyboardButton('💎 Upgrade to Premium', callback_data='premium_info')],
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )
        
        logger.info(f"Free trial granted to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in free trial callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^contact_admin$'))
async def contact_admin_callback(bot, query):
    user_id = query.from_user.id
    user_name = query.from_user.first_name
    user_username = f"@{query.from_user.username}" if query.from_user.username else ""
    logger.info(f"Contact admin callback from user {user_id} ({user_name})")
    
    try:
        # Check if user already has a pending chat request
        existing_request = await db.get_pending_chat_request(user_id)
        if existing_request:
            await query.answer(
                "⏳ You already have a pending chat request.\n"
                "Please wait for admin approval.",
                show_alert=True
            )
            return
        
        # Check if user is already in an active chat
        active_chat = await db.get_active_chat_for_user(user_id)
        if active_chat:
            await query.answer(
                "💬 You already have an active chat session with admin!\n"
                "Just send your message and it will be forwarded.",
                show_alert=True
            )
            return
            
        # Create chat request
        request_id = await db.create_chat_request(user_id)
        
        # Notification for contact request
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_contact_request(
                user_id=user_id,
                request_type="general support",
                status="submitted"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send contact request notification: {notif_err}")
        
        await query.message.edit_text(
            text="<b>💬 Contact Request Submitted!</b>\n\n"
                 "<b>Your request to contact admin has been submitted.</b>\n"
                 "<b>⏳ Please wait for admin approval.</b>\n\n"
                 f"<b>Request ID:</b> <code>{request_id}</code>\n"
                 "<b>💬 You will be notified once an admin accepts your request.</b>",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )
        
        # Send notification to all sudo users (admin + owner) with accept/deny options
        sudo_users = Config.OWNER_ID + Config.ADMIN_ID
        
        for sudo_id in sudo_users:
            try:
                buttons = [
                    [
                        InlineKeyboardButton("✅ Accept Chat", callback_data=f"accept_chat_{request_id}"),
                        InlineKeyboardButton("❌ Deny", callback_data=f"deny_chat_{request_id}")
                    ]
                ]
                
                await bot.send_message(
                    sudo_id,
                    f"<b>💬 New Contact Request</b>\n\n"
                    f"<b>User:</b> {user_name} {user_username}\n"
                    f"<b>User ID:</b> <code>{user_id}</code>\n"
                    f"<b>Request ID:</b> <code>{request_id}</code>\n"
                    f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    f"<b>Choose an action:</b>",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as send_err:
                logger.error(f"Failed to send contact request to admin {sudo_id}: {send_err}")
        
        logger.info(f"Contact request created: {request_id} for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error in contact admin callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

@Client.on_callback_query(filters.regex(r'^premium_info$'))
async def premium_info_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"Premium info callback from user {user_id}")
    
    try:
        # Notification for plan exploration
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_plan_exploration(
                user_id=user_id, 
                plan_type="Premium Plan Information", 
                action="viewed premium info", 
                source="main menu button"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send plan exploration notification: {notif_err}")
        
        await query.message.edit_text(
            text=Translation.PLAN_INFO_MSG,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📊 Check My Plan', callback_data='my_plan')],
                [InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')],
                [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
            ])
        )
    except Exception as e:
        logger.error(f"Error in premium info callback for user {user_id}: {e}", exc_info=True)

@Client.on_callback_query(filters.regex(r'^my_plan$'))
async def my_plan_callback(bot, query):
    user_id = query.from_user.id
    logger.info(f"My plan callback from user {user_id}")
    
    try:
        # Notification for plan exploration
        try:
            from utils.notifications import NotificationManager
            notification_manager = NotificationManager(bot)
            await notification_manager.notify_plan_exploration(
                user_id=user_id, 
                plan_type="Current Plan Status", 
                action="checked current plan", 
                source="premium info menu"
            )
        except Exception as notif_err:
            logger.error(f"Failed to send plan exploration notification: {notif_err}")
        
        # Check user's plan status
        premium_info = await db.get_premium_user_details(user_id)
        daily_usage = await db.get_daily_usage(user_id)
        usage_count = daily_usage.get('processes', 0)
        
        if premium_info:
            # User has active premium plan
            plan_type = premium_info.get('plan_type', 'unknown')
            expires_at = premium_info.get('expires_at', 'Unknown')
            # Calculate days remaining
            from datetime import datetime
            expires_at_obj = premium_info.get('expires_at', datetime.utcnow())
            if isinstance(expires_at_obj, datetime):
                days_remaining = max(0, (expires_at_obj - datetime.utcnow()).days)
            else:
                days_remaining = 0
            
            if plan_type.lower() == 'plus':
                plan_text = f"""<b>✨ Your Plus Plan</b>

<b>✅ Status:</b> Plus Plan Active
<b>📅 Plan Type:</b> Plus (15-30 days)
<b>⏰ Expires:</b> {expires_at}
<b>⏱️ Days Left:</b> {days_remaining} days
<b>📊 This Month:</b> {usage_count} processes used

<b>🎯 Plus Plan Features:</b>
• ♾️ Unlimited forwarding processes
• ⚡ Standard processing speed
• 🔄 Basic filtering options
• 📱 Standard support

<b>💡 Upgrade to Pro for:</b>
• 🔥 FTM Mode with source tracking
• 🛡️ Priority support
• 🚀 Enhanced performance"""
            elif plan_type.lower() == 'pro':
                plan_text = f"""<b>🔥 Your Pro Plan</b>

<b>✅ Status:</b> Pro Plan Active
<b>📅 Plan Type:</b> Pro (15-30 days)
<b>⏰ Expires:</b> {expires_at}
<b>⏱️ Days Left:</b> {days_remaining} days
<b>📊 This Month:</b> {usage_count} processes used

<b>🚀 Pro Plan Features:</b>
• ♾️ Unlimited forwarding processes
• 🔥 FTM Mode with source tracking
• ⚡ Priority processing speed
• 🛠️ Advanced filtering options
• 🛡️ Priority customer support
• 📈 Enhanced performance"""
            else:
                plan_text = f"""<b>💎 Your Premium Plan</b>

<b>✅ Status:</b> Premium Active
<b>📅 Plan Type:</b> {plan_type}
<b>⏰ Expires:</b> {expires_at}
<b>🔄 Usage:</b> Unlimited processes
<b>📊 This Month:</b> {usage_count} processes used

<b>🎉 You have access to premium features!</b>"""
        else:
            # User is on free plan
            plan_text = f"""<b>🆓 Your Free Plan</b>

<b>📊 Status:</b> Free User
<b>🔄 Monthly Usage:</b> {usage_count}/1 processes
<b>🗓️ Usage Resets:</b> 1st of each month
<b>📈 Remaining:</b> {max(0, 1 - usage_count)} free processes

<b>💡 Current Features:</b>
• 1️⃣ One free process per month
• 🔄 Basic forwarding functionality
• 📋 Standard filtering options

<b>🚀 Available Plans:</b>
<b>✨ Plus Plan:</b> ₹199/15d, ₹299/30d
• Unlimited forwarding

<b>🔥 Pro Plan:</b> ₹299/15d, ₹549/30d  
• Unlimited forwarding + FTM Mode + Priority support"""
        
        buttons = []
        if not premium_info:
            # Free user - show upgrade options
            buttons.append([InlineKeyboardButton('💎 Upgrade Now', callback_data='premium#main')])
        elif premium_info.get('plan_type', '').lower() == 'plus':
            # Plus user - show Pro upgrade option
            buttons.append([InlineKeyboardButton('🔥 Upgrade to Pro', callback_data='premium#main')])
        
        buttons.extend([
            [InlineKeyboardButton('💬 Contact Admin', callback_data='contact_admin')],
            [InlineKeyboardButton('🔙 Back to Menu', callback_data='back')]
        ])
        
        await query.message.edit_text(
            text=plan_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        logger.error(f"Error in my plan callback for user {user_id}: {e}", exc_info=True)
        await query.answer("❌ An error occurred. Please try again.", show_alert=True)

