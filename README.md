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
- **Docker** (opcional, para execução em container)
- **make** (opcional, para usar os atalhos do Makefile)

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