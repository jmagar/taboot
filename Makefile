.PHONY: help start stop restart status logs clean
.PHONY: start-api stop-api restart-api logs-api
.PHONY: start-web stop-web restart-web logs-web
.PHONY: start-rerank stop-rerank restart-rerank logs-rerank
.PHONY: start-worker stop-worker restart-worker logs-worker
.PHONY: start-all stop-all check-deps

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Log directory
LOG_DIR := .logs
PID_DIR := .pids

# Default service ports (services load .env themselves via python-dotenv/Next.js)
API_PORT := 4209
WEB_PORT := 3005
RERANK_PORT := 4208

help: ## Show this help message
	@echo "$(CYAN)Taboot Local Development Makefile$(RESET)"
	@echo ""
	@echo "$(GREEN)Service Management:$(RESET)"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Logs are stored in $(LOG_DIR)/$(RESET)"
	@echo "$(YELLOW)PIDs are stored in $(PID_DIR)/$(RESET)"

check-deps: ## Check if required dependencies are installed
	@echo "$(CYAN)Checking dependencies...$(RESET)"
	@command -v uv >/dev/null 2>&1 || { echo "$(RED)✗ uv not found. Install: curl -LsSf https://astral.sh/uv/install.sh | sh$(RESET)"; exit 1; }
	@command -v pnpm >/dev/null 2>&1 || { echo "$(RED)✗ pnpm not found. Install: npm install -g pnpm$(RESET)"; exit 1; }
	@command -v python3 >/dev/null 2>&1 || { echo "$(RED)✗ python3 not found$(RESET)"; exit 1; }
	@command -v node >/dev/null 2>&1 || { echo "$(RED)✗ node not found$(RESET)"; exit 1; }
	@echo "$(GREEN)✓ All dependencies found$(RESET)"

$(LOG_DIR):
	@mkdir -p $(LOG_DIR)

$(PID_DIR):
	@mkdir -p $(PID_DIR)

# ==========================================
# API Service (FastAPI - Port 4209)
# ==========================================

