#!/usr/bin/env python3
"""Export IdeaForge Markdown reports, PRDs, or PRPs to an interactive Web GUI
(self-contained static HTML) or serve a live local Portfolio Hub web dashboard.

Pure Python 3 stdlib — zero external pip or npm dependencies.

Usage:
  # 1. Single Markdown -> self-contained interactive HTML
  python3 export_web.py --input examples/sample-report/sample-executive-report.md \
    --output examples/sample-report/sample-executive-report.html \
    --title "Sample Report" --model-inputs .agents/skills/financial-modeler/scripts/example_inputs.json

  # 2. Project folder (prps/<slug> or prds/<slug>) -> self-contained HTML
  python3 export_web.py --project prps/<slug> --mode executive \
    --output prps/<slug>/assets/<slug>-web.html --title "Project Name"

  # 3. Live local Web Dashboard (Portfolio Hub + Viewer + What-If Simulator)
  python3 export_web.py --serve --port 8765
"""
import argparse
import base64
import html
import http.server
import json
import mimetypes
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import urllib.parse
import webbrowser
from datetime import date
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent.parent.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import export_pdf  # noqa: E402

SCRIPTS_DIR = REPO_ROOT / "scripts"
if SCRIPTS_DIR.is_dir() and str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import lint_project  # noqa: E402
except Exception:
    lint_project = None


I18N = {
    "id": {
        "hub_title": "IdeaForge Portfolio Hub",
        "hub_subtitle": "Dashboard interaktif untuk seluruh proyek PRP, PRD, dan Quick Brief.",
        "back_hub": "Portfolio Hub",
        "search_placeholder": "Cari dokumen atau teks... (/)",
        "documents": "Dokumen",
        "sections": "Daftar Bagian",
        "all_view": "Tampilan Penuh",
        "tab_view": "Per Dokumen",
        "simulator": "Simulator Finansial",
        "quality_gates": "Quality Gate",
        "print_pdf": "Cetak / PDF",
        "download_html": "Unduh HTML",
        "theme_toggle": "Tema",
        "evidence_filter": "Filter Bukti",
        "all_tags": "Semua",
        "reset_sim": "Reset Default",
        "copy_json": "Salin inputs.json",
        "copied": "Tersalin!",
        "no_results": "Tidak ada hasil yang cocok.",
        "open_web": "Buka Web GUI",
        "export_pdf_btn": "Unduh PDF",
        "empty_hub": "Belum ada proyek di prps/, prds/, atau ideas/. Jalankan init_project.py untuk memulai.",
        "files_unit": "dokumen",
        "score_label": "Skor",
        "breakeven": "Break-Even (Base)",
        "ending_cash": "Kas Bulan 12",
        "lowest_cash": "Kas Terendah",
        "gross_margin": "Margin Kontribusi",
        "ltv_cac": "Rasio LTV / CAC",
        "payback": "Payback CAC",
        "runway": "Runway (Base)",
        "month_prefix": "Bulan",
        "not_reached": "Belum tercapai",
        "scenario_pess": "Pesimis",
        "scenario_base": "Dasar",
        "scenario_opt": "Optimis",
        "sim_subtitle": "Geser parameter di bawah untuk melihat dampak langsung ke arus kas 12 bulan, break-even, dan unit economics.",
    },
    "en": {
        "hub_title": "IdeaForge Portfolio Hub",
        "hub_subtitle": "Interactive workspace dashboard for all PRPs, PRDs, and Quick Briefs.",
        "back_hub": "Portfolio Hub",
        "search_placeholder": "Search documents or text... (/)",
        "documents": "Documents",
        "sections": "On This Page",
        "all_view": "Full View",
        "tab_view": "By Document",
        "simulator": "Financial Simulator",
        "quality_gates": "Quality Gates",
        "print_pdf": "Print / PDF",
        "download_html": "Download HTML",
        "theme_toggle": "Theme",
        "evidence_filter": "Evidence Filter",
        "all_tags": "All",
        "reset_sim": "Reset Defaults",
        "copy_json": "Copy inputs.json",
        "copied": "Copied!",
        "no_results": "No matching content found.",
        "open_web": "Open Web GUI",
        "export_pdf_btn": "Download PDF",
        "empty_hub": "No projects found in prps/, prds/, or ideas/ yet. Run init_project.py to scaffold one.",
        "files_unit": "docs",
        "score_label": "Score",
        "breakeven": "Break-Even (Base)",
        "ending_cash": "Month-12 Cash",
        "lowest_cash": "Lowest Cash",
        "gross_margin": "Contribution Margin",
        "ltv_cac": "LTV / CAC Ratio",
        "payback": "CAC Payback",
        "runway": "Runway (Base)",
        "month_prefix": "Month",
        "not_reached": "Not within 12 mo",
        "scenario_pess": "Pessimistic",
        "scenario_base": "Base",
        "scenario_opt": "Optimistic",
        "sim_subtitle": "Adjust key assumptions below to simulate 12-month cash flow, break-even, and unit economics in real time.",
    },
}


def inline_local_assets(html_body: str, base_dir: Path) -> str:
    """Embed local SVG/PNG/JPG images so static HTML works offline anywhere."""
    img_re = re.compile(r'<img src="([^"]+)" alt="([^"]*)">')

    def _replace(match: re.Match) -> str:
        src = match.group(1)
        alt = match.group(2)
        local_path: Path | None = None
        if src.startswith("file://"):
            parsed = urllib.parse.urlparse(src)
            local_path = Path(urllib.parse.unquote(parsed.path))
        elif not src.startswith(("http://", "https://", "data:")):
            local_path = (base_dir / src).resolve()

        if local_path and local_path.is_file():
            ext = local_path.suffix.lower()
            if ext == ".svg":
                svg_text = local_path.read_text(encoding="utf-8").strip()
                svg_text = re.sub(r"<\?xml[^>]*\?>", "", svg_text).strip()
                cap = f'<figcaption>{alt}</figcaption>' if alt else ""
                return f'<figure class="svg-figure">{svg_text}{cap}</figure>'
            mime, _ = mimetypes.guess_type(str(local_path))
            if mime and mime.startswith("image/"):
                b64 = base64.b64encode(local_path.read_bytes()).decode("ascii")
                return f'<figure class="img-figure"><img src="data:{mime};base64,{b64}" alt="{alt}"></figure>'
        return match.group(0)

    return img_re.sub(_replace, html_body)


def make_interactive_checkboxes(html_body: str, doc_id: str) -> str:
    """Turn static unicode checkboxes from md_to_html into interactive checkboxes."""
    idx = 0

    def _repl_unchecked(_m: re.Match) -> str:
        nonlocal idx
        idx += 1
        key = f"{doc_id}-cb-{idx}"
        return f'<li class="task-item"><label><input type="checkbox" class="task-cb" data-task-key="{key}"><span>'

    def _repl_checked(_m: re.Match) -> str:
        nonlocal idx
        idx += 1
        key = f"{doc_id}-cb-{idx}"
        return f'<li class="task-item is-done"><label><input type="checkbox" class="task-cb" data-task-key="{key}" checked><span>'

    out_lines = []
    for ln in html_body.splitlines():
        if "<li>&#9744; " in ln:
            ln = re.sub(r"<li>&#9744; ", _repl_unchecked, ln, count=1)
            ln = ln.replace("</li>", "</span></label></li>", 1)
        elif "<li>&#9745; " in ln:
            ln = re.sub(r"<li>&#9745; ", _repl_checked, ln, count=1)
            ln = ln.replace("</li>", "</span></label></li>", 1)
        out_lines.append(ln)
    return "\n".join(out_lines)


def _friendly_doc_label(path: Path) -> str:
    stem = path.stem
    if stem.upper() == "PRD":
        return "PRD"
    if stem.upper() == "README":
        return "Overview / README"
    cleaned = re.sub(r"^\d+-", "", stem).replace("-", " ").replace("_", " ").strip()
    prefix_m = re.match(r"^(\d+)-", stem)
    title = cleaned.title() if cleaned else stem
    return f"{prefix_m.group(1)} · {title}" if prefix_m else title


def load_project_documents(project_dir: Path, mode: str) -> list[dict]:
    """Load ordered markdown documents from a prps/, prds/, or ideas/ folder."""
    files: list[Path] = []
    seen: set[Path] = set()

    def _add(p: Path) -> None:
        rp = p.resolve()
        if rp.is_file() and rp not in seen:
            seen.add(rp)
            files.append(rp)

    if mode in export_pdf.SECTION_MODES:
        for fname in export_pdf.SECTION_MODES[mode]:
            _add(project_dir / fname)

    if mode in ("prd", "technical", "full"):
        sub_prds = project_dir / "prds"
        if sub_prds.is_dir():
            for prd_doc in sorted(sub_prds.glob("*.md")):
                _add(prd_doc)
        decisions_dir = project_dir / "decisions"
        if decisions_dir.is_dir():
            for adr in sorted(decisions_dir.glob("ADR-*.md")):
                _add(adr)

    # Fallback for ideas/<slug>/ or custom folders without standard numbered files
    if not files:
        for md in sorted(project_dir.glob("*.md")):
            if md.name.upper() != "CHANGELOG.MD":
                _add(md)

    if not files:
        raise FileNotFoundError(f"No Markdown documents found in {project_dir}")

    docs = []
    for idx, fpath in enumerate(files):
        raw = fpath.read_text(encoding="utf-8")
        first_h1 = next(
            (re.sub(r"^#\s+", "", ln.strip()) for ln in raw.splitlines() if ln.strip().startswith("# ")),
            None,
        )
        doc_id = f"doc-{idx + 1}-{export_pdf.slugify(fpath.stem)}"
        docs.append(
            {
                "id": doc_id,
                "filename": fpath.name,
                "label": _friendly_doc_label(fpath),
                "title": first_h1 or _friendly_doc_label(fpath),
                "markdown": raw,
                "base_dir": fpath.parent,
            }
        )
    return docs


