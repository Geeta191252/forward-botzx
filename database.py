from os import environ 
from config import Config
import motor.motor_asyncio
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta

async def mongodb_version():
    x = MongoClient(Config.DATABASE_URI)
    mongodb_version = x.server_info()['version']
    return mongodb_version

class Database:

    def __init__(self, uri, database_name):
        self._client = motor.motor_asyncio.AsyncIOMotorClient(uri)
        self.db = self._client[database_name]
        self.bot = self.db.bots
        self.col = self.db.users
        self.nfy = self.db.notify
        self.chl = self.db.channels
        self.queue_col = self.db.queue  # For crash recovery queue
        self.premium_col = self.db.premium_users  # Premium users collection
        self.payment_col = self.db.payment_verifications  # Payment verification collection
        self.usage_col = self.db.usage_tracking  # Monthly usage tracking
        self.admin_chat_col = self.db.admin_chats  # Admin chat sessions
        self.contact_requests_col = self.db.contact_requests  # Contact requests collection 
        self.chat_requests_col = self.db.chat_requests  # Chat requests collection 

    def new_user(self, id, name):
        from datetime import datetime
        return dict(
            id = id,
            name = name,
            joined_date = datetime.utcnow(),
            ban_status=dict(
                is_banned=False,
                ban_reason="",
            ),
        )

    async def add_user(self, id, name):
        user = self.new_user(id, name)
        await self.col.insert_one(user)

    async def is_user_exist(self, id):
        user = await self.col.find_one({'id':int(id)})
        return bool(user)

    async def total_users_bots_count(self):
        bcount = await self.bot.count_documents({})
        count = await self.col.count_documents({})
        return count, bcount

    async def total_channels(self):
        count = await self.chl.count_documents({})
        return count

    async def remove_ban(self, id):
        ban_status = dict(
            is_banned=False,
            ban_reason=''
        )
        await self.col.update_one({'id': id}, {'$set': {'ban_status': ban_status}})

    async def ban_user(self, user_id, ban_reason="No Reason"):
        ban_status = dict(
            is_banned=True,
            ban_reason=ban_reason
        )
        await self.col.update_one({'id': user_id}, {'$set': {'ban_status': ban_status}})

    async def get_ban_status(self, id):
        default = dict(
            is_banned=False,
            ban_reason=''
        )
        user = await self.col.find_one({'id':int(id)})
        if not user:
            return default
        return user.get('ban_status', default)

    async def get_all_users(self):
        return await self.col.find({}).to_list(length=1000)

    async def get_user(self, user_id):
        """Get user data by user ID"""
        return await self.col.find_one({'id': int(user_id)})

    async def delete_user(self, user_id):
        await self.col.delete_many({'id': int(user_id)})

    async def get_banned(self):
        users = self.col.find({'ban_status.is_banned': True})
        b_users = [user['id'] async for user in users]
        return b_users

    async def update_configs(self, id, configs):
        await self.col.update_one({'id': int(id)}, {'$set': {'configs': configs}})

    async def get_configs(self, id):
        default = {
            'caption': None,
            'button': None,
            'duplicate': True,
            'db_uri': None,
            'forward_tag': False,
            'file_size': 0,
            'size_limit': None,
            'extension': None,
            'keywords': None,
            'ftm_mode': False,  # Now called FTM Delta mode
            'ftm_alpha_mode': False,  # New FTM Alpha mode for real-time forwarding
            'alpha_source_chat': None,  # Source channel for Alpha mode
            'alpha_target_chat': None,  # Target channel for Alpha mode
            'protect': None,
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
        }
        user = await self.col.find_one({'id':int(id)})
        if user:
            return user.get('configs', default)
        return default 

    async def add_bot(self, datas):
       if not await self.is_bot_exist(datas['user_id']):
          await self.bot.insert_one(datas)

    async def remove_bot(self, user_id):
       await self.bot.delete_many({'user_id': int(user_id)})

    async def get_bot(self, user_id: int):
       bot = await self.bot.find_one({'user_id': user_id})
       return bot if bot else None

    async def is_bot_exist(self, user_id):
       bot = await self.bot.find_one({'user_id': user_id})
       return bool(bot)

    async def in_channel(self, user_id: int, chat_id: int) -> bool:
       channel = await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})
       return bool(channel)

    async def add_channel(self, user_id: int, chat_id: int, title, username):
       channel = await self.in_channel(user_id, chat_id)
       if channel:
         return False
       return await self.chl.insert_one({"user_id": user_id, "chat_id": chat_id, "title": title, "username": username})

    async def remove_channel(self, user_id: int, chat_id: int):
       channel = await self.in_channel(user_id, chat_id )
       if not channel:
         return False
       return await self.chl.delete_many({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_channel_details(self, user_id: int, chat_id: int):
       return await self.chl.find_one({"user_id": int(user_id), "chat_id": int(chat_id)})

    async def get_user_channels(self, user_id: int):
       channels = self.chl.find({"user_id": int(user_id)})
       return [channel async for channel in channels]

    async def get_filters(self, user_id):
       filters = []
       filter = (await self.get_configs(user_id))['filters']
       for k, v in filter.items():
          if v == False:
            filters.append(str(k))
       return filters

    async def add_frwd(self, user_id):
       return await self.nfy.insert_one({'user_id': int(user_id)})

    async def rmve_frwd(self, user_id=0, all=False):
       data = {} if all else {'user_id': int(user_id)}
       return await self.nfy.delete_many(data)

    async def get_all_frwd(self):
       return self.nfy.find({})

    # Queue management for crash recovery
    async def add_queue_item(self, user_id, process_data):
        """Add a forwarding process to the queue"""
        queue_item = {
            'user_id': user_id,
            'status': 'active',
            'created_at': datetime.utcnow(),
            'process_data': process_data
        }
        result = await self.queue_col.insert_one(queue_item)
        return result.inserted_id
    
    async def update_queue_status(self, user_id, status):
        """Update queue status (active, completed, cancelled)"""
        return await self.queue_col.update_one(
            {'user_id': user_id, 'status': 'active'},
            {'$set': {'status': status, 'updated_at': datetime.utcnow()}}
        )
    
    async def get_active_queues(self):
        """Get all active forwarding processes for crash recovery"""
        return await self.queue_col.find({'status': 'active'}).to_list(length=100)
    
    async def remove_completed_queues(self):
        """Clean up completed/cancelled queue items older than 1 day"""
        cutoff = datetime.utcnow() - timedelta(days=1)
        result = await self.queue_col.delete_many({
            'status': {'$in': ['completed', 'cancelled']},
            'updated_at': {'$lt': cutoff}
        })
        return result.deleted_count

    # Premium user management
    async def add_premium_user(self, user_id, plan_type="pro", duration_days=30, amount_paid=None):
        """Add a user to premium with three-tier support"""
        expires_at = datetime.utcnow() + timedelta(days=duration_days)
        
        premium_data = {
            'user_id': int(user_id),
            'plan_type': plan_type,  # 'free', 'plus', 'pro'
            'duration_days': duration_days,
            'amount_paid': amount_paid,
            'subscribed_at': datetime.utcnow(),
            'expires_at': expires_at,
            'is_active': True,
            'auto_renew': False,
            'features': self._get_plan_features(plan_type)
        }
        
        # Remove existing premium record if any
        await self.premium_col.delete_many({'user_id': int(user_id)})
        return await self.premium_col.insert_one(premium_data)
    
    def _get_plan_features(self, plan_type):
        """Get features for a specific plan type"""
        from config import Config
        return Config.PLAN_FEATURES.get(plan_type, Config.PLAN_FEATURES['free'])

    async def remove_premium_user(self, user_id):
        """Remove a user from premium"""
        return await self.premium_col.delete_many({'user_id': int(user_id)})

    async def is_premium_user(self, user_id):
        """Check if user has active premium subscription"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        return bool(user)
    
    async def get_user_plan(self, user_id):
        """Get user's current plan type"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        return user['plan_type'] if user else 'free'
    
    async def get_user_plan_features(self, user_id):
        """Get user's plan features"""
        user = await self.premium_col.find_one({
            'user_id': int(user_id),
            'is_active': True,
            'expires_at': {'$gt': datetime.utcnow()}
        })
        if user:
            plan_type = user.get('plan_type', 'free')
            current_plan_features = self._get_plan_features(plan_type)
            stored_features = user.get('features', {})
            
            # Merge current plan features with stored features (current plan takes precedence for missing keys)
            merged_features = {**current_plan_features, **stored_features}
            
            # If features are missing/outdated, update them in database
            if stored_features != merged_features:
                await self.premium_col.update_one(
                    {'user_id': int(user_id)},
                    {'$set': {'features': merged_features}}
                )
                print(f"✅ Updated features for Pro user {user_id}: added missing keys")
            
            return merged_features
        return self._get_plan_features('free')
    
    async def can_use_ftm_mode(self, user_id):
        """Check if user can use FTM Delta mode (Pro plan only)"""
        features = await self.get_user_plan_features(user_id)
        return features.get('ftm_mode', False)

    async def can_use_ftm_alpha_mode(self, user_id):
        """Check if user can use FTM Alpha mode (Pro plan only)"""
        features = await self.get_user_plan_features(user_id)
        return features.get('ftm_alpha_mode', False)
    
    async def get_forwarding_limit(self, user_id):
        """Get user's daily forwarding limit"""
        features = await self.get_user_plan_features(user_id)
        return features.get('forwarding_limit', 5)
    
    async def has_priority_support(self, user_id):
        """Check if user has priority support"""
        features = await self.get_user_plan_features(user_id)
        return features.get('priority_support', False)

    async def get_premium_user_details(self, user_id):
        """Get premium user details"""
        return await self.premium_col.find_one({'user_id': int(user_id)})
    
    async def get_premium_info(self, user_id):
        """Get premium user info (alias for get_premium_user_details)"""
        return await self.get_premium_user_details(user_id)
    
    async def get_user_usage(self, user_id):
        """Get user's total usage count"""
        daily_usage = await self.get_daily_usage(user_id)
        return daily_usage.get('processes', 0)
    
    async def get_days_remaining(self, user_id):
        """Get days remaining for premium subscription"""
        premium_info = await self.get_premium_user_details(user_id)
        if premium_info and premium_info.get('expires_at'):
            from datetime import datetime
            expires_at = premium_info['expires_at']
            if isinstance(expires_at, datetime):
                days_remaining = max(0, (expires_at - datetime.utcnow()).days)
                return days_remaining
        return 0
    
    async def get_monthly_usage(self, user_id):
        """Get user's usage for current month"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        usage = await self.usage_col.find_one({
            'user_id': int(user_id),
            'date': start_of_month
        })
        return usage if usage else {'user_id': int(user_id), 'date': start_of_month, 'processes': 0, 'trial_processes': 0}

    async def add_trial_processes(self, user_id, additional_processes=1):
        """Add trial processes to user's monthly limit"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Check if trial already activated this month
        existing = await self.usage_col.find_one({
            'user_id': int(user_id), 
            'date': start_of_month,
            'trial_activated': True
        })
        
        if existing:
            return False  # Trial already claimed this month
            
        await self.usage_col.update_one(
            {'user_id': int(user_id), 'date': start_of_month},
            {
                '$set': {
                    'trial_processes': additional_processes, 
                    'trial_activated': True, 
                    'trial_granted_at': datetime.utcnow()
                },
                '$setOnInsert': {'processes': 0}
            },
            upsert=True
        )
        return True  # Trial successfully granted

    async def get_trial_status(self, user_id):
        """Get user's trial status - whether they have used their free trial"""
        monthly_usage = await self.get_monthly_usage(user_id)
        return {
            'used': monthly_usage.get('trial_activated', False),
            'trial_processes': monthly_usage.get('trial_processes', 0),
            'granted_at': monthly_usage.get('trial_granted_at')
        }

    async def get_alpha_config(self, user_id):
        """Get FTM Alpha mode configuration for user"""
        configs = await self.get_configs(user_id)
        return {
            'enabled': configs.get('ftm_alpha_mode', False),
            'source_chat': configs.get('alpha_source_chat'),
            'target_chat': configs.get('alpha_target_chat')
        }

    async def set_alpha_config(self, user_id, source_chat=None, target_chat=None, enabled=None):
        """Set FTM Alpha mode configuration"""
        current_config = await self.get_configs(user_id)
        
        if source_chat is not None:
            current_config['alpha_source_chat'] = source_chat
        if target_chat is not None:
            current_config['alpha_target_chat'] = target_chat
        if enabled is not None:
            current_config['ftm_alpha_mode'] = enabled
            
        await self.update_configs(user_id, current_config)
        return True

    async def validate_alpha_permissions(self, user_id, bot_client, source_chat, target_chat):
        """Validate if bot is admin in both source and target chats for Alpha mode"""
        try:
            # Check source chat permissions
            source_member = await bot_client.get_chat_member(source_chat, bot_client.me.id)
            if source_member.status not in ['administrator', 'creator']:
                return False, "Bot is not admin in source channel"
            
            # Check target chat permissions
            target_member = await bot_client.get_chat_member(target_chat, bot_client.me.id)
            if target_member.status not in ['administrator', 'creator']:
                return False, "Bot is not admin in target channel"
                
            return True, "Bot has admin permissions in both channels"
        except Exception as e:
            return False, f"Permission check failed: {str(e)}"

    async def get_all_alpha_users(self):
        """Get all users with active Alpha mode for real-time processing"""
        pipeline = [
            {'$match': {'configs.ftm_alpha_mode': True}},
            {'$project': {
                'user_id': '$id',
                'source_chat': '$configs.alpha_source_chat',
                'target_chat': '$configs.alpha_target_chat'
            }}
        ]
        return await self.col.aggregate(pipeline).to_list(length=1000)

    async def get_user_process_limit(self, user_id):
        """Get user's total process limit including trials"""
        base_limit = await self.get_forwarding_limit(user_id)
        if base_limit == -1:  # Premium user
            return -1
        
        # Check for trial processes
        monthly_usage = await self.get_monthly_usage(user_id)
        trial_processes = monthly_usage.get('trial_processes', 0)
        return base_limit + trial_processes

    async def get_all_premium_users(self):
        """Get all premium users"""
        return await self.premium_col.find({'is_active': True}).to_list(length=1000)

    async def cleanup_expired_premium(self):
        """Remove expired premium subscriptions"""
        result = await self.premium_col.update_many(
            {'expires_at': {'$lt': datetime.utcnow()}},
            {'$set': {'is_active': False}}
        )
        return result.modified_count

    # Payment verification system
    async def submit_payment_verification(self, user_id, screenshot_file_id, plan_type='pro', duration_days=30, amount=None):
        """Submit payment verification with plan support"""
        verification_data = {
            'user_id': int(user_id),
            'screenshot_file_id': screenshot_file_id,
            'plan_type': plan_type,
            'duration_days': duration_days,
            'amount': amount,
            'payment_method': '6354228145@axl',
            'submitted_at': datetime.utcnow(),
            'status': 'pending',  # pending, approved, rejected
            'reviewed_by': None,
            'reviewed_at': None,
            'review_notes': None
        }
        result = await self.payment_col.insert_one(verification_data)
        return result.inserted_id

    async def get_pending_verifications(self):
        """Get all pending payment verifications"""
        return await self.payment_col.find({'status': 'pending'}).to_list(length=100)

    async def approve_payment(self, verification_id, admin_id, notes=None):
        """Approve payment verification"""
        result = await self.payment_col.update_one(
            {'_id': verification_id},
            {
                '$set': {
                    'status': 'approved',
                    'reviewed_by': int(admin_id),
                    'reviewed_at': datetime.utcnow(),
                    'review_notes': notes
                }
            }
        )
        
        # Get the verification to add premium subscription
        verification = await self.payment_col.find_one({'_id': verification_id})
        if verification and result.modified_count > 0:
            # Add premium subscription based on plan and duration
            await self.add_premium_user(
                verification['user_id'], 
                verification.get('plan_type', 'pro'),
                verification.get('duration_days', 30),
                verification.get('amount')
            )
        
        return result.modified_count > 0

    async def reject_payment(self, verification_id, admin_id, notes=None):
        """Reject payment verification"""
        result = await self.payment_col.update_one(
            {'_id': verification_id},
            {
                '$set': {
                    'status': 'rejected',
                    'reviewed_by': int(admin_id),
                    'reviewed_at': datetime.utcnow(),
                    'review_notes': notes or 'Payment verification rejected'
                }
            }
        )
        return result.modified_count > 0

    async def get_verification_by_id(self, verification_id):
        """Get verification details by ID"""
        return await self.payment_col.find_one({'_id': verification_id})

    # Usage tracking for daily limits
    async def get_daily_usage(self, user_id):
        """Get user's usage for current day"""
        start_of_day = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        usage = await self.usage_col.find_one({
            'user_id': int(user_id),
            'date': start_of_day
        })
        return usage if usage else {'user_id': int(user_id), 'date': start_of_day, 'processes': 0}

    async def increment_usage(self, user_id):
        """Increment user's monthly usage"""
        start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        await self.usage_col.update_one(
            {'user_id': int(user_id), 'date': start_of_month},
            {
                '$inc': {'processes': 1},
                '$set': {'last_used': datetime.utcnow()}
            },
            upsert=True
        )

    async def can_user_process(self, user_id):
        """Check if user can process based on their plan (including trial processes)"""
        # Get user's total forwarding limit (including trial processes)
        limit = await self.get_user_process_limit(user_id)
        
        # Unlimited for premium plans (Plus and Pro)
        if limit == -1:
            return True, "unlimited"
        
        # Check monthly usage for free users
        usage = await self.get_monthly_usage(user_id)
        if usage['processes'] >= limit:
            return False, "monthly_limit_reached"
        
        return True, "allowed"
    
    # Force subscribe functionality
    async def check_force_subscribe(self, user_id, client):
        """Check if user is subscribed to all required channels"""
        from config import Config
        
        try:
            subscription_results = {}
            all_subscribed = True
            
            for channel in Config.FORCE_SUBSCRIBE_CHANNELS:
                subscribed = False
                channel_key = channel['username']
                
                # Check subscription using username first (more reliable)
                try:
                    member = await client.get_chat_member(f"@{channel['username']}", user_id)
                    subscribed = member.status not in ['left', 'kicked']
                    print(f"{channel['display_name']} check: {subscribed} for user {user_id}")
                except Exception as e:
                    print(f"Error checking {channel['display_name']} with username: {e}")
                    # Fallback to ID if username fails
                    try:
                        member = await client.get_chat_member(channel['id'], user_id)
                        subscribed = member.status not in ['left', 'kicked']
                        print(f"{channel['display_name']} check (ID fallback): {subscribed} for user {user_id}")
                    except Exception as id_error:
                        print(f"Error checking {channel['display_name']} with ID: {id_error}")
                        subscribed = False
                
                subscription_results[channel_key] = subscribed
                if not subscribed:
                    all_subscribed = False
            
            result = {
                **subscription_results,
                'all_subscribed': all_subscribed,
                'missing_channels': [
                    channel['display_name'] for channel in Config.FORCE_SUBSCRIBE_CHANNELS 
                    if not subscription_results.get(channel['username'], False)
                ]
            }
            
            print(f"Subscription check result for user {user_id}: {result}")
            return result
            
        except Exception as e:
            print(f"Force subscribe check error: {e}")
            # If there's an error checking, assume not subscribed
            default_result = {channel['username']: False for channel in Config.FORCE_SUBSCRIBE_CHANNELS}
            default_result.update({
                'all_subscribed': False,
                'missing_channels': [channel['display_name'] for channel in Config.FORCE_SUBSCRIBE_CHANNELS]
            })
            return default_result

    # Admin chat sessions
    async def start_admin_chat(self, admin_id, target_user_id):
        """Start admin chat session with user"""
        chat_data = {
            'admin_id': int(admin_id),
            'target_user_id': int(target_user_id),
            'started_at': datetime.utcnow(),
            'is_active': True,
            'messages': []
        }
        
        # End any existing chat session for this admin
        await self.admin_chat_col.update_many(
            {'admin_id': int(admin_id), 'is_active': True},
            {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
        )
        
        result = await self.admin_chat_col.insert_one(chat_data)
        return result.inserted_id

    async def get_active_admin_chat(self, admin_id):
        """Get active admin chat session"""
        return await self.admin_chat_col.find_one({
            'admin_id': int(admin_id),
            'is_active': True
        })

    async def end_admin_chat(self, admin_id):
        """End admin chat session"""
        return await self.admin_chat_col.update_many(
            {'admin_id': int(admin_id), 'is_active': True},
            {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
        )

    async def add_chat_message(self, session_id, from_admin, message_text):
        """Add message to admin chat session"""
        message_data = {
            'from_admin': from_admin,
            'message': message_text,
            'timestamp': datetime.utcnow()
        }
        return await self.admin_chat_col.update_one(
            {'_id': session_id},
            {'$push': {'messages': message_data}}
        )

    async def get_active_chat_for_user(self, user_id):
        """Get active admin chat session for a specific user"""
        return await self.admin_chat_col.find_one({
            'target_user_id': int(user_id),
            'is_active': True
        })
        
    async def get_active_admin_chat(self, admin_id):
        """Get active admin chat session for a specific admin"""
        return await self.admin_chat_col.find_one({
            'admin_id': int(admin_id),
            'is_active': True
        })
    
    # Contact requests methods
    async def create_contact_request(self, user_id):
        """Create a new contact request"""
        contact_data = {
            'user_id': int(user_id),
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'reviewed_at': None,
            'reviewed_by': None
        }
        
        result = await self.contact_requests_col.insert_one(contact_data)
        return result.inserted_id
        
    async def create_chat_request(self, user_id):
        """Create a new chat request"""
        chat_data = {
            'user_id': int(user_id),
            'status': 'pending',
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(hours=24),  # Auto-expire after 24 hours
            'reviewed_at': None,
            'reviewed_by': None,
            'notifications': []  # Store notification message IDs for cleanup
        }
        
        result = await self.chat_requests_col.insert_one(chat_data)
        return result.inserted_id
        
    async def get_pending_chat_request(self, user_id):
        """Get pending chat request for user"""
        return await self.chat_requests_col.find_one({
            'user_id': int(user_id),
            'status': 'pending'
        })
        
    async def get_chat_request_by_id(self, request_id):
        """Get chat request by ID"""
        return await self.chat_requests_col.find_one({
            '_id': ObjectId(request_id)
        })
        
    async def update_chat_request_status(self, request_id, status, admin_id=None):
        """Update chat request status"""
        update_data = {
            'status': status,
            'reviewed_at': datetime.utcnow()
        }
        if admin_id:
            update_data['reviewed_by'] = int(admin_id)
            
        return await self.chat_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': update_data}
        )
        
    async def store_chat_notifications(self, request_id, notification_messages):
        """Store notification message IDs for cleanup"""
        return await self.chat_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {'$set': {'notifications': notification_messages}}
        )
        
    async def cleanup_chat_notifications(self, request_id, client, accepting_admin_id):
        """Delete notifications from all other admins when one admin accepts"""
        try:
            # Get the request to find notification messages
            request = await self.get_chat_request_by_id(request_id)
            if not request or 'notifications' not in request:
                return
            
            # Delete messages from all admins except the one who accepted
            for notification in request['notifications']:
                if notification['admin_id'] != accepting_admin_id:
                    try:
                        await client.delete_messages(
                            chat_id=notification['admin_id'],
                            message_ids=notification['message_id']
                        )
                    except Exception as e:
                        print(f"Failed to delete notification for admin {notification['admin_id']}: {e}")
        except Exception as e:
            print(f"Error cleaning up notifications: {e}")
            
    async def cleanup_expired_chat_requests(self):
        """Remove chat requests and data older than 24 hours"""
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        # Find expired requests
        expired_requests = self.chat_requests_col.find({
            'created_at': {'$lt': cutoff_time}
        })
        
        # Also cleanup any active chat sessions from expired requests
        async for request in expired_requests:
            if request.get('status') == 'accepted':
                # End any active chat sessions
                await self.admin_chat_col.update_many(
                    {'target_user_id': request['user_id'], 'is_active': True},
                    {'$set': {'is_active': False, 'ended_at': datetime.utcnow()}}
                )
        
        # Delete expired chat requests
        result = await self.chat_requests_col.delete_many({
            'created_at': {'$lt': cutoff_time}
        })
        
        return result.deleted_count

    async def get_pending_contact_request(self, user_id):
        """Get pending contact request for user"""
        return await self.contact_requests_col.find_one({
            'user_id': int(user_id),
            'status': 'pending'
        })

    async def get_contact_request_by_id(self, request_id):
        """Get contact request by ID"""
        return await self.contact_requests_col.find_one({
            '_id': ObjectId(request_id)
        })

    async def update_contact_request_status(self, request_id, status):
        """Update contact request status"""
        return await self.contact_requests_col.update_one(
            {'_id': ObjectId(request_id)},
            {
                '$set': {
                    'status': status,
                    'reviewed_at': datetime.utcnow()
                }
            }
        )

db = Database(Config.DATABASE_URI, Config.DATABASE_NAME)
