# Tasmia: the daily commands in one place.
# Run `make` alone to see the list.

TASMIA_VENV ?= /tmp/opencode/warsh-venv

.PHONY: help test web-test web-golden web-run ai-setup ai-run

help: ## list the targets
	@grep -E '^[a-z-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-9s %s\n", $$1, $$2}'

test: ## run the Python core tests (no torch needed)
	cd core && python3 -m unittest discover tests -q

web-test: ## go build + vet + test for the web backend
	cd web/backend && go build ./... && go vet ./... && go test ./...

web-golden: ## regenerate the Go text parity golden from core
	PYTHONPATH=core python3 tools/build_text_golden.py

web-run: ## start the web backend on :8080
	cd web/backend && go run ./cmd

ai-setup: ## create the torch venv + install the service deps
	bash tools/setup_venv.sh
	$(TASMIA_VENV)/bin/python -m pip install -q peft soundfile fastapi "uvicorn[standard]" python-multipart
	$(TASMIA_VENV)/bin/python -m pip install -q -e ./core

ai-run: ## start the Python AI service on :7860
	cd ai && $(TASMIA_VENV)/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 7860
