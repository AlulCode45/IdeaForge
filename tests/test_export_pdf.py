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
            "## Sub Section\n\n"
            "- [ ] Open task\n"
            "  - Nested item\n"
            "- [x] Done task [Verified]\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "  A --> B\n"
            "```\n"
        )
        body, toc, has_mermaid = export_pdf.md_to_html(md, ROOT)
        self.assertTrue(has_mermaid)
        self.assertEqual(len(toc), 2)
        self.assertIn("&#9744; ", body)
        self.assertIn("&#9745; ", body)
        self.assertNotIn("&amp;#9744;", body)
        self.assertIn('<div class="mermaid">', body)
        self.assertIn('<span class="tag">Verified</span>', body)

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


if __name__ == "__main__":
    unittest.main()
