with source as (
    select * from {{ source('olist', 'products') }}
),

translation as (
    select * from {{ ref('product_category_name_translation') }}
)

select
    s.product_id,
    s.product_category_name,
    -- tên category gốc tiếng Bồ; map sang tiếng Anh, thiếu thì giữ nguyên gốc
    coalesce(t.product_category_name_english, s.product_category_name) as product_category_name_english,
    cast(nullif(s.product_weight_g, '') as integer)  as product_weight_g,
    cast(nullif(s.product_length_cm, '') as integer) as product_length_cm,
    cast(nullif(s.product_height_cm, '') as integer) as product_height_cm,
    cast(nullif(s.product_width_cm, '') as integer)  as product_width_cm
from source s
left join translation t
    on s.product_category_name = t.product_category_name
