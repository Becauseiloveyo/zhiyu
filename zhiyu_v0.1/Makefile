.PHONY: test compile up down
compile:
	PYTHONPATH=src python -m py_compile $$(find src tests migrations -name '*.py' -print)
test:
	PYTHONPATH=src pytest -q
up:
	docker compose up --build
down:
	docker compose down
