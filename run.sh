#!/bin/bash

PORT=${1:-8080}

activate_venv() {
  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
  elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
  else
    echo "Ambiente virtual não encontrado!"
    exit 1
  fi
}

if [ ! -d "venv" ]; then
  echo "Criando venv..."
  python -m venv venv
  activate_venv
  pip install -r requirements.txt
else
  activate_venv
fi

mkdir -p logs metrics
echo "Iniciando servidor na porta $PORT..."
python app/server.py --port $PORT
