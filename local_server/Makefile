.PHONY: local-run cloud-run install test server

local-run:
	COMPOSE_PROFILES=local FIRESTORE_EMULATOR_HOST=firebase-emulator:8080 \
	  docker compose up

cloud-run:
	docker compose up

install:
	uv pip install -e ".[test]"

test:
	pytest tests/

server:
	uvicorn local_server.main:app --reload --host 127.0.0.1 --port 8088
