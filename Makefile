.venv: Pipfile
	PIPENV_VENV_IN_PROJECT="enabled" pipenv install
	touch .venv

test: .venv
	pipenv run coverage run -m unittest tests

lint: .venv
	pipenv run pylint pywpas

ci: lint
	pipenv run coverage run -m unittest tests

install:
	python setup.py install
