from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Catalog
from app.utils.decorators import admin_required

catalogs_bp = Blueprint('catalogs', __name__)

@catalogs_bp.route('/admin/catalogs')
@login_required
@admin_required
def manage_catalogs():
    priorities = Catalog.query.filter_by(name='priority', is_active=True).all()
    statuses = Catalog.query.filter_by(name='status', is_active=True).all()
    return render_template('admin/catalogs.html', priorities=priorities, statuses=statuses)

@catalogs_bp.route('/admin/catalogs/add', methods=['POST'])
@login_required
@admin_required
def add_catalog_item():
    catalog_type = request.form.get('catalog_type')
    value = request.form.get('value')
    
    if not value:
        flash('El valor no puede estar vacío.', 'danger')
        return redirect(url_for('catalogs.manage_catalogs'))
    
    # Verificar si ya existe
    existing = Catalog.query.filter_by(name=catalog_type, value=value).first()
    if existing:
        flash('Este valor ya existe en el catálogo.', 'warning')
        return redirect(url_for('catalogs.manage_catalogs'))
    
    catalog_item = Catalog(
        name=catalog_type,
        value=value,
        is_active=True
    )
    
    db.session.add(catalog_item)
    db.session.commit()
    
    flash(f'Valor "{value}" agregado al catálogo {catalog_type}.', 'success')
    return redirect(url_for('catalogs.manage_catalogs'))

@catalogs_bp.route('/admin/catalogs/delete/<int:catalog_id>')
@login_required
@admin_required
def delete_catalog_item(catalog_id):
    catalog_item = Catalog.query.get_or_404(catalog_id)
    value = catalog_item.value
    catalog_type = catalog_item.name
    
    # No permitir eliminar valores que están en uso
    from app.models import Project
    if catalog_type == 'priority':
        in_use = Project.query.filter_by(priority=value).first()
    else:  # status
        in_use = Project.query.filter_by(status=value).first()
    
    if in_use:
        flash(f'No se puede eliminar "{value}" porque está en uso en algunos proyectos.', 'danger')
        return redirect(url_for('catalogs.manage_catalogs'))
    
    db.session.delete(catalog_item)
    db.session.commit()
    
    flash(f'Valor "{value}" eliminado del catálogo {catalog_type}.', 'info')
    return redirect(url_for('catalogs.manage_catalogs'))

@catalogs_bp.route('/admin/catalogs/toggle/<int:catalog_id>')
@login_required
@admin_required
def toggle_catalog_item(catalog_id):
    catalog_item = Catalog.query.get_or_404(catalog_id)
    catalog_item.is_active = not catalog_item.is_active
    db.session.commit()
    
    status = "activado" if catalog_item.is_active else "desactivado"
    flash(f'Valor "{catalog_item.value}" {status}.', 'success')
    return redirect(url_for('catalogs.manage_catalogs'))