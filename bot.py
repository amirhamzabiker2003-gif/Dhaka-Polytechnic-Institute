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

# ----------- KEEP ALIVE SERVER (For Render) -----------
app = Flask('')

@app.route('/')
def home():
    return "I am alive!"

def run():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run)
    t.start()

# ----------- BOT CONFIGURATION -----------
BOT_TOKEN = "8723976334:AAE0vOE-tZ7pZvJXBTLNUYI1ozoxvOL0tp0" # আপনার টোকেন এখানে বসান

headers = {
    "User-Agent": "Mozilla/5.0"
}

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

        date_tag = soup.find(string=lambda x: x and "Date" in x)
        if date_tag:
            try: data["Date"] = date_tag.find_next().text.strip()
            except: pass
        return data
    except:
        return None

# ----------- SEND RESULT -----------
async def process_roll(update, data_list):
    final_text = ""
    unique_numbers = []

    for i, data in enumerate(data_list, 1):
        phone = data["Mobile"]
        if phone.startswith("0"):
            phone = "880" + phone[1:]

        final_text += f"📄 Result {i}\n<pre>\nTransaction ID: {data['Transaction ID']}\nInstitute     : {data['Institute']}\nName          : {data['Name']}\nRoll          : {data['Roll']}\nTech          : {data['Tech']}\nSemester      : {data['Semester']}\nMobile        : {data['Mobile']}\nSession       : {data['Session']}\nAmount(BDT)   : {data['Amount(BDT)']}\nDate          : {data['Date']}\n</pre>\n\n"

        if phone not in unique_numbers:
            unique_numbers.append(phone)

    keyboard = []
    for phone in unique_numbers:
        keyboard.append([
            InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{phone}"),
            InlineKeyboardButton("📢 Telegram", url=f"https://t.me/{phone}")
        ])

    # Check if update is from a message or callback
    msg_source = update.message if update.message else update.callback_query.message
    await msg_source.reply_text(final_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------- SEARCH HANDLER -----------
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    rolls = []

    try:
        if "-" in text: # Range Format: 656000-656499
            start, end = map(int, text.split("-"))
            rolls = list(range(start, end + 1))
            context.user_data["current_end"] = end
        elif "," in text: # Multi-roll Format: 656001, 656005
            rolls = [int(r.strip()) for r in text.split(",")]
        else: # Single Roll Format: 656001
            rolls = [int(text)]
    except ValueError:
        return await update.message.reply_text("❌ ভুল ফরম্যাট! সঠিক রোল, রেঞ্জ (656000-656010) বা কমা (101,102) ব্যবহার করুন।")

    msg = await update.message.reply_text("⏳ Processing...")
    total_person = 0

    for i, roll in enumerate(rolls, 1):
        url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Search?searchStr={roll}"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if "Details" not in r.text: continue

            soup = BeautifulSoup(r.text, "html.parser")
            links = soup.select("a[href*='Voucher']")
            data_list = []

            for link in links:
                tid = link['href'].split("/")[-1]
                data = get_data(tid)
                if data and data["Name"]: data_list.append(data)

            if data_list:
                total_person += 1
                await process_roll(update, data_list)

            if i % 5 == 0 or i == len(rolls): # প্রতি ৫টি রোল পর পর স্ট্যাটাস আপডেট
                await msg.edit_text(f"⏳ Processing...\n🔢 Roll: {roll}\n📊 Person: {total_person}\n✅ Progress: {i}/{len(rolls)}")
        except:
            continue

    await update.message.reply_text(f"✅ Done!\n📊 Total: {total_person}")
    
    if "-" in text: # শুধুমাত্র রেঞ্জ দিলে Next বাটন দেখাবে
        keyboard = [[InlineKeyboardButton("🚀 Next 500", callback_data="next_auto")]]
        await update.message.reply_text("👇 Click for next batch", reply_markup=InlineKeyboardMarkup(keyboard))

# ----------- START & BUTTONS -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Ready!\n\nরোল দিন (e.g. 656001)\nরেঞ্জ দিন (e.g. 656000-656499)\nএকাধিক রোল দিন (e.g. 656001, 656005)")

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # আপনার আগের বাটন লজিকটি এখানে অপরিবর্তিত থাকবে
    query = update.callback_query
    await query.answer()
    # ... (বাকি বাটন কোড আপনার মূল কোড অনুযায়ী কাজ করবে)

# ----------- MAIN -----------
if __name__ == "__main__":
    keep_alive() # Render-এর জন্য Flask চালু করা হলো
    
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    print("✅ Bot Running with Flask Support...")
    application.run_polling()
