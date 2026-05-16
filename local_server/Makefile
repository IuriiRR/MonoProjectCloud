.PHONY: local-run cloud-run

local-run:
	COMPOSE_PROFILES=local FIRESTORE_EMULATOR_HOST=firebase-emulator:8080 \
	  docker compose up

cloud-run:
	docker compose up
