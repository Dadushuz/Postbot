import os
import json
import logging
import httpx
from aiogram import Bot
from aiogram.types import URLInputFile
from fastapi import FastAPI
import uvicorn
from groq import Groq
from dotenv import load_dotenv

# Sozlamalar
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

async def get_image(query):
    if not UNSPLASH_ACCESS_KEY: return None
    url = f"https://api.unsplash.com/photos/random?query={query}&orientation=landscape&client_id={UNSPLASH_ACCESS_KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                return resp.json()['urls']['regular']
        except: pass
    return None

async def get_ai_content():
    if not GROQ_API_KEY: return None
    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = (
        "Sen professional jurnalistsan. Fan, koinot yoki tabiat haqida hayratlanarli fakt yoz. "
        "Matn sof o'zbek tilida (o', g', sh, ch harflari bilan) bo'lsin. "
        "Faqat JSON formatda javob ber: "
        "{\"title\": \"Sarlavha 🌟\", \"explanation\": \"Batafsil matn\", \"source_name\": \"NASA/BBC\", \"source_url\": \"https://link.com\", \"image_query\": \"space\"}"
    )

    try:
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(chat_completion.choices[0].message.content)
    except Exception as e:
        logging.error(f"❌ AI xatosi: {e}")
        return None

async def create_post():
    data = await get_ai_content()
    if not data: return False
    
    img_url = await get_image(data.get("image_query", "nature"))
    
    # Professional dizayn (HTML)
    caption = (
        f"🌟 <b>{data['title']}</b>\n\n"
        f"{data['explanation']}\n\n"
        f"🔗 <b>Manba:</b> <a href='{data['source_url']}'>{data['source_name']}</a>\n\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💡 <b>@MAQSADIM</b> — Har kuni yangi bilimlar!"
    )

    try:
        if img_url:
            # Xato tuzatildi: disable_web_page_preview olib tashlandi
            await bot.send_photo(
                chat_id=CHANNEL_ID, 
                photo=img_url, 
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
        logging.error(f"❌ Telegram xatosi: {e}")
        return False

@app.get("/trigger-post")
async def trigger():
    if await create_post():
        return {"status": "success", "message": "Post chiqdi!"}
    return {"status": "error", "message": "Xatolik bo'ldi"}

@app.get("/")
def home(): return {"status": "Bot is Live"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