def run_lint_summary(project_dir: Path) -> dict | None:
    """Run lint_project checks in-process if available and applicable."""
    if lint_project is None or not project_dir.is_dir():
        return None
    if not ((project_dir / "README.md").exists() or (project_dir / "PRD.md").exists()):
        return None
    findings: list[tuple[str, str]] = []
    index_path = project_dir.parent / "INDEX.md"
    lint_project.check_core_files(project_dir, findings)
    lint_project.check_links(project_dir, findings)
    if hasattr(lint_project, "check_prd"):
        lint_project.check_prd(project_dir, findings)
    lint_project.check_scorecard(project_dir, findings)
    lint_project.check_stale_dates(project_dir, 365, findings)
    lint_project.check_evidence_labels(project_dir, findings)
    lint_project.check_financial_consistency(project_dir, findings)
    lint_project.check_anti_slop(project_dir, findings)
    lint_project.check_index_registration(project_dir, index_path, findings)
    fails = sum(1 for sev, _ in findings if sev == "FAIL")
    warns = sum(1 for sev, _ in findings if sev == "WARN")
    passes = sum(1 for sev, _ in findings if sev == "PASS")
    return {
        "fails": fails,
        "warns": warns,
        "passes": passes,
        "items": [{"severity": sev, "message": msg} for sev, msg in findings],
    }


def extract_scorecard_badge(project_dir: Path) -> tuple[str | None, str | None]:
    """Extract total score and verdict from 17-scorecard-and-decision.md if present."""
    sc_path = project_dir / "17-scorecard-and-decision.md"
    if not sc_path.exists():
        return None, None
    text = sc_path.read_text(encoding="utf-8")
    score_m = re.search(r"total[^\n]*\|\s*\*{0,2}(\d+(?:[.,]\d+)?)\s*/\s*5(?:\.0)?", text, re.I)
    verdict_m = re.search(r"##\s*Verdict\s*\n+([^\n#]+)", text, re.I)
    score = score_m.group(1).replace(",", ".") if score_m else None
    verdict = verdict_m.group(1).strip(" *`") if verdict_m else None
    return score, verdict


