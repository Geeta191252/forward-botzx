# FTM Alpha Mode - Real-time Auto-forwarding Plugin
import asyncio
from pyrogram import Client, filters
from pyrogram.errors import FloodWait, ChatAdminRequired, ChannelPrivate
from database import db
from config import Config

# Global variable to store active Alpha mode configurations
active_alpha_configs = {}

async def load_alpha_configs():
    """Load all active FTM Alpha mode configurations"""
    global active_alpha_configs
    try:
        alpha_users = await db.get_all_alpha_users()
        active_alpha_configs = {}
        
        for config in alpha_users:
            if config.get('source_chat') and config.get('target_chat'):
                source_chat = str(config['source_chat'])
                if source_chat not in active_alpha_configs:
                    active_alpha_configs[source_chat] = []
                
                active_alpha_configs[source_chat].append({
                    'user_id': config['user_id'],
                    'target_chat': config['target_chat']
                })
        
        print(f"✅ FTM Alpha Mode: Loaded {len(active_alpha_configs)} source channels")
    except Exception as e:
        print(f"❌ Error loading Alpha configs: {e}")

async def validate_and_filter_configs(bot):
    """Validate bot permissions and filter valid configurations"""
    global active_alpha_configs
    valid_configs = {}
    
    for source_chat, targets in active_alpha_configs.items():
        valid_targets = []
        
        for target_config in targets:
            try:
                user_id = target_config['user_id']
                target_chat = target_config['target_chat']
                
                # Validate user still has Pro plan
                if not await db.can_use_ftm_alpha_mode(user_id):
                    continue
                
                # Check bot permissions in both chats
                is_valid, reason = await db.validate_alpha_permissions(user_id, bot, source_chat, target_chat)
                if is_valid:
                    valid_targets.append(target_config)
                else:
                    print(f"⚠️ Alpha Mode: Skipping {source_chat} -> {target_chat}: {reason}")
                    
            except Exception as e:
                print(f"❌ Error validating config for user {user_id}: {e}")
        
        if valid_targets:
            valid_configs[source_chat] = valid_targets
    
    active_alpha_configs = valid_configs
    print(f"✅ FTM Alpha Mode: {len(valid_configs)} source channels with valid permissions")

@Client.on_message(filters.channel & ~filters.service)
async def ftm_alpha_handler(client, message):
    """Real-time message handler for FTM Alpha mode"""
    try:
        source_chat_id = str(message.chat.id)
        
        # Check if this channel has active Alpha mode configurations
        if source_chat_id not in active_alpha_configs:
            return
        
        # Skip old messages (only forward new/live messages)
        from datetime import datetime, timedelta
        if message.date < (datetime.utcnow() - timedelta(minutes=2)):
            return
        
        print(f"🔥 FTM Alpha: Processing message {message.id} from {source_chat_id}")
        
        # Process each target configuration for this source channel
        for target_config in active_alpha_configs[source_chat_id]:
            try:
                target_chat = target_config['target_chat']
                user_id = target_config['user_id']
                
                # Double-check user still has permissions
                if not await db.can_use_ftm_alpha_mode(user_id):
                    continue
                
                # Forward message without "Forwarded from" tag (using copy_message)
                await client.copy_message(
                    chat_id=target_chat,
                    from_chat_id=source_chat_id,
                    message_id=message.id,
                    caption=message.caption,
                    reply_markup=message.reply_markup
                )
                
                print(f"✅ Alpha Mode: Forwarded message {message.id} to {target_chat}")
                
                # Small delay to avoid flooding
                await asyncio.sleep(0.5)
                
            except FloodWait as e:
                print(f"⏳ Alpha Mode: FloodWait {e.value}s for target {target_chat}")
                await asyncio.sleep(e.value)
            except ChatAdminRequired:
                print(f"❌ Alpha Mode: Bot not admin in {target_chat}, disabling config")
                await db.set_alpha_config(user_id, enabled=False)
            except ChannelPrivate:
                print(f"❌ Alpha Mode: Cannot access {target_chat}, disabling config")
                await db.set_alpha_config(user_id, enabled=False)
            except Exception as e:
                print(f"❌ Alpha Mode forwarding error: {e}")
    
    except Exception as e:
        print(f"❌ FTM Alpha handler error: {e}")

# Background task to periodically reload configurations
async def alpha_config_reloader():
    """Periodically reload Alpha mode configurations"""
    while True:
        try:
            await asyncio.sleep(300)  # Reload every 5 minutes
            await load_alpha_configs()
        except Exception as e:
            print(f"❌ Alpha config reloader error: {e}")

# Initialize Alpha mode when bot starts
async def initialize_alpha_mode(bot):
    """Initialize FTM Alpha mode on bot startup"""
    print("🚀 Initializing FTM Alpha Mode...")
    await load_alpha_configs()
    await validate_and_filter_configs(bot)
    
    # Start background config reloader
    asyncio.create_task(alpha_config_reloader())
    print("✅ FTM Alpha Mode initialized successfully!")

# Export the initialization function
__all__ = ['initialize_alpha_mode', 'ftm_alpha_handler', 'load_alpha_configs']