PY=python
PORT?=8080

run:
	./run.sh $(PORT)

test:
	$(PY) -m pytest -q

bench:
	$(PY) scripts/load_test.py --url http://127.0.0.1:$(PORT)/index.html --clients 20 --requests-per-client 50
	$(PY) scripts/load_test.py --url http://127.0.0.1:$(PORT)/index.html --clients 20 --requests-per-client 50 --bypass
	@echo "Bench CSV salvo em metrics/bench_results.csv"

plots:
	$(PY) scripts/plot_results.py

docker-build:
	docker build -t http-mini .

docker-run:
	docker run --rm -p 8080:8080 http-mini
