import requests
import asyncio
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

# ----------- KEEP ALIVE SERVER -----------
app = Flask('')

@app.route('/')
def home():
    return "Bot is Running!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# ----------- CONFIGURATION -----------
BOT_TOKEN = "8775932474:AAHSUTDImw7ivJaSDM3fwB2nOsPoYx9dS4A" # এখানে আপনার টোকেন বসান

headers = {"User-Agent": "Mozilla/5.0"}

# ----------- DATA SCRAPER -----------
def get_data(tid):
    url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Voucher/{tid}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        data = {
            "Transaction ID": tid, "Institute": "", "Name": "", "Roll": "",
            "Tech": "", "Semester": "", "Mobile": "", "Session": "",
            "Amount(BDT)": "", "Date": ""
        }
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                key = cols[0].text.strip().replace(":", "")
                value = cols[1].text.strip()
                if "Institute" in key: data["Institute"] = value
                elif "Name" in key: data["Name"] = value
                elif "Roll" in key: data["Roll"] = value
                elif "Tech" in key: data["Tech"] = value
                elif "Semester" in key: data["Semester"] = value
                elif "Mobile" in key: data["Mobile"] = value
                elif "Session" in key: data["Session"] = value
                elif "Amount" in key: data["Amount(BDT)"] = value
        return data
    except:
        return None

# ----------- SEND RESULT -----------
async def process_roll(update, data_list):
    final_text = ""
    unique_numbers = []
    for i, data in enumerate(data_list, 1):
        phone = data["Mobile"]
        if phone.startswith("0"): phone = "880" + phone[1:]
        final_text += f"📄 Result {i}\n<pre>\nTransaction ID: {data['Transaction ID']}\nInstitute     : {data['Institute']}\nName          : {data['Name']}\nRoll          : {data['Roll']}\nTech          : {data['Tech']}\nSemester      : {data['Semester']}\nMobile        : {data['Mobile']}\nSession       : {data['Session']}\nAmount(BDT)   : {data['Amount(BDT)']}\nDate          : {data['Date']}\n</pre>\n\n"
        if phone not in unique_numbers: unique_numbers.append(phone)

    keyboard = []
    for phone in unique_numbers:
        keyboard.append([
            InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{phone}"),
            InlineKeyboardButton("📢 Telegram", url=f"https://t.me/{phone}")
        ])
    
    msg_source = update.message if update.message else update.callback_query.message
    await msg_source.reply_text(final_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------- SEARCH CORE LOGIC -----------
async def run_search(update_or_query, context, start_r, end_r):
    rolls = list(range(start_r, end_r + 1))
    context.user_data["current_end"] = end_r
    
    msg_source = update_or_query.message if hasattr(update_or_query, 'message') else update_or_query
    status_msg = await msg_source.reply_text("⏳ Processing...")
    
    total_found = 0
    for i, roll in enumerate(rolls, 1):
        url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Search?searchStr={roll}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if "Details" in r.text:
                soup = BeautifulSoup(r.text, "html.parser")
                links = soup.select("a[href*='Voucher']")
                data_list = []
                for link in links:
                    tid = link['href'].split("/")[-1]
                    data = get_data(tid)
                    if data and data["Name"]: data_list.append(data)
                
                if data_list:
                    total_found += 1
                    await process_roll(update_or_query, data_list)

            await status_msg.edit_text(
                f"⏳ Processing...\n🔢 Roll: {roll}\n📊 Found: {total_found}\n✅ Progress: {i}/{len(rolls)}"
            )
        except: continue

    # রেজাল্ট শেষ হলে মেসেজ এবং Next বাটন
    keyboard = [[InlineKeyboardButton("👉 Next 500?", callback_data="next_500")]]
    await msg_source.reply_text(
        f"✅ Done!\n📊 Total Found: {total_found}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ----------- HANDLERS -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Start", callback_data="btn_ready")]]
    await update.message.reply_text("বটটি শুরু করতে নিচের বাটনে ক্লিক করুন:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        if "-" in text:
            s, e = map(int, text.split("-"))
            await run_search(update, context, s, e)
        elif "," in text:
            rolls = [int(r.strip()) for r in text.split(",")]
            # কমার ক্ষেত্রে নেক্সট বাটন দরকার নেই, শুধু রেজাল্ট আসবে
            for r in rolls: await run_search(update, context, r, r)
        else:
            r = int(text)
            await run_search(update, context, r, r)
    except: pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "btn_ready":
        await query.message.reply_text("🚀 Ready!")
    
    elif query.data == "next_500":
        last_end = context.user_data.get("current_end", 0)
        if last_end > 0:
            await run_search(query, context, last_end + 1, last_end + 500)

# ----------- MAIN -----------
if __name__ == "__main__":
    keep_alive()
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()
