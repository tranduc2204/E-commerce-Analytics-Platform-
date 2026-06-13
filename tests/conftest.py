"""Fixtures dùng chung cho test."""

import pandas as pd
import pytest

from utils.config import Settings


@pytest.fixture
def settings():
    """Settings giả, không chạm hạ tầng thật."""
    return Settings(
        minio_endpoint="http://localhost:9000",
        minio_access_key="test",
        minio_secret_key="test",
        lake_bucket="test-lake",
        trino_host="localhost",
        trino_port=8080,
        trino_user="test",
        data_dir="/tmp/olist-test",
    )


@pytest.fixture
def sample_olist():
    """Bộ dữ liệu Olist tí hon, mọi cột string như CSV gốc.

    Chứa cố tình các ca biên:
    - 2 đơn ngày 2017-05-15, 1 đơn ngày 2017-05-16
    - 1 đơn order_purchase_timestamp rỗng (phải bị loại khỏi mọi ngày)
    """
    orders = pd.DataFrame(
        [
            ["o1", "c1", "delivered", "2017-05-15 10:00:00"],
            ["o2", "c2", "canceled", "2017-05-15 18:30:00"],
            ["o3", "c3", "delivered", "2017-05-16 09:00:00"],
            ["o4", "c4", "delivered", ""],  # thiếu timestamp
        ],
        columns=["order_id", "customer_id", "order_status", "order_purchase_timestamp"],
    )
    order_items = pd.DataFrame(
        [
            ["o1", "1", "p1", "s1", "100.00", "10.00"],
            ["o2", "1", "p2", "s1", "50.00", "5.00"],
            ["o3", "1", "p1", "s2", "30.00", "3.00"],
            ["o4", "1", "p1", "s1", "20.00", "2.00"],
        ],
        columns=["order_id", "order_item_id", "product_id", "seller_id", "price", "freight_value"],
    )
    order_payments = pd.DataFrame(
        [
            ["o1", "1", "credit_card", "1", "110.00"],
            ["o2", "1", "boleto", "1", "55.00"],
            ["o3", "1", "voucher", "1", "33.00"],
        ],
        columns=["order_id", "payment_sequential", "payment_type",
                 "payment_installments", "payment_value"],
    )
    order_reviews = pd.DataFrame(
        [["r1", "o1", "5", "2017-05-20"]],
        columns=["review_id", "order_id", "review_score", "review_creation_date"],
    )
    customers = pd.DataFrame(
        [
            ["c1", "u1", "01000", "sao paulo", "SP"],
            ["c2", "u2", "02000", "rio", "RJ"],
            ["c3", "u3", "03000", "belo horizonte", "MG"],
            ["c4", "u4", "04000", "curitiba", "PR"],
        ],
        columns=["customer_id", "customer_unique_id", "customer_zip_code_prefix",
                 "customer_city", "customer_state"],
    )
    return {
        "orders": orders,
        "order_items": order_items,
        "order_payments": order_payments,
        "order_reviews": order_reviews,
        "customers": customers,
    }