start-api: $(LOG_DIR) $(PID_DIR) ## Start the FastAPI service
	@if [ -f $(PID_DIR)/api.pid ] && kill -0 $$(cat $(PID_DIR)/api.pid) 2>/dev/null; then \
		echo "$(YELLOW)API service already running (PID: $$(cat $(PID_DIR)/api.pid))$(RESET)"; \
	else \
		echo "$(CYAN)Starting API service on port $(API_PORT)...$(RESET)"; \
		for pid in $$(lsof -ti :$(API_PORT) 2>/dev/null); do kill -9 $$pid 2>/dev/null || true; done; \
		uv run uvicorn apps.api.app:app --host 0.0.0.0 --port $(API_PORT) --reload \
			> $(LOG_DIR)/api.log 2>&1 & echo $$! > $(PID_DIR)/api.pid; \
		sleep 2; \
		if kill -0 $$(cat $(PID_DIR)/api.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ API service started (PID: $$(cat $(PID_DIR)/api.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ API service failed to start. Check $(LOG_DIR)/api.log$(RESET)"; \
			rm -f $(PID_DIR)/api.pid; \
			exit 1; \
		fi \
	fi

stop-api: ## Stop the FastAPI service
	@if [ -f $(PID_DIR)/api.pid ]; then \
		echo "$(CYAN)Stopping API service...$(RESET)"; \
		PID=$$(cat $(PID_DIR)/api.pid); \
		pkill -TERM -P $$PID 2>/dev/null || true; \
		kill -TERM $$PID 2>/dev/null || true; \
		sleep 1; \
		pkill -9 -P $$PID 2>/dev/null || true; \
		kill -9 $$PID 2>/dev/null || true; \
		rm -f $(PID_DIR)/api.pid; \
		echo "$(GREEN)✓ API service stopped$(RESET)"; \
	else \
		echo "$(YELLOW)API service not running$(RESET)"; \
	fi

restart-api: stop-api start-api ## Restart the FastAPI service

logs-api: ## Tail API service logs
	@tail -f $(LOG_DIR)/api.log

# ==========================================
# Web Service (Next.js - Port 4211)
# ==========================================

start-web: $(LOG_DIR) $(PID_DIR) ## Start the Next.js web service
	@if [ -f $(PID_DIR)/web.pid ] && kill -0 $$(cat $(PID_DIR)/web.pid) 2>/dev/null; then \
		echo "$(YELLOW)Web service already running (PID: $$(cat $(PID_DIR)/web.pid))$(RESET)"; \
	else \
        WEB_PORT=$$(grep TABOOT_WEB_PORT .env 2>/dev/null | cut -d'"' -f2 || echo "4211"); \
		echo "$(CYAN)Starting Web service on port $$WEB_PORT...$(RESET)"; \
		for pid in $$(lsof -ti :$$WEB_PORT 2>/dev/null); do kill -9 $$pid 2>/dev/null || true; done; \
		sleep 1; \
		PORT=$$WEB_PORT pnpm --filter @taboot/web dev > $(LOG_DIR)/web.log 2>&1 & echo $$! > $(PID_DIR)/web.pid; \
		sleep 3; \
		if kill -0 $$(cat $(PID_DIR)/web.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Web service started (PID: $$(cat $(PID_DIR)/web.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Web service failed to start. Check $(LOG_DIR)/web.log$(RESET)"; \
			rm -f $(PID_DIR)/web.pid; \
			exit 1; \
		fi \
	fi

stop-web: ## Stop the Next.js web service
	@if [ -f $(PID_DIR)/web.pid ]; then \
		echo "$(CYAN)Stopping Web service...$(RESET)"; \
		PID=$$(cat $(PID_DIR)/web.pid); \
		pkill -TERM -P $$PID 2>/dev/null || true; \
		kill -TERM $$PID 2>/dev/null || true; \
		sleep 1; \
		pkill -9 -P $$PID 2>/dev/null || true; \
		kill -9 $$PID 2>/dev/null || true; \
		rm -f $(PID_DIR)/web.pid; \
		echo "$(GREEN)✓ Web service stopped$(RESET)"; \
	else \
		echo "$(YELLOW)Web service not running$(RESET)"; \
	fi

restart-web: stop-web start-web ## Restart the Next.js web service

logs-web: ## Tail Web service logs
	@tail -f $(LOG_DIR)/web.log

# ==========================================
# Reranker Service (Port 8081)
# ==========================================

start-rerank: $(LOG_DIR) $(PID_DIR) ## Start the reranker service
	@if [ -f $(PID_DIR)/rerank.pid ] && kill -0 $$(cat $(PID_DIR)/rerank.pid) 2>/dev/null; then \
		echo "$(YELLOW)Reranker service already running (PID: $$(cat $(PID_DIR)/rerank.pid))$(RESET)"; \
	else \
		echo "$(CYAN)Starting Reranker service on port $(RERANK_PORT)...$(RESET)"; \
		for pid in $$(lsof -ti :$(RERANK_PORT) 2>/dev/null); do kill -9 $$pid 2>/dev/null || true; done; \
		uv run uvicorn apps.rerank.app:app --host 0.0.0.0 --port $(RERANK_PORT) \
			> $(LOG_DIR)/rerank.log 2>&1 & echo $$! > $(PID_DIR)/rerank.pid; \
		sleep 2; \
		if kill -0 $$(cat $(PID_DIR)/rerank.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Reranker service started (PID: $$(cat $(PID_DIR)/rerank.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Reranker service failed to start. Check $(LOG_DIR)/rerank.log$(RESET)"; \
			rm -f $(PID_DIR)/rerank.pid; \
			exit 1; \
		fi \
	fi

stop-rerank: ## Stop the reranker service
	@if [ -f $(PID_DIR)/rerank.pid ]; then \
		echo "$(CYAN)Stopping Reranker service...$(RESET)"; \
		PID=$$(cat $(PID_DIR)/rerank.pid); \
		pkill -TERM -P $$PID 2>/dev/null || true; \
		kill -TERM $$PID 2>/dev/null || true; \
		sleep 1; \
		pkill -9 -P $$PID 2>/dev/null || true; \
		kill -9 $$PID 2>/dev/null || true; \
		rm -f $(PID_DIR)/rerank.pid; \
		echo "$(GREEN)✓ Reranker service stopped$(RESET)"; \
	else \
		echo "$(YELLOW)Reranker service not running$(RESET)"; \
	fi

restart-rerank: stop-rerank start-rerank ## Restart the reranker service

logs-rerank: ## Tail Reranker service logs
	@tail -f $(LOG_DIR)/rerank.log

# ==========================================
# Worker Service
# ==========================================

start-worker: $(LOG_DIR) $(PID_DIR) ## Start the extraction worker
	@if [ -f $(PID_DIR)/worker.pid ] && kill -0 $$(cat $(PID_DIR)/worker.pid) 2>/dev/null; then \
		echo "$(YELLOW)Worker service already running (PID: $$(cat $(PID_DIR)/worker.pid))$(RESET)"; \
	else \
		echo "$(CYAN)Starting Worker service...$(RESET)"; \
		uv run python -m apps.worker.main > $(LOG_DIR)/worker.log 2>&1 & echo $$! > $(PID_DIR)/worker.pid; \
		sleep 2; \
		if kill -0 $$(cat $(PID_DIR)/worker.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Worker service started (PID: $$(cat $(PID_DIR)/worker.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Worker service failed to start. Check $(LOG_DIR)/worker.log$(RESET)"; \
			rm -f $(PID_DIR)/worker.pid; \
			exit 1; \
		fi \
	fi

stop-worker: ## Stop the extraction worker
	@if [ -f $(PID_DIR)/worker.pid ]; then \
		echo "$(CYAN)Stopping Worker service...$(RESET)"; \
		PID=$$(cat $(PID_DIR)/worker.pid); \
		pkill -TERM -P $$PID 2>/dev/null || true; \
		kill -TERM $$PID 2>/dev/null || true; \
		sleep 1; \
		pkill -9 -P $$PID 2>/dev/null || true; \
		kill -9 $$PID 2>/dev/null || true; \
		rm -f $(PID_DIR)/worker.pid; \
		echo "$(GREEN)✓ Worker service stopped$(RESET)"; \
	else \
		echo "$(YELLOW)Worker service not running$(RESET)"; \
	fi

restart-worker: stop-worker start-worker ## Restart the extraction worker

logs-worker: ## Tail Worker service logs
	@tail -f $(LOG_DIR)/worker.log

# ==========================================
# All Services Management
# ==========================================

start-all: check-deps start-api start-web start-rerank start-worker ## Start all services
	@echo ""
	@echo "$(GREEN)✓ All services started$(RESET)"
	@make status

stop-all: stop-api stop-web stop-rerank stop-worker ## Stop all services
	@echo "$(GREEN)✓ All services stopped$(RESET)"

restart-all: stop-all start-all ## Restart all services

status: ## Show status of all services
	@echo "$(CYAN)Service Status:$(RESET)"
	@echo ""
	@printf "  %-15s " "API:"; \
		if [ -f $(PID_DIR)/api.pid ] && kill -0 $$(cat $(PID_DIR)/api.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Running (PID: $$(cat $(PID_DIR)/api.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Stopped$(RESET)"; \
		fi
	@printf "  %-15s " "Web:"; \
		if [ -f $(PID_DIR)/web.pid ] && kill -0 $$(cat $(PID_DIR)/web.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Running (PID: $$(cat $(PID_DIR)/web.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Stopped$(RESET)"; \
		fi
	@printf "  %-15s " "Reranker:"; \
		if [ -f $(PID_DIR)/rerank.pid ] && kill -0 $$(cat $(PID_DIR)/rerank.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Running (PID: $$(cat $(PID_DIR)/rerank.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Stopped$(RESET)"; \
		fi
	@printf "  %-15s " "Worker:"; \
		if [ -f $(PID_DIR)/worker.pid ] && kill -0 $$(cat $(PID_DIR)/worker.pid) 2>/dev/null; then \
			echo "$(GREEN)✓ Running (PID: $$(cat $(PID_DIR)/worker.pid))$(RESET)"; \
		else \
			echo "$(RED)✗ Stopped$(RESET)"; \
		fi
	@echo ""
	@echo "$(YELLOW)Ports:$(RESET)"
	@WEB_PORT_ACTUAL=$$(grep TABOOT_WEB_PORT .env 2>/dev/null | cut -d'"' -f2 || echo "4211"); \
	echo "  API:      http://localhost:$(API_PORT)"; \
	echo "  Web:      http://localhost:$$WEB_PORT_ACTUAL"; \
	echo "  Reranker: http://localhost:$(RERANK_PORT)"

logs: ## Tail all service logs
	@tail -f $(LOG_DIR)/*.log

clean: stop-all ## Stop all services and clean logs/PIDs
	@echo "$(CYAN)Cleaning logs and PID files...$(RESET)"
	@rm -rf $(LOG_DIR) $(PID_DIR)
	@echo "$(GREEN)✓ Cleaned$(RESET)"

# Individual service management (short aliases)
start: start-all
stop: stop-all
restart: restart-all
