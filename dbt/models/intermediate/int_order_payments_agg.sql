-- Gộp payment về grain 1 dòng = 1 đơn (đơn có thể nhiều dòng payment).
with payments as (
    select * from {{ ref('stg_order_payments') }}
)

select
    order_id,
    sum(payment_value)         as total_payment_value,
    max(payment_installments)  as max_installments,
    count(*)                   as payment_count,
    -- phương thức có giá trị lớn nhất coi là phương thức chính
    max_by(payment_type, payment_value) as primary_payment_type
from payments
group by order_id
