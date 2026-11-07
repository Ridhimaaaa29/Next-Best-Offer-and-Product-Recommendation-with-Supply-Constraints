.PHONY: help install test run lint clean

help:
	@echo "Available commands:"
	@echo "  install  - Install dependencies"
	@echo "  test     - Run all unit and integration tests"
	@echo "  run      - Start local FastAPI development server"
	@echo "  clean    - Remove pycache and temporary files"

install:
	pip install -r backend/requirements.txt

test:
	pytest -v

run:
	uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
