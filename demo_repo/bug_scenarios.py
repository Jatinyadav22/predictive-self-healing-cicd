"""
Fault Injection Scenarios for Demonstrating Live Autonomous Self-Healing and Guardrails.
"""

from pathlib import Path

DEMO_DIR = Path(__file__).resolve().parent
APP_FILE = DEMO_DIR / "app.py"
CONFIG_FILE = DEMO_DIR / "config.yaml"

CLEAN_APP_CODE = '''"""
Order and Billing Microservice core module.
"""

from pathlib import Path
from typing import Any
import yaml

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"

def load_service_config(config_file: Path = CONFIG_PATH) -> dict[str, Any]:
    """Loads YAML configuration for the billing microservice."""
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    # Required keys verification
    _ = data["service_name"]
    _ = data["api_timeout_seconds"]
    return data

def calculate_tax(amount: float, state: str = "DEFAULT") -> float:
    """Calculates tax on an amount given a jurisdiction state code."""
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    rates = {
        "CA": 0.0825,
        "NY": 0.08875,
        "TX": 0.0625,
        "DEFAULT": 0.05
    }
    rate = rates.get(state.upper(), rates["DEFAULT"])
    return round(amount * rate, 2)

def apply_discount(total: float, discount_percent: float) -> float:
    """Applies a percentage discount to the total order amount."""
    if total < 0:
        raise ValueError("Total cannot be negative")
    if discount_percent < 0 or discount_percent > 100:
        raise ValueError("Discount must be between 0 and 100")

    discount_amount = total * (discount_percent / 100.0)
    final_price = total - discount_amount
    return round(final_price, 2)

def process_order(items: list[dict[str, Any]], state: str = "DEFAULT", discount_percent: float = 0.0) -> dict[str, Any]:
    """Processes an order, calculates subtotal, discount, tax, and grand total."""
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

CLEAN_CONFIG_YAML = '''service_name: "order-billing-service"
version: "1.4.0"
environment: "production"
currency: "USD"
api_timeout_seconds: 30
max_discount_percentage: 50.0
tax_rates:
  CA: 0.0825
  NY: 0.08875
  TX: 0.0625
  DEFAULT: 0.05
