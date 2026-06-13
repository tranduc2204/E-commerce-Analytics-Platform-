-- Dim ngày sinh từ dải ngày của đơn, phục vụ phân tích theo lịch.
{{ config(materialized='table') }}

with bounds as (
    select
        date(min(order_purchase_timestamp)) as start_date,
        date(max(order_purchase_timestamp)) as end_date
    from {{ ref('stg_orders') }}
),

date_spine as (
    select start_date + (s.n * interval '1' day) as date_day
    from bounds
    cross join unnest(sequence(0, date_diff('day',
        (select start_date from bounds),
        (select end_date from bounds)))) as s(n)
)

select
    date_day,
    cast(date_format(date_day, '%Y%m%d') as integer) as date_key,
    year(date_day)         as year,
    month(date_day)        as month,
    day(date_day)          as day,
    day_of_week(date_day)  as day_of_week,
    date_format(date_day, '%Y-%m') as year_month,
    quarter(date_day)      as quarter
from date_spine
