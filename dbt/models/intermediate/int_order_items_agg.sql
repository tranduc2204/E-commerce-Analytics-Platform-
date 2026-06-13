-- Gộp item về grain 1 dòng = 1 đơn để gắn vào fct_orders.
with items as (
    select * from {{ ref('stg_order_items') }}
)

select
    order_id,
    count(*)            as item_count,
    count(distinct product_id) as distinct_product_count,
    count(distinct seller_id)  as distinct_seller_count,
    sum(price)          as total_item_price,
    sum(freight_value)  as total_freight_value,
    sum(price) + sum(freight_value) as total_order_value
from items
group by order_id
