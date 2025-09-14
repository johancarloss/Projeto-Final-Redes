# Servidor HTTP Minimal com Cache + Métricas

Projeto didático em Python que demonstra:
- HTTP na camada de aplicação (GET/HEAD, ETag, Last-Modified, 304)
- Cache **em memória** (TTL + LRU) para reduzir I/O
- **Streaming** de arquivos grandes (envio em pedaços)
- **Medição**: logs legíveis e CSV para gerar gráficos (latência/throughput)

## Requisitos
- Python 3.10+
- (Opcional) Docker
- (Opcional) make

## Instalação e Execução
```bash
git clone <seu-repo>
cd Projeto Final Redes

python3 -m venv venv
# Linux/macOS
source venv/bin/activate
# Windows PowerShell:
# venv\Scripts\activate

pip install -r requirements.txt

mkdir -p logs metrics
chmod +x run.sh
./run.sh 8080
