.PHONY: run test

run:
	docker compose up --build

test:
	python -m pytest -q
	cd frontend && npm install && npm test -- --run

frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev


