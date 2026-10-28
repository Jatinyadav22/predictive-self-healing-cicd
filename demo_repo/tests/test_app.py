"""
Comprehensive pytest test suite for order billing microservice.
"""

import sys
from pathlib import Path
_repo_dir = Path(__file__).resolve().parent.parent
if str(_repo_dir) not in sys.path:
    sys.path.insert(0, str(_repo_dir))

import pytest
from app import calculate_tax, apply_discount, process_order, load_service_config

def test_load_service_config():
    config = load_service_config()
    assert config["service_name"] == "order-billing-service"
    assert config["api_timeout_seconds"] == 30
    assert config["currency"] == "USD"

def test_calculate_tax_ca():
    tax = calculate_tax(100.0, state="CA")
    assert tax == 8.25

def test_calculate_tax_ny():
    tax = calculate_tax(200.0, state="NY")
    assert tax == 17.75

def test_calculate_tax_default():
    tax = calculate_tax(100.0, state="IL")
    assert tax == 5.00

def test_calculate_tax_negative_amount():
    with pytest.raises(ValueError):
        calculate_tax(-50.0)

def test_apply_discount_standard():
    # 10% off 100 should be 90
    discounted = apply_discount(100.0, 10.0)
    assert discounted == 90.0

def test_apply_discount_zero():
    discounted = apply_discount(150.0, 0.0)
    assert discounted == 150.0

def test_apply_discount_full():
    discounted = apply_discount(250.0, 100.0)
    assert discounted == 0.0

def test_apply_discount_invalid_range():
    with pytest.raises(ValueError):
        apply_discount(100.0, 110.0)

def test_process_order_complete_flow():
    items = [
        {"name": "Developer Keyboard", "price": 100.0, "quantity": 1},
        {"name": "USB-C Cable", "price": 20.0, "quantity": 2}
    ]
    # subtotal = 140.0. 10% discount -> 126.0. CA tax (8.25%) -> 10.40. Grand total -> 136.40
    result = process_order(items, state="CA", discount_percent=10.0)
    assert result["items_count"] == 2
    assert result["subtotal"] == 140.0
    assert result["discounted_subtotal"] == 126.0
    assert result["tax"] == 10.40
    assert result["grand_total"] == 136.40

def test_process_order_empty_items():
    with pytest.raises(ValueError):
        process_order([], state="CA")
