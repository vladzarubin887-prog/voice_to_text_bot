from aiogram import Router, types
from aiogram.filters import Command

from bot.config import Config
from bot.database import Database

router = Router()
db = Database(Config.DATABASE_PATH)

def is_admin(user_id: int) -> bool:
    return user_id in Config.ADMIN_IDS

@router.message(Command("stats"))
async def admin_stats(message: types.Message):
    if not is_admin(message.from_user.id):
        return
    
    stats = db.get_admin_stats()
    
    await message.reply(
        f"📊 *Статистика бота*\n\n"
        f"👥 Пользователей: {stats['total_users']}\n"
        f"📝 Запросов: {stats['total_requests']}\n"
        f"⏱ Обработано: {stats['total_duration_minutes']} мин.",
        parse_mode="Markdown"
    )