# Estágio 1: Base
FROM python:3.10-slim

# Define o diretório de trabalho
WORKDIR /usr/src/app

# Copia os arquivos de dependências
COPY requirements.txt ./

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação e os arquivos estáticos
COPY ./app ./app
COPY ./www ./www

# Expõe a porta que o servidor irá usar
EXPOSE 8080

# Comando para rodar a aplicação
CMD [ "python", "./app/server.py" ]