import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)
from config import BOT_TOKEN, ADMIN_ID

# ---------------- DATABASE ----------------
conn = sqlite3.connect("database.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    ref INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    description TEXT,
    link TEXT,
    reward INTEGER
)""")

c.execute("""CREATE TABLE IF NOT EXISTS submissions (
    user_id INTEGER,
    task_id INTEGER
)""")
conn.commit()

# ---------------- START ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref = None

    if context.args:
        ref = int(context.args[0])

    c.execute("SELECT * FROM users WHERE user_id=?", (user.id,))
    if not c.fetchone():
        c.execute("INSERT INTO users (user_id, ref) VALUES (?,?)", (user.id, ref))
        if ref:
            c.execute("UPDATE users SET balance = balance + 2 WHERE user_id=?", (ref,))
    conn.commit()

    keyboard = [
        [InlineKeyboardButton("🧾 Tasks", callback_data="tasks")],
        [InlineKeyboardButton("💰 Balance", callback_data="balance")],
        [InlineKeyboardButton("👥 Refer", callback_data="refer")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw")]
    ]
    await update.message.reply_text(
        "👋 Welcome to Task Earning Bot\n\nChoose an option:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ---------------- BALANCE ----------------
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    c.execute("SELECT balance FROM users WHERE user_id=?", (q.from_user.id,))
    bal = c.fetchone()[0]
    await q.answer()
    await q.message.reply_text(f"💰 Your balance: {bal} ৳")

# ---------------- TASK LIST ----------------
async def tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    c.execute("SELECT * FROM tasks")
    rows = c.fetchall()

    if not rows:
        await q.message.reply_text("❌ No tasks available now")
        return

    for t in rows:
        task_id, title, desc, link, reward = t
        c.execute("SELECT * FROM submissions WHERE user_id=? AND task_id=?",
                  (q.from_user.id, task_id))
        if c.fetchone():
            continue

        btn = [[InlineKeyboardButton("✅ Done", callback_data=f"done_{task_id}")]]
        await q.message.reply_text(
            f"📌 {title}\n\n{desc}\n\n💰 Reward: {reward} ৳\n🔗 {link}",
            reply_markup=InlineKeyboardMarkup(btn)
        )

# ---------------- DONE ----------------
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    task_id = int(q.data.split("_")[1])
    user = q.from_user

    c.execute("INSERT INTO submissions VALUES (?,?)", (user.id, task_id))
    conn.commit()

    await q.answer("Submitted for review")

    c.execute("SELECT title, reward FROM tasks WHERE id=?", (task_id,))
    title, reward = c.fetchone()

    await context.bot.send_message(
        ADMIN_ID,
        f"🆕 Task Submission\n\n"
        f"👤 User: {user.id}\n"
        f"📌 Task: {title}\n"
        f"💰 Reward: {reward}\n\n"
        f"/approve {user.id} {task_id}"
    )

# ---------------- ADMIN: ADD TASK ----------------
async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["addtask"] = True
    await update.message.reply_text(
        "Send task like this:\n\n"
        "Title | Description | Link | Reward\n\n"
        "Example:\nJoin Channel | Join & stay 1 min | https://t.me/test | 5"
    )

async def save_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("addtask"):
        return

    try:
        title, desc, link, reward = update.message.text.split("|")
        c.execute("INSERT INTO tasks (title,description,link,reward) VALUES (?,?,?,?)",
                  (title.strip(), desc.strip(), link.strip(), int(reward.strip())))
        conn.commit()
        await update.message.reply_text("✅ Task added successfully")
    except:
        await update.message.reply_text("❌ Format error")

    context.user_data["addtask"] = False

# ---------------- ADMIN: APPROVE ----------------
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        task_id = int(context.args[1])
        c.execute("SELECT reward FROM tasks WHERE id=?", (task_id,))
        reward = c.fetchone()[0]
        c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (reward, user_id))
        conn.commit()
        await update.message.reply_text("✅ Approved")
    except:
        await update.message.reply_text("❌ Error")

# ---------------- REFER ----------------
async def refer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    link = f"https://t.me/{context.bot.username}?start={q.from_user.id}"
    await q.answer()
    await q.message.reply_text(f"👥 Refer & Earn\n\nYour link:\n{link}\n\n+2৳ per user")

# ---------------- WITHDRAW ----------------
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        "💸 Withdraw Request\n\n"
        "Send like this:\n"
        "Amount | Method | Number\n\n"
        "Example:\n500 | bKash | 01XXXXXXXXX
Example:\n500 | Nagad | 01XXXXXXXXX
"
    )

async def withdraw_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "|" not in text:
        return
    await context.bot.send_message(ADMIN_ID, f"💸 Withdraw Request\n\n{text}")

# ---------------- MAIN ----------------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addtask", addtask))
app.add_handler(CommandHandler("approve", approve))
app.add_handler(CallbackQueryHandler(tasks, pattern="tasks"))
app.add_handler(CallbackQueryHandler(balance, pattern="balance"))
app.add_handler(CallbackQueryHandler(refer, pattern="refer"))
app.add_handler(CallbackQueryHandler(withdraw, pattern="withdraw"))
app.add_handler(CallbackQueryHandler(done, pattern="done_"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_task))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_msg))

app.run_polling()
