import json
from datetime import datetime
from pathlib import Path

SITE_TITLE = "GeniusBar"
OUTPUT_FILE = "index.html"
ARTICLES_FILE = "articles.json"

HTML_HEAD = f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{SITE_TITLE}</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
    <style>
        body {{ font-family: 'Inter', sans-serif; margin: 0; padding: 0; background: #f9f9f9; }}
        header {{ background: #222; color: #fff; padding: 1rem; display: flex; justify-content: space-between; align-items: center; }}
        .logo {{ font-size: 1.5rem; font-weight: bold; }}
        .tg-button {{ background: #0088cc; color: white; padding: 0.5rem 1rem; border-radius: 5px; text-decoration: none; }}
        .container {{ padding: 2rem; max-width: 1000px; margin: auto; }}
        .articles {{ display: grid; gap: 1rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
        article {{ background: white; padding: 1rem; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
        footer {{ padding: 2rem; background: #eee; text-align: center; }}
    </style>
</head>
<body>
<header>
    <div class="logo">{SITE_TITLE}</div>
    <a class="tg-button" href="https://t.me/YOUR_BOT_USERNAME">Telegram</a>
</header>
<div class="container">
    <section class="articles">
"""

HTML_FOOT = """
    </section>
</div>
<footer>
    <p>Адреса: Траса Київ-Луганськ-Ізварено 295, Знам'янка</p>
    <p>Телефон: 066 720 48 55</p>
    <p><a href='https://maps.app.goo.gl/AvtdZg32ub6cXANY8' target='_blank'>Google Maps</a></p>
</footer>
</body>
</html>
"""


def generate_site():
    with open(ARTICLES_FILE, "r", encoding="utf-8") as f:
        articles = json.load(f)

    html_content = HTML_HEAD

    for article in sorted(articles, key=lambda x: x.get("date", ""), reverse=True):
        title = article.get("title", "Без назви")
        content = article.get("content", "")
        date = article.get("date", "")
        html_content += f"""
        <article>
            <h3>{title}</h3>
            <small>{date}</small>
            <p>{content}</p>
        </article>
        """

    html_content += HTML_FOOT

    Path(OUTPUT_FILE).write_text(html_content, encoding="utf-8")
    print(f"✅ Сайт згенеровано у {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_site()
