"""Unit test logic cắt lát theo ngày — phần nghiệp vụ thật của replay."""

from extract.replay import slice_for_date


def test_slice_picks_only_that_day(sample_olist):
    result = slice_for_date(sample_olist, "2017-05-15")
    assert set(result["orders"]["order_id"]) == {"o1", "o2"}


def test_missing_timestamp_belongs_to_no_day(sample_olist):
    # o4 thiếu timestamp → không xuất hiện ở bất kỳ ngày nào
    for day in ["2017-05-15", "2017-05-16", "1970-01-01"]:
        result = slice_for_date(sample_olist, day)
        assert "o4" not in set(result["orders"]["order_id"])


def test_child_tables_follow_parent_orders(sample_olist):
    result = slice_for_date(sample_olist, "2017-05-15")
    # items/payments chỉ của o1,o2
    assert set(result["order_items"]["order_id"]) <= {"o1", "o2"}
    assert set(result["order_payments"]["order_id"]) <= {"o1", "o2"}
    # customers theo customer_id của đơn trong ngày
    assert set(result["customers"]["customer_id"]) == {"c1", "c2"}


def test_day_with_no_orders_yields_empty(sample_olist):
    result = slice_for_date(sample_olist, "2099-01-01")
    assert result["orders"].empty
    assert result["order_items"].empty


def test_referential_integrity_within_slice(sample_olist):
    result = slice_for_date(sample_olist, "2017-05-16")
    order_ids = set(result["orders"]["order_id"])
    assert set(result["order_items"]["order_id"]) <= order_ids
    assert set(result["order_reviews"]["order_id"]) <= order_ids
