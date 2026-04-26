#!/bin/bash
set -e

echo "=================================================="
echo "Inicializando banco de dados..."
echo "=================================================="
cd estoque_app
python init_db.py
DB_STATUS=$?

if [ $DB_STATUS -eq 0 ]; then
    echo "✓ Banco de dados inicializado com sucesso"
else
    echo "✗ Erro ao inicializar banco de dados"
    exit 1
fi

echo ""
echo "=================================================="
echo "Iniciando Gunicorn..."
echo "=================================================="
gunicorn --workers 4 --threads 2 --worker-class gthread --bind 0.0.0.0:$PORT run:app
