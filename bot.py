import json
import subprocess
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from datetime import datetime
import os
from dotenv import load_dotenv

# Налаштування
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ARTICLES_FILE = "articles.json"
IMAGES_DIR = "images"
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "").split(",") if id]

os.makedirs(IMAGES_DIR, exist_ok=True)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_states = {}

# Функції для роботи з даними
def load_articles():
    """Завантажує статті з перевіркою ID"""
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)
            # Переконуємося, що всі ID - прості числа
            if articles and not isinstance(articles[0]['id'], int):
                return regenerate_ids(articles)
            return articles
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def regenerate_ids(articles):
    """Перетворює ID у простий числовий формат"""
    for i, article in enumerate(articles, 1):
        article['id'] = i
    save_articles(articles)
    return articles

def save_articles(articles):
    """Зберігає статті у файл"""
    with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)

def get_next_id():
    """Генерує наступний ID"""
    return len(load_articles()) + 1

async def update_website():
    """Оновлює сайт та GitHub Pages"""
    try:
        subprocess.run(["python3", "generate_site.py"], check=True)
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", "Оновлення статей"], check=True)
        subprocess.run(["git", "push"], check=True)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Помилка оновлення сайту: {e}")
        return False

def save_image(file_id: str, user_id: int) -> str:
    """Зберігає зображення статті"""
    image_path = os.path.join(IMAGES_DIR, f"{user_id}_{file_id}.jpg")
    return image_path

def create_main_keyboard():
    """Створює основну клавіатуру"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/add"), KeyboardButton(text="/list")],
            [KeyboardButton(text="/edit"), KeyboardButton(text="/delete")],
            [KeyboardButton(text="/cancel")]
        ],
        resize_keyboard=True
    )

# Обробники команд
@dp.message(CommandStart())
async def start(message: types.Message):
    """Обробка /start"""
    await message.answer(
        "📰 Вітаю в новинному боті!\n\n"
        "Доступні команди:\n"
        "/add - додати статтю\n"
        "/list - перегляд статей\n"
        "/edit - редагування\n"
        "/delete - видалення",
        reply_markup=create_main_keyboard()
    )

@dp.message(Command("cancel"))
async def cancel(message: types.Message):
    """Скасування поточної дії"""
    user_id = message.from_user.id
    if user_id in user_states:
        user_states.pop(user_id)
        await message.answer("Дію скасовано.", reply_markup=create_main_keyboard())
    else:
        await message.answer("Немає активних дій для скасування.")

@dp.message(Command("add"))
async def add_article_start(message: types.Message):
    """Початок додавання статті"""
    user_states[message.from_user.id] = {
        "step": "waiting_photo",
        "new_id": get_next_id()
    }
    await message.answer("Надішліть фото для статті:")

@dp.message(Command("list"))
async def list_articles(message: types.Message):
    """Показує список статей з кнопками"""
    articles = load_articles()
    
    if not articles:
        await message.answer("Статей поки немає.", reply_markup=create_main_keyboard())
        return
    
    builder = InlineKeyboardBuilder()
    for article in articles:
        builder.button(
            text=f"{article['id']}. {article['title'][:20]}",
            callback_data=f"view_{article['id']}"
        )
    builder.adjust(2)
    
    await message.answer(
        "📋 Список статей:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("view_"))
async def view_article(callback: types.CallbackQuery):
    """Перегляд конкретної статті"""
    article_id = int(callback.data.split("_")[1])
    articles = load_articles()
    article = next((a for a in articles if a['id'] == article_id), None)
    
    if not article:
        await callback.answer("Стаття не знайдена")
        return
    
    date = datetime.strptime(article['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
    text = f"📖 <b>{article['title']}</b>\n📅 {date}\n\n{article['content']}"
    
    if 'image' in article and os.path.exists(article['image']):
        await callback.message.answer_photo(
            FSInputFile(article['image']),
            caption=text
        )
    else:
        await callback.message.answer(text)
    
    await callback.answer()

@dp.message(Command("edit"))
async def edit_articles_list(message: types.Message):
    """Список статей для редагування"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Тільки для адміністраторів")
        return
    
    articles = load_articles()
    
    if not articles:
        await message.answer("Немає статей для редагування")
        return
    
    builder = InlineKeyboardBuilder()
    for article in articles:
        builder.button(
            text=f"✏️ {article['id']}. {article['title'][:15]}",
            callback_data=f"edit_{article['id']}"
        )
    builder.adjust(1)
    
    await message.answer(
        "Оберіть статтю для редагування:",
        reply_markup=builder.as_markup()
    )

@dp.callback_query(lambda c: c.data.startswith("edit_"))
async def edit_article_start(callback: types.CallbackQuery):
    """Початок редагування статті"""
    article_id = int(callback.data.split("_")[1])
    articles = load_articles()
    article = next((a for a in articles if a['id'] == article_id), None)
    
    if not article:
        await callback.answer("Стаття не знайдена")
        return
    
    user_states[callback.from_user.id] = {
        "step": "editing",
        "article_id": article_id,
        "original_title": article['title'],
        "original_image": article.get('image', '')
    }
    
    await callback.message.answer(
        f"Редагуємо: <b>{article['title']}</b>\n\n"
        "Надішліть:\n1. Нове фото ('пропустити' щоб залишити поточне)\n"
        "2. Новий заголовок\n3. Новий текст"
    )
    await callback.answer()

