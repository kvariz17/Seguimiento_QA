from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'Admin':
            flash('Acceso denegado. Se requieren privilegios de administrador.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['Admin', 'Supervisor']:
            flash('Acceso denegado. Se requieren privilegios de supervisor.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def logout_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            flash('Ya tienes una sesión activa.', 'info')
            if current_user.role == 'Admin':
                return redirect(url_for('main.admin_dashboard'))
            elif current_user.role == 'Supervisor':
                return redirect(url_for('main.supervisor_dashboard'))
            else:
                return redirect(url_for('main.analyst_dashboard'))
        return f(*args, **kwargs)
    return decorated_function