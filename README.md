# Scalable Audio Transcription & Note Generation System

## Overview

A production-grade, scalable ML inference pipeline that processes audio files, transcribes them using OpenAI Whisper, and generates structured diary-style notes using LLMs. The system is designed to handle 10,000 hours of audio per hour with auto-scaling capabilities.

## Architecture

### System Components

1. **Ingestion API** - FastAPI service for job submission and validation
2. **Message Queue** - Redis for local development, GCP Pub/Sub for cloud
3. **Transcription Service** - Whisper-based audio transcription workers
4. **LLM Service** - OpenAI API integration for note generation
5. **Job Status API** - Track job progress and retrieve results
6. **Storage Layer** - Local filesystem/NFS for development, GCS for cloud
7. **Observability** - Prometheus metrics, structured logging

### Key Features

- **Modular Architecture**: Microservices-based design
- **Scalability**: Horizontal scaling with queue-based processing
- **Multi-stage Docker**: Optimized container builds
- **Cloud-Optional**: Local development with optional GCP deployment
- **Rate Limiting**: Per-user/IP throttling
- **Observability**: Prometheus metrics, OpenTelemetry tracing, structured logging
- **LLM Routing**: Multi-provider support with intelligent fallbacks (OpenAI, Anthropic, etc.)
- **CI/CD Pipeline**: GitHub Actions workflow for testing and deployment

## Quick Start

1. Clone the repository
2. Copy environment variables: `cp .env.example .env`
3. Start the system: `docker-compose up -d`
4. Submit a job: `curl -X POST http://localhost:8000/jobs -H "Content-Type: application/json" -d '{"audio_url": "YOUR_AUDIO_URL"}'`

## Project Structure

```
├── services/
│   ├── ingestion-api/         # Job submission and validation
│   ├── transcription-worker/  # Whisper transcription service
│   ├── llm-worker/           # Note generation service
│   └── job-status-api/       # Job tracking and results
├── shared/
│   ├── models/               # Data models and schemas
│   ├── utils/                # Common utilities
│   └── config/               # Configuration management
├── infrastructure/
│   ├── docker/               # Docker configurations
│   ├── terraform/            # GCP infrastructure (optional)
│   └── monitoring/           # Observability stack
├── tests/                    # Test suites
└── docs/                     # Documentation
```

## Development

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- OpenAI API Key

### Environment Setup

1. Set up environment variables in `.env`
2. Run `make setup` to initialize the development environment
3. Use `make test` to run the test suite

## Production Deployment

### Local/On-Premise
- Use Docker Compose for local development
- Scale workers based on load

### Cloud (GCP)
- Deploy using Terraform modules
- Use GKE for container orchestration
- Leverage GCP Pub/Sub and Cloud Storage

## Monitoring & Observability

- Prometheus metrics on `:9090`
- Grafana dashboards on `:3000`
- Jaeger UI for distributed tracing on `:16686`
- OpenTelemetry collector on `:4317` (gRPC) and `:4318` (HTTP)
- Health checks on `/health` endpoints
- Structured logging with correlation IDs

## API Documentation

- Ingestion API: http://localhost:8000/docs
- Job Status API: http://localhost:8001/docs
- Jaeger UI (Tracing): http://localhost:16686
- Prometheus (Metrics): http://localhost:9090
- Grafana (Dashboards): http://localhost:3000

## Implementation Status

- ✅ Microservices architecture with Redis pub/sub for async processing
- ✅ Multi-stage Docker builds (base→development→production→gpu)
- ✅ LLM router with multi-provider support (OpenAI, Anthropic, Mistral)
- ✅ Observability stack (Prometheus, OpenTelemetry, Jaeger)
- ✅ CI/CD pipeline with GitHub Actions
- ✅ Comprehensive test suite (unit and integration tests)
- ✅ Kubernetes manifests for cloud deployment
- ✅ Terraform infrastructure for GCP

## Self-Hosted GitHub Actions Runners

This project includes a complete setup for self-hosted GitHub Actions runners optimized for ML workflows:

```bash
# Set up a new runner
make runner-setup

# Start/stop the runner service
make runner-start
make runner-stop

# Check runner status
make runner-status

# Update runner
make runner-update

# Install ML dependencies
make runner-install-deps

# Test runner setup (dry run mode)
make runner-test

# Check runner health
make runner-health

# Validate workflow files
make validate-workflows
```

For detailed instructions, see [MLOps Runner Setup Guide](docs/mlops-runner-setup-guide.md) and [Runner Troubleshooting Guide](docs/runner-troubleshooting-guide.md)

This project supports self-hosted GitHub Actions runners, which offer several benefits:

- **Custom Hardware**: Use your own hardware resources for CI/CD
- **GPU Access**: Run ML workloads with GPU acceleration
- **Persistent Cache**: Speed up builds with locally cached dependencies
- **Cost Savings**: No GitHub-hosted minutes consumption

### Quick Setup:

```bash
# Install the self-hosted runner
make runner-setup

# Start the runner service
make runner-start

# Check runner status
make runner-status
```

For detailed instructions, see [MLOps Runner Setup Guide](docs/mlops-runner-setup-guide.md)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

If you encounter any issues or have questions, please:
1. Check the [documentation](docs/)
2. Search existing [issues](https://github.com/ayanasser/transcribe_diary_LLMops_system/issues)
3. Create a new issue if needed

---

**Built with ❤️ for scalable MLOps workflows**
