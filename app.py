from flask import Flask, render_template, request, redirect, url_for, flash, session, g, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, Usuario, Turno, LogActividad, RolUsuario, ConfiguracionHorario
from config import Config
from datetime import datetime, timedelta, date
import json
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Inicializar Flask
app = Flask(__name__)
app.config.from_object(Config)

# Inicializar extensiones
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página'

# Context processor
@app.context_processor
def utility_processor():
    return {'now': datetime}

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ==================== CONFIGURACIÓN INICIAL DE HORARIOS ====================
def crear_configuracion_inicial():
    """Crea la configuración de horarios por defecto si no existe"""
    config = ConfiguracionHorario.query.first()
    if not config:
        # Horarios laborables por defecto
        horas_laborales = {
            "lunes": ["09:00-13:00", "15:00-18:00"],
            "martes": ["09:00-13:00", "15:00-18:00"],
            "miercoles": ["09:00-13:00", "15:00-18:00"],
            "jueves": ["09:00-13:00", "15:00-18:00"],
            "viernes": ["09:00-13:00", "15:00-18:00"]
        }
        
        # Horario de almuerzo
        horario_almuerzo = {
            "inicio": "13:00",
            "fin": "15:00"
        }
        
        config = ConfiguracionHorario(
            nombre="Configuración Principal",
            activo=True,
            duracion_turno=60
        )
        config.set_horas_laborales(horas_laborales)
        config.set_dias_no_laborables([])
        config.set_horario_almuerzo(horario_almuerzo)
        
        db.session.add(config)
        db.session.commit()
        print("Configuración de horarios creada")

# Agregar esta llamada después de crear las tablas
with app.app_context():
    db.create_all()
    
    # Crear usuario admin si no existe
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(
            username='admin',
            email='admin@sistema.com',
            nombre_completo='Administrador del Sistema',
            rol=RolUsuario.ADMIN,
            activo=True
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print("Usuario admin creado: admin / admin123")
    
    # Crear configuración de horarios
    crear_configuracion_inicial()

# ==================== RUTAS PARA CONFIGURACIÓN DE HORARIOS ====================
@app.route('/admin/horarios')
@login_required
def admin_horarios():
    """Panel de configuración de horarios"""
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('dashboard'))
    
    config = ConfiguracionHorario.query.first()
    return render_template('admin/horarios.html', config=config)

@app.route('/admin/horarios/guardar', methods=['POST'])
@login_required
def admin_horarios_guardar():
    """Guardar configuración de horarios"""
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('dashboard'))
    
    config = ConfiguracionHorario.query.first()
    if not config:
        config = ConfiguracionHorario()
        db.session.add(config)
    
    # Guardar horas laborables
    horas_laborales = {}
    dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
    
    for dia in dias:
        bloques = []
        mañana_inicio = request.form.get(f'{dia}_manana_inicio')
        mañana_fin = request.form.get(f'{dia}_manana_fin')
        tarde_inicio = request.form.get(f'{dia}_tarde_inicio')
        tarde_fin = request.form.get(f'{dia}_tarde_fin')
        
        if mañana_inicio and mañana_fin:
            bloques.append(f"{mañana_inicio}-{mañana_fin}")
        if tarde_inicio and tarde_fin:
            bloques.append(f"{tarde_inicio}-{tarde_fin}")
        
        if bloques:
            horas_laborales[dia] = bloques
    
    config.set_horas_laborales(horas_laborales)
    
    # Guardar horario de almuerzo
    almuerzo_inicio = request.form.get('almuerzo_inicio')
    almuerzo_fin = request.form.get('almuerzo_fin')
    config.set_horario_almuerzo({
        "inicio": almuerzo_inicio,
        "fin": almuerzo_fin
    })
    
    # Guardar días no laborables
    dias_no_laborables = request.form.get('dias_no_laborables', '')
    if dias_no_laborables:
        dias_list = [d.strip() for d in dias_no_laborables.split(',') if d.strip()]
        config.set_dias_no_laborables(dias_list)
    else:
        config.set_dias_no_laborables([])
    
    # Guardar duración del turno
    config.duracion_turno = int(request.form.get('duracion_turno', 60))
    
    try:
        db.session.commit()
        flash('Configuración de horarios guardada exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al guardar la configuración', 'error')
    
    return redirect(url_for('admin_horarios'))