WEB_CSS = r"""
:root {
  --bg: #F8FAFC;
  --surface: #FFFFFF;
  --surface-alt: #F1F5F9;
  --border: #E2E8F0;
  --border-strong: #CBD5E1;
  --text: #0F172A;
  --text-muted: #475569;
  --text-subtle: #64748B;
  --accent: #1B365D;
  --accent-bright: #2563EB;
  --accent-soft: #EFF6FF;
  --accent-border: #BFDBFE;
  --good-bg: #F0FDF4;
  --good-text: #166534;
  --good-border: #86EFAC;
  --warn-bg: #FEF2F2;
  --warn-text: #991B1B;
  --warn-border: #FCA5A5;
  --amber-bg: #FEF3C7;
  --amber-text: #92400E;
  --amber-border: #FCD34D;
  --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.05);
  --shadow-md: 0 4px 12px rgba(15, 23, 42, 0.06);
  --radius: 8px;
  --sidebar-w: 276px;
  --topbar-h: 58px;
  --font-sans: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", monospace;
}

[data-theme="dark"] {
  --bg: #0B1120;
  --surface: #111827;
  --surface-alt: #1E293B;
  --border: #1F2937;
  --border-strong: #334155;
  --text: #F1F5F9;
  --text-muted: #CBD5E1;
  --text-subtle: #94A3B8;
  --accent: #60A5FA;
  --accent-bright: #3B82F6;
  --accent-soft: rgba(37, 99, 235, 0.14);
  --accent-border: rgba(96, 165, 250, 0.35);
  --good-bg: rgba(22, 101, 52, 0.22);
  --good-text: #86EFAC;
  --good-border: rgba(134, 239, 172, 0.35);
  --warn-bg: rgba(153, 27, 27, 0.24);
  --warn-text: #FCA5A5;
  --warn-border: rgba(252, 165, 165, 0.35);
  --amber-bg: rgba(146, 64, 14, 0.25);
  --amber-text: #FCD34D;
  --amber-border: rgba(252, 211, 77, 0.35);
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.28);
  --shadow-md: 0 6px 18px rgba(0, 0, 0, 0.35);
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 15px;
  line-height: 1.65;
  -webkit-font-smoothing: antialiased;
}

/* Topbar */
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: var(--topbar-h);
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 18px;
  gap: 12px;
  box-shadow: var(--shadow-sm);
}
.topbar-left, .topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 14px;
  color: var(--accent);
  text-decoration: none;
  white-space: nowrap;
}
.brand-dot {
  width: 9px;
  height: 9px;
  border-radius: 3px;
  background: var(--accent-bright);
  display: inline-block;
}
.topbar-title {
  font-weight: 600;
  font-size: 14.5px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.topbar-kicker {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  border: 1px solid var(--accent-border);
  white-space: nowrap;
}
.search-wrap {
  position: relative;
  width: 240px;
  max-width: 34vw;
}
.search-input {
  width: 100%;
  height: 34px;
  padding: 0 12px;
  border-radius: 7px;
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  outline: none;
}
.search-input:focus {
  border-color: var(--accent-bright);
  box-shadow: 0 0 0 3px var(--accent-soft);
}
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 34px;
  padding: 0 12px;
  border-radius: 7px;
  border: 1px solid var(--border-strong);
  background: var(--surface);
  color: var(--text);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.btn:hover { background: var(--surface-alt); }
.btn-primary {
  background: var(--accent);
  border-color: var(--accent);
  color: #FFFFFF;
}
.btn-primary:hover { filter: brightness(1.08); background: var(--accent); }
.btn-sm { height: 29px; padding: 0 10px; font-size: 12px; }
.menu-btn { display: none; }

/* App Shell */
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-w) minmax(0, 1fr);
  min-height: calc(100vh - var(--topbar-h));
}
.sidebar {
  position: sticky;
  top: var(--topbar-h);
  height: calc(100vh - var(--topbar-h));
  overflow-y: auto;
  background: var(--surface);
  border-right: 1px solid var(--border);
  padding: 16px 14px 28px;
}
.sidebar-section { margin-bottom: 18px; }
.sidebar-heading {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-subtle);
  margin: 0 0 8px 8px;
}
.nav-list { list-style: none; margin: 0; padding: 0; }
.nav-item { margin-bottom: 2px; }
.nav-btn {
  width: 100%;
  text-align: left;
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 13.5px;
  font-weight: 500;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  text-decoration: none;
}
.nav-btn:hover { background: var(--surface-alt); color: var(--text); }
.nav-btn.active {
  background: var(--accent-soft);
  color: var(--accent);
  font-weight: 600;
}
.nav-sub {
  padding-left: 18px;
  font-size: 12.5px;
  font-weight: 400;
}
.view-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
  padding: 3px;
  border-radius: 7px;
  background: var(--surface-alt);
  margin-bottom: 14px;
}
.view-toggle button {
  border: 0;
  background: transparent;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 5px 6px;
  border-radius: 5px;
  cursor: pointer;
}
.view-toggle button.active {
  background: var(--surface);
  color: var(--text);
  box-shadow: var(--shadow-sm);
}

/* Main Content */
.main {
  padding: 26px 34px 64px;
  max-width: 980px;
  width: 100%;
  margin: 0 auto;
}
.hero-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-top: 4px solid var(--accent);
  border-radius: var(--radius);
  padding: 22px 24px;
  margin-bottom: 18px;
  box-shadow: var(--shadow-sm);
}
.hero-title {
  margin: 0 0 6px 0;
  font-size: 24px;
  line-height: 1.25;
  color: var(--text);
  border: none;
  padding: 0;
}
.hero-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  font-size: 13px;
  color: var(--text-subtle);
}

/* Evidence Filter Bar */
.toolbar-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-bottom: 18px;
}
.pill-group { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.pill-label { font-size: 12px; font-weight: 600; color: var(--text-subtle); margin-right: 4px; }
.filter-pill {
  border: 1px solid var(--border-strong);
  background: var(--bg);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 999px;
  cursor: pointer;
}
.filter-pill.active {
  background: var(--accent);
  border-color: var(--accent);
  color: #FFFFFF;
}
.lint-pill {
  font-family: var(--font-mono);
  font-size: 11.5px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 999px;
  border: 1px solid var(--good-border);
  background: var(--good-bg);
  color: var(--good-text);
  cursor: pointer;
}
.lint-pill.has-warn {
  border-color: var(--amber-border);
  background: var(--amber-bg);
  color: var(--amber-text);
}
.lint-pill.has-fail {
  border-color: var(--warn-border);
  background: var(--warn-bg);
  color: var(--warn-text);
}
.lint-drawer {
  display: none;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 16px;
  margin-bottom: 18px;
  font-size: 13px;
}
.lint-drawer.open { display: block; }
.lint-row { display: flex; gap: 10px; padding: 4px 0; border-bottom: 1px solid var(--border); }
.lint-row:last-child { border-bottom: none; }

/* Document Article */
.doc-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 26px 30px;
  margin-bottom: 22px;
  box-shadow: var(--shadow-sm);
}
.doc-panel.hidden { display: none; }
.doc-panel h1 {
  font-size: 21px;
  margin: 0 0 14px 0;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
  color: var(--text);
}
.doc-panel h2 {
  font-size: 17px;
  margin: 24px 0 10px 0;
  color: var(--accent);
}
.doc-panel h3 { font-size: 15px; margin: 18px 0 8px 0; color: var(--text); }
.doc-panel h4 { font-size: 14px; margin: 14px 0 6px 0; color: var(--text-muted); }
.doc-panel p { margin: 0 0 11px 0; }
.doc-panel ul, .doc-panel ol { margin: 0 0 12px 0; padding-left: 22px; }
.doc-panel li { margin-bottom: 5px; }
.doc-panel a { color: var(--accent-bright); text-decoration: none; }
.doc-panel a:hover { text-decoration: underline; }
.doc-panel hr { border: 0; border-top: 1px solid var(--border); margin: 20px 0; }

/* Callouts & KPI Grid */
.callout-rec {
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  border-left: 4px solid var(--accent);
  padding: 12px 16px;
  border-radius: 6px;
  margin: 12px 0 16px 0;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
  gap: 10px;
  margin: 14px 0 18px 0;
}
.kpi-card {
  background: var(--bg);
  border: 1px solid var(--border);
  border-top: 3px solid var(--accent);
  border-radius: 6px;
  padding: 12px 14px;
}
.kpi-card.good { border-top-color: #16A34A; background: var(--good-bg); }
.kpi-card.warn { border-top-color: #DC2626; background: var(--warn-bg); }
.kpi-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-subtle);
  margin-bottom: 4px;
}
.kpi-val {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.kpi-sub { font-size: 12px; color: var(--text-muted); margin-top: 3px; }

blockquote {
  margin: 12px 0;
  padding: 10px 15px;
  background: var(--surface-alt);
  border-left: 4px solid var(--accent);
  border-radius: 0 6px 6px 0;
  color: var(--text-muted);
}
blockquote.callout-warn {
  background: var(--warn-bg);
  border-left-color: #DC2626;
  color: var(--warn-text);
}

/* Tables */
.table-wrap { overflow-x: auto; margin: 14px 0 18px 0; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
th {
  background: var(--surface-alt);
  color: var(--text);
  font-weight: 600;
  text-align: left;
  padding: 8px 10px;
  border-top: 2px solid var(--accent);
  border-bottom: 1px solid var(--border-strong);
}
td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.score-bar-wrap { display: inline-flex; align-items: center; gap: 8px; }
.score-bar {
  width: 56px;
  height: 8px;
  background: var(--border);
  border-radius: 4px;
  overflow: hidden;
  display: inline-block;
}
.score-fill { height: 100%; background: var(--accent-bright); }

/* Code & Diagrams */
code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--surface-alt);
  padding: 2px 5px;
  border-radius: 4px;
}
pre {
  background: var(--surface-alt);
  border: 1px solid var(--border);
  padding: 12px 14px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 12.5px;
}
pre code { background: none; padding: 0; }
.svg-figure, .img-figure {
  margin: 16px 0;
  padding: 12px;
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  text-align: center;
}
.svg-figure svg, .img-figure img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
.svg-figure figcaption { font-size: 12px; color: #475569; margin-top: 6px; }
.mermaid-block {
  margin: 16px 0;
  padding: 14px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  overflow-x: auto;
  text-align: center;
}
.mermaid-fallback {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
}

/* Evidence Tags */
.tag {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid var(--border-strong);
  background: var(--surface-alt);
  color: var(--text-muted);
  white-space: nowrap;
}
.tag-verified { background: var(--good-bg); border-color: var(--good-border); color: var(--good-text); }
.tag-estimate { background: var(--accent-soft); border-color: var(--accent-border); color: var(--accent); }
.tag-assumption { background: var(--amber-bg); border-color: var(--amber-border); color: var(--amber-text); }
.tag-unverified, .tag-stale { background: var(--warn-bg); border-color: var(--warn-border); color: var(--warn-text); }

/* Interactive Checklists */
li.task-item { list-style: none; margin-left: -18px; }
li.task-item label { display: inline-flex; align-items: flex-start; gap: 8px; cursor: pointer; }
li.task-item input[type="checkbox"] { margin-top: 4px; accent-color: var(--accent-bright); width: 15px; height: 15px; }
li.task-item.is-done span { text-decoration: line-through; color: var(--text-subtle); }

/* Highlight search/filter */
.evidence-dim { opacity: 0.28; transition: opacity 0.15s ease; }
.evidence-hit { outline: 2px solid var(--accent-bright); outline-offset: 2px; border-radius: 4px; }
mark.search-hl { background: #FDE047; color: #0F172A; padding: 0 2px; border-radius: 2px; }

/* Financial What-If Simulator */
.sim-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
  margin: 16px 0 20px 0;
}
.sim-control {
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px 12px;
}
.sim-control-head {
  display: flex;
  justify-content: space-between;
  font-size: 12.5px;
  font-weight: 600;
  margin-bottom: 6px;
}
.sim-control-val { font-family: var(--font-mono); color: var(--accent); }
.sim-control input[type="range"] { width: 100%; accent-color: var(--accent-bright); cursor: pointer; }
.sim-actions { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px; }
.sim-chart-box {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px;
  margin: 14px 0 18px 0;
}
.sim-chart-box svg { width: 100%; height: auto; display: block; }

/* Portfolio Hub */
.hub-wrap { max-width: 1120px; margin: 0 auto; padding: 28px 24px 64px; }
.hub-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 12px;
  margin: 18px 0 22px 0;
}
.hub-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
  gap: 16px;
}
.hub-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 12px;
  box-shadow: var(--shadow-sm);
  transition: transform 0.14s ease, border-color 0.14s ease;
}
.hub-card:hover { transform: translateY(-2px); border-color: var(--accent-bright); }
.hub-card-title { font-size: 16px; font-weight: 700; margin: 4px 0; color: var(--text); }
.hub-card-path { font-family: var(--font-mono); font-size: 11.5px; color: var(--text-subtle); }
.hub-card-badges { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
.hub-card-actions { display: flex; flex-wrap: wrap; gap: 8px; padding-top: 10px; border-top: 1px solid var(--border); }

@media (max-width: 900px) {
  .menu-btn { display: inline-flex; }
  .shell { grid-template-columns: 1fr; }
  .sidebar {
    position: fixed;
    left: 0;
    top: var(--topbar-h);
    width: 280px;
    z-index: 50;
    transform: translateX(-105%);
    transition: transform 0.2s ease;
    box-shadow: var(--shadow-md);
  }
  .sidebar.open { transform: translateX(0); }
  .main { padding: 18px 16px 48px; }
  .doc-panel { padding: 18px 16px; }
  .search-wrap { width: 150px; }
}

@media print {
  .topbar, .sidebar, .toolbar-strip, .lint-drawer, .sim-actions, .sim-grid { display: none !important; }
  .shell { display: block; }
  .main { max-width: 100%; padding: 0; }
  .doc-panel { display: block !important; border: none; box-shadow: none; padding: 0; page-break-after: always; }
  body { background: #FFFFFF; color: #111317; font-size: 10pt; }
}
"""


