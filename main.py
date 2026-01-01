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

# --- 2. IDEAL AI (Groq - Llama 3.3 70B) ---
async def get_ai_content():
    if not GROQ_API_KEY:
        return None

    client = Groq(api_key=GROQ_API_KEY)
    
    # AIga mukammal o'zbek tili va jozibadorlik haqida buyruq beramiz
    prompt = (
        "Sen professionall yozuvchi va ilmiy-ommabop kanal adminisan. "
        "Menga fan, koinot, tarix yoki tabiat haqida HAYRATLANARLI fakt ayt. "
        "Qoidalaring:\n"
        "1. Til: Sof o'zbek tilida, imlo xatolarisiz yoz (o', g', sh, ch harflariga diqqat qil).\n"
        "2. Uslub: Ma'lumot quruq bo'lmasin, o'quvchini hayratga solsin.\n"
        "3. Struktura: Diqqat tortuvchi sarlavha, asosiy qism va oxirida o'ylantiruvchi qisqa savol.\n\n"
        "Javobni faqat JSON formatda qaytar: "
        "{\"title\": \"Sarlavha (EMOJI bilan)\", \"explanation\": \"Batafsil matn (jozibador)\", \"source\": \"Manba nomi\", \"image_query\": \"Inglizcha rasm uchun kalit so'z\"}"
    )

    try:
        logging.info("🧠 Llama 3.3 ideal matn tayyorlamoqda...")
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7, # Bir oz ijodiylik qo'shamiz
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        logging.error(f"❌ Groq xatosi: {e}")
        return None

# --- 3. POST TAYYORLASH (Chiroyli dizayn) ---
async def create_post():
    data = await get_ai_content()
    
    if not data:
        return "❌ AI ishlamadi."
    
    img = await get_image(data.get("image_query", "science technology"))
    
    # Telegram uchun chiroyli dizayn (HTML)
    caption = (
        f"🌟 <b>{data['title']}</b>\n\n"
        f"{data['explanation']}\n\n"
        f"📖 <b>Manba:</b> <i>{data['source']}</i>\n\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💡 @SeningKanaling — Har kuni yangi bilimlar!" # Kanalingiz linkini yozing
    )

    try:
        if img:
            await bot.send_photo(CHANNEL_ID, photo=img, caption=caption, parse_mode="HTML")
        else:
            await bot.send_message(CHANNEL_ID, text=caption, parse_mode="HTML")
        return "✅ Ideal post chiqdi!"
    except Exception as e:
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
