.PHONY: run test audit
run:
	python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 5190

test:
	pytest
	node --check frontend/app.js

audit:
	python scripts/release_audit.py
