import json
import urllib.request

buggy_code = '''"""
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
    discount_amount = total * (discount_percent / 100.0)
    final_price = total - discount_amount - 5.0  # Defect introduced in commit
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
'''

payload = {
    "commit_sha": "b93c8a11",
    "commit_message": "feat(billing): modify discount formula",
    "branch": "main",
    "author": "Jatinyadav22",
    "repository": "Jatinyadav22/predictive-self-healing-cicd",
    "run_id": "8877665544",
    "run_url": "https://github.com/Jatinyadav22/predictive-self-healing-cicd/actions/runs/8877665544",
    "failure_logs": "FAILED demo_repo/tests/test_app.py::test_apply_discount_standard - assert 85.0 == 90.0",
    "demo_app_content": buggy_code,
    "lines_added": 12,
    "lines_deleted": 3,
    "files_changed": 1
}

req = urllib.request.Request(
    "http://localhost:8000/api/webhooks/github",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

print("Sending webhook request to AutoHeal platform...")
with urllib.request.urlopen(req, timeout=180) as resp:
    res_data = resp.read().decode("utf-8")
    result = json.loads(res_data)
    print("=== AutoHeal Webhook Execution Result ===")
    print("Status:", result.get("status"))
    print("Run ID:", result.get("run_id"))
    print("RCA Summary:", result.get("rca_summary"))
    print("Risk Score:", result.get("risk_score"), "%")
    print("Unified Diff:\n", result.get("unified_diff"))
