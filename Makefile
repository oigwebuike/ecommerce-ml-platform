.PHONY: setup install test run clean docker-up docker-down deploy

# Setup development environment
setup:
	python -m venv venv
	source venv/bin/activate && pip install -r requirements.txt
	cp .env.example .env

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	python -m pytest tests/ -v --tb=short

# Run performance tests
test-performance:
	python -m pytest tests/test_pipeline.py::TestPerformance -v

# Start infrastructure
docker-up:
	docker-compose up -d
	@echo "Waiting for services to start..."
	sleep 10
	@echo "✅ Infrastructure ready!"

# Stop infrastructure  
docker-down:
	docker-compose down

# Run complete demo
run: docker-up
	python run_demo.py

# Run individual components
run-generator:
	python src/1_data_generator.py

run-stream:
	python src/2_stream_processor.py

run-batch:
	python src/3_batch_processor.py

run-api:
	python src/4_ml_inference_api.py

# Clean up
clean:
	docker-compose down
	rm -rf __pycache__ .pytest_cache
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete

# Deploy to AWS
deploy:
	cd infrastructure && terraform init && terraform apply

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Lint code
lint:
	flake8 src/ tests/
	mypy src/ tests/

# Build Docker image
docker-build:
	docker build -t ecommerce-ml-platform .

# Show help
help:
	@echo "Available commands:"
	@echo "  setup           - Setup development environment"
	@echo "  install         - Install dependencies"
	@echo "  test            - Run all tests"
	@echo "  test-performance - Run performance tests"
	@echo "  docker-up       - Start infrastructure"
	@echo "  docker-down     - Stop infrastructure"
	@echo "  run             - Run complete demo"
	@echo "  clean           - Clean up resources"
	@echo "  deploy          - Deploy to AWS"
	@echo "  help            - Show this help"
