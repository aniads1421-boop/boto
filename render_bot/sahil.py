import sqlite3
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, CallbackQueryHandler, CommandHandler, filters

ADMIN_ID = 5673449417
admin_active_target = {}

def init_db():
    conn = sqlite3.connect("bot_chats.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            sender TEXT,
            message TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

def save_message(user_id, user_name, sender, message):
    conn = sqlite3.connect("bot_chats.db")
    cursor = conn.cursor()
    time_now = datetime.datetime.now().strftime("%I:%M %p")
    cursor.execute("INSERT INTO messages (user_id, user_name, sender, message, timestamp) VALUES (?, ?, ?, ?, ?)",
                   (user_id, user_name, sender, message, time_now))
    conn.commit()
    conn.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    message = update.message
    if not message or not message.text:
        return

    if user.id == ADMIN_ID:
        current_target = admin_active_target.get(ADMIN_ID)
        if current_target:
            try:
                await context.bot.send_message(chat_id=current_target, text=message.text)
                
                conn = sqlite3.connect("bot_chats.db")
                cursor = conn.cursor()
                cursor.execute("SELECT user_name FROM messages WHERE user_id = ? LIMIT 1", (current_target,))
                res = cursor.fetchone()
                u_name = res[0] if res else "User"
                conn.close()

                save_message(current_target, u_name, "Admin", message.text)
                await message.reply_text("✅ Sent!")
            except Exception as e:
                await message.reply_text("❌ Error sending message.")
        else:
            await message.reply_text("⚠️ Pehle kisi user ke button par click karke chat open karein.")
    else:
        save_message(user.id, user.first_name, "User", message.text)

        keyboard = [[InlineKeyboardButton(f"💬 Open Chat with {user.first_name}", callback_data=f"chat_{user.id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        forward_msg = f"📩 Naya Message\n👤 {user.first_name}\n🆔 ID: `{user.id}`\n\n💬 {message.text}"
        await context.bot.send_message(chat_id=ADMIN_ID, text=forward_msg, parse_mode="Markdown", reply_markup=reply_markup)
        await message.reply_text("Aapka message mil gaya hai, jald hi jawab milega.")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        conn = sqlite3.connect("bot_chats.db")
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT user_id, user_name FROM messages ORDER BY id DESC")
        users = cursor.fetchall()
        conn.close()

        if not users:
            await update.message.reply_text("📭 Abhi koi chat history nahi hai.")
            return

        keyboard = []
        text = "📋 **Saare Users ki List:**\n\n"
        
        seen = set()
        for u_id, u_name in users:
            if u_id not in seen:
                seen.add(u_id)
                keyboard.append([InlineKeyboardButton(f"💬 Open Chat with {u_name}", callback_data=f"chat_{u_id}")]
                )

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(text, reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if data.startswith("chat_"):
        target_user_id = int(data.split("_")[1])
        admin_active_target[ADMIN_ID] = target_user_id

        conn = sqlite3.connect("bot_chats.db")
        cursor = conn.cursor()
        cursor.execute("SELECT user_name FROM messages WHERE user_id = ? LIMIT 1", (target_user_id,))
        res = cursor.fetchone()
        user_name = res[0] if res else "User"

        cursor.execute("SELECT sender, message, timestamp FROM messages WHERE user_id = ? ORDER BY id ASC", (target_user_id,))
        chats = cursor.fetchall()
        conn.close()

        chat_view = f"🟢 **Live Chatting with {user_name}**\n-----------------------------------\n"
        for sender, msg, timestamp in chats:
            if sender == "Admin":
                chat_view += f"🧑‍💻 **Aap:** {msg} _({timestamp})_\n"
            else:
                chat_view += f"👤 **{user_name}:** {msg} _({timestamp})_\n"

        chat_view += f"\n-----------------------------------\n✍️ _Ab aap jo bhi message yahan bhejenge, woh seedha {user_name} ke paas chala jayega._"
        
        # Yahan edit ki jagah naya message bheja ja raha hai taaki alag bubble dikhe
        await context.bot.send_message(chat_id=ADMIN_ID, text=chat_view, parse_mode="Markdown")

if __name__ == '__main__':
    app = ApplicationBuilder().token("8523577042:AAGsUuvJv0HvW25LBy7l73zrocc0SPbBMcA").build()
    
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    app.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is running...")
    app.run_polling()