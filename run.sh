#!/bin/bash
# run.sh

# Activar entorno virtual
source venv/bin/activate

# Obtener IP local
IP=$(hostname -I | awk '{print $1}')

echo "======================================"
echo "Servidor iniciado en:"
echo "Local: http://localhost:5001"
echo "Red: http://$IP:5001"
echo "======================================"
echo "Para acceder desde tu celular:"
echo "1. Conecta tu celular a la misma red WiFi"
echo "2. Abre en el navegador: http://$IP:5001"
echo "======================================"

# Ejecutar la app
python3 app.py