WEB_JS = r"""
(function() {
  const CFG = window.__IDEAFORGE_DATA__ || {};
  const LABELS = CFG.labels || {};
  const STORAGE_THEME = 'ideaforge-theme';

  // Theme
  const savedTheme = localStorage.getItem(STORAGE_THEME) ||
    (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.setAttribute('data-theme', savedTheme);

  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem(STORAGE_THEME, next);
    });
  }

  // Mobile sidebar drawer
  const menuBtn = document.getElementById('menu-toggle');
  const sidebar = document.getElementById('sidebar');
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => sidebar.classList.toggle('open'));
  }

  // Lint drawer toggle
  const lintBtn = document.getElementById('lint-toggle');
  const lintDrawer = document.getElementById('lint-drawer');
  if (lintBtn && lintDrawer) {
    lintBtn.addEventListener('click', () => lintDrawer.classList.toggle('open'));
  }

  // Document switching & view mode (By Document vs Full View)
  const panels = Array.from(document.querySelectorAll('.doc-panel'));
  const navBtns = Array.from(document.querySelectorAll('[data-doc-target]'));
  const tocLinks = Array.from(document.querySelectorAll('[data-sec-doc]'));
  const btnTab = document.getElementById('mode-tab');
  const btnAll = document.getElementById('mode-all');
  let viewMode = panels.length > 2 ? 'tab' : 'all';
  let activeDocId = panels.length ? panels[0].id : null;

  function applyViewMode() {
    if (btnTab) btnTab.classList.toggle('active', viewMode === 'tab');
    if (btnAll) btnAll.classList.toggle('active', viewMode === 'all');
    panels.forEach(p => {
      if (viewMode === 'all') {
        p.classList.remove('hidden');
      } else {
        p.classList.toggle('hidden', p.id !== activeDocId);
      }
    });
    navBtns.forEach(b => b.classList.toggle('active', b.dataset.docTarget === activeDocId));
    tocLinks.forEach(a => {
      a.parentElement.style.display = (viewMode === 'all' || a.dataset.secDoc === activeDocId) ? '' : 'none';
    });
  }

  navBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      activeDocId = btn.dataset.docTarget;
      applyViewMode();
      const target = document.getElementById(activeDocId);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      if (sidebar) sidebar.classList.remove('open');
    });
  });
  if (btnTab) btnTab.addEventListener('click', () => { viewMode = 'tab'; applyViewMode(); });
  if (btnAll) btnAll.addEventListener('click', () => { viewMode = 'all'; applyViewMode(); });
  if (panels.length) applyViewMode();

  // Interactive Checklists (persisted in localStorage)
  const docKeyPrefix = 'ideaforge-cb:' + (CFG.projectId || 'doc') + ':';
  document.querySelectorAll('.task-cb').forEach(cb => {
    const k = docKeyPrefix + cb.dataset.taskKey;
    const saved = localStorage.getItem(k);
    if (saved !== null) {
      cb.checked = saved === '1';
      cb.closest('li').classList.toggle('is-done', cb.checked);
    }
    cb.addEventListener('change', () => {
      localStorage.setItem(k, cb.checked ? '1' : '0');
      cb.closest('li').classList.toggle('is-done', cb.checked);
    });
  });

  // Evidence Tag Filter
  const filterPills = Array.from(document.querySelectorAll('[data-ev-filter]'));
  filterPills.forEach(pill => {
    pill.addEventListener('click', () => {
      const tag = pill.dataset.evFilter;
      filterPills.forEach(p => p.classList.toggle('active', p === pill));
      const blocks = document.querySelectorAll('.doc-panel p, .doc-panel li, .doc-panel tr');
      if (tag === 'all') {
        blocks.forEach(b => b.classList.remove('evidence-dim', 'evidence-hit'));
        return;
      }
      if (viewMode === 'tab') { viewMode = 'all'; applyViewMode(); }
      let firstHit = null;
      blocks.forEach(b => {
        if (b.tagName === 'TR' && b.querySelector('th')) return;
        const match = b.querySelector('.tag-' + tag);
        b.classList.toggle('evidence-hit', !!match);
        b.classList.toggle('evidence-dim', !match);
        if (match && !firstHit) firstHit = b;
      });
      if (firstHit) firstHit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  // Instant Search ('/' shortcut)
  const searchInput = document.getElementById('search-input');
  document.addEventListener('keydown', e => {
    if (e.key === '/' && document.activeElement !== searchInput && !/INPUT|TEXTAREA/.test(document.activeElement.tagName)) {
      e.preventDefault();
      if (searchInput) searchInput.focus();
    } else if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      searchInput.blur();
    }
  });
  if (searchInput) {
    searchInput.addEventListener('input', () => {
      const q = searchInput.value.trim().toLowerCase();
      // Portfolio hub card filtering
      const hubCards = document.querySelectorAll('.hub-card');
      if (hubCards.length) {
        hubCards.forEach(c => {
          const ok = !q || c.textContent.toLowerCase().includes(q);
          c.style.display = ok ? '' : 'none';
        });
        return;
      }
      if (!q) {
        panels.forEach(p => p.querySelectorAll('p, li, tr').forEach(el => { el.style.display = ''; }));
        applyViewMode();
        return;
      }
      panels.forEach(p => {
        const hit = p.textContent.toLowerCase().includes(q);
        p.classList.toggle('hidden', !hit);
      });
    });
  }

  // Portfolio hub track filter pills
  document.querySelectorAll('[data-track-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      const tr = btn.dataset.trackFilter;
      document.querySelectorAll('[data-track-filter]').forEach(b => b.classList.toggle('active', b === btn));
      document.querySelectorAll('.hub-card').forEach(c => {
        c.style.display = (tr === 'all' || c.dataset.track === tr) ? '' : 'none';
      });
    });
  });

  // Interactive Financial What-If Simulator (mirrors model.py exact math)
  const simRoot = document.getElementById('sim-panel');
  if (simRoot && CFG.modelInputs) {
    const baseInputs = JSON.parse(JSON.stringify(CFG.modelInputs));
    const locale = CFG.locale || (String(baseInputs.currency || 'IDR').toUpperCase() === 'IDR' ? 'id' : 'en');
    const currency = baseInputs.currency || 'IDR';
    const isSaas = String(baseInputs.model_type || 'transactional').toLowerCase() === 'saas';
    const months = 12;

    const state = {
      price: Number(baseInputs.price || 0),
      volume: Number(isSaas ? (baseInputs.month1_new_customers ?? baseInputs.month1_units ?? 10) : (baseInputs.month1_units ?? 50)),
      vc: Number(baseInputs.unit_variable_cost || 0),
      fixed: Number(baseInputs.monthly_fixed_costs || 0),
      cac: Number(baseInputs.cac || 0),
      growth: Number(baseInputs.monthly_growth || 0.1),
      churn: Number(baseInputs.monthly_churn_rate || 0.05),
      repeat: Math.max(1, Number(baseInputs.repeat_orders_per_customer || 1)),
    };

    function fmtNum(v, dec = 0) {
      const n = Number(v || 0);
      const s = n.toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
      return locale === 'id' ? s.replace(/,/g, 'X').replace(/\./g, ',').replace(/X/g, '.') : s;
    }
    function fmtShort(v) {
      const av = Math.abs(v);
      if (av >= 1e9) return fmtNum(v / 1e9, 1) + (locale === 'id' ? 'M ' : 'B ') + currency;
      if (av >= 1e6) return fmtNum(v / 1e6, 1) + (locale === 'id' ? 'jt ' : 'M ') + currency;
      if (av >= 1e3) return fmtNum(v / 1e3, 0) + (locale === 'id' ? 'rb ' : 'k ') + currency;
      return fmtNum(v, 0) + ' ' + currency;
    }

    function runScenario(mult) {
      const price = state.price;
      const growth = state.growth * (mult.growth ?? 1);
      const costMult = mult.cost ?? 1;
      const vc = state.vc * costMult;
      const fixed = state.fixed * costMult;
      const capex = Number(baseInputs.capex || 0);
      const feeRate = Number(baseInputs.channel_fee_rate || 0);
      const taxRate = Number(baseInputs.tax_rate || 0);
      const taxProfRate = Number(baseInputs.tax_on_profit_rate || 0);
      const cac = state.cac;
      let cash = Number(baseInputs.starting_cash || 0) - capex;
      let breakeven = null;
      let exhausted = cash <= 0 ? 0 : null;
      let finalProfit = 0;
      const rows = [];

      if (isSaas) {
        let active = Number(baseInputs.starting_active_customers || 0);
        let newCust = state.volume * (mult.units ?? 1);
        const churn = Math.min(0.99, Math.max(0, state.churn * (mult.churn ?? 1)));
        for (let mo = 1; mo <= months; mo++) {
          active = Math.max(0, active - active * churn + newCust);
          const rev = active * price;
          const gp = rev - active * vc - rev * feeRate;
          const ebt = gp - fixed - newCust * cac;
          const tax = rev * taxRate + Math.max(0, ebt) * taxProfRate;
          const net = ebt - tax;
          cash += net;
          finalProfit = net;
          if (breakeven === null && net >= 0) breakeven = mo;
          if (exhausted === null && cash <= 0) exhausted = mo;
          rows.push({ mo, vol: Math.round(active), rev: Math.round(rev), net: Math.round(net), cash: Math.round(cash) });
          newCust *= (1 + growth);
        }
        const unitMargin = price * (1 - feeRate) - vc;
        const ltv = churn > 0 ? unitMargin / churn : null;
        return {
          rows, breakeven, exhausted, finalProfit,
          lowestCash: Math.min(...rows.map(r => r.cash)),
          endingCash: rows[rows.length - 1].cash,
          grossMarginPct: price > 0 ? (unitMargin / price) * 100 : 0,
          ltvCac: (cac > 0 && ltv !== null) ? ltv / cac : null,
          payback: (unitMargin > 0 && cac > 0) ? cac / unitMargin : null,
        };
      } else {
        let units = state.volume * (mult.units ?? 1);
        const repeat = Math.max(1, state.repeat);
        for (let mo = 1; mo <= months; mo++) {
          const rev = units * price;
          const gp = rev - units * vc - rev * feeRate;
          const acq = (units / repeat) * cac;
          const ebt = gp - fixed - acq;
          const tax = rev * taxRate + Math.max(0, ebt) * taxProfRate;
          const net = ebt - tax;
          cash += net;
          finalProfit = net;
          if (breakeven === null && net >= 0) breakeven = mo;
          if (exhausted === null && cash <= 0) exhausted = mo;
          rows.push({ mo, vol: Math.round(units), rev: Math.round(rev), net: Math.round(net), cash: Math.round(cash) });
          units *= (1 + growth);
        }
        const unitMargin = price * (1 - feeRate) - vc;
        const ltv = unitMargin * repeat;
        return {
          rows, breakeven, exhausted, finalProfit,
          lowestCash: Math.min(...rows.map(r => r.cash)),
          endingCash: rows[rows.length - 1].cash,
          grossMarginPct: price > 0 ? (unitMargin / price) * 100 : 0,
          ltvCac: cac > 0 ? ltv / cac : null,
          payback: (unitMargin > 0 && cac > 0) ? cac / (unitMargin * repeat) : null,
        };
      }
    }

    function renderSimChart(resMap) {
      const w = 720, h = 250, pl = 74, pr = 92, pt = 28, pb = 42;
      const pw = w - pl - pr, ph = h - pt - pb;
      const all = Object.values(resMap).flatMap(r => r.rows.map(x => x.cash)).concat([0]);
      const minV = Math.min(...all), maxV = Math.max(Math.max(...all), minV + 1);
      const xPos = idx => pl + (idx / (months - 1)) * pw;
      const yPos = v => pt + ph - ((v - minV) / (maxV - minV)) * ph;
      const colors = { optimistic: '#1B365D', base: '#2563EB', pessimistic: '#DC2626' };
      const labels = {
        optimistic: LABELS.scenario_opt || 'Optimistic',
        base: LABELS.scenario_base || 'Base',
        pessimistic: LABELS.scenario_pess || 'Pessimistic',
      };
      let svg = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg"><rect width="${w}" height="${h}" fill="#FFFFFF"/>`;
      for (let s = 0; s <= 4; s++) {
        const v = minV + (maxV - minV) * (s / 4);
        const y = yPos(v).toFixed(1);
        svg += `<line x1="${pl}" y1="${y}" x2="${pl + pw}" y2="${y}" stroke="#EEF2F6"/>`;
        svg += `<text x="${pl - 8}" y="${Number(y) + 3}" text-anchor="end" font-size="9.5" fill="#64748B" font-family="sans-serif">${fmtShort(v)}</text>`;
      }
      if (minV < 0 && maxV > 0) {
        const y0 = yPos(0).toFixed(1);
        svg += `<line x1="${pl}" y1="${y0}" x2="${pl + pw}" y2="${y0}" stroke="#64748B" stroke-dasharray="4,3"/>`;
      }
      let lxLegend = pl;
      ['optimistic', 'base', 'pessimistic'].forEach(key => {
        const r = resMap[key];
        if (!r) return;
        const pts = r.rows.map((row, idx) => `${xPos(idx).toFixed(1)},${yPos(row.cash).toFixed(1)}`).join(' ');
        const dash = key === 'pessimistic' ? ' stroke-dasharray="5,3"' : '';
        svg += `<polyline fill="none" stroke="${colors[key]}" stroke-width="2.4"${dash} points="${pts}"/>`;
        const last = r.rows[r.rows.length - 1];
        const cx = xPos(months - 1).toFixed(1), cy = yPos(last.cash).toFixed(1);
        svg += `<circle cx="${cx}" cy="${cy}" r="3.5" fill="${colors[key]}"/>`;
        svg += `<text x="${Number(cx) + 7}" y="${Number(cy) + 3}" font-size="9.5" font-weight="600" fill="${colors[key]}" font-family="sans-serif">${fmtShort(last.cash)}</text>`;
        svg += `<line x1="${lxLegend}" y1="${h - 12}" x2="${lxLegend + 18}" y2="${h - 12}" stroke="${colors[key]}" stroke-width="2.4"${dash}/>`;
        svg += `<text x="${lxLegend + 24}" y="${h - 9}" font-size="10" fill="#1E293B" font-family="sans-serif">${labels[key]}</text>`;
        lxLegend += 120;
      });
      for (let m = 1; m <= months; m += 2) {
        svg += `<text x="${xPos(m - 1).toFixed(1)}" y="${pt + ph + 15}" text-anchor="middle" font-size="9.5" fill="#64748B" font-family="sans-serif">M${m}</text>`;
      }
      svg += '</svg>';
      return svg;
    }

    function updateSim() {
      const mults = baseInputs.scenario_multipliers || {
        pessimistic: { units: 0.7, growth: 0.6, cost: 1.1, churn: 1.3 },
        base: { units: 1.0, growth: 1.0, cost: 1.0, churn: 1.0 },
        optimistic: { units: 1.3, growth: 1.3, cost: 0.95, churn: 0.8 },
      };
      const resMap = {
        pessimistic: runScenario(mults.pessimistic || { units: 0.7, growth: 0.6, cost: 1.1 }),
        base: runScenario(mults.base || { units: 1, growth: 1, cost: 1 }),
        optimistic: runScenario(mults.optimistic || { units: 1.3, growth: 1.3, cost: 0.95 }),
      };
      const base = resMap.base;
      const pess = resMap.pessimistic;
      const beTxt = base.breakeven ? `${LABELS.month_prefix || 'Month'} ${base.breakeven}` : (LABELS.not_reached || 'Not within 12 mo');
      const ltvTxt = base.ltvCac !== null ? `${base.ltvCac.toFixed(1)}x` : 'N/A';
      const pbTxt = base.payback !== null ? `${base.payback.toFixed(1)} mo` : 'N/A';
      const kpiHtml = `
        <div class="kpi-card ${base.breakeven ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.breakeven || 'Break-Even'}</div><div class="kpi-val">${beTxt}</div><div class="kpi-sub">Pess: ${pess.breakeven ? 'M' + pess.breakeven : '-'}</div></div>
        <div class="kpi-card ${base.endingCash > 0 ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.ending_cash || 'Month-12 Cash'}</div><div class="kpi-val">${fmtShort(base.endingCash)}</div><div class="kpi-sub">${LABELS.lowest_cash || 'Lowest'}: ${fmtShort(base.lowestCash)}</div></div>
        <div class="kpi-card ${base.grossMarginPct >= 40 ? 'good' : ''}"><div class="kpi-label">${LABELS.gross_margin || 'Margin'}</div><div class="kpi-val">${base.grossMarginPct.toFixed(1)}%</div><div class="kpi-sub">${LABELS.payback || 'Payback'}: ${pbTxt}</div></div>
        <div class="kpi-card ${(base.ltvCac || 0) >= 3 ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.ltv_cac || 'LTV / CAC'}</div><div class="kpi-val">${ltvTxt}</div><div class="kpi-sub">Pess M12: ${fmtShort(pess.endingCash)}</div></div>
      `;
      document.getElementById('sim-kpis').innerHTML = kpiHtml;
      document.getElementById('sim-chart').innerHTML = renderSimChart(resMap);
      const tbody = base.rows.map(r =>
        `<tr><td>M${r.mo}</td><td class="num">${fmtNum(r.vol)}</td><td class="num">${fmtNum(r.rev)}</td><td class="num">${fmtNum(r.net)}</td><td class="num"><strong>${fmtNum(r.cash)}</strong></td></tr>`
      ).join('');
      document.getElementById('sim-table-body').innerHTML = tbody;
    }

    function bindSlider(id, key, fmtFn) {
      const el = document.getElementById(id);
      const lbl = document.getElementById(id + '-val');
      if (!el) return;
      const sync = () => {
        state[key] = Number(el.value);
        if (lbl) lbl.textContent = fmtFn(state[key]);
        updateSim();
      };
      el.addEventListener('input', sync);
      if (lbl) lbl.textContent = fmtFn(state[key]);
    }

    bindSlider('sim-price', 'price', v => fmtNum(v) + ' ' + currency);
    bindSlider('sim-volume', 'volume', v => fmtNum(v));
    bindSlider('sim-vc', 'vc', v => fmtNum(v) + ' ' + currency);
    bindSlider('sim-fixed', 'fixed', v => fmtNum(v) + ' ' + currency);
    bindSlider('sim-cac', 'cac', v => fmtNum(v) + ' ' + currency);
    bindSlider('sim-growth', 'growth', v => (v * 100).toFixed(0) + '%');
    if (isSaas) bindSlider('sim-churn', 'churn', v => (v * 100).toFixed(1) + '%');
    else bindSlider('sim-repeat', 'repeat', v => v.toFixed(1) + 'x');

    const resetBtn = document.getElementById('sim-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        const defaults = {
          'sim-price': Number(baseInputs.price || 0),
          'sim-volume': Number(isSaas ? (baseInputs.month1_new_customers ?? baseInputs.month1_units ?? 10) : (baseInputs.month1_units ?? 50)),
          'sim-vc': Number(baseInputs.unit_variable_cost || 0),
          'sim-fixed': Number(baseInputs.monthly_fixed_costs || 0),
          'sim-cac': Number(baseInputs.cac || 0),
          'sim-growth': Number(baseInputs.monthly_growth || 0.1),
          'sim-churn': Number(baseInputs.monthly_churn_rate || 0.05),
          'sim-repeat': Math.max(1, Number(baseInputs.repeat_orders_per_customer || 1)),
        };
        Object.entries(defaults).forEach(([id, val]) => {
          const el = document.getElementById(id);
          if (el) { el.value = val; el.dispatchEvent(new Event('input')); }
        });
      });
    }

    const copyBtn = document.getElementById('sim-copy');
    if (copyBtn) {
      copyBtn.addEventListener('click', () => {
        const updated = JSON.parse(JSON.stringify(baseInputs));
        updated.price = state.price;
        if (isSaas) {
          updated.month1_new_customers = state.volume;
          updated.monthly_churn_rate = state.churn;
        } else {
          updated.month1_units = state.volume;
          updated.repeat_orders_per_customer = state.repeat;
        }
        updated.unit_variable_cost = state.vc;
        updated.monthly_fixed_costs = state.fixed;
        updated.cac = state.cac;
        updated.monthly_growth = state.growth;
        const jsonStr = JSON.stringify(updated, null, 2);
        if (navigator.clipboard) navigator.clipboard.writeText(jsonStr);
        const orig = copyBtn.textContent;
        copyBtn.textContent = LABELS.copied || 'Copied!';
        setTimeout(() => { copyBtn.textContent = orig; }, 1600);
      });
    }

    updateSim();
  }
})();
"""


