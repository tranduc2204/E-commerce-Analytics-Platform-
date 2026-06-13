-- Current view của khách dựng từ snapshot SCD2: chỉ lấy bản ghi đang hiệu lực.
-- Grain = customer_unique_id (người thật), không phải customer_id (theo từng đơn).
{{ config(materialized='table') }}

with snap as (
    select * from {{ ref('scd_customers') }}
    where dbt_valid_to is null
)

select
    customer_unique_id,
    customer_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state,
    dbt_valid_from as effective_from
from snap
