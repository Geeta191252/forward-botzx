import asyncio
import logging 
import os
import logging.config
from database import db 
from config import Config  
from pyrogram import Client, __version__
from pyrogram.raw.all import layer 
from pyrogram.enums import ParseMode
from pyrogram.errors import FloodWait
from pyrogram import utils as pyroutils 

logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)

# Adjust Pyrogram chat ID ranges to solve peer ID issue
pyroutils.MIN_CHAT_ID = -999999999999
pyroutils.MIN_CHANNEL_ID = -100999999999999

class Bot(Client): 
    def __init__(self):
        super().__init__(
            Config.BOT_SESSION,
            api_hash=Config.API_HASH,
            api_id=Config.API_ID,
            plugins={
                "root": "plugins"
            },
            workers=50,
            bot_token=Config.BOT_TOKEN
        )
        self.log = logging
        self.log_channel_id = getattr(Config, 'LOG_CHANNEL_ID', -1003003594014)  # Default to the mentioned channel
        self.notification_manager = None  # Will be initialized after start

    async def start(self):
        await super().start()
        me = await self.get_me()
        logging.info(f"{me.first_name} with for pyrogram v{__version__} (Layer {layer}) started on @{me.username}.")
        self.id = me.id
        self.username = me.username
        self.first_name = me.first_name
        self.set_parse_mode(ParseMode.DEFAULT)
        
        # Initialize notification manager
        from utils.notifications import NotificationManager
        self.notification_manager = NotificationManager(self)
        
        text = "**๏[-ิ_•ิ]๏ bot restarted !**"
        logging.info(text)
        success = failed = 0
        
        # Send restart message to all users (not just forwarding users)
        all_users = await db.get_all_users()
        async for user in all_users:
           chat_id = user['id']
           try:
              await self.send_message(chat_id, text)
              success += 1
           except FloodWait as e:
              await asyncio.sleep(e.value + 1)
              try:
                 await self.send_message(chat_id, text)
                 success += 1
              except Exception:
                 failed += 1
           except Exception:
              failed += 1 
        
        # Also send to owner
        for owner_id in Config.OWNER_ID:
           try:
              await self.send_message(owner_id, text)
           except Exception:
              pass
        
        # Clear all forwarding sessions
        await db.rmve_frwd(all=True)
        if (success + failed) != 0:
           logging.info(f"Restart message status - "
                 f"success: {success}, "
                 f"failed: {failed}")
        
        # Send startup notification to log channel after restart messages are sent
        try:
            startup_msg = f"""<b>🚀 Bot Started Successfully!</b>

<b>Bot Name:</b> {me.first_name}
<b>Username:</b> @{me.username}
<b>Bot ID:</b> <code>{me.id}</code>
<b>Pyrogram Version:</b> v{__version__}
<b>Layer:</b> {layer}

<b>Restart Stats:</b>
• Success: {success} users notified
• Failed: {failed} users failed
• Total Users: {success + failed}

<b>Status:</b> ✅ Online and Ready"""
            
            await self.notification_manager.send_log_notification(startup_msg)
            logging.info("Startup notification sent to log channel")
        except Exception as e:
            logging.error(f"Failed to send startup notification: {e}")
        
        # Start background cleanup task for chat requests
        try:
            from utils.cleanup import periodic_cleanup
            asyncio.create_task(periodic_cleanup())
            logging.info("Background cleanup task started")
        except Exception as e:
            logging.error(f"Failed to start cleanup task: {e}")

    async def stop(self, *args):
        msg = f"@{self.username} stopped. Bye."
        await super().stop()
        logging.info(msg)

if __name__ == "__main__":
    bot = Bot()
    bot.run()
