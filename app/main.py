import os
import time
import secrets
from datetime import datetime, timedelta

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session
)
from werkzeug.utils import secure_filename

from .extensions import SessionLocal
from .models import User, Guide, Comment
from config import Config

main_bp = Blueprint('main', __name__)


def current_user(db):
    """Возвращаем пользователя по session['user_id'] или None."""
    uid = session.get('user_id')
    if not uid:
        return None
    # session.get(Guide, id) — корректнее, чем Query.get (SQLAlchemy 2.x)
    return db.get(User, uid)


def can_edit(user, guide):
    if not user or not guide:
        return False
    return user.id == guide.author_id or (session.get('role') == 'admin')


@main_bp.route('/')
def index():
    db = SessionLocal()
    try:
        q = request.args.get('q', '').strip()
        query = db.query(Guide).order_by(Guide.created_at.desc())
        if q:
            query = query.filter(Guide.title.ilike(f'%{q}%'))
        guides = query.limit(6).all()
        return render_template('index.html', guides=guides, query=q)
    finally:
        db.close()


@main_bp.route('/guides')
def guides_list():
    db = SessionLocal()
    try:
        q = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        query = db.query(Guide)
        if q:
            query = query.filter(Guide.title.ilike(f'%{q}%'))
        if category:
            query = query.filter(Guide.category == category)
        guides = query.order_by(Guide.created_at.desc()).all()
        return render_template('guides.html', guides=guides)
    finally:
        db.close()


@main_bp.route('/guides/<int:gid>')
def guide_detail(gid):
    db = SessionLocal()
    try:
        guide = db.get(Guide, gid)
        if not guide:
            flash('Гайд не найден', 'warning')
            return redirect(url_for('main.guides_list'))
        return render_template('guide_detail.html', guide=guide)
    finally:
        db.close()


@main_bp.route('/guides/new', methods=['GET', 'POST'])
def create_guide():
    db = SessionLocal()
    try:
        if not session.get('user_id'):
            flash('Авторизуйтесь, чтобы публиковать гайды.', 'warning')
            return redirect(url_for('auth.login'))

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()

            valid_categories = getattr(Config, "CATEGORIES", [])
            if category not in valid_categories:
                flash('Выберите категорию из списка.', 'danger')
                return render_template('guide_new.html')

            if not title or not description:
                flash('Заполните обязательные поля', 'danger')
                return render_template('guide_new.html')

            # необязательная обложка
            img_url = None
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(f"{int(time.time())}_{image.filename}")
                upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                path = os.path.join(upload_dir, filename)
                image.save(path)
                img_url = f"/static/uploads/{filename}"

            g = Guide(
                title=title,
                description=description,
                category=category,
                author_id=session['user_id'],
                image_url=img_url
            )
            db.add(g)
            db.commit()
            flash('Гайд опубликован.', 'success')
            return redirect(url_for('main.guide_detail', gid=g.id))

        return render_template('guide_new.html')
    finally:
        db.close()


@main_bp.route('/guides/<int:gid>/edit', methods=['GET', 'POST'])
def edit_guide(gid):
    db = SessionLocal()
    try:
        me = current_user(db)
        if not me:
            flash('Авторизуйтесь, чтобы редактировать.', 'warning')
            return redirect(url_for('auth.login'))

        guide = db.get(Guide, gid)
        if not guide:
            flash('Гайд не найден', 'warning')
            return redirect(url_for('main.guides_list'))

        if not can_edit(me, guide):
            flash('Недостаточно прав для редактирования.', 'danger')
            return redirect(url_for('main.guide_detail', gid=gid))

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            category = request.form.get('category', '').strip()

            valid_categories = getattr(Config, "CATEGORIES", [])
            if category not in valid_categories:
                flash('Выберите категорию из списка.', 'danger')
                return render_template('guide_edit.html', guide=guide)

            if not title or not description:
                flash('Заполните обязательные поля', 'danger')
                return render_template('guide_edit.html', guide=guide)

            # опциональное обновление обложки
            image = request.files.get('image')
            if image and image.filename:
                filename = secure_filename(f"{int(time.time())}_{image.filename}")
                upload_dir = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
                os.makedirs(upload_dir, exist_ok=True)
                path = os.path.join(upload_dir, filename)
                image.save(path)
                guide.image_url = f"/static/uploads/{filename}"

            guide.title = title
            guide.description = description
            guide.category = category
            db.commit()
            flash('Изменения сохранены.', 'success')
            return redirect(url_for('main.guide_detail', gid=gid))

        return render_template('guide_edit.html', guide=guide)
    finally:
        db.close()


