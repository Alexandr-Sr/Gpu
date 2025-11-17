import os
import asyncio
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

from sqlalchemy import and_

from config import Config
from .extensions import SessionLocal
from .models import User, Guide

# ---------- загрузка .env ----------
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не найден TELEGRAM_BOT_TOKEN в .env")

# ---------- вспомогательные ----------
def _categories():
    cats = getattr(Config, "CATEGORIES", None)
    if isinstance(cats, (list, tuple)) and cats:
        return list(cats)
    return ["Видеокарты", "Ноутбуки", "Прочее"]

def _get_linked_user(db, update: Update):
    tg_id = update.effective_user.id
    return db.query(User).filter(User.telegram_id == tg_id).first()

async def _save_guide(update: Update, *, title: str, category: str, description: str) -> str:
    db = SessionLocal()
    try:
        user = _get_linked_user(db, update)
        if not user:
            return "Нет привязки Telegram → сайт. Сначала привяжи через /link <код> (код берётся на сайте в «Привязать Telegram»)."

        guide = Guide(
            title=title.strip(),
            description=description.strip(),
            category=category.strip(),
            author_id=user.id,
            created_at=datetime.utcnow()
        )
        db.add(guide)
        db.commit()
        return f"Гайд сохранён ✅\nАвтор: {user.username}\nНазвание: {title}\nКатегория: {category}"
    except Exception as e:
        db.rollback()
        return f"Не удалось сохранить гайд: {e}"
    finally:
        db.close()

