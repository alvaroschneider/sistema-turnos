from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, time, date, timedelta
from enum import Enum
import json

db = SQLAlchemy()

class RolUsuario(Enum):
    ADMIN = 'admin'
    OPERADOR = 'operador'
    USUARIO = 'usuario'

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    nombre_completo = db.Column(db.String(150), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)
    direccion = db.Column(db.String(200), nullable=True)
    rol = db.Column(db.Enum(RolUsuario), default=RolUsuario.USUARIO)
    activo = db.Column(db.Boolean, default=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime, nullable=True)
    
    # Relaciones
    turnos = db.relationship('Turno', foreign_keys='Turno.usuario_id', backref='usuario', lazy='dynamic')
    turnos_creados = db.relationship('Turno', foreign_keys='Turno.usuario_creacion_id', backref='creador')
    turnos_atendidos = db.relationship('Turno', foreign_keys='Turno.usuario_atencion_id', backref='atendedor')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Usuario {self.username}>'

class ConfiguracionHorario(db.Model):
    """Configuración de horarios laborales"""
    __tablename__ = 'configuracion_horarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    
    # Horario laboral (JSON)
    horas_laborales = db.Column(db.Text, nullable=False)  # Formato: {"lunes": ["09:00-13:00", "15:00-18:00"], ...}
    
    # Días no laborables (JSON)
    dias_no_laborables = db.Column(db.Text, default='[]')  # Lista de fechas en formato YYYY-MM-DD
    
    # Horario de almuerzo (JSON)
    horario_almuerzo = db.Column(db.Text, nullable=False)  # Formato: {"inicio": "12:00", "fin": "14:00"}
    
    # Duración del turno en minutos
    duracion_turno = db.Column(db.Integer, default=60)  # 1 hora por defecto
    
    # Activo
    activo = db.Column(db.Boolean, default=True)
    
    # Metadatos
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_actualizacion = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def get_horas_laborales(self):
        return json.loads(self.horas_laborales)
    
    def set_horas_laborales(self, horas):
        self.horas_laborales = json.dumps(horas)
    
    def get_dias_no_laborables(self):
        return json.loads(self.dias_no_laborables)
    
    def set_dias_no_laborables(self, dias):
        self.dias_no_laborables = json.dumps(dias)
    
    def get_horario_almuerzo(self):
        return json.loads(self.horario_almuerzo)
    
    def set_horario_almuerzo(self, horario):
        self.horario_almuerzo = json.dumps(horario)
    
    def es_dia_laborable(self, fecha):
        """Verifica si una fecha es laborable"""
        # Verificar si es día no laborable
        if fecha.strftime('%Y-%m-%d') in self.get_dias_no_laborables():
            return False
        
        # Verificar si es día de la semana laborable
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        dia_nombre = dias_semana[fecha.weekday()]
        horas_laborales = self.get_horas_laborales()
        
        return dia_nombre in horas_laborales
    
    def es_hora_laborable(self, fecha_hora):
        """Verifica si una hora específica es laborable"""
        if not self.es_dia_laborable(fecha_hora.date()):
            return False
        
        hora = fecha_hora.time()
        horas_laborales = self.get_horas_laborales()
        dia_nombre = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo'][fecha_hora.weekday()]
        
        # Obtener bloques horarios del día
        bloques = horas_laborales.get(dia_nombre, [])
        
        # Verificar si la hora está dentro de algún bloque
        for bloque in bloques:
            inicio, fin = bloque.split('-')
            hora_inicio = datetime.strptime(inicio, '%H:%M').time()
            hora_fin = datetime.strptime(fin, '%H:%M').time()
            
            if hora_inicio <= hora < hora_fin:
                # Verificar si no es hora de almuerzo
                almuerzo = self.get_horario_almuerzo()
                almuerzo_inicio = datetime.strptime(almuerzo['inicio'], '%H:%M').time()
                almuerzo_fin = datetime.strptime(almuerzo['fin'], '%H:%M').time()
                
                # Si es hora de almuerzo, no es laborable
                if almuerzo_inicio <= hora < almuerzo_fin:
                    return False
                return True
        
        return False
    
    def obtener_horarios_disponibles(self, fecha, duracion_minutos=None):
        """Obtiene los horarios disponibles para una fecha específica"""
        if duracion_minutos is None:
            duracion_minutos = self.duracion_turno
        
        if not self.es_dia_laborable(fecha):
            return []
        
        # Obtener bloques horarios del día
        dias_semana = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        dia_nombre = dias_semana[fecha.weekday()]
        bloques = self.get_horas_laborales().get(dia_nombre, [])
        
        horarios_disponibles = []
        
        for bloque in bloques:
            inicio, fin = bloque.split('-')
            hora_inicio = datetime.strptime(inicio, '%H:%M')
            hora_fin = datetime.strptime(fin, '%H:%M')
            
            # Obtener horario de almuerzo
            almuerzo = self.get_horario_almuerzo()
            almuerzo_inicio = datetime.strptime(almuerzo['inicio'], '%H:%M')
            almuerzo_fin = datetime.strptime(almuerzo['fin'], '%H:%M')
            
            # Generar intervalos
            hora_actual = hora_inicio
            while hora_actual + timedelta(minutes=duracion_minutos) <= hora_fin:
                hora_turno = hora_actual.time()
                hora_fin_turno = (hora_actual + timedelta(minutes=duracion_minutos)).time()
                
                # Verificar que no cruce con almuerzo
                if not (hora_actual < almuerzo_fin and (hora_actual + timedelta(minutes=duracion_minutos)) > almuerzo_inicio):
                    # Verificar si el horario ya está ocupado
                    turno_existente = Turno.query.filter(
                        Turno.fecha_turno == datetime.combine(fecha, hora_turno),
                        Turno.estado != 'cancelado'
                    ).first()
                    
                    if not turno_existente:
                        horarios_disponibles.append(hora_turno.strftime('%H:%M'))
                
                hora_actual += timedelta(minutes=duracion_minutos)
        
        return horarios_disponibles

class Turno(db.Model):
    __tablename__ = 'turnos'
    
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    nombre_cliente = db.Column(db.String(100), nullable=False)
    tipo_servicio = db.Column(db.String(50), nullable=False)
    
    # Fecha y hora del turno
    fecha_turno = db.Column(db.DateTime, nullable=False)  # Fecha y hora específica del turno
    
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, atendido, cancelado, no_asistio
    prioridad = db.Column(db.Integer, default=0)  # 0=normal, 1=prioritario
    
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_atencion = db.Column(db.DateTime, nullable=True)
    tiempo_espera = db.Column(db.Integer, nullable=True)
    
    # Relaciones con usuarios
    usuario_creacion_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    usuario_atencion_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=True)
    
    def calcular_tiempo_espera(self):
        if self.fecha_atencion:
            delta = self.fecha_atencion - self.fecha_creacion
            self.tiempo_espera = int(delta.total_seconds() / 60)
        return self.tiempo_espera
    
    def __repr__(self):
        return f'<Turno {self.numero} - {self.fecha_turno}>'

class LogActividad(db.Model):
    __tablename__ = 'logs_actividad'
    
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    accion = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    
    usuario = db.relationship('Usuario', backref='logs')