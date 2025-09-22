#!/bin/bash

# Define a porta ou usa 8080 como padrão
PORT=${1:-8080}

# Função para ativar venv de forma portátil
activate_venv() {
  if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate    # Linux/macOS
  elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows
  else
    echo "Erro: ambiente virtual não encontrado!"
    exit 1
  fi
}

# Cria o venv se não existir
if [ ! -d "venv" ]; then
  echo "Criando ambiente virtual..."
  python -m venv venv
  echo "Ativando ambiente e instalando dependências..."
  activate_venv
  pip install -r requirements.txt
else
  activate_venv
fi

echo "Iniciando servidor HTTP na porta $PORT..."
python -m app.server --port $PORT