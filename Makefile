.PHONY: test
test: venv
	venv/bin/python tests.py

.PHONY: lint
lint: venv
	venv/bin/flake8 mobi

venv:
	virtualenv -p python venv
	venv/bin/pip install flake8

