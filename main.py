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

# --- 2. PROFESSIONAL AI (Groq Llama 3.3 - 70B) ---
async def get_ai_content():
    if not GROQ_API_KEY:
        return None

    client = Groq(api_key=GROQ_API_KEY)
    
    prompt = (
        "Sen professional ilmiy-ommabop jurnalistsan. "
        "Menga koinot, tabiat, texnologiya yoki inson psixologiyasi haqida hayratlanarli fakt yoz.\n\n"
        "Talablar:\n"
        "1. Til: Sof o'zbek tilida, imlo xatolarisiz (o', g', sh, ch harflariga diqqat qil).\n"
        "2. Uslub: O'quvchini jalb qiluvchi, hayratga soluvchi ohangda bo'lsin.\n"
        "3. Manba: Ma'lumot haqiqiy bo'lsin va unga tegishli ishonchli inglizcha manba linkini (URL) top.\n\n"
        "Faqat JSON formatda javob ber:\n"
        "{"
        "\"title\": \"Sarlavha (Emoji bilan)\", "
        "\"explanation\": \"Faktning batafsil va qiziqarli bayoni\", "
        "\"source_name\": \"Manba nomi (masalan: NASA, BBC, Wikipedia)\", "
        "\"source_url\": \"Haqiqiy manba linki (URL)\", "
        "\"image_query\": \"Rasm qidirish uchun inglizcha kalit so'z\""
        "}"
    )

    try:
        logging.info("🧠 Llama 3.3 professional matn va manba qidirmoqda...")
        # TO'G'IRLANGAN QATOR: .completions.create
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.6,
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        return json.loads(content)
        
    except Exception as e:
        logging.error(f"❌ Groq xatosi: {e}")
        return None


# --- 3. IDEAL POST DESIGN (Havola bilan) ---
async def create_post():
    data = await get_ai_content()
    
    if not data:
        return "❌ AI ishlamadi."
    
    img = await get_image(data.get("image_query", "science technology"))
    
    # Post dizayni: Sarlavha, Matn va Pastda manba linki
    caption = (
        f"🌟 <b>{data['title']}</b>\n\n"
        f"{data['explanation']}\n\n"
        f"📖 <b>Manba:</b> <a href='{data['source_url']}'>{data['source_name']}</a>\n\n"
        f"➖➖➖➖➖➖➖➖\n"
        f"💡 <b>@SeningKanaling</b> — Har kuni yangi bilimlar!" # BU YERGA KANALINGIZ LINKINI YOZING
    )

    try:
        if img:
            # send_photo ishlatamiz, rasm va tagida chiroyli matn bo'ladi
            await bot.send_photo(
                chat_id=CHANNEL_ID, 
                photo=img, 
                caption=caption, 
                parse_mode="HTML",
                disable_web_page_preview=False # Linkning kichik rasmi chiqishi uchun
            )
        else:
            await bot.send_message(
                chat_id=CHANNEL_ID, 
                text=caption, 
                parse_mode="HTML",
                disable_web_page_preview=False
            )
        return "✅ Professional post chiqdi!"
    except Exception as e:
        logging.error(f"Telegram xatosi: {e}")
        return f"Xatolik: {e}"
        
# --- SERVER ---
@app.get("/")
def root(): return {"status": "Groq Bot Active 🚀"}

@app.get("/trigger-post")
async def trigger():
    res = await create_post()
    return {"result": res}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)
