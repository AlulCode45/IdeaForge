import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL_SCRIPT = ROOT / ".agents/skills/financial-modeler/scripts/model.py"
sys.path.insert(0, str(MODEL_SCRIPT.parent))
import model  # noqa: E402


class TestFinancialModel(unittest.TestCase):
    def test_cac_not_double_counted_on_repeat_orders(self):
        inputs = {
            "model_type": "transactional",
            "currency": "IDR",
            "price": 100000,
            "unit_variable_cost": 40000,
            "monthly_fixed_costs": 0,
            "starting_cash": 1000000,
            "month1_units": 10,
            "monthly_growth": 0.0,
            "cac": 20000,
            "repeat_orders_per_customer": 2.0,
            "scenario_multipliers": {"base": {"units": 1.0, "growth": 1.0, "cost": 1.0}},
        }
        res = model.run_transactional(inputs, inputs["scenario_multipliers"]["base"], months=1)
        # 10 units * (100k - 40k) = 600k gross profit; 10 / 2.0 = 5 new customers * 20k = 100k CAC -> 500k net
        self.assertEqual(res["rows"][0][3], 500000)

    def test_zero_cac_does_not_crash(self):
        inputs = {
            "model_type": "transactional",
            "currency": "USD",
            "price": 50,
            "unit_variable_cost": 10,
            "monthly_fixed_costs": 100,
            "starting_cash": 1000,
            "month1_units": 10,
            "monthly_growth": 0.0,
            "cac": 0,
            "repeat_orders_per_customer": 1.0,
            "scenario_multipliers": {"base": {"units": 1.0, "growth": 1.0, "cost": 1.0}},
        }
        res = model.run_transactional(inputs, inputs["scenario_multipliers"]["base"], months=3)
        self.assertIsNone(res["ltv_cac"])

    def test_saas_mode_and_cli_outputs(self):
        saas_path = ROOT / ".agents/skills/financial-modeler/scripts/example_saas_inputs.json"
        with tempfile.TemporaryDirectory() as tmp:
            charts_dir = Path(tmp) / "charts"
            json_out = Path(tmp) / "summary.json"
            proc = subprocess.run(
                [sys.executable, str(MODEL_SCRIPT), str(saas_path), "--charts-dir", str(charts_dir), "--json-out", str(json_out)],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("mode: saas", proc.stdout)
            self.assertIn("2-Way Sensitivity", proc.stdout)
            for fname in ("cash-projection.svg", "revenue-profit.svg", "unit-economics.svg", "sensitivity-heatmap.svg"):
                p = charts_dir / fname
                self.assertTrue(p.exists(), f"Missing {fname}")
                self.assertIn("<svg", p.read_text(encoding="utf-8"))
            summary = json.loads(json_out.read_text(encoding="utf-8"))
            self.assertEqual(summary["model_type"], "saas")
            self.assertIn("base", summary["scenarios"])


if __name__ == "__main__":
    unittest.main()
