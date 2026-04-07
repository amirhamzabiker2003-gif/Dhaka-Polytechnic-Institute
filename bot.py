import requests
import asyncio
from bs4 import BeautifulSoup

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler
)

BOT_TOKEN = "8723976334:AAE0vOE-tZ7pZvJXBTLNUYI1ozoxvOL0tp0"

headers = {
    "User-Agent": "Mozilla/5.0"
}

# ----------- DATA SCRAPER -----------
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

    date_tag = soup.find(string=lambda x: x and "Date" in x)
    if date_tag:
        try:
            data["Date"] = date_tag.find_next().text.strip()
        except:
            pass

    return data


# ----------- SEND RESULT -----------
async def process_roll(update, data_list):

    final_text = ""
    unique_numbers = []

    for i, data in enumerate(data_list, 1):

        phone = data["Mobile"]

        if phone.startswith("0"):
            phone = "880" + phone[1:]

        final_text += f"""📄 Result {i}

<pre>
Transaction ID: {data['Transaction ID']}
Institute     : {data['Institute']}
Name          : {data['Name']}
Roll          : {data['Roll']}
Tech          : {data['Tech']}
Semester      : {data['Semester']}
Mobile        : {data['Mobile']}
Session       : {data['Session']}
Amount(BDT)   : {data['Amount(BDT)']}
Date          : {data['Date']}
</pre>

"""

        if phone not in unique_numbers:
            unique_numbers.append(phone)

    keyboard = []

    for phone in unique_numbers:
        keyboard.append([
            InlineKeyboardButton("📱 WhatsApp", url=f"https://wa.me/{phone}"),
            InlineKeyboardButton("📢 Telegram", url=f"https://t.me/{phone}")
        ])

    await update.message.reply_text(
        final_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ----------- SEARCH -----------
async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    if "-" not in text:
        return await update.message.reply_text("❌ Range দাও (e.g. 656000-656499)")

    start, end = map(int, text.split("-"))

    context.user_data["current_end"] = end

    rolls = list(range(start, end + 1))

    msg = await update.message.reply_text("⏳ Processing...")

    total_person = 0

    for i, roll in enumerate(rolls, 1):

        url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Search?searchStr={roll}"
        r = requests.get(url, headers=headers)

        if "Details" not in r.text:
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        links = soup.select("a[href*='Voucher']")

        data_list = []

        for link in links:
            tid = link['href'].split("/")[-1]
            data = get_data(tid)

            if data["Name"]:
                data_list.append(data)

        if data_list:
            total_person += 1
            await process_roll(update, data_list)

        await msg.edit_text(
            f"⏳ Processing...\n🔢 Roll: {roll}\n📊 Person: {total_person}\n✅ Progress: {i}/{len(rolls)}"
        )

    # ✅ Done
    await update.message.reply_text(
        f"✅ Done!\n📊 Total: {total_person}"
    )

    # 🚀 Next button
    keyboard = [
        [InlineKeyboardButton("🚀 Next 500", callback_data="next_auto")]
    ]

    await update.message.reply_text(
        "👇 Click for next batch",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ----------- NEXT BUTTON -----------
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "next_auto":

        start = context.user_data.get("current_end", 0) + 1
        end = start + 499

        context.user_data["current_end"] = end

        rolls = list(range(start, end + 1))

        await query.message.reply_text("⏳ Processing next 500...")

        total_person = 0

        for roll in rolls:

            url = f"https://billpay.sonalibank.com.bd/dhkPolytechnic/Home/Search?searchStr={roll}"
            r = requests.get(url, headers=headers)

            if "Details" not in r.text:
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            links = soup.select("a[href*='Voucher']")

            data_list = []

            for link in links:
                tid = link['href'].split("/")[-1]
                data = get_data(tid)

                if data["Name"]:
                    data_list.append(data)

            if data_list:
                total_person += 1
                await process_roll(query, data_list)

            await asyncio.sleep(1)

        # ✅ Done
        await query.message.reply_text(
            f"✅ Done!\n📊 Total: {total_person}"
        )

        # 🚀 Next again
        keyboard = [
            [InlineKeyboardButton("🚀 Next 500", callback_data="next_auto")]
        ]

        await query.message.reply_text(
            "👇 Click for next batch",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ----------- START -----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Ready! Range দাও (e.g. 656000-656499)")


# ----------- MAIN -----------
app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search))

print("✅ Bot Running...")
app.run_polling()
