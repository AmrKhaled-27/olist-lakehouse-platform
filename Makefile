.PHONY: help venv install up down restart logs-minio logs-spark ingest test lint format clean

SHELL := powershell.exe

help:
	@echo "Available commands for Olist Lakehouse Platform:"
	@echo "  make venv          - Create virtual environment with Python 3.12"
	@echo "  make install       - Install project dependencies"
	@echo "  make up            - Start all Lakehouse Docker containers (MinIO, Spark, etc.)"
	@echo "  make down          - Stop and remove Docker containers"
	@echo "  make restart       - Restart Docker services"
	@echo "  make logs-minio    - Follow MinIO logs"
	@echo "  make logs-spark    - Follow Spark Master logs"
	@echo "  make ingest        - Run Bronze CSV ingestion into MinIO (uses data/raw or starter samples)"
	@echo "  make ingest-kaggle - Download official Olist dataset from Kaggle & ingest into MinIO"
	@echo "  make test          - Run PyTest unit and integration tests"
	@echo "  make lint          - Run Flake8 and Black code checks"
	@echo "  make format        - Format codebase with Black and isort"
	@echo "  make clean         - Clean temporary files and caches"

venv:
	py -3.12 -m venv .venv
	.\.venv\Scripts\python.exe -m pip install --upgrade pip

install:
	.\.venv\Scripts\python.exe -m pip install -r requirements.txt

up:
	docker compose -f docker/docker-compose.yml up -d --build

down:
	docker compose -f docker/docker-compose.yml down

restart:
	docker compose -f docker/docker-compose.yml restart

logs-minio:
	docker compose -f docker/docker-compose.yml logs -f minio

logs-spark:
	docker compose -f docker/docker-compose.yml logs -f spark-master

ingest:
	.\.venv\Scripts\python.exe -m src.ingestion.ingest_bronze --generate-samples

ingest-kaggle:
	.\.venv\Scripts\python.exe -m src.ingestion.ingest_bronze --download-kaggle

transform-silver:
	.\.venv\Scripts\python.exe -m src.spark_jobs.bronze_to_silver --all

dbt-compile:
	docker compose -f docker/docker-compose.yml run --rm dbt compile

dbt-run:
	docker compose -f docker/docker-compose.yml run --rm dbt run

dbt-test:
	docker compose -f docker/docker-compose.yml run --rm dbt test

dashboard:
	.\.venv\Scripts\streamlit.exe run src/dashboard/app.py

dashboard-docker:
	docker compose -f docker/docker-compose.yml up -d --build streamlit

airflow-up:
	docker compose -f docker/docker-compose.yml --profile airflow up -d --build

airflow-down:
	docker compose -f docker/docker-compose.yml --profile airflow stop airflow-webserver airflow-scheduler airflow-postgres

airflow-logs:
	docker compose -f docker/docker-compose.yml logs -f airflow-webserver airflow-scheduler

airflow-trigger:
	docker compose -f docker/docker-compose.yml exec airflow-webserver airflow dags trigger olist_lakehouse_pipeline

test:
	.\.venv\Scripts\pytest.exe -v

lint:
	.\.venv\Scripts\flake8.exe src tests configs
	.\.venv\Scripts\black.exe --check src tests configs

format:
	.\.venv\Scripts\black.exe src tests configs
	.\.venv\Scripts\isort.exe src tests configs

clean:
	Get-ChildItem -Path . -Recurse -Include __pycache__,*.pyc,.pytest_cache | Remove-Item -Recurse -Force
