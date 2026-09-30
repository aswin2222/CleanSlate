.PHONY: setup dev test lint bench adversarial verify demo docker-up clean

PYTHON := python
PYTEST := pytest

setup:
	$(PYTHON) -m pip install -e backend/ || $(PYTHON) -m pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --reload --port 8000 &
	cd frontend && npm run dev

test:
	$(PYTEST) backend/tests -v --cov=backend/app --cov-report=term-missing

lint:
	ruff check backend/
	mypy backend/app/

bench:
	$(PYTHON) scripts/generate_demo_data.py
	$(PYTHON) backend/app/evaluation/benchmark.py

adversarial:
	$(PYTHON) scripts/generate_adversarial_corpus.py
	$(PYTHON) -m pytest backend/tests/adversarial -v

verify:
	bash scripts/verify_all.sh

demo:
	$(PYTHON) scripts/generate_demo_data.py --run-flow

docker-up:
	docker-compose up --build -d

clean:
	rm -rf .pytest_cache .coverage htmlcov backend/.ruff_cache backend/__pycache__ storage/*.tmp
