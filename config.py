from os import environ 

class Config:
    API_ID = environ.get("API_ID", "28776072")
    API_HASH = environ.get("API_HASH", "b3a786dce1f4e7d56674b7cadfde3c9d")
    BOT_TOKEN = environ.get("BOT_TOKEN", "8101859818:AAFGgME2zDxkcyKSfnDOGd0UhLacq0gvBzY") 
    BOT_SESSION = environ.get("BOT_SESSION", "forward-bot") 
    DATABASE_URI = environ.get("DATABASE", "mongodb+srv://xchetan:xchetan@cluster0.kmqg03h.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME = environ.get("DATABASE_NAME", "forwrd-botzx")
    OWNER_ID = [int(id) for id in environ.get("OWNER_ID", '7744665378').split()]
    ADMIN_ID = [int(id) for id in environ.get("ADMIN_ID", '7966880099').split() if id.strip()]
    LOG_CHANNEL_ID = int(environ.get("LOG_CHANNEL_ID", "-1003003594014"))
    
    # Multiple force subscribed channels support
    # Format: channel_username:channel_id:channel_url:display_name
    FORCE_SUBSCRIBE_CHANNELS = [
        {
            'username': 'ftmbotzx',
            'id': int(environ.get("UPDATE_CHANNEL_ID", "-1002200226545")),
            'url': "https://t.me/+tgPf04FXMOllMWVl",
            'display_name': 'Update Channel',
            'button_text': '🤖 Join Main Channel'
        }
        # Add more channels here as needed
        # {
        #     'username': 'your_third_channel',
        #     'id': -1002345678902,
        #     'url': "https://t.me/your_third_channel",
        #     'display_name': 'Third Channel',
        #     'button_text': '📺 Join Third Channel'
        # },
        # {
        #     'username': 'your_fourth_channel',
        #     'id': -1002345678903,
        #     'url': "https://t.me/your_fourth_channel", 
        #     'display_name': 'Fourth Channel',
        #     'button_text': '🎬 Join Fourth Channel'
        # }
        # ... add up to 10 or more channels as needed
    ]
    
    # Backward compatibility
    UPDATE_CHANNEL = FORCE_SUBSCRIBE_CHANNELS[0]['url']
    SUPPORT_GROUP = FORCE_SUBSCRIBE_CHANNELS[1]['url']
    UPDATE_CHANNEL_USERNAME = FORCE_SUBSCRIBE_CHANNELS[0]['username']
    SUPPORT_GROUP_USERNAME = FORCE_SUBSCRIBE_CHANNELS[1]['username']
    UPDATE_CHANNEL_ID = FORCE_SUBSCRIBE_CHANNELS[0]['id']
    SUPPORT_GROUP_ID = FORCE_SUBSCRIBE_CHANNELS[1]['id']
    
    # Three-tier pricing structure
    PLAN_PRICING = {
        'plus': {
            '15_days': 199,
            '30_days': 299
        },
        'pro': {
            '15_days': 299,
            '30_days': 549
        }
    }
    
    # Plan features
    PLAN_FEATURES = {
        'free': {
            'forwarding_limit': 1,  # per month
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': False
        },
        'plus': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': False,
            'priority_support': False,
            'unlimited_forwarding': True
        },
        'pro': {
            'forwarding_limit': -1,  # unlimited
            'ftm_mode': True,  # FTM Delta mode
            'ftm_alpha_mode': True,  # FTM Alpha mode - real-time auto-forwarding
            'priority_support': True,
            'unlimited_forwarding': True
        }
    }
    
    @staticmethod
    def is_sudo_user(user_id):
        """Check if user is sudo (owner or admin)"""
        return int(user_id) in Config.OWNER_ID or int(user_id) in Config.ADMIN_ID

class temp(object): 
    lock = {}
    CANCEL = {}
    forwardings = 0
    BANNED_USERS = []
    IS_FRWD_CHAT = []
    CURRENT_PROCESSES = {}  # Track ongoing processes per user
    
