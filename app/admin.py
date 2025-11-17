
from flask import Blueprint, render_template, redirect, url_for, flash, session, request
from .extensions import SessionLocal
from .models import User, Guide

admin_bp = Blueprint('admin', __name__)

def require_admin():
    role = session.get('role')
    return role == 'admin'

@admin_bp.route('/admin', methods=['GET','POST'])
def dashboard():
    if not require_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    db = SessionLocal()
    users = db.query(User).order_by(User.created_at.desc()).all()
    guides = db.query(Guide).order_by(Guide.created_at.desc()).all()
    stats = {
        'users': len(users),
        'guides': len(guides)
    }
    return render_template('admin.html', users=users, guides=guides, stats=stats)

@admin_bp.route('/admin/role', methods=['POST'])
def set_role():
    if not require_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    db = SessionLocal()
    uid = int(request.form.get('user_id'))
    role = request.form.get('role','user')
    u = db.query(User).get(uid)
    if u:
        u.role = role; db.commit()
        flash('Роль обновлена', 'success')
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/admin/guide/delete', methods=['POST'])
def delete_guide():
    if not require_admin():
        flash('Доступ запрещён', 'danger')
        return redirect(url_for('main.index'))
    db = SessionLocal()
    gid = int(request.form.get('guide_id'))
    g = db.query(Guide).get(gid)
    if g:
        db.delete(g); db.commit()
        flash('Гайд удалён', 'info')
    return redirect(url_for('admin.dashboard'))
