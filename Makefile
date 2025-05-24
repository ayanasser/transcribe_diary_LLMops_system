.PHONY: help setup build start stop restart logs clean test integration-test lint format build-fast build-optimized build-dev build-performance runner-setup runner-start runner-stop runner-status runner-update

# Default target
help:
	@echo "Available commands:"
	@echo "  setup          - Set up the development environment"
	@echo "  build          - Build all Docker images"
	@echo "  build-fast     - Build with cache optimization"
	@echo "  build-optimized - Build with advanced optimizations"
	@echo "  build-dev      - Build for development with bind mounts"
	@echo "  build-performance - Test build performance"
	@echo "  start          - Start all services"
	@echo "  start-gpu      - Start services with GPU support"
	@echo "  start-dev      - Start development environment with bind mounts"
	@echo "  stop           - Stop all services"
	@echo "  restart        - Restart all services"
	@echo "  logs           - Show logs from all services"
	@echo "  logs-api       - Show logs from API services"
	@echo "  logs-workers   - Show logs from worker services"
	@echo "  clean          - Clean up Docker resources"
	@echo "  test           - Run unit tests"
	@echo "  integration-test - Run integration tests"
	@echo "  lint           - Run linting"
	@echo "  format         - Format code"
	@echo "  status         - Show service status"
	@echo ""
	@echo "GitHub Runner Commands:"
	@echo "  runner-setup   - Set up GitHub self-hosted runner"
	@echo "  runner-start   - Start runner service"
	@echo "  runner-stop    - Stop runner service"
	@echo "  runner-status  - Check runner status"
	@echo "  runner-update  - Update runner to latest version"

# Setup development environment
setup:
	@echo "Setting up development environment..."
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env file from template. Please edit it with your configuration."; fi
	@mkdir -p storage/{transcriptions,diary_notes,temp}
	@mkdir -p logs
	@docker network create transcription-net 2>/dev/null || true
	@echo "Setup complete!"
	

# Build Docker images
build:
	@echo "Building Docker images..."
	docker-compose build

# Fast build with cache optimization
build-fast:
	@echo "Building with cache optimization..."
	@export DOCKER_BUILDKIT=1 && \
	export COMPOSE_DOCKER_CLI_BUILD=1 && \
	docker-compose -f docker-compose.yml -f docker-compose.fast.yml build

# Advanced optimized build
build-optimized:
	@echo "Building with advanced optimizations..."
	@./scripts/build-optimized.sh

# Development build with bind mounts
build-dev:
	@echo "Building development environment..."
	@export DOCKER_BUILDKIT=1 && \
	export BUILD_TARGET=development && \
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build

# Test build performance
build-performance:
	@echo "Testing build performance..."
	@./scripts/build-performance.sh

# Start all services
start: setup
	@echo "Starting all services..."
	docker-compose up -d
	@echo "Services are starting up..."
	@echo "API Documentation:"
	@echo "  - Ingestion API: http://localhost:8000/docs"
	@echo "  - Job Status API: http://localhost:8001/docs"
	@echo "  - Grafana: http://localhost:3000 (admin/admin)"
	@echo "  - Prometheus: http://localhost:9090"

# Start services with GPU support
start-gpu: setup
	@echo "Starting services with GPU support..."
	docker-compose --profile gpu up -d
	@echo "Services with GPU support are starting up..."

# Start development environment with bind mounts
start-dev: setup build-dev
	@echo "Starting development environment with bind mounts..."
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
	@echo "Development environment is starting up..."
	@echo "Code changes will be reflected immediately (no rebuild needed)"
	@echo "API Documentation:"
	@echo "  - Ingestion API: http://localhost:8000/docs"
	@echo "  - Job Status API: http://localhost:8001/docs"

# Stop all services
stop:
	@echo "Stopping all services..."
	docker-compose down

# Restart all services
restart: stop start

# Show logs from all services
logs:
	docker-compose logs -f

# Show logs from API services
logs-api:
	docker-compose logs -f ingestion-api job-status-api

# Show logs from worker services
logs-workers:
	docker-compose logs -f transcription-worker llm-worker

# Clean up Docker resources
clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	@echo "Cleanup complete!"

# Run tests
test:
	@echo "Running tests..."
	@if [ -d "tests" ]; then \
		python -m pytest tests/unit/ -v; \
	else \
		echo "No tests directory found"; \
	fi

# Run integration tests
integration-test:
	@echo "Running integration tests..."
	@if [ -d "tests/integration" ]; then \
		INGESTION_API_URL=http://localhost:8000 JOB_STATUS_API_URL=http://localhost:8001 \
		python -m pytest tests/integration/ -v --integration; \
	else \
		echo "No integration tests directory found"; \
	fi

# Run linting
lint:
	@echo "Running linting..."
	@find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | xargs flake8 --max-line-length=120 --ignore=E501,W503

# Format code
format:
	@echo "Formatting code..."
	@find . -name "*.py" -not -path "./venv/*" -not -path "./.venv/*" | xargs black --line-length=120

# Show service status
status:
	@echo "Service Status:"
	@docker-compose ps

# Clean up Docker resources and remove cache files
clean-all: clean
	@echo "Cleaning up all development resources..."
	@find . -type d -name __pycache__ -exec rm -rf {} +
	@find . -type d -name .pytest_cache -exec rm -rf {} +
	@find . -type d -name .coverage -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@echo "All cleaned up!"

# GitHub Runner Commands
runner-setup:
	@echo "Setting up GitHub self-hosted runner..."
	@chmod +x scripts/setup-github-runner.sh
	@./scripts/setup-github-runner.sh

runner-start:
	@echo "Starting GitHub runner service..."
	@chmod +x scripts/manage-runner.sh
	@./scripts/manage-runner.sh start

runner-stop:
	@echo "Stopping GitHub runner service..."
	@chmod +x scripts/manage-runner.sh
	@./scripts/manage-runner.sh stop

runner-status:
	@echo "Checking GitHub runner status..."
	@chmod +x scripts/manage-runner.sh
	@./scripts/manage-runner.sh status

runner-update:
	@echo "Updating GitHub runner..."
	@chmod +x scripts/update-runner.sh
	@./scripts/update-runner.sh

runner-install-deps:
	@echo "Installing MLOps dependencies for runner..."
	@sudo chmod +x scripts/install-mlops-deps.sh
	@sudo ./scripts/install-mlops-deps.sh
