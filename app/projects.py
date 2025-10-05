from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Project, User, ProjectAnalyst, Log, Catalog  # <- Asegurar que ProjectAnalyst esté importado
from app.utils.decorators import supervisor_required, admin_required
from datetime import datetime

projects_bp = Blueprint('projects', __name__)

def get_catalog_options(catalog_name):
    """Obtener opciones activas de un catálogo"""
    return [c.value for c in Catalog.query.filter_by(name=catalog_name, is_active=True).all()]

def log_project_change(project_id, user_id, field, old_value, new_value):
    """Función auxiliar para registrar cambios en el log"""
    log = Log(
        project_id=project_id,
        user_id=user_id,
        changed_field=field,
        old_value=str(old_value) if old_value is not None else '',
        new_value=str(new_value) if new_value is not None else ''
    )
    db.session.add(log)

@projects_bp.route('/projects')
@login_required
def projects_list():
    if current_user.role == 'Admin':
        projects = Project.query.all()
    elif current_user.role == 'Supervisor':
        projects = Project.query.filter_by(created_by_id=current_user.id).all()
    else:  # Analista
        # CORREGIDO: Obtener proyectos asignados al analista actual
        projects = Project.query.join(ProjectAnalyst).filter(
            ProjectAnalyst.analyst_id == current_user.id
        ).all()
    
    return render_template('projects/list.html', projects=projects)

