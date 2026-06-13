-- Câu hỏi nghiệp vụ: GMV theo tháng, lũy kế (running total), tăng trưởng MoM.
{{ config(materialized='table') }}

with monthly as (
    select
        date_format(order_purchase_timestamp, '%Y-%m') as year_month,
        sum(gmv)        as gmv,
        count(*)        as order_count,
        count(*) filter (where order_status = 'canceled') as canceled_orders,
        count(*) filter (where is_late_delivery)          as late_orders
    from {{ ref('fct_orders') }}
    group by 1
)

select
    year_month,
    gmv,
    order_count,
    canceled_orders,
    late_orders,
    -- tỷ lệ huỷ / giao trễ
    round(1.0 * canceled_orders / nullif(order_count, 0), 4) as cancel_rate,
    round(1.0 * late_orders / nullif(order_count, 0), 4)     as late_rate,
    -- GMV lũy kế
    sum(gmv) over (order by year_month
                   rows between unbounded preceding and current row) as gmv_cumulative,
    -- tăng trưởng MoM
    lag(gmv) over (order by year_month) as gmv_prev_month,
    round(
        (gmv - lag(gmv) over (order by year_month))
        / nullif(lag(gmv) over (order by year_month), 0), 4
    ) as gmv_mom_growth
from monthly
order by year_month
