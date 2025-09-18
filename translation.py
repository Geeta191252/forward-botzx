import os
from config import Config

class Translation(object):
  START_TXT = """<b>ʜᴇʟʟᴏ {}</b>

<i>ɪ'ᴍ ᴀ <b>ᴘᴏᴡᴇʀғᴜʟʟ</b> ᴀᴜᴛᴏ ғᴏʀᴡᴀʀᴅ ʙᴏᴛ

ɪ ᴄᴀɴ ғᴏʀᴡᴀʀᴅ ᴀʟʟ ᴍᴇssᴀɢᴇ ғʀᴏᴍ ᴏɴᴇ ᴄʜᴀɴɴᴇʟ ᴛᴏ ᴀɴᴏᴛʜᴇʀ ᴄʜᴀɴɴᴇʟ</i> <b>➜ ᴡɪᴛʜ ᴍᴏʀᴇ ғᴇᴀᴛᴜʀᴇs.
ᴄʟɪᴄᴋ ʜᴇʟᴘ ʙᴜᴛᴛᴏɴ ᴛᴏ ᴋɴᴏᴡ ᴍᴏʀᴇ ᴀʙᴏᴜᴛ ᴍᴇ</b>"""


  HELP_TXT = """<b><u>🔆 HELP</b></u>

<u>**📚 Available commands:**</u>
<b>⏣ __/start - check I'm alive__ 
⏣ __/forward - forward messages__
⏣ __/settings - configure your settings__
⏣ __/reset - reset your settings__
⏣ __/speedtest - network speed test (admin only)__
⏣ __/system - system information (admin only)__</b>

<b><u>💢 Features:</b></u>
<b>► __Forward message from public channel to your channel without admin permission. if the channel is private need admin permission__
► __Forward message from private channel to your channel by using userbot(user must be member in there)__
► __custom caption__
► __custom button__
► __support restricted chats__
► __skip duplicate messages__
► __filter type of messages__
► __skip messages based on extensions & keywords & size__
► __FTM Delta Mode with source link tracking__
► __FTM Alpha Mode for real-time auto-forwarding (Pro only)__
► __Real-time network speed testing__
► __Detailed system monitoring__</b>
"""
  
  HOW_USE_TXT = """<b><u>⚠️ Before Forwarding:</b></u>
<b>► __add a bot or userbot__
► __add atleast one to channel__ `(your bot/userbot must be admin in there)`
► __You can add chats or bots by using /settings__
► __if the **From Channel** is private your userbot must be member in there or your bot must need admin permission in there also__
► __Then use /forward to forward messages__</b>"""
  
  ABOUT_TXT = """<b>╭──────❰ 🤖 Bot Details ❱──────〄
│ 
│ 🤖 Mʏ Nᴀᴍᴇ : <a href=https://t.me/Auto_Forward3_Bot>Auto 𝙵𝙾𝚁𝚆𝙰𝚁𝙳 𝙱𝙾𝚃</a>
│ 👨‍💻 ᴅᴇᴠᴘʟᴏᴇʀ : <a href=https://t.me/Hidden_Xman>Hidden Xman</a>
│ 🤖 ᴜᴘᴅᴀᴛᴇ  : <a href=https://t.me/Hidden_Xman>Hidden Xman</a>
│ 📡 ʜᴏsᴛ ᴏɴ : <a href=https://heroku.com.in/>𝙷𝙴𝚁𝙾𝙺𝚄</a>
│ 🗣️ ʟᴀɴɢᴜᴀɢᴇ  : ᴘʏᴛʜᴏɴ 3 {python_version}
│ 📚 ʟɪʙʀᴀʀʏ  : ᴘʏʀᴏɢʀᴀᴍ  
╰────────────────────⍟</b>"""
  
  STATUS_TXT = """<b>╭──────❪ 🤖 Bot Status ❫─────⍟
│
├👨 ᴜsᴇʀs  : {}
│
├🤖 ʙᴏᴛs : {}
│
├📣 ᴄʜᴀɴɴᴇʟ  : {} 
╰───────────────────⍟</b>""" 
  
  FROM_MSG = "<b>❪ SET SOURCE CHAT ❫\n\nForward the last message or last message link of source chat.\n/cancel - cancel this process</b>"
  TO_MSG = "<b>❪ CHOOSE TARGET CHAT ❫\n\nChoose your target chat from the given buttons.\n/cancel - Cancel this process</b>"
  SKIP_MSG = "<b>❪ SET MESSAGE SKIPING NUMBER ❫</b>\n\n<b>Skip the message as much as you enter the number and the rest of the message will be forwarded\nDefault Skip Number =</b> <code>0</code>\n<code>eg: You enter 0 = 0 message skiped\n You enter 5 = 5 message skiped</code>\n/cancel <b>- cancel this process</b>"
  CANCEL = "<b>Process Cancelled Succefully !</b>"
  BOT_DETAILS = "<b><u>📄 BOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ BOT ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"
  USER_DETAILS = "<b><u>📄 USERBOT DETAILS</b></u>\n\n<b>➣ NAME:</b> <code>{}</code>\n<b>➣ USER ID:</b> <code>{}</code>\n<b>➣ USERNAME:</b> @{}"  
         
  TEXT = """<b>╭────❰ <u>Forwarded Status</u> ❱────❍
┃
┣⊸<b>📋 ᴛᴏᴛᴀʟ ᴍsɢs :</b> <code>{}</code>
┣⊸<b>🕵 ғᴇᴛᴄʜᴇᴅ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>✅ sᴜᴄᴄᴇғᴜʟʟʏ ғᴡᴅ :</b> <code>{}</code>
┣⊸<b>👥 ᴅᴜᴘʟɪᴄᴀᴛᴇ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>🗑️ ᴅᴇʟᴇᴛᴇᴅ/ғɪʟᴛᴇʀᴇᴅ :</b> <code>{}</code>
┣⊸<b>🪆 sᴋɪᴘᴘᴇᴅ ᴍsɢ :</b> <code>{}</code>
┣⊸<b>📊 sᴛᴀᴛᴜs :</b> <code>{}</code>
┣⊸<b>⏳ ᴘʀᴏɢʀᴇss :</b> <code>{}</code> %
┣⊸<b>⏰ ᴇᴛᴀ :</b> <code>{}</code>
┃
╰────⌊ <b>{}</b> ⌉───❍</b>"""

  TEXT1 = """<b>╭─❰ <u>Forwarded Status</u> ❱─❍
┃
┣⊸🕵𝙁𝙚𝙘𝙝𝙚𝙙 𝙈𝙨𝙜 : {}
┣⊸✅𝙎𝙪𝙘𝙘𝙚𝙛𝙪𝙡𝙮 𝙁𝙬𝙙 : {}
┣⊸👥𝘿𝙪𝙥𝙡𝙞𝙘𝙖𝙩𝙚 𝙈𝙨𝙜: {}
┣⊸🗑𝘿𝙚𝙡𝙚𝙩𝙚𝙙 𝙈𝙨𝙜: {}
┣⊸🪆𝙎𝙠𝙞𝙥𝙥𝙚𝙙 : {}
┣⊸📊𝙎𝙩𝙖𝙩𝙨 : {}
┣⊸⏳𝙋𝙧𝙤𝙜𝙧𝙚𝙨𝙨 : {}
┣⊸𝙀𝙏𝘼 : {}
┃
╰─⌊ {} ⌉─❍</b>"""

  DOUBLE_CHECK = """<b><u>DOUBLE CHECKING ⚠️</b></u>
<code>Before forwarding the messages Click the Yes button only after checking the following</code>

<b>★ YOUR BOT:</b> [{botname}](t.me/{botuname})
<b>★ FROM CHANNEL:</b> `{from_chat}`
<b>★ TO CHANNEL:</b> `{to_chat}`
<b>★ SKIP MESSAGES:</b> `{skip}`

<i>° [{botname}](t.me/{botuname}) must be admin in **TARGET CHAT**</i> (`{to_chat}`)
<i>° If the **SOURCE CHAT** is private your userbot must be member or your bot must be admin in there also</b></i>

<b>If the above is checked then the yes button can be clicked</b>"""

  # Premium System Messages
  PREMIUM_LIMIT_MSG = """<b>🚫 Monthly Limit Reached!</b>

<b>Free users are limited to 1 process per month.</b>

<b>💎 Upgrade to Premium for unlimited access!</b>
• <b>Price:</b> ₹200/month
• <b>Payment:</b> 8504021912@slc
• <b>Benefits:</b> Unlimited forwarding

<b>How to upgrade:</b>
1. Send ₹200 to <code>8504021912@slc</code>
2. Take screenshot of payment
3. Send screenshot with <code>/verify</code>
4. Wait for admin approval

<b>Your current usage:</b> 1/1 processes used this month
<b>Next reset:</b> 1st of next month"""

  VERIFY_USAGE_MSG = """<b>❌ Invalid Usage!</b>

<b>Please reply to your payment screenshot with /verify command.</b>

<b>Example:</b>
1. Send your payment screenshot
2. Reply to that screenshot with <code>/verify</code>"""

  VERIFY_SUCCESS_MSG = """<b>✅ Payment Screenshot Submitted!</b>

<b>Your payment verification has been submitted to admins for review.</b>

<b>⏳ Please wait for admin approval.</b>
<b>💬 You will be notified once your payment is verified.</b>

<b>Verification ID:</b> <code>{verification_id}</code>"""

  PAYMENT_APPROVED_MSG = """<b>🎉 Payment Approved!</b>

<b>✅ Your payment has been verified and approved!</b>
<b>💎 You now have Premium access for 30 days.</b>

<b>Premium Benefits:</b>
• Unlimited forwarding processes
• Priority support
• All premium features unlocked

<b>Use /myplan to check your subscription details.</b>"""

  PAYMENT_REJECTED_MSG = """<b>❌ Payment Rejected</b>

<b>Your payment verification has been rejected.</b>

<b>Possible reasons:</b>
• Invalid payment screenshot
• Incorrect amount
• Payment not found
• Duplicate submission

<b>Please verify your payment and submit again with /verify</b>
<b>Or contact support for assistance.</b>"""

  PREMIUM_GRANTED_MSG = """<b>🎉 Premium Access Granted!</b>

<b>✅ You have been granted Premium access for {days} days!</b>
<b>💎 Granted by: {admin_name}</b>

<b>Premium Benefits:</b>
• Unlimited forwarding processes
• Priority support
• All premium features unlocked

<b>Expires:</b> {expires_date} UTC
<b>Use /myplan to check your subscription details.</b>"""

  PREMIUM_REMOVED_MSG = """<b>❌ Premium Access Removed</b>

<b>Your premium access has been removed by an admin.</b>
<b>Removed by:</b> {admin_name}

<b>You are now on the free plan with monthly limits.</b>
<b>💎 To get premium again, use /plan to see available plans</b>"""

  PLAN_INFO_MSG = """<b>💎 Premium Plans</b>

<b>🆓 Free Plan</b>
• 1 forwarding process per month
• Basic support
• Standard features

<b>💎 Premium Plan - ₹200/month</b>
• ✅ Unlimited forwarding processes
• ✅ Priority support
• ✅ All premium features
• ✅ No monthly limits
• ✅ Advanced customization options

<b>💳 How to Subscribe:</b>
1. Send ₹200 to <code>8504021912@slc</code>
2. Take screenshot of payment confirmation
3. Send screenshot with <code>/verify</code> command
4. Wait for admin approval (usually within 24 hours)

<b>💡 Tips:</b>
• Include your username in payment reference
• Keep payment screenshot clear and complete
• Contact support if you need help

<b>📊 Check your current plan with /myplan</b>"""

  CHAT_STARTED_MSG = """<b>💬 Chat Session Started</b>

<b>Target User:</b> {user_info}
<b>User ID:</b> <code>{user_id}</code>
<b>Session ID:</b> <code>{session_id}</code>

<b>💡 Now send any message and it will be forwarded to the user.</b>
<b>🔚 Use /endchat to end the session.</b>"""

  ADMIN_CHAT_NOTIFY_MSG = """<b>💬 Admin Chat Session</b>

<b>An admin has started a chat session with you.</b>
<b>Admin:</b> {admin_name}

<b>You can now chat directly with the admin!</b>"""
