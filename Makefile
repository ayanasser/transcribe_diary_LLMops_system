.PHONY: help setup build start stop restart logs clean test integration-test lint format build-fast build-optimized build-dev build-performance

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

# Development helpers
dev-api:
	@echo "Starting API services only..."
	docker-compose up -d redis postgres ingestion-api job-status-api

dev-workers:
	@echo "Starting worker services..."
	docker-compose up -d transcription-worker llm-worker

# Submit a test job
test-job:
	@echo "Submitting a test job..."
	@curl -X POST http://localhost:8000/jobs \
		-H "Content-Type: application/json" \
		-d '{"audio_url": "https://www2.cs.uic.edu/~i101/SoundFiles/BabyElephantWalk60.wav", "priority": "medium"}' \
		| jq '.'

# Check job status (requires JOB_ID environment variable)
check-job:
	@if [ -z "$(JOB_ID)" ]; then \
		echo "Please provide JOB_ID: make check-job JOB_ID=your-job-id"; \
	else \
		curl -s http://localhost:8001/jobs/$(JOB_ID) | jq '.'; \
	fi

# Monitor metrics
metrics:
	@echo "Opening monitoring dashboards..."
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000"

# Production deployment
deploy-prod:
	@echo "Deploying to production..."
	@export BUILD_TARGET=production && docker-compose --profile production up -d

# Backup data
backup:
	@echo "Creating backup..."
	@mkdir -p backups/$(shell date +%Y%m%d_%H%M%S)
	@docker-compose exec postgres pg_dump -U user transcription_db > backups/$(shell date +%Y%m%d_%H%M%S)/database.sql
	@docker run --rm -v transcription_shared_storage:/data -v $(PWD)/backups/$(shell date +%Y%m%d_%H%M%S):/backup busybox tar czf /backup/storage.tar.gz -C /data .
	@echo "Backup created in backups/$(shell date +%Y%m%d_%H%M%S)/"
