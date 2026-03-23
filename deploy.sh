#!/bin/bash
# Script de despliegue automático

echo "Instalando Sistema de Turnos..."

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar archivo de configuración
if [ ! -f .env ]; then
    cp .env.example .env
    echo "Crea el archivo .env con tus credenciales de MySQL"
fi

echo "Instalación completada!"
echo "Configura el archivo .env y luego ejecuta: python3 app.py"