# ---------- команды ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cats = ", ".join(_categories())
    await update.message.reply_text(
        "Привет! Я бот GPU Care.\n\n"
        "Команды:\n"
        "• /link <код> — привязать Telegram к аккаунту сайта (код сгенерируй в разделе «Привязать Telegram»).\n"
        "• /newguide — добавить гайд пошагово.\n"
        "• /pasteguide — вставить гайд одним сообщением по шаблону.\n"
        "• /cancel — отменить текущую операцию.\n\n"
        f"Доступные категории: {cats}"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

async def link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        if not context.args:
            await update.message.reply_text("Использование: /link <код>. Сгенерируй код на сайте в «Привязать Telegram».")
            return

        code = context.args[0].strip()
        user = db.query(User).filter(
            and_(User.link_code == code, User.link_expires_at > datetime.utcnow())
        ).first()

        if not user:
            await update.message.reply_text("Код не найден или истёк. Сгенерируй новый код на сайте.")
            return

        tg_id = update.effective_user.id
        exists = db.query(User).filter(User.telegram_id == tg_id).first()
        if exists and exists.id != user.id:
            await update.message.reply_text("Этот Telegram уже привязан к другому аккаунту на сайте.")
            return

        user.telegram_id = tg_id
        user.link_code = None
        user.link_expires_at = None
        db.commit()

        await update.message.reply_text(f"Готово! Telegram привязан к профилю {user.username}. Можешь пользоваться /newguide или /pasteguide.")
    except Exception as e:
        db.rollback()
        await update.message.reply_text(f"Ошибка привязки: {e}")
    finally:
        db.close()

# ---------- Пошаговое создание гайда ----------
TITLE, CATEGORY, DESCRIPTION = range(3)

async def newguide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        user = _get_linked_user(db, update)
        if not user:
            await update.message.reply_text(
                "Эта команда доступна только после привязки.\n"
                "На сайте в меню «Привязать Telegram» сгенерируй код и отправь /link <код> здесь."
            )
            return ConversationHandler.END
    finally:
        db.close()

    await update.message.reply_text("Введи *название* гайда:", parse_mode="Markdown")
    return TITLE

async def newguide_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = (update.message.text or "").strip()
    if not title:
        await update.message.reply_text("Название не может быть пустым. Введи название ещё раз.")
        return TITLE
    context.user_data["title"] = title
    cats = _categories()
    kb = ReplyKeyboardMarkup([[c] for c in cats], resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Выбери категорию:", reply_markup=kb)
    return CATEGORY

async def newguide_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = (update.message.text or "").strip()
    if category not in _categories():
        await update.message.reply_text("Категория не из списка. Выбери кнопку или напиши ровно одно из значений.")
        return CATEGORY
    context.user_data["category"] = category
    await update.message.reply_text("Вставь *описание* гайда (можно несколько абзацев):", reply_markup=ReplyKeyboardRemove(), parse_mode="Markdown")
    return DESCRIPTION

async def newguide_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    description = (update.message.text or "").strip()
    if not description:
        await update.message.reply_text("Описание не может быть пустым. Напиши описание.")
        return DESCRIPTION

    title = context.user_data.get("title")
    category = context.user_data.get("category")

    msg = await _save_guide(update, title=title, category=category, description=description)
    await update.message.reply_text(msg)
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Операция отменена.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END

# ---------- Шаблон: вставка одним сообщением ----------
TEMPLATE = (
    "Шаблон для /pasteguide:\n\n"
    "Название: <текст>\n"
    "Категория: Видеокарты|Ноутбуки|Прочее\n"
    "Описание:\n"
    "<многострочный текст>"
)

def _parse_paste(text: str):
    """
    Разбирает текст вида:
    Название: ...
    Категория: ...
    Описание:
    ...
    Возвращает (title, category, description) или (None, None, None), если не получилось.
    """
    # Нормализуем переводы строк
    lines = [l.rstrip() for l in text.splitlines()]
    title = None
    category = None
    desc_lines = []
    mode_desc = False

    for line in lines:
        if line.lower().startswith("название:"):
            title = line.split(":", 1)[1].strip()
            continue
        if line.lower().startswith("категория:"):
            category = line.split(":", 1)[1].strip()
            continue
        if line.lower().startswith("описание:"):
            mode_desc = True
            continue
        if mode_desc:
            desc_lines.append(line)

    description = "\n".join(desc_lines).strip() if desc_lines else None
    if not (title and category and description):
        return None, None, None
    return title, category, description

async def pasteguide(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        user = _get_linked_user(db, update)
        if not user:
            await update.message.reply_text(
                "Команда доступна только после привязки.\n"
                "На сайте сгенерируй код в «Привязать Telegram» и отправь /link <код>."
            )
            return
    finally:
        db.close()

    await update.message.reply_text(
        "Вставь гайд одним сообщением по шаблону ниже.\n\n" + TEMPLATE
    )

    return  # дальше ждём обычное сообщение от пользователя

async def pasteguide_catcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Ловит произвольные сообщения после /pasteguide и пробует распарсить шаблон.
    """
    # Проверим, не в другой ли сейчас разговорной ветке пользователь
    # Если в ConversationHandler — то туда управление уже передано.
    text = (update.message.text or "").strip()
    if not text:
        return

    # хак: если пользователь не вызывал /pasteguide — просто молчим
    # можно хранить флаг в context.user_data, но упростим: пробуем парс, если не похоже — выходим
    if "название:" not in text.lower() or "категория:" not in text.lower() or "описание:" not in text.lower():
        return

    title, category, description = _parse_paste(text)
    if not title:
        await update.message.reply_text("Не удалось разобрать шаблон. Проверь формат.\n\n" + TEMPLATE)
        return

    if category not in _categories():
        await update.message.reply_text(
            f"Категория '{category}' не поддерживается. Допустимые: {', '.join(_categories())}\n\n" + TEMPLATE
        )
        return

    msg = await _save_guide(update, title=title, category=category, description=description)
    await update.message.reply_text(msg)


def build_application():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Базовые команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("link", link))

    # Пошаговый мастер создания гайда
    conv = ConversationHandler(
        entry_points=[CommandHandler("newguide", newguide)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, newguide_title)],
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, newguide_category)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, newguide_description)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(conv)

    # Вставка одним сообщением
    app.add_handler(CommandHandler("pasteguide", pasteguide))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, pasteguide_catcher))

    return app


if __name__ == "__main__":
    application = build_application()
    print("Telegram bot is running (polling)...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)
