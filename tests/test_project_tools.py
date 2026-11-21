import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INIT_SCRIPT = ROOT / "scripts/init_project.py"
LINT_SCRIPT = ROOT / "scripts/lint_project.py"
INSTALL_SCRIPT = ROOT / "scripts/install_skills.py"


class TestProjectTools(unittest.TestCase):
    def _setup_workspace(self, tmp_path: Path) -> None:
        shutil.copytree(ROOT / "templates", tmp_path / "templates")
        fin_scripts = tmp_path / ".agents/skills/financial-modeler/scripts"
        fin_scripts.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            ROOT / ".agents/skills/financial-modeler/scripts/example_inputs.json",
            fin_scripts / "example_inputs.json",
        )
        shutil.copyfile(
            ROOT / ".agents/skills/financial-modeler/scripts/example_saas_inputs.json",
            fin_scripts / "example_saas_inputs.json",
        )
        (tmp_path / "prps").mkdir(exist_ok=True)

    def test_init_and_lint_full_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._setup_workspace(ws)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "demo-saas",
                    "--title",
                    "Demo SaaS",
                    "--track",
                    "full",
                    "--model-type",
                    "saas",
                    "--date",
                    "2026-11-22",
                    "--base-dir",
                    str(ws),
                ],
                check=True,
                capture_output=True,
            )
            proj = ws / "prps/2026-11-22-demo-saas"
            self.assertTrue((proj / "README.md").exists())
            self.assertTrue((proj / "CHANGELOG.md").exists())
            self.assertTrue((proj / "13-assumption-register.md").exists())
            self.assertTrue((proj / "model/inputs.json").exists())
            self.assertIn("2026-11-22-demo-saas", (ws / "prps/INDEX.md").read_text(encoding="utf-8"))

            lint_proc = subprocess.run(
                [sys.executable, str(LINT_SCRIPT), str(proj)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(lint_proc.returncode, 0, lint_proc.stdout + lint_proc.stderr)

    def test_lint_catches_scorecard_math_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            self._setup_workspace(ws)
            subprocess.run(
                [
                    sys.executable,
                    str(INIT_SCRIPT),
                    "--slug",
                    "bad-math",
                    "--title",
                    "Bad Math",
                    "--track",
                    "business",
                    "--date",
                    "2026-11-22",
                    "--base-dir",
                    str(ws),
                ],
                check=True,
                capture_output=True,
            )
            proj = ws / "prps/2026-11-22-bad-math"
            (proj / "17-scorecard-and-decision.md").write_text(
                "# Scorecard\n\n"
                "| Criterion | Weight | Score (1-5) | Weighted | Justification |\n"
                "|---|---|---|---|---|\n"
                "| Market demand | 100 | 3 | 4.50 | wrong math |\n"
                "| **Total** | 100 | | **4.50/5.0** | |\n\n"
                "## Verdict\nGo\n",
                encoding="utf-8",
            )
            lint_proc = subprocess.run(
                [sys.executable, str(LINT_SCRIPT), str(proj)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(lint_proc.returncode, 0)
            self.assertIn("[FAIL]", lint_proc.stdout)

    def test_install_skills_for_claude_and_gemini(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            shutil.copytree(ROOT / ".agents", ws / ".agents")
            subprocess.run(
                [sys.executable, str(INSTALL_SCRIPT), "--target", "all", "--scope", "project", "--base-dir", str(ws)],
                check=True,
                capture_output=True,
            )
            self.assertTrue((ws / ".claude/skills/project-intake/SKILL.md").exists())
            self.assertTrue((ws / ".gemini/skills/financial-modeler/scripts/model.py").exists())
            self.assertTrue((ws / ".codex/skills/decision-scorecard/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
