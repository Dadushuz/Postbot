import os
import json
import logging
import httpx
from aiogram import Bot, Dispatcher
from fastapi import FastAPI
import uvicorn
from groq import Groq  # <-- Yangi AI
from dotenv import load_dotenv

# Sozlamalar
logging.basicConfig(level=logging.INFO)
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") # <-- Yangi kalit
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY")

bot = Bot(token=BOT_TOKEN)
app = FastAPI()

# --- 1. RASM OLISH (O'zgarmadi) ---
async def get_image(query):
    if not UNSPLASH_ACCESS_KEY: return None
    url = "https://api.unsplash.com/photos/random"
    params = {"query": query, "orientation": "landscape", "client_id": UNSPLASH_ACCESS_KEY}
    
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                return resp.json()['urls']['regular']
        except Exception as e:
            logging.error(f"Rasm xatosi: {e}")
    return None

# --- 2. YANGI AI (Groq - Llama 3) ---
async def get_ai_content():
    if not GROQ_API_KEY:
        logging.error("❌ Groq kaliti yo'q!")
        return None

    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = (
        "Sen Telegram kanal uchun qiziqarli faktlar yozadigan botsan. "
        "Menga fan, tarix, tabiat yoki texnologiya haqida bitta juda qiziqarli va noyob fakt ayt. "
        "Javobni faqat JSON formatda qaytar: "
        "{\"title\": \"Sarlavha (O'zbekcha)\", \"explanation\": \"Qiziqarli fakt matni (3-4 gap, O'zbekcha)\", \"source\": \"Manba nomi\", \"image_query\": \"Inglizcha kalit so'z\"}"
    )

    try:
        logging.info("🧠 Groq (Llama 3) o'ylamoqda...")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",  # <-- Juda tez va bepul model
            response_format={"type": "json_object"} # <-- JSON berishini kafolatlaymiz
        )
        
        content = chat_completion.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        logging.error(f"❌ Groq xatosi: {e}")
        return None

# --- 3. POST TAYYORLASH ---
async def create_post():
    data = await get_ai_content()
    
    if not data:
        return "❌ AI ishlamadi. Loglarni qarang."
    
    img = await get_image(data.get("image_query", "nature"))
    caption = f"⚡️ <b>{data['title']}</b>\n\n{data['explanation']}\n\nManba: {data['source']} | 🤖 Bot"

    try:
        if img:
            await bot.send_photo(CHANNEL_ID, photo=img, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, text=caption, parse_mode="HTML")
        return "✅ Post chiqdi! (Groq orqali)"
    except Exception as e:
        logging.error(f"Telegram xatosi: {e}")
        return f"Telegram xatosi: {e}"

# --- SERVER ---
@app.get("/")
def root(): return {"status": "Groq Bot Active 🚀"}

@app.get("/trigger-post")
async def trigger():
    res = await create_post()
    return {"result": res}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
