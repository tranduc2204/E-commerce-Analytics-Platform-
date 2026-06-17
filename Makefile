





# Makefile — phím tắt cho stack Olist lakehouse.
# docker compose tự nạp .env; copy .env.example -> .env trước khi chạy.

SHELL := /bin/bash
DATE  ?= 2017-05-15          # ghi đè: make replay DATE=2017-06-01

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Liệt kê các target
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ---------- môi trường Python (host) ----------
.PHONY: install
install:  ## Cài deps dev vào venv hiện hành (pip install -e .[dev,dbt,extract])
	pip install -e ".[dev,dbt,extract]"

# ---------- hạ tầng Docker ----------
.PHONY: up
up:  ## Dựng toàn bộ stack (MinIO, Postgres, Nessie, Trino, Airflow, Metabase)
	docker compose up -d

.PHONY: down
down:  ## Tắt stack (giữ volume)
	docker compose down

.PHONY: clean
clean:  ## Tắt stack + xoá volume (mất sạch dữ liệu lake + catalog Nessie)
	docker compose down -v

.PHONY: ps
ps:  ## Trạng thái service
	docker compose ps

.PHONY: logs
logs:  ## Theo dõi log (make logs SVC=trino)
	docker compose logs -f $(SVC)

# ---------- đăng ký schema raw trong Trino (chạy 1 lần sau khi có dữ liệu) ----------
.PHONY: init-raw
init-raw:  ## Tạo schema + external table raw trong Trino
	docker compose exec trino trino --catalog raw -f /sql/01_init_raw.sql
	docker compose exec trino trino --catalog raw -f /sql/02_raw_tables.sql

# ---------- extract / load ----------
.PHONY: download
download:  ## Tải dataset Olist từ Kaggle về DATA_DIR
	python -m extract.download_olist

.PHONY: bootstrap
bootstrap:  ## Ghi products/sellers/geolocation lên raw zone (1 lần)
	python -m extract.replay --bootstrap

.PHONY: replay
replay:  ## Replay 1 ngày: make replay DATE=2017-05-15
	python -m extract.replay --date $(DATE)

.PHONY: load
load:  ## Sync partition mới vào metastore
	python -m extract.load_raw

# ---------- dbt ----------
.PHONY: dbt-deps
dbt-deps:  ## Tải dbt packages
	cd dbt && dbt deps

.PHONY: dbt-build
dbt-build:  ## seed + run + snapshot + test
	cd dbt && dbt build

.PHONY: dbt-parse
dbt-parse:  ## Validate model/refs/jinja, không cần kết nối DB
	cd dbt && dbt deps && dbt parse

# ---------- tests ----------
.PHONY: test
test:  ## Unit + DAG integrity (không cần hạ tầng)
	pytest tests/unit airflow/tests

.PHONY: test-integration
test-integration:  ## Integration (cần `make up` trước)
	pytest -m integration
