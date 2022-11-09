deps:
	pip-compile requirements.in
	pip-compile requirements_dev.in
	pip-sync requirements.txt requirements_dev.txt


tests: deps
	pytest ./tests

prod:
	git pull
	docker-compose up -d --build web
