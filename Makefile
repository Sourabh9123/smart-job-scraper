.PHONY: setup install run clean

# Use the python executable from the active environment
PYTHON := python
PIP := pip

setup: install
	@echo "Setup complete. You can now run 'make run'"

install:
	$(PIP) install -r requirements.txt

run:
	$(PYTHON) -m src.main

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
