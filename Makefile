
SHELL := /bin/bash

.PHONY: compose-up compose-down compose-logs \
        water-api-setup water-api-env water-api-seed water-api-run \
        client-setup client-run \
        game-setup game-run \
        build-dev run-dev \
        fmt

build-dev:
	docker build -t water-dev -f water_api/Dockerfile .

run-dev:
	docker run -v $(pwd)/water_api:/app -p 8000:8000 water-dev \
	  uvicorn app.main:app --host 0.0.0.0 --port 8000
