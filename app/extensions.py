# app/extensions.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config import Config
from .models import Base  # модели должны наследовать Base из app.models

# Надёжный пул соединений + авто-проверка «живости»
engine = create_engine(
    Config.SQLALCHEMY_DATABASE_URI,
    future=True,
    pool_pre_ping=True,   # чинит «уснувшие» коннекты
    pool_size=10,         # базовый размер пула
    max_overflow=20,      # пиковые коннекты сверх пула
    pool_timeout=30,      # сколько ждать свободный коннект
    pool_recycle=1800,    # переподключать каждые 30 минут
)

# Потокобезопасная сессия, привязанная к контексту запроса
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
)

def init_db():
    """Создание всех таблиц по моделям."""
    Base.metadata.create_all(bind=engine)