# Funciones auxiliares
def registrar_log(usuario_id, accion, descripcion, ip_address=None):
    """Registra actividad del usuario en el log"""
    log = LogActividad(
        usuario_id=usuario_id,
        accion=accion,
        descripcion=descripcion,
        ip_address=ip_address or request.remote_addr
    )
    db.session.add(log)
    db.session.commit()

def generar_numero_turno():
    """Genera el siguiente número de turno"""
    ultimo_turno = Turno.query.order_by(Turno.id.desc()).first()
    if ultimo_turno:
        numero = int(ultimo_turno.numero) + 1
        return str(numero).zfill(3)
    return '001'

def verificar_permiso(rol_requerido):
    """Verifica si el usuario tiene el rol requerido"""
    if current_user.rol == RolUsuario.ADMIN:
        return True
    return current_user.rol == rol_requerido

# ==================== RUTAS DE AUTENTICACIÓN ====================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        usuario = Usuario.query.filter_by(username=username).first()
        
        if usuario and usuario.check_password(password) and usuario.activo:
            login_user(usuario, remember=True)
            usuario.ultimo_acceso = datetime.utcnow()
            db.session.commit()
            
            registrar_log(
                usuario.id,
                'login',
                f'Usuario {usuario.username} inició sesión'
            )
            
            next_page = request.args.get('next')
            flash(f'Bienvenido {usuario.nombre_completo}!', 'success')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre_completo = request.form.get('nombre_completo')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validaciones
        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect(url_for('register'))
        
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('register'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return redirect(url_for('register'))
        
        # Crear nuevo usuario (por defecto como usuario normal)
        nuevo_usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            rol=RolUsuario.USUARIO,
            activo=True
        )
        nuevo_usuario.set_password(password)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Usuario registrado exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar usuario', 'error')
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    registrar_log(current_user.id, 'logout', f'Usuario {current_user.username} cerró sesión')
    logout_user()
    flash('Has cerrado sesión exitosamente', 'success')
    return redirect(url_for('login'))

# ==================== RUTAS PRINCIPALES ====================
@app.route('/')
@login_required
def dashboard():
    # Estadísticas para el dashboard
    turnos_hoy = Turno.query.filter(
        db.func.date(Turno.fecha_creacion) == datetime.utcnow().date()
    ).count()
    
    turnos_pendientes = Turno.query.filter_by(estado='pendiente').count()
    turnos_atendidos_hoy = Turno.query.filter(
        Turno.estado == 'atendido',
        db.func.date(Turno.fecha_atencion) == datetime.utcnow().date()
    ).count()
    
    tiempo_promedio = db.session.query(db.func.avg(Turno.tiempo_espera)).filter(
        Turno.tiempo_espera.isnot(None)
    ).scalar() or 0
    
    # Últimos turnos
    ultimos_turnos = Turno.query.order_by(Turno.fecha_creacion.desc()).limit(5).all()
    
    return render_template('dashboard.html',
                         turnos_hoy=turnos_hoy,
                         turnos_pendientes=turnos_pendientes,
                         turnos_atendidos_hoy=turnos_atendidos_hoy,
                         tiempo_promedio=int(tiempo_promedio),
                         ultimos_turnos=ultimos_turnos)

