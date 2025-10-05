from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Project, ProjectAnalyst 
from app.utils.decorators import admin_required, supervisor_required

main_bp = Blueprint('main', __name__)

@main_bp.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    # Estadísticas para el dashboard
    total_users = User.query.count()
    pending_users = User.query.filter_by(is_active=False).count()
    active_users = User.query.filter_by(is_active=True).count()
    total_projects = Project.query.count()
    
    users_pending = User.query.filter_by(is_active=False).all()
    
    return render_template('dashboards/admin_dashboard.html',
                         total_users=total_users,
                         pending_users=pending_users,
                         active_users=active_users,
                         total_projects=total_projects,
                         users_pending=users_pending)

@main_bp.route('/supervisor/dashboard')
@login_required
@supervisor_required
def supervisor_dashboard():
    # Proyectos creados por este supervisor
    user_projects = Project.query.filter_by(created_by_id=current_user.id).all()
    
    return render_template('dashboards/supervisor_dashboard.html',
                         projects=user_projects)

@main_bp.route('/analyst/dashboard')
@login_required
def analyst_dashboard():
    # Obtener proyectos asignados al analista actual
    assigned_projects = Project.query.join(ProjectAnalyst).filter(
        ProjectAnalyst.analyst_id == current_user.id
    ).all()
    
    return render_template('dashboards/analyst_dashboard.html', projects=assigned_projects)

@main_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@main_bp.route('/admin/approve-user/<int:user_id>')
@login_required
@admin_required
def approve_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes aprobar tu propio usuario.', 'warning')
        return redirect(url_for('main.manage_users'))
    
    user.is_active = True
    db.session.commit()
    flash(f'Usuario {user.username} aprobado correctamente.', 'success')
    return redirect(url_for('main.manage_users'))

@main_bp.route('/admin/reject-user/<int:user_id>')
@login_required
@admin_required
def reject_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('No puedes rechazar tu propio usuario.', 'warning')
        return redirect(url_for('main.manage_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {username} rechazado y eliminado correctamente.', 'info')
    return redirect(url_for('main.manage_users'))

@main_bp.route('/admin/edit-user/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        # Actualizar datos del usuario
        user.username = request.form.get('username')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        user.is_active = bool(request.form.get('is_active'))
        
        db.session.commit()
        flash(f'Usuario {user.username} actualizado correctamente.', 'success')
        return redirect(url_for('main.manage_users'))
    
    return render_template('admin/edit_user.html', user=user)

@main_bp.route('/admin/reset-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_password(user_id):
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if new_password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('admin/reset_password.html', user=user)
        
        if len(new_password) < 6:
            flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
            return render_template('admin/reset_password.html', user=user)
        
        user.set_password(new_password)
        db.session.commit()
        flash(f'Contraseña de {user.username} restablecida correctamente.', 'success')
        return redirect(url_for('main.manage_users'))
    
    return render_template('admin/reset_password.html', user=user)

@main_bp.route('/admin/delete-user/<int:user_id>')
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('No puedes eliminar tu propio usuario.', 'warning')
        return redirect(url_for('main.manage_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'Usuario {username} eliminado correctamente.', 'info')
    return redirect(url_for('main.manage_users'))