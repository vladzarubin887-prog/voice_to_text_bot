from aiogram import Router, types
from aiogram.filters import Command

from bot.config import Config
from bot.database import Database

router = Router()
db = Database(Config.DATABASE_PATH)

@router.message(Command("start"))
async def start_command(message: types.Message):
    user = message.from_user
    
    db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    await message.reply(
        f"👋 Привет, {user.first_name}!\n\n"
        "Я бот для распознавания голосовых сообщений.\n\n"
        "🎙️ Отправь мне голосовое сообщение, и я превращу его в текст.\n\n"
        "📖 Команды:\n"
        "/start - приветствие\n"
        "/stats - моя статистика\n"
        "/help - помощь\n\n"
        f"⏰ Макс. длительность: {Config.MAX_AUDIO_DURATION} сек."
    )

@router.message(Command("help"))
async def help_command(message: types.Message):
    await message.reply(
        "📖 *Помощь*\n\n"
        "🎙️ Отправь голосовое сообщение\n"
        "📋 Команды:\n"
        "/start - приветствие\n"
        "/stats - статистика\n"
        "/help - эта справка\n\n"
        f"⚙️ Макс. длительность: {Config.MAX_AUDIO_DURATION} сек.",
        parse_mode="Markdown"
    )

@router.message(Command("stats"))
async def stats_command(message: types.Message):
    stats = db.get_user_stats(message.from_user.id)
    
    await message.reply(
        f"📊 *Статистика*\n\n"
        f"📝 Запросов: {stats['total_requests']}\n"
        f"⏱ Обработано: {stats['total_duration_minutes']} мин.",
        parse_mode="Markdown"
    )