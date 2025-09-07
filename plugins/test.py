import os
import re 
import sys
import typing
import asyncio 
import logging 
from database import db 
from config import Config, temp
from pyrogram import Client, filters
from pyrogram.raw.all import layer
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message 
from pyrogram.errors.exceptions.bad_request_400 import AccessTokenExpired, AccessTokenInvalid
from pyrogram.errors import FloodWait
from config import Config
from translation import Translation

from typing import Union, Optional, AsyncGenerator

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BTN_URL_REGEX = re.compile(r"(\[([^\[]+?)]\[buttonurl:/{0,2}(.+?)(:same)?])")
BOT_TOKEN_TEXT = "<b>1) create a bot using @BotFather\n2) Then you will get a message with bot token\n3) Forward that message to me</b>"
SESSION_STRING_SIZE = 351

async def get_configs(user_id):
    """Get user configurations from database"""
    try:
        user_data = await db.get_user(user_id)
        if not user_data:
            # Return default config if user not found
            return {
                'filters': {
                    'text': True,
                    'photo': True,
                    'video': True,
                    'document': True,
                    'audio': True,
                    'voice': True,
                    'animation': True,
                    'sticker': True,
                    'poll': True,
                    'image_text': False
                },
                'forward_tag': False,
                'protect': False,
                'duplicate': True,
                'file_size': 0,
                'size_limit': False,
                'extension': [],
                'keywords': [],
                'ftm_mode': False
            }
        return user_data
    except Exception as e:
        print(f"Error getting configs for user {user_id}: {e}")
        # Return default config on error
        return {
            'filters': {
                'text': True,
                'photo': True,
                'video': True,
                'document': True,
                'audio': True,
                'voice': True,
                'animation': True,
                'sticker': True,
                'poll': True,
                'image_text': False
            },
            'caption': None,
            'forward_tag': False,
            'protect': False,
            'duplicate': True,
            'file_size': 0,
            'size_limit': False,
            'extension': [],
            'keywords': [],
            'button': None,
            'db_uri': None,
            'ftm_mode': False
        }

async def update_configs(user_id, key, value):
    """Update user configuration in database"""
    try:
        await db.update_user_config(user_id, key, value)
        return True
    except Exception as e:
        print(f"Error updating config for user {user_id}: {e}")
        return False

async def start_clone_bot(FwdBot, data=None):
   await FwdBot.start()
   #
   async def iter_messages(
      self, 
      chat_id: Union[int, str], 
      limit: int, 
      offset: int = 0,
      search: str = None,
      filter: "types.TypeMessagesFilter" = None,
      ) -> Optional[AsyncGenerator["types.Message", None]]:
        """Iterate through a chat sequentially.
        This convenience method does the same as repeatedly calling :meth:`~pyrogram.Client.get_messages` in a loop, thus saving
        you from the hassle of setting up boilerplate code. It is useful for getting the whole chat messages with a
        single call.
        Parameters:
            chat_id (``int`` | ``str``):
                Unique identifier (int) or username (str) of the target chat.
                For your personal cloud (Saved Messages) you can simply use "me" or "self".
                For a contact that exists in your Telegram address book you can use his phone number (str).

            limit (``int``):
                Identifier of the last message to be returned.

            offset (``int``, *optional*):
                Identifier of the first message to be returned.
                Defaults to 0.
        Returns:
            ``Generator``: A generator yielding :obj:`~pyrogram.types.Message` objects.
        Example:
            .. code-block:: python
                for message in app.iter_messages("pyrogram", 1, 15000):
                    print(message.text)
        """
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1
   #
   # Bind the method to the instance properly
   import types
   FwdBot.iter_messages = types.MethodType(iter_messages, FwdBot)
   return FwdBot