@dp.message(Command("delete"))
async def delete_article(message: types.Message, command: CommandObject):
    """Видалення статті за ID"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Тільки для адміністраторів")
        return
    
    if not command.args:
        await message.answer("Введіть номер статті, наприклад: /delete 3")
        return
    
    try:
        article_id = int(command.args)
        articles = load_articles()
        article = next((a for a in articles if a['id'] == article_id), None)
        
        if not article:
            await message.answer("Стаття з таким ID не знайдена")
            return
        
        # Видаляємо статтю
        articles = [a for a in articles if a['id'] != article_id]
        save_articles(articles)
        
        # Видаляємо зображення
        if 'image' in article and os.path.exists(article['image']):
            os.remove(article['image'])
        
        if await update_website():
            await message.answer(f"✅ Статтю '{article['title']}' видалено!")
        else:
            await message.answer("Статтю видалено, але помилка оновлення сайту")
            
    except ValueError:
        await message.answer("Невірний номер статті")

# Обробник повідомлень
@dp.message()
async def handle_messages(message: types.Message):
    """Обробка всіх повідомлень"""
    user_id = message.from_user.id
    state = user_states.get(user_id)
    
    if not state:
        await message.answer("Використайте одну з команд", reply_markup=create_main_keyboard())
        return
    
    if state["step"] == "waiting_photo":
        if message.photo:
            file_id = message.photo[-1].file_id
            image_path = save_image(file_id, user_id)
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, image_path)
            
            state["image_path"] = image_path
            state["step"] = "waiting_title"
            await message.answer("Фото збережено! Введіть заголовок:")
        else:
            await message.answer("Будь ласка, надішліть фото")
    
    elif state["step"] == "waiting_title":
        if len(message.text) > 100:
            await message.answer("Заголовок занадто довгий (макс. 100 символів)")
            return
        
        state["title"] = message.text
        state["step"] = "waiting_content"
        await message.answer("Тепер введіть текст статті:")
    
    elif state["step"] == "waiting_content":
        if len(message.text) > 4000:
            await message.answer("Текст занадто довгий (макс. 4000 символів)")
            return
        
        # Створюємо нову статтю
        new_article = {
            "id": state["new_id"],
            "title": state["title"],
            "content": message.text,
            "image": state["image_path"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "author": message.from_user.full_name
        }
        
        # Додаємо до списку
        articles = load_articles()
        articles.append(new_article)
        save_articles(articles)
        
        # Оновлюємо сайт
        if await update_website():
            await message.answer(
                f"✅ Статтю додано! ID: {new_article['id']}",
                reply_markup=create_main_keyboard()
            )
        else:
            await message.answer("Статтю додано, але помилка оновлення сайту")
        
        user_states.pop(user_id)
    
    elif state["step"] == "editing":
        if "edit_step" not in state:
            # Перший крок - фото
            if message.text and message.text.lower() == "пропустити":
                state["edit_step"] = "title"
                await message.answer("Фото залишено. Введіть новий заголовок:")
            elif message.photo:
                file_id = message.photo[-1].file_id
                image_path = save_image(file_id, user_id)
                file = await bot.get_file(file_id)
                await bot.download_file(file.file_path, image_path)
                
                # Видаляємо старе фото
                if state["original_image"] and os.path.exists(state["original_image"]):
                    os.remove(state["original_image"])
                
                state["new_image"] = image_path
                state["edit_step"] = "title"
                await message.answer("Нове фото збережено! Введіть заголовок:")
            else:
                await message.answer("Надішліть фото або 'пропустити'")
        
        elif state["edit_step"] == "title":
            if len(message.text) > 100:
                await message.answer("Заголовок занадто довгий (макс. 100 символів)")
                return
            
            state["new_title"] = message.text
            state["edit_step"] = "content"
            await message.answer("Тепер введіть новий текст:")
        
        elif state["edit_step"] == "content":
            if len(message.text) > 4000:
                await message.answer("Текст занадто довгий (макс. 4000 символів)")
                return
            
            # Оновлюємо статтю
            articles = load_articles()
            for article in articles:
                if article["id"] == state["article_id"]:
                    if "new_image" in state:
                        article["image"] = state["new_image"]
                    if "new_title" in state:
                        article["title"] = state["new_title"]
                    article["content"] = message.text
                    article["date"] = datetime.now().strftime("%Y-%m-%d")
                    break
            
            save_articles(articles)
            
            if await update_website():
                await message.answer(
                    f"✅ Статтю оновлено!",
                    reply_markup=create_main_keyboard()
                )
            else:
                await message.answer("Статтю оновлено, але помилка оновлення сайту")
            
            user_states.pop(user_id)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())