@main_bp.route('/guides/<int:gid>/delete', methods=['POST'])
def delete_guide(gid):
    db = SessionLocal()
    try:
        me = current_user(db)
        if not me:
            flash('Авторизуйтесь, чтобы удалять.', 'warning')
            return redirect(url_for('auth.login'))

        guide = db.get(Guide, gid)
        if not guide:
            flash('Гайд не найден', 'warning')
            return redirect(url_for('main.guides_list'))

        if not can_edit(me, guide):
            flash('Недостаточно прав для удаления.', 'danger')
            return redirect(url_for('main.guide_detail', gid=gid))

        db.delete(guide)
        db.commit()
        flash('Гайд удалён.', 'info')
        return redirect(url_for('main.guides_list'))
    finally:
        db.close()


@main_bp.route('/guides/<int:gid>/comment', methods=['POST'])
def add_comment(gid):
    db = SessionLocal()
    try:
        if not session.get('user_id'):
            flash('Нужно войти, чтобы комментировать.', 'warning')
            return redirect(url_for('auth.login'))

        text = request.form.get('text', '').strip()
        guide = db.get(Guide, gid)

        if not guide or not text:
            flash('Ошибка комментария.', 'danger')
            return redirect(url_for('main.guide_detail', gid=gid))

        com = Comment(text=text, author_id=session['user_id'], guide_id=gid)
        db.add(com)
        db.commit()
        flash('Комментарий добавлен.', 'success')
        return redirect(url_for('main.guide_detail', gid=gid))
    finally:
        db.close()


@main_bp.route("/about")
def about():
    return render_template("about.html")


# ---------- Привязка Telegram к сайту ----------

@main_bp.route("/settings/link-telegram", methods=["GET"])
def link_telegram_view():
    db = SessionLocal()
    try:
        me = current_user(db)
        if not me:
            flash("Авторизуйтесь.", "warning")
            return redirect(url_for("auth.login"))

        # показываем код только если он ещё валиден
        valid = bool(me.link_expires_at and me.link_expires_at > datetime.utcnow())
        code = me.link_code if valid else None
        return render_template("link_telegram.html", code=code, expires_at=me.link_expires_at)
    finally:
        db.close()


@main_bp.route("/settings/link-telegram/generate", methods=["POST"])
def link_telegram_generate():
    db = SessionLocal()
    try:
        me = current_user(db)
        if not me:
            flash("Авторизуйтесь.", "warning")
            return redirect(url_for("auth.login"))

        # короткий одноразовый код на 10 минут
        code = secrets.token_hex(4)  # 8 символов hex
        me.link_code = code
        me.link_expires_at = datetime.utcnow() + timedelta(minutes=10)
        db.commit()

        flash("Код сгенерирован. Действует 10 минут.", "success")
        return redirect(url_for("main.link_telegram_view"))
    finally:
        db.close()


@main_bp.route('/profile/<username>')
def profile(username):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            flash('Пользователь не найден', 'warning')
            return redirect(url_for('main.index'))

        guides = (
            db.query(Guide)
              .filter(Guide.author_id == user.id)
              .order_by(Guide.created_at.desc())
              .all()
        )
        return render_template('profile.html', user=user, guides=guides)
    finally:
        db.close()
