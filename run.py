# run.py
from flask import Flask
from config import Config
from app.extensions import init_db, SessionLocal
from app.main import main_bp
from app.auth import auth_bp, init_oauth
from app.admin import admin_bp
from app.api import api_bp

def create_app():
    app = Flask(__name__, static_folder='app/static', template_folder='app/templates')
    app.config.from_object(Config)

    # Блюпринты
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp)

    # OAuth (Google)
    init_oauth(app)

    # Критично: по окончанию любого запроса освобождаем сессию → коннект возвращается в пул
    @app.teardown_appcontext
    def cleanup_session(exc=None):
        SessionLocal.remove()

    return app

app = create_app()

# Глобальные переменные для шаблонов
@app.context_processor
def inject_globals():
    from config import Config
    return {"CATEGORIES": getattr(Config, "CATEGORIES", ["Видеокарты", "Ноутбуки", "Прочее"])}

# CLI-команда для инициализации БД
@app.cli.command('db_create')
def db_create():
    init_db()
    print('DB created.')

if __name__ == '__main__':
    app.run()
