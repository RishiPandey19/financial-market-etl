PYTHON ?= python3
VENV_PYTHON := .venv/bin/python
VENV_PIP := .venv/bin/pip
PYTHONPATH := src

.PHONY: setup test test-unit test-integration postgres-up postgres-down run demo airflow-init airflow-up airflow-down clean

setup:
	$(PYTHON) -m venv .venv
	$(VENV_PYTHON) -m pip install --upgrade pip
	$(VENV_PIP) install -r requirements.txt

test:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest

test-unit:
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest tests/unit

test-integration:
	docker compose up -d postgres
	RUN_INTEGRATION_TESTS=true DATABASE_URL=postgresql+psycopg2://etl:etl@localhost:5433/market_data PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m pytest tests/integration

postgres-up:
	docker compose up -d postgres

postgres-down:
	docker compose stop postgres

run: postgres-up
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m market_etl.pipeline --output-size compact

demo: postgres-up
	PYTHONPATH=$(PYTHONPATH) $(VENV_PYTHON) -m market_etl.demo

airflow-init:
	export AIRFLOW_UID=$$(id -u); docker compose up --build airflow-init

airflow-up:
	export AIRFLOW_UID=$$(id -u); docker compose up --build

airflow-down:
	docker compose down

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	rm -rf .pytest_cache
