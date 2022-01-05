.venv: Pipfile
	PIPENV_VENV_IN_PROJECT="enabled" pipenv install --dev --skip-lock
	touch .venv

.PHONY: deps
deps: .venv

.PHONY: test
test: deps
	pipenv run coverage run -m unittest tests
	pipenv run coverage report -m

.PHONY: lint
lint: deps
	pipenv run pylint pywpas

.PHONY: ci
ci:
	${MAKE} lint
	${MAKE} test

.PHONY: install
install:
	python setup.py install
