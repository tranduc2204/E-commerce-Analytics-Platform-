with source as (
    select * from {{ source('olist', 'orders') }}
)

select
    order_id,
    customer_id,
    order_status,
    -- raw là varchar; cast về timestamp ở đây, chuỗi rỗng → null
    cast(nullif(order_purchase_timestamp, '') as timestamp)      as order_purchase_timestamp,
    cast(nullif(order_approved_at, '') as timestamp)             as order_approved_at,
    cast(nullif(order_delivered_carrier_date, '') as timestamp)  as order_delivered_carrier_date,
    cast(nullif(order_delivered_customer_date, '') as timestamp) as order_delivered_customer_date,
    cast(nullif(order_estimated_delivery_date, '') as timestamp) as order_estimated_delivery_date
from source
