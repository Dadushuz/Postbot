import os
import json
import logging
import httpx
from dotenv import load_dotenv
from aiogram import Bot
from fastapi import FastAPI

# ================== SOZLAMALAR ==================
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

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

# ================== GEMINI AI (100% ISHLAYDIGAN) ==================
async def get_ai_content():
    if not GOOGLE_API_KEY:
        return None

    # ❗ MUHIM: REST API uchun ENG ISHONCHLI MODEL
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1/models/gemini-1.5-pro:generateContent?key={GOOGLE_API_KEY}"
    )

    prompt = (
        "Fan, tarix yoki tabiat haqida qiziqarli va noyob fakt ayt.\n"
        "Faqat JSON formatda javob ber:\n"
        "{"
        "\"title\": \"Mavzu\", "
        "\"explanation\": \"Qisqa tushuntirish (o‘zbekcha)\", "
        "\"source_url\": \"https://google.com\", "
        "\"image_query\": \"english keyword\""
        "}"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=20) as client:
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

# ================== POST YARATISH ==================
async def create_post():
    logging.info("⏳ Post tayyorlanmoqda...")

    ai_data = await get_ai_content()
    if not ai_data:
        logging.error("❌ AI ishlamadi")
        return False

    image_url = await get_image(ai_data.get("image_query", "nature"))

    caption = (
        f"✨ <b>{ai_data['title']}</b>\n\n"
        f"{ai_data['explanation']}\n\n"
        f"🔗 <a href='{ai_data['source_url']}'>Manba</a> | 🤖 AI Post"
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

# ================== WEB ==================
@app.get("/")
async def root():
    return {"status": "Bot ishlayapti ✅"}

@app.get("/trigger-post")
async def trigger_post():
    ok = await create_post()
    return {"success": ok}

# ================== RUN ==================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)