# ==================== RUTAS DE TURNOS ====================
@app.route('/tomar_turno', methods=['GET', 'POST'])
@login_required
def tomar_turno():
    config = ConfiguracionHorario.query.first()
    
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        servicio = request.form.get('servicio')
        fecha_turno_str = request.form.get('fecha_turno')
        hora_turno = request.form.get('hora_turno')
        prioridad = request.form.get('prioridad', 0)
        
        if not nombre or not servicio or not fecha_turno_str or not hora_turno:
            flash('Todos los campos son obligatorios', 'error')
            return redirect(url_for('tomar_turno'))
        
        # Convertir fecha y hora
        fecha_turno = datetime.strptime(f"{fecha_turno_str} {hora_turno}", '%Y-%m-%d %H:%M')
        
        # Validar que la fecha/hora sea laborable
        if not config.es_hora_laborable(fecha_turno):
            flash('La fecha y hora seleccionada no está disponible', 'error')
            return redirect(url_for('tomar_turno'))
        
        # Verificar que no haya otro turno en ese horario
        turno_existente = Turno.query.filter(
            Turno.fecha_turno == fecha_turno,
            Turno.estado != 'cancelado'
        ).first()
        
        if turno_existente:
            flash('Ya existe un turno en ese horario. Por favor selecciona otro horario.', 'error')
            return redirect(url_for('tomar_turno'))
        
        numero_turno = generar_numero_turno()
        
        nuevo_turno = Turno(
            numero=numero_turno,
            usuario_id=current_user.id,
            nombre_cliente=nombre,
            tipo_servicio=servicio,
            fecha_turno=fecha_turno,
            estado='pendiente',
            prioridad=int(prioridad),
            usuario_creacion_id=current_user.id
        )
        
        try:
            db.session.add(nuevo_turno)
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'crear_turno',
                f'Turno #{numero_turno} creado para {nombre} - Servicio: {servicio} - Fecha: {fecha_turno}'
            )
            
            flash(f'Turno #{numero_turno} creado exitosamente para el {fecha_turno.strftime("%d/%m/%Y %H:%M")}', 'success')
            return render_template('tomar_turno.html', turno=nuevo_turno)
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el turno', 'error')
            return redirect(url_for('tomar_turno'))
    
    # GET: Mostrar formulario con fechas disponibles
    return render_template('tomar_turno.html', turno=None, config=config)

@app.route('/obtener_horarios_disponibles')
@login_required
def obtener_horarios_disponibles():
    """API para obtener horarios disponibles por fecha"""
    fecha_str = request.args.get('fecha')
    if not fecha_str:
        return jsonify({'horarios': []})
    
    try:
        fecha = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        config = ConfiguracionHorario.query.first()
        
        if not config:
            return jsonify({'horarios': []})
        
        horarios = config.obtener_horarios_disponibles(fecha)
        
        return jsonify({'horarios': horarios})
    except Exception as e:
        print(f"Error al obtener horarios: {e}")
        return jsonify({'horarios': [], 'error': str(e)})


@app.route('/listar_turnos')
@login_required
def listar_turnos():
    # Ordenar por fecha y hora
    pendientes = Turno.query.filter_by(estado='pendiente').order_by(
        Turno.prioridad.desc(),
        Turno.fecha_turno
    ).all()
    
    atendidos = Turno.query.filter_by(estado='atendido').order_by(
        Turno.fecha_atencion.desc()
    ).limit(20).all()
    
    return render_template('listar_turnos.html', 
                         pendientes=pendientes, 
                         atendidos=atendidos)

@app.route('/atender_turno/<int:id>', methods=['GET', 'POST'])
@login_required
def atender_turno(id):
    # Solo admin y operadores pueden atender turnos
    if not verificar_permiso(RolUsuario.OPERADOR) and current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para atender turnos', 'error')
        return redirect(url_for('listar_turnos'))
    
    turno = Turno.query.get_or_404(id)
    
    # Obtener siguientes turnos para mostrar en la página
    siguientes_turnos = Turno.query.filter_by(estado='pendiente').filter(
        Turno.id != id
    ).order_by(
        Turno.prioridad.desc(),
        Turno.fecha_creacion
    ).limit(5).all()
    
    if request.method == 'POST':
        if turno.estado == 'pendiente':
            notas = request.form.get('notas', '')
            turno.estado = 'atendido'
            turno.fecha_atencion = datetime.utcnow()
            turno.usuario_atencion_id = current_user.id
            turno.calcular_tiempo_espera()
            
            try:
                db.session.commit()
                
                registrar_log(
                    current_user.id,
                    'atender_turno',
                    f'Turno #{turno.numero} atendido por {current_user.username}. Notas: {notas[:100]}'
                )
                
                flash(f'Turno #{turno.numero} atendido exitosamente', 'success')
                return redirect(url_for('listar_turnos'))
            except Exception as e:
                db.session.rollback()
                flash('Error al atender el turno', 'error')
                return redirect(url_for('atender_turno', id=id))
    
    return render_template('atender_turno.html', 
                         turno=turno, 
                         siguientes_turnos=siguientes_turnos)

