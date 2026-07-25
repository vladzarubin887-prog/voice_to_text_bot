import os
import sqlite3
import time
import asyncio
import logging
import random
from pathlib import Path
from datetime import datetime, timedelta
from contextlib import contextmanager
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router, F, types
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from faster_whisper import WhisperModel
from pydub import AudioSegment

os.environ["HTTP_PROXY"] = ""
os.environ["HTTPS_PROXY"] = ""
os.environ["NO_PROXY"] = "*"

from deep_translator import GoogleTranslator

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN", "8771022122:AAH04pxTHzoen9xBaVMdw0IywgqO28O14YM")
ADMIN_IDS = [5252362476]
MAX_AUDIO_DURATION = 300
WHISPER_MODEL = "tiny"
DATABASE_PATH = "data/bot.db"
TEMP_FOLDER = "temp"

Path(TEMP_FOLDER).mkdir(exist_ok=True)
Path("data").mkdir(exist_ok=True)
Path("models").mkdir(exist_ok=True)

LANGUAGES = {
    'ru': '🇷🇺 Русский',
    'en': '🇬🇧 English',
    'de': '🇩🇪 Deutsch',
    'fr': '🇫🇷 Français',
    'es': '🇪🇸 Español',
    'it': '🇮🇹 Italiano',
    'zh-cn': '🇨🇳 中文',
    'ja': '🇯🇵 日本語',
    'ko': '🇰🇷 한국어',
    'ar': '🇸🇦 العربية',
    'pt': '🇵🇹 Português'
}

