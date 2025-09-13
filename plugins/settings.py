import asyncio 
from database import db
from config import Config
from translation import Translation
from pyrogram import Client, filters
from .test import get_configs, update_configs, CLIENT, parse_buttons
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

CLIENT = CLIENT()

# Force subscribe buttons
force_sub_buttons = [[
        InlineKeyboardButton('📜 Join Support Group', url=Config.SUPPORT_GROUP),
        InlineKeyboardButton('🤖 Join Update Channel', url=Config.UPDATE_CHANNEL)
        ],[
        InlineKeyboardButton('✅ Check Subscription', callback_data='check_subscription')
        ]]

@Client.on_message(filters.command('settings'))
async def settings(client, message):
   user_id = message.from_user.id
   
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
           await message.delete()
           return await message.reply_text(
               text=force_sub_text,
               reply_markup=InlineKeyboardMarkup(force_sub_buttons)
           )
   
   await message.delete()
   await message.reply_text(
     "<b>change your settings as your wish</b>",
     reply_markup=main_buttons()
     )
    
@Client.on_callback_query(filters.regex(r'^settings'))
async def settings_query(bot, query):
  user_id = query.from_user.id
  
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
  
  i, type = query.data.split("#")
  buttons = [[InlineKeyboardButton('↩ Back', callback_data="settings#main")]]
  
  if type=="main":
     await query.message.edit_text(
       "<b>change your settings as your wish</b>",
       reply_markup=main_buttons())
       
  elif type=="bots":
     buttons = [] 
     _bot = await db.get_bot(user_id)
     if _bot is not None:
        buttons.append([InlineKeyboardButton(_bot['name'],
                         callback_data=f"settings#editbot")])
     else:
        buttons.append([InlineKeyboardButton('✚ Add bot ✚', 
                         callback_data="settings#addbot")])
        buttons.append([InlineKeyboardButton('✚ Add User bot (Session) ✚', 
                         callback_data="settings#adduserbot")])
        buttons.append([InlineKeyboardButton('✚ Add User bot (Phone) ✚', 
                         callback_data="settings#addphonebot")])
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
       "<b><u>My Bots</b></u>\n\n<b>You can manage your bots in here</b>",
       reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbot":
     await query.message.delete()
     bot = await CLIENT.add_bot(bot, query)
     if bot != True: return
     
     # Send notification for bot addition
     try:
         from utils.notifications import NotificationManager
         notify = NotificationManager(query.message._client)
         await notify.notify_user_action(user_id, "Added Bot Token", "Bot token successfully added to database", "Bot Management")
     except Exception as notify_err:
         print(f"Failed to send bot addition notification: {notify_err}")
     
     await query.message.reply_text(
        "<b>bot token successfully added to db</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="adduserbot":
     await query.message.delete()
     user = await CLIENT.add_session(bot, query)
     if user != True: return
     
     # Send notification for userbot session addition
     try:
         from utils.notifications import NotificationManager
         notify = NotificationManager(query.message._client)
         await notify.notify_user_action(user_id, "Added Userbot Session", "Userbot session successfully added to database", "Bot Management")
     except Exception as notify_err:
         print(f"Failed to send userbot session addition notification: {notify_err}")
     
     await query.message.reply_text(
        "<b>session successfully added to db</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addphonebot":
     await query.message.delete()
     user = await CLIENT.add_phone_login(bot, query)
     if user != True: return
     
     # Send notification for phone bot addition
     try:
         from utils.notifications import NotificationManager
         notify = NotificationManager(query.message._client)
         await notify.notify_user_action(user_id, "Added Phone Bot", "Userbot successfully logged in via phone and added to database", "Bot Management")
     except Exception as notify_err:
         print(f"Failed to send phone bot addition notification: {notify_err}")
     
     await query.message.reply_text(
        "<b>user bot successfully logged in and added to db</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="channels":
     buttons = []
     channels = await db.get_user_channels(user_id)
     for channel in channels:
        buttons.append([InlineKeyboardButton(f"{channel['title']}",
                         callback_data=f"settings#editchannels_{channel['chat_id']}")])
     buttons.append([InlineKeyboardButton('✚ Add Channel ✚', 
                      callback_data="settings#addchannel")])
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text( 
       "<b><u>My Channels</b></u>\n\n<b>you can manage your target chats in here</b>",
       reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="addchannel":  
     await query.message.delete()
     try:
         text = await bot.send_message(user_id, "<b>❪ SET TARGET CHAT ❫\n\nForward a message from Your target chat\n/cancel - cancel this process</b>")
         chat_ids = await bot.listen(chat_id=user_id, timeout=300)
         if chat_ids.text=="/cancel":
            await chat_ids.delete()
            return await text.edit_text(
                  "<b>process canceled</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
         elif not chat_ids.forward_date:
            await chat_ids.delete()
            return await text.edit_text("**This is not a forward message**")
         else:
            chat_id = chat_ids.forward_from_chat.id
            title = chat_ids.forward_from_chat.title
            username = chat_ids.forward_from_chat.username
            username = "@" + username if username else "private"
         chat = await db.add_channel(user_id, chat_id, title, username)
         await chat_ids.delete()
         
         # Send notification for channel addition
         if chat:  # Only if channel was actually added (not already existing)
             try:
                 from utils.notifications import NotificationManager
                 notify = NotificationManager(bot)
                 await notify.notify_user_action(user_id, "Added Channel", f"Channel: {title} (ID: {chat_id})")
             except Exception as notify_err:
                 print(f"Failed to send channel addition notification: {notify_err}")
         
         await text.edit_text(
            "<b>Successfully updated</b>" if chat else "<b>This channel already added</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await text.edit_text('Process has been automatically cancelled', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="editbot": 
     bot = await db.get_bot(user_id)
     TEXT = Translation.BOT_DETAILS if bot['is_bot'] else Translation.USER_DETAILS
     buttons = [[InlineKeyboardButton('❌ Remove ❌', callback_data=f"settings#removebot")
               ],
               [InlineKeyboardButton('↩ Back', callback_data="settings#bots")]]
     await query.message.edit_text(
        TEXT.format(bot['name'], bot['id'], bot['username']),
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type=="removebot":
     # Get bot details before removal for notification
     bot_details = await db.get_bot(user_id)
     await db.remove_bot(user_id)
     
     # Send notification for bot removal
     try:
         from utils.notifications import NotificationManager
         notify = NotificationManager(query.message._client)
         bot_info = f"Bot: {bot_details['name']}" if bot_details else "Bot removed"
         await notify.notify_user_action(user_id, "Removed Bot", bot_info)
     except Exception as notify_err:
         print(f"Failed to send bot removal notification: {notify_err}")
     
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type.startswith("editchannels"): 
     chat_id = type.split('_')[1]
     chat = await db.get_channel_details(user_id, chat_id)
     buttons = [[InlineKeyboardButton('❌ Remove ❌', callback_data=f"settings#removechannel_{chat_id}")
               ],
               [InlineKeyboardButton('↩ Back', callback_data="settings#channels")]]
     await query.message.edit_text(
        f"<b><u>📄 CHANNEL DETAILS</b></u>\n\n<b>- TITLE:</b> <code>{chat['title']}</code>\n<b>- CHANNEL ID: </b> <code>{chat['chat_id']}</code>\n<b>- USERNAME:</b> {chat['username']}",
        reply_markup=InlineKeyboardMarkup(buttons))
                                             
  elif type.startswith("removechannel"):
     chat_id = type.split('_')[1]
     # Get channel details before removal for notification
     channel_details = await db.get_channel_details(user_id, chat_id)
     await db.remove_channel(user_id, chat_id)
     
     # Send notification for channel removal
     try:
         from utils.notifications import NotificationManager
         notify = NotificationManager(query.message._client)
         channel_info = f"Channel: {channel_details['title']} (ID: {chat_id})" if channel_details else f"Channel removed (ID: {chat_id})"
         await notify.notify_user_action(user_id, "Removed Channel", channel_info)
     except Exception as notify_err:
         print(f"Failed to send channel removal notification: {notify_err}")
     
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                               
  elif type=="caption":
     buttons = []
     data = await get_configs(user_id)
     caption = data['caption']
     if caption is None:
        buttons.append([InlineKeyboardButton('✚ Add Caption ✚', 
                      callback_data="settings#addcaption")])
     else:
        buttons.append([InlineKeyboardButton('See Caption', 
                      callback_data="settings#seecaption")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Delete Caption', 
                      callback_data="settings#deletecaption"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM CAPTION</b></u>\n\n<b>You can set a custom caption to videos and documents. Normaly use its default caption</b>\n\n<b><u>AVAILABLE FILLINGS:</b></u>\n- <code>{filename}</code> : Filename\n- <code>{size}</code> : File size\n- <code>{caption}</code> : default caption",
        reply_markup=InlineKeyboardMarkup(buttons))
                               
  elif type=="seecaption":   
     data = await get_configs(user_id)
     buttons = [[InlineKeyboardButton('🖋️ Edit Caption', 
                  callback_data="settings#addcaption")
               ],[
               InlineKeyboardButton('↩ Back', 
                 callback_data="settings#caption")]]
     await query.message.edit_text(
        f"<b><u>YOUR CUSTOM CAPTION</b></u>\n\n<code>{data['caption']}</code>",
        reply_markup=InlineKeyboardMarkup(buttons))
    
  elif type=="deletecaption":
     await update_configs(user_id, 'caption', None)
     await query.message.edit_text(
        "<b>successfully updated</b>",
        reply_markup=InlineKeyboardMarkup(buttons))
                              
  elif type=="addcaption":
     await query.message.delete()
     try:
         text = await bot.send_message(query.message.chat.id, "Send your custom caption\n/cancel - <code>cancel this process</code>")
         caption = await bot.listen(chat_id=user_id, timeout=300)
         if caption.text=="/cancel":
            await caption.delete()
            return await text.edit_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
         try:
            caption.text.format(filename='', size='', caption='')
         except KeyError as e:
            await caption.delete()
            return await text.edit_text(
               f"<b>wrong filling {e} used in your caption. change it</b>",
               reply_markup=InlineKeyboardMarkup(buttons))
         await update_configs(user_id, 'caption', caption.text)
         await caption.delete()
         await text.edit_text(
            "<b>successfully updated</b>",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await text.edit_text('Process has been automatically cancelled', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="button":
     buttons = []
     button = (await get_configs(user_id))['button']
     if button is None:
        buttons.append([InlineKeyboardButton('✚ Add Button ✚', 
                      callback_data="settings#addbutton")])
     else:
        buttons.append([InlineKeyboardButton('👀 See Button', 
                      callback_data="settings#seebutton")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Remove Button ', 
                      callback_data="settings#deletebutton"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>CUSTOM BUTTON</b></u>\n\n<b>You can set a inline button to messages.</b>\n\n<b><u>FORMAT:</b></u>\n`[Forward bot][buttonurl:https://t.me/devgaganbot]`\n",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="addbutton":
     await query.message.delete()
     try:
         txt = await bot.send_message(user_id, text="**Send your custom button.\n\nFORMAT:**\n`[forward bot][buttonurl:https://t.me/devgaganbot]`\n")
         ask = await bot.listen(chat_id=user_id, timeout=300)
         button = parse_buttons(ask.text.html)
         if not button:
            await ask.delete()
            return await txt.edit_text("**INVALID BUTTON**")
         await update_configs(user_id, 'button', ask.text.html)
         await ask.delete()
         await txt.edit_text("**Successfully button added**",
            reply_markup=InlineKeyboardMarkup(buttons))
     except asyncio.exceptions.TimeoutError:
         await txt.edit_text('Process has been automatically cancelled', reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seebutton":
      button = (await get_configs(user_id))['button']
      button = parse_buttons(button, markup=False)
      button.append([InlineKeyboardButton("↩ Back", "settings#button")])
      await query.message.edit_text(
         "**YOUR CUSTOM BUTTON**",
         reply_markup=InlineKeyboardMarkup(button))
      
  elif type=="deletebutton":
     await update_configs(user_id, 'button', None)
     await query.message.edit_text(
        "**Successfully button deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
   
  elif type=="database":
     buttons = []
     db_uri = (await get_configs(user_id))['db_uri']
     if db_uri is None:
        buttons.append([InlineKeyboardButton('✚ Add Url ✚', 
                      callback_data="settings#addurl")])
     else:
        buttons.append([InlineKeyboardButton('👀 See Url', 
                      callback_data="settings#seeurl")])
        buttons[-1].append(InlineKeyboardButton('🗑️ Remove Url ', 
                      callback_data="settings#deleteurl"))
     buttons.append([InlineKeyboardButton('↩ Back', 
                      callback_data="settings#main")])
     await query.message.edit_text(
        "<b><u>DATABASE</u>\n\nDatabase is required for store your duplicate messages permenant. other wise stored duplicate media may be disappeared when after bot restart.</b>",
        reply_markup=InlineKeyboardMarkup(buttons))

  elif type=="addurl":
     await query.message.delete()
     uri = await bot.ask(user_id, "<b>please send your mongodb url.</b>\n\n<i>get your Mongodb url from [here](https://mongodb.com)</i>", disable_web_page_preview=True)
     if uri.text=="/cancel":
        return await uri.reply_text(
                  "<b>process canceled !</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
     if not uri.text.startswith("mongodb+srv://") and not uri.text.endswith("majority"):
        return await uri.reply("<b>Invalid Mongodb Url</b>",
                   reply_markup=InlineKeyboardMarkup(buttons))
     await update_configs(user_id, 'db_uri', uri.text)
     await uri.reply("**Successfully database url added**",
             reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="seeurl":
     db_uri = (await get_configs(user_id))['db_uri']
     await query.answer(f"DATABASE URL: {db_uri}", show_alert=True)
  
  elif type=="deleteurl":
     await update_configs(user_id, 'db_uri', None)
     await query.message.edit_text(
        "**Successfully your database url deleted**",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type=="filters":
     await query.message.edit_text(
        "<b><u>💠 CUSTOM FILTERS 💠</b></u>\n\n**configure the type of messages which you want forward**",
        reply_markup=await filters_buttons(user_id))
  
  elif type=="nextfilters":
     await query.edit_message_reply_markup( 
        reply_markup=await next_filters_buttons(user_id))
   
  elif type.startswith("updatefilter"):
     i, key, value = type.split('-')
     if value=="True":
        await update_configs(user_id, key, False)
     else:
        await update_configs(user_id, key, True)
     if key in ['poll', 'protect']:
        return await query.edit_message_reply_markup(
           reply_markup=await next_filters_buttons(user_id)) 
     await query.edit_message_reply_markup(
        reply_markup=await filters_buttons(user_id))
   
  elif type.startswith("file_size"):
    settings = await get_configs(user_id)
    size = settings.get('file_size', 0)
    i, limit = size_limit(settings['size_limit'])
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {limit} `{size} MB` will forward</b>',
       reply_markup=size_button(size))
  
  elif type.startswith("update_size"):
    size = int(query.data.split('-')[1])
    if 0 < size > 2000:
      return await query.answer("size limit exceeded", show_alert=True)
    await update_configs(user_id, 'file_size', size)
    i, limit = size_limit((await get_configs(user_id))['size_limit'])
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {limit} `{size} MB` will forward</b>',
       reply_markup=size_button(size))
  
  elif type.startswith('update_limit'):
    i, limit, size = type.split('-')
    limit, sts = size_limit(limit)
    await update_configs(user_id, 'size_limit', limit) 
    await query.message.edit_text(
       f'<b><u>SIZE LIMIT</b></u><b>\n\nyou can set file size limit to forward\n\nStatus: files with {sts} `{size} MB` will forward</b>',
       reply_markup=size_button(int(size)))
      
  elif type == "add_extension":
    await query.message.delete() 
    ext = await bot.ask(user_id, text="**please send your extensions (seperete by space)**")
    if ext.text == '/cancel':
       return await ext.reply_text(
                  "<b>process canceled</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
    extensions = ext.text.split(" ")
    extension = (await get_configs(user_id))['extension']
    if extension:
        for extn in extensions:
            extension.append(extn)
    else:
        extension = extensions
    await update_configs(user_id, 'extension', extension)
    await ext.reply_text(
        f"**successfully updated**",
        reply_markup=InlineKeyboardMarkup(buttons))
      
  elif type == "get_extension":
    extensions = (await get_configs(user_id))['extension']
    btn = extract_btn(extensions)
    btn.append([InlineKeyboardButton('✚ ADD ✚', 'settings#add_extension')])
    btn.append([InlineKeyboardButton('Remove all', 'settings#rmve_all_extension')])
    btn.append([InlineKeyboardButton('↩ Back', 'settings#main')])
    await query.message.edit_text(
        text='<b><u>EXTENSIONS</u></b>\n\n**Files with these extiontions will not forward**',
        reply_markup=InlineKeyboardMarkup(btn))
  
  elif type == "rmve_all_extension":
    await update_configs(user_id, 'extension', None)
    await query.message.edit_text(text="**successfully deleted**",
                                   reply_markup=InlineKeyboardMarkup(buttons))
  elif type == "add_keyword":
    await query.message.delete()
    ask = await bot.ask(user_id, text="**please send the keywords (seperete by space)**")
    if ask.text == '/cancel':
       return await ask.reply_text(
                  "<b>process canceled</b>",
                  reply_markup=InlineKeyboardMarkup(buttons))
    keywords = ask.text.split(" ")
    keyword = (await get_configs(user_id))['keywords']
    if keyword:
        for word in keywords:
            keyword.append(word)
    else:
        keyword = keywords
    await update_configs(user_id, 'keywords', keyword)
    await ask.reply_text(
        f"**successfully updated**",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type == "get_keyword":
    keywords = (await get_configs(user_id))['keywords']
    btn = extract_btn(keywords)
    btn.append([InlineKeyboardButton('✚ ADD ✚', 'settings#add_keyword')])
    btn.append([InlineKeyboardButton('Remove all', 'settings#rmve_all_keyword')])
    btn.append([InlineKeyboardButton('↩ Back', 'settings#main')])
    await query.message.edit_text(
        text='<b><u>KEYWORDS</u></b>\n\n**File with these keywords in file name will forwad**',
        reply_markup=InlineKeyboardMarkup(btn))
      
  elif type == "rmve_all_keyword":
    await update_configs(user_id, 'keywords', None)
    await query.message.edit_text(text="**successfully deleted**",
                                   reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="ftmmode":
     # New FTM main menu with Delta and Alpha options
     user_can_use_ftm = await db.can_use_ftm_mode(user_id)
     user_can_use_alpha = await db.can_use_ftm_alpha_mode(user_id)
     
     buttons = []
     
     if user_can_use_ftm:
         buttons.append([InlineKeyboardButton('🔥 FTM Delta Mode', callback_data='settings#ftm_delta')])
     else:
         buttons.append([InlineKeyboardButton('🔥 FTM Delta Mode (Pro Only)', callback_data='settings#ftm_delta')])
         
     if user_can_use_alpha:
         buttons.append([InlineKeyboardButton('⚡ FTM Alpha Mode', callback_data='settings#ftm_alpha')])
     else:
         buttons.append([InlineKeyboardButton('⚡ FTM Alpha Mode (Pro Only)', callback_data='settings#ftm_alpha')])
     
     buttons.append([InlineKeyboardButton('↩ Back', callback_data="settings#main")])
     
     await query.message.edit_text(
        f"<b><u>🚀 FTM MODES 🚀</u></b>\n\n"
        f"<b>🔥 FTM Delta Mode:</b>\n"
        f"• Adds source tracking to forwarded messages\n"
        f"• Creates 'Source Link' buttons\n"
        f"• Embeds original message links\n\n"
        f"<b>⚡ FTM Alpha Mode:</b> 🔜\n"
        f"• Real-time auto-forwarding between channels\n"
        f"• Live sync of all new incoming posts\n"
        f"• No 'Forwarded from' tags (bot-uploaded)\n"
        f"• Requires bot admin in both channels\n\n"
        f"<b>⚠️ Fun Fact:</b> We're launching a special Ultra plan for Alpha mode soon! 😉",
        reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="toggle_ftmmode":
     user_can_use_ftm = await db.can_use_ftm_mode(user_id)
     
     if not user_can_use_ftm:
         buttons = [[
            InlineKeyboardButton('💎 Upgrade to Pro Plan',
                        callback_data='premium#main')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#main")
            ]]
         await query.message.edit_text(
            f"<b><u>🔥 FTM MODE 🔥</u></b>\n\n<b>⚠️ Pro Plan Required</b>\n\nFTM Mode is a premium feature available only to Pro plan users.\n\n<b>Pro Plan Benefits:</b>\n• FTM Mode with source tracking\n• Unlimited forwarding\n• Priority support\n\n<b>Pricing:</b>\n• 15 days: ₹299\n• 30 days: ₹549",
            reply_markup=InlineKeyboardMarkup(buttons))
     else:
         current_mode = (await get_configs(user_id))['ftm_mode']
         new_mode = not current_mode
         await update_configs(user_id, 'ftm_mode', new_mode)
         status = "🟢 Enabled" if new_mode else "🔴 Disabled"
         buttons = [[
            InlineKeyboardButton('✅ Enable' if not new_mode else '❌ Disable',
                        callback_data=f'settings#toggle_ftmmode')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#main")
            ]]
         await query.message.edit_text(
            f"<b><u>🔥 FTM MODE 🔥</u></b>\n\n<b>Status:</b> {status}\n\n<b>When FTM Mode is enabled:</b>\n• Each forwarded message will have a 'Source Link' button\n• Original message link will be added to caption\n• Target message link will be embedded in caption\n\n<b>Note:</b> This mode adds source tracking to all forwarded messages.",
            reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="ftm_delta":
     # FTM Delta Mode settings (formerly FTM mode)
     ftm_mode = (await get_configs(user_id))['ftm_mode']
     user_can_use_ftm = await db.can_use_ftm_mode(user_id)
     
     if not user_can_use_ftm:
         buttons = [[
            InlineKeyboardButton('💎 Upgrade to Pro Plan',
                        callback_data='premium#main')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#ftmmode")
            ]]
         await query.message.edit_text(
            f"<b><u>🔥 FTM DELTA MODE 🔥</u></b>\n\n<b>⚠️ Pro Plan Required</b>\n\nFTM Delta Mode is a premium feature available only to Pro plan users.\n\n<b>Pro Plan Benefits:</b>\n• FTM Delta Mode with source tracking\n• Unlimited forwarding\n• Priority support\n\n<b>Pricing:</b>\n• 15 days: ₹299\n• 30 days: ₹549",
            reply_markup=InlineKeyboardMarkup(buttons))
     else:
         buttons = [[
            InlineKeyboardButton('✅ Enable' if not ftm_mode else '❌ Disable',
                        callback_data=f'settings#toggle_ftm_delta')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#ftmmode")
            ]]
         status = "🟢 Enabled" if ftm_mode else "🔴 Disabled"
         await query.message.edit_text(
            f"<b><u>🔥 FTM DELTA MODE 🔥</u></b>\n\n<b>Status:</b> {status}\n\n<b>When FTM Delta Mode is enabled:</b>\n• Each forwarded message will have a 'Source Link' button\n• Original message link will be added to caption\n• Target message link will be embedded in caption\n\n<b>Note:</b> This mode adds source tracking to all forwarded messages.",
            reply_markup=InlineKeyboardMarkup(buttons))
  
  elif type=="toggle_ftm_delta":
     # Toggle FTM Delta mode (same as old toggle_ftmmode)
     user_can_use_ftm = await db.can_use_ftm_mode(user_id)
     
     if not user_can_use_ftm:
         buttons = [[
            InlineKeyboardButton('💎 Upgrade to Pro Plan',
                        callback_data='premium#main')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#ftmmode")
            ]]
         await query.message.edit_text(
            f"<b><u>🔥 FTM DELTA MODE 🔥</u></b>\n\n<b>⚠️ Pro Plan Required</b>\n\nFTM Delta Mode is a premium feature available only to Pro plan users.\n\n<b>Pro Plan Benefits:</b>\n• FTM Delta Mode with source tracking\n• Unlimited forwarding\n• Priority support\n\n<b>Pricing:</b>\n• 15 days: ₹299\n• 30 days: ₹549",
            reply_markup=InlineKeyboardMarkup(buttons))
     else:
         current_mode = (await get_configs(user_id))['ftm_mode']
         new_mode = not current_mode
         await update_configs(user_id, 'ftm_mode', new_mode)
         status = "🟢 Enabled" if new_mode else "🔴 Disabled"
         buttons = [[
            InlineKeyboardButton('✅ Enable' if not new_mode else '❌ Disable',
                        callback_data=f'settings#toggle_ftm_delta')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#ftmmode")
            ]]
         await query.message.edit_text(
            f"<b><u>🔥 FTM DELTA MODE 🔥</u></b>\n\n<b>Status:</b> {status}\n\n<b>When FTM Delta Mode is enabled:</b>\n• Each forwarded message will have a 'Source Link' button\n• Original message link will be added to caption\n• Target message link will be embedded in caption\n\n<b>Note:</b> This mode adds source tracking to all forwarded messages.",
            reply_markup=InlineKeyboardMarkup(buttons))

  elif type=="ftm_alpha":
     # FTM Alpha Mode settings (new real-time forwarding)
     alpha_config = await db.get_alpha_config(user_id)
     user_can_use_alpha = await db.can_use_ftm_alpha_mode(user_id)
     
     if not user_can_use_alpha:
         buttons = [[
            InlineKeyboardButton('💎 Upgrade to Pro Plan',
                        callback_data='premium#main')
            ],[
            InlineKeyboardButton('↩ Back',
                        callback_data="settings#ftmmode")
            ]]
         await query.message.edit_text(
            f"<b><u>⚡ FTM ALPHA MODE ⚡</u></b>\n\n<b>⚠️ Pro Plan Required</b>\n\nFTM Alpha Mode is an advanced premium feature available only to Pro plan users.\n\n<b>Alpha Mode Features:</b>\n• Real-time auto-forwarding between channels\n• Live sync of all new incoming posts\n• No 'Forwarded from' tags (bot-uploaded)\n• Requires bot admin in both channels\n\n<b>🚀 Fun Warning:</b> We're launching an Ultra plan for Alpha mode soon! 😉\n\n<b>Pricing:</b>\n• 15 days: ₹299\n• 30 days: ₹549",
            reply_markup=InlineKeyboardMarkup(buttons))
     else:
         status = "🟢 Enabled" if alpha_config['enabled'] else "🔴 Disabled"
         source_info = f"📤 Source: {alpha_config['source_chat']}" if alpha_config['source_chat'] else "📤 Source: Not configured"
         target_info = f"📥 Target: {alpha_config['target_chat']}" if alpha_config['target_chat'] else "📥 Target: Not configured"
         
         buttons = []
         if alpha_config['enabled']:
             buttons.append([InlineKeyboardButton('❌ Disable Alpha Mode', callback_data='settings#toggle_ftm_alpha')])
         else:
             buttons.append([InlineKeyboardButton('✅ Enable Alpha Mode', callback_data='settings#toggle_ftm_alpha')])
             
         buttons.extend([
             [InlineKeyboardButton('📤 Set Source Channel', callback_data='settings#set_alpha_source')],
             [InlineKeyboardButton('📥 Set Target Channel', callback_data='settings#set_alpha_target')],
             [InlineKeyboardButton('↩ Back', callback_data="settings#ftmmode")]
         ])
         
         await query.message.edit_text(
            f"<b><u>⚡ FTM ALPHA MODE ⚡</u></b>\n\n<b>Status:</b> {status}\n\n{source_info}\n{target_info}\n\n<b>When Alpha Mode is enabled:</b>\n• All new messages from source channel are auto-forwarded\n• Messages are forwarded instantly in real-time\n• No 'Forwarded from' tag (bot-uploaded)\n• Bot must be admin in both channels\n\n<b>⚠️ Note:</b> This feature requires bot admin permissions in both channels.",
            reply_markup=InlineKeyboardMarkup(buttons))

  elif type=="toggle_ftm_alpha":
     # Toggle FTM Alpha mode
     user_can_use_alpha = await db.can_use_ftm_alpha_mode(user_id)
     
     if not user_can_use_alpha:
         return await query.answer("❌ FTM Alpha Mode requires Pro plan!", show_alert=True)
     
     alpha_config = await db.get_alpha_config(user_id)
     new_status = not alpha_config['enabled']
     
     # Check if channels are configured before enabling
     if new_status and (not alpha_config['source_chat'] or not alpha_config['target_chat']):
         return await query.answer("❌ Please configure source and target channels first!", show_alert=True)
     
     await db.set_alpha_config(user_id, enabled=new_status)
     await query.answer(f"✅ FTM Alpha Mode {'enabled' if new_status else 'disabled'}!", show_alert=True)
     
     # Refresh the Alpha mode settings
     await settings_callback(None, query, "ftm_alpha")

  elif type=="set_alpha_source":
     # Set Alpha mode source channel
     user_can_use_alpha = await db.can_use_ftm_alpha_mode(user_id)
     if not user_can_use_alpha:
         return await query.answer("❌ FTM Alpha Mode requires Pro plan!", show_alert=True)
         
     await query.answer("📤 Send the source channel username or invite link (e.g., @channel or https://t.me/channel)", show_alert=True)
     # Note: This would need additional input handling in a real implementation
     
  elif type=="set_alpha_target":
     # Set Alpha mode target channel
     user_can_use_alpha = await db.can_use_ftm_alpha_mode(user_id)
     if not user_can_use_alpha:
         return await query.answer("❌ FTM Alpha Mode requires Pro plan!", show_alert=True)
         
     await query.answer("📥 Send the target channel username or invite link (e.g., @channel or https://t.me/channel)", show_alert=True)
     # Note: This would need additional input handling in a real implementation

  elif type.startswith("alert"):
    alert = type.split('_')[1]
    await query.answer(alert, show_alert=True)
      
def main_buttons():
  buttons = [[
       InlineKeyboardButton('🤖 Bᴏᴛs',
                    callback_data=f'settings#bots'),
       InlineKeyboardButton('🏷 Cʜᴀɴɴᴇʟs',
                    callback_data=f'settings#channels')
       ],[
       InlineKeyboardButton('🖋️ Cᴀᴘᴛɪᴏɴ',
                    callback_data=f'settings#caption'),
       InlineKeyboardButton('🗃 MᴏɴɢᴏDB',
                    callback_data=f'settings#database')
       ],[
       InlineKeyboardButton('🕵‍♀ Fɪʟᴛᴇʀs 🕵‍♀',
                    callback_data=f'settings#filters'),
       InlineKeyboardButton('⏹ Bᴜᴛᴛᴏɴ',
                    callback_data=f'settings#button')
       ],[
       InlineKeyboardButton('🔥 FTM Mᴏᴅᴇ',
                    callback_data='settings#ftmmode'),
       InlineKeyboardButton('Exᴛʀᴀ Sᴇᴛᴛɪɴɢs 🧪',
                    callback_data='settings#nextfilters')
       ],[      
       InlineKeyboardButton('⫷ Bᴀᴄᴋ', callback_data='back')
       ]]
  return InlineKeyboardMarkup(buttons)

def size_limit(limit):
   if str(limit) == "None":
      return None, ""
   elif str(limit) == "True":
      return True, "more than"
   else:
      return False, "less than"

def extract_btn(datas):
    i = 0
    btn = []
    if datas:
       for data in datas:
         if i >= 5:
            i = 0
         if i == 0:
            btn.append([InlineKeyboardButton(data, f'settings#alert_{data}')])
            i += 1
            continue
         elif i > 0:
            btn[-1].append(InlineKeyboardButton(data, f'settings#alert_{data}'))
            i += 1
    return btn 

def size_button(size):
  buttons = [[
       InlineKeyboardButton('+',
                    callback_data=f'settings#update_limit-True-{size}'),
       InlineKeyboardButton('=',
                    callback_data=f'settings#update_limit-None-{size}'),
       InlineKeyboardButton('-',
                    callback_data=f'settings#update_limit-False-{size}')
       ],[
       InlineKeyboardButton('+1',
                    callback_data=f'settings#update_size-{size + 1}'),
       InlineKeyboardButton('-1',
                    callback_data=f'settings#update_size_-{size - 1}')
       ],[
       InlineKeyboardButton('+5',
                    callback_data=f'settings#update_size-{size + 5}'),
       InlineKeyboardButton('-5',
                    callback_data=f'settings#update_size_-{size - 5}')
       ],[
       InlineKeyboardButton('+10',
                    callback_data=f'settings#update_size-{size + 10}'),
       InlineKeyboardButton('-10',
                    callback_data=f'settings#update_size_-{size - 10}')
       ],[
       InlineKeyboardButton('+50',
                    callback_data=f'settings#update_size-{size + 50}'),
       InlineKeyboardButton('-50',
                    callback_data=f'settings#update_size_-{size - 50}')
       ],[
       InlineKeyboardButton('+100',
                    callback_data=f'settings#update_size-{size + 100}'),
       InlineKeyboardButton('-100',
                    callback_data=f'settings#update_size_-{size - 100}')
       ],[
       InlineKeyboardButton('↩ Back',
                    callback_data="settings#main")
     ]]
  return InlineKeyboardMarkup(buttons)
       
async def filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('🏷️ Forward tag',
                    callback_data=f'settings_#updatefilter-forward_tag-{filter["forward_tag"]}'),
       InlineKeyboardButton('✅' if filter['forward_tag'] else '❌',
                    callback_data=f'settings#updatefilter-forward_tag-{filter["forward_tag"]}')
       ],[
       InlineKeyboardButton('🖍️ Texts',
                    callback_data=f'settings_#updatefilter-text-{filters["text"]}'),
       InlineKeyboardButton('✅' if filters['text'] else '❌',
                    callback_data=f'settings#updatefilter-text-{filters["text"]}')
       ],[
       InlineKeyboardButton('📁 Documents',
                    callback_data=f'settings_#updatefilter-document-{filters["document"]}'),
       InlineKeyboardButton('✅' if filters['document'] else '❌',
                    callback_data=f'settings#updatefilter-document-{filters["document"]}')
       ],[
       InlineKeyboardButton('🎞️ Videos',
                    callback_data=f'settings_#updatefilter-video-{filters["video"]}'),
       InlineKeyboardButton('✅' if filters['video'] else '❌',
                    callback_data=f'settings#updatefilter-video-{filters["video"]}')
       ],[
       InlineKeyboardButton('📷 Photos',
                    callback_data=f'settings_#updatefilter-photo-{filters["photo"]}'),
       InlineKeyboardButton('✅' if filters['photo'] else '❌',
                    callback_data=f'settings#updatefilter-photo-{filters["photo"]}')
       ],[
       InlineKeyboardButton('🎧 Audios',
                    callback_data=f'settings_#updatefilter-audio-{filters["audio"]}'),
       InlineKeyboardButton('✅' if filters['audio'] else '❌',
                    callback_data=f'settings#updatefilter-audio-{filters["audio"]}')
       ],[
       InlineKeyboardButton('🎤 Voices',
                    callback_data=f'settings_#updatefilter-voice-{filters["voice"]}'),
       InlineKeyboardButton('✅' if filters['voice'] else '❌',
                    callback_data=f'settings#updatefilter-voice-{filters["voice"]}')
       ],[
       InlineKeyboardButton('🎭 Animations',
                    callback_data=f'settings_#updatefilter-animation-{filters["animation"]}'),
       InlineKeyboardButton('✅' if filters['animation'] else '❌',
                    callback_data=f'settings#updatefilter-animation-{filters["animation"]}')
       ],[
       InlineKeyboardButton('🃏 Stickers',
                    callback_data=f'settings_#updatefilter-sticker-{filters["sticker"]}'),
       InlineKeyboardButton('✅' if filters['sticker'] else '❌',
                    callback_data=f'settings#updatefilter-sticker-{filters["sticker"]}')
       ],[
       InlineKeyboardButton('▶️ Skip duplicate',
                    callback_data=f'settings_#updatefilter-duplicate-{filter["duplicate"]}'),
       InlineKeyboardButton('✅' if filter['duplicate'] else '❌',
                    callback_data=f'settings#updatefilter-duplicate-{filter["duplicate"]}')
       ],[
       InlineKeyboardButton('🖼️📝 Image+Text',
                    callback_data=f'settings_#updatefilter-image_text-{filters["image_text"]}'),
       InlineKeyboardButton('✅' if filters['image_text'] else '❌',
                    callback_data=f'settings#updatefilter-image_text-{filters["image_text"]}')
       ],[
       InlineKeyboardButton('⫷ back',
                    callback_data="settings#main")
       ]]
  return InlineKeyboardMarkup(buttons) 

async def next_filters_buttons(user_id):
  filter = await get_configs(user_id)
  filters = filter['filters']
  buttons = [[
       InlineKeyboardButton('📊 Poll',
                    callback_data=f'settings_#updatefilter-poll-{filters["poll"]}'),
       InlineKeyboardButton('✅' if filters['poll'] else '❌',
                    callback_data=f'settings#updatefilter-poll-{filters["poll"]}')
       ],[
       InlineKeyboardButton('🔒 Secure message',
                    callback_data=f'settings_#updatefilter-protect-{filter["protect"]}'),
       InlineKeyboardButton('✅' if filter['protect'] else '❌',
                    callback_data=f'settings#updatefilter-protect-{filter["protect"]}')
       ],[
       InlineKeyboardButton('🛑 size limit',
                    callback_data='settings#file_size')
       ],[
       InlineKeyboardButton('💾 Extension',
                    callback_data='settings#get_extension')
       ],[
       InlineKeyboardButton('♦️ keywords ♦️',
                    callback_data='settings#get_keyword')
       ],[
       InlineKeyboardButton('⫷ back', 
                    callback_data="settings#main")
       ]]
  return InlineKeyboardMarkup(buttons) 
   