def _build_simulator_panel(model_inputs: dict, lang: str) -> str:
    t = I18N[lang]
    currency = model_inputs.get("currency", "IDR")
    is_saas = str(model_inputs.get("model_type", "transactional")).lower() == "saas"
    price = float(model_inputs.get("price", 100000))
    vol = float(model_inputs.get("month1_new_customers", model_inputs.get("month1_units", 50)) if is_saas else model_inputs.get("month1_units", 50))
    vc = float(model_inputs.get("unit_variable_cost", 0))
    fixed = float(model_inputs.get("monthly_fixed_costs", 0))
    cac = float(model_inputs.get("cac", 0))
    growth = float(model_inputs.get("monthly_growth", 0.1))
    churn = float(model_inputs.get("monthly_churn_rate", 0.05))
    repeat = max(1.0, float(model_inputs.get("repeat_orders_per_customer", 1.0)))

    def _slider(sid: str, label: str, val: float, mn: float, mx: float, step: float) -> str:
        return (
            f'<div class="sim-control">'
            f'<div class="sim-control-head"><span>{html.escape(label)}</span><span class="sim-control-val" id="{sid}-val"></span></div>'
            f'<input id="{sid}" type="range" min="{mn}" max="{mx}" step="{step}" value="{val}">'
            f'</div>'
        )

    vol_label = "New Customers (M1)" if is_saas else "Month-1 Units"
    extra_slider = (
        _slider("sim-churn", "Monthly Churn Rate", churn, 0.0, 0.30, 0.005)
        if is_saas
        else _slider("sim-repeat", "Repeat Orders / Customer", repeat, 1.0, 6.0, 0.1)
    )
    controls = "".join(
        [
            _slider("sim-price", f"Price / ARPU ({currency})", price, max(1.0, round(price * 0.4)), max(10.0, round(price * 2.0)), max(1.0, round(price * 0.02))),
            _slider("sim-volume", vol_label, vol, max(1.0, round(vol * 0.2)), max(20.0, round(vol * 3.0)), 1.0),
            _slider("sim-vc", f"Unit Variable Cost ({currency})", vc, 0.0, max(10.0, round(max(vc, price * 0.5) * 2.0)), max(1.0, round(max(vc, 100.0) * 0.02))),
            _slider("sim-fixed", f"Monthly Fixed Costs ({currency})", fixed, 0.0, max(100.0, round(max(fixed, 1000.0) * 2.5)), max(1.0, round(max(fixed, 1000.0) * 0.02))),
            _slider("sim-cac", f"CAC ({currency})", cac, 0.0, max(10.0, round(max(cac, price * 0.5) * 3.0)), max(1.0, round(max(cac, 100.0) * 0.02))),
            _slider("sim-growth", "Monthly Growth Rate", growth, 0.0, 0.40, 0.01),
            extra_slider,
        ]
    )
    vol_col = "Active Cust." if is_saas else "Units"
    return (
        f'<section id="sim-panel" class="doc-panel">'
        f'<h1>{html.escape(t["simulator"])} ({ "SaaS" if is_saas else "Transactional" })</h1>'
        f'<p>{html.escape(t["sim_subtitle"])}</p>'
        f'<div class="sim-actions">'
        f'<button type="button" id="sim-reset" class="btn btn-sm">{html.escape(t["reset_sim"])}</button>'
        f'<button type="button" id="sim-copy" class="btn btn-sm btn-primary">{html.escape(t["copy_json"])}</button>'
        f'</div>'
        f'<div class="sim-grid">{controls}</div>'
        f'<div id="sim-kpis" class="kpi-grid"></div>'
        f'<div id="sim-chart" class="sim-chart-box"></div>'
        f'<div class="table-wrap"><table><thead><tr>'
        f'<th>Month</th><th class="num">{vol_col}</th><th class="num">Revenue ({html.escape(currency)})</th>'
        f'<th class="num">Net Profit ({html.escape(currency)})</th><th class="num">Cash ({html.escape(currency)})</th>'
        f'</tr></thead><tbody id="sim-table-body"></tbody></table></div>'
        f'</section>'
    )


