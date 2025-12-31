import os
import json
import logging
import asyncio
import requests # Bizga faqat shu kerak, bu hamma joyda bor
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# O'zgaruvchilarni olish
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Botni yaratish
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- 1. RASM QISMI (Unsplash) ---
async def get_image(query):
    if not UNSPLASH_ACCESS_KEY: return None
    url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['urls']['regular']
    except Exception as e:
        logging.error(f"Rasm xatosi: {e}")
    return None

# --- 2. AI QISMI (Kutubxonasiz, to'g'ridan-to'g'ri ulanish) ---
async def get_ai_content():
    if not GOOGLE_API_KEY: return None
    
    # MANA SHU YER "BETON" YECHIM 👇
    # Hech qanday kutubxona kerak emas, to'g'ridan-to'g'ri Googlega ulanamiz
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
    headers = {'Content-Type': 'application/json'}
    
    prompt = "Menga fan, tarix yoki tabiat haqida qiziqarli va noyob fakt ayt. Javob faqat JSON formatda bo'lsin: {\"title\": \"Mavzu\", \"explanation\": \"Qisqa malumot (o'zbekcha)\", \"source_url\": \"google.com\", \"image_query\": \"English keyword for image\"}"
    
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        # Agar xato bo'lsa logga chiqaramiz
        if response.status_code != 200:
            logging.error(f"AI Xatosi: {response.text}")
            return None
            
        data = response.json()
        # Javobni tozalash
        text = data['candidates'][0]['content']['parts'][0]['text']
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        logging.error(f"Ulanish xatosi: {e}")
        return None

# --- 3. POST TAYYORLASH VA YUBORISH ---
async def create_post():
    logging.info("⏳ Post tayyorlanmoqda...")
    
    # 1. AIdan malumot olamiz
    ai_data = await get_ai_content()
    if not ai_data:
        logging.error("❌ AI ishlamadi")
        return False

    # 2. Rasm olamiz
    image_url = await get_image(ai_data.get("image_query", "nature"))
    
    # 3. Post matnini yasaymiz
    caption = f"✨ **{ai_data['title']}**\n\n{ai_data['explanation']}\n\n🔗 [Manba]({ai_data['source_url']}) | 🤖 AI Post"

    # 4. Kanalga yuboramiz
    try:
        if image_url:
            await bot.send_photo(chat_id=CHANNEL_ID, photo=image_url, caption=caption, parse_mode="Markdown")
        else:
            await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="Markdown")
        return True
    except Exception as e:
        logging.error(f"Telegram xatosi: {e}")
        return False

# --- WEBHOOK (Trigger) ---
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
async def root():
    return {"message": "Bot ishlayapti!"}

@app.get("/trigger-post")
async def trigger_post():
    result = await create_post()
    if result:
        return {"status": "success", "message": "Post chiqdi!"}
    return {"status": "error", "message": "Xatolik bo'ldi"}

# Ishga tushirish
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
        
