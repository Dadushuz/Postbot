import os
import json
import logging
import random
import httpx
from dotenv import load_dotenv
from aiogram import Bot
from fastapi import FastAPI

# ================== BASIC SETUP ==================
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# ================== CONTENT CONFIG ==================
TOPICS = [
    "ancient history mystery",
    "space and universe",
    "human psychology",
    "weird science facts",
    "nature secrets",
    "lost civilizations",
]

CTA_TEXT = "\n\n💬 Izohda fikringni yoz!"

# ================== UNSPLASH ==================
async def get_image(query: str):
    if not UNSPLASH_ACCESS_KEY:
        return None

    url = "https://api.unsplash.com/photos/random"
    params = {
        "query": query,
        "orientation": "landscape",
        "client_id": UNSPLASH_ACCESS_KEY,
    }

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            if r.status_code == 200:
                return r.json()["urls"]["regular"]
    except Exception as e:
        logging.error(f"❌ Unsplash xato: {e}")

    return None

# ================== GEMINI AI (REST · STABLE) ==================
async def get_ai_content():
    if not GOOGLE_API_KEY:
        return None

    topic = random.choice(TOPICS)

    # Agar 1.5-pro ishlamasa, keyinchalik "gemini-pro" ga o'zgartirish mumkin
    url = (
    "https://generativelanguage.googleapis.com/"
    f"v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
     )

    prompt = (
        "Sen ilmiy-ommabop Telegram kanallar uchun kontent yozuvchi mutaxassissan.\n"
        "O‘zbekiston auditoriyasi uchun juda qiziqarli va kam tanilgan fakt yoz.\n\n"
        f"Mavzu yo‘nalishi: {topic}\n\n"
        "Talablar:\n"
        "- Sarlavha diqqat tortuvchi bo‘lsin\n"
        "- Matn 3–5 gapdan iborat bo‘lsin\n"
        "- Oddiy va jonli o‘zbek tilida yoz\n"
        "- Oxirida o‘ylantiruvchi savol bo‘lsin\n"
        "- Clickbait bo‘lmasin\n\n"
        "Faqat JSON formatda javob ber:\n"
        "{"
        "\"title\": \"Qiziqarli sarlavha\", "
        "\"explanation\": \"Asosiy matn + savol\", "
        "\"source_url\": \"https://en.wikipedia.org\", "
        "\"image_query\": \"strong visual english keyword\""
        "}"
    )

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.post(url, json=payload)

            if r.status_code != 200:
                logging.error(f"❌ Gemini xato: {r.text}")
                return None

            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.replace("```json", "").replace("```", "").strip()

            return json.loads(text)

    except Exception as e:
        logging.error(f"❌ AI parsing xato: {e}")
        return None

# ================== POST CREATOR ==================
async def create_post():
    logging.info("⏳ Post tayyorlanmoqda...")

    ai_data = await get_ai_content()
    if not ai_data:
        logging.error("❌ AI ishlamadi")
        return False

    image_url = await get_image(ai_data.get("image_query", "nature"))

    caption = (
        f"✨ <b>{ai_data['title']}</b>\n\n"
        f"{ai_data['explanation']}"
        f"{CTA_TEXT}\n\n"
        f"🔗 <a href='{ai_data['source_url']}'>Manba</a> | 🤖 AI"
    )

    try:
        if image_url:
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=image_url,
                caption=caption,
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=caption,
                parse_mode="HTML"
            )
        return True

    except Exception as e:
        logging.error(f"❌ Telegram xato: {e}")
        return False

# ================== FASTAPI ==================
@app.get("/")
async def root():
    return {"status": "Bot ishlayapti ✅"}

@app.get("/trigger-post")
async def trigger_post():
    ok = await create_post()
    if ok:
        return {"success": True, "message": "Post chiqdi!"}
    return {"success": False, "message": "Xatolik"}

# ================== RUN ==================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
