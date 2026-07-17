import logging
import os
import json
import re
import ast
import operator
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8957495939:AAHKT6nLeBjczBzF8hAFmbprojvb4LdUoSQ")
ADMIN_ID = 7592705124
USERS_FILE = "users.json"


# ── User Storage ──────────────────────────────────────────────────────────────

def load_users() -> dict:
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_users(users: dict):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def register_user(update: Update):
    users = load_users()
    uid = str(update.effective_user.id)
    users[uid] = {
        "id": update.effective_user.id,
        "username": update.effective_user.username or "",
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or "",
    }
    save_users(users)


# ── Safe Calculator ───────────────────────────────────────────────────────────

# Matches expressions like: 1+1, 1 + 1, 10*5, 3.5 / 2, 100 - 20, etc.
CALC_PATTERN = re.compile(
    r'^\s*-?\d+(\.\d+)?(\s*[+\-*/]\s*-?\d+(\.\d+)?)+\s*$'
)

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.USub: operator.neg,
}


def safe_eval(node):
    """Safely evaluate arithmetic AST nodes only."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in SAFE_OPS:
        left = safe_eval(node.left)
        right = safe_eval(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ZeroDivisionError("သုည (0) နဲ့ စားလို့မရပါ")
        return SAFE_OPS[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in SAFE_OPS:
        return SAFE_OPS[type(node.op)](safe_eval(node.operand))
    else:
        raise ValueError("Invalid expression")


def calculate(expr: str):
    """
    Parse and calculate a math expression string.
    Returns (display_expr, result) tuple.
    display_expr strips extra spaces for clean display.
    """
    # Normalize spaces around operators for display (e.g., "1 +1" -> "1+1")
    display_expr = re.sub(r'\s*([+\-*/])\s*', r'\1', expr.strip())
    tree = ast.parse(display_expr, mode='eval')
    result = safe_eval(tree.body)
    # Format result: show int if whole number, else float
    if isinstance(result, float) and result.is_integer():
        result_str = str(int(result))
    else:
        result_str = f"{result:.10g}"
    return display_expr, result_str


def is_calc_expression(text: str) -> bool:
    """Check if the message looks like a calculator expression."""
    return bool(CALC_PATTERN.match(text))


# ── MLBB Nickname Lookup ──────────────────────────────────────────────────────

def fetch_nickname(user_id, server_id):
    headers = {"User-Agent": "Mozilla/5.0"}
    apis = [
        f"https://api.isan.eu.org/nickname/ml?id={user_id}&zone={server_id}",
        f"https://mlbb-api.vercel.app/api/check?uid={user_id}&zoneId={server_id}",
        f"https://hoshiyuki.site/mlbb/cek?id={user_id}&server={server_id}",
        f"https://api.ryzentx.repl.co/api/mlbb?id={user_id}&zone={server_id}",
    ]
    for url in apis:
        try:
            r = requests.get(url, timeout=6, headers=headers)
            if r.status_code == 200:
                data = r.json()
                name = (data.get("name") or data.get("nickname") or
                        data.get("username") or data.get("data", {}).get("name"))
                if name and name not in ("Unknown", "", None):
                    return name
        except Exception:
            continue
    return "❓ Not Found"


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update)
    await update.message.reply_text(
        "မင်္ဂလာပါ! 👋\n\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "🤖 *Bot အကြောင်း*\n"
        "━━━━━━━━━━━━━━━━━━━━━\n\n"
        "ဒီ Bot မှာ အောက်ပါ features ၂ ခု ပါဝင်သည်:\n\n"

        "🧮 *1. Calculator (တွက်ချက်မှု)*\n"
        "• ပေါင်း: `1+1`  သို့  `1 + 1` → `1+1=2`\n"
        "• နှုတ်: `10-3`  သို့  `10 - 3` → `10-3=7`\n"
        "• မြှောက်: `5*4`  သို့  `5 * 4` → `5*4=20`\n"
        "• စား: `10/2`  သို့  `10 / 2` → `10/2=5`\n"
        "• Space ရှိ/မရှိ နှစ်မျိုးစလုံး ရပါသည်\n\n"

        "🎮 *2. MLBB Player Check*\n"
        "• User ID နဲ့ Server ID ကို space ခြားပြီး ပို့ပေးပါ\n"
        "• 📌 ဥပမာ: `1114917746 13481`\n\n"

        "━━━━━━━━━━━━━━━━━━━━━\n"
        "စတင်အသုံးပြုနိုင်ပါပြီ! 🚀",
        parse_mode='Markdown',
        do_quote=True,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update)
    text = update.message.text.strip()

    # ── Calculator branch ──────────────────────────────────────────────────
    if is_calc_expression(text):
        try:
            display_expr, result = calculate(text)
            await update.message.reply_text(
                f"`{display_expr}={result}`",
                parse_mode='Markdown',
                do_quote=True,
            )
        except ZeroDivisionError as e:
            await update.message.reply_text(f"⚠️ {e}", do_quote=True)
        except Exception:
            await update.message.reply_text("⚠️ တွက်ချက်မှု မှားယွင်းနေသည်။", do_quote=True)
        return

    # ── MLBB Player Check branch ───────────────────────────────────────────
    parts = text.split()

    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        await update.message.reply_text(
            "⚠️ မသိသော command ဖြစ်သည်။\n\n"
            "🧮 *Calculator:*  `1+1`  သို့  `1 + 1`\n"
            "🎮 *MLBB Check:*  `UserID ServerID`  ဥပမာ: `1114917746 13481`\n\n"
            "/start နှိပ်ပြီး အသေးစိတ် ကြည့်ပါ။",
            parse_mode='Markdown',
            do_quote=True,
        )
        return

    user_id, server_id = parts[0], parts[1]
    msg = await update.message.reply_text("🔍 စစ်ဆေးနေသည်...", do_quote=True)

    nickname = fetch_nickname(user_id, server_id)

    result = (
        f"┌─────────────────────────\n"
        f"│  🎮  *MOBILE LEGENDS*\n"
        f"│  *Player Information*\n"
        f"└─────────────────────────\n"
        f"\n"
        f"  👤  *Nickname*\n"
        f"  ┗  `{nickname}`\n"
        f"\n"
        f"  🆔  *User ID*\n"
        f"  ┗  `{user_id}`\n"
        f"\n"
        f"  🌐  *Server ID*\n"
        f"  ┗  `{server_id}`\n"
        f"\n"
        f"─────────────────────────\n"
        f"  ✅  *Check Completed Successfully*"
    )
    await msg.edit_text(result, parse_mode='Markdown')


# ── Admin: /user_list ─────────────────────────────────────────────────────────

async def user_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    users = load_users()
    if not users:
        await update.message.reply_text("📭 မည်သည့် user မျှ မရှိသေးပါ။")
        return

    lines = [f"👥 *User List* — {len(users)} ဦး\n─────────────────────────"]
    for u in users.values():
        uname = f"@{u['username']}" if u['username'] else "—"
        name = f"{u['first_name']} {u['last_name']}".strip() or "—"
        lines.append(f"• `{u['id']}`  {name}  {uname}")

    text = "\n".join(lines)
    if len(text) <= 4096:
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        chunk, chunks = [], []
        for line in lines:
            chunk.append(line)
            if len("\n".join(chunk)) > 3800:
                chunks.append("\n".join(chunk[:-1]))
                chunk = [line]
        chunks.append("\n".join(chunk))
        for part in chunks:
            await update.message.reply_text(part, parse_mode='Markdown')


# ── Admin: /user_message ──────────────────────────────────────────────────────

async def user_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text(
            "📝 Message မပါပါ။\n"
            "ဥပမာ: `/user_message မင်္ဂလာပါ!`",
            parse_mode='Markdown'
        )
        return

    text_to_send = " ".join(context.args)
    users = load_users()

    if not users:
        await update.message.reply_text("📭 မည်သည့် user မျှ မရှိသေးပါ။")
        return

    status_msg = await update.message.reply_text(f"📤 Sending to {len(users)} users...")

    success, failed = 0, 0
    for u in users.values():
        try:
            await context.bot.send_message(
                chat_id=u['id'],
                text=f"📢 *Admin Message*\n\n{text_to_send}",
                parse_mode='Markdown'
            )
            success += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ *ပို့ပြီးပါပြီ*\n\n"
        f"  ✔️  Success: {success}\n"
        f"  ❌  Failed: {failed}",
        parse_mode='Markdown'
    )


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('user_list', user_list))
    app.add_handler(CommandHandler('user_message', user_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling(drop_pending_updates=True)
