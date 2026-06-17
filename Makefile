.DEFAULT_GOAL := help
.PHONY: help install dev lint lint-fix format format-check typecheck test test-cov test-quick yamllint pre-commit pre-commit-install clean dist ci all

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─── Setup ────────────────────────────────────────────────────────────────────

install: ## Install package in editable mode
	pip install -e .

dev: ## Install with dev dependencies + pre-commit hooks
	pip install -e ".[dev]"
	pre-commit install

pre-commit-install: ## Install pre-commit hooks only
	pre-commit install

# ─── Linting & Formatting ────────────────────────────────────────────────────

lint: ## Run ruff linter (errors only, no fix)
	ruff check src/ tests/

lint-fix: ## Run ruff linter with auto-fix
	ruff check --fix src/ tests/

format: ## Format Python code with ruff
	ruff format src/ tests/

format-check: ## Check formatting without modifying files
	ruff format --check src/ tests/

typecheck: ## Run mypy type checking
	mypy src/ tests/

yamllint: ## Lint YAML files
	yamllint -d "{extends: relaxed, rules: {line-length: {max: 150}}}" \
		.github/workflows/*.yml registry-entry.yaml

# ─── Testing ─────────────────────────────────────────────────────────────────

test: ## Run all tests with coverage
	pytest tests/ -v

test-cov: ## Run tests with full coverage report (HTML + terminal)
	pytest tests/ -v --cov=ovms_release --cov-report=term-missing --cov-report=html --cov-report=xml

test-quick: ## Run tests without coverage (fast)
	pytest tests/ -v --no-header -q --override-ini="addopts="

# ─── Pre-commit ──────────────────────────────────────────────────────────────

pre-commit: ## Run all pre-commit hooks on all files
	pre-commit run --all-files

# ─── CI (runs the same checks as GitHub Actions) ─────────────────────────────

ci: lint format-check typecheck yamllint test ## Run full CI check suite locally

# ─── Build & Release ─────────────────────────────────────────────────────────

dist: clean ## Build distribution packages
	python -m build

# ─── Cleanup ─────────────────────────────────────────────────────────────────

clean: ## Remove build artifacts and caches
	rm -rf htmlcov/ .coverage .coverage.* coverage.xml
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	rm -rf dist/ build/ src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# ─── Composite ───────────────────────────────────────────────────────────────

all: lint typecheck test ## Run lint + typecheck + test
