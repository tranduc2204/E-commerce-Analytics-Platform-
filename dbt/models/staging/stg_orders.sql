with source as (
    select * from {{ source('olist', 'orders') }}
)

select
    order_id,
    customer_id,
    order_status,
    -- raw là varchar; cast về timestamp ở đây, chuỗi rỗng → null
    from_iso8601_timestamp(nullif(order_purchase_timestamp, ''))      as order_purchase_timestamp,
    from_iso8601_timestamp(nullif(order_approved_at, ''))             as order_approved_at,
    from_iso8601_timestamp(nullif(order_delivered_carrier_date, ''))  as order_delivered_carrier_date,
    from_iso8601_timestamp(nullif(order_delivered_customer_date, '')) as order_delivered_customer_date,
    from_iso8601_timestamp(nullif(order_estimated_delivery_date, '')) as order_estimated_delivery_date
from source
