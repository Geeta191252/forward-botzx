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
        InlineKeyboardButton('🎁 Get Free Trial', callback_data='get_free_trial'),
        InlineKeyboardButton('📊 My Plan', callback_data='my_plan')
        ],[
        InlineKeyboardButton('💎 Premium Plans', callback_data='premium_plans'),
        InlineKeyboardButton('🙋‍♂️ ʜᴇʟᴘ', callback_data='help')
        ],[
        InlineKeyboardButton('💁‍♂️ ᴀʙᴏᴜᴛ ', callback_data='about'),
        InlineKeyboardButton('⚙️ sᴇᴛᴛɪɴɢs ⚙️', callback_data='settings#main')
        ],[
        InlineKeyboardButton('📞 Contact Admin', callback_data='contact_admin')
        ]]

# Dynamic force subscribe buttons based on config
def get_force_sub_buttons():
    """Generate force subscribe buttons based on configured channels"""
    buttons = []
    
    # Add channel buttons in rows of 2
    for i in range(0, len(Config.FORCE_SUBSCRIBE_CHANNELS), 2):
        row = []
        for j in range(2):
            if i + j < len(Config.FORCE_SUBSCRIBE_CHANNELS):
                channel = Config.FORCE_SUBSCRIBE_CHANNELS[i + j]
                row.append(InlineKeyboardButton(
                    channel['button_text'], 
                    url=channel['url']
                ))
        buttons.append(row)
    
    # Add check subscription button
    buttons.append([InlineKeyboardButton('✅ Check Subscription', callback_data='check_subscription')])
    return buttons

