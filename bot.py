import json
import subprocess
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.utils import executor
import asyncio
from datetime import datetime
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ARTICLES_FILE = "articles.json"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_states = {}

@dp.message(CommandStart())
async def start(message: types.Message):
    user_states[message.from_user.id] = {"step": "title"}
    await message.answer("Привіт! Надішли заголовок для нової статті або /list для перегляду існуючих.")

@dp.message(Command("list"))
async def list_articles(message: types.Message):
    try:
        with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
            articles = json.load(f)
    except FileNotFoundError:
        articles = []

    if not articles:
        await message.answer("Статей поки немає.")
        return

    response = "📰 Поточні статті:\n\n"
    for article in sorted(articles, key=lambda x: x.get("date", ""), reverse=True):
        response += f"{article['date']} — {article['title']}\n"

    await message.answer(response)

@dp.message()
async def collect_article(message: types.Message):
    user_id = message.from_user.id
    state = user_states.get(user_id)

    if not state:
        await message.answer("Надішли /start для початку додавання статті.")
        return

    if state["step"] == "title":
        state["title"] = message.text
        state["step"] = "content"
        await message.answer("Добре! Тепер надішли текст статті:")

    elif state["step"] == "content":
        state["content"] = message.text
        state["step"] = "done"

        new_article = {
            "title": state["title"],
            "content": state["content"],
            "date": datetime.now().strftime("%Y-%m-%d")
        }

        try:
            with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
                articles = json.load(f)
        except FileNotFoundError:
            articles = []

        articles.append(new_article)

        with open(ARTICLES_FILE, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)

        # Запуск генерації сайту
        subprocess.run(["python3", "generate_site.py"], check=True)

        # Git commit + push
        subprocess.run(["git", "add", "index.html", "articles.json"], check=True)
        subprocess.run(["git", "commit", "-m", f"Додано статтю: {state['title']}"], check=True)
        subprocess.run(["git", "push"], check=True)

        await message.answer("✅ Статтю додано, сайт оновлено та запушено до GitHub Pages!")
        user_states.pop(user_id)

if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
