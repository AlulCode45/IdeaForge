import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_SCRIPT = ROOT / "scripts/init_project.py"
WEB_SCRIPT = ROOT / ".agents/skills/executive-reporter/scripts/export_web.py"
sys.path.insert(0, str(WEB_SCRIPT.parent))
import export_web  # noqa: E402


class TestExportWeb(unittest.TestCase):
    def _setup_workspace(self, ws: Path) -> None:
        shutil.copytree(ROOT / "templates", ws / "templates")
        fin_scripts = ws / ".agents/skills/financial-modeler/scripts"
        fin_scripts.mkdir(parents=True, exist_ok=True)
        for name in ("example_inputs.json", "example_saas_inputs.json"):
            shutil.copyfile(ROOT / ".agents/skills/financial-modeler/scripts" / name, fin_scripts / name)

    def test_single_markdown_export_inlines_svg_and_simulator(self):
        sample_md = ROOT / "examples/sample-report/sample-executive-report.md"
        inputs_json = ROOT / ".agents/skills/financial-modeler/scripts/example_inputs.json"
        with tempfile.TemporaryDirectory() as tmp:
            out_html = Path(tmp) / "report.html"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(WEB_SCRIPT),
                    "--input",
                    str(sample_md),
                    "--model-inputs",
                    str(inputs_json),
                    "--output",
                    str(out_html),
                    "--title",
                    "Sample Web Report",
                    "--lang",
                    "en",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Web GUI generated:", proc.stdout)
            text = out_html.read_text(encoding="utf-8")
            self.assertIn("<svg", text)  # inlined cash-projection.svg
            self.assertIn('id="sim-panel"', text)
            self.assertIn('id="sim-price"', text)
            self.assertIn('class="task-cb"', text)
            self.assertIn('data-ev-filter="estimate"', text)
            self.assertIn('<div class="mermaid">', text)
            self.assertIn("score-bar", text)

    def test_project_export_prd_and_full_with_lint_and_simulator(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._setup_workspace(ws)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "checkout-v2",
                    "--title",
                    "Checkout v2",
                    "--track",
                    "prd",
                    "--date",
                    "2026-11-26",
                    "--base-dir",
                    str(ws),
                ],
                check=True,
                capture_output=True,
            )
            prd_dir = ws / "prds/2026-11-26-checkout-v2"
            prd_html = prd_dir / "assets/checkout-v2-prd.html"
            subprocess.run(
                [
                    sys.executable,
                    str(WEB_SCRIPT),
                    "--project",
                    str(prd_dir),
                    "--mode",
                    "prd",
                    "--output",
                    str(prd_html),
                    "--lang",
                    "id",
                ],
                check=True,
                capture_output=True,
            )
            html_text = prd_html.read_text(encoding="utf-8")
            self.assertIn("Product Requirements Document (PRD)", html_text)
            self.assertIn("0 FAIL", html_text)
            self.assertIn("FR-001", html_text)

            # Full SaaS project includes interactive SaaS What-If Simulator automatically
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "bengkel-saas",
                    "--title",
                    "Bengkel SaaS",
                    "--track",
                    "full",
                    "--model-type",
                    "saas",
                    "--date",
                    "2026-11-26",
                    "--base-dir",
                    str(ws),
                ],
                check=True,
                capture_output=True,
            )
            prp_dir = ws / "prds/2026-11-26-bengkel-saas"
            (prp_dir / "00-overview.md").write_text("# Overview\n\nTarget launch Q1 [Assumption].\n", encoding="utf-8")
            prp_html = prp_dir / "assets/bengkel-web.html"
            subprocess.run(
                [
                    sys.executable,
                    str(WEB_SCRIPT),
                    "--project",
                    str(prp_dir),
                    "--mode",
                    "full",
                    "--output",
                    str(prp_html),
                ],
                check=True,
                capture_output=True,
            )
            prp_text = prp_html.read_text(encoding="utf-8")
            self.assertIn('id="sim-churn"', prp_text)
            self.assertIn("SaaS", prp_text)

    def test_live_server_hub_view_download_and_path_safety(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._setup_workspace(ws)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "wallet-prd",
                    "--title",
                    "Wallet PRD",
                    "--track",
                    "prd",
                    "--date",
                    "2026-11-26",
                    "--base-dir",
                    str(ws),
                ],
                check=True,
                capture_output=True,
            )

            server = export_web.create_server(ws, "127.0.0.1", 0, lang="id")
            port = server.server_address[1]
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            try:
                base_url = f"http://127.0.0.1:{port}"
                with urllib.request.urlopen(f"{base_url}/") as resp:
                    self.assertEqual(resp.status, 200)
                    hub_html = resp.read().decode("utf-8")
                    self.assertIn("IdeaForge Portfolio Hub", hub_html)
                    self.assertIn("Wallet PRD", hub_html)

                rel = urllib.parse.quote("prds/2026-11-26-wallet-prd")
                with urllib.request.urlopen(f"{base_url}/view?path={rel}&mode=prd") as resp:
                    self.assertEqual(resp.status, 200)
                    view_html = resp.read().decode("utf-8")
                    self.assertIn("Portfolio Hub", view_html)
                    self.assertIn("FR-001", view_html)
                    self.assertIn('id="edit-toggle-btn"', view_html)

                # Test live editing via POST /api/save-doc
                updated_md = (ws / "prds/2026-11-26-wallet-prd/PRD.md").read_text(encoding="utf-8") + "\n- **FR-099**: Live edited item.\n"
                save_req = urllib.request.Request(
                    f"{base_url}/api/save-doc",
                    data=json.dumps({
                        "path": "prds/2026-11-26-wallet-prd",
                        "filename": "PRD.md",
                        "content": updated_md,
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(save_req) as resp:
                    self.assertEqual(resp.status, 200)
                    save_data = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(save_data["ok"])
                    self.assertIn("FR-099", save_data["html"])
                    self.assertIn("Live edited item.", (ws / "prds/2026-11-26-wallet-prd/PRD.md").read_text(encoding="utf-8"))

                # Test that Mermaid flows inside reports are automatically upgraded to interactive Visual Architect Flow Cards
                flow_md = updated_md + "\n## Alur Utama\n\n```mermaid\nflowchart LR\n  A[Kasir] --> B[Bayar]\n```\n"
                flow_req = urllib.request.Request(
                    f"{base_url}/api/save-doc",
                    data=json.dumps({
                        "path": "prds/2026-11-26-wallet-prd",
                        "filename": "PRD.md",
                        "content": flow_md,
                    }).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(flow_req) as resp:
                    self.assertEqual(resp.status, 200)
                    fdata = json.loads(resp.read().decode("utf-8"))
                    self.assertTrue(fdata["ok"])
                    self.assertIn("va-flow-card", fdata["html"])
                    self.assertIn("data-va-expand", fdata["html"])

                with urllib.request.urlopen(f"{base_url}/api/download-html?path={rel}&mode=prd") as resp:
                    self.assertEqual(resp.status, 200)
                    self.assertIn("attachment", resp.headers.get("Content-Disposition", ""))

                with self.assertRaises(urllib.error.HTTPError) as ctx:
                    urllib.request.urlopen(f"{base_url}/view?path=../../etc/passwd")
                self.assertEqual(ctx.exception.code, 403)
                ctx.exception.close()
            finally:
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
