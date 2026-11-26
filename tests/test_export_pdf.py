import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXPORT_SCRIPT = ROOT / ".agents/skills/executive-reporter/scripts/export_pdf.py"
sys.path.insert(0, str(EXPORT_SCRIPT.parent))
import export_pdf  # noqa: E402


class TestExportPdf(unittest.TestCase):
    def test_mermaid_checkbox_nested_list_and_toc(self):
        md = (
            "# Section One\n\n"
            "**Recommendation**: Proceed with pilot.\n\n"
            "<!-- kpi-grid -->\n"
            "Score | 3.6/5.0 | Conditional | good\n"
            "<!-- /kpi-grid -->\n\n"
            "| Criterion | Weight | Score (1-5) |\n"
            "|---|---|---|\n"
            "| Demand | 100 | 4 |\n\n"
            "## Sub Section\n\n"
            "- [ ] Open task\n"
            "  - Nested item\n"
            "- [x] Done task [Verified]\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "  A --> B\n"
            "```\n"
        )
        body, toc, has_mermaid = export_pdf.md_to_html(md, ROOT, add_back_to_toc=True)
        self.assertTrue(has_mermaid)
        self.assertEqual(len(toc), 2)
        self.assertIn("&#9744; ", body)
        self.assertIn("&#9745; ", body)
        self.assertNotIn("&amp;#9744;", body)
        self.assertIn('<div class="mermaid">', body)
        self.assertIn("tag-verified", body)
        self.assertIn("kpi-grid", body)
        self.assertIn("callout-rec", body)
        self.assertIn("score-bar", body)
        self.assertIn('href="#toc-top"', body)

    def test_real_pdf_generation_with_sample_report(self):
        sample_md = ROOT / "examples/sample-report/sample-executive-report.md"
        with tempfile.TemporaryDirectory() as tmp:
            out_pdf = Path(tmp) / "out.pdf"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EXPORT_SCRIPT),
                    "--input",
                    str(sample_md),
                    "--output",
                    str(out_pdf),
                    "--title",
                    "Test Sample PDF",
                    "--toc",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(out_pdf.exists())
            self.assertGreater(out_pdf.stat().st_size, 5000)
            self.assertIn("PDF generated:", proc.stdout)

    def test_export_prd_project_mode(self):
        init_script = ROOT / "scripts/init_project.py"
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            (ws / "templates").mkdir()
            for tpl in (ROOT / "templates").glob("*.md"):
                (ws / "templates" / tpl.name).write_text(tpl.read_text(encoding="utf-8"), encoding="utf-8")
            subprocess.run(
                [
                    sys.executable,
                    str(init_script),
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
            proj = ws / "prds/2026-11-26-checkout-v2"
            out_pdf = proj / "assets/checkout-v2-prd.pdf"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(EXPORT_SCRIPT),
                    "--project",
                    str(proj),
                    "--mode",
                    "prd",
                    "--lang",
                    "en",
                    "--output",
                    str(out_pdf),
                    "--title",
                    "Checkout v2 PRD",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertTrue(out_pdf.exists())
            self.assertGreater(out_pdf.stat().st_size, 5000)
            self.assertIn("PDF generated:", proc.stdout)


if __name__ == "__main__":
    unittest.main()
