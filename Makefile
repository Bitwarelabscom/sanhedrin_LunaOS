# Sanhedrin Makefile
# Common development tasks

.PHONY: help install install-dev lint format test test-cov type-check security clean build docker serve docs

# Default target
help:
	@echo "Sanhedrin Development Commands"
	@echo "=============================="
	@echo ""
	@echo "Setup:"
	@echo "  make install      Install package and core dependencies"
	@echo "  make install-dev  Install with all development dependencies"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint         Run linter (ruff check)"
	@echo "  make format       Format code (ruff format)"
	@echo "  make type-check   Run type checker (mypy)"
	@echo "  make security     Run security scanner (bandit)"
	@echo "  make check        Run all checks (lint, format, type-check)"
	@echo ""
	@echo "Testing:"
	@echo "  make test         Run tests"
	@echo "  make test-cov     Run tests with coverage report"
	@echo "  make test-watch   Run tests in watch mode"
	@echo ""
	@echo "Build:"
	@echo "  make build        Build distribution packages"
	@echo "  make docker       Build Docker image"
	@echo "  make clean        Clean build artifacts"
	@echo ""
	@echo "Run:"
	@echo "  make serve        Start development server"
	@echo "  make serve-prod   Start production server"
	@echo ""

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[all]"
	pre-commit install

# Code Quality
lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check:
	mypy src/sanhedrin

security:
	bandit -r src/sanhedrin -ll
	@echo "Checking dependencies..."
	pip-audit || true

check: lint type-check
	ruff format --check src/ tests/

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=sanhedrin --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

test-watch:
	pytest-watch -- tests/ -v

# Build
build: clean
	python -m build

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

docker:
	docker build -t sanhedrin:latest .

# Run
serve:
	SANHEDRIN_ENV=development python -m sanhedrin.cli.main serve --reload

serve-prod:
	SANHEDRIN_ENV=production python -m sanhedrin.cli.main serve --host 127.0.0.1 --port 8000

# Documentation
docs:
	@echo "Documentation is in README.md"
	@echo "API docs available at http://localhost:8000/docs when server is running"

# Pre-commit
pre-commit:
	pre-commit run --all-files

# Version bump helpers
version-patch:
	@echo "Update version in pyproject.toml manually"
	@grep "version" pyproject.toml | head -1

version-minor:
	@echo "Update version in pyproject.toml manually"
	@grep "version" pyproject.toml | head -1
