#!/bin/bash

# Define a porta ou usa 8080 como padrão
PORT=${1:-8080}

# Verifica se o ambiente virtual existe, se não, cria e instala as dependências
if [ ! -d "venv" ]; then
  echo "Criando ambiente virtual..."
  python -m venv venv
  echo "Ativando ambiente e instalando dependências..."
  source venv/Scripts/activate
  pip install -r requirements.txt
else
  source venv/bin/activate
fi

echo "Iniciando servidor HTTP na porta $PORT..."
python app/server.py --port $PORT