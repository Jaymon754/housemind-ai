.PHONY: install dev start build train test rag-eval pdf video remote-check docker clean

install:
	./scripts/bootstrap.sh

dev:
	./scripts/dev.sh

start:
	./scripts/start.sh

build:
	cd frontend && pnpm build

train:
	./scripts/train.sh

test:
	.venv/bin/python -m pytest tests -q

rag-eval:
	.venv/bin/python ml/evaluate_rag.py

pdf:
	./scripts/build_pdf.sh

video:
	.venv/bin/python scripts/build_demo_video.py

remote-check:
	.venv/bin/python scripts/check_remote.py

docker:
	docker compose up --build

clean:
	rm -rf frontend/dist .pytest_cache
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +
