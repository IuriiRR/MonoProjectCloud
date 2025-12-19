.PHONY: run test

run:
	docker compose up --build

test:
	python -m pytest -q


