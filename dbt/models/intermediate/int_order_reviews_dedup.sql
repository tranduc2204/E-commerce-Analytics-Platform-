-- 1 đơn có thể nhiều review; lấy review mới nhất theo creation_date làm đại diện.
with reviews as (
    select * from {{ ref('stg_order_reviews') }}
),

ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by review_creation_date desc
        ) as rn
    from reviews
)

select
    order_id,
    review_id,
    review_score,
    review_creation_date
from ranked
where rn = 1
