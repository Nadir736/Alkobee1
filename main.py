import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ----------------- البيانات الخاصة بك -----------------
BOT_TOKEN = "8835745730:AAGvzm2-SkNTeIcsFguUPlsUPs3pxkjnylg"
ADMIN_CHAT_ID = "825802452"  # ID حسابك لاستلام التنبيهات

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ----------------- البحث في PartSouq -----------------
def search_partsouq(part_number: str) -> dict:
    url = f"https://partsouq.com/ar/search/all?q={part_number}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return {"url": url, "text": "تم العثور على الرابط المباشر، يمكنك فتح الرابط لاستعراض كافة التفاصيل والبدائل."}
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        rows = soup.find_all('tr')
        
        for row in rows:
            text = row.get_text(separator=" ", strip=True)
            if part_number.lower() in text.lower():
                results.append(text)
        
        if not results:
            return {"url": url, "text": "لم نتمكن من سحب البدائل أوتوماتيكياً، يمكنك مراجعة الرابط المباشر للحصول على نتائج دقيقة."}
            
        summary = "\n".join(results[:5])
        return {"url": url, "text": summary}

    except Exception as e:
        return {"url": url, "text": f"تعذر جلب النتائج تلقائياً. يمكنك الاستعلام مباشرة عبر الرابط."}

# ----------------- أوامر البوت -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("مشاركة رقم الهاتف 📱", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    
    await update.message.reply_text(
        "أهلاً بك في بوت البحث عن قطع غيار السيارات والبدائل! 🚗\n\n"
        "يرجى الضغط على الزر أدناه لمشاركة رقم هاتفك للبدء بالبحث:",
        reply_markup=reply_markup
    )

async def handle_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    contact = update.message.contact
    context.user_data['phone_number'] = contact.phone_number
    await update.message.reply_text("تم حفظ رقم الهاتف بنجاح! ✅\nالان أرسل رقم القطعة التي تريد البحث عنها:")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    part_number = update.message.text.strip()
    user = update.effective_user
    phone = context.user_data.get('phone_number', 'لم يشارك الرقم')
    
    await update.message.reply_text(f"🔍 جاري البحث عن القطعة: `{part_number}` ...", parse_mode='Markdown')
    
    # البحث
    result = search_partsouq(part_number)
    
    # الرد على الزبون
    msg = f"🔗 **رابط نتائج البحث والبدائل في PartSouq:**\n{result['url']}\n\n"
    if result.get("text"):
        msg += f"📋 **الملخص:**\n{result['text']}"
    await update.message.reply_text(msg, parse_mode='Markdown')
        
    # إرسال إشعار لك (المشرف)
    admin_msg = (
        f"📥 **طلب بحث جديد:**\n\n"
        f"🔢 **رقم القطعة:** `{part_number}`\n"
        f"👤 **الزبون:** {user.full_name} (@{user.username or 'بدون_معرف'})\n"
        f"🆔 **المعرف:** `{user.id}`\n"
        f"📱 **رقم الهاتف:** `{phone}`\n"
        f"🔗 **رابط القطعة:** {result['url']}"
    )
    
    try:
        await context.bot.send_message(chat_id=ADMIN_CHAT_ID, text=admin_msg, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"خطأ في إرسال التنبيه للمشرف: {e}")

# ----------------- التشغيل -----------------
if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.CONTACT, handle_contact))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))
    
    print("البوت يعمل الآن...")
    app.run_polling()
