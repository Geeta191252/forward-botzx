from os import environ 

class Config:
    API_ID = environ.get("API_ID", "28776072")
    API_HASH = environ.get("API_HASH", "b3a786dce1f4e7d56674b7cadfde3c9d")
    BOT_TOKEN = environ.get("BOT_TOKEN", "8101859818:AAFGgME2zDxkcyKSfnDOGd0UhLacq0gvBzY") 
    BOT_SESSION = environ.get("BOT_SESSION", "forward-bot") 
    DATABASE_URI = environ.get("DATABASE", "mongodb+srv://ftm:ftm@cluster0.9a4gw2t.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
    DATABASE_NAME = environ.get("DATABASE_NAME", "forward-bot")
    OWNER_ID = [int(id) for id in environ.get("OWNER_ID", '7744665378').split()]
    ADMIN_ID = [int(id) for id in environ.get("ADMIN_ID", '7966880099').split() if id.strip()]
    LOG_CHANNEL_ID = int(environ.get("LOG_CHANNEL_ID", "-1003003594014"))
    
    # Updated channel and group URLs
    UPDATE_CHANNEL = "https://t.me/ftmbotzx"
    SUPPORT_GROUP = "https://t.me/ftmbotzx_support"
    # Note: Use actual channel usernames instead of hardcoded IDs for better reliability
    UPDATE_CHANNEL_USERNAME = "ftmbotzx"  # Channel username without @
    SUPPORT_GROUP_USERNAME = "ftmbotzx_support"  # Group username without @
    UPDATE_CHANNEL_ID = int(environ.get("UPDATE_CHANNEL_ID", "-1002346789012"))  # Update channel ID for @ftmbotzx  
    SUPPORT_GROUP_ID = int(environ.get("SUPPORT_GROUP_ID", "-1002345678901"))   # Support group ID for @ftmbotzx_support
    
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
    
