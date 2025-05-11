import json
from datetime import datetime
import os

IMAGES_DIR = "images"

def load_articles():
    """Завантаження статей з файлу"""
    try:
        with open('articles.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

# Завантажуємо та сортуємо статті
articles = sorted(load_articles(), key=lambda x: x['date'], reverse=True)

# Генеруємо HTML
html = f"""
<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Новини</title>
    <style>
        :root {{
            --bg-color: #121212;
            --text-color: #e0e0e0;
            --primary-color: #bb86fc;
            --secondary-color: #03dac6;
            --card-bg: #1e1e1e;
            --border-color: #333;
        }}
        
        body {{
            font-family: 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            color: var(--text-color);
            background-color: var(--bg-color);
            margin: 0;
            padding: 0;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }}
        
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 1px solid var(--border-color);
        }}
        
        h1 {{
            color: var(--primary-color);
            margin: 0;
            font-size: 2.5rem;
        }}
        
        .date {{
            color: var(--secondary-color);
            font-size: 0.9rem;
        }}
        
        .articles-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 25px;
        }}
        
        .article-card {{
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
            transition: transform 0.3s ease;
            border: 1px solid var(--border-color);
        }}
        
        .article-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.4);
        }}
        
        .article-image {{
            width: 100%;
            height: 200px;
            object-fit: cover;
            border-bottom: 1px solid var(--border-color);
        }}
        
        .article-content {{
            padding: 25px;
        }}
        
        .article-title {{
            color: var(--primary-color);
            margin-top: 0;
            margin-bottom: 10px;
            font-size: 1.5rem;
        }}
        
        .article-text {{
            color: var(--text-color);
            margin-bottom: 15px;
        }}
        
        .article-meta {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: #888;
        }}
        
        .author {{
            color: var(--secondary-color);
        }}
        
        .no-image {{
            background-color: #2a2a2a;
            display: flex;
            align-items: center;
            justify-content: center;
            height: 200px;
            color: #666;
            font-style: italic;
        }}
        
        @media (max-width: 768px) {{
            .articles-container {{
                grid-template-columns: 1fr;
            }}
            
            header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 10px;
            }}
            
            .article-image {{
                height: 150px;
            }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>GENIUS BAR</h1>
        <div class="date">Last update: {datetime.now().strftime('%d.%m.%Y о %H:%M')}</div>
    </header>
    
    <div class="articles-container">
"""

for article in articles:
    date = datetime.strptime(article['date'], '%Y-%m-%d').strftime('%d.%m.%Y')
    image_tag = f'<img src="{article["image"]}" alt="{article["title"]}" class="article-image">' if "image" in article else '<div class="no-image">Немає зображення</div>'
    
    html += f"""
        <div class="article-card">
            {image_tag}
            <div class="article-content">
                <h2 class="article-title">{article['title']}</h2>
                <div class="article-text">{article['content']}</div>
                <div class="article-meta">
                    <span class="author">{article.get('author', 'Невідомий автор')}</span>
                    <span class="date">{date}</span>
                </div>
            </div>
        </div>
    """

html += """
    </div>
</body>
</html>
"""

# Записуємо HTML у файл
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Перегенеровано успішно!")