class CLIENT: 
  def __init__(self):
     self.api_id = Config.API_ID
     self.api_hash = Config.API_HASH

  def client(self, data, user=None):
     if user == None and data.get('is_bot') == False:
        return Client("USERBOT", self.api_id, self.api_hash, session_string=data.get('session'))
     elif user == True:
        return Client("USERBOT", self.api_id, self.api_hash, session_string=data)
     elif user != False:
        data = data.get('token')
     return Client("BOT", self.api_id, self.api_hash, bot_token=data, in_memory=True)

  async def add_bot(self, bot, message):
     user_id = int(message.from_user.id)
     msg = await bot.ask(chat_id=user_id, text=BOT_TOKEN_TEXT)
     if msg.text=='/cancel':
        return await msg.reply('<b>process cancelled !</b>')
     elif not msg.forward_date:
       return await msg.reply_text("<b>This is not a forward message</b>")
     elif str(msg.forward_from.id) != "93372553":
       return await msg.reply_text("<b>This message was not forward from bot father</b>")
     bot_token = re.findall(r'\d[0-9]{8,10}:[0-9A-Za-z_-]{35}', msg.text, re.IGNORECASE)
     bot_token = bot_token[0] if bot_token else None
     if not bot_token:
       return await msg.reply_text("<b>There is no bot token in that message</b>")
     try:
       _client = await start_clone_bot(self.client(bot_token, False), True)
     except Exception as e:
       await msg.reply_text(f"<b>BOT ERROR:</b> `{e}`")
     _bot = _client.me
     details = {
       'id': _bot.id,
       'is_bot': True,
       'user_id': user_id,
       'name': _bot.first_name,
       'token': bot_token,
       'username': _bot.username 
     }
     await db.add_bot(details)
     return True

  async def add_session(self, bot, message):
     user_id = int(message.from_user.id)
     text = "<b>⚠️ DISCLAIMER ⚠️</b>\n\n<code>you can use your session for forward message from private chat to another chat.\nPlease add your pyrogram session with your own risk. Their is a chance to ban your account. My developer is not responsible if your account may get banned.</code>"
     await bot.send_message(user_id, text=text)
     msg = await bot.ask(chat_id=user_id, text="<b>send your pyrogram session.\nGet it from trusted sources.\n\n/cancel - cancel the process</b>")
     if msg.text=='/cancel':
        return await msg.reply('<b>process cancelled !</b>')
     elif len(msg.text) < SESSION_STRING_SIZE:
        return await msg.reply('<b>invalid session sring</b>')
     try:
       client = await start_clone_bot(self.client(msg.text, True), True)
     except Exception as e:
       await msg.reply_text(f"<b>USER BOT ERROR:</b> `{e}`")
     user = client.me
     details = {
       'id': user.id,
       'is_bot': False,
       'user_id': user_id,
       'name': user.first_name,
       'session': msg.text,
       'username': user.username
     }
     await db.add_bot(details)
     return True

  async def add_phone_login(self, bot, message):
     user_id = int(message.from_user.id)
     text = "<b>⚠️ DISCLAIMER ⚠️</b>\n\n<code>Login with phone number to create user bot session. Please use your own risk. There is a chance to ban your account. My developer is not responsible if your account may get banned.</code>"
     await bot.send_message(user_id, text=text)

     # Get phone number
     phone_msg = await bot.ask(chat_id=user_id, text="<b>Send your phone number with country code (e.g., +1234567890)\n\n/cancel - cancel the process</b>")
     if phone_msg.text == '/cancel':
        return await phone_msg.reply('<b>process cancelled !</b>')

     phone_number = phone_msg.text.strip()
     if not phone_number.startswith('+'):
        return await phone_msg.reply('<b>Please include country code with + sign</b>')

     client = None
     try:
       # Create client with phone number
       client = Client("USERBOT_PHONE", self.api_id, self.api_hash, phone_number=phone_number, in_memory=True)
       await client.connect()

       # Send code
       sent_code = await client.send_code(phone_number)

       # Get verification code with specific format instruction
       code_msg = await bot.ask(chat_id=user_id, text="<b>Send the verification code you received from Telegram.\n\n⚠️ Format: If code is 12345, send it as: FTM12345\n\n/cancel - cancel the process</b>")
       if code_msg.text == '/cancel':
          await client.disconnect()
          return await code_msg.reply('<b>process cancelled !</b>')

       verification_code = code_msg.text.strip()

       # Extract actual code if it has FTM prefix
       if verification_code.upper().startswith('FTM'):
          verification_code = verification_code[3:]  # Remove FTM prefix

       # Add delay to avoid rate limiting
       await asyncio.sleep(2)

       # Sign in with phone and code
       try:
          await client.sign_in(phone_number, sent_code.phone_code_hash, verification_code)
       except Exception as e:
          error_str = str(e).lower()
          if "two-step verification" in error_str or "password" in error_str or "2fa" in error_str:
             # Get 2FA password
             password_msg = await bot.ask(chat_id=user_id, text="<b>Two-step verification is enabled on your account.\n\nSend your 2FA password (cloud password)\n\n/cancel - cancel the process</b>")
             if password_msg.text == '/cancel':
                await client.disconnect()
                return await password_msg.reply('<b>process cancelled !</b>')

             try:
                await asyncio.sleep(1)  # Small delay
                await client.check_password(password_msg.text)
             except Exception as pwd_e:
                await client.disconnect()
                return await password_msg.reply(f"<b>PASSWORD ERROR:</b> `{pwd_e}`")
          elif "flood" in error_str:
             await client.disconnect()
             return await code_msg.reply("<b>Too many login attempts. Please try again later (after 24 hours).</b>")
          elif "phone_code_invalid" in error_str:
             await client.disconnect()
             return await code_msg.reply("<b>Invalid verification code. Please check and try again.</b>")
          elif "phone_code_expired" in error_str:
             await client.disconnect()
             return await code_msg.reply("<b>Verification code expired. Please start the login process again.</b>")
          else:
             await client.disconnect()
             return await code_msg.reply(f"<b>VERIFICATION ERROR:</b> `{e}`")

       # Add small delay before exporting session
       await asyncio.sleep(1)

       # Export session string
       session_string = await client.export_session_string()
       await client.disconnect()

       # Add delay before creating new client
       await asyncio.sleep(2)

       # Create new client with session string to verify
       verify_client = await start_clone_bot(self.client(session_string, True), True)
       user = verify_client.me
       await verify_client.stop()

       details = {
         'id': user.id,
         'is_bot': False,
         'user_id': user_id,
         'name': user.first_name,
         'session': session_string,
         'username': user.username
       }
       await db.add_bot(details)

       success_msg = f"<b>✅ Successfully logged in!</b>\n\n<b>Account:</b> {user.first_name}\n<b>Username:</b> @{user.username if user.username else 'None'}\n<b>ID:</b> {user.id}"
       await phone_msg.reply(success_msg)
       return True

     except Exception as e:
       try:
          if client:
             await client.disconnect()
       except:
          pass
       error_str = str(e).lower()
       if "flood" in error_str:
          await phone_msg.reply_text("<b>LOGIN ERROR:</b> Too many attempts. Please try again after 24 hours.")
       elif "phone_number_invalid" in error_str:
          await phone_msg.reply_text("<b>LOGIN ERROR:</b> Invalid phone number format.")
       elif "phone_number_banned" in error_str:
          await phone_msg.reply_text("<b>LOGIN ERROR:</b> This phone number is banned from Telegram.")
       else:
          await phone_msg.reply_text(f"<b>LOGIN ERROR:</b> `{e}`")
       return False

