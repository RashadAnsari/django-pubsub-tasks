local: dependencies-lock code-format lint

dependencies-lock:
	poetry lock --no-update

code-format:
	ruff format
	ruff check --fix

lint:
	ruff check

create_local_pubsub:
	python manage.py create_local_pubsub

runserver:
	python manage.py runserver

up:
	docker compose up -d

down:
	docker compose down
