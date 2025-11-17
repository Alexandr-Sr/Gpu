
from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload
import jwt
from config import Config
from .extensions import SessionLocal
from .models import Guide, User

api_bp = Blueprint('api', __name__, url_prefix='/api')

def require_jwt():
    auth = request.headers.get('Authorization','')
    if not auth.startswith('Bearer '):
        return None
    token = auth.split(' ',1)[1]
    try:
        data = jwt.decode(token, Config.JWT_SECRET, algorithms=['HS256'])
        return data.get('sub')
    except Exception:
        return None

@api_bp.get('/guides')
def api_guides():
    db = SessionLocal()
    guides = db.query(Guide).options(joinedload(Guide.author)).order_by(Guide.created_at.desc()).limit(20).all()
    return jsonify([{
        'id': g.id,
        'title': g.title,
        'description': g.description[:300],
        'image_url': g.image_url,
        'category': g.category,
        'author': g.author.username,
        'created_at': g.created_at.isoformat()
    } for g in guides])

@api_bp.post('/guides')
def api_create_guide():
    uid = require_jwt()
    if not uid: return {'error': 'unauthorized'}, 401
    payload = request.get_json(force=True, silent=True) or {}
    title = payload.get('title','').strip()
    description = payload.get('description','').strip()
    category = payload.get('category','Обслуживание').strip()
    if not title or not description:
        return {'error':'title and description required'}, 400
    db = SessionLocal()
    g = Guide(title=title, description=description, category=category, author_id=uid)
    db.add(g); db.commit()
    return {'id': g.id}, 201

@api_bp.get('/guides/<int:gid>')
def api_get_guide(gid):
    db = SessionLocal()
    g = db.query(Guide).options(joinedload(Guide.author)).get(gid)
    if not g: return {'error':'not found'}, 404
    return {
        'id': g.id,
        'title': g.title,
        'description': g.description,
        'image_url': g.image_url,
        'category': g.category,
        'author': g.author.username,
        'created_at': g.created_at.isoformat()
    }
