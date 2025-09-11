# Servidor HTTP Minimal com Caching e Medição de Desempenho

Este é um projeto universitário que implementa um servidor HTTP simples em Python, utilizando apenas bibliotecas padrão para o núcleo do servidor. O objetivo é demonstrar de forma prática os conceitos das camadas de aplicação (protocolo HTTP) e Transporte (sockets TCP).

O Servidor é capaz de servir arquivos estáticos, implementar uma estratégia de cache em memória e registrar métricas de desempenho para análise posterior.

## 🎯 Propósito

* **Demonstrar conceitos de Redes:** Entender na prática como funciona a comunicação cliente-servidor, o parsing de requisições HTTP e a montagem de respostas.
* **Implementar Caching:** Avaliar o impacto de uma estratégia de cache em memória no tempo de resposta e na carga do servidor.
* **Análise de Desemepenho:** Coletar e visualizar métricas para comparar o desempenho do servidor com e sem cache, sob diferentes cargas de trabalho.

## ⚙️ Pré-requisitos

### Obrigatório
- Python 3.10 ou superior

### Opcionais
- **Docker** (para execução em container)
- **make** (para usar os atalhos do Makefile)

## 🚀 Execução

### 1. Preparação do ambiente (execução local, sem Docker)

Clone o repositório e crie um ambiente virtual Python:

```bash
git clone https://github.com/johancarloss/Projeto-Final-Redes.git
cd Projeto-Final-Redes

python3 -m venv venv
# No Linux/macOS
source venv/bin/activate
# No Windows PowerShell
venv\Scripts\activat

pip install -r requirements.txt
```

### 2. Executando o Servidor Localmente

Para iniciar o servidor HTTP, use o script `run.sh`:

```bash
chmod +x run.sh
./run.sh
```

O servidor estará rodando em https://localhost:8080
Você pode acessar pelo navegador ou via curl:

# Acessar o index
curl https://localhost:8080/

# Acessar a imagem
curl https://localhost:8080/image1.jpg -o downloaded_image.jpg

### 3. Executando com Docker

Você pode rodar o servidor em um container Docker:

```bash
docker build -t http-server
docker run -p 8080:8080 --name my-http-server http-server
```

### 4. Testes de Carga (em desenvolvimento)

Futuramente será possível simular múltiplos acessos com:

```bash
python scripts/load_test.py
```

### 5. Geração de Gráficos (em desenvolvimento)

Após os testes de carga, será possível gerar gráficos com:

```bash
python scripts/plot_results.py
```