def render_web_document(
    docs: list[dict],
    title: str,
    kicker: str,
    meta: str,
    lang: str = "id",
    model_inputs: dict | None = None,
    lint_info: dict | None = None,
    mermaid_js: str | None = None,
    hub_back_url: str | None = None,
    download_html_url: str | None = None,
    export_pdf_url: str | None = None,
    project_id: str = "report",
) -> str:
    """Compile one or more Markdown documents into a single self-contained Web GUI HTML string."""
    t = I18N[lang]
    has_mermaid = False
    rendered_panels: list[str] = []
    sidebar_docs: list[str] = []
    sidebar_sections: list[str] = []
    tag_counts = {"verified": 0, "estimate": 0, "assumption": 0, "unverified": 0, "stale": 0}

    for doc in docs:
        body_html, toc, doc_mermaid = export_pdf.md_to_html(doc["markdown"], doc["base_dir"], add_back_to_toc=False, lang=lang)
        has_mermaid = has_mermaid or doc_mermaid
        body_html = inline_local_assets(body_html, doc["base_dir"])
        body_html = make_interactive_checkboxes(body_html, doc["id"])
        # Wrap tables for horizontal responsiveness
        body_html = body_html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")

        for k in tag_counts:
            tag_counts[k] += len(re.findall(rf'class="tag tag-{k}"', body_html))

        rendered_panels.append(f'<article id="{doc["id"]}" class="doc-panel">{body_html}</article>')
        sidebar_docs.append(
            f'<li class="nav-item"><button type="button" class="nav-btn" data-doc-target="{doc["id"]}">'
            f'<span>{html.escape(doc["label"])}</span></button></li>'
        )
        for level, sec_title, sec_id in toc:
            if level == 2:
                sidebar_sections.append(
                    f'<li class="nav-item"><a class="nav-btn nav-sub" data-sec-doc="{doc["id"]}" href="#{sec_id}">'
                    f'{html.escape(sec_title)}</a></li>'
                )

    if model_inputs:
        rendered_panels.append(_build_simulator_panel(model_inputs, lang))
        sidebar_docs.append(
            f'<li class="nav-item"><button type="button" class="nav-btn" data-doc-target="sim-panel">'
            f'<span>&#9881; {html.escape(t["simulator"])}</span></button></li>'
        )

    # Evidence filter bar
    ev_pills = [f'<button type="button" class="filter-pill active" data-ev-filter="all">{html.escape(t["all_tags"])}</button>']
    for k, label in (("verified", "Verified"), ("estimate", "Estimate"), ("assumption", "Assumption"), ("unverified", "Unverified"), ("stale", "Stale")):
        if tag_counts[k] > 0:
            ev_pills.append(
                f'<button type="button" class="filter-pill" data-ev-filter="{k}">{label} ({tag_counts[k]})</button>'
            )

    lint_badge_html = ""
    lint_drawer_html = ""
    if lint_info:
        cls = "lint-pill has-fail" if lint_info["fails"] else ("lint-pill has-warn" if lint_info["warns"] else "lint-pill")
        lint_badge_html = (
            f'<button type="button" id="lint-toggle" class="{cls}">'
            f'{html.escape(t["quality_gates"])}: {lint_info["fails"]} FAIL · {lint_info["warns"]} WARN</button>'
        )
        rows_html = "".join(
            f'<div class="lint-row"><span class="tag tag-{"verified" if item["severity"]=="PASS" else ("assumption" if item["severity"]=="WARN" else "unverified")}">{item["severity"]}</span>'
            f'<span>{html.escape(item["message"])}</span></div>'
            for item in lint_info["items"]
        )
        lint_drawer_html = f'<div id="lint-drawer" class="lint-drawer">{rows_html}</div>'

    view_toggle_html = ""
    if len(rendered_panels) > 1:
        view_toggle_html = (
            '<div class="view-toggle">'
            f'<button type="button" id="mode-tab">{html.escape(t["tab_view"])}</button>'
            f'<button type="button" id="mode-all">{html.escape(t["all_view"])}</button>'
            '</div>'
        )

    back_html = (
        f'<a class="btn btn-sm" href="{html.escape(hub_back_url)}">&larr; {html.escape(t["back_hub"])}</a>'
        if hub_back_url
        else '<span class="brand-mark"><span class="brand-dot"></span>IdeaForge</span>'
    )
    dl_html_btn = (
        f'<a class="btn btn-sm" href="{html.escape(download_html_url)}">{html.escape(t["download_html"])}</a>'
        if download_html_url
        else ""
    )
    pdf_btn = (
        f'<a class="btn btn-sm btn-primary" href="{html.escape(export_pdf_url)}">{html.escape(t["export_pdf_btn"])}</a>'
        if export_pdf_url
        else f'<button type="button" class="btn btn-sm btn-primary" onclick="window.print()">{html.escape(t["print_pdf"])}</button>'
    )

    cfg_payload = {
        "projectId": project_id,
        "locale": lang,
        "labels": t,
        "modelInputs": model_inputs,
    }
    safe_json = json.dumps(cfg_payload).replace("</", "<\\/")
    mermaid_script = export_pdf.build_mermaid_script(mermaid_js) if has_mermaid else ""

    return f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} — IdeaForge Web</title>