'''

class BugInjector:
    """Injects real software faults into demo_repo for live demonstration and testing."""

    @staticmethod
    def restore_pristine() -> dict[str, str]:
        """Restores all source files to known-good 100% passing state."""
        APP_FILE.write_text(CLEAN_APP_CODE, encoding="utf-8")
        CONFIG_FILE.write_text(CLEAN_CONFIG_YAML, encoding="utf-8")
        return {"status": "SUCCESS", "message": "Restored repository to pristine passing state."}

    @staticmethod
    def inject_logic_assertion_bug() -> dict[str, str]:
        """Scenario 1: Off-by-one / inverted discount calculation logic bug."""
        BugInjector.restore_pristine()
        # Invert calculation so 10% discount adds instead of subtracts: final_price = total + discount_amount
        buggy_code = CLEAN_APP_CODE.replace(
            "final_price = total - discount_amount",
            "final_price = total - (discount_amount + 5.0)  # BUG: off-by-five subtraction"
        )
        APP_FILE.write_text(buggy_code, encoding="utf-8")
        return {
            "scenario": "LOGIC_ASSERTION_BUG",
            "description": "Injected off-by-five logic error in apply_discount(). test_apply_discount_standard will fail with AssertionError."
        }

    @staticmethod
    def inject_import_error_bug() -> dict[str, str]:
        """Scenario 2: Broken module import defect."""
        BugInjector.restore_pristine()
        buggy_code = "import nonexistent_billing_telemetry_sdk\n" + CLEAN_APP_CODE
        APP_FILE.write_text(buggy_code, encoding="utf-8")
        return {
            "scenario": "IMPORT_ERROR_BUG",
            "description": "Injected missing module import. Pytest will fail with ModuleNotFoundError."
        }

    @staticmethod
    def inject_syntax_error_bug() -> dict[str, str]:
        """Scenario 3: Syntax error (missing colon)."""
        BugInjector.restore_pristine()
        buggy_code = CLEAN_APP_CODE.replace(
            "def calculate_tax(amount: float, state: str = \"DEFAULT\") -> float:",
            "def calculate_tax(amount: float, state: str = \"DEFAULT\") -> float"
        )
        APP_FILE.write_text(buggy_code, encoding="utf-8")
        return {
            "scenario": "SYNTAX_ERROR_BUG",
            "description": "Injected syntax error (missing colon). Python interpreter will raise SyntaxError."
        }

    @staticmethod
    def inject_config_typo_bug() -> dict[str, str]:
        """Scenario 4: Missing configuration key / typo in config.yaml."""
        BugInjector.restore_pristine()
        buggy_yaml = CLEAN_CONFIG_YAML.replace("api_timeout_seconds: 30", "timeout_legacy_sec: 30")
        CONFIG_FILE.write_text(buggy_yaml, encoding="utf-8")
        return {
            "scenario": "CONFIG_TYPO_BUG",
            "description": "Renamed api_timeout_seconds in config.yaml. test_load_service_config will raise KeyError."
        }

    @staticmethod
    def inject_high_risk_scenario() -> dict[str, str]:
        """Scenario 5: High-risk commit that triggers Human-in-the-Loop policy gate."""
        BugInjector.restore_pristine()
        # Invert logic bug, but commit risk is set high
        buggy_code = CLEAN_APP_CODE.replace(
            "final_price = total - discount_amount",
            "final_price = total + discount_amount  # High risk inversion"
        )
        APP_FILE.write_text(buggy_code, encoding="utf-8")
        return {
            "scenario": "HIGH_RISK_SCENARIO",
            "description": "Injected high-risk defect. Evaluator will assign high risk score, requiring Human-in-the-Loop approval before patch is applied."
        }

bug_injector = BugInjector()

SCENARIOS = {
    "1": {
        "name": "Scenario 1: Logic Defect",
        "description": "Injected off-by-five logic error in apply_discount(). test_apply_discount_standard will fail with AssertionError.",
        "target_file": "app.py"
    },
    "2": {
        "name": "Scenario 2: Syntax Error",
        "description": "Injected syntax error (missing colon). Python interpreter will raise SyntaxError.",
        "target_file": "app.py"
    },
    "3": {
        "name": "Scenario 3: Missing Module Dependency",
        "description": "Injected missing module import. Pytest will fail with ModuleNotFoundError.",
        "target_file": "app.py"
    },
    "4": {
        "name": "Scenario 4: Config / YAML Typo",
        "description": "Renamed api_timeout_seconds in config.yaml. test_load_service_config will raise KeyError.",
        "target_file": "config.yaml"
    },
    "5": {
        "name": "Scenario 5: High-Risk Inversion (Safety Gate & HITL)",
        "description": "Injected high-risk defect. Evaluator will assign high risk score, requiring Human-in-the-Loop approval before patch is applied.",
        "target_file": "app.py"
    }
}

def inject_fault(scenario_id: str) -> str:
    if scenario_id == "1":
        res = bug_injector.inject_logic_assertion_bug()
    elif scenario_id == "2":
        res = bug_injector.inject_syntax_error_bug()
    elif scenario_id == "3":
        res = bug_injector.inject_import_error_bug()
    elif scenario_id == "4":
        res = bug_injector.inject_config_typo_bug()
    elif scenario_id == "5":
        res = bug_injector.inject_high_risk_scenario()
    else:
        return "Unknown scenario"
    return res.get("description", "Injected fault")

def reset_demo_repo() -> str:
    res = bug_injector.restore_pristine()
    return res.get("message", "Restored pristine state")

