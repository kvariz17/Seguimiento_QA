from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User
from app.utils.decorators import logout_required

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
@auth_bp.route('/index')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'Admin':
            return redirect(url_for('main.admin_dashboard'))
        elif current_user.role == 'Supervisor':
            return redirect(url_for('main.supervisor_dashboard'))
        else:
            return redirect(url_for('main.analyst_dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
@logout_required
def login():
    if request.method == 'POST':
        username = request.form.get('username')  # Cambiado de email a username
        password = request.form.get('password')
        remember_me = bool(request.form.get('remember_me'))
        
        user = User.query.filter_by(username=username).first()  # Cambiado de email a username
        
        if user and user.check_password(password):
            if user.is_active:
                login_user(user, remember=remember_me)
                flash(f'¡Bienvenido {user.username}!', 'success')
                
                # Redirigir según el rol
                if user.role == 'Admin':
                    return redirect(url_for('main.admin_dashboard'))
                elif user.role == 'Supervisor':
                    return redirect(url_for('main.supervisor_dashboard'))
                else:
                    return redirect(url_for('main.analyst_dashboard'))
            else:
                flash('Tu cuenta está pendiente de aprobación por un administrador.', 'warning')
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')  # Mensaje actualizado
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
@logout_required
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        role = request.form.get('role', 'Analista')
        
        # Validaciones básicas
        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está en uso.', 'danger')
            return render_template('auth/register.html')
        
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado.', 'danger')
            return render_template('auth/register.html')
        
        # Crear usuario (inactivo por defecto)
        new_user = User(
            username=username,
            email=email,
            role=role,
            is_active=False  # Requiere aprobación del admin
        )
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('¡Registro exitoso! Tu cuenta está pendiente de aprobación por un administrador.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('auth.login'))