import os
import asyncio
from datetime import datetime, timedelta
from bson import ObjectId
from database import db
from config import Config
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message

# Purchase plan callback handlers
@Client.on_callback_query(filters.regex(r'^buy_(plus|pro)_(15|30)$'))
async def buy_plan_callback(client, callback_query):
    user_id = callback_query.from_user.id
    data_parts = callback_query.data.split('_')
    plan_type = data_parts[1]  # plus or pro
    duration = int(data_parts[2])  # 15 or 30
    
    # Get pricing
    from config import Config
    amount = Config.PLAN_PRICING[plan_type][f'{duration}_days']
    
    purchase_text = (
        f"💳 <b>Purchase {plan_type.upper()} Plan</b>\n\n"
        f"📦 <b>Plan:</b> {plan_type.upper()}\n"
        f"⏰ <b>Duration:</b> {duration} days\n"
        f"💰 <b>Amount:</b> ₹{amount}\n\n"
        f"<b>💵 Payment Instructions:</b>\n"
        f"1. Send ₹{amount} to UPI: <code>6354228145@axl</code>\n"
        f"2. Take a screenshot of the payment\n"
        f"3. Send the screenshot to this bot\n"
        f"4. Reply to the screenshot with: <code>/verify {plan_type} {duration}</code>\n\n"
        f"<b>⚠️ Important:</b>\n"
        f"• Pay exact amount: ₹{amount}\n"
        f"• Include payment reference in screenshot\n"
        f"• Verification usually takes 5-10 minutes"
    )
    
    buttons = [
        [
            InlineKeyboardButton("📋 Copy UPI ID", callback_data="copy_upi"),
            InlineKeyboardButton("💬 Contact Support", callback_data="contact_admin")
        ],
        [
            InlineKeyboardButton("🔙 Back to Plans", callback_data="premium_plans")
        ]
    ]
    
    await callback_query.message.edit_text(
        text=purchase_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# /verify command for payment screenshot submission
@Client.on_message(filters.private & filters.command(['verify']))
async def verify_payment(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    
    # Parse command arguments
    command_parts = message.text.split()
    plan_type = 'pro'
    duration = 30
    
    if len(command_parts) >= 3:
        plan_type = command_parts[1].lower()
        try:
            duration = int(command_parts[2])
        except:
            duration = 30
    
    if not message.reply_to_message or not message.reply_to_message.photo:
        return await message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Please reply to your payment screenshot with /verify command.</b>\n\n"
            "<b>Examples:</b>\n"
            "• <code>/verify pro 30</code> (for Pro 30 days)\n"
            "• <code>/verify plus 15</code> (for Plus 15 days)\n"
            "• <code>/verify</code> (defaults to Pro 30 days)\n\n"
            "<b>Steps:</b>\n"
            "1. Send your payment screenshot\n"
            "2. Reply to that screenshot with the verify command"
        )
    
    # Get the screenshot
    photo = message.reply_to_message.photo
    screenshot_file_id = photo.file_id
    
    # Validate plan and get amount
    from config import Config
    if plan_type not in ['plus', 'pro']:
        return await message.reply_text("❌ Invalid plan type. Use 'plus' or 'pro'")
    
    if duration not in [15, 30]:
        return await message.reply_text("❌ Invalid duration. Use 15 or 30 days")
    
    amount = Config.PLAN_PRICING[plan_type][f'{duration}_days']
    
    try:
        # Submit payment verification
        verification_id = await db.submit_payment_verification(
            user_id, screenshot_file_id, plan_type, duration, amount
        )
        
        await message.reply_text(
            "<b>✅ Payment Screenshot Submitted!</b>\n\n"
            f"<b>Plan:</b> {plan_type.upper()}\n"
            f"<b>Duration:</b> {duration} days\n"
            f"<b>Amount:</b> ₹{amount}\n\n"
            "<b>Your payment verification has been submitted to admins for review.</b>\n\n"
            "<b>⏳ Please wait for admin approval.</b>\n"
            "<b>💬 You will be notified once your payment is verified.</b>\n\n"
            f"<b>Verification ID:</b> <code>{verification_id}</code>"
        )
        
        # Notify sudo users about new payment verification
        sudo_users = Config.OWNER_ID + Config.ADMIN_ID
        for sudo_id in sudo_users:
            try:
                buttons = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve_payment_{verification_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject_payment_{verification_id}")
                    ],
                    [
                        InlineKeyboardButton("💬 Chat with User", callback_data=f"chat_user_{user_id}")
                    ]
                ]
                
                await client.send_photo(
                    sudo_id,
                    screenshot_file_id,
                    caption=f"<b>💰 New Payment Verification</b>\n\n"
                            f"<b>User:</b> {user_name} (<code>{user_id}</code>)\n"
                            f"<b>Plan:</b> {plan_type.upper()}\n"
                            f"<b>Duration:</b> {duration} days\n"
                            f"<b>Amount:</b> ₹{amount}\n"
                            f"<b>Payment Method:</b> 6354228145@axl\n"
                            f"<b>Submitted:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                            f"<b>Verification ID:</b> <code>{verification_id}</code>",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
            except Exception as e:
                print(f"Failed to notify sudo user {sudo_id}: {e}")
                
    except Exception as e:
        await message.reply_text(
            f"<b>❌ Error submitting verification:</b>\n<code>{str(e)}</code>"
        )

# Payment approval/rejection callbacks
@Client.on_callback_query(filters.regex(r'^approve_payment_'))
async def approve_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    verification_id = ObjectId(callback_query.data.split("_")[2])
    
    try:
        # Get verification details
        verification = await db.get_verification_by_id(verification_id)
        if not verification:
            return await callback_query.answer("❌ Verification not found!", show_alert=True)
        
        if verification['status'] != 'pending':
            return await callback_query.answer(f"❌ Already {verification['status']}!", show_alert=True)
        
        # Approve payment
        success = await db.approve_payment(verification_id, user_id, "Payment approved by admin")
        
        if success:
            # Get verification details for plan info
            verification = await db.get_verification_by_id(verification_id)
            plan_type = verification.get('plan_type', 'pro').upper()
            duration = verification.get('duration_days', 30)
            amount = verification.get('amount', 0)
            
            # Update the admin message
            await callback_query.message.edit_caption(
                callback_query.message.caption + f"\n\n<b>✅ APPROVED by {callback_query.from_user.first_name}</b>",
                reply_markup=None
            )
            
            # Notify the user
            try:
                # Get plan features for display
                user_features = await db.get_user_plan_features(verification['user_id'])
                features_text = ""
                if user_features.get('unlimited_forwarding'):
                    features_text += "• Unlimited forwarding processes\n"
                if user_features.get('ftm_mode'):
                    features_text += "• FTM mode enabled\n"
                if user_features.get('priority_support'):
                    features_text += "• Priority support\n"
                
                await client.send_message(
                    verification['user_id'],
                    f"<b>🎉 Payment Approved!</b>\n\n"
                    f"<b>✅ Your payment has been verified and approved!</b>\n"
                    f"<b>💎 You now have {plan_type} plan for {duration} days.</b>\n"
                    f"<b>💰 Amount paid: ₹{amount}</b>\n\n"
                    f"<b>{plan_type} Plan Benefits:</b>\n"
                    f"{features_text}\n"
                    f"<b>Use /myplan to check your subscription details.</b>"
                )
            except:
                pass
            
            await callback_query.answer("✅ Payment approved successfully!", show_alert=True)
        else:
            await callback_query.answer("❌ Failed to approve payment!", show_alert=True)
            
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^reject_payment_'))
async def reject_payment_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    verification_id = ObjectId(callback_query.data.split("_")[2])
    
    try:
        # Get verification details
        verification = await db.get_verification_by_id(verification_id)
        if not verification:
            return await callback_query.answer("❌ Verification not found!", show_alert=True)
        
        if verification['status'] != 'pending':
            return await callback_query.answer(f"❌ Already {verification['status']}!", show_alert=True)
        
        # Reject payment
        success = await db.reject_payment(verification_id, user_id, "Payment rejected by admin")
        
        if success:
            # Update the admin message
            await callback_query.message.edit_caption(
                callback_query.message.caption + f"\n\n<b>❌ REJECTED by {callback_query.from_user.first_name}</b>",
                reply_markup=None
            )
            
            # Notify the user
            try:
                await client.send_message(
                    verification['user_id'],
                    "<b>❌ Payment Rejected</b>\n\n"
                    "<b>Your payment verification has been rejected.</b>\n\n"
                    "<b>Possible reasons:</b>\n"
                    "• Invalid payment screenshot\n"
                    "• Incorrect amount\n"
                    "• Payment not found\n"
                    "• Duplicate submission\n\n"
                    "<b>Please verify your payment and submit again with /verify</b>\n"
                    "<b>Or contact support for assistance.</b>"
                )
            except:
                pass
            
            await callback_query.answer("❌ Payment rejected!", show_alert=True)
        else:
            await callback_query.answer("❌ Failed to reject payment!", show_alert=True)
            
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

# /chat command for admins to chat with users

# End chat command
@Client.on_message(filters.private & filters.command(['endchat']))
async def end_chat_command(client, message):
    user_id = message.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    # End active chat session
    result = await db.end_admin_chat(user_id)
    
    if result.modified_count > 0:
        await message.reply_text("✅ Chat session ended successfully!")
    else:
        await message.reply_text("❌ No active chat session found!")

# Handle messages in admin chat sessions
@Client.on_message(filters.private & ~filters.command(['start', 'help', 'forward', 'fwd', 'settings', 'verify', 'chat', 'contact', 'endchat', 'add_premium', 'remove_premium', 'pusers', 'plan', 'myplan', 'chatuser']))
async def handle_chat_messages(client, message):
    user_id = message.from_user.id
    
    # Check if admin has active chat session
    if Config.is_sudo_user(user_id):
        chat_session = await db.get_active_admin_chat(user_id)
        if chat_session:
            target_user_id = chat_session['target_user_id']
            
            # Forward admin message to user
            try:
                await client.send_message(
                    target_user_id,
                    f"<b>👨‍💼 Admin:</b> {message.text or '[Media/File]'}"
                )
                
                # Log the message
                await db.add_chat_message(chat_session['_id'], True, message.text or '[Media/File]')
                
                # Confirm to admin
                await message.reply_text("✅ Message sent to user!")
                
            except Exception as e:
                await message.reply_text(f"❌ Failed to send message: {str(e)}")
            return
    
    # Check if user has an active chat session with an admin (user replying to admin)
    else:
        active_chat = await db.get_active_chat_for_user(user_id)
        if active_chat:
            admin_id = active_chat['admin_id']
            
            # Forward user message to admin
            try:
                # Get user info for better display
                user_name = message.from_user.first_name
                user_username = f"@{message.from_user.username}" if message.from_user.username else ""
                
                await client.send_message(
                    admin_id,
                    f"<b>👤 {user_name} {user_username} (ID: {user_id}):</b>\n{message.text or '[Media/File]'}"
                )
                
                # Log the message
                await db.add_chat_message(active_chat['_id'], False, message.text or '[Media/File]')
                
                # Confirm to user that message was sent
                await message.reply_text("✅ Your message has been sent to admin!")
                
            except Exception as e:
                await message.reply_text(f"❌ Failed to send message to admin: {str(e)}")
            return

# /contact command for users to initiate chat with admin or owner
@Client.on_message(filters.private & filters.command(['contact']))
async def chat_request_command(client, message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_username = f"@{message.from_user.username}" if message.from_user.username else ""
    
    try:
        # Check if user already has a pending chat request
        existing_request = await db.get_pending_chat_request(user_id)
        if existing_request:
            return await message.reply_text(
                "<b>⏳ Chat Request Already Pending</b>\n\n"
                "<b>You already have a pending chat request.</b>\n"
                "<b>Please wait for admin approval.</b>\n\n"
                f"<b>Request ID:</b> <code>{existing_request['_id']}</code>\n"
                f"<b>Submitted:</b> {existing_request['created_at'].strftime('%Y-%m-%d %H:%M:%S')} UTC"
            )
        
        # Check if user is already in an active chat
        active_chat = await db.get_active_chat_for_user(user_id)
        if active_chat:
            return await message.reply_text(
                "<b>💬 You already have an active chat session with admin!</b>\n\n"
                "<b>Just send your message and it will be forwarded to admin.</b>"
            )
            
        # Create chat request
        request_id = await db.create_chat_request(user_id)
        
        await message.reply_text(
            "<b>💬 Chat Request Submitted!</b>\n\n"
            "<b>Your request to chat with admin has been submitted.</b>\n"
            "<b>⏳ Please wait for admin approval.</b>\n\n"
            f"<b>Request ID:</b> <code>{request_id}</code>\n"
            "<b>💬 You will be notified once an admin accepts your request.</b>"
        )
        
        # Send notification to all sudo users (admin + owner) with accept/deny options
        sudo_users = Config.OWNER_ID + Config.ADMIN_ID
        notification_messages = []  # Store message IDs for cleanup
        
        for sudo_id in sudo_users:
            try:
                buttons = [
                    [
                        InlineKeyboardButton("✅ Accept Chat", callback_data=f"accept_chat_{request_id}"),
                        InlineKeyboardButton("❌ Deny", callback_data=f"deny_chat_{request_id}")
                    ]
                ]
                
                sent_msg = await client.send_message(
                    sudo_id,
                    f"<b>💬 New Chat Request</b>\n\n"
                    f"<b>User:</b> {user_name} {user_username}\n"
                    f"<b>User ID:</b> <code>{user_id}</code>\n"
                    f"<b>Request ID:</b> <code>{request_id}</code>\n"
                    f"<b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                    "<b>User wants to start a chat session.</b>\n\n"
                    "<b>✅ Accept to connect with this user</b>\n"
                    "<b>❌ Deny to reject this request</b>",
                    reply_markup=InlineKeyboardMarkup(buttons)
                )
                
                # Store notification message info for cleanup
                notification_messages.append({
                    'admin_id': sudo_id,
                    'message_id': sent_msg.id
                })
                
            except Exception as e:
                print(f"Failed to notify admin {sudo_id}: {e}")
        
        # Store notification messages in the request for cleanup
        await db.store_chat_notifications(request_id, notification_messages)
        
        # Log the chat request for monitoring
        from utils.notifications import NotificationManager
        notify = NotificationManager(client)
        await notify.notify_contact_request(user_id, "premium support", "submitted")
        
    except Exception as e:
        await message.reply_text(
            "<b>❌ Chat Request Failed</b>\n\n"
            "<b>An error occurred while processing your chat request.</b>\n\n"
            "<b>Please try again later.</b>"
        )


# Chat request accept/deny callbacks
@Client.on_callback_query(filters.regex(r'^accept_chat_'))
async def accept_chat_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    request_id = ObjectId(callback_query.data.split("_")[2])
    
    try:
        # Get chat request details
        request = await db.get_chat_request_by_id(request_id)
        if not request:
            return await callback_query.answer("❌ Chat request not found!", show_alert=True)
        
        if request['status'] != 'pending':
            return await callback_query.answer(f"❌ Already {request['status']}!", show_alert=True)
        
        # Start chat session
        session_id = await db.start_admin_chat(user_id, request['user_id'])
        await db.update_chat_request_status(request_id, 'accepted', user_id)
        
        # Delete notifications from all other admins
        await db.cleanup_chat_notifications(request_id, client, user_id)
        
        # Update current admin message
        await callback_query.message.edit_text(
            f"<b>✅ CHAT ACCEPTED by {callback_query.from_user.first_name}</b>\n\n"
            f"<b>User:</b> {request.get('user_name', 'Unknown')} {request.get('user_username', '')}\n"
            f"<b>User ID:</b> <code>{request['user_id']}</code>\n"
            f"<b>Request ID:</b> <code>{request_id}</code>\n\n"
            f"<b>🔗 Chat session started!</b>\n"
            f"<b>Session ID:</b> <code>{session_id}</code>",
            reply_markup=None
        )
        
        # Notify the user
        try:
            await client.send_message(
                request['user_id'],
                f"<b>✅ Chat Request Accepted!</b>\n\n"
                f"<b>Admin {callback_query.from_user.first_name} has accepted your chat request!</b>\n\n"
                f"<b>💬 You can now chat directly with the admin.</b>\n"
                f"<b>Just send your message and it will be forwarded.</b>\n\n"
                f"<b>Session ID:</b> <code>{session_id}</code>"
            )
        except:
            pass
        
        await callback_query.answer("✅ Chat request accepted and session started!", show_alert=True)
        
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

@Client.on_callback_query(filters.regex(r'^deny_chat_'))
async def deny_chat_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    request_id = ObjectId(callback_query.data.split("_")[2])
    
    try:
        # Get chat request details
        request = await db.get_chat_request_by_id(request_id)
        if not request:
            return await callback_query.answer("❌ Chat request not found!", show_alert=True)
        
        if request['status'] != 'pending':
            return await callback_query.answer(f"❌ Already {request['status']}!", show_alert=True)
        
        # Deny chat request
        await db.update_chat_request_status(request_id, 'denied', user_id)
        
        # Delete notifications from all admins
        await db.cleanup_chat_notifications(request_id, client, user_id)
        
        # Update current admin message
        await callback_query.message.edit_text(
            f"<b>❌ CHAT DENIED by {callback_query.from_user.first_name}</b>\n\n"
            f"<b>User:</b> {request.get('user_name', 'Unknown')} {request.get('user_username', '')}\n"
            f"<b>User ID:</b> <code>{request['user_id']}</code>\n"
            f"<b>Request ID:</b> <code>{request_id}</code>\n\n"
            f"<b>🚫 Chat request has been denied.</b>",
            reply_markup=None
        )
        
        # Notify the user
        try:
            await client.send_message(
                request['user_id'],
                "<b>❌ Chat Request Denied</b>\n\n"
                "<b>Your chat request has been denied by admin.</b>\n"
                "<b>You can try again later if needed.</b>"
            )
        except:
            pass
        
        await callback_query.answer("❌ Chat request denied!", show_alert=True)
        
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

# Admin-only chat command for direct user connection without permission
@Client.on_message(filters.private & filters.command(['chatuser']))
async def admin_chat_user_command(client, message):
    user_id = message.from_user.id
    
    # Check if user is admin/owner
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    try:
        # Get user ID from command
        command_parts = message.text.split()
        if len(command_parts) < 2:
            return await message.reply_text(
                "<b>📝 Usage:</b> <code>/chatuser USER_ID</code>\n\n"
                "<b>Example:</b> <code>/chatuser 123456789</code>\n\n"
                "<b>This command allows admins to directly start a chat with any user.</b>"
            )
        
        target_user_id = int(command_parts[1])
        
        # Check if admin already has an active chat
        existing_chat = await db.get_active_admin_chat(user_id)
        if existing_chat:
            await db.end_admin_chat(user_id)  # End existing chat
        
        # Start new chat session
        session_id = await db.start_admin_chat(user_id, target_user_id)
        
        # Get target user info
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"{target_user.first_name} (@{target_user.username})" if target_user.username else target_user.first_name
        except:
            user_info = f"User ID {target_user_id}"
        
        await message.reply_text(
            f"<b>✅ Direct Chat Started!</b>\n\n"
            f"<b>Target User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Session ID:</b> <code>{session_id}</code>\n\n"
            f"<b>💬 You can now chat directly with this user.</b>\n"
            f"<b>Messages you send will be forwarded to them.</b>\n\n"
            f"<b>Use /endchat to end this session.</b>"
        )
        
        # Notify the target user
        try:
            admin_name = message.from_user.first_name
            await client.send_message(
                target_user_id,
                f"<b>📞 Admin Chat Started!</b>\n\n"
                f"<b>Admin {admin_name} has started a chat session with you!</b>\n\n"
                f"<b>💬 You can now chat directly with the admin.</b>\n"
                f"<b>Just send your message and it will be forwarded.</b>\n\n"
                f"<b>Session ID:</b> <code>{session_id}</code>"
            )
        except Exception as e:
            await message.reply_text(f"⚠️ Chat started but failed to notify user: {str(e)}")
        
    except ValueError:
        await message.reply_text(
            "<b>❌ Invalid User ID!</b>\n\n"
            "<b>Please provide a valid numeric user ID.</b>\n\n"
            "<b>Example:</b> <code>/chatuser 123456789</code>"
        )
    except Exception as e:
        await message.reply_text(f"❌ Error starting chat: {str(e)}")

# End chat command for admins
@Client.on_message(filters.private & filters.command(['endchat']))
async def end_chat_command(client, message):
    user_id = message.from_user.id
    
    # Check if user is admin/owner
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    try:
        # Check if admin has an active chat
        active_chat = await db.get_active_admin_chat(user_id)
        if not active_chat:
            return await message.reply_text(
                "<b>❌ No Active Chat!</b>\n\n"
                "<b>You don't have any active chat sessions.</b>\n\n"
                "<b>Use /chatuser USER_ID to start a new chat.</b>"
            )
        
        # End the chat session
        await db.end_admin_chat(user_id)
        
        # Get target user info
        target_user_id = active_chat['target_user_id']
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"{target_user.first_name} (@{target_user.username})" if target_user.username else target_user.first_name
        except:
            user_info = f"User ID {target_user_id}"
        
        await message.reply_text(
            f"<b>✅ Chat Session Ended!</b>\n\n"
            f"<b>Target User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Session ID:</b> <code>{active_chat['_id']}</code>\n\n"
            f"<b>🔒 Chat session has been closed.</b>"
        )
        
        # Notify the target user
        try:
            admin_name = message.from_user.first_name
            await client.send_message(
                target_user_id,
                f"<b>🔒 Chat Session Ended!</b>\n\n"
                f"<b>Admin {admin_name} has ended the chat session.</b>\n\n"
                f"<b>💬 Use /chat to request a new chat session if needed.</b>"
            )
        except:
            pass  # Ignore if we can't notify the user
        
    except Exception as e:
        await message.reply_text(f"❌ Error ending chat: {str(e)}")

# /add_premium command for admins
@Client.on_message(filters.private & filters.command(['add_premium']))
async def add_premium_command(client, message):
    user_id = message.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    if len(message.command) < 3:
        return await message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Usage:</b> <code>/add_premium [user_id] [plan_type] [days]</code>\n"
            "<b>Example:</b> <code>/add_premium 123456789 pro 30</code>\n\n"
            "<b>Plan Types:</b>\n"
            "• <b>plus</b> - Unlimited forwarding only\n"
            "• <b>pro</b> - Unlimited forwarding + FTM mode + Priority support\n\n"
            "<b>Default: 30 days if days not specified.</b>"
        )
    
    try:
        target_user_id = int(message.command[1])
        plan_type = message.command[2].lower()
        days = int(message.command[3]) if len(message.command) > 3 else 30
        
        # Validate plan type
        if plan_type not in ['plus', 'pro']:
            return await message.reply_text(
                "❌ Invalid plan type! Please use 'plus' or 'pro'.\n\n"
                "<b>Plan Types:</b>\n"
                "• <b>plus</b> - Unlimited forwarding only\n"
                "• <b>pro</b> - Unlimited forwarding + FTM mode + Priority support"
            )
        
        if days <= 0:
            return await message.reply_text("❌ Days must be greater than 0!")
        
        # Add premium subscription
        expires_at = datetime.utcnow() + timedelta(days=days)
        await db.add_premium_user(target_user_id, plan_type, days)
        
        # Send admin action notification
        from utils.notifications import NotificationManager
        notify = NotificationManager(client)
        await notify.notify_admin_action(
            user_id, 
            "Added Premium User", 
            target_user_id, 
            f"Plan: {plan_type.upper()}, Duration: {days} days"
        )
        
        # Get user info
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"{target_user.first_name} (@{target_user.username})" if target_user.username else target_user.first_name
        except:
            user_info = f"User ID: {target_user_id}"
        
        await message.reply_text(
            f"<b>✅ Premium Added Successfully!</b>\n\n"
            f"<b>User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Plan Type:</b> {plan_type.upper()}\n"
            f"<b>Duration:</b> {days} days\n"
            f"<b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        
        # Notify the user
        try:
            # Get plan-specific features
            if plan_type == 'plus':
                features_text = "• Unlimited forwarding processes\n"
            else:  # pro plan
                features_text = "• Unlimited forwarding processes\n• FTM mode enabled\n• Priority support\n"
            
            await client.send_message(
                target_user_id,
                f"<b>🎉 Premium Access Granted!</b>\n\n"
                f"<b>✅ You have been granted {plan_type.upper()} plan for {days} days!</b>\n"
                f"<b>💎 Granted by: {message.from_user.first_name}</b>\n\n"
                f"<b>{plan_type.upper()} Plan Benefits:</b>\n"
                f"{features_text}\n"
                f"<b>Expires:</b> {expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
                "<b>Use /myplan to check your subscription details.</b>"
            )
        except:
            await message.reply_text("⚠️ Could not notify the user about premium access.")
            
    except ValueError:
        await message.reply_text("❌ Invalid user ID or days! Please provide valid numeric values.")
    except Exception as e:
        await message.reply_text(f"❌ Error adding premium: {str(e)}")

# /remove_premium command for admins
@Client.on_message(filters.private & filters.command(['remove_premium']))
async def remove_premium_command(client, message):
    user_id = message.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    if len(message.command) < 2:
        return await message.reply_text(
            "<b>❌ Invalid Usage!</b>\n\n"
            "<b>Usage:</b> <code>/remove_premium [user_id]</code>\n"
            "<b>Example:</b> <code>/remove_premium 123456789</code>\n\n"
            "<b>This will remove premium access from the user.</b>"
        )
    
    try:
        target_user_id = int(message.command[1])
        
        # Check if user has premium
        if not await db.is_premium_user(target_user_id):
            return await message.reply_text("❌ User doesn't have premium access!")
        
        # Remove premium subscription
        await db.remove_premium_user(target_user_id)
        
        # Get user info
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"{target_user.first_name} (@{target_user.username})" if target_user.username else target_user.first_name
        except:
            user_info = f"User ID: {target_user_id}"
        
        await message.reply_text(
            f"<b>✅ Premium Removed Successfully!</b>\n\n"
            f"<b>User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n"
            f"<b>Removed by:</b> {message.from_user.first_name}"
        )
        
        # Notify the user
        try:
            await client.send_message(
                target_user_id,
                f"<b>❌ Premium Access Removed</b>\n\n"
                f"<b>Your premium access has been removed by an admin.</b>\n"
                f"<b>Removed by:</b> {message.from_user.first_name}\n\n"
                "<b>You are now on the free plan with monthly limits.</b>\n"
                "<b>💎 To get premium again, use /plan to see available plans</b>"
            )
        except:
            await message.reply_text("⚠️ Could not notify the user about premium removal.")
            
    except ValueError:
        await message.reply_text("❌ Invalid user ID! Please provide a valid numeric user ID.")
    except Exception as e:
        await message.reply_text(f"❌ Error removing premium: {str(e)}")

# /pusers command to list all premium users
@Client.on_message(filters.private & filters.command(['pusers']))
async def premium_users_command(client, message):
    user_id = message.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await message.reply_text("❌ You don't have permission to use this command!")
    
    try:
        premium_users = await db.get_all_premium_users()
        
        if not premium_users:
            return await message.reply_text("📝 No premium users found!")
        
        text = "<b>💎 Premium Users List</b>\n\n"
        
        for i, user in enumerate(premium_users, 1):
            user_id_p = user['user_id']
            plan_type = user['plan_type']
            subscribed = user['subscribed_at'].strftime('%Y-%m-%d')
            expires = user['expires_at'].strftime('%Y-%m-%d') if user['expires_at'] else 'Never'
            
            # Get user info
            try:
                user_info = await client.get_users(user_id_p)
                name = f"{user_info.first_name} (@{user_info.username})" if user_info.username else user_info.first_name
            except:
                name = "Unknown User"
            
            text += f"<b>{i}.</b> {name}\n"
            text += f"   <b>ID:</b> <code>{user_id_p}</code>\n"
            text += f"   <b>Plan:</b> {plan_type}\n"
            text += f"   <b>Since:</b> {subscribed}\n"
            text += f"   <b>Expires:</b> {expires}\n\n"
            
            # Split message if too long
            if len(text) > 3500:
                await message.reply_text(text)
                text = ""
        
        if text:
            await message.reply_text(text)
            
    except Exception as e:
        await message.reply_text(f"❌ Error fetching premium users: {str(e)}")

# /plan command for users to see available plans
@Client.on_message(filters.private & filters.command(['plan']))
async def plan_command(client, message):
    from config import Config
    plan_text = f"""<b>💎 Premium Plans</b>

<b>🆓 Free Plan</b>
• 1 forwarding process per month
• Basic support
• Standard features

<b>✨ Plus Plan</b>
• ♾️ Unlimited forwarding processes
• 🔄 All basic features
• 📱 Standard support
• 💰 15 days: ₹{Config.PLAN_PRICING['plus']['15_days']}
• 💰 30 days: ₹{Config.PLAN_PRICING['plus']['30_days']}

<b>🏆 Pro Plan</b>
• ♾️ Unlimited forwarding processes
• 🔥 FTM mode with source tracking
• 🛡️ Priority support
• ⚡ Enhanced performance
• 💰 15 days: ₹{Config.PLAN_PRICING['pro']['15_days']}
• 💰 30 days: ₹{Config.PLAN_PRICING['pro']['30_days']}

<b>💳 How to Subscribe:</b>
1. Send payment to <code>6354228145@axl</code>
2. Take screenshot of payment confirmation
3. Send screenshot with <code>/verify [plan] [duration]</code>
4. Wait for admin approval (usually within 10 minutes)

<b>Examples:</b>
• <code>/verify plus 15</code> (for Plus 15 days)
• <code>/verify pro 30</code> (for Pro 30 days)

<b>📊 Check your current plan with /myplan</b>"""

    await message.reply_text(plan_text)

# /myplan command for users to check their subscription
@Client.on_message(filters.private & filters.command(['myplan']))
async def myplan_command(client, message):
    user_id = message.from_user.id
    
    try:
        # Check if user is premium
        is_premium = await db.is_premium_user(user_id)
        premium_details = await db.get_premium_user_details(user_id)
        usage = await db.get_daily_usage(user_id)
        
        if is_premium and premium_details:
            # Premium user
            plan_type = premium_details['plan_type']
            subscribed = premium_details['subscribed_at'].strftime('%Y-%m-%d %H:%M:%S')
            expires = premium_details['expires_at'].strftime('%Y-%m-%d %H:%M:%S') if premium_details['expires_at'] else 'Never'
            
            status_text = f"<b>💎 Your Premium Plan</b>\n\n"
            status_text += f"<b>Plan:</b> Premium ({plan_type})\n"
            status_text += f"<b>Status:</b> ✅ Active\n"
            status_text += f"<b>Subscribed:</b> {subscribed} UTC\n"
            status_text += f"<b>Expires:</b> {expires} UTC\n\n"
            status_text += f"<b>✅ Benefits:</b>\n"
            status_text += f"• Unlimited forwarding processes\n"
            status_text += f"• Priority support\n"
            status_text += f"• All premium features unlocked\n\n"
            
            if premium_details['expires_at']:
                days_left = (premium_details['expires_at'] - datetime.utcnow()).days
                status_text += f"<b>⏰ Days remaining:</b> {days_left} days\n"
            
        else:
            # Free user
            # Get monthly usage and check trial status
            monthly_usage = await db.get_monthly_usage(user_id)
            processes_used = monthly_usage.get('processes', 0)
            
            # Check trial status for proper limit calculation
            trial_status = await db.get_trial_status(user_id)
            processes_limit = 1  # Base free process
            if trial_status and trial_status.get('used', False):
                processes_limit = 2  # Base + trial
            
            status_text = f"<b>🆓 Your Free Plan</b>\n\n"
            status_text += f"<b>📊 Account Status:</b> Free User\n"
            status_text += f"<b>🗓️ Monthly Allocation:</b> {processes_limit} processes\n"
            
            if trial_status and trial_status.get('used', False):
                status_text += f"<b>🎁 Breakdown:</b> 1 base + 1 free trial bonus\n"
            else:
                status_text += f"<b>🎁 Free Trial:</b> Available (claim +1 extra process)\n"
            
            status_text += f"\n<b>📈 Monthly Usage:</b>\n"
            status_text += f"• <b>Used:</b> {processes_used}/{processes_limit} processes\n"
            status_text += f"• <b>Remaining:</b> {max(0, processes_limit - processes_used)} processes\n"
            status_text += f"• <b>Resets:</b> 1st of every month\n\n"
            
            if processes_used >= processes_limit:
                status_text += f"<b>🚫 Monthly limit reached!</b>\n"
                status_text += f"<b>💎 Upgrade to Premium for unlimited access!</b>\n\n"
            
            status_text += f"<b>💡 Upgrade to Premium:</b>\n"
            status_text += f"<b>✨ Plus Plan:</b> ₹199/15d, ₹299/30d\n"
            status_text += f"<b>🏆 Pro Plan:</b> ₹299/15d, ₹549/30d\n"
            status_text += f"• Use <code>/verify [plan] [duration]</code> with payment screenshot\n\n"
            
        status_text += f"<b>📋 See all plans with /plan</b>"
        
        await message.reply_text(status_text)
        
    except Exception as e:
        await message.reply_text(f"❌ Error fetching plan details: {str(e)}")

# Chat with user callback from payment verification
@Client.on_callback_query(filters.regex(r'^chat_user_'))
async def chat_user_callback(client, callback_query):
    user_id = callback_query.from_user.id
    
    if not Config.is_sudo_user(user_id):
        return await callback_query.answer("❌ You don't have permission!", show_alert=True)
    
    target_user_id = int(callback_query.data.split("_")[2])
    
    try:
        # Start chat session
        session_id = await db.start_admin_chat(user_id, target_user_id)
        
        # Get user info
        try:
            target_user = await client.get_users(target_user_id)
            user_info = f"{target_user.first_name} (@{target_user.username})" if target_user.username else target_user.first_name
        except:
            user_info = f"User ID: {target_user_id}"
        
        await callback_query.message.reply_text(
            f"<b>💬 Chat Session Started</b>\n\n"
            f"<b>Target User:</b> {user_info}\n"
            f"<b>User ID:</b> <code>{target_user_id}</code>\n\n"
            "<b>💡 Now send any message and it will be forwarded to the user.</b>\n"
            "<b>🔚 Use /endchat to end the session.</b>"
        )
        
        await callback_query.answer("✅ Chat session started!")
        
        # Notify the target user
        try:
            await client.send_message(
                target_user_id,
                f"<b>💬 Admin Chat Session</b>\n\n"
                f"<b>An admin has started a chat session with you.</b>\n"
                f"<b>Admin:</b> {callback_query.from_user.first_name}\n\n"
                "<b>You can now chat directly with the admin!</b>"
            )
        except:
            pass
            
    except Exception as e:
        await callback_query.answer(f"❌ Error: {str(e)}", show_alert=True)

# Copy UPI ID callback
@Client.on_callback_query(filters.regex(r'^copy_upi$'))
async def copy_upi_callback(client, callback_query):
    await callback_query.answer("📋 UPI ID: 6354228145@axl", show_alert=True)