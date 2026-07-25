from aiogram import Router, F, types
from aiogram.types import FSInputFile
import os
from datetime import datetime

from bot.config import Config
from bot.database import Database
from bot.services.whisper_service import WhisperService
from bot.services.audio_processor import AudioProcessor

router = Router()

# Инициализация
db = Database(Config.DATABASE_PATH)
whisper = WhisperService(
    model_size=Config.WHISPER_MODEL,
    device="cpu"
)
audio_processor = AudioProcessor(Config.TEMP_FOLDER)

# Хранилище активных задач
active_tasks = {}

@router.message(F.voice)
async def handle_voice(message: types.Message, bot):
    user_id = message.from_user.id
    voice = message.voice
    
    # Проверка длительности
    if voice.duration > Config.MAX_AUDIO_DURATION:
        await message.reply(
            f"⏰ Длительность превышает {Config.MAX_AUDIO_DURATION} секунд.\n"
            f"Пожалуйста, отправьте более короткое сообщение."
        )
        return
    
    # Проверка, не обрабатывается ли уже сообщение
    if user_id in active_tasks:
        await message.reply("⏳ Ваше предыдущее сообщение еще обрабатывается. Подождите.")
        return
    
    # Регистрируем пользователя
    db.get_or_create_user(
        user_id,
        message.from_user.username,
        message.from_user.first_name,
        message.from_user.last_name
    )
    
    # Статус
    status_msg = await message.reply("🎙️ Принимаю голосовое сообщение...")
    
    # Добавляем в активные задачи
    active_tasks[user_id] = True
    
    try:
        # Получаем файл
        file = await bot.get_file(voice.file_id)
        
        # Скачиваем
        ogg_path = await audio_processor.download_audio(file, voice.file_id)
        
        # Получаем длительность
        duration = await audio_processor.get_duration(ogg_path)
        
        # Конвертируем в WAV
        wav_path = await audio_processor.convert_to_wav(ogg_path)
        
        await status_msg.edit_text(
            f"🔄 Идет распознавание...\n"
            f"⏱ Длительность: {duration} сек.\n"
            f"⏳ Это может занять некоторое время..."
        )
        
        # Распознаем
        text, language, elapsed = whisper.transcribe(wav_path)
        
        if not text or text.strip() == "":
            await status_msg.edit_text(
                "❌ Не удалось распознать речь.\n"
                "Попробуйте говорить четче."
            )
            return
        
        # Сохраняем в БД
        db.save_transcription(user_id, voice.file_id, duration, text, language)
        db.update_user_stats(user_id, duration)
        
        # Отправляем результат
        await status_msg.delete()
        
        if len(text) > 4000:
            # Если текст длинный - отправляем файлом
            txt_filename = f"transcription_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            txt_path = os.path.join(Config.TEMP_FOLDER, txt_filename)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            await message.reply_document(
                FSInputFile(txt_path),
                caption=f"📄 Расшифровка ({duration} сек., {language})"
            )
            
            os.remove(txt_path)
        else:
            await message.reply(
                f"📝 *Расшифровка:*\n\n{text}\n\n"
                f"⏱ {duration} сек. | 🌐 {language} | ⏳ {elapsed:.1f} сек.",
                parse_mode="Markdown"
            )
        
        # Удаляем временные файлы
        await audio_processor.cleanup(ogg_path, wav_path)
        
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)}")
        print(f"Ошибка: {e}")
    finally:
        # Убираем из активных задач
        if user_id in active_tasks:
            del active_tasks[user_id]