@projects_bp.route('/projects/create', methods=['GET', 'POST'])
@login_required
@supervisor_required
def create_project():
    if request.method == 'POST':
        # Validar campos obligatorios
        gsf_code = request.form.get('gsf_code')
        invgate_code = request.form.get('invgate_code')
        name = request.form.get('name')
        
        if not all([gsf_code, invgate_code, name]):
            flash('Los campos Código GSF, Código Invgate y Nombre son obligatorios.', 'danger')
            return render_template('projects/create.html')
        
        # Validar que la priorización y estado sean válidos
        priority = request.form.get('priority')
        status = request.form.get('status', 'Pendiente')
        
        if priority and priority not in get_catalog_options('priority'):
            flash('La priorización seleccionada no es válida.', 'danger')
            return render_template('projects/create.html')
        
        if status not in get_catalog_options('status'):
            flash('El estado seleccionado no es válido.', 'danger')
            return render_template('projects/create.html')
        
        # Crear proyecto
        project = Project(
            gsf_code=gsf_code,
            invgate_code=invgate_code,
            name=name,
            priority=priority,
            estimated_hours=request.form.get('estimated_hours'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date() if request.form.get('start_date') else None,
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date() if request.form.get('end_date') else None,
            status=status,
            progress=request.form.get('progress', 0),
            test_cases=request.form.get('test_cases', 0),
            executed_cases=request.form.get('executed_cases', 0),
            created_by_id=current_user.id
        )
        
        db.session.add(project)
        db.session.flush()  # Para obtener el ID del proyecto
        
        # Asignar analistas
        analyst_ids = request.form.getlist('analysts')
        for analyst_id in analyst_ids:
            project_analyst = ProjectAnalyst(
                project_id=project.id,
                analyst_id=analyst_id
            )
            db.session.add(project_analyst)
        
        db.session.commit()
        
        # Log de creación
        log_project_change(project.id, current_user.id, 'PROYECTO CREADO', None, project.name)
        
        flash(f'Proyecto "{name}" creado exitosamente.', 'success')
        return redirect(url_for('projects.projects_list'))
    
    # Obtener datos para el formulario
    analysts = User.query.filter_by(role='Analista', is_active=True).all()
    priorities = get_catalog_options('priority')
    statuses = get_catalog_options('status')
    return render_template('projects/create.html', analysts=analysts, priorities=priorities, statuses=statuses)

@projects_bp.route('/projects/<int:project_id>')
@login_required
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar permisos
    if current_user.role == 'Analista':
        assigned = ProjectAnalyst.query.filter_by(project_id=project_id, analyst_id=current_user.id).first()
        if not assigned:
            flash('No tienes permisos para ver este proyecto.', 'danger')
            return redirect(url_for('projects.projects_list'))
    
    elif current_user.role == 'Supervisor':
        if project.created_by_id != current_user.id:
            flash('No tienes permisos para ver este proyecto.', 'danger')
            return redirect(url_for('projects.projects_list'))
    
    logs = Log.query.filter_by(project_id=project_id).order_by(Log.changed_at.desc()).all()
    return render_template('projects/detail.html', project=project, logs=logs)

@projects_bp.route('/projects/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
@supervisor_required
def edit_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar que el supervisor es el creador
    if project.created_by_id != current_user.id and current_user.role != 'Admin':
        flash('No tienes permisos para editar este proyecto.', 'danger')
        return redirect(url_for('projects.projects_list'))
    
    if request.method == 'POST':
        # Guardar valores antiguos para el log
        old_values = {
            'name': project.name,
            'priority': project.priority,
            'status': project.status,
            'progress': project.progress
        }
        
        # Validar catálogos
        priority = request.form.get('priority')
        status = request.form.get('status')
        
        if priority and priority not in get_catalog_options('priority'):
            flash('La priorización seleccionada no es válida.', 'danger')
            return redirect(url_for('projects.edit_project', project_id=project_id))
        
        if status not in get_catalog_options('status'):
            flash('El estado seleccionado no es válido.', 'danger')
            return redirect(url_for('projects.edit_project', project_id=project_id))
        
        # Actualizar proyecto
        project.gsf_code = request.form.get('gsf_code')
        project.invgate_code = request.form.get('invgate_code')
        project.name = request.form.get('name')
        project.priority = priority
        
        # Manejar campos numéricos que pueden estar vacíos
        estimated_hours = request.form.get('estimated_hours')
        project.estimated_hours = int(estimated_hours) if estimated_hours else None
        
        project.status = status
        project.progress = int(request.form.get('progress', 0))
        project.test_cases = int(request.form.get('test_cases', 0))
        project.executed_cases = int(request.form.get('executed_cases', 0))
        
        # Fechas - manejar campos vacíos
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        
        if start_date:
            project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            project.start_date = None
            
        if end_date:
            project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            project.end_date = None
        
        # Actualizar analistas
        ProjectAnalyst.query.filter_by(project_id=project_id).delete()
        analyst_ids = request.form.getlist('analysts')
        for analyst_id in analyst_ids:
            project_analyst = ProjectAnalyst(
                project_id=project_id,
                analyst_id=analyst_id
            )
            db.session.add(project_analyst)
        
        # Log de cambios
        for field, old_value in old_values.items():
            new_value = getattr(project, field)
            if str(old_value) != str(new_value):
                log_project_change(project_id, current_user.id, field, old_value, new_value)
        
        db.session.commit()
        flash(f'Proyecto "{project.name}" actualizado exitosamente.', 'success')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    analysts = User.query.filter_by(role='Analista', is_active=True).all()
    assigned_analysts = [pa.analyst_id for pa in project.analysts]
    priorities = get_catalog_options('priority')
    statuses = get_catalog_options('status')
    return render_template('projects/edit.html', project=project, analysts=analysts, 
                         assigned_analysts=assigned_analysts, priorities=priorities, statuses=statuses)

@projects_bp.route('/projects/<int:project_id>/update-progress', methods=['GET', 'POST'])
@login_required
def update_progress(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar permisos (solo analistas asignados o supervisores/admin)
    if current_user.role == 'Analista':
        assigned = ProjectAnalyst.query.filter_by(project_id=project_id, analyst_id=current_user.id).first()
        if not assigned:
            flash('No tienes permisos para actualizar este proyecto.', 'danger')
            return redirect(url_for('projects.projects_list'))
    
    if request.method == 'POST':
        # Guardar valores antiguos
        old_progress = project.progress
        old_status = project.status
        old_executed = project.executed_cases
        old_test_cases = project.test_cases
        old_observation = project.observation
        
        # Validar estado
        new_status = request.form.get('status')
        if new_status not in get_catalog_options('status'):
            flash('El estado seleccionado no es válido.', 'danger')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        
        # Actualizar campos
        project.progress = int(request.form.get('progress', project.progress))
        project.status = new_status
        project.test_cases = int(request.form.get('test_cases', project.test_cases))
        project.executed_cases = int(request.form.get('executed_cases', project.executed_cases))
        project.observation = request.form.get('observation', '')
        
        # Validar progreso
        if project.progress < 0 or project.progress > 100:
            flash('El porcentaje de avance debe estar entre 0 y 100.', 'danger')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        
        # Validar que casos ejecutados no sean mayores que casos de prueba
        if project.executed_cases > project.test_cases:
            flash('Los casos ejecutados no pueden ser mayores que los casos de prueba.', 'danger')
            return redirect(url_for('projects.project_detail', project_id=project_id))
        
        # Log de cambios
        if old_progress != project.progress:
            log_project_change(project_id, current_user.id, 'progress', old_progress, project.progress)
        if old_status != project.status:
            log_project_change(project_id, current_user.id, 'status', old_status, project.status)
        if old_test_cases != project.test_cases:
            log_project_change(project_id, current_user.id, 'test_cases', old_test_cases, project.test_cases)
        if old_executed != project.executed_cases:
            log_project_change(project_id, current_user.id, 'executed_cases', old_executed, project.executed_cases)
        if old_observation != project.observation:
            log_project_change(project_id, current_user.id, 'observation', old_observation, project.observation)
        
        db.session.commit()
        flash('Progreso del proyecto actualizado exitosamente.', 'success')
        return redirect(url_for('projects.project_detail', project_id=project_id))
    
    # Si es GET, mostrar formulario de actualización
    statuses = get_catalog_options('status')
    return render_template('projects/update_progress.html', project=project, statuses=statuses)

@projects_bp.route('/projects/<int:project_id>/delete', methods=['POST'])
@login_required
@supervisor_required
def delete_project(project_id):
    project = Project.query.get_or_404(project_id)
    
    # Verificar permisos
    if project.created_by_id != current_user.id and current_user.role != 'Admin':
        flash('No tienes permisos para eliminar este proyecto.', 'danger')
        return redirect(url_for('projects.projects_list'))
    
    project_name = project.name
    
    # Eliminar proyecto y relaciones (cascade se encarga de esto)
    db.session.delete(project)
    db.session.commit()
    
    flash(f'Proyecto "{project_name}" eliminado exitosamente.', 'info')
    return redirect(url_for('projects.projects_list'))