-- Grain: 1 dòng = 1 đơn. Incremental merge theo order_id, partition theo tháng mua.
{{ config(
    materialized='incremental',
    incremental_strategy='merge',
    unique_key='order_id',
    properties={
        "format": "'PARQUET'",
        "partitioning": "ARRAY['month(order_purchase_timestamp)']"
    }
) }}

with orders as (
    select * from {{ ref('stg_orders') }}
    {% if is_incremental() %}
    -- chỉ xử lý đơn mới hơn mốc đã nạp (lookback 3 ngày phòng đơn đến trễ)
    where order_purchase_timestamp >= (
        select coalesce(max(order_purchase_timestamp), timestamp '1970-01-01')
               - interval '3' day
        from {{ this }}
    )
    {% endif %}
),

items as (
    select * from {{ ref('int_order_items_agg') }}
),

payments as (
    select * from {{ ref('int_order_payments_agg') }}
),

reviews as (
    select * from {{ ref('int_order_reviews_dedup') }}
),

customers as (
    select customer_id, customer_unique_id, customer_state
    from {{ ref('stg_customers') }}
)

select
    o.order_id,
    c.customer_unique_id,
    c.customer_state               as customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    -- GMV chỉ tính đơn không huỷ; đơn canceled/unavailable = 0
    case when o.order_status not in ('canceled', 'unavailable')
         then coalesce(i.total_order_value, 0) else 0 end as gmv,
    coalesce(i.item_count, 0)      as item_count,
    coalesce(i.total_item_price, 0) as total_item_price,
    coalesce(i.total_freight_value, 0) as total_freight_value,
    p.total_payment_value,
    p.max_installments,
    p.primary_payment_type,
    r.review_score,

    -- cờ giao trễ: giao sau ngày dự kiến. null delivered_date → null (chưa biết)
    case
        when o.order_delivered_customer_date is null then null
        when o.order_delivered_customer_date > o.order_estimated_delivery_date then true
        else false
    end as is_late_delivery,
    date_diff('day', o.order_purchase_timestamp, o.order_delivered_customer_date)
        as delivery_days
from orders o
left join items     i on o.order_id = i.order_id
left join payments  p on o.order_id = p.order_id
left join reviews   r on o.order_id = r.order_id
left join customers c on o.customer_id = c.customer_id