TEXTS = {
    'ru': {
        'start_first': "👋 Привет, {name}!\n\n🌍 *Выберите язык, на котором я буду общаться с вами:*",
        'start_back': "👋 С возвращением, {name}!\n\n🌍 Язык общения: {lang}\n\n🎙️ Отправь голосовое → распознаю и переведу\n📝 Отправь текст → переведу\n💡 Совет дня\n🔥 Стрик и статистика",
        'lang_changed': "✅ Язык общения установлен: *{lang}*",
        'stats': "📊 *Статистика*\n\n📝 Всего запросов: {total}\n⏱ Обработано минут: {minutes}\n🔥 Сегодня: {daily} запросов\n🔥 Стрик: {streak} дней",
        'history': "📜 *Последние расшифровки:*\n\n",
        'history_empty': "📭 У тебя пока нет расшифровок.",
        'tip': "💡 *Совет дня:*\n\n{tip}",
        'help': "📖 *Помощь*\n\n🎙️ Голосовое → текст + перевод\n📝 Текст → перевод\n📊 Статистика\n📝 История\n💡 Совет дня\n🌍 Сменить язык\n📩 Отзывы",
        'feedback': "📩 Напиши свой отзыв или предложение.\n\nПросто отправь текст сообщением!",
        'feedback_thanks': "✅ Спасибо за отзыв! ❤️",
        'feedback_admin': "📩 Новый отзыв от @{user}:\n\n{text}",
        'feedback_empty': "📭 Отзывов пока нет.",
        'feedback_all': "📩 *Все отзывы:*\n\n",
        'feedback_deleted': "✅ Отзыв #{id} удален.",
        'feedback_not_found': "❌ Отзыв с ID {id} не найден.",
        'feedback_delete_usage': "ℹ️ Использование: `/delete_feedback ID`",
        'feedback_delete_error': "❌ ID должен быть числом.",
        'cancel': "✅ Отмена.",
        'short': "📝 Слишком коротко.",
        'error': "❌ Ошибка: {error}",
        'max_duration': "⏰ Максимум {max} сек.",
        'wait': "⏳ Подожди...",
        'recognizing': "🎙️ Принимаю...",
        'recognizing_progress': "🔄 Распознаю... ({duration} сек.)",
        'not_recognized': "❌ Не распознано.",
        'access_denied': "⛔ Доступ запрещен.",
        'menu_stats': "📊 Статистика",
        'menu_history': "📝 История",
        'menu_tip': "💡 Совет дня",
        'menu_lang': "🌍 Сменить язык",
        'menu_help': "❓ Помощь",
        'menu_feedback': "📩 Отзыв",
        'choose_lang': "🌍 *Выберите язык для перевода*\n\nТекущий язык: {lang}",
        'lang_set': "🌍 *Выберите язык, на котором я буду общаться с вами:*"
    },
    'en': {
        'start_first': "👋 Hello, {name}!\n\n🌍 *Choose the language I will use to communicate with you:*",
        'start_back': "👋 Welcome back, {name}!\n\n🌍 Language: {lang}\n\n🎙️ Send voice → recognize and translate\n📝 Send text → translate\n💡 Tip of the day\n🔥 Streak and statistics",
        'lang_changed': "✅ Language set to: *{lang}*",
        'stats': "📊 *Statistics*\n\n📝 Total requests: {total}\n⏱ Minutes processed: {minutes}\n🔥 Today: {daily} requests\n🔥 Streak: {streak} days",
        'history': "📜 *Last transcriptions:*\n\n",
        'history_empty': "📭 You have no transcriptions yet.",
        'tip': "💡 *Tip of the day:*\n\n{tip}",
        'help': "📖 *Help*\n\n🎙️ Voice → text + translation\n📝 Text → translation\n📊 Statistics\n📝 History\n💡 Tip of the day\n🌍 Change language\n📩 Feedback",
        'feedback': "📩 Write your feedback or suggestion.\n\nJust send a text message!",
        'feedback_thanks': "✅ Thank you for your feedback! ❤️",
        'feedback_admin': "📩 New feedback from @{user}:\n\n{text}",
        'feedback_empty': "📭 No feedback yet.",
        'feedback_all': "📩 *All feedback:*\n\n",
        'feedback_deleted': "✅ Feedback #{id} deleted.",
        'feedback_not_found': "❌ Feedback with ID {id} not found.",
        'feedback_delete_usage': "ℹ️ Usage: `/delete_feedback ID`",
        'feedback_delete_error': "❌ ID must be a number.",
        'cancel': "✅ Cancelled.",
        'short': "📝 Too short.",
        'error': "❌ Error: {error}",
        'max_duration': "⏰ Maximum {max} sec.",
        'wait': "⏳ Please wait...",
        'recognizing': "🎙️ Receiving...",
        'recognizing_progress': "🔄 Recognizing... ({duration} sec.)",
        'not_recognized': "❌ Not recognized.",
        'access_denied': "⛔ Access denied.",
        'menu_stats': "📊 Statistics",
        'menu_history': "📝 History",
        'menu_tip': "💡 Tip of the day",
        'menu_lang': "🌍 Change language",
        'menu_help': "❓ Help",
        'menu_feedback': "📩 Feedback",
        'choose_lang': "🌍 *Choose language for translation*\n\nCurrent language: {lang}",
        'lang_set': "🌍 *Choose the language I will use to communicate with you:*"
    }
}

