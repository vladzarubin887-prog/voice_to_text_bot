import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
    MAX_AUDIO_DURATION = int(os.getenv("MAX_AUDIO_DURATION", 300))
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")
    DATABASE_PATH = "data/bot.db"
    TEMP_FOLDER = "temp"