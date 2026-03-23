# Sistema de Gestión de Turnos

Sistema completo para la gestión de turnos con autenticación de usuarios, configuración de horarios laborales y selección de fechas.

## Características

- 🔐 Autenticación de usuarios (admin, operador, usuario)
- 📅 Selección de fecha y hora para turnos
- ⏰ Configuración flexible de horarios laborales
- 🍽️ Horario de almuerzo configurable
- 📊 Dashboard con estadísticas en tiempo real
- 👥 Gestión de usuarios
- 📱 Diseño responsive (funciona en móviles)
- 📝 Logs de actividad
- 🎯 Turnos prioritarios

## Tecnologías Utilizadas

- **Backend**: Python 3.x, Flask
- **Base de Datos**: MySQL
- **Frontend**: HTML5, CSS3, JavaScript
- **Autenticación**: Flask-Login
- **ORM**: Flask-SQLAlchemy

## Requisitos Previos

- Python 3.8 o superior
- MySQL 5.7 o superior
- pip (gestor de paquetes de Python)

## Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/sistema-turnos.git
cd sistema-turnos

### 2. Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

### 3. Instalar dependencias

```bash
pip install -r requirements.txt

### 4. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales de MySQL
nano .env

### 5. Crear base de datos

```bash
mysql -u root -p
CREATE DATABASE sistema_turnos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

### 6. Ejecutar la aplicación

```bash
python app.py
# o usar el script de inicio
chmod +x run.sh
./run.sh

### 7. Acceder a la aplicación

Local: http://localhost:5001

Red: http://tu-ip:5001

Credenciales por defecto
Admin: admin / admin123

Estructura del Proyecto
text
sistema-turnos/
├── app.py                 # Aplicación principal
├── models.py              # Modelos de datos
├── config.py              # Configuración
├── requirements.txt       # Dependencias
├── .env.example          # Ejemplo de variables de entorno
├── run.sh                # Script de inicio
├── templates/            # Plantillas HTML
│   ├── admin/           # Plantillas de administración
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── tomar_turno.html
│   ├── listar_turnos.html
│   ├── mis_turnos.html
│   └── perfil.html
└── static/              # Archivos estáticos
    └── style.css
Uso
Para Usuarios
Registrarse o iniciar sesión

Solicitar turno seleccionando fecha y hora disponible

Ver sus turnos en "Mis Turnos"

Cancelar turnos pendientes

Para Operadores
Atender turnos desde la lista

Ver estadísticas básicas

Para Administradores
Gestionar usuarios (crear, editar, eliminar)

Configurar horarios laborales

Ver estadísticas completas

Establecer turnos prioritarios

Configuración de Horarios
Los administradores pueden configurar:

Días laborables

Horarios de mañana y tarde

Horario de almuerzo

Días no laborables (feriados)

Duración de los turnos