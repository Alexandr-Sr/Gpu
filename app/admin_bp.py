from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime
from .models import Guide, User
from . import db

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/verify_guide', methods=['POST'])
@login_required
def verify_guide():
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Требуются права администратора'}), 403
    data = request.get_json() or {}
    guide_id = data.get('guide_id')
    if not guide_id:
        return jsonify({'error': 'guide_id required'}), 400
    guide = db.session.get(Guide, guide_id)
    if not guide:
        return jsonify({'error': 'Guide not found'}), 404
    new_val = not bool(guide.verified_by_admin)
    guide.verified_by_admin = new_val
    if new_val:
        guide.verified_by_id = current_user.id
        guide.verified_at = datetime.utcnow()
    else:
        guide.verified_by_id = None
        guide.verified_at = None
    db.session.add(guide)
    db.session.commit()
    return jsonify({
        'guide_id': guide.id,
        'verified_by_admin': guide.verified_by_admin,
        'verified_by_id': guide.verified_by_id,
        'verified_at': guide.verified_at.isoformat() if guide.verified_at else None
    })

@admin_bp.route('/toggle_admin', methods=['POST'])
@login_required
def toggle_admin():
    if not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Требуются права администратора'}), 403
    data = request.get_json() or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    user.is_admin = not bool(user.is_admin)
    db.session.add(user)
    db.session.commit()
    return jsonify({'user_id': user.id, 'is_admin': user.is_admin})
