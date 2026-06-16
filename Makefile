.PHONY: setup test lint ping eval serve demo fmt clean

VENV ?= .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

setup:                ## create venv + install pinned deps
	python3 -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r requirements.txt
	$(PIP) install -e .

test:                 ## run unit tests
	$(PY) -m pytest

lint:                 ## ruff lint
	$(VENV)/bin/ruff check src tests eval

fmt:                  ## ruff autofix + format
	$(VENV)/bin/ruff check --fix src tests eval
	$(VENV)/bin/ruff format src tests eval

ping:                 ## smoke-test the configured DeepSeek model (real call)
	$(PY) -m retailcare.config --ping

eval:                 ## run the eval closed loop (M3+)
	$(PY) -m eval.runner

serve:                ## run FastAPI service (M1+)
	$(VENV)/bin/uvicorn retailcare.api.app:app --reload --app-dir src

demo:                 ## end-to-end demo (M4)
	$(PY) -m retailcare.demo

clean:
	rm -rf $(VENV) .pytest_cache .ruff_cache **/__pycache__ .chroma *.db
