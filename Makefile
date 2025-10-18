SHELL := /bin/bash

.PHONY: build-dev run-dev stop-dev restart-dev logs-dev

build-dev:
	cd compose && docker compose build api

run-api-dev:
	cd compose && docker compose up api db minio -d

stop-api-dev:
	cd compose && docker compose down

restart-api-dev:
	cd compose && docker compose restart api

logs-api-dev:
	cd compose && docker compose logs -f api
