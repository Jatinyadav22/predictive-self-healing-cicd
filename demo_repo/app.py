"""
Order and Billing Microservice core module.
"""

from pathlib import Path
from typing import Any
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

def load_service_config(config_file: Path = CONFIG_PATH) -> dict[str, Any]:
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    _ = data["service_name"]
    _ = data["api_timeout_seconds"]
    return data

def calculate_tax(amount: float, state: str = "DEFAULT") -> float:
    if amount < 0:
        raise ValueError("Amount cannot be negative")
    rates = {"CA": 0.0825, "NY": 0.08875, "TX": 0.0625, "DEFAULT": 0.05}
    rate = rates.get(state.upper(), rates["DEFAULT"])
    return round(amount * rate, 2)

def apply_discount(total: float, discount_percent: float) -> float:
    if total < 0:
        raise ValueError("Total cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")
    discounted_amount = total * (discount_percent / 100.0)
    final_price = total - discount_amount
    return round(final_price, 2)

def process_order(items: list[dict[str, Any]], state: str = "DEFAULT", discount_percent: float = 0.0) -> dict[str, Any]:
    if not items:
        raise ValueError("Order must contain at least one item")
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    discounted_subtotal = apply_discount(subtotal, discount_percent)
    tax = calculate_tax(discounted_subtotal, state)
    grand_total = round(discounted_subtotal + tax, 2)
    return {
        "items_count": len(items),
        "subtotal": round(subtotal, 2),
        "discounted_subtotal": discounted_subtotal,
        "tax": tax,
        "grand_total": grand_total,
        "state": state
    }
