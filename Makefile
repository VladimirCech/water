SHELL := /bin/bash

.PHONY: build-dev run-dev stop-dev restart-dev logs-dev

build-dev:
	cd compose && docker compose build api

run-dev:
	cd compose && docker compose up api db

stop-dev:
	cd compose && docker compose down

restart-dev:
	cd compose && docker compose restart api

logs-dev:
	cd compose && docker compose logs -f api
