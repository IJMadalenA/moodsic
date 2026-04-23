# Makefile for the project

# Variables
DC := docker compose
UV := uv run
Django_Command := uv run manage.py
CHECK_TAGS := admin caches commands compatibility database files models security staticfiles templates translation urls

.PHONY: pull
pull:
	$(DC) pull

.PHONY: up
up:
	$(DC) up -d

.PHONY: build
build:
	$(DC) up --build -d

.PHONY: down
down:
	$(DC) down

.PHONY: logs
logs:
	$(DC) logs -f

.PHONY: ps
ps:
	$(DC) ps

.PHONY: restart
restart:
	$(DC) restart

.PHONY: shell
shell:
	$(DC) exec django-web bash || $(DC) exec django-web sh

.PHONY: test
test:
	clear
	$(DC) exec django-web uv run pytest