<style>{WEB_CSS}</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-left">
    <button type="button" id="menu-toggle" class="btn btn-sm menu-btn" aria-label="Menu">&#9776;</button>
    {back_html}
    <span class="topbar-kicker">{html.escape(kicker)}</span>
    <span class="topbar-title">{html.escape(title)}</span>
  </div>
  <div class="topbar-right">
    <div class="search-wrap">
      <input id="search-input" class="search-input" type="search" placeholder="{html.escape(t['search_placeholder'])}" autocomplete="off">
    </div>
    {dl_html_btn}
    {pdf_btn}
    <button type="button" id="theme-toggle" class="btn btn-sm">{html.escape(t['theme_toggle'])}</button>
  </div>
</header>

<div class="shell">
  <aside id="sidebar" class="sidebar">
    {view_toggle_html}
    <div class="sidebar-section">
      <p class="sidebar-heading">{html.escape(t['documents'])}</p>
      <ul class="nav-list">{"".join(sidebar_docs)}</ul>
    </div>
    {f'<div class="sidebar-section"><p class="sidebar-heading">{html.escape(t["sections"])}</p><ul class="nav-list">{"".join(sidebar_sections)}</ul></div>' if sidebar_sections else ''}
  </aside>

  <main class="main">
    <section class="hero-card">
      <h1 class="hero-title">{html.escape(title)}</h1>
      <div class="hero-meta">
        <span>{html.escape(kicker)}</span>
        <span>&middot;</span>
        <span>{html.escape(meta)}</span>
        <span>&middot;</span>
        <span>{len(docs)} {html.escape(t['files_unit'])}</span>
      </div>
    </section>

    <div class="toolbar-strip">
      <div class="pill-group">
        <span class="pill-label">{html.escape(t['evidence_filter'])}:</span>
        {"".join(ev_pills)}
      </div>
      {lint_badge_html}
    </div>
    {lint_drawer_html}

    {"".join(rendered_panels)}
  </main>
</div>

<script>window.__IDEAFORGE_DATA__ = {safe_json};</script>
<script>{WEB_JS}</script>
{mermaid_script}
</body>
</html>
"""


def discover_workspace_items(base_dir: Path) -> list[dict]:
    """Discover all PRPs, PRDs, Quick Briefs, and sample reports in the workspace."""
    items: list[dict] = []

    def _scan_project_root(folder_name: str, track_group: str, default_mode: str) -> None:
        root_sub = base_dir / folder_name
        if not root_sub.is_dir():
            return
        for child in sorted(root_sub.iterdir(), reverse=True):
            if not child.is_dir() or child.name.startswith("."):
                continue
            mds = list(child.glob("*.md"))
            if not mds:
                continue
            title = child.name
            readme = child / "README.md"
            if readme.exists():
                for ln in readme.read_text(encoding="utf-8").splitlines():
                    if ln.strip().startswith("# "):
                        title = ln.strip()[2:].strip()
                        break
            lint_info = run_lint_summary(child)
            score, verdict = extract_scorecard_badge(child)
            has_sim = (child / "model" / "inputs.json").exists()
            items.append(
                {
                    "title": title,
                    "rel_path": str(child.relative_to(base_dir)),
                    "group": track_group,
                    "mode": default_mode,
                    "doc_count": len(mds),
                    "score": score,
                    "verdict": verdict,
                    "lint": lint_info,
                    "has_sim": has_sim,
                    "is_file": False,
                }
            )

    _scan_project_root("prps", "prp", "executive")
    _scan_project_root("prds", "prd", "prd")
    _scan_project_root("ideas", "idea", "executive")

    sample_md = base_dir / "examples" / "sample-report" / "sample-executive-report.md"
    if sample_md.is_file():
        items.append(
            {
                "title": "Sample Business Analysis Report",
                "rel_path": str(sample_md.relative_to(base_dir)),
                "group": "sample",
                "mode": "executive",
                "doc_count": 1,
                "score": "3.75",
                "verdict": "Go with conditions",
                "lint": None,
                "has_sim": (base_dir / ".agents/skills/financial-modeler/scripts/example_inputs.json").exists(),
                "is_file": True,
            }
        )
    return items


def render_portfolio_hub(base_dir: Path, lang: str = "id") -> str:
    """Render the interactive Portfolio Hub HTML page for --serve mode."""
    t = I18N[lang]
    items = discover_workspace_items(base_dir)
    counts = {
        "prp": sum(1 for x in items if x["group"] == "prp"),
        "prd": sum(1 for x in items if x["group"] == "prd"),
        "idea": sum(1 for x in items if x["group"] == "idea"),
        "sample": sum(1 for x in items if x["group"] == "sample"),
    }

    cards_html = []
    for it in items:
        q_path = urllib.parse.quote(it["rel_path"])
        view_url = f'/view?path={q_path}&mode={it["mode"]}'
        dl_url = f'/api/download-html?path={q_path}&mode={it["mode"]}'
        pdf_url = f'/api/export-pdf?path={q_path}&mode={it["mode"]}'
        badges = [f'<span class="tag tag-estimate">{it["group"].upper()}</span>']
        badges.append(f'<span class="tag">{it["doc_count"]} {html.escape(t["files_unit"])}</span>')
        if it["score"]:
            badges.append(f'<span class="tag tag-verified">{html.escape(t["score_label"])} {html.escape(it["score"])}/5</span>')
        if it["has_sim"]:
            badges.append('<span class="tag tag-estimate">What-If Sim</span>')
        if it["lint"]:
            l_cls = "tag-unverified" if it["lint"]["fails"] else ("tag-assumption" if it["lint"]["warns"] else "tag-verified")
            badges.append(f'<span class="tag {l_cls}">Lint: {it["lint"]["fails"]}F/{it["lint"]["warns"]}W</span>')

        verdict_line = f'<div class="kpi-sub">{html.escape(it["verdict"])}</div>' if it["verdict"] else ""
        cards_html.append(
            f'<div class="hub-card" data-track="{it["group"]}">'
            f'<div>'
            f'<div class="hub-card-path">{html.escape(it["rel_path"])}</div>'
            f'<div class="hub-card-title">{html.escape(it["title"])}</div>'
            f'{verdict_line}'
            f'<div class="hub-card-badges">{"".join(badges)}</div>'
            f'</div>'
            f'<div class="hub-card-actions">'
            f'<a class="btn btn-sm btn-primary" href="{view_url}">{html.escape(t["open_web"])}</a>'
            f'<a class="btn btn-sm" href="{dl_url}">{html.escape(t["download_html"])}</a>'
            f'<a class="btn btn-sm" href="{pdf_url}">PDF</a>'
            f'</div>'
            f'</div>'
        )

    body_grid = (
        f'<div class="hub-grid">{"".join(cards_html)}</div>'
        if cards_html
        else f'<div class="doc-panel"><p>{html.escape(t["empty_hub"])}</p></div>'
    )

    return f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t['hub_title'])}</title>
<style>{WEB_CSS}</style>
</head>
<body>
<header class="topbar">
  <div class="topbar-left">
    <span class="brand-mark"><span class="brand-dot"></span>IdeaForge</span>
    <span class="topbar-kicker">Web GUI</span>
    <span class="topbar-title">{html.escape(t['hub_title'])}</span>
  </div>
  <div class="topbar-right">
    <div class="search-wrap">
      <input id="search-input" class="search-input" type="search" placeholder="{html.escape(t['search_placeholder'])}" autocomplete="off">
    </div>
    <button type="button" id="theme-toggle" class="btn btn-sm">{html.escape(t['theme_toggle'])}</button>
  </div>
</header>

<main class="hub-wrap">
  <section class="hero-card">
    <h1 class="hero-title">{html.escape(t['hub_title'])}</h1>
    <p style="margin:0;color:var(--text-muted);">{html.escape(t['hub_subtitle'])}</p>
  </section>

  <div class="hub-stats">
    <div class="kpi-card"><div class="kpi-label">PRPs</div><div class="kpi-val">{counts['prp']}</div><div class="kpi-sub">prps/</div></div>
    <div class="kpi-card good"><div class="kpi-label">PRDs</div><div class="kpi-val">{counts['prd']}</div><div class="kpi-sub">prds/</div></div>
    <div class="kpi-card"><div class="kpi-label">Quick Briefs</div><div class="kpi-val">{counts['idea']}</div><div class="kpi-sub">ideas/</div></div>
    <div class="kpi-card"><div class="kpi-label">Samples</div><div class="kpi-val">{counts['sample']}</div><div class="kpi-sub">examples/</div></div>
  </div>

  <div class="toolbar-strip">
    <div class="pill-group">
      <button type="button" class="filter-pill active" data-track-filter="all">{html.escape(t['all_tags'])} ({len(items)})</button>
      <button type="button" class="filter-pill" data-track-filter="prp">PRP ({counts['prp']})</button>
      <button type="button" class="filter-pill" data-track-filter="prd">PRD ({counts['prd']})</button>
      <button type="button" class="filter-pill" data-track-filter="idea">Ideas ({counts['idea']})</button>
      <button type="button" class="filter-pill" data-track-filter="sample">Samples ({counts['sample']})</button>
    </div>
  </div>

  {body_grid}
</main>
<script>window.__IDEAFORGE_DATA__ = {json.dumps({"locale": lang, "labels": t})};</script>
<script>{WEB_JS}</script>
</body>
</html>
"""


