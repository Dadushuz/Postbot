import logging
import asyncio
import os
import json
import re
import psycopg2
import google.generativeai as genai
import requests
from datetime import datetime
from fastapi import FastAPI
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import uvicorn

# --- SOZLAMALAR ---
logging.basicConfig(level=logging.INFO)
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID") # Kanal ID string bo'lib kelishi mumkin
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# --- AI SOZLAMALARI ---
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-pro')


app = FastAPI()
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZA FUNKSIYALARI ---
def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    CREATE TABLE IF NOT EXISTS post_history (
                        id SERIAL PRIMARY KEY, 
                        topic TEXT,
                        source_url TEXT,
                        posted_at TIMESTAMP DEFAULT NOW()
                    )
                ''')
                conn.commit()
        logging.info("✅ Baza jadvallari tayyor!")
    except Exception as e:
        logging.error(f"❌ Baza xatosi: {e}")

init_db()

# --- ASOSIY FUNKSIYALAR ---
async def get_ai_content():
    if not model: return None
    prompt = """
    Menga fan, tarix, tabiat yoki texnologiya haqida juda qiziqarli fakt top.
    
    Talablar:
    1. Faktni o'zbek tilida qiziqarli va qisqa (3 gap) tushuntir.
    2. Faktni tasdiqlovchi manba (URL) top.
    3. Rasm uchun inglizcha qidiruv so'zini (search query) yoz.
    
    Javob formati (JSON):
    {"title": "Sarlavha", "explanation": "Matn...", "source_url": "url...", "image_query": "english words"}
    """
    try:
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        logging.error(f"AI Xatosi: {e}")
        return None

async def get_unsplash_image(query):
    if not UNSPLASH_ACCESS_KEY: return None
    url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_ACCESS_KEY}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()['urls']['regular']
    except: return None

# --- SERVER YO'LLARI ---
@app.get("/")
async def root(): return {"status": "🤖 Bot ishlamoqda!"}

@app.get("/trigger-post")
async def trigger_post():
    logging.info("⏳ Post tayyorlanmoqda...")
    ai_data = await get_ai_content()
    if not ai_data: return {"status": "AI xatosi"}
    
    image_url = await get_unsplash_image(ai_data['image_query'])
    caption = (f"✨ <b>{ai_data['title']}</b>\n\n{ai_data['explanation']}\n\n"
               f"🔗 <a href='{ai_data['source_url']}'>Manba</a> | 🤖 AI Post")
    
    try:
        chat_id = int(CHANNEL_ID) if CHANNEL_ID else None
        if not chat_id: return {"status": "Kanal ID yo'q"}

        if image_url:
            await bot.send_photo(chat_id=chat_id, photo=image_url, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(chat_id=chat_id, text=caption, parse_mode="HTML", disable_web_page_preview=True)
            
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO post_history (topic, source_url) VALUES (%s, %s)", (ai_data['title'], ai_data['source_url']))
                conn.commit()
        return {"status": "success"}
    except Exception as e:
        return {"status": f"Xato: {e}"}

# --- ISHGA TUSHIRISH ---
@dp.message(Command("start"))
async def start(msg: types.Message):
    await msg.answer("Bot ishlamoqda!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    config = uvicorn.Config(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
    server = uvicorn.Server(config)
    await asyncio.gather(dp.start_polling(bot), server.serve())

if __name__ == "__main__":
    asyncio.run(main())
  
