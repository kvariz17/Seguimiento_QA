from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

db = SQLAlchemy()
login_manager = LoginManager()

def create_app():
    app = Flask(__name__)
    
    # Configuración
    app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui_cambiar_en_produccion'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qa_system.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Inicializar extensiones
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'
    
    # Registrar blueprints
    from app.auth import auth_bp
    from app.main import main_bp
    from app.projects import projects_bp
    from app.catalogs import catalogs_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(catalogs_bp)
    
    # Crear tablas y datos por defecto
    with app.app_context():
        db.create_all()
        from app.models import User, Catalog
        
        # Crear usuario admin si no existe
        if not User.query.filter_by(username='admin').first():
            admin_user = User(
                username='admin',
                email='admin@qa.com',
                role='Admin',
                is_active=True
            )
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Usuario admin creado: admin / admin123")
        
        # Crear catálogos por defecto si no existen
        default_priorities = ['Regulatorio', 'Crítico', 'Alta', 'Media', 'Baja']
        default_statuses = ['Pendiente', 'En Progreso', 'En Revisión', 'Completado', 'Bloqueado']
        
        for priority in default_priorities:
            if not Catalog.query.filter_by(name='priority', value=priority).first():
                catalog_item = Catalog(name='priority', value=priority)
                db.session.add(catalog_item)
        
        for status in default_statuses:
            if not Catalog.query.filter_by(name='status', value=status).first():
                catalog_item = Catalog(name='status', value=status)
                db.session.add(catalog_item)
        
        db.session.commit()
        print("Catálogos por defecto creados")
    
    return app