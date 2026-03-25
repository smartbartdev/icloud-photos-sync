PYTHON ?= python3

.PHONY: install-dev test smoke

install-dev:
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTHON) -m pytest -q

smoke:
	@echo "1) ipb init"
	@echo "2) ipb doctor"
	@echo "3) ipb sync --dry-run --limit 5"
	@echo "4) ipb status"