def _resolve_safe_target(base_dir: Path, rel_path: str) -> Path:
    target = (base_dir / rel_path).resolve()
    if not target.is_relative_to(base_dir.resolve()):
        raise PermissionError("Path outside workspace is not allowed.")
    if not target.exists():
        raise FileNotFoundError(f"Target not found: {rel_path}")
    return target


def build_html_for_target(
    target: Path,
    mode: str = "executive",
    title: str | None = None,
    kicker: str | None = None,
    lang: str = "id",
    model_inputs_path: Path | None = None,
    mermaid_js: str | None = None,
    hub_back_url: str | None = None,
    download_html_url: str | None = None,
    export_pdf_url: str | None = None,
    base_dir: Path | None = None,
) -> tuple[str, str]:
    """Build interactive Web GUI HTML for either a single Markdown file or a project directory."""
    model_inputs = None
    lint_info = None

    if target.is_file():
        raw = target.read_text(encoding="utf-8")
        doc_title = title or target.stem.replace("-", " ").title()
        docs = [
            {
                "id": f"doc-1-{export_pdf.slugify(target.stem)}",
                "filename": target.name,
                "label": _friendly_doc_label(target),
                "title": doc_title,
                "markdown": raw,
                "base_dir": target.parent,
            }
        ]
        # Auto-attach example_inputs.json for sample-executive-report.md if no explicit override
        if model_inputs_path is None and target.name == "sample-executive-report.md" and base_dir:
            candidate = base_dir / ".agents/skills/financial-modeler/scripts/example_inputs.json"
            if candidate.is_file():
                model_inputs_path = candidate
        project_id = target.stem
        resolved_kicker = kicker or "Strategic Analysis Report"
    else:
        docs = load_project_documents(target, mode)
        doc_title = title or target.name.replace("-", " ").title()
        if model_inputs_path is None:
            candidate = target / "model" / "inputs.json"
            if candidate.is_file():
                model_inputs_path = candidate
        lint_info = run_lint_summary(target)
        project_id = target.name
        resolved_kicker = kicker or ("Product Requirements Document (PRD)" if mode == "prd" else "Strategic Analysis Report")

    if model_inputs_path and model_inputs_path.is_file():
        model_inputs = json.loads(model_inputs_path.read_text(encoding="utf-8"))

    meta = f"{'Date' if lang == 'en' else 'Tanggal'}: {date.today().isoformat()}"
    full_html = render_web_document(
        docs=docs,
        title=doc_title,
        kicker=resolved_kicker,
        meta=meta,
        lang=lang,
        model_inputs=model_inputs,
        lint_info=lint_info,
        mermaid_js=mermaid_js,
        hub_back_url=hub_back_url,
        download_html_url=download_html_url,
        export_pdf_url=export_pdf_url,
        project_id=project_id,
    )
    return full_html, doc_title


def create_server(base_dir: Path, host: str, port: int, lang: str = "id", mermaid_js: str | None = None):
    """Create a local stdlib HTTP server serving the live IdeaForge Portfolio Hub & Viewer."""
    base_dir = base_dir.resolve()

    class IdeaForgeHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            return  # Keep terminal output quiet unless needed

        def _send_bytes(self, data: bytes, content_type: str, status: int = 200, extra_headers: dict | None = None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            qs = urllib.parse.parse_qs(parsed.query)
            try:
                if parsed.path in ("/", "/index.html"):
                    page = render_portfolio_hub(base_dir, lang=lang).encode("utf-8")
                    self._send_bytes(page, "text/html; charset=utf-8")
                    return

                if parsed.path == "/view":
                    rel = qs.get("path", [""])[0]
                    mode = qs.get("mode", ["executive"])[0]
                    if mode not in ("executive", "technical", "full", "prd"):
                        mode = "executive"
                    target = _resolve_safe_target(base_dir, rel)
                    q_rel = urllib.parse.quote(rel)
                    page, _ = build_html_for_target(
                        target=target,
                        mode=mode,
                        lang=lang,
                        mermaid_js=mermaid_js,
                        hub_back_url="/",
                        download_html_url=f"/api/download-html?path={q_rel}&mode={mode}",
                        export_pdf_url=f"/api/export-pdf?path={q_rel}&mode={mode}",
                        base_dir=base_dir,
                    )
                    self._send_bytes(page.encode("utf-8"), "text/html; charset=utf-8")
                    return

                if parsed.path == "/api/download-html":
                    rel = qs.get("path", [""])[0]
                    mode = qs.get("mode", ["executive"])[0]
                    target = _resolve_safe_target(base_dir, rel)
                    page, doc_title = build_html_for_target(
                        target=target,
                        mode=mode,
                        lang=lang,
                        mermaid_js=mermaid_js,
                        base_dir=base_dir,
                    )
                    fname = f"{export_pdf.slugify(doc_title)}.html"
                    self._send_bytes(
                        page.encode("utf-8"),
                        "text/html; charset=utf-8",
                        extra_headers={"Content-Disposition": f'attachment; filename="{fname}"'},
                    )
                    return

                if parsed.path == "/api/export-pdf":
                    rel = qs.get("path", [""])[0]
                    mode = qs.get("mode", ["executive"])[0]
                    target = _resolve_safe_target(base_dir, rel)
                    with tempfile.TemporaryDirectory() as tmp:
                        out_pdf = Path(tmp) / "export.pdf"
                        cmd = [sys.executable, str(SCRIPT_DIR / "export_pdf.py")]
                        if target.is_file():
                            cmd.extend(["--input", str(target), "--toc"])
                        else:
                            cmd.extend(["--project", str(target), "--mode", mode])
                        cmd.extend(["--lang", lang, "--output", str(out_pdf)])
                        res = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
                        if res.returncode != 0 or not out_pdf.exists():
                            self._send_bytes(f"PDF export failed:\n{res.stderr}".encode("utf-8"), "text/plain; charset=utf-8", status=500)
                            return
                        pdf_bytes = out_pdf.read_bytes()
                    fname = f"{export_pdf.slugify(target.stem)}.pdf"
                    self._send_bytes(
                        pdf_bytes,
                        "application/pdf",
                        extra_headers={"Content-Disposition": f'attachment; filename="{fname}"'},
                    )
                    return

                self._send_bytes(b"Not Found", "text/plain; charset=utf-8", status=404)
            except PermissionError as e:
                self._send_bytes(str(e).encode("utf-8"), "text/plain; charset=utf-8", status=403)
            except FileNotFoundError as e:
                self._send_bytes(str(e).encode("utf-8"), "text/plain; charset=utf-8", status=404)
            except Exception as e:
                self._send_bytes(f"Server error: {e}".encode("utf-8"), "text/plain; charset=utf-8", status=500)

    class ReusableTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    return ReusableTCPServer((host, port), IdeaForgeHandler)


def main():
    ap = argparse.ArgumentParser(description="Export IdeaForge analysis to interactive Web GUI HTML or serve live Portfolio Hub.")
    ap.add_argument("--input", help="Path to a single Markdown file")
    ap.add_argument("--project", help="Path to a prps/<slug>, prds/<slug>, or ideas/<slug> folder")
    ap.add_argument("--output", help="Output static .html path (required when not using --serve)")
    ap.add_argument("--title", help="Custom document title")
    ap.add_argument("--kicker", default=None, help="Top category label")
    ap.add_argument("--mode", choices=["executive", "technical", "full", "prd"], default="executive", help="Section profile for --project")
    ap.add_argument("--model-inputs", help="Optional path to financial model inputs.json for interactive What-If Simulator")
    ap.add_argument("--mermaid-js", default=os.environ.get("MERMAID_JS"), help="Optional local path to mermaid.min.js")
    ap.add_argument("--lang", choices=["id", "en"], default="id", help="UI language (id or en)")
    ap.add_argument("--serve", action="store_true", help="Launch local interactive Portfolio Hub & Web Viewer server")
    ap.add_argument("--host", default="127.0.0.1", help="Bind host for --serve (default: 127.0.0.1)")
    ap.add_argument("--port", type=int, default=8765, help="Port for --serve (default: 8765)")
    ap.add_argument("--base-dir", default=".", help="Workspace root directory for --serve")
    ap.add_argument("--no-open", action="store_true", help="Do not auto-open browser in --serve mode")
    args = ap.parse_args()

    if args.serve:
        base_dir = Path(args.base_dir).resolve()
        server = create_server(base_dir, args.host, args.port, lang=args.lang, mermaid_js=args.mermaid_js)
        actual_port = server.server_address[1]
        url = f"http://{args.host}:{actual_port}/"
        print(f"IdeaForge Web GUI running at {url} (workspace: {base_dir})")
        print("Press Ctrl+C to stop.")
        if not args.no_open:
            try:
                webbrowser.open(url)
            except Exception:
                pass
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down IdeaForge Web GUI.")
        finally:
            server.server_close()
        return

    if not args.input and not args.project:
        ap.error("Provide --input, --project, or --serve.")
    if not args.output:
        ap.error("Provide --output when exporting static HTML.")

    target = Path(args.input or args.project).resolve()
    model_inputs_path = Path(args.model_inputs).resolve() if args.model_inputs else None
    full_html, _ = build_html_for_target(
        target=target,
        mode=args.mode,
        title=args.title,
        kicker=args.kicker,
        lang=args.lang,
        model_inputs_path=model_inputs_path,
        mermaid_js=args.mermaid_js,
        base_dir=Path(args.base_dir).resolve(),
    )
    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(full_html, encoding="utf-8")
    print(f"Web GUI generated: {out_path} ({out_path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
