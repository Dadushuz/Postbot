import json
import logging
import httpx
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
import uvicorn
import asyncio

# ======================================================
# 🛑 DIQQAT: KALITINGIZNI SHU YERGA YOZING (Qo'shtirnoq ichiga)
MENING_KALITIM = "AIzaSyAYf34HAgo7sYJUtWC1I9RuLbabdAWhfJM"  # <-- Mana shu yerga uzun kalitni joylang
# ======================================================

# Agar Bot Token Renderda bo'lsa, os.getenv ishlatamiz. 
# Agar u ham ishlamasa, uni ham shu yerga yozish mumkin.
import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN") 
CHANNEL_ID = os.getenv("CHANNEL_ID")
# UNSPLASH KALITINI HAM AGAR ISHLAMASA SHU YERGA YOZING
UNSPLASH_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

# Loglarni yoqish
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# 1. Google Modelini tekshirish va olish
async def get_ai_content():
    # Biz 2 xil URLni sinab ko'ramiz (biri o'xshamasa, ikkinchisi)
    urls = [
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={MENING_KALITIM}",
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={MENING_KALITIM}"
    ]

    prompt = "Menga fan haqida 1 ta qiziqarli fakt ayt. Javob JSON formatda bo'lsin: {\"title\": \"Mavzu\", \"explanation\": \"Fakt\", \"source_url\": \"google.com\", \"image_query\": \"nature\"}"
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    async with httpx.AsyncClient(timeout=30) as client:
        for url in urls:
            try:
                logging.info(f"🔄 Urinib ko'rilmoqda: {url.split('models/')[1].split(':')[0]}...")
                response = await client.post(url, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    text = data['candidates'][0]['content']['parts'][0]['text']
                    # JSON tozalash
                    text = text.replace("```json", "").replace("```", "").strip()
                    logging.info("✅ Google ishladi!")
                    return json.loads(text)
                else:
                    logging.error(f"❌ Xatolik ({response.status_code}): {response.text}")
            except Exception as e:
                logging.error(f"Ulanish xatosi: {e}")
                
    return None

# 2. Rasm olish
async def get_image(query):
    if not UNSPLASH_KEY: return None
    url = f"https://api.unsplash.com/photos/random?query={query}&client_id={UNSPLASH_KEY}&orientation=landscape"
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()['urls']['regular']
        except:
            pass
    return None

# 3. Post yaratish
async def create_post():
    data = await get_ai_content()
    if not data:
        return "❌ AI ishlamadi. Loglarni tekshiring."
    
    img = await get_image(data.get("image_query", "technology"))
    caption = f"✨ <b>{data['title']}</b>\n\n{data['explanation']}\n\n🔗 Manba: {data['source_url']}"
    
    try:
        if img:
            await bot.send_photo(CHANNEL_ID, photo=img, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, text=caption, parse_mode="HTML")
        return "✅ Post chiqdi!"
    except Exception as e:
        return f"❌ Telegram xatosi: {e}"

# Server
@app.get("/")
def read_root(): return {"status": "Active"}

@app.get("/trigger-post")
async def trigger():
    res = await create_post()
    return {"result": res}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
