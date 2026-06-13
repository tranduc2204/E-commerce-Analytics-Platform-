-- Đăng ký các bảng external trỏ vào parquet do extract/replay.py ghi.
-- Mọi cột đều varchar: raw giữ nguyên trạng như CSV, việc cast kiểu là của dbt staging.
-- Cột partition ingestion_date phải đứng cuối danh sách.
-- Sau mỗi lần replay ghi partition mới, chạy:
--   CALL raw.system.sync_partition_metadata('olist', '<table>', 'ADD')
-- (extract/load_raw.py làm việc này tự động)

CREATE TABLE IF NOT EXISTS raw.olist.orders (
    order_id                       varchar,
    customer_id                    varchar,
    order_status                   varchar,
    order_purchase_timestamp       varchar,
    order_approved_at              varchar,
    order_delivered_carrier_date   varchar,
    order_delivered_customer_date  varchar,
    order_estimated_delivery_date  varchar,
    ingestion_date                 varchar
) WITH (
    external_location = 's3://lake/raw/orders',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.order_items (
    order_id             varchar,
    order_item_id        varchar,
    product_id           varchar,
    seller_id            varchar,
    shipping_limit_date  varchar,
    price                varchar,
    freight_value        varchar,
    ingestion_date       varchar
) WITH (
    external_location = 's3://lake/raw/order_items',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.order_payments (
    order_id              varchar,
    payment_sequential    varchar,
    payment_type          varchar,
    payment_installments  varchar,
    payment_value         varchar,
    ingestion_date        varchar
) WITH (
    external_location = 's3://lake/raw/order_payments',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.order_reviews (
    review_id                varchar,
    order_id                 varchar,
    review_score             varchar,
    review_comment_title     varchar,
    review_comment_message   varchar,
    review_creation_date     varchar,
    review_answer_timestamp  varchar,
    ingestion_date           varchar
) WITH (
    external_location = 's3://lake/raw/order_reviews',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.customers (
    customer_id               varchar,
    customer_unique_id        varchar,
    customer_zip_code_prefix  varchar,
    customer_city             varchar,
    customer_state            varchar,
    ingestion_date            varchar
) WITH (
    external_location = 's3://lake/raw/customers',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.products (
    product_id                  varchar,
    product_category_name       varchar,
    product_name_lenght         varchar,
    product_description_lenght  varchar,
    product_photos_qty          varchar,
    product_weight_g            varchar,
    product_length_cm           varchar,
    product_height_cm           varchar,
    product_width_cm            varchar,
    ingestion_date              varchar
) WITH (
    external_location = 's3://lake/raw/products',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.sellers (
    seller_id               varchar,
    seller_zip_code_prefix  varchar,
    seller_city             varchar,
    seller_state            varchar,
    ingestion_date          varchar
) WITH (
    external_location = 's3://lake/raw/sellers',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);

CREATE TABLE IF NOT EXISTS raw.olist.geolocation (
    geolocation_zip_code_prefix  varchar,
    geolocation_lat              varchar,
    geolocation_lng              varchar,
    geolocation_city             varchar,
    geolocation_state            varchar,
    ingestion_date               varchar
) WITH (
    external_location = 's3://lake/raw/geolocation',
    format = 'PARQUET',
    partitioned_by = ARRAY['ingestion_date']
);
