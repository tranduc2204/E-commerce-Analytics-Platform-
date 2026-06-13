with source as (
    select * from {{ source('olist', 'order_items') }}
)

select
    order_id,
    cast(order_item_id as integer)     as order_item_id,
    product_id,
    seller_id,
    from_iso8601_timestamp(nullif(shipping_limit_date, '')) as shipping_limit_date,
    cast(price as decimal(10, 2))         as price,
    cast(freight_value as decimal(10, 2)) as freight_value
from source
