-- Grain: 1 dòng = 1 item trong đơn (order_id, order_item_id).
-- Bảng số lượng lớn nhất → incremental theo order, partition theo tháng mua.
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key=['order_id', 'order_item_id'],
    properties={
        "format": "'PARQUET'",
        "partitioning": "ARRAY['month(order_purchase_timestamp)']"
    }
) }}

with items as (
    select * from {{ ref('stg_order_items') }}
),

orders as (
    select order_id, customer_id, order_status, order_purchase_timestamp
    from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    where order_purchase_timestamp >= (
        select coalesce(max(order_purchase_timestamp), timestamp '1970-01-01')
               - interval '3' day
        from {{ this }}
    )
    {% endif %}
)

select
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    o.customer_id,
    o.order_status,
    o.order_purchase_timestamp,
    i.price,
    i.freight_value,
    i.price + i.freight_value as item_total_value
from items i
inner join orders o on i.order_id = o.order_id