force_sub_buttons = get_force_sub_buttons()


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
            missing_channels = subscription_status.get('missing_channels', [])
            if len(missing_channels) > 3:
                missing_text = f"{', '.join(missing_channels[:3])} and {len(missing_channels) - 3} more"
            else:
                missing_text = ', '.join(missing_channels)
                
            await callback_query.answer(f"❌ Please join: {missing_text}", show_alert=True)
            
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
            "• 1 forwarding process per month\n"
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
                 "<b>Premium Management Commands:</b>\n"
                 "• <code>/add_premium [user_id] [plan_type] [days]</code>\n"
                 "  Plan types: <b>plus</b> or <b>pro</b>\n"
                 "  Example: <code>/add_premium 123456789 pro 30</code>\n"
                 "• <code>/remove_premium [user_id]</code>\n\n"
                 "<b>User Management:</b>\n"
                 "• <code>/users</code> - List all registered users\n\n"
                 "<b>System Tools:</b> Monitor server performance\n"
                 "<b>User Support:</b> Direct chat with users\n"
                 "<b>Bot Control:</b> Restart and configuration\n\n"
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
        
        # Grant the free trial (add 1 extra process - total 2 for this month)
        trial_granted = await db.add_trial_processes(user_id, 1)
        
        if not trial_granted:
            await query.answer(
                "❌ You have already claimed your free trial this month!\n"
                "💎 Upgrade to Premium for unlimited access.",
                show_alert=True
            )
            return
        
        # Send notification to admins
        try:
            notify = NotificationManager(bot)
            await notify.notify_free_trial_activity(
                user_id=user_id, 
                action="activated free trial", 
                remaining_usage=1  # User now has 2 total processes (1 base + 1 trial)
            )
        except Exception as notify_err:
            logger.error(f"Failed to send free trial notification: {notify_err}")
        
        # Send confirmation message to user
        await query.message.edit_text(
            text="<b>🎉 Free Trial Activated!</b>\n\n"
                 "<b>✅ You have received +1 additional process for this month!</b>\n\n"
                 "<b>📋 Your monthly allowance:</b>\n"
                 "• Base free plan: 1 process\n"
                 "• Trial bonus: +1 process\n"
                 "• <b>Total available: 2 processes</b>\n\n"
                 "<b>What you can do:</b>\n"
                 "• Use /forward to start forwarding messages\n"
                 "• Process two forwarding jobs this month\n\n"
                 "<b>💎 Want unlimited access?</b>\n"
                 "Upgrade to Premium:\n"
                 "• <b>Plus Plan:</b> ₹199/15d, ₹299/30d - Unlimited forwarding\n"
                 "• <b>Pro Plan:</b> ₹299/15d, ₹549/30d - Unlimited + FTM Mode + Priority support\n\n"
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
            # User is on free plan - check if trial was used
            trial_status = await db.get_trial_status(user_id)
            total_processes = 1  # Base free process
            trial_text = ""
            if trial_status and trial_status.get('used', False):
                total_processes = 2  # Base + trial
                trial_text = " (1 base + 1 trial)"
                
            plan_text = f"""<b>🆓 Your Free Plan</b>

<b>📊 Status:</b> Free User
<b>🔄 Monthly Usage:</b> {usage_count}/{total_processes} processes
<b>🗓️ Usage Resets:</b> 1st of each month
<b>📈 Remaining:</b> {max(0, total_processes - usage_count)} free processes

<b>💡 Current Features:</b>
• {total_processes}️⃣ {total_processes} free process{'es' if total_processes > 1 else ''} per month{trial_text}
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

# /info command for users to get all their information
@Client.on_message(filters.private & filters.command(['info']))
async def info_command(client, message):
    user = message.from_user
    user_id = user.id
    logger.info(f"Info command from user {user_id}")
    
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
        
        # Get user information
        premium_info = await db.get_premium_user_details(user_id)
        daily_usage = await db.get_daily_usage(user_id)
        monthly_usage = await db.get_monthly_usage(user_id)
        user_data = await db.get_user(user_id)
        
        # Format join date
        from datetime import datetime
        join_date = user_data.get('joined_date', datetime.utcnow()) if user_data else datetime.utcnow()
        if isinstance(join_date, datetime):
            join_date_str = join_date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            join_date_str = "Unknown"
            
        # Build user info text
        info_text = f"<b>👤 Your Account Information</b>\n\n"
        info_text += f"<b>📋 Basic Details:</b>\n"
        info_text += f"• <b>Name:</b> {user.first_name}"
        if user.last_name:
            info_text += f" {user.last_name}"
        info_text += f"\n• <b>Username:</b> @{user.username}" if user.username else "\n• <b>Username:</b> Not set"
        info_text += f"\n• <b>User ID:</b> <code>{user_id}</code>"
        info_text += f"\n• <b>Joined:</b> {join_date_str}\n\n"
        
        # Subscription status
        if premium_info:
            plan_type = premium_info.get('plan_type', 'unknown').upper()
            expires_at = premium_info.get('expires_at', 'Unknown')
            if isinstance(expires_at, datetime):
                expires_at_str = expires_at.strftime('%Y-%m-%d %H:%M:%S')
                days_remaining = max(0, (expires_at - datetime.utcnow()).days)
            else:
                expires_at_str = str(expires_at)
                days_remaining = 0
                
            info_text += f"<b>💎 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> {plan_type} Plan ✅\n"
            info_text += f"• <b>Expires:</b> {expires_at_str}\n"
            info_text += f"• <b>Days Left:</b> {days_remaining} days\n\n"
        else:
            info_text += f"<b>🆓 Subscription Status:</b>\n"
            info_text += f"• <b>Plan:</b> Free User\n"
            info_text += f"• <b>Limit:</b> 1 process per month\n\n"
        
        # Usage statistics
        info_text += f"<b>📊 Usage Statistics:</b>\n"
        info_text += f"• <b>This Month:</b> {monthly_usage.get('processes', 0)} processes\n"
        info_text += f"• <b>Today:</b> {daily_usage.get('processes', 0)} processes\n"
        
        # Get forwarding limit
        limit = await db.get_forwarding_limit(user_id)
        if limit == -1:
            info_text += f"• <b>Limit:</b> Unlimited processes ♾️\n\n"
        else:
            remaining = max(0, limit - monthly_usage.get('processes', 0))
            info_text += f"• <b>Monthly Limit:</b> {limit} processes\n"
            info_text += f"• <b>Remaining:</b> {remaining} processes\n\n"
        
        info_text += f"<b>Use /myplan for subscription details and upgrade options.</b>"
        
        await message.reply_text(
            text=info_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('💎 My Plan', callback_data='my_plan')],
                [InlineKeyboardButton('⚙️ Settings', callback_data='settings#main')],
                [InlineKeyboardButton('🔙 Main Menu', callback_data='back')]
            ]),
            quote=True
        )
        
    except Exception as e:
        logger.error(f"Error in info command for user {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred while fetching your information. Please try again.")

# Helper function to generate users list text and buttons
async def generate_users_list(page=1):
    """Generate users list with pagination"""
    # Get all users from database
    all_users = await db.get_all_users()
    
    if not all_users:
        return "📋 No registered users found.", []
    
    # Pagination settings
    users_per_page = 10
    total_pages = (len(all_users) + users_per_page - 1) // users_per_page
    
    # Ensure page is within bounds
    page = max(1, min(page, total_pages))
    
    start_idx = (page - 1) * users_per_page
    end_idx = min(start_idx + users_per_page, len(all_users))
    
    # Count statistics
    premium_count = plus_count = pro_count = free_count = active_today = 0
    
    from datetime import datetime, timedelta
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Enhanced header with statistics
    users_text = f"<b>👥 All Registered Users</b>\n\n"
    users_text += f"<b>📄 Page {page} of {total_pages}</b>\n"
    users_text += f"<b>📊 Total Users: {len(all_users)}</b>\n"
    users_text += f"{'='*40}\n\n"
    
    # Process users for current page
    for i, user_info in enumerate(all_users[start_idx:end_idx], start_idx + 1):
        user_id_info = user_info.get('id', 'Unknown')
        user_name = user_info.get('name', 'Unknown')
        joined_date = user_info.get('joined_date', 'Unknown')
        
        # Check if user has premium
        premium_info = await db.get_premium_user_details(user_id_info)
        if premium_info:
            plan_type = premium_info.get('plan_type', 'premium').upper()
            if plan_type == 'PRO':
                status = "💎 PRO"
                pro_count += 1
            elif plan_type == 'PLUS':
                status = "💎 PLUS"  
                plus_count += 1
            else:
                status = f"💎 {plan_type}"
                premium_count += 1
            
            # Check expiry
            expires_at = premium_info.get('expires_at')
            if expires_at and isinstance(expires_at, datetime):
                days_left = (expires_at - datetime.utcnow()).days
                if days_left <= 0:
                    status += " (EXPIRED)"
                elif days_left <= 3:
                    status += f" ({days_left}d)"
        else:
            status = "🆓 FREE"
            free_count += 1
        
        # Format join date and check if active today
        if isinstance(joined_date, datetime):
            join_str = joined_date.strftime('%Y-%m-%d')
            if joined_date >= today:
                active_today += 1
        else:
            join_str = "Unknown"
        
        # Truncate long names for better display
        display_name = user_name[:20] + "..." if len(user_name) > 20 else user_name
        
        users_text += f"<b>{i}.</b> <b>{display_name}</b>\n"
        users_text += f"    <b>ID:</b> <code>{user_id_info}</code>\n"
        users_text += f"    <b>Status:</b> {status}\n"
        users_text += f"    <b>Joined:</b> {join_str}\n\n"
    
    # Summary statistics
    users_text += f"{'='*40}\n"
    users_text += f"<b>📊 Summary:</b>\n"
    users_text += f"• <b>Premium Users:</b> {pro_count + plus_count}\n"
    users_text += f"• <b>Free Users:</b> {free_count}\n" 
    users_text += f"• <b>Total:</b> {len(all_users)} users\n\n"
    
    # Generate pagination buttons
    buttons = []
    nav_row = []
    
    # First and Previous buttons
    if page > 1:
        if page > 2:
            nav_row.append(InlineKeyboardButton('⏪ First', callback_data='users_list_1'))
        nav_row.append(InlineKeyboardButton('◀️ Previous', callback_data=f'users_list_{page-1}'))
    
    # Current page indicator
    nav_row.append(InlineKeyboardButton(f'• {page}/{total_pages} •', callback_data='users_current'))
    
    # Next and Last buttons  
    if page < total_pages:
        nav_row.append(InlineKeyboardButton('Next ▶️', callback_data=f'users_list_{page+1}'))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton('Last ⏩', callback_data=f'users_list_{total_pages}'))
    
    if nav_row:
        buttons.append(nav_row)
    
    # Quick jump buttons (show nearby pages)
    if total_pages > 5:
        jump_row = []
        start_jump = max(1, page - 2)
        end_jump = min(total_pages, page + 2)
        
        for p in range(start_jump, end_jump + 1):
            if p != page:
                jump_row.append(InlineKeyboardButton(str(p), callback_data=f'users_list_{p}'))
        
        if jump_row:
            buttons.append(jump_row)
    
    # Action buttons
    buttons.extend([
        [
            InlineKeyboardButton('🔄 Refresh', callback_data=f'users_list_{page}'),
            InlineKeyboardButton('💎 Premium Only', callback_data='admin_premium_users')
        ],
        [
            InlineKeyboardButton('📈 User Stats', callback_data='admin_user_stats'),
            InlineKeyboardButton('🆓 Free Only', callback_data='admin_free_users')
        ],
        [
            InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')
        ]
    ])
    
    return users_text, buttons

# /users command for admins to get list of all registered users
@Client.on_message(filters.private & filters.command(['users']))
async def users_command(client, message):
    user_id = message.from_user.id
    logger.info(f"Users command from admin {user_id}")
    
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    try:
        # Generate users list for page 1
        users_text, buttons = await generate_users_list(1)
        
        await message.reply_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(buttons),
            quote=True
        )
        
    except Exception as e:
        logger.error(f"Error in users command for admin {user_id}: {e}", exc_info=True)
        await message.reply_text("❌ An error occurred while fetching users list. Please try again.")

# Enhanced callback handlers for user list pagination
@Client.on_callback_query(filters.regex(r'^users_list_(\d+)$'))
async def users_list_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    try:
        page = int(callback_query.data.split('_')[2])
        
        # Generate users list for the requested page
        users_text, buttons = await generate_users_list(page)
        
        await callback_query.message.edit_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
        await callback_query.answer(f"📄 Page {page}")
        
    except Exception as e:
        logger.error(f"Error in users list callback: {e}", exc_info=True)
        await callback_query.answer("❌ Error loading page!", show_alert=True)

@Client.on_callback_query(filters.regex(r'^users_current$'))
async def users_current_callback(client, callback_query):
    """Handle current page indicator click"""
    await callback_query.answer("📍 Current page", show_alert=False)

@Client.on_callback_query(filters.regex(r'^admin_free_users$'))
async def admin_free_users_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    try:
        # Get all users and filter free users
        all_users = await db.get_all_users()
        free_users = []
        
        for user_info in all_users:
            user_id_info = user_info.get('id')
            if not await db.is_premium_user(user_id_info):
                free_users.append(user_info)
        
        if not free_users:
            return await callback_query.message.edit_text(
                "<b>🆓 Free Users</b>\n\n<i>No free users found!</i>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('🔙 Back', callback_data='admin_commands')]])
            )
        
        users_text = f"<b>🆓 Free Users Only</b>\n"
        users_text += f"<b>Total Free Users:</b> {len(free_users)}\n"
        users_text += f"{'='*30}\n\n"
        
        for i, user_info in enumerate(free_users[:20], 1):  # Show first 20 free users
            user_id_info = user_info.get('id', 'Unknown')
            user_name = user_info.get('name', 'Unknown')
            joined_date = user_info.get('joined_date', 'Unknown')
            
            # Format join date
            if isinstance(joined_date, datetime):
                join_str = joined_date.strftime('%d %b %Y')
            else:
                join_str = "Unknown"
            
            # Check usage
            usage = await db.get_monthly_usage(user_id_info)
            usage_count = usage.get('processes', 0)
            
            display_name = user_name[:20] + "..." if len(user_name) > 20 else user_name
            
            users_text += f"<b>{i:2d}.</b> {display_name}\n"
            users_text += f"     <b>ID:</b> <code>{user_id_info}</code>\n"
            users_text += f"     <b>Usage:</b> {usage_count}/2 processes\n"
            users_text += f"     <b>Joined:</b> {join_str}\n\n"
        
        if len(free_users) > 20:
            users_text += f"<i>... and {len(free_users) - 20} more free users</i>\n"
        
        buttons = [
            [InlineKeyboardButton('👥 All Users', callback_data='users_page_1')],
            [InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')]
        ]
        
        await callback_query.message.edit_text(
            text=users_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^admin_user_stats$'))
async def admin_user_stats_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    try:
        # Get comprehensive user statistics
        all_users = await db.get_all_users()
        premium_users = await db.get_all_premium_users()
        
        from datetime import datetime, timedelta
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Count statistics
        total_users = len(all_users)
        total_premium = len(premium_users)
        total_free = total_users - total_premium
        
        # Count by plan type
        pro_users = len([p for p in premium_users if p.get('plan_type') == 'pro'])
        plus_users = len([p for p in premium_users if p.get('plan_type') == 'plus'])
        
        # Count by join date
        new_today = len([u for u in all_users if u.get('joined_date', datetime.min) >= today])
        new_week = len([u for u in all_users if u.get('joined_date', datetime.min) >= week_ago])
        new_month = len([u for u in all_users if u.get('joined_date', datetime.min) >= month_ago])
        
        # Revenue calculation
        estimated_revenue = (pro_users * 549) + (plus_users * 299)
        
        stats_text = f"""<b>📊 Comprehensive User Statistics</b>

<b>👥 User Base Overview:</b>
├ <b>Total Users:</b> {total_users:,}
├ <b>Premium Users:</b> {total_premium:,} ({total_premium/total_users*100:.1f}%)
└ <b>Free Users:</b> {total_free:,} ({total_free/total_users*100:.1f}%)

<b>💎 Premium Breakdown:</b>
├ <b>🔥 Pro Users:</b> {pro_users:,}
├ <b>✨ Plus Users:</b> {plus_users:,}
└ <b>💰 Est. Revenue:</b> ₹{estimated_revenue:,}

<b>📈 Growth Statistics:</b>
├ <b>New Today:</b> {new_today:,}
├ <b>New This Week:</b> {new_week:,}
└ <b>New This Month:</b> {new_month:,}

<b>📊 Conversion Rate:</b>
├ <b>Free to Premium:</b> {total_premium/total_users*100:.1f}%
├ <b>Pro Preference:</b> {pro_users/(pro_users+plus_users)*100 if (pro_users+plus_users) > 0 else 0:.1f}%
└ <b>Daily Avg Signups:</b> {new_month/30:.1f}

<b>💡 Business Insights:</b>
• Premium conversion rate is {'excellent' if total_premium/total_users > 0.15 else 'good' if total_premium/total_users > 0.1 else 'needs improvement'}
• {'Strong' if new_today > 5 else 'Moderate' if new_today > 2 else 'Low'} user acquisition today
• Monthly revenue trend: ₹{estimated_revenue:,}"""
        
        buttons = [
            [
                InlineKeyboardButton('👥 All Users', callback_data='users_page_1'),
                InlineKeyboardButton('💎 Premium Only', callback_data='admin_premium_users')
            ],
            [
                InlineKeyboardButton('🔄 Refresh Stats', callback_data='admin_user_stats'),
                InlineKeyboardButton('🔙 Admin Menu', callback_data='admin_commands')
            ]
        ]
        
        await callback_query.message.edit_text(
            text=stats_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

