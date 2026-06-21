.PHONY: format lint test
format:        ## auto-format to PEP 8 (isort + black)
	isort --profile black --line-length 88 app scripts tests
	black --line-length 88 app scripts tests
lint:          ## check PEP 8 compliance (fails CI if not clean)
	flake8 app scripts tests
	black --check --line-length 88 app scripts tests
	isort --check-only --profile black --line-length 88 app scripts tests
test:          ## run the test suite
	pytest -q
