-- Schema cho raw zone, trỏ vào prefix raw/ trên MinIO
CREATE SCHEMA IF NOT EXISTS raw.olist WITH (location = 's3://lake/raw');
