from datetime import date

from services.cur.parser import parse_cur_rows


def _row(**overrides):
    base = {
        "line_item_usage_account_id": "111111111111",
        "line_item_usage_start_date": "2026-09-01T00:00:00Z",
        "line_item_product_code": "AmazonEC2",
        "line_item_line_item_type": "Usage",
        "line_item_unblended_cost": "1.50",
        "line_item_currency_code": "USD",
    }
    base.update(overrides)
    return base


def test_aggregates_usage_by_account_date_service():
    rows = [_row(line_item_unblended_cost="1.50"), _row(line_item_unblended_cost="2.25")]
    results = parse_cur_rows(rows)
    assert len(results) == 1
    assert results[0].usage_account_id == "111111111111"
    assert results[0].usage_date == date(2026, 9, 1)
    assert results[0].service == "AmazonEC2"
    assert results[0].unblended_cost == 3.75
    assert results[0].amortized_cost == 3.75


def test_excludes_credits_and_refunds_and_tax():
    rows = [
        _row(line_item_unblended_cost="10.00"),
        _row(line_item_line_item_type="Credit", line_item_unblended_cost="-5.00"),
        _row(line_item_line_item_type="Refund", line_item_unblended_cost="-3.00"),
        _row(line_item_line_item_type="Tax", line_item_unblended_cost="1.00"),
    ]
    results = parse_cur_rows(rows)
    assert len(results) == 1
    assert results[0].unblended_cost == 10.00


def test_amortized_cost_includes_ri_and_sp_amortization():
    rows = [
        _row(
            line_item_unblended_cost="0.00",
            reservation_amortized_upfront_fee_for_billing_period="0.50",
            savings_plan_amortized_upfront_commitment_for_billing_period="0.25",
        )
    ]
    results = parse_cur_rows(rows)
    assert results[0].unblended_cost == 0.0
    assert results[0].amortized_cost == 0.75


def test_separates_by_service_and_date():
    rows = [
        _row(line_item_product_code="AmazonEC2", line_item_unblended_cost="1.00"),
        _row(line_item_product_code="AmazonS3", line_item_unblended_cost="2.00"),
        _row(line_item_usage_start_date="2026-09-02T00:00:00Z", line_item_unblended_cost="3.00"),
    ]
    results = parse_cur_rows(rows)
    assert len(results) == 3
    total = sum(r.unblended_cost for r in results)
    assert total == 6.00


def test_separates_by_account():
    rows = [
        _row(line_item_usage_account_id="111111111111", line_item_unblended_cost="1.00"),
        _row(line_item_usage_account_id="222222222222", line_item_unblended_cost="2.00"),
    ]
    results = parse_cur_rows(rows)
    assert {r.usage_account_id for r in results} == {"111111111111", "222222222222"}
