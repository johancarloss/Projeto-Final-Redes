.PHONY: all run test clean docker-build docker-run

# Variáveis
PYTHON = python3
VENV_DIR = venv

all: run

# Ativa o venv e rodar o servidor
run:
	@echo "Iniciando o servidor em https://localhost:8080..."
	@$(PYTHON) app/server.py

# Roda os testes unitários com pytest
test:
	@echo "Limpando arquivos gerados..."
	@rm -rf `find . -name __pycache__`
	@rm -f results.cv
	@rm -f *.png

# Constrói a imagem Docker
docker-build:
	@echo "Construindo a imagem Docker..."
	@docker build -t http-server .

# Roda o container Docker
docker-run:
	@echo "Executando o container Docker..."
	@docker run -p 8080:8080 --rm --name my-http-server http-server