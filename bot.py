import requests
import asyncio
import threading
from bs4 import BeautifulSoup
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

BOT_TOKEN = "8775932474:AAGarYQSKIsn732Y9LFIgYdNrQ_q-X3S0p0"

# ----------- FLASK (KEEP ALIVE) -----------
app_flask = Flask(__name__)

@app_flask.route('/')
def home():
    return "Bot is running!"

# ----------- SCRAPER -----------
headers = {"User-Agent": "Mozilla/5.0"}

def get_data(tid):
    url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Voucher/{tid}"
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    data = {
        "Transaction ID": tid,
        "Institute": "",
        "Name": "",
        "Roll": "",
        "Tech": "",
        "Semester": "",
        "Mobile": "",
        "Session": "",
        "Amount(BDT)": "",
        "Date": ""
    }

    rows = soup.find_all("tr")

    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 2:
            key = cols[0].text.strip().replace(":", "")
            value = cols[1].text.strip()

            if "Institute" in key:
                data["Institute"] = value
            elif "Name" in key:
                data["Name"] = value
            elif "Roll" in key:
                data["Roll"] = value
            elif "Tech" in key:
                data["Tech"] = value
            elif "Semester" in key:
                data["Semester"] = value
            elif "Mobile" in key:
                data["Mobile"] = value
            elif "Session" in key:
                data["Session"] = value
            elif "Amount" in key:
                data["Amount(BDT)"] = value

    return data

# ----------- START -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Ready! Roll বা Range দাও")

# ----------- SEARCH -----------
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    rolls = []

    # 👉 RANGE
    if "-" in text:
        try:
            start, end = map(int, text.split("-"))
            rolls = list(range(start, end + 1))
        except:
            return await update.message.reply_text("❌ Invalid range")

    else:
        parts = text.split()
        for p in parts:
            if p.isdigit():
                rolls.append(int(p))

    if not rolls:
        return

    msg = await update.message.reply_text("⏳ Processing...")

    total_person = 0
    last_roll = rolls[-1]

    for roll in rolls:

        url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Search?searchStr={roll}"
        r = requests.get(url, headers=headers)

        if "Details" not in r.text:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a[href*='Voucher']")

        results_text = ""
        numbers = set()
        found = False
        count = 0

        for link in links:
            tid = link['href'].split("/")[-1]
            data = get_data(tid)

            if data["Name"]:
                found = True
                count += 1
                numbers.add(data["Mobile"])

                results_text += f"""📄 Result {count}

Transaction ID: {data['Transaction ID']}
Institute: {data['Institute']}
Name: {data['Name']}
Roll: {data['Roll']}
Tech: {data['Tech']}
Semester: {data['Semester']}
Mobile: {data['Mobile']}
Session: {data['Session']}
Amount(BDT): {data['Amount(BDT)']}
Date: {data['Date']}

"""

        if found:
            total_person += 1

            keyboard = []
            for num in numbers:
                wa = f"https://wa.me/88{num}"
                tg = f"https://t.me/+88{num}"

                keyboard.append([
                    InlineKeyboardButton("📱 WhatsApp", url=wa),
                    InlineKeyboardButton("📢 Telegram", url=tg)
                ])

            await update.message.reply_text(
                results_text.strip(),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

        await asyncio.sleep(1.5)

    # 👉 DONE + NEXT BUTTON
    keyboard = []

    if len(rolls) > 1:
        keyboard.append([
            InlineKeyboardButton("🚀 Next 500", callback_data="next_auto")
        ])
        context.user_data["next_start"] = last_roll + 1

    await msg.edit_text(
        f"✅ Done!\n📊 Total: {total_person}",
        reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None
    )

# ----------- NEXT BUTTON -----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next_auto":
        start = context.user_data.get("next_start", 0)
        end = start + 499
        await query.message.reply_text(f"{start}-{end}")

# ----------- RUN BOT -----------
def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

    print("✅ Bot Running...")
    app.run_polling()

# ----------- MAIN -----------
if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    app_flask.run(host="0.0.0.0", port=10000)
