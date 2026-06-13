with source as (
    select * from {{ source('olist', 'order_reviews') }}
)

select
    review_id,
    order_id,
    cast(review_score as integer) as review_score,
    nullif(review_comment_title, '')   as review_comment_title,
    nullif(review_comment_message, '') as review_comment_message,
    cast(nullif(review_creation_date, '') as timestamp)    as review_creation_date,
    cast(nullif(review_answer_timestamp, '') as timestamp) as review_answer_timestamp
from source
