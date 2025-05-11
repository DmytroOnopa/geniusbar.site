import json
import subprocess
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import FSInputFile, InputMediaPhoto
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv
import shutil

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Завантажуємо токен з .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ARTICLES_FILE = "articles.json"
IMAGES_DIR = "images"
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

# Створюємо папку для зображень
os.makedirs(IMAGES_DIR, exist_ok=True)

# Ініціалізація бота
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Словник для зберігання станів користувачів
user_states = {}

def load_articles():
    """Завантаження статей з файлу з обробкою помилок"""
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_articles(articles):
    """Збереження статей у файл"""
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

async def update_website():
    """Оновлення сайту та публікація на GitHub Pages"""
    try:
        # Генерація сайту
        subprocess.run(["python3", "generate_site.py"], check=True)
        
        # Оновлення Git репозиторію
        subprocess.run(["git", "add", "index.html", "articles.json", IMAGES_DIR], check=True)
        subprocess.run(["git", "commit", "-m", "Оновлення статей"], check=True)
        subprocess.run(["git", "push"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Помилка при оновленні сайту: {e}")
        return False

def save_image(file_id: str, user_id: int) -> str:
    """Зберігає зображення і повертає шлях до нього"""
    image_path = os.path.join(IMAGES_DIR, f"{user_id}_{file_id}.jpg")
    return image_path

@dp.message(CommandStart())
async def start(message: types.Message):
    """Обробка команди /start"""
    await message.answer(
        "👋 Вітаю в новинному боті!\n\n"
        "Доступні команди:\n"
        "/add - додати нову статтю (фото + текст)\n"
        "/list - перегляд усіх статей\n"
        "/edit - редагувати статтю\n"
        "/cancel - скасувати поточну дію"
    )

@dp.message(Command("cancel"))
async def cancel(message: types.Message):
    """Скасування поточної дії"""
    user_id = message.from_user.id
    if user_id in user_states:
        user_states.pop(user_id)
        await message.answer("Дію скасовано.")
    else:
        await message.answer("Немає активних дій для скасування.")

@dp.message(Command("add"))
async def add_article_start(message: types.Message):
    """Початок додавання статті"""
    user_states[message.from_user.id] = {"step": "waiting_photo"}
    await message.answer("Будь ласка, надішліть фото для статті:")

@dp.message(Command("list"))
async def list_articles(message: types.Message):
    """Виведення списку статей"""
    articles = load_articles()

    if not articles:
        await message.answer("Статей поки немає.")
        return

    response = "📰 Список статей:\n\n"
    for idx, article in enumerate(sorted(articles, key=lambda x: x.get("date", ""), reverse=True), 1):
        date = datetime.strptime(article['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
        response += f"{idx}. {date} - {article['title']}\n"

    await message.answer(response)

@dp.message(Command("edit"))
async def edit_article_start(message: types.Message, command: CommandObject):
    """Початок редагування статті"""
    articles = load_articles()
    
    if not command.args:
        await message.answer("Введіть номер статті для редагування, наприклад: /edit 1")
        return
    
    try:
        article_num = int(command.args)
        if article_num < 1 or article_num > len(articles):
            raise ValueError
    except ValueError:
        await message.answer("Невірний номер статті.")
        return
    
    article = sorted(articles, key=lambda x: x.get("date", ""), reverse=True)[article_num - 1]
    user_states[message.from_user.id] = {
        "step": "editing",
        "article_id": article['id'],
        "original_title": article['title']
    }
    
    await message.answer(
        f"Редагуємо статтю: {article['title']}\n\n"
        "Надішліть нове фото (або 'пропустити' щоб залишити поточне),\n"
        "потім нову назву та новий текст."
    )

@dp.message()
async def handle_messages(message: types.Message):
    """Обробка всіх повідомлень"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        await message.answer("Використайте одну з команд: /start, /add, /list, /edit")
        return
    
    if state["step"] == "waiting_photo":
        if message.photo:
            # Зберігаємо фото
            file_id = message.photo[-1].file_id
            image_path = save_image(file_id, user_id)
            
            # Завантажуємо фото
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, image_path)
            
            state["image_path"] = image_path
            state["step"] = "waiting_title"
            await message.answer("Фото збережено! Тепер введіть заголовок статті:")
        else:
            await message.answer("Будь ласка, надішліть фото для статті.")
    
    elif state["step"] == "waiting_title":
        if len(message.text) > 100:
            await message.answer("Заголовок занадто довгий. Максимум 100 символів.")
            return
        
        state["title"] = message.text
        state["step"] = "waiting_content"
        await message.answer("Чудовий заголовок! Тепер введіть текст статті:")
    
    elif state["step"] == "waiting_content":
        if len(message.text) > 4000:
            await message.answer("Текст статті занадто довгий. Максимум 4000 символів.")
            return
        
        state["content"] = message.text
        
        # Створюємо нову статтю
        new_article = {
            "id": str(datetime.now().timestamp()),
            "title": state["title"],
            "content": state["content"],
            "image": state["image_path"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "author": message.from_user.full_name
        }
        
        # Додаємо статтю
        articles = load_articles()
        articles.append(new_article)
        save_articles(articles)
        
        # Оновлюємо сайт
        success = await update_website()
        
        if success:
            await message.answer_photo(
                photo=FSInputFile(state["image_path"]),
                caption=f"✅ Статтю додано!\n\n<b>{state['title']}</b>\n\n{state['content']}"
            )
        else:
            await message.answer("Статтю додано, але виникли проблеми з оновленням сайту.")
        
        user_states.pop(user_id)
    
    elif state["step"] == "editing":
        if "edit_step" not in state:
            # Перший крок редагування - фото
            if message.text and message.text.lower() == "пропустити":
                state["edit_step"] = "title"
                await message.answer("Залишаємо поточне фото. Тепер введіть нову назву:")
            elif message.photo:
                file_id = message.photo[-1].file_id
                image_path = save_image(file_id, user_id)
                
                file = await bot.get_file(file_id)
                await bot.download_file(file.file_path, image_path)
                
                state["new_image"] = image_path
                state["edit_step"] = "title"
                await message.answer("Нове фото збережено! Тепер введіть нову назву:")
            else:
                await message.answer("Надішліть нове фото або напишіть 'пропустити'")
        
        elif state["edit_step"] == "title":
            if len(message.text) > 100:
                await message.answer("Заголовок занадто довгий. Максимум 100 символів.")
                return
            
            state["new_title"] = message.text
            state["edit_step"] = "content"
            await message.answer("Гарна назва! Тепер введіть новий текст:")
        
        elif state["edit_step"] == "content":
            if len(message.text) > 4000:
                await message.answer("Текст статті занадто довгий. Максимум 4000 символів.")
                return
            
            state["new_content"] = message.text
            
            # Оновлюємо статтю
            articles = load_articles()
            for article in articles:
                if article["id"] == state["article_id"]:
                    if "new_image" in state:
                        article["image"] = state["new_image"]
                    if "new_title" in state:
                        article["title"] = state["new_title"]
                    if "new_content" in state:
                        article["content"] = state["new_content"]
                    article["date"] = datetime.now().strftime("%Y-%m-%d")
                    break
            
            save_articles(articles)
            
            # Оновлюємо сайт
            success = await update_website()
            
            if success:
                await message.answer(
                    f"✅ Статтю '{state.get('new_title', state['original_title'])} успішно оновлено!"
                )
            else:
                await message.answer("Статтю оновлено, але виникли проблеми з оновленням сайту.")
            
            user_states.pop(user_id)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())