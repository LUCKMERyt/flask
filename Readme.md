# Личный сайт на Flask

Главная, «Обо мне», каталог (поиск, фильтры, сортировка, пагинация, живые подсказки),
отзывы с рейтингом, регистрация/вход, админ-панель, светлая и тёмная темы.

## Запуск
```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # и заполните значения
flask db upgrade            # создаст таблицу reviews
python app.py
```
Откройте http://127.0.0.1:5000

## Админка
Адрес `/admin`. Чтобы закрыть её от посторонних, задайте `ADMIN_USERNAMES=ваш_логин`
в `.env`, зарегистрируйтесь с этим логином и войдите.

## Структура
- `app.py` — маршруты; `admin.py` — админка; `models.py` — модели; `utils.py` — CSRF, права, форматирование
- `templates/` — шаблоны (`_icons.html`, `_macros.html` — общие компоненты)
- `static/custom.css` — дизайн-система, `static/app.js` — интерактив
