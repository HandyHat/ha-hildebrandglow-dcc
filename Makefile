help : Makefile
	@echo "Usage: make [command]"
	@echo ""
	@sed -n 's/^##//p' $<

##  install-dev    Install dependencies required for development
install-dev:
	pip install -r requirements-dev.txt

##  format         Run linters on the codebase and attempt to fix any issues found
format:
	isort --recursive custom_components
	black -l 88 -t py38 custom_components
	flake8 custom_components
	mypy custom_components/hildebrandglow/

lint-isort:
	isort --check --recursive custom_components

lint-black:
	black -l 88 -t py38 --check custom_components

lint-flake8:
	flake8 custom_components

lint-mypy:
ifeq ($(CI),true)
	MYPYPATH="${HOME}/homeassistant/core-master" mypy custom_components/hildebrandglow/
else
	mypy custom_components/hildebrandglow/
endif

##  lint           Dry-run linters on the codebase without making any changes
lint: lint-isort lint-black lint-flake8 lint-mypy
