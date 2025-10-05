from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # Admin, Supervisor, Analista
    is_active = db.Column(db.Boolean, default=False)  # False=pending approval
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relaciones
    projects_created = db.relationship('Project', backref='creator', lazy=True, foreign_keys='Project.created_by_id')
    projects_assigned = db.relationship('ProjectAnalyst', backref='analyst', lazy=True, foreign_keys='ProjectAnalyst.analyst_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username} - {self.role}>'

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    gsf_code = db.Column(db.String(50), nullable=False)
    invgate_code = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    priority = db.Column(db.String(20))  # Regulatorio, Crítico, Alta, Media, Baja
    estimated_hours = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(50))
    progress = db.Column(db.Integer, default=0)  # 0-100
    test_cases = db.Column(db.Integer, default=0)
    executed_cases = db.Column(db.Integer, default=0)
    observation = db.Column(db.Text)  # <- NUEVO CAMPO: Observación del analista
    
    # Claves foráneas
    created_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Tiempo
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relaciones
    analysts = db.relationship('ProjectAnalyst', backref='project', lazy=True, cascade='all, delete-orphan')
    evidences = db.relationship('Evidence', backref='project', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('Log', backref='project', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.gsf_code} - {self.name}>'

class ProjectAnalyst(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    analyst_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProjectAnalyst project:{self.project_id} analyst:{self.analyst_id}>'

class Evidence(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)  # Tamaño en bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Claves foráneas
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Relación
    uploader = db.relationship('User', backref='evidences')
    
    def __repr__(self):
        return f'<Evidence {self.filename}>'

class Log(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    changed_field = db.Column(db.String(100), nullable=False)
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación
    user = db.relationship('User', backref='logs')
    
    def __repr__(self):
        return f'<Log {self.changed_field} by user:{self.user_id}>'

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relación
    user = db.relationship('User', backref='notifications')
    
    def __repr__(self):
        return f'<Notification for user:{self.user_id}>'

class Catalog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # 'priority', 'status'
    value = db.Column(db.String(100), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Catalog {self.name}: {self.value}>'

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))