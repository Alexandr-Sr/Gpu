
import bcrypt, jwt, secrets
from datetime import datetime, timedelta
from flask import Blueprint, redirect, request, session, url_for, flash, render_template
from authlib.integrations.flask_client import OAuth
from config import Config
from .extensions import SessionLocal
from .models import User

auth_bp = Blueprint('auth', __name__)
oauth = OAuth()
google = None

def init_oauth(app):
    global google
    oauth.init_app(app)
    google = oauth.register(
        name='google',
        client_id=Config.GOOGLE_CLIENT_ID,
        client_secret=Config.GOOGLE_CLIENT_SECRET,
        access_token_url='https://oauth2.googleapis.com/token',
        access_token_params=None,
        authorize_url='https://accounts.google.com/o/oauth2/v2/auth',
        authorize_params={'prompt': 'select_account'},
        api_base_url='https://www.googleapis.com/oauth2/v2/',
        client_kwargs={'scope': 'email profile'}
    )

def create_jwt(user_id):
    payload = {
        'sub': user_id,
        'exp': datetime.utcnow() + timedelta(hours=12),
        'iat': datetime.utcnow()
    }
    token = jwt.encode(payload, Config.JWT_SECRET, algorithm='HS256')
    return token

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    db = SessionLocal()
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        if not username or not email or not password:
            flash('Заполните все поля', 'danger')
            return render_template('register.html')
        if db.query(User).filter((User.username==username)|(User.email==email)).first():
            flash('Пользователь уже существует', 'danger')
            return render_template('register.html')
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user = User(username=username, email=email, password_hash=pw_hash, role='user')
        db.add(user); db.commit()
        flash('Регистрация успешна! Можно войти.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    db = SessionLocal()
    if request.method == 'POST':
        email = request.form.get('email','').strip().lower()
        password = request.form.get('password','')
        user = db.query(User).filter(User.email==email).first()
        if not user or not user.password_hash or not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
            flash('Неверные email или пароль', 'danger')
            return render_template('login.html')
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role
        flash('Добро пожаловать!', 'success')
        return redirect(url_for('main.index'))
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из аккаунта.', 'info')
    return redirect(url_for('main.index'))

@auth_bp.route('/auth/google')
def google_login():
    if not Config.GOOGLE_CLIENT_ID:
        flash('Google OAuth не настроен', 'warning')
        return redirect(url_for('auth.login'))
    redirect_uri = Config.OAUTH_REDIRECT_URI
    return google.authorize_redirect(redirect_uri)

@auth_bp.route('/auth/google/callback')
def google_callback():
    token = google.authorize_access_token()
    resp = google.get('userinfo')
    profile = resp.json()
    db = SessionLocal()
    user = db.query(User).filter(User.google_id==profile.get('id')).first()
    if not user:
        # пытаемся найти по email
        user = db.query(User).filter(User.email==profile.get('email').lower()).first()
        if user:
            user.google_id = profile.get('id')
        else:
            user = User(
                username=profile.get('name') or profile.get('email').split('@')[0],
                email=profile.get('email').lower(),
                password_hash=None,
                role='user',
                google_id=profile.get('id')
            )
            db.add(user)
        db.commit()
    session['user_id'] = user.id
    session['username'] = user.username
    session['role'] = user.role
    flash('Вход через Google выполнен.', 'success')
    return redirect(url_for('main.index'))

@auth_bp.route('/token')
def token():
    uid = session.get('user_id')
    if not uid:
        return {'error': 'unauthorized'}, 401
    return {'token': create_jwt(uid)}
