# ----------------------------
# Variables
# ----------------------------
FRONTEND_DIR=./frontend
BACKEND_DIR=./src/saas_backend

FRONTEND_IMAGE=my-frontend
BACKEND_IMAGE=my-backend

# ----------------------------
# Frontend targets
# ----------------------------
install-frontend:
	cd $(FRONTEND_DIR) && npm install

dev-frontend:
	cd $(FRONTEND_DIR) && npm run dev

build-frontend:
	docker build -t $(FRONTEND_IMAGE) $(FRONTEND_DIR)

start-frontend:
	docker run -p 3000:3000 -e NEXT_PUBLIC_API_URL="http://localhost:8000" $(FRONTEND_IMAGE)

lint-frontend:
	cd $(FRONTEND_DIR) && npm run lint

# ----------------------------
# Backend targets
# ----------------------------
build-backend:
	docker build -t $(BACKEND_IMAGE) $(BACKEND_DIR)

start-backend-dev:
	docker run -p 8000:8000 -e APP_MODE=dev $(BACKEND_IMAGE)

start-backend-prod:
	docker run -p 8000:8000 -e APP_MODE=prod $(BACKEND_IMAGE)

# ----------------------------
# Combined targets
# ----------------------------
build-all: build-backend build-frontend

start-all-dev:
	# Start backend in dev
	make start-backend-dev &
	# Start frontend in dev
	make dev-frontend

start-all-prod:
	# Start backend in prod
	make start-backend-prod &
	# Start frontend in prod
	make start-frontend

# ----------------------------
# Utilities
# ----------------------------
help:
	@echo "Available commands:"
	@echo "  make install-frontend      - Install frontend dependencies"
	@echo "  make dev-frontend          - Start frontend dev server"
	@echo "  make build-frontend        - Build frontend Docker image"
	@echo "  make start-frontend        - Run frontend container"
	@echo "  make lint-frontend         - Lint frontend code"
	@echo "  make build-backend         - Build backend Docker image"
	@echo "  make start-backend-dev     - Run backend container in dev mode"
	@echo "  make start-backend-prod    - Run backend container in prod mode"
	@echo "  make build-all             - Build both frontend and backend images"
	@echo "  make start-all-dev         - Start both services in dev mode"
	@echo "  make start-all-prod        - Start both services in prod mode"

# Kill backend running on port 8000 (optional)
kill-backend-port:
	-@fuser -k 8000/tcp || true
