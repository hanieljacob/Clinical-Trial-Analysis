PYTHON := $(shell command -v python3 2>/dev/null || command -v python 2>/dev/null)

.PHONY: setup pipeline dashboard

setup:
	$(PYTHON) -m pip install -r requirements.txt

pipeline:
	$(PYTHON) pipeline.py

dashboard:
	$(PYTHON) -m streamlit run dashboard/app.py
