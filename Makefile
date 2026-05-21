.PHONY: run test

run:
	docker compose up --build

test:
	python -m pytest -q --verbose
	PYTHONPATH=local_server/src:. python -m pytest --verbose -q local_server/tests 
	cd frontend && npm install && npm test -- --run

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

cli:
	FIRESTORE_EMULATOR_HOST=localhost:8080 PYTHONPATH=. python scripts/cli.py

