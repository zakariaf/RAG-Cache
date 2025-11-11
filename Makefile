.PHONY: help install install-dev clean test test-unit test-integration test-coverage \
        format lint type-check quality docker-build docker-up docker-down docker-logs \
        docker-ps docker-clean run dev security-check all

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON := python3.11
PIP := $(PYTHON) -m pip
PYTEST := pytest
BLACK := black
ISORT := isort
FLAKE8 := flake8
MYPY := mypy
DOCKER_COMPOSE := docker-compose
APP_DIR := app
TESTS_DIR := tests

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
NC := \033[0m # No Color

##@ Help

help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make $(BLUE)<target>$(NC)\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Installation

install: ## Install production dependencies
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

install-dev: ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

##@ Code Quality

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code with black...$(NC)"
	$(BLACK) $(APP_DIR)/ $(TESTS_DIR)/
	@echo "$(BLUE)Sorting imports with isort...$(NC)"
	$(ISORT) $(APP_DIR)/ $(TESTS_DIR)/

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	$(BLACK) --check $(APP_DIR)/ $(TESTS_DIR)/
	$(ISORT) --check-only $(APP_DIR)/ $(TESTS_DIR)/

lint: ## Run flake8 linter
	@echo "$(BLUE)Running flake8 linter...$(NC)"
	$(FLAKE8) $(APP_DIR)/ $(TESTS_DIR)/ --max-line-length=88 --extend-ignore=E203,W503

type-check: ## Run mypy type checker
	@echo "$(BLUE)Running mypy type checker...$(NC)"
	$(MYPY) $(APP_DIR)/ --ignore-missing-imports

quality: format-check lint type-check ## Run all code quality checks
	@echo "$(GREEN)✓ All code quality checks passed!$(NC)"

##@ Testing

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	$(PYTEST) $(TESTS_DIR)/ -v

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(PYTEST) $(TESTS_DIR)/unit/ -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(PYTEST) $(TESTS_DIR)/integration/ -v -m integration

test-coverage: ## Run tests with coverage report
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(PYTEST) $(TESTS_DIR)/unit/ -v \
		--cov=$(APP_DIR) \
		--cov-report=xml \
		--cov-report=term-missing \
		--cov-report=html \
		--cov-fail-under=70
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/index.html$(NC)"

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(PYTEST) $(TESTS_DIR)/ -v --looponfail

##@ Security

security-check: ## Run security checks (safety + bandit)
	@echo "$(BLUE)Running security checks...$(NC)"
	@command -v safety >/dev/null 2>&1 || (echo "Installing safety..." && $(PIP) install safety)
	@command -v bandit >/dev/null 2>&1 || (echo "Installing bandit..." && $(PIP) install bandit)
	safety check --json || true
	bandit -r $(APP_DIR)/ -f json || true
	@echo "$(GREEN)✓ Security checks completed$(NC)"

##@ Docker

docker-build: ## Build Docker images
	@echo "$(BLUE)Building Docker images...$(NC)"
	$(DOCKER_COMPOSE) build

docker-up: ## Start all services in background
	@echo "$(BLUE)Starting services...$(NC)"
	$(DOCKER_COMPOSE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo "API: http://localhost:8000"
	@echo "API Docs: http://localhost:8000/docs"
	@echo "Health: http://localhost:8000/health"

docker-down: ## Stop all services
	@echo "$(BLUE)Stopping services...$(NC)"
	$(DOCKER_COMPOSE) down
	@echo "$(GREEN)✓ Services stopped$(NC)"

docker-logs: ## Show logs from all services
	$(DOCKER_COMPOSE) logs -f

docker-ps: ## Show running containers
	$(DOCKER_COMPOSE) ps

docker-clean: ## Stop and remove all containers, networks, and volumes
	@echo "$(RED)Cleaning up Docker resources...$(NC)"
	$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "$(GREEN)✓ Docker cleanup complete$(NC)"

docker-restart: docker-down docker-up ## Restart all services

##@ Development

run: ## Run the FastAPI application locally
	@echo "$(BLUE)Starting FastAPI application...$(NC)"
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev: install-dev docker-up ## Setup development environment
	@echo "$(GREEN)✓ Development environment ready!$(NC)"
	@echo "Run 'make run' to start the application"

##@ Cleanup

clean: ## Clean up Python cache files and build artifacts
	@echo "$(BLUE)Cleaning up...$(NC)"
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.pytest_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.mypy_cache' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name 'htmlcov' -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name 'coverage.xml' -delete
	find . -type f -name '.coverage' -delete
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-all: clean docker-clean ## Deep clean including Docker resources
	@echo "$(GREEN)✓ Deep clean complete$(NC)"

##@ CI/CD

ci-quality: quality ## Run CI quality checks
	@echo "$(GREEN)✓ CI quality checks passed$(NC)"

ci-test: test-coverage ## Run CI test suite
	@echo "$(GREEN)✓ CI tests passed$(NC)"

ci: ci-quality ci-test ## Run full CI pipeline locally
	@echo "$(GREEN)✓ Full CI pipeline passed$(NC)"

##@ Quick Commands

all: clean install-dev quality test ## Run complete workflow (clean, install, quality, test)
	@echo "$(GREEN)✓ Complete workflow finished!$(NC)"

quick: format test-unit ## Quick check (format + unit tests)
	@echo "$(GREEN)✓ Quick check passed!$(NC)"

commit-check: quality test-unit ## Pre-commit checks (run before committing)
	@echo "$(GREEN)✓ Ready to commit!$(NC)"
