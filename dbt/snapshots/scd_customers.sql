{% snapshot scd_customers %}
-- SCD2: theo dõi khách (customer_unique_id) đổi địa chỉ qua các đơn.
-- check strategy: phát hiện thay đổi ở zip/city/state thì đóng bản cũ, mở bản mới.
{{
    config(
        target_schema='snapshots',
        unique_key='customer_unique_id',
        strategy='check',
        check_cols=['customer_zip_code_prefix', 'customer_city', 'customer_state'],
    )
}}

-- 1 dòng / customer_unique_id, lấy customer_id mới nhất làm đại diện
with ranked as (
    select
        customer_unique_id,
        customer_id,
        customer_zip_code_prefix,
        customer_city,
        customer_state,
        row_number() over (partition by customer_unique_id
                           order by customer_id) as rn
    from {{ ref('stg_customers') }}
)
select
    customer_unique_id,
    customer_id,
    customer_zip_code_prefix,
    customer_city,
    customer_state
from ranked
where rn = 1

{% endsnapshot %}
