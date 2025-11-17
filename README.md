
# Сайт по обслуживанию видеокарт и комплектующих

Проект полностью реализует ТЗ: главная, раздел «Гайды», добавление гайда с фото, система пользователей (регистрация/логин, Google OAuth 2.0), роли (user/admin), профиль, комментарии, панель администратора, JWT для API, PostgreSQL + SQLAlchemy, адаптивная вёрстка в тёмном техно‑стиле.

## Стек
- Backend: Python 3.11, Flask
- БД: PostgreSQL
- ORM: SQLAlchemy
- Аутентификация: пароли (bcrypt), Google OAuth 2.0 (authlib), JWT (PyJWT)
- Frontend: Jinja2 + Bootstrap 5 (тёмная тема), небольшие JS‑скрипты
- Загрузка файлов: изображения гайдов хранятся в `static/uploads/`

## Быстрый старт (локально)
1) Создайте и активируйте окружение:
```bash
python -m venv .venv
source ./.venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
2) Установите переменные окружения (см. `.env.example`) и создайте файл `.env`.
3) Инициализируйте БД:
```bash
flask db_create
```
4) Запуск:
```bash
flask run
```
Откройте http://127.0.0.1:5000

## Переменные окружения
Скопируйте `.env.example` → `.env` и заполните:
```
FLASK_SECRET=замените_на_секрет
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/gpu_service
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
OAUTH_REDIRECT_URI=http://127.0.0.1:5000/auth/google/callback
JWT_SECRET=замените_на_секрет
```
> Для теста можно использовать бесплатную PostgreSQL локально (Docker) или в облаке.

## Роли и вход в админку
- Обычный пользователь получает роль `user`.
- Администратор создаётся вручную: выполните в интерактивной консоли Flask (или через SQL) присвоение `role='admin'` нужному пользователю.
- Админ‑панель: `/admin`.

## Структура БД
- `users (id, username, email, password_hash, role, google_id, created_at)`
- `guides (id, title, description, image_url, author_id, category, created_at)`
- `comments (id, text, author_id, guide_id, created_at)`

## Маршруты
- Главная: `/` (последние гайды, поиск)
- Гайды: `/guides` (список) → `/guides/<id>` (страница гайда)
- Добавить гайд: `/guides/new` (только авторизованным)
- Комментарии: POST `/guides/<id>/comment` (только авторизованным)
- Регистрация/Вход: `/register`, `/login`, `/logout`
- Google OAuth: `/auth/google`, `/auth/google/callback`
- Профиль: `/profile/<username>`
- Админка: `/admin` (управление пользователями/гайдами)
- JWT API (примеры): `/api/guides`, `/api/guides/<id>`

## Мини‑дизайн‑система
- Тёмная палитра, неоновые акценты (#00e7ff, #9d4edd).
- Карточки гайдов, аккуратная типографика, responsive.

## Развёртывание на VPS (кратко)
- Установите Python 3.11, PostgreSQL 15+
- Настройте `.env`, выполните `pip install -r requirements.txt`, `flask db_create`
- Запустите через gunicorn + nginx (пример в `deploy/gunicorn_start.sh`)

## Лицензия
MIT