@Client.on_message(filters.private & filters.command('reset'))
async def forward_tag(bot, m):
   default = await db.get_configs("01")
   temp.CONFIGS[m.from_user.id] = default
   await db.update_configs(m.from_user.id, default)
   await m.reply("successfully settings reseted ✔️")

@Client.on_message(filters.command('resetall') & filters.user(Config.OWNER_ID))
async def resetall(bot, message):
  users = await db.get_all_users()
  sts = await message.reply("**processing**")
  TEXT = "total: {}\nsuccess: {}\nfailed: {}\nexcept: {}"
  total = success = failed = already = 0
  ERRORS = []
  async for user in users:
      user_id = user['id']
      default = await get_configs(user_id)
      default['db_uri'] = None
      total += 1
      if total %10 == 0:
         await sts.edit(TEXT.format(total, success, failed, already))
      try: 
         await db.update_configs(user_id, default)
         success += 1
      except Exception as e:
         ERRORS.append(e)
         failed += 1
  if ERRORS:
     await message.reply(ERRORS[:100])
  await sts.edit("completed\n" + TEXT.format(total, success, failed, already))

async def get_configs(user_id):
  #configs = temp.CONFIGS.get(user_id)
  #if not configs:
  configs = await db.get_configs(user_id)
  
  # Ensure all required keys exist with proper defaults
  if 'ftm_mode' not in configs:
     configs['ftm_mode'] = False
  if 'keywords' not in configs:
     configs['keywords'] = []
  if 'extension' not in configs:
     configs['extension'] = []
  if 'file_size' not in configs:
     configs['file_size'] = 0
  if 'size_limit' not in configs:
     configs['size_limit'] = False
  if 'duplicate' not in configs:
     configs['duplicate'] = True
  if 'protect' not in configs:
     configs['protect'] = False
  if 'forward_tag' not in configs:
     configs['forward_tag'] = False
  if 'caption' not in configs:
     configs['caption'] = None
  if 'button' not in configs:
     configs['button'] = None
  if 'db_uri' not in configs:
     configs['db_uri'] = None
     
  # Ensure filters exist and have all required message types
  if 'filters' not in configs:
     configs['filters'] = {
            'text': True,
            'photo': True,
            'video': True,
            'document': True,
            'audio': True,
            'voice': True,
            'animation': True,
            'sticker': True,
            'poll': True,
            'image_text': False
        }
  else:
      # Ensure all filter types exist
      default_filters = {
          'text': True,
          'photo': True,
          'video': True,
          'document': True,
          'audio': True,
          'voice': True,
          'animation': True,
          'sticker': True,
          'poll': True,
          'image_text': False
      }
      for key, default_value in default_filters.items():
          if key not in configs['filters']:
              configs['filters'][key] = default_value
          
  #temp.CONFIGS[user_id] = configs 
  return configs

async def update_configs(user_id, key, value):
  current = await db.get_configs(user_id)
  if key in ['caption', 'duplicate', 'db_uri', 'forward_tag', 'protect', 'file_size', 'size_limit', 'extension', 'keywords', 'button', 'ftm_mode']:
     current[key] = value
  else: 
     current['filters'][key] = value
 # temp.CONFIGS[user_id] = value
  await db.update_configs(user_id, current)

def parse_buttons(text, markup=True):
    buttons = []
    for match in BTN_URL_REGEX.finditer(text):
        n_escapes = 0
        to_check = match.start(1) - 1
        while to_check > 0 and text[to_check] == "\\":
            n_escapes += 1
            to_check -= 1

        if n_escapes % 2 == 0:
            if bool(match.group(4)) and buttons:
                buttons[-1].append(InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", "")))
            else:
                buttons.append([InlineKeyboardButton(
                    text=match.group(2),
                    url=match.group(3).replace(" ", ""))])
    if markup and buttons:
       buttons = InlineKeyboardMarkup(buttons)
    return buttons if buttons else None
