.PHONY: build up down logs shell build-db build-memory answer

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f music-agent

shell:
	docker compose exec music-agent /bin/sh

build-db:
	docker compose run --rm music-agent music-agent-build-db

build-memory:
	docker compose run --rm music-agent music-agent-build-memory

answer:
	docker compose run --rm music-agent music-agent-answer "$(q)"
