SHELL := /bin/bash

DC := docker compose
DB_SERVICE := postgres
DB_USER := notification_user
DB_NAME := booking
MIGRATIONS_DIR := database/migrations

.PHONY: help up down ps logs db-shell migrate migrate-force generator-run generator-stop generator-logs

help:
	@echo "Available targets:"
	@echo "  make up            - Start all services (including generator)"
	@echo "  make down          - Stop all services (including generator)"
	@echo "  make ps            - Show services status"
	@echo "  make logs          - Follow docker compose logs"
	@echo "  make db-shell      - Open psql shell in postgres container"
	@echo "  make migrate       - Apply new SQL migrations once (tracked in schema_migrations)"
	@echo "  make migrate-force - Reapply all SQL migrations without tracking"
	@echo "  make generator-run - Run Kafka message generator in background (dev/test)"
	@echo "  make generator-stop - Stop Kafka message generator"
	@echo "  make generator-logs - Follow Kafka message generator logs"

up:
	-$(DC) --profile generator rm -f -s generator >/dev/null 2>&1 || true
	$(DC) up -d --remove-orphans

down:
	$(DC) --profile generator down --remove-orphans

ps:
	$(DC) ps

logs:
	$(DC) logs -f

db-shell:
	$(DC) exec -it $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME)

migrate:
	@set -e; \
	$(DC) exec -T $(DB_SERVICE) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME) \
		-c "CREATE TABLE IF NOT EXISTS schema_migrations (version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());"; \
	for file in $$(ls $(MIGRATIONS_DIR)/*.sql | sort); do \
		version=$$(basename "$$file"); \
		applied=$$($(DC) exec -T $(DB_SERVICE) psql -U $(DB_USER) -d $(DB_NAME) -tAc "SELECT 1 FROM schema_migrations WHERE version='$$version'"); \
		if [[ "$$applied" == "1" ]]; then \
			echo "Skipping $$version (already applied)"; \
		else \
			echo "Applying $$version"; \
			cat "$$file" | $(DC) exec -T $(DB_SERVICE) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME); \
			$(DC) exec -T $(DB_SERVICE) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME) \
				-c "INSERT INTO schema_migrations(version) VALUES ('$$version')"; \
		fi; \
	done

migrate-force:
	@set -e; \
	for file in $$(ls $(MIGRATIONS_DIR)/*.sql | sort); do \
		echo "Applying $$file"; \
		cat "$$file" | $(DC) exec -T $(DB_SERVICE) psql -v ON_ERROR_STOP=1 -U $(DB_USER) -d $(DB_NAME); \
	done

generator-run:
	$(DC) up -d kafka
	$(DC) --profile generator up -d generator

generator-stop:
	$(DC) --profile generator stop generator

generator-logs:
	$(DC) --profile generator logs -f generator