class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_requests INTEGER DEFAULT 0,
                total_duration INTEGER DEFAULT 0,
                daily_requests INTEGER DEFAULT 0,
                last_active DATE,
                streak INTEGER DEFAULT 0,
                last_request DATE,
                preferred_lang TEXT DEFAULT 'ru'
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS transcriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                file_id TEXT,
                duration INTEGER,
                text TEXT,
                language TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            for col in ['daily_requests', 'last_active', 'streak', 'last_request', 'preferred_lang']:
                try:
                    cursor.execute(f'ALTER TABLE users ADD COLUMN {col}')
                except:
                    pass
            conn.commit()
    
    def get_or_create_user(self, user_id, username=None, first_name=None, last_name=None):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
            if not cursor.fetchone():
                cursor.execute(
                    'INSERT INTO users (user_id, username, first_name, last_name, last_active, streak, last_request) VALUES (?, ?, ?, ?, ?, ?, ?)',
                    (user_id, username, first_name, last_name, datetime.now().date(), 1, datetime.now().date())
                )
                conn.commit()
                return False
            else:
                cursor.execute('UPDATE users SET last_active = ? WHERE user_id = ?', (datetime.now().date(), user_id))
                cursor.execute('SELECT last_request FROM users WHERE user_id = ?', (user_id,))
                row = cursor.fetchone()
                if row and row['last_request']:
                    try:
                        last_req = datetime.strptime(row['last_request'], '%Y-%m-%d').date()
                        if (datetime.now().date() - last_req).days == 1:
                            cursor.execute('UPDATE users SET streak = streak + 1 WHERE user_id = ?', (user_id,))
                        elif (datetime.now().date() - last_req).days > 1:
                            cursor.execute('UPDATE users SET streak = 1 WHERE user_id = ?', (user_id,))
                    except:
                        pass
                    cursor.execute('UPDATE users SET last_request = ? WHERE user_id = ?', (datetime.now().date(), user_id))
                conn.commit()
                return True
    
    def set_language(self, user_id, lang_code):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET preferred_lang = ? WHERE user_id = ?', (lang_code, user_id))
            conn.commit()
    
    def get_language(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT preferred_lang FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return row['preferred_lang'] if row else 'ru'
    
    def save_transcription(self, user_id, file_id, duration, text, language):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO transcriptions (user_id, file_id, duration, text, language) VALUES (?, ?, ?, ?, ?)',
                (user_id, file_id, duration, text, language)
            )
            conn.commit()
    
    def update_user_stats(self, user_id, duration):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET total_requests = total_requests + 1, total_duration = total_duration + ? WHERE user_id = ?',
                (duration, user_id)
            )
            conn.commit()
    
    def update_daily_stats(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET daily_requests = daily_requests + 1 WHERE user_id = ?', (user_id,))
            conn.commit()
    
    def get_user_stats(self, user_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT total_requests, total_duration, daily_requests, streak FROM users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row:
                return {
                    'total_requests': row['total_requests'],
                    'total_duration_minutes': round(row['total_duration'] / 60, 1),
                    'daily_requests': row['daily_requests'],
                    'streak': row['streak']
                }
            return {'total_requests': 0, 'total_duration_minutes': 0, 'daily_requests': 0, 'streak': 0}
    
    def get_admin_stats(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users')
            users = cursor.fetchone()[0]
            cursor.execute('SELECT SUM(total_requests) FROM users')
            req = cursor.fetchone()[0] or 0
            cursor.execute('SELECT SUM(total_duration) FROM users')
            dur = cursor.fetchone()[0] or 0
            cursor.execute('SELECT COUNT(*) FROM feedback')
            feedback = cursor.fetchone()[0]
            return {
                'total_users': users,
                'total_requests': req,
                'total_duration_minutes': round(dur / 60, 1),
                'feedback': feedback
            }
    
    def get_user_transcriptions(self, user_id, limit=5):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, text, duration, language, created_at
                FROM transcriptions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, limit))
            return cursor.fetchall()
    
    def save_feedback(self, user_id, message):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO feedback (user_id, message) VALUES (?, ?)', (user_id, message))
            conn.commit()
    
    def get_all_feedback(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, user_id, message, created_at
                FROM feedback
                ORDER BY created_at DESC
            ''')
            return cursor.fetchall()
    
    def delete_feedback(self, feedback_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM feedback WHERE id = ?', (feedback_id,))
            conn.commit()
            return cursor.rowcount > 0

db = Database(DATABASE_PATH)

class WhisperService:
    def __init__(self):
        self.model = None
    
    def _load(self):
        if self.model is None:
            print("🔄 Загрузка модели Whisper...")
            self.model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8", download_root="models/")
            print("✅ Модель загружена!")
    
    def transcribe(self, audio_path):
        self._load()
        start = time.time()
        segments, info = self.model.transcribe(audio_path, language=None, task="transcribe", beam_size=5, vad_filter=True)
        text = " ".join([seg.text for seg in segments])
        elapsed = time.time() - start
        return text.strip(), info.language, elapsed

whisper = WhisperService()
translator = GoogleTranslator(source='auto', target='ru')

class AudioProcessor:
    async def download(self, file, file_id, bot):
        path = f"{TEMP_FOLDER}/{file_id}.ogg"
        await bot.download_file(file.file_path, path)
        return path
    
    async def convert(self, ogg_path):
        wav_path = ogg_path.replace('.ogg', '.wav')
        audio = AudioSegment.from_file(ogg_path, format="ogg")
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(wav_path, format="wav")
        return wav_path
    
    async def get_duration(self, path):
        try:
            return int(len(AudioSegment.from_file(path)) / 1000)
        except:
            return 0
    
    async def cleanup(self, *paths):
        for p in paths:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except:
                    pass

audio_proc = AudioProcessor()

TIPS = {
    'ru': [
        "🧠 Чтобы лучше запоминать слова, используйте их в предложениях.",
        "🎯 Говорите в тишине и чётко — качество распознавания речи выше.",
        "📅 Ежедневные 5-минутные занятия дают лучший результат.",
        "🌍 Выберите язык и переводите на него все тексты.",
        "🎙️ Если голосовое не распозналось — запишите ещё раз.",
        "🔥 Чем длиннее стрик — тем лучше запоминание! Заходите каждый день.",
        "📝 Длинные расшифровки бот отправляет файлом.",
        "⭐ Если бот помогает — оставьте отзыв.",
        "🌙 Учите язык перед сном — информация лучше усваивается.",
        "📊 Отслеживайте статистику в /stats — рост мотивирует.",
        "🔁 Повторение — ключ к запоминанию."
    ],
    'en': [
        "🧠 Use new words in sentences to remember them better.",
        "🎯 Speak clearly in silence for better recognition.",
        "📅 Daily 5-minute sessions give the best results.",
        "🌍 Choose a language and translate everything into it.",
        "🎙️ If voice is not recognized — record it again.",
        "🔥 The longer the streak, the better the learning! Visit every day.",
        "📝 Long transcriptions are sent as a file.",
        "⭐ Leave feedback if the bot helps you.",
        "🌙 Learn languages before sleep — information is absorbed better.",
        "📊 Track statistics in /stats — growth motivates.",
        "🔁 Repetition is the key to memorization."
    ]
}

class LanguageSelection(StatesGroup):
    waiting_for_language = State()

def get_main_keyboard(lang):
    t = TEXTS.get(lang, TEXTS['ru'])
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t['menu_stats']), KeyboardButton(text=t['menu_history'])],
            [KeyboardButton(text=t['menu_tip']), KeyboardButton(text=t['menu_lang'])],
            [KeyboardButton(text=t['menu_help']), KeyboardButton(text=t['menu_feedback'])]
        ],
        resize_keyboard=True
    )

def get_language_keyboard():
    keyboard = []
    row = []
    for i, (code, name) in enumerate(LANGUAGES.items()):
        row.append(InlineKeyboardButton(text=name, callback_data=f"lang_first_{code}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_text(user_id, key, **kwargs):
    lang = db.get_language(user_id)
    text_dict = TEXTS.get(lang, TEXTS['ru'])
    text = text_dict.get(key, TEXTS['ru'].get(key, key))
    if kwargs:
        text = text.format(**kwargs)
    return text

router = Router()
active_tasks = {}
waiting_for_feedback = {}

@router.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    user = message.from_user
    is_existing = db.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    if not is_existing:
        await state.set_state(LanguageSelection.waiting_for_language)
        await message.reply(
            get_text(user.id, 'start_first', name=user.first_name),
            reply_markup=get_language_keyboard(),
            parse_mode="Markdown"
        )
    else:
        lang = db.get_language(user.id)
        lang_name = LANGUAGES.get(lang, '🇷🇺 Русский')
        await message.reply(
            get_text(user.id, 'start_back', name=user.first_name, lang=lang_name),
            reply_markup=get_main_keyboard(lang)
        )

@router.callback_query(lambda c: c.data.startswith("lang_first_"))
async def set_first_language(callback: types.CallbackQuery, state: FSMContext):
    lang_code = callback.data.replace("lang_first_", "")
    user_id = callback.from_user.id
    db.set_language(user_id, lang_code)
    lang_name = LANGUAGES.get(lang_code, lang_code)
    await state.clear()
    await callback.answer(f"✅ {lang_name}")
    await callback.message.delete()
    await callback.message.answer(
        get_text(user_id, 'lang_changed', lang=lang_name),
        reply_markup=get_main_keyboard(lang_code),
        parse_mode="Markdown"
    )

@router.message(Command("stats"))
async def stats_cmd(message: types.Message):
    s = db.get_user_stats(message.from_user.id)
    await message.reply(
        get_text(message.from_user.id, 'stats', 
                 total=s['total_requests'], 
                 minutes=s['total_duration_minutes'],
                 daily=s['daily_requests'],
                 streak=s['streak']),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(db.get_language(message.from_user.id))
    )

@router.message(Command("history"))
async def history_cmd(message: types.Message):
    history = db.get_user_transcriptions(message.from_user.id, 5)
    if not history:
        await message.reply(get_text(message.from_user.id, 'history_empty'), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))
        return
    text = get_text(message.from_user.id, 'history')
    for i, h in enumerate(history, 1):
        preview = h['text'][:50] + "..." if len(h['text']) > 50 else h['text']
        text += f"{i}. {preview}\n"
    await message.reply(text, parse_mode="Markdown", reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))

@router.message(Command("tip"))
async def tip_cmd(message: types.Message):
    lang = db.get_language(message.from_user.id)
    tips = TIPS.get(lang, TIPS['ru'])
    await message.reply(
        get_text(message.from_user.id, 'tip', tip=random.choice(tips)),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(lang)
    )

@router.message(Command("lang"))
async def lang_cmd(message: types.Message):
    current_lang = db.get_language(message.from_user.id)
    current_name = LANGUAGES.get(current_lang, '🇷🇺 Русский')
    await message.reply(
        get_text(message.from_user.id, 'choose_lang', lang=current_name),
        reply_markup=get_language_keyboard(),
        parse_mode="Markdown"
    )

@router.message(Command("help"))
async def help_cmd(message: types.Message):
    await message.reply(
        get_text(message.from_user.id, 'help'),
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(db.get_language(message.from_user.id))
    )

@router.message(Command("feedback"))
async def feedback_admin_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply(get_text(message.from_user.id, 'access_denied'))
        return
    
    feedbacks = db.get_all_feedback()
    if not feedbacks:
        await message.reply(get_text(message.from_user.id, 'feedback_empty'), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))
        return
    
    text = get_text(message.from_user.id, 'feedback_all')
    for f in feedbacks[:10]:
        created = datetime.fromisoformat(f['created_at']).strftime("%d.%m %H:%M")
        text += f"#{f['id']} [{created}] ID:{f['user_id']}\n{f['message']}\n\n"
    
    if len(text) > 4000:
        txt_path = f"{TEMP_FOLDER}/feedback_all.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write(text)
        await message.reply_document(FSInputFile(txt_path), caption="📩 Все отзывы")
        os.remove(txt_path)
    else:
        await message.reply(text, parse_mode="Markdown", reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))

@router.message(Command("delete_feedback"))
async def delete_feedback_cmd(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.reply(get_text(message.from_user.id, 'access_denied'))
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        await message.reply(get_text(message.from_user.id, 'feedback_delete_usage'), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))
        return
    
    try:
        feedback_id = int(parts[1])
    except ValueError:
        await message.reply(get_text(message.from_user.id, 'feedback_delete_error'), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))
        return
    
    if db.delete_feedback(feedback_id):
        await message.reply(get_text(message.from_user.id, 'feedback_deleted', id=feedback_id), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))
    else:
        await message.reply(get_text(message.from_user.id, 'feedback_not_found', id=feedback_id), reply_markup=get_main_keyboard(db.get_language(message.from_user.id)))

@router.callback_query(lambda c: c.data.startswith("lang_") and not c.data.startswith("lang_first_"))
async def set_language(callback: types.CallbackQuery):
    lang_code = callback.data.replace("lang_", "")
    user_id = callback.from_user.id
    db.set_language(user_id, lang_code)
    lang_name = LANGUAGES.get(lang_code, lang_code)
    await callback.answer(f"✅ {lang_name}")
    await callback.message.edit_text(
        get_text(user_id, 'lang_changed', lang=lang_name),
        parse_mode="Markdown"
    )

@router.message(F.text)
async def handle_text(message: types.Message):
    text = message.text
    uid = message.from_user.id
    lang = db.get_language(uid)
    
    t = TEXTS.get(lang, TEXTS['ru'])
    menu_buttons = [t['menu_stats'], t['menu_history'], t['menu_tip'], t['menu_lang'], t['menu_help'], t['menu_feedback']]
    
    if text.startswith('/'):
        return
    
    if text in menu_buttons:
        if text == t['menu_stats']:
            await stats_cmd(message)
        elif text == t['menu_history']:
            await history_cmd(message)
        elif text == t['menu_tip']:
            await tip_cmd(message)
        elif text == t['menu_lang']:
            await lang_cmd(message)
        elif text == t['menu_help']:
            await help_cmd(message)
        elif text == t['menu_feedback']:
            waiting_for_feedback[uid] = True
            await message.reply(get_text(uid, 'feedback'), reply_markup=get_main_keyboard(lang))
        return
    
    if uid in waiting_for_feedback:
        db.save_feedback(uid, text)
        del waiting_for_feedback[uid]
        await message.reply(get_text(uid, 'feedback_thanks'), reply_markup=get_main_keyboard(lang))
        for admin_id in ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    get_text(uid, 'feedback_admin', user=message.from_user.username or 'user', text=text)
                )
            except:
                pass
        return
    
    if len(text) < 2:
        await message.reply(get_text(uid, 'short'), reply_markup=get_main_keyboard(lang))
        return
    
    try:
        target_lang = db.get_language(uid)
        translator.target = target_lang
        translated = translator.translate(text)
        await message.reply(translated, reply_markup=get_main_keyboard(lang))
    except Exception as e:
        await message.reply(get_text(uid, 'error', error=e), reply_markup=get_main_keyboard(lang))

@router.message(F.voice)
async def handle_voice(message: types.Message, bot: Bot):
    uid = message.from_user.id
    voice = message.voice
    lang = db.get_language(uid)

    if voice.duration > MAX_AUDIO_DURATION:
        await message.reply(get_text(uid, 'max_duration', max=MAX_AUDIO_DURATION), reply_markup=get_main_keyboard(lang))
        return
    
    if uid in active_tasks:
        await message.reply(get_text(uid, 'wait'), reply_markup=get_main_keyboard(lang))
        return

    db.get_or_create_user(uid, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    active_tasks[uid] = True
    status_msg = await message.reply(get_text(uid, 'recognizing'))

    try:
        file = await bot.get_file(voice.file_id)
        ogg_path = await audio_proc.download(file, voice.file_id, bot)
        duration = await audio_proc.get_duration(ogg_path)
        wav_path = await audio_proc.convert(ogg_path)

        await status_msg.edit_text(get_text(uid, 'recognizing_progress', duration=duration))
        text, detected_lang, elapsed = whisper.transcribe(wav_path)

        if not text:
            await status_msg.edit_text(get_text(uid, 'not_recognized'), reply_markup=get_main_keyboard(lang))
            return

        db.save_transcription(uid, voice.file_id, duration, text, detected_lang)
        db.update_user_stats(uid, duration)
        db.update_daily_stats(uid)
        await status_msg.delete()

        try:
            target_lang = db.get_language(uid)
            translator.target = target_lang
            translated = translator.translate(text)
            await message.reply(translated, reply_markup=get_main_keyboard(lang))
        except:
            await message.reply(text, reply_markup=get_main_keyboard(lang))

        await audio_proc.cleanup(ogg_path, wav_path)

    except Exception as e:
        await status_msg.edit_text(get_text(uid, 'error', error=e))
    finally:
        if uid in active_tasks:
            del active_tasks[uid]

async def main():
    logging.basicConfig(level=logging.INFO)
    storage = MemoryStorage()
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN), request_timeout=120)
    dp = Dispatcher(storage=storage)
    dp.include_router(router)
    print("🚀 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())