@app.route('/cancelar_turno/<int:id>')
@login_required
def cancelar_turno(id):
    turno = Turno.query.get_or_404(id)
    
    if turno.estado == 'pendiente':
        turno.estado = 'cancelado'
        
        try:
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'cancelar_turno',
                f'Turno #{turno.numero} cancelado por {current_user.username}'
            )
            
            flash(f'Turno #{turno.numero} cancelado', 'warning')
        except Exception as e:
            db.session.rollback()
            flash('Error al cancelar el turno', 'error')
    
    return redirect(url_for('listar_turnos'))

# ==================== RUTAS DE USUARIOS ====================
@app.route('/perfil')
@login_required
def perfil():
    return render_template('perfil.html', usuario=current_user)

@app.route('/perfil/editar', methods=['GET', 'POST'])
@login_required
def perfil_editar():
    if request.method == 'POST':
        current_user.nombre_completo = request.form.get('nombre_completo')
        current_user.telefono = request.form.get('telefono')
        current_user.direccion = request.form.get('direccion')
        
        # Cambiar email requiere verificación
        nuevo_email = request.form.get('email')
        if nuevo_email != current_user.email:
            if Usuario.query.filter_by(email=nuevo_email).first():
                flash('El email ya está registrado por otro usuario', 'error')
                return redirect(url_for('perfil_editar'))
            current_user.email = nuevo_email
        
        # Cambiar contraseña
        password_actual = request.form.get('password_actual')
        nueva_password = request.form.get('nueva_password')
        confirmar_password = request.form.get('confirmar_password')
        
        if password_actual and nueva_password:
            if not current_user.check_password(password_actual):
                flash('Contraseña actual incorrecta', 'error')
                return redirect(url_for('perfil_editar'))
            
            if nueva_password != confirmar_password:
                flash('Las nuevas contraseñas no coinciden', 'error')
                return redirect(url_for('perfil_editar'))
            
            current_user.set_password(nueva_password)
        
        try:
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'editar_perfil',
                f'Perfil de {current_user.username} actualizado'
            )
            
            flash('Perfil actualizado exitosamente', 'success')
            return redirect(url_for('perfil'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el perfil', 'error')
    
    return render_template('perfil_editar.html', usuario=current_user)

@app.route('/mis_turnos')
@login_required
def mis_turnos():
    # Obtener turnos del usuario actual, ordenados por fecha
    turnos = Turno.query.filter_by(usuario_id=current_user.id).order_by(
        Turno.fecha_turno.desc()
    ).all()
    
    return render_template('mis_turnos.html', turnos=turnos)

@app.route('/cancelar_mi_turno/<int:id>')
@login_required
def cancelar_mi_turno(id):
    turno = Turno.query.get_or_404(id)
    
    # Verificar que el turno pertenezca al usuario
    if turno.usuario_id != current_user.id:
        flash('No tienes permiso para cancelar este turno', 'error')
        return redirect(url_for('mis_turnos'))
    
    if turno.estado == 'pendiente':
        turno.estado = 'cancelado'
        
        try:
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'cancelar_mi_turno',
                f'Turno #{turno.numero} cancelado por el usuario {current_user.username}'
            )
            
            flash(f'Turno #{turno.numero} cancelado exitosamente', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error al cancelar el turno', 'error')
    else:
        flash('Solo se pueden cancelar turnos pendientes', 'error')
    
    return redirect(url_for('mis_turnos'))

# ==================== RUTAS DE ADMINISTRACIÓN ====================
@app.route('/estadisticas')
@login_required
def estadisticas():
    # Solo admin puede ver estadísticas completas
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('dashboard'))
    
    # Estadísticas avanzadas
    total_turnos = Turno.query.count()
    turnos_por_servicio = db.session.query(
        Turno.tipo_servicio,
        db.func.count(Turno.id)
    ).group_by(Turno.tipo_servicio).all()
    
    turnos_por_estado = db.session.query(
        Turno.estado,
        db.func.count(Turno.id)
    ).group_by(Turno.estado).all()
    
    turnos_por_usuario = db.session.query(
        Usuario.username,
        db.func.count(Turno.id)
    ).join(Turno, Turno.usuario_creacion_id == Usuario.id).group_by(Usuario.username).all()
    
    return render_template('estadisticas.html',
                         total_turnos=total_turnos,
                         turnos_por_servicio=turnos_por_servicio,
                         turnos_por_estado=turnos_por_estado,
                         turnos_por_usuario=turnos_por_usuario)

@app.route('/admin/usuarios')
@login_required
def admin_usuarios():
    # Solo admin puede ver todos los usuarios
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para acceder a esta página', 'error')
        return redirect(url_for('dashboard'))
    
    usuarios = Usuario.query.all()
    return render_template('admin/usuarios.html', usuarios=usuarios)

@app.route('/admin/usuario/nuevo', methods=['GET', 'POST'])
@login_required
def admin_usuario_nuevo():
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        nombre_completo = request.form.get('nombre_completo')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        rol = request.form.get('rol')
        password = request.form.get('password')
        
        # Validaciones
        if Usuario.query.filter_by(username=username).first():
            flash('El nombre de usuario ya existe', 'error')
            return redirect(url_for('admin_usuario_nuevo'))
        
        if Usuario.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return redirect(url_for('admin_usuario_nuevo'))
        
        # Crear nuevo usuario
        nuevo_usuario = Usuario(
            username=username,
            email=email,
            nombre_completo=nombre_completo,
            telefono=telefono,
            direccion=direccion,
            rol=RolUsuario(rol),
            activo=True
        )
        nuevo_usuario.set_password(password)
        
        try:
            db.session.add(nuevo_usuario)
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'crear_usuario',
                f'Usuario {username} creado por {current_user.username}'
            )
            
            flash(f'Usuario {username} creado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al crear el usuario', 'error')
    
    return render_template('admin/usuario_form.html', usuario=None)

@app.route('/admin/usuario/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def admin_usuario_editar(id):
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    
    if request.method == 'POST':
        usuario.username = request.form.get('username')
        usuario.email = request.form.get('email')
        usuario.nombre_completo = request.form.get('nombre_completo')
        usuario.telefono = request.form.get('telefono')
        usuario.direccion = request.form.get('direccion')
        usuario.rol = RolUsuario(request.form.get('rol'))
        usuario.activo = 'activo' in request.form
        
        # Cambiar contraseña si se proporcionó
        nueva_password = request.form.get('password')
        if nueva_password:
            usuario.set_password(nueva_password)
        
        try:
            db.session.commit()
            
            registrar_log(
                current_user.id,
                'editar_usuario',
                f'Usuario {usuario.username} editado por {current_user.username}'
            )
            
            flash(f'Usuario {usuario.username} actualizado exitosamente', 'success')
            return redirect(url_for('admin_usuarios'))
        except Exception as e:
            db.session.rollback()
            flash('Error al actualizar el usuario', 'error')
    
    return render_template('admin/usuario_form.html', usuario=usuario)

@app.route('/admin/usuario/eliminar/<int:id>')
@login_required
def admin_usuario_eliminar(id):
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    
    # No permitir eliminar al propio admin
    if usuario.id == current_user.id:
        flash('No puedes eliminar tu propia cuenta', 'error')
        return redirect(url_for('admin_usuarios'))
    
    try:
        db.session.delete(usuario)
        db.session.commit()
        
        registrar_log(
            current_user.id,
            'eliminar_usuario',
            f'Usuario {usuario.username} eliminado por {current_user.username}'
        )
        
        flash(f'Usuario {usuario.username} eliminado exitosamente', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al eliminar el usuario', 'error')
    
    return redirect(url_for('admin_usuarios'))

@app.route('/cambiar_rol/<int:id>', methods=['POST'])
@login_required
def cambiar_rol(id):
    if current_user.rol != RolUsuario.ADMIN:
        flash('No tienes permiso para realizar esta acción', 'error')
        return redirect(url_for('dashboard'))
    
    usuario = Usuario.query.get_or_404(id)
    nuevo_rol = request.form.get('rol')
    
    if nuevo_rol in [r.value for r in RolUsuario]:
        usuario.rol = RolUsuario(nuevo_rol)
        db.session.commit()
        
        registrar_log(
            current_user.id,
            'cambiar_rol',
            f'Rol de {usuario.username} cambiado a {nuevo_rol}'
        )
        
        flash(f'Rol de {usuario.username} actualizado exitosamente', 'success')
    
    return redirect(url_for('admin_usuarios'))

# ==================== INICIO DE LA APLICACIÓN ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)