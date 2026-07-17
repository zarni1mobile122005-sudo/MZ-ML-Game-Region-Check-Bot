import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "8957495939:AAHxxJYnG7_mI8g-7MFAmXN-YPphhpfJt30"

# Server ID to Region Mapping (Estimated based on common patterns)
def get_region_by_server(server_id):
    server_id = int(server_id)
    if 2000 <= server_id <= 2999:
        return "Indonesia (ID)"
    elif 3000 <= server_id <= 3999:
        return "South East Asia (SEA) / Philippines"
    elif 4000 <= server_id <= 4999:
        return "Latin America (LATAM)"
    elif 5000 <= server_id <= 5999:
        return "North America (NA)"
    elif 6000 <= server_id <= 6999:
        return "Europe (EU)"
    elif 8000 <= server_id <= 8999:
        return "India / Asia"
    elif 9000 <= server_id <= 9999:
        return "Brazil (BR)"
    elif 1000 <= server_id <= 1999:
        return "Old Servers / Global"
    else:
        return "Unknown / Global"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "မင်္ဂလာပါ!🌐 Mobile Legends Region🔎 Check Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "👤 Player ရဲ့ 🌐 Region ကို🔎 စစ်ဆေးဖို့အတွက် User🆔 ID နဲ့ Server ID ကို အခုလို ပို့ပေးပါ -\n"
        "ဥပမာ - (game id) (sever id) "
    )

async def check_region(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    parts = text.split()
    
    if len(parts) != 2:
        await update.message.reply_text("ကျေးဇူးပြု၍ User ID နှင့် Server ID ကို space ခြားပြီး ပို့ပေးပါ။\nဥပမာ - `1114917746 13481`")
        return

    user_id, server_id = parts[0], parts[1]
    
    # Try multiple API endpoints (Fallback logic)
    nickname = "Unknown"
    region_info = get_region_by_server(server_id)
    
    # Attempt 1: isan API (Commonly used for MLBB bots)
    try:
        # Note: In production, some APIs might need specific headers or are temporary
        api_url = f"https://api.isan.eu.org/nickname/ml?id={user_id}&zone={server_id}"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            nickname = data.get("name", "Unknown")
    except:
        pass

    # Final Result Message
    result_msg = (
        f"🎮 **Mobile Legends Player Info**\n\n"
        f"👤 **Nickname:** {nickname}\n"
        f"🆔 **User ID:** {user_id}\n"
        f"🌐 **Server ID:** {server_id}\n"
        f"📍 **Estimated Region:** {region_info}\n\n"
        f"💡 *✅Region Check Done...*"
    )
    
    await update.message.reply_text(result_msg, parse_mode='Markdown')

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    check_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), check_region)
    
    application.add_handler(start_handler)
    application.add_handler(check_handler)
    
    print("Bot is running...")
    application.run_polling()

