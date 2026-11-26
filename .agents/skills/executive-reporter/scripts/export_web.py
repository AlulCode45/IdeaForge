#!/usr/bin/env python3
"""Export IdeaForge Markdown reports, PRDs, or PRPs to an interactive Web GUI
(self-contained static HTML) or serve a live local Portfolio Hub web dashboard.

Pure Python 3 stdlib, zero external pip or npm dependencies.

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


# Consistent 16px Lucide-style inline SVG icon set (stroke-width 1.5)
BRAND_MARK_SVG = (
    '<svg class="brand-svg" width="22" height="22" viewBox="0 0 76 76" fill="none" aria-hidden="true">'
    '<rect width="76" height="76" rx="8" fill="var(--surface-2)" stroke="var(--line)" stroke-width="2"/>'
    '<path d="M16 51H60L55 61H21L16 51Z" fill="var(--text-muted)"/>'
    '<path d="M12 41H64L57 50H19L12 41Z" fill="var(--primary)"/>'
    '<path d="M38 11L44 23L56 26L44 29L38 41L32 29L20 26L32 23L38 11Z" fill="var(--accent)"/>'
    "</svg>"
)

SUN_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41'
    'M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41"/></svg>'
)

MOON_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>'
)

SEARCH_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>'
)

DOWNLOAD_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/>'
    '<line x1="12" x2="12" y1="15" y2="3"/></svg>'
)

FILE_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 9H8"/><path d="M16 13H8"/><path d="M16 17H8"/></svg>'
)

PANEL_LEFT_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="M9 3v18"/></svg>'
)

LAYERS_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/>'
    '<path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>'
)

FOLDER_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z"/></svg>'
)

FILE_CHECK_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>'
    '<path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="m9 15 2 2 4-4"/></svg>'
)

LIGHTBULB_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
    '<path d="M9 18h6"/><path d="M10 22h4"/></svg>'
)

BOOK_OPEN_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'
)

TABLE_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>'
)

GRID_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/>'
    '<rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/></svg>'
)

SLIDERS_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<line x1="21" x2="14" y1="4" y2="4"/><line x1="10" x2="3" y1="4" y2="4"/>'
    '<line x1="21" x2="12" y1="12" y2="12"/><line x1="8" x2="3" y1="12" y2="12"/>'
    '<line x1="21" x2="16" y1="20" y2="20"/><line x1="12" x2="3" y1="20" y2="20"/>'
    '<line x1="14" x2="14" y1="2" y2="6"/><line x1="8" x2="8" y1="10" y2="14"/><line x1="16" x2="16" y1="18" y2="22"/></svg>'
)

ARROW_UP_DOWN_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>'
)

MENU_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<line x1="4" x2="20" y1="12" y2="12"/><line x1="4" x2="20" y1="6" y2="6"/><line x1="4" x2="20" y1="18" y2="18"/></svg>'
)

X_SVG = (
    '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" '
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
    '<path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>'
)

I18N = {
    "id": {
        "hub_title": "IdeaForge Portfolio Hub",
        "hub_subtitle": "Direktori dokumen analisa strategis, PRD, dan proyeksi finansial.",
        "back_hub": "Portfolio Hub",
        "search_placeholder": "Cari... (/)",
        "documents": "Dokumen",
        "sections": "Daftar Bagian",
        "all_view": "Semua",
        "tab_view": "Per Bab",
        "simulator": "Simulator Finansial",
        "quality_gates": "Audit Kualitas",
        "print_pdf": "Cetak / PDF",
        "download_html": "Simpan HTML",
        "light_label": "Terang",
        "dark_label": "Gelap",
        "evidence_filter": "Saring Bukti",
        "all_tags": "Semua",
        "reset_sim": "Reset",
        "copy_json": "Salin inputs.json",
        "copied": "Tersalin",
        "no_results": "Tidak ada bagian yang cocok dengan pencarian Anda.",
        "reset_search": "Hapus pencarian",
        "open_web": "Buka",
        "export_pdf_btn": "Unduh PDF",
        "empty_hub": "Belum ada proyek di prps/, prds/, atau ideas/. Jalankan scripts/init_project.py untuk membuat proyek pertama.",
        "files_unit": "dokumen",
        "score_label": "Skor",
        "breakeven": "Break-Even (Dasar)",
        "ending_cash": "Kas Bulan 12",
        "lowest_cash": "Kas Terendah",
        "gross_margin": "Margin Kontribusi",
        "ltv_cac": "LTV / CAC",
        "payback": "Payback CAC",
        "month_prefix": "Bulan",
        "not_reached": "Belum tercapai",
        "scenario_pess": "Pesimis",
        "scenario_base": "Dasar",
        "scenario_opt": "Optimis",
        "sim_subtitle": "Ubah asumsi di panel kiri untuk melihat dampak langsung ke arus kas 12 bulan, titik impas, dan unit economics.",
        "col_project": "Dokumen",
        "col_track": "Tipe",
        "col_score": "Skor",
        "col_decision": "Keputusan",
        "col_audit": "Audit",
        "col_actions": "Aksi",
        "params_heading": "Parameter Asumsi",
        "monthly_table": "Rincian Bulanan (Skenario Dasar)",
        "tab_ideas": "Ide",
        "tab_samples": "Contoh",
        "search_hub_placeholder": "Cari dokumen",
        "sort_label": "Urutkan",
        "sort_newest": "Terbaru",
        "sort_score": "Skor tertinggi",
        "sort_name": "Nama",
        "decision_filter_label": "Keputusan",
        "decision_all": "Semua keputusan",
        "dec_go": "Go",
        "dec_conditional": "Go dengan syarat",
        "dec_nogo": "No-go",
        "dec_pending": "Belum dinilai",
        "not_audited": "Belum diaudit",
        "audit_pass": "Lolos",
        "no_score": "Belum ada skor",
        "sim_badge": "Simulasi",
        "sim_tooltip": "Dilengkapi simulator finansial What-If interaktif",
        "stat_total": "Total Dokumen",
        "stat_avg_score": "Rata-rata Skor",
        "stat_decisions": "Ringkasan Keputusan",
        "stat_updated": "Pembaruan Terakhir",
        "reset_filters": "Atur ulang filter",
        "empty_prd": "Belum ada dokumen PRD. Jalankan skill untuk membuat dokumen pertama.",
        "empty_prp": "Belum ada dokumen PRP. Jalankan skill untuk membuat dokumen pertama.",
        "empty_idea": "Belum ada catatan ide. Jalankan skill untuk mencatat ide pertama.",
        "empty_sample": "Tidak ada dokumen contoh yang tersedia.",
        "empty_filtered": "Tidak ada dokumen yang sesuai dengan filter atau pencarian Anda.",
    },
    "en": {
        "hub_title": "IdeaForge Portfolio Hub",
        "hub_subtitle": "Directory of strategic analyses, PRDs, and financial models.",
        "back_hub": "Portfolio Hub",
        "search_placeholder": "Search... (/)",
        "documents": "Documents",
        "sections": "On This Page",
        "all_view": "Full",
        "tab_view": "By Doc",
        "simulator": "Financial Simulator",
        "quality_gates": "Quality Audit",
        "print_pdf": "Print / PDF",
        "download_html": "Save HTML",
        "light_label": "Light",
        "dark_label": "Dark",
        "evidence_filter": "Evidence",
        "all_tags": "All",
        "reset_sim": "Reset",
        "copy_json": "Copy inputs.json",
        "copied": "Copied",
        "no_results": "No sections matched your search query.",
        "reset_search": "Clear search",
        "open_web": "Open",
        "export_pdf_btn": "Download PDF",
        "empty_hub": "No projects found in prps/, prds/, or ideas/ yet. Run scripts/init_project.py to create your first project.",
        "files_unit": "docs",
        "score_label": "Score",
        "breakeven": "Break-Even (Base)",
        "ending_cash": "Month-12 Cash",
        "lowest_cash": "Lowest Cash",
        "gross_margin": "Contribution Margin",
        "ltv_cac": "LTV / CAC",
        "payback": "CAC Payback",
        "month_prefix": "Month",
        "not_reached": "Not within 12 mo",
        "scenario_pess": "Pessimistic",
        "scenario_base": "Base",
        "scenario_opt": "Optimistic",
        "sim_subtitle": "Adjust assumptions on the left to inspect real-time effects on 12-month cash flow, break-even, and unit economics.",
        "col_project": "Document",
        "col_track": "Type",
        "col_score": "Score",
        "col_decision": "Decision",
        "col_audit": "Audit",
        "col_actions": "Actions",
        "params_heading": "Assumptions",
        "monthly_table": "Monthly Breakdown (Base Scenario)",
        "tab_ideas": "Ideas",
        "tab_samples": "Samples",
        "search_hub_placeholder": "Search documents",
        "sort_label": "Sort",
        "sort_newest": "Newest",
        "sort_score": "Highest score",
        "sort_name": "Name",
        "decision_filter_label": "Decision",
        "decision_all": "All decisions",
        "dec_go": "Go",
        "dec_conditional": "Conditional Go",
        "dec_nogo": "No-go",
        "dec_pending": "Pending",
        "not_audited": "Not audited",
        "audit_pass": "Passed",
        "no_score": "No score",
        "sim_badge": "Simulation",
        "sim_tooltip": "Includes interactive What-If financial simulator",
        "stat_total": "Total Documents",
        "stat_avg_score": "Average Score",
        "stat_decisions": "Decisions",
        "stat_updated": "Last Updated",
        "reset_filters": "Reset filters",
        "empty_prd": "No PRD documents yet. Run the prd-writer skill to create your first PRD.",
        "empty_prp": "No PRP documents yet. Run the prp-writer skill to create your first PRP.",
        "empty_idea": "No idea notes yet. Run the ideation skill to capture your first note.",
        "empty_sample": "No sample documents available.",
        "empty_filtered": "No documents match your active filter or search query.",
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
                cap = f"<figcaption>{alt}</figcaption>" if alt else ""
                return f'<figure class="svg-figure">{svg_text}{cap}</figure>'
            mime, _ = mimetypes.guess_type(str(local_path))
            if mime and mime.startswith("image/"):
                b64 = base64.b64encode(local_path.read_bytes()).decode("ascii")
                return f'<figure class="img-figure"><img src="data:{mime};base64,{b64}" alt="{alt}"></figure>'
        return match.group(0)

    return img_re.sub(_replace, html_body)


def make_interactive_checkboxes(html_body: str, doc_id: str) -> str:
    """Turn static unicode checkboxes from md_to_html into accessible interactive checkboxes."""
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
        return "Overview"
    cleaned = re.sub(r"^\d+-", "", stem).replace("-", " ").replace("_", " ").strip()
    prefix_m = re.match(r"^(\d+)-", stem)
    title = cleaned.title() if cleaned else stem
    return f"{prefix_m.group(1)} {title}" if prefix_m else title


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


# Institutional Editorial design tokens (Light & Dark, WCAG AA verified)
WEB_CSS = r"""
:root {
  --bg: #F6F4EF;
  --surface: #FFFFFF;
  --surface-2: #F3F0EA;
  --line: #DDD8CE;
  --line-soft: #ECE9E2;
  --text: #1B1F24;
  --text-muted: #5B6470;
  --primary: #12263F;
  --primary-fg: #FFFFFF;
  --accent: #B5541C;
  --go: #1E6B4A;
  --go-bg: #E3F0E9;
  --conditional: #8A5A00;
  --conditional-bg: #F6EBD3;
  --nogo: #9B2C2C;
  --nogo-bg: #F6E0E0;
  --pending: #4B5563;
  --pending-bg: #E8EAED;
  --overlay-bg: rgba(17, 24, 39, 0.45);

  /* Semantic aliases for document viewer components */
  --canvas: var(--bg);
  --sheet: var(--surface);
  --subtle-surface: var(--surface-2);
  --rule: var(--line);
  --rule-strong: var(--line);
  --ink: var(--text);
  --ink-muted: var(--text-muted);
  --ink-subtle: var(--text-muted);
  --link: var(--primary);
  --brand-spark: var(--accent);
  --focus-ring: var(--accent);
  --good-bg: var(--go-bg);
  --good-fg: var(--go);
  --good-rule: var(--line);
  --warn-bg: var(--nogo-bg);
  --warn-fg: var(--nogo);
  --warn-rule: var(--line);
  --amber-bg: var(--conditional-bg);
  --amber-fg: var(--conditional);
  --amber-rule: var(--line);
  --info-bg: var(--surface-2);
  --info-fg: var(--primary);
  --info-rule: var(--line);

  --font-serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "JetBrains Mono", "SF Mono", Menlo, monospace;

  /* 4px spacing scale */
  --sp-1: 4px;
  --sp-2: 8px;
  --sp-3: 12px;
  --sp-4: 16px;
  --sp-6: 24px;
  --sp-8: 32px;
  --sp-12: 48px;

  --topbar-h: 56px;
  --rail-w: 256px;
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;
  --shadow-float: 0 4px 12px rgba(0, 0, 0, 0.08);
}

[data-theme="dark"] {
  --bg: #0E141B;
  --surface: #151D27;
  --surface-2: #111922;
  --line: #263241;
  --line-soft: #1B2531;
  --text: #E7EAEE;
  --text-muted: #9AA5B1;
  --primary: #8FB3E0;
  --primary-fg: #0E141B;
  --accent: #E08A4F;
  --go: #74D4A7;
  --go-bg: #132A22;
  --conditional: #F2B84B;
  --conditional-bg: #2A2010;
  --nogo: #F08A8A;
  --nogo-bg: #2D171A;
  --pending: #A5B0BC;
  --pending-bg: #1E2733;
  --overlay-bg: rgba(0, 0, 0, 0.6);
}

*, *::before, *::after { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}

/* Accessible focus ring (2px --accent offset 2px) */
:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { transition: none !important; animation: none !important; }
}

.skip-link {
  position: absolute;
  left: -9999px;
  top: 8px;
  padding: 8px 14px;
  background: var(--primary);
  color: var(--primary-fg);
  font-size: 13px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  z-index: 100;
}
.skip-link:focus { left: 12px; }

/* Minimal 56px Masthead (no shadow) */
.topbar {
  position: sticky;
  top: 0;
  z-index: 40;
  height: var(--topbar-h);
  background: var(--surface);
  border-bottom: 1px solid var(--line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-6);
  gap: var(--sp-3);
}
.topbar-left, .topbar-right {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
  min-width: 0;
}
.brand-link {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
  font-size: 16px;
  letter-spacing: -0.01em;
  white-space: nowrap;
}
.brand-link:hover { color: var(--primary); }
.crumb-sep { color: var(--line); user-select: none; }
.topbar-doc-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-box {
  position: relative;
  display: flex;
  align-items: center;
  width: 240px;
}
.search-icon {
  position: absolute;
  left: var(--sp-3);
  color: var(--text-muted);
  pointer-events: none;
  display: inline-flex;
}
.search-input {
  width: 100%;
  height: 34px;
  padding: 0 36px 0 34px;
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--bg);
  color: var(--text);
  font-size: 13px;
  font-family: inherit;
  transition: border-color 140ms ease, background 140ms ease;
}
.search-input:focus { border-color: var(--accent); background: var(--surface); }
.search-input::placeholder { color: var(--text-muted); }
.kbd-hint {
  position: absolute;
  right: var(--sp-2);
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1;
  padding: 3px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text-muted);
  pointer-events: none;
}
.search-toggle-btn { display: none; }

/* Buttons & Theme Segmented Control */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--sp-2);
  height: 32px;
  padding: 0 var(--sp-3);
  border-radius: var(--radius-md);
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
  white-space: nowrap;
  transition: background 140ms ease, border-color 140ms ease;
}
.btn:hover { background: var(--surface-2); }
.btn-primary {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-fg);
  font-weight: 600;
}
.btn-primary:hover { opacity: 0.92; background: var(--primary); }
.btn-ghost { border-color: transparent; background: transparent; }
.btn-ghost:hover { background: var(--surface-2); }

.theme-switch {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--bg);
}
.theme-opt {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 var(--sp-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease;
}
.theme-opt:hover { color: var(--text); }
.theme-opt[aria-pressed="true"] {
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
}

.menu-btn { display: none; }

/* Workspace Layout */
.workspace {
  display: grid;
  grid-template-columns: var(--rail-w) minmax(0, 1fr);
  max-width: 1320px;
  margin: 0 auto;
  min-height: calc(100vh - var(--topbar-h));
}

/* Quiet Editorial Rail */
.rail {
  position: sticky;
  top: var(--topbar-h);
  height: calc(100vh - var(--topbar-h));
  overflow-y: auto;
  padding: 24px 16px 28px 20px;
  border-right: 1px solid var(--rule);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 20px;
}
.rail-group { margin-bottom: 20px; }
.rail-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--ink-subtle);
  margin: 0 0 8px 8px;
}
.rail-list { list-style: none; margin: 0; padding: 0; }
.rail-list li { margin-bottom: 2px; }
.rail-link {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 9px;
  border: 0;
  border-left: 2px solid transparent;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  background: transparent;
  color: var(--ink-muted);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 500;
  text-align: left;
  text-decoration: none;
  cursor: pointer;
}
.rail-link:hover { color: var(--ink); background: var(--subtle-surface); }
.rail-link.active {
  color: var(--ink);
  font-weight: 600;
  border-left-color: var(--brand-spark);
  background: var(--subtle-surface);
}
.rail-sub {
  padding-left: 16px;
  font-size: 13px;
  font-weight: 400;
}
.seg-control {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2px;
  padding: 2px;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--subtle-surface);
  margin-bottom: 18px;
}
.seg-control button {
  height: 30px;
  border: 0;
  border-radius: 3px;
  background: transparent;
  color: var(--ink-subtle);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 500;
  cursor: pointer;
}
.seg-control button.active {
  background: var(--sheet);
  color: var(--ink);
  font-weight: 600;
}

.rail-footer {
  padding-top: 14px;
  border-top: 1px solid var(--rule);
}
.audit-trigger {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
  background: var(--sheet);
  color: var(--ink);
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
}
.audit-trigger:hover { background: var(--subtle-surface); }
.audit-count { font-family: var(--font-mono); font-size: 12px; }
.audit-ok { color: var(--good-fg); }
.audit-warn { color: var(--amber-fg); }
.audit-fail { color: var(--warn-fg); }

/* Editorial Document Canvas */
.content-stage {
  padding: 28px 36px 72px;
  min-width: 0;
}
.sheet {
  max-width: 840px;
  margin: 0 auto;
  background: var(--sheet);
  border: 1px solid var(--rule);
  border-radius: var(--radius-md);
  padding: 36px 44px 48px;
}
.doc-masthead {
  padding-bottom: 18px;
  margin-bottom: 24px;
  border-bottom: 1px solid var(--rule);
}
.doc-category {
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: var(--accent);
  margin: 0 0 6px 0;
}
.doc-headline {
  font-family: var(--font-serif);
  font-size: 30px;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: -0.015em;
  color: var(--ink);
  margin: 0 0 10px 0;
}
.doc-meta-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  font-size: 13px;
  color: var(--ink-subtle);
}

/* Evidence Filter Inline Strip */
.evidence-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--rule);
}
.evidence-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--ink-subtle);
  margin-right: 4px;
}
.ev-btn {
  height: 28px;
  padding: 0 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--rule);
  background: transparent;
  color: var(--ink-muted);
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
}
.ev-btn:hover { background: var(--subtle-surface); color: var(--ink); }
.ev-btn.active {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-fg);
  font-weight: 600;
}

/* Audit Findings Panel */
.lint-drawer {
  display: none;
  margin: 0 0 24px 0;
  padding: 14px 16px;
  border: 1px solid var(--rule-strong);
  border-radius: var(--radius-sm);
  background: var(--canvas);
  font-size: 13px;
}
.lint-drawer.open { display: block; }
.lint-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid var(--rule);
}
.lint-row:last-child { border-bottom: none; }

/* Document Prose */
.doc-panel { margin-bottom: 36px; }
.doc-panel:last-child { margin-bottom: 0; }
.doc-panel.hidden { display: none; }
.doc-panel + .doc-panel:not(.hidden) {
  padding-top: 32px;
  border-top: 1px solid var(--rule);
}
.doc-panel h1 {
  font-family: var(--font-serif);
  font-size: 23px;
  font-weight: 700;
  line-height: 1.28;
  color: var(--ink);
  margin: 0 0 14px 0;
}
.doc-panel h2 {
  font-family: var(--font-serif);
  font-size: 19px;
  font-weight: 700;
  line-height: 1.32;
  color: var(--ink);
  margin: 28px 0 10px 0;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--rule);
}
.doc-panel h3 {
  font-size: 15.5px;
  font-weight: 700;
  color: var(--ink);
  margin: 22px 0 8px 0;
}
.doc-panel h4 {
  font-size: 14px;
  font-weight: 600;
  color: var(--ink-muted);
  margin: 16px 0 6px 0;
}
.doc-panel p { margin: 0 0 13px 0; color: var(--ink); }
.doc-panel ul, .doc-panel ol { margin: 0 0 14px 0; padding-left: 22px; }
.doc-panel li { margin-bottom: 6px; }
.doc-panel a { color: var(--link); text-decoration: underline; text-underline-offset: 2px; }
.doc-panel a:hover { color: var(--accent); }
.doc-panel hr { border: 0; border-top: 1px solid var(--rule); margin: 24px 0; }

/* Editorial Recommendation Note */
.callout-rec {
  background: var(--subtle-surface);
  border: 1px solid var(--rule-strong);
  padding: 14px 18px;
  border-radius: var(--radius-sm);
  margin: 16px 0 20px 0;
  font-size: 14.5px;
}

/* Hairline Editorial Metric Strip (replaces boxy stat cards) */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  border-top: 1px solid var(--rule-strong);
  border-bottom: 1px solid var(--rule-strong);
  margin: 18px 0 24px 0;
}
.kpi-card {
  padding: 14px 16px;
  border-right: 1px solid var(--rule);
}
.kpi-card:last-child { border-right: none; }
.kpi-label {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink-subtle);
  margin-bottom: 4px;
}
.kpi-val {
  font-size: 18px;
  font-weight: 700;
  color: var(--ink);
  font-variant-numeric: tabular-nums;
  line-height: 1.25;
}
.kpi-card.good .kpi-val { color: var(--good-fg); }
.kpi-card.warn .kpi-val { color: var(--warn-fg); }
.kpi-sub { font-size: 12px; color: var(--ink-subtle); margin-top: 3px; }

blockquote {
  margin: 16px 0;
  padding: 10px 16px;
  border-left: 2px solid var(--rule-strong);
  color: var(--ink-muted);
  font-size: 14px;
}
blockquote.callout-warn {
  background: var(--warn-bg);
  border-left: 3px solid var(--warn-fg);
  color: var(--warn-fg);
}

/* Tables */
.table-wrap { overflow-x: auto; margin: 16px 0 22px 0; }
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13.5px;
}
th {
  font-weight: 600;
  color: var(--ink);
  text-align: left;
  padding: 9px 10px;
  border-top: 1.5px solid var(--ink);
  border-bottom: 1px solid var(--rule-strong);
  background: transparent;
}
td {
  padding: 9px 10px;
  border-bottom: 1px solid var(--rule);
  vertical-align: top;
}
tbody tr:hover td { background: var(--subtle-surface); }
td.num, th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  font-size: 13px;
}
.score-bar-wrap { display: inline-flex; align-items: center; gap: 8px; }
.score-bar {
  width: 54px;
  height: 6px;
  background: var(--rule);
  border-radius: 2px;
  overflow: hidden;
  display: inline-block;
}
.score-fill { height: 100%; background: var(--primary); }

/* Code & Diagrams */
code {
  font-family: var(--font-mono);
  font-size: 12.5px;
  background: var(--subtle-surface);
  padding: 1px 5px;
  border-radius: 3px;
  overflow-wrap: anywhere;
}
pre {
  background: var(--subtle-surface);
  border: 1px solid var(--rule);
  padding: 12px 14px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-size: 12.5px;
}
pre code { background: none; padding: 0; }

.svg-figure, .img-figure {
  margin: 18px 0 22px 0;
  padding: 14px;
  background: #FFFFFF;
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  text-align: center;
}
[data-theme="dark"] .svg-figure {
  background: #F8FAFC;
  border-color: var(--rule-strong);
}
.svg-figure svg, .img-figure img { max-width: 100%; height: auto; display: block; margin: 0 auto; }
.svg-figure figcaption { font-size: 12px; color: #4B5563; margin-top: 8px; }

.mermaid-block {
  margin: 18px 0 22px 0;
  padding: 16px;
  background: var(--canvas);
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  overflow-x: auto;
  text-align: center;
}
.mermaid-fallback {
  text-align: left;
  font-family: var(--font-mono);
  font-size: 12px;
  white-space: pre-wrap;
}

/* Evidence Tags (functional, flat, crisp) */
.tag {
  font-family: var(--font-mono);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 3px;
  border: 1px solid var(--rule-strong);
  background: var(--subtle-surface);
  color: var(--ink-muted);
  white-space: nowrap;
}
.tag-verified { background: var(--good-bg); border-color: var(--good-rule); color: var(--good-fg); }
.tag-estimate { background: var(--info-bg); border-color: var(--info-rule); color: var(--info-fg); }
.tag-assumption { background: var(--amber-bg); border-color: var(--amber-rule); color: var(--amber-fg); }
.tag-unverified, .tag-stale { background: var(--warn-bg); border-color: var(--warn-rule); color: var(--warn-fg); }

/* Interactive Checklists */
li.task-item { list-style: none; margin-left: -18px; }
li.task-item label { display: inline-flex; align-items: flex-start; gap: 9px; cursor: pointer; }
li.task-item input[type="checkbox"] {
  margin-top: 4px;
  width: 16px;
  height: 16px;
  accent-color: var(--primary);
  cursor: pointer;
}
li.task-item.is-done span { text-decoration: line-through; color: var(--ink-subtle); }

/* Filter & Empty Search States */
.evidence-dim { opacity: 0.28; }
.evidence-hit { background: var(--amber-bg); border-radius: 3px; }
.empty-search {
  display: none;
  padding: 28px 20px;
  text-align: center;
  border: 1px dashed var(--rule-strong);
  border-radius: var(--radius-sm);
  color: var(--ink-muted);
  margin: 16px 0;
}
.empty-search.visible { display: block; }

/* Two-Pane Financial What-If Workbench */
.sim-workbench {
  display: grid;
  grid-template-columns: 270px minmax(0, 1fr);
  gap: 24px;
  align-items: start;
  margin-top: 18px;
}
.sim-workbench > * { min-width: 0; }
.sim-controls-col {
  background: var(--canvas);
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  padding: 16px;
}
.sim-controls-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--rule);
}
.sim-controls-head h3 { margin: 0; font-size: 13.5px; }
.sim-control { margin-bottom: 14px; }
.sim-control:last-of-type { margin-bottom: 0; }
.sim-control-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 12.5px;
  color: var(--ink-muted);
  margin-bottom: 4px;
}
.sim-control-val {
  font-family: var(--font-mono);
  font-weight: 600;
  color: var(--ink);
}
.sim-control input[type="range"] {
  width: 100%;
  accent-color: var(--primary);
  cursor: pointer;
}
.sim-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--rule);
}
.sim-actions .btn { flex: 1; }
.sim-chart-box {
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  background: var(--canvas);
  padding: 12px;
  margin-bottom: 16px;
}
.sim-chart-box svg { width: 100%; height: auto; display: block; }
details.sim-details {
  border: 1px solid var(--rule);
  border-radius: var(--radius-sm);
  padding: 10px 14px;
}
details.sim-details summary {
  cursor: pointer;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--ink);
}

/* Notion-style App Shell for Portfolio Hub ("Workspace Tenang") */
.hub-app {
  display: grid;
  grid-template-columns: 260px minmax(0, 1fr);
  min-height: 100vh;
  background: var(--bg);
  transition: grid-template-columns 150ms ease;
}
.hub-app.is-collapsed { grid-template-columns: 56px minmax(0, 1fr); }

.hub-sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  background: var(--surface-2);
  border-right: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 0 var(--sp-2) var(--sp-3);
}
.ws-switcher {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--sp-1) 0 var(--sp-2);
  margin-bottom: var(--sp-2);
  flex-shrink: 0;
}
.ws-brand {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  color: var(--text);
  font-weight: 600;
  font-size: 14px;
  text-decoration: none;
  white-space: nowrap;
  overflow: hidden;
}
.collapse-btn {
  width: 28px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 140ms ease, color 140ms ease;
}
.collapse-btn:hover { background: var(--line-soft); color: var(--text); }

.nav-item-btn {
  width: 100%;
  height: 32px;
  padding: 0 var(--sp-3);
  border: 0;
  border-left: 2px solid transparent;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 14px;
  font-weight: 400;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  cursor: pointer;
  text-decoration: none;
  text-align: left;
  transition: background 140ms ease, color 140ms ease;
}
.nav-item-btn:hover { background: var(--line-soft); color: var(--text); }
.nav-item-btn.active,
.nav-item-btn[aria-current="page"] {
  background: var(--line-soft);
  color: var(--text);
  font-weight: 600;
  border-left-color: var(--accent);
}
.nav-item-left {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
  flex: 1;
}
.nav-item-left svg { flex-shrink: 0; }
.nav-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-count {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.nav-kbd {
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text-muted);
  flex-shrink: 0;
}
.sidebar-section { margin-top: var(--sp-4); }
.sidebar-section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  padding: 0 var(--sp-3);
  margin: 0 0 var(--sp-1) 0;
}
.sidebar-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.sidebar-footer {
  padding-top: var(--sp-3);
  margin-top: var(--sp-4);
  border-top: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}
.sidebar-version {
  padding: 2px var(--sp-3) 0;
  font-size: 12px;
  color: var(--text-muted);
  font-family: var(--font-mono);
}

/* Collapsed 56px Sidebar Mode */
.hub-app.is-collapsed .hub-sidebar { padding: 0 var(--sp-2) var(--sp-3); }
.hub-app.is-collapsed .ws-brand-text,
.hub-app.is-collapsed .nav-label,
.hub-app.is-collapsed .nav-count,
.hub-app.is-collapsed .nav-kbd,
.hub-app.is-collapsed .sidebar-section-label,
.hub-app.is-collapsed .sidebar-recent-group,
.hub-app.is-collapsed .sidebar-version { display: none; }
.hub-app.is-collapsed .ws-switcher { justify-content: center; padding: 0; }
.hub-app.is-collapsed .ws-brand { display: none; }
.hub-app.is-collapsed .nav-item-btn { justify-content: center; padding: 0; border-left-color: transparent; }
.hub-app.is-collapsed .nav-item-btn[aria-current="page"] { background: var(--line-soft); outline: 1px solid var(--line); }
.hub-app.is-collapsed .nav-item-left { justify-content: center; flex: 0; }

/* Main Workspace Area */
.hub-main {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
.hub-topbar {
  height: 48px;
  padding: 0 var(--sp-8);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
}
.hub-topbar-left {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  min-width: 0;
}
.hub-hamburger {
  display: none;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.hub-breadcrumb {
  font-size: 13px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hub-breadcrumb strong { color: var(--text); font-weight: 500; }

.hub-content {
  width: 100%;
  max-width: none;
  padding: var(--sp-4) var(--sp-8) var(--sp-12);
}
.hub-page-header { margin-bottom: var(--sp-6); }
.hub-page-header h1 {
  font-family: var(--font-serif);
  font-size: 32px;
  font-weight: 600;
  letter-spacing: -0.01em;
  line-height: 1.2;
  color: var(--primary);
  margin: 0 0 var(--sp-2) 0;
}
.hub-page-desc {
  margin: 0 0 var(--sp-2) 0;
  font-size: 14px;
  color: var(--text-muted);
}
.hub-summary-line {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}
.hub-summary-line .mono-num {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

/* Database Toolbar */
.db-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  padding-bottom: var(--sp-3);
  border-bottom: 1px solid var(--line);
}
.view-seg {
  display: inline-flex;
  align-items: center;
  padding: 2px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface-2);
}
.view-seg-btn {
  height: 28px;
  padding: 0 var(--sp-3);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: background 140ms ease, color 140ms ease;
}
.view-seg-btn:hover { color: var(--text); }
.view-seg-btn[aria-pressed="true"] {
  background: var(--surface);
  color: var(--text);
  font-weight: 600;
}

.db-toolbar-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
}
.popover-anchor { position: relative; }
.toolbar-btn {
  height: 32px;
  padding: 0 var(--sp-3);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  transition: background 140ms ease;
}
.toolbar-btn:hover { background: var(--line-soft); }
.toolbar-btn[aria-expanded="true"] { background: var(--line-soft); border-color: var(--text-muted); }

.db-local-search {
  position: relative;
  display: flex;
  align-items: center;
  width: 200px;
}
.db-local-search svg {
  position: absolute;
  left: 10px;
  color: var(--text-muted);
  pointer-events: none;
}
.db-local-input {
  width: 100%;
  height: 32px;
  padding: 0 10px 0 32px;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
}
.db-local-input:focus { border-color: var(--accent); }
.db-local-input::placeholder { color: var(--text-muted); }

/* Lightweight Popover */
.popover-menu {
  display: none;
  position: absolute;
  right: 0;
  top: calc(100% + 6px);
  min-width: 220px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-float);
  padding: var(--sp-3);
  z-index: 30;
}
.popover-menu.open { display: block; }
.pop-group { margin-bottom: var(--sp-3); }
.pop-group:last-child { margin-bottom: 0; }
.pop-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin: 0 0 var(--sp-2) 0;
}
.pop-opt {
  width: 100%;
  padding: 6px var(--sp-2);
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pop-opt:hover { background: var(--line-soft); }
.pop-opt.active { font-weight: 600; color: var(--primary); background: var(--line-soft); }

/* Active Filter Chips */
.active-chips {
  display: none;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
  padding: var(--sp-2) 0;
}
.active-chips.visible { display: flex; }
.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 24px;
  padding: 0 var(--sp-2);
  border: 1px solid var(--line);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  font-family: inherit;
  font-size: 12px;
  cursor: pointer;
}
.filter-chip:hover { background: var(--line-soft); }

/* Notion-style Database Table (flat lines, no heavy outer frame) */
.db-table-wrap { width: 100%; overflow-x: auto; }
.db-table {
  width: 100%;
  border-collapse: collapse;
  margin: 0;
}
.db-table thead th {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  text-align: left;
  padding: 10px var(--sp-3);
  border-top: none;
  border-bottom: 1px solid var(--line);
  background: transparent;
  white-space: nowrap;
}
.db-table tbody tr {
  border-bottom: 1px solid var(--line);
  cursor: pointer;
  transition: background 140ms ease;
}
.db-table tbody tr:hover,
.db-table tbody tr:focus-visible,
.db-table tbody tr:focus-within {
  background: var(--line-soft);
}
.db-table tbody td {
  padding: 10px var(--sp-3);
  vertical-align: middle;
  border-bottom: none;
}
.db-doc-cell { min-width: 220px; width: 42%; }
.db-doc-row {
  display: flex;
  align-items: flex-start;
  gap: var(--sp-2);
}
.db-doc-icon { color: var(--text-muted); margin-top: 2px; flex-shrink: 0; }
.db-doc-meta { min-width: 0; flex: 1; }
.db-doc-title {
  font-size: 14px;
  font-weight: 500;
  line-height: 1.35;
  color: var(--text);
  text-decoration: none;
  display: block;
}
.db-doc-title:hover { color: var(--primary); text-decoration: underline; }
.db-doc-path {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
}

.badge-combined {
  display: inline-flex;
  align-items: center;
  height: 22px;
  padding: 0 var(--sp-2);
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
}
.audit-nowrap { white-space: nowrap; }

.db-actions-cell { width: 76px; text-align: right; }
.row-actions {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  opacity: 0;
  transition: opacity 140ms ease;
}
.db-table tbody tr:hover .row-actions,
.db-table tbody tr:focus-within .row-actions {
  opacity: 1;
}
@media (hover: none) {
  .row-actions { opacity: 1; }
}
.icon-action-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  border: 1px solid var(--line);
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
  transition: background 140ms ease;
}
.icon-action-btn:hover { background: var(--surface-2); }

/* Gallery View (hidden unless active) */
.db-gallery {
  display: none;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--sp-4);
  margin-top: var(--sp-4);
}
.db-gallery.active { display: grid; }
.db-table-wrap.hidden { display: none; }
.gallery-card {
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: var(--sp-3);
  cursor: pointer;
  transition: border-color 140ms ease;
}
.gallery-card:hover, .gallery-card:focus-within { border-color: var(--text-muted); }
.gallery-card-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-2);
  padding-top: var(--sp-3);
  border-top: 1px solid var(--line);
}

/* Command Palette Modal (560px) */
.cmd-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  z-index: 80;
  align-items: flex-start;
  justify-content: center;
  padding: 12vh var(--sp-4) var(--sp-4);
}
.cmd-backdrop.open { display: flex; }
.cmd-modal {
  width: 100%;
  max-width: 560px;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-float);
  overflow: hidden;
}
.cmd-input-row {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  padding: 0 var(--sp-4);
  border-bottom: 1px solid var(--line);
}
.cmd-input {
  width: 100%;
  height: 46px;
  border: 0;
  background: transparent;
  color: var(--text);
  font-family: inherit;
  font-size: 14px;
  outline: none;
}
.cmd-results {
  max-height: 320px;
  overflow-y: auto;
  padding: var(--sp-2);
}
.cmd-item {
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--text);
  font-family: inherit;
  text-align: left;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sp-3);
  cursor: pointer;
}
.cmd-item:hover, .cmd-item.is-selected { background: var(--line-soft); }
.cmd-item-sub {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
}

.drawer-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: var(--overlay-bg);
  z-index: 45;
}
.drawer-backdrop.open { display: block; }

@media (max-width: 768px) {
  .hub-app, .hub-app.is-collapsed { grid-template-columns: minmax(0, 1fr); }
  .hub-sidebar {
    position: fixed;
    left: 0;
    top: 0;
    width: 260px;
    z-index: 60;
    transform: translateX(-105%);
    transition: transform 150ms ease;
    box-shadow: var(--shadow-float);
  }
  .hub-sidebar.open { transform: translateX(0); }
  .hub-app.is-collapsed .ws-brand-text,
  .hub-app.is-collapsed .nav-label,
  .hub-app.is-collapsed .nav-count,
  .hub-app.is-collapsed .nav-kbd,
  .hub-app.is-collapsed .sidebar-section-label,
  .hub-app.is-collapsed .sidebar-recent-group,
  .hub-app.is-collapsed .sidebar-version { display: inline; }
  .hub-app.is-collapsed .ws-brand { display: inline-flex; }
  .hub-app.is-collapsed .sidebar-section-label { display: block; }
  .hub-app.is-collapsed .nav-item-btn { justify-content: space-between; padding: 0 var(--sp-3); }
  .hub-app.is-collapsed .nav-item-left { flex: 1; justify-content: flex-start; }

  .hub-hamburger { display: inline-flex; }
  .collapse-btn { display: none; }
  .hub-topbar { padding: 0 var(--sp-4); }
  .hub-content { padding: var(--sp-3) var(--sp-4) var(--sp-8); }
  .hub-page-header h1 { font-size: 26px; }
  .db-local-search { width: 100%; }
  .db-toolbar-right { width: 100%; }
  .db-table, .db-table tbody, .db-table tr, .db-table td { display: block; width: 100%; min-width: 0; }
  .db-table thead { display: none; }
  .db-table tbody tr {
    padding: var(--sp-3) 0;
  }
  .db-table tbody td { padding: 3px 0; max-width: 100%; }
  .db-doc-cell { max-width: 100%; }
  .db-doc-path { white-space: normal; word-break: break-all; }
  .db-actions-cell { width: 100%; text-align: left; padding-top: var(--sp-2) !important; }
  .row-actions { opacity: 1; }
}

/* Score cell with thin 0-5 bar */
.score-cell { min-width: 96px; }
.score-num {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}
.score-track {
  width: 72px;
  height: 4px;
  background: var(--line);
  border-radius: 2px;
  overflow: hidden;
  margin-top: var(--sp-1);
}
.score-fill-bar {
  height: 100%;
  background: var(--primary);
}
.muted-text { font-size: 13px; color: var(--text-muted); }

/* Decision semantic pills */
.decision-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
}
.decision-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.dec-go { color: var(--go); background: var(--go-bg); }
.dec-conditional { color: var(--conditional); background: var(--conditional-bg); }
.dec-nogo { color: var(--nogo); background: var(--nogo-bg); }
.dec-pending { color: var(--pending); background: var(--pending-bg); }

.hub-row-actions {
  display: flex;
  flex-wrap: nowrap;
  gap: var(--sp-2);
  justify-content: flex-end;
}
.hub-empty {
  padding: var(--sp-8) var(--sp-6);
  text-align: center;
  color: var(--text-muted);
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
}
.empty-hub-state {
  display: none;
  padding: var(--sp-8) var(--sp-6);
  text-align: center;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  color: var(--text-muted);
}
.empty-hub-state.visible { display: block; }

@media (max-width: 1120px) {
  .hub-topbar, .hub-content { padding-left: var(--sp-6); padding-right: var(--sp-6); }
  .db-doc-cell { min-width: 160px; max-width: 230px; }
  .db-table thead th, .db-table tbody td { padding: 10px var(--sp-2); }
  .hub-doc-cell { max-width: 260px; }
  .hub-table thead th,
  .hub-table tbody td { padding: var(--sp-3); }
}

@media (max-width: 960px) {
  .menu-btn { display: inline-flex; min-width: 36px; min-height: 36px; padding: 0 var(--sp-2); }
  .workspace { display: block; }
  .rail {
    position: fixed;
    left: 0;
    top: var(--topbar-h);
    width: 280px;
    max-width: 85vw;
    background: var(--surface);
    z-index: 50;
    transform: translateX(-105%);
    transition: transform 150ms ease;
    box-shadow: var(--shadow-float);
  }
  .rail.open { transform: translateX(0); }
  .content-stage { padding: var(--sp-4) var(--sp-3) var(--sp-12); }
  .sheet { padding: var(--sp-6) var(--sp-4) var(--sp-8); width: 100%; }
  .doc-headline { font-size: 24px; overflow-wrap: break-word; }
  .sim-workbench { grid-template-columns: 1fr; }
  .kpi-grid { grid-template-columns: repeat(2, 1fr); }
  .kpi-card { border-right: none; border-bottom: 1px solid var(--line); }
  .topbar { padding: 0 var(--sp-3); }
  .topbar-doc-name, .crumb-sep { display: none; }
}

@media (max-width: 768px) {
  .hub-shell { padding: var(--sp-6) var(--sp-4) var(--sp-8); }
  .hub-header h1 { font-size: 24px; }
  .stat-strip { display: grid; grid-template-columns: repeat(2, 1fr); }
  .stat-item { border-right: none; margin-right: 0; padding: var(--sp-3) var(--sp-2); border-bottom: 1px solid var(--line); }
  .stat-item:nth-last-child(-n+2) { border-bottom: none; }

  /* Header search collapses to icon button on mobile */
  .search-toggle-btn { display: inline-flex; }
  .search-box { display: none; }
  .topbar.search-open .search-box {
    display: flex;
    position: absolute;
    left: 0;
    right: 0;
    top: var(--topbar-h);
    width: 100%;
    padding: var(--sp-2) var(--sp-4);
    background: var(--surface);
    border-bottom: 1px solid var(--line);
    box-shadow: var(--shadow-float);
  }
  .topbar.search-open .search-icon { left: 26px; }
  .topbar.search-open .kbd-hint { display: none; }

  /* Transform document table into stacked cards on <768px */
  .hub-table-card { background: transparent; border: none; border-radius: 0; overflow: visible; }
  .hub-table, .hub-table tbody, .hub-table tr, .hub-table td { display: block; width: 100%; min-width: 0; }
  .hub-table thead { display: none; }
  .hub-table tbody tr {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius-md);
    padding: var(--sp-4);
    margin-bottom: var(--sp-3);
  }
  .hub-table tbody tr:last-child { border-bottom: 1px solid var(--line); margin-bottom: 0; }
  .hub-table tbody td {
    padding: var(--sp-1) 0;
    max-width: 100%;
  }
  .hub-doc-cell { max-width: 100%; margin-bottom: var(--sp-2); }
  .hub-sub-path { white-space: normal; word-break: break-all; }
  .hub-tabs { gap: var(--sp-4); }
  .hub-selects { flex-direction: column; align-items: stretch; width: 100%; gap: var(--sp-2); }
  .select-field { justify-content: space-between; width: 100%; }
  .hub-select { width: 65%; min-width: 0; }
  .hub-row-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
    margin-top: var(--sp-3);
    padding-top: var(--sp-3);
    border-top: 1px solid var(--line);
  }
  .hub-row-actions .btn { flex: 1 1 auto; }
  .theme-opt span { display: none; }
  .theme-opt { padding: 0 var(--sp-2); }
  .btn-dl-html { display: none; }
  .kpi-grid { grid-template-columns: 1fr; }
}

@media print {
  :root, [data-theme="dark"] {
    --bg: #FFFFFF;
    --surface: #FFFFFF;
    --surface-2: #F3F4F6;
    --text: #000000;
    --text-muted: #374151;
    --primary: #000000;
    --line: #9CA3AF;
  }
  .topbar, .rail, .evidence-strip, .lint-drawer, .sim-controls-col, .empty-search,
  .hub-controls, .hub-row-actions, .theme-switch, .empty-hub-state,
  .hub-sidebar, .hub-topbar, .db-toolbar, .active-chips, .db-actions-cell,
  .cmd-backdrop, .drawer-backdrop { display: none !important; }
  .workspace, .hub-app { display: block; }
  .content-stage, .hub-shell, .hub-content { padding: 0; max-width: 100%; }
  .sheet { max-width: 100%; border: none; padding: 0; }
  .hub-table-card { border-color: #000000; }
  .hub-table th, .hub-table td, .db-table th, .db-table td { color: #000000; border-color: #9CA3AF; }
  .decision-pill, .badge-outline, .badge-combined { border: 1px solid #000000; background: #FFFFFF; color: #000000; }
  .doc-panel { display: block !important; page-break-after: always; }
  .sim-workbench { display: block; }
}
"""


WEB_JS = r"""
(function() {
  const CFG = window.__IDEAFORGE_DATA__ || {};
  const LABELS = CFG.labels || {};
  const STORAGE_THEME = 'ideaforge-theme-v2';

  // Theme: follows prefers-color-scheme by default, manual toggle persisted in localStorage
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  const savedTheme = localStorage.getItem(STORAGE_THEME) || (prefersDark ? 'dark' : 'light');
  function setTheme(theme, persist) {
    const val = theme === 'dark' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', val);
    if (persist) localStorage.setItem(STORAGE_THEME, val);
    document.querySelectorAll('[data-set-theme]').forEach(btn => {
      btn.setAttribute('aria-pressed', String(btn.dataset.setTheme === val));
    });
    const hubThemeLabel = document.getElementById('hub-theme-label');
    if (hubThemeLabel) {
      hubThemeLabel.textContent = val === 'dark' ? (LABELS.theme_dark || 'Tema: Gelap') : (LABELS.theme_light || 'Tema: Terang');
    }
    const hubThemeIcon = document.getElementById('hub-theme-icon');
    if (hubThemeIcon) {
      hubThemeIcon.innerHTML = val === 'dark' ? (CFG.moonSvg || '') : (CFG.sunSvg || '');
    }
    if (typeof window.__ideaforgeRedrawSim === 'function') {
      window.__ideaforgeRedrawSim();
    }
  }
  setTheme(savedTheme, false);
  document.querySelectorAll('[data-set-theme]').forEach(btn => {
    btn.addEventListener('click', () => setTheme(btn.dataset.setTheme, true));
  });
  const hubThemeBtn = document.getElementById('hub-theme-toggle');
  if (hubThemeBtn) {
    hubThemeBtn.addEventListener('click', () => {
      const cur = document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
      setTheme(cur === 'dark' ? 'light' : 'dark', true);
    });
  }

  // Mobile search toggle
  const searchToggleBtn = document.getElementById('search-toggle');
  const topbarEl = document.querySelector('.topbar');
  if (searchToggleBtn && topbarEl) {
    searchToggleBtn.addEventListener('click', () => {
      const open = topbarEl.classList.toggle('search-open');
      searchToggleBtn.setAttribute('aria-expanded', String(open));
      if (open) {
        const inp = document.getElementById('search-input');
        if (inp) inp.focus();
      }
    });
  }

  // Mobile rail drawer
  const menuBtn = document.getElementById('menu-toggle');
  const rail = document.getElementById('sidebar');
  if (menuBtn && rail) {
    menuBtn.addEventListener('click', () => {
      const open = rail.classList.toggle('open');
      menuBtn.setAttribute('aria-expanded', String(open));
    });
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && rail.classList.contains('open')) {
        rail.classList.remove('open');
        menuBtn.setAttribute('aria-expanded', 'false');
      }
    });
  }

  // Quality audit drawer
  const lintBtn = document.getElementById('lint-toggle');
  const lintDrawer = document.getElementById('lint-drawer');
  if (lintBtn && lintDrawer) {
    lintBtn.addEventListener('click', () => {
      const open = lintDrawer.classList.toggle('open');
      lintBtn.setAttribute('aria-expanded', String(open));
      if (open) lintDrawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    });
  }

  // Document switching & Full vs By-Doc mode
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
      p.classList.toggle('hidden', viewMode === 'tab' && p.id !== activeDocId);
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
      if (rail) rail.classList.remove('open');
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
      const blocks = document.querySelectorAll('.doc-panel p, .doc-panel li, .doc-panel tbody tr');
      if (tag === 'all') {
        blocks.forEach(b => b.classList.remove('evidence-dim', 'evidence-hit'));
        return;
      }
      if (viewMode === 'tab') { viewMode = 'all'; applyViewMode(); }
      let firstHit = null;
      blocks.forEach(b => {
        const match = b.querySelector('.tag-' + tag);
        b.classList.toggle('evidence-hit', !!match);
        b.classList.toggle('evidence-dim', !match);
        if (match && !firstHit) firstHit = b;
      });
      if (firstHit) firstHit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  });

  // Instant Search ('/' or Cmd/Ctrl+K shortcut) with explicit empty state
  const searchInput = document.getElementById('search-input');
  const emptyBox = document.getElementById('empty-search');
  const clearSearchBtn = document.getElementById('clear-search-btn');

  document.addEventListener('keydown', e => {
    const inField = /INPUT|TEXTAREA/.test(document.activeElement.tagName);
    if ((e.key === '/' && !inField) || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) {
      e.preventDefault();
      if (searchInput) searchInput.focus();
    } else if (e.key === 'Escape' && document.activeElement === searchInput) {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      searchInput.blur();
    }
  });

  if (clearSearchBtn && searchInput) {
    clearSearchBtn.addEventListener('click', () => {
      searchInput.value = '';
      searchInput.dispatchEvent(new Event('input'));
      searchInput.focus();
    });
  }

  // Notion-style Hub App Shell: sidebar collapse ('['), mobile drawer, view switch, popovers, command palette
  const hubApp = document.getElementById('hub-app');
  if (hubApp) {
    const STORAGE_COLLAPSE = 'ideaforge-hub-collapsed';
    const STORAGE_VIEW = 'ideaforge-hub-view';
    const sidebarEl = document.getElementById('hub-sidebar');
    const collapseBtn = document.getElementById('hub-collapse-btn');
    const hamburgerBtn = document.getElementById('hub-hamburger');
    const drawerBackdrop = document.getElementById('drawer-backdrop');

    function setCollapsed(collapsed, persist) {
      hubApp.classList.toggle('is-collapsed', collapsed);
      if (collapseBtn) collapseBtn.setAttribute('aria-expanded', String(!collapsed));
      if (persist) localStorage.setItem(STORAGE_COLLAPSE, collapsed ? '1' : '0');
    }
    if (localStorage.getItem(STORAGE_COLLAPSE) === '1') setCollapsed(true, false);
    if (collapseBtn) {
      collapseBtn.addEventListener('click', () => setCollapsed(!hubApp.classList.contains('is-collapsed'), true));
    }

    function setMobileDrawer(open) {
      if (!sidebarEl || !drawerBackdrop) return;
      sidebarEl.classList.toggle('open', open);
      drawerBackdrop.classList.toggle('open', open);
      if (hamburgerBtn) hamburgerBtn.setAttribute('aria-expanded', String(open));
      if (!open && hamburgerBtn) hamburgerBtn.focus();
    }
    if (hamburgerBtn) hamburgerBtn.addEventListener('click', () => setMobileDrawer(true));
    if (drawerBackdrop) drawerBackdrop.addEventListener('click', () => setMobileDrawer(false));

    // View Switcher (Tabel | Galeri)
    const tableWrap = document.getElementById('db-table-wrap');
    const galleryEl = document.getElementById('db-gallery');
    const viewTableBtn = document.getElementById('view-table-btn');
    const viewGalleryBtn = document.getElementById('view-gallery-btn');
    let curView = localStorage.getItem(STORAGE_VIEW) === 'gallery' ? 'gallery' : 'table';

    function setDbView(mode, persist) {
      curView = mode === 'gallery' ? 'gallery' : 'table';
      if (persist) localStorage.setItem(STORAGE_VIEW, curView);
      if (viewTableBtn) viewTableBtn.setAttribute('aria-pressed', String(curView === 'table'));
      if (viewGalleryBtn) viewGalleryBtn.setAttribute('aria-pressed', String(curView === 'gallery'));
      applyHubDatabase();
    }
    if (viewTableBtn) viewTableBtn.addEventListener('click', () => setDbView('table', true));
    if (viewGalleryBtn) viewGalleryBtn.addEventListener('click', () => setDbView('gallery', true));

    // Popovers (Filter & Urutkan)
    const filterBtn = document.getElementById('filter-pop-btn');
    const filterPop = document.getElementById('filter-popover');
    const sortBtn = document.getElementById('sort-pop-btn');
    const sortPop = document.getElementById('sort-popover');

    function closePopovers(returnFocusTo) {
      if (filterPop) filterPop.classList.remove('open');
      if (sortPop) sortPop.classList.remove('open');
      if (filterBtn) filterBtn.setAttribute('aria-expanded', 'false');
      if (sortBtn) sortBtn.setAttribute('aria-expanded', 'false');
      if (returnFocusTo) returnFocusTo.focus();
    }
    if (filterBtn && filterPop) {
      filterBtn.addEventListener('click', e => {
        e.stopPropagation();
        const willOpen = !filterPop.classList.contains('open');
        closePopovers();
        if (willOpen) {
          filterPop.classList.add('open');
          filterBtn.setAttribute('aria-expanded', 'true');
          const firstOpt = filterPop.querySelector('.pop-opt');
          if (firstOpt) firstOpt.focus();
        }
      });
    }
    if (sortBtn && sortPop) {
      sortBtn.addEventListener('click', e => {
        e.stopPropagation();
        const willOpen = !sortPop.classList.contains('open');
        closePopovers();
        if (willOpen) {
          sortPop.classList.add('open');
          sortBtn.setAttribute('aria-expanded', 'true');
          const firstOpt = sortPop.querySelector('.pop-opt');
          if (firstOpt) firstOpt.focus();
        }
      });
    }
    document.addEventListener('click', e => {
      if (filterPop && !filterPop.contains(e.target) && e.target !== filterBtn &&
          sortPop && !sortPop.contains(e.target) && e.target !== sortBtn) {
        closePopovers();
      }
    });

    // State for collection, decision, type filter, sort, local search
    let activeTrack = 'all';
    let activeDecision = 'all';
    let activeTypeFilter = 'all';
    let activeSort = 'newest';
    const localSearchEl = document.getElementById('db-local-search');

    const collectionMeta = CFG.collections || {};
    const pageTitleEl = document.getElementById('hub-page-title');
    const pageDescEl = document.getElementById('hub-page-desc');
    const breadcrumbEl = document.getElementById('hub-breadcrumb');
    const chipsEl = document.getElementById('active-chips');

    function renderChips() {
      if (!chipsEl) return;
      const chips = [];
      if (activeDecision !== 'all') {
        const lbl = (CFG.decisionLabels || {})[activeDecision] || activeDecision;
        chips.push(`<button type="button" class="filter-chip" data-clear="decision">Keputusan: ${lbl} ×</button>`);
      }
      if (activeTypeFilter !== 'all') {
        const lbl = (CFG.typeLabels || {})[activeTypeFilter] || activeTypeFilter.toUpperCase();
        chips.push(`<button type="button" class="filter-chip" data-clear="type">Tipe: ${lbl} ×</button>`);
      }
      chipsEl.innerHTML = chips.join('');
      chipsEl.classList.toggle('visible', chips.length > 0);
      chipsEl.querySelectorAll('[data-clear]').forEach(btn => {
        btn.addEventListener('click', () => {
          if (btn.dataset.clear === 'decision') activeDecision = 'all';
          if (btn.dataset.clear === 'type') activeTypeFilter = 'all';
          syncPopoverOptions();
          applyHubDatabase();
        });
      });
    }

    function syncPopoverOptions() {
      document.querySelectorAll('[data-pop-decision]').forEach(b => b.classList.toggle('active', b.dataset.popDecision === activeDecision));
      document.querySelectorAll('[data-pop-type]').forEach(b => b.classList.toggle('active', b.dataset.popType === activeTypeFilter));
      document.querySelectorAll('[data-pop-sort]').forEach(b => b.classList.toggle('active', b.dataset.popSort === activeSort));
    }

    function applyHubDatabase() {
      const tbody = document.getElementById('hub-tbody');
      const rows = Array.from(document.querySelectorAll('.hub-row'));
      const cards = Array.from(document.querySelectorAll('.gallery-card'));
      const q = localSearchEl ? localSearchEl.value.trim().toLowerCase() : '';

      const meta = collectionMeta[activeTrack] || collectionMeta.all || {};
      if (pageTitleEl && meta.title) pageTitleEl.textContent = meta.title;
      if (pageDescEl && meta.desc) pageDescEl.textContent = meta.desc;
      if (breadcrumbEl && meta.crumb) breadcrumbEl.innerHTML = meta.crumb;

      const cmp = (a, b) => {
        if (activeSort === 'score') return Number(b.dataset.score || -1) - Number(a.dataset.score || -1);
        if (activeSort === 'name') return (a.dataset.title || '').localeCompare(b.dataset.title || '');
        return Number(b.dataset.updated || 0) - Number(a.dataset.updated || 0);
      };
      if (tbody) {
        rows.sort(cmp).forEach(r => tbody.appendChild(r));
      }
      if (galleryEl) {
        cards.sort(cmp).forEach(c => galleryEl.appendChild(c));
      }

      const effectiveTrack = activeTypeFilter !== 'all' ? activeTypeFilter : activeTrack;
      let visible = 0;
      const filterItem = el => {
        const okTrack = effectiveTrack === 'all' || el.dataset.track === effectiveTrack;
        const okDec = activeDecision === 'all' || el.dataset.decision === activeDecision;
        const okQ = !q || el.textContent.toLowerCase().includes(q);
        const show = okTrack && okDec && okQ;
        el.style.display = show ? '' : 'none';
        return show;
      };
      rows.forEach(r => { if (filterItem(r)) visible += 1; });
      cards.forEach(c => filterItem(c));

      if (tableWrap) tableWrap.classList.toggle('hidden', visible === 0 || curView !== 'table');
      if (galleryEl) galleryEl.classList.toggle('active', visible > 0 && curView === 'gallery');

      const emptyEl = document.getElementById('empty-search');
      if (emptyEl) {
        emptyEl.classList.toggle('visible', visible === 0);
        const msgEl = document.getElementById('empty-hub-msg');
        if (msgEl && visible === 0) {
          const emptyByTrack = {
            prd: LABELS.empty_prd,
            prp: LABELS.empty_prp,
            idea: LABELS.empty_idea,
            sample: LABELS.empty_sample,
          };
          msgEl.textContent = (!q && activeDecision === 'all' && emptyByTrack[effectiveTrack])
            ? emptyByTrack[effectiveTrack]
            : (LABELS.empty_filtered || LABELS.no_results);
        }
      }
      renderChips();
    }

    document.querySelectorAll('[data-nav-track]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTrack = btn.dataset.navTrack;
        activeTypeFilter = 'all';
        document.querySelectorAll('[data-nav-track]').forEach(b => {
          const isAct = b === btn;
          b.classList.toggle('active', isAct);
          if (isAct) b.setAttribute('aria-current', 'page');
          else b.removeAttribute('aria-current');
        });
        syncPopoverOptions();
        applyHubDatabase();
        setMobileDrawer(false);
      });
    });

    document.querySelectorAll('[data-pop-decision]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeDecision = btn.dataset.popDecision;
        syncPopoverOptions();
        applyHubDatabase();
        closePopovers(filterBtn);
      });
    });
    document.querySelectorAll('[data-pop-type]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeTypeFilter = btn.dataset.popType;
        syncPopoverOptions();
        applyHubDatabase();
        closePopovers(filterBtn);
      });
    });
    document.querySelectorAll('[data-pop-sort]').forEach(btn => {
      btn.addEventListener('click', () => {
        activeSort = btn.dataset.popSort;
        syncPopoverOptions();
        applyHubDatabase();
        closePopovers(sortBtn);
      });
    });
    if (localSearchEl) localSearchEl.addEventListener('input', applyHubDatabase);

    const resetBtn = document.getElementById('reset-hub-filters');
    if (resetBtn) {
      resetBtn.addEventListener('click', () => {
        activeTrack = 'all';
        activeDecision = 'all';
        activeTypeFilter = 'all';
        if (localSearchEl) localSearchEl.value = '';
        document.querySelectorAll('[data-nav-track]').forEach(b => {
          const isAct = b.dataset.navTrack === 'all';
          b.classList.toggle('active', isAct);
          if (isAct) b.setAttribute('aria-current', 'page');
          else b.removeAttribute('aria-current');
        });
        syncPopoverOptions();
        applyHubDatabase();
      });
    }

    // Row & Gallery card click + keyboard navigation (Enter opens, Up/Down moves rows)
    document.querySelectorAll('.hub-row').forEach(row => {
      row.addEventListener('click', e => {
        if (e.target.closest('a, button')) return;
        if (row.dataset.href) window.location.href = row.dataset.href;
      });
      row.addEventListener('keydown', e => {
        if (e.key === 'Enter' && e.target === row && row.dataset.href) {
          window.location.href = row.dataset.href;
        } else if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
          const vis = Array.from(document.querySelectorAll('.hub-row')).filter(r => r.style.display !== 'none');
          const idx = vis.indexOf(row);
          if (idx !== -1) {
            e.preventDefault();
            const next = e.key === 'ArrowDown' ? vis[Math.min(vis.length - 1, idx + 1)] : vis[Math.max(0, idx - 1)];
            if (next) next.focus();
          }
        }
      });
    });
    document.querySelectorAll('.gallery-card').forEach(card => {
      card.addEventListener('click', e => {
        if (e.target.closest('a, button')) return;
        if (card.dataset.href) window.location.href = card.dataset.href;
      });
      card.addEventListener('keydown', e => {
        if (e.key === 'Enter' && e.target === card && card.dataset.href) {
          window.location.href = card.dataset.href;
        }
      });
    });

    // Command Palette Modal ('/' or sidebar Cari button)
    const cmdBackdrop = document.getElementById('cmd-backdrop');
    const cmdInput = document.getElementById('cmd-input');
    const cmdResults = document.getElementById('cmd-results');
    const cmdTrigger = document.getElementById('hub-search-trigger');
    let cmdLastFocus = null;
    let cmdSelectedIdx = 0;

    function renderCmdResults() {
      if (!cmdResults) return;
      const q = cmdInput ? cmdInput.value.trim().toLowerCase() : '';
      const docs = (CFG.hubItems || []).filter(it => !q || it.title.toLowerCase().includes(q) || it.path.toLowerCase().includes(q));
      if (!docs.length) {
        cmdResults.innerHTML = `<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:13px;">${LABELS.empty_filtered || 'Tidak ditemukan.'}</div>`;
        return;
      }
      cmdSelectedIdx = Math.min(cmdSelectedIdx, docs.length - 1);
      cmdResults.innerHTML = docs.map((it, idx) =>
        `<button type="button" class="cmd-item${idx === cmdSelectedIdx ? ' is-selected' : ''}" data-cmd-href="${it.href}">`
        + `<span><strong>${it.title}</strong><div class="cmd-item-sub">${it.path}</div></span>`
        + `<span class="badge-combined">${it.type}</span></button>`
      ).join('');
      cmdResults.querySelectorAll('.cmd-item').forEach(btn => {
        btn.addEventListener('click', () => { window.location.href = btn.dataset.cmdHref; });
      });
    }

    function openCmdPalette(triggerEl) {
      if (!cmdBackdrop) return;
      cmdLastFocus = triggerEl || document.activeElement;
      cmdBackdrop.classList.add('open');
      cmdSelectedIdx = 0;
      if (cmdInput) { cmdInput.value = ''; cmdInput.focus(); }
      renderCmdResults();
    }
    function closeCmdPalette() {
      if (!cmdBackdrop) return;
      cmdBackdrop.classList.remove('open');
      if (cmdLastFocus && typeof cmdLastFocus.focus === 'function') cmdLastFocus.focus();
    }

    if (cmdTrigger) cmdTrigger.addEventListener('click', () => openCmdPalette(cmdTrigger));
    if (cmdBackdrop) {
      cmdBackdrop.addEventListener('click', e => { if (e.target === cmdBackdrop) closeCmdPalette(); });
    }
    if (cmdInput) {
      cmdInput.addEventListener('input', () => { cmdSelectedIdx = 0; renderCmdResults(); });
      cmdInput.addEventListener('keydown', e => {
        const items = cmdResults ? Array.from(cmdResults.querySelectorAll('.cmd-item')) : [];
        if (e.key === 'ArrowDown' && items.length) {
          e.preventDefault();
          cmdSelectedIdx = (cmdSelectedIdx + 1) % items.length;
          renderCmdResults();
        } else if (e.key === 'ArrowUp' && items.length) {
          e.preventDefault();
          cmdSelectedIdx = (cmdSelectedIdx - 1 + items.length) % items.length;
          renderCmdResults();
        } else if (e.key === 'Enter' && items[cmdSelectedIdx]) {
          e.preventDefault();
          window.location.href = items[cmdSelectedIdx].dataset.cmdHref;
        } else if (e.key === 'Escape') {
          e.preventDefault();
          closeCmdPalette();
        }
      });
    }

    document.addEventListener('keydown', e => {
      const inField = /INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName);
      if ((e.key === '/' && !inField) || ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k')) {
        e.preventDefault();
        openCmdPalette(document.activeElement);
      } else if (e.key === '[' && !inField) {
        e.preventDefault();
        setCollapsed(!hubApp.classList.contains('is-collapsed'), true);
      } else if (e.key === 'Escape') {
        if (cmdBackdrop && cmdBackdrop.classList.contains('open')) closeCmdPalette();
        else if (filterPop && filterPop.classList.contains('open')) closePopovers(filterBtn);
        else if (sortPop && sortPop.classList.contains('open')) closePopovers(sortBtn);
        else if (sidebarEl && sidebarEl.classList.contains('open')) setMobileDrawer(false);
      }
    });

    setDbView(curView, false);
  }

  function applyHubFilters() {
    const tbody = document.getElementById('hub-tbody');
    const rows = Array.from(document.querySelectorAll('.hub-row'));
    const tableCard = document.getElementById('hub-table-card');
    if (!tbody) return;

    const activeTab = document.querySelector('[data-track-filter].active');
    const tr = activeTab ? activeTab.dataset.trackFilter : 'all';
    const decFilterEl = document.getElementById('decision-filter');
    const dec = decFilterEl ? decFilterEl.value : 'all';
    const sortEl = document.getElementById('sort-select');
    const sortBy = sortEl ? sortEl.value : 'newest';
    const q = searchInput ? searchInput.value.trim().toLowerCase() : '';

    // Sort rows deterministically
    rows.sort((a, b) => {
      if (sortBy === 'score') {
        return Number(b.dataset.score || -1) - Number(a.dataset.score || -1);
      }
      if (sortBy === 'name') {
        return (a.dataset.title || '').localeCompare(b.dataset.title || '');
      }
      return Number(b.dataset.updated || 0) - Number(a.dataset.updated || 0);
    });
    rows.forEach(r => tbody.appendChild(r));

    let visible = 0;
    rows.forEach(r => {
      const okTrack = tr === 'all' || r.dataset.track === tr;
      const okDec = dec === 'all' || r.dataset.decision === dec;
      const okQuery = !q || r.textContent.toLowerCase().includes(q);
      const show = okTrack && okDec && okQuery;
      r.style.display = show ? '' : 'none';
      if (show) visible += 1;
    });

    if (tableCard) tableCard.style.display = visible === 0 ? 'none' : '';
    if (emptyBox) {
      emptyBox.classList.toggle('visible', visible === 0);
      const msgEl = document.getElementById('empty-hub-msg');
      if (msgEl && visible === 0) {
        const emptyByTrack = {
          prd: LABELS.empty_prd,
          prp: LABELS.empty_prp,
          idea: LABELS.empty_idea,
          sample: LABELS.empty_sample,
        };
        msgEl.textContent = (!q && dec === 'all' && emptyByTrack[tr]) ? emptyByTrack[tr] : (LABELS.empty_filtered || LABELS.no_results);
      }
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', () => {
      if (document.getElementById('hub-tbody')) {
        applyHubFilters();
        return;
      }
      const q = searchInput.value.trim().toLowerCase();
      if (!q) {
        if (emptyBox) emptyBox.classList.remove('visible');
        applyViewMode();
        return;
      }
      let hits = 0;
      panels.forEach(p => {
        const hit = p.textContent.toLowerCase().includes(q);
        p.classList.toggle('hidden', !hit);
        if (hit) hits += 1;
      });
      if (emptyBox) emptyBox.classList.toggle('visible', hits === 0);
    });
  }

  document.querySelectorAll('[data-track-filter]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-track-filter]').forEach(b => {
        const isAct = b === btn;
        b.classList.toggle('active', isAct);
        b.setAttribute('aria-selected', String(isAct));
      });
      applyHubFilters();
    });
  });

  const decSelect = document.getElementById('decision-filter');
  if (decSelect) decSelect.addEventListener('change', applyHubFilters);
  const sortSelect = document.getElementById('sort-select');
  if (sortSelect) sortSelect.addEventListener('change', applyHubFilters);

  const resetFiltersBtn = document.getElementById('reset-hub-filters');
  if (resetFiltersBtn) {
    resetFiltersBtn.addEventListener('click', () => {
      if (searchInput) searchInput.value = '';
      if (decSelect) decSelect.value = 'all';
      const allTab = document.querySelector('[data-track-filter="all"]');
      if (allTab) {
        document.querySelectorAll('[data-track-filter]').forEach(b => {
          const isAct = b === allTab;
          b.classList.toggle('active', isAct);
          b.setAttribute('aria-selected', String(isAct));
        });
      }
      applyHubFilters();
    });
  }

  // Keyboard accessibility for table rows (Enter opens the row link)
  document.querySelectorAll('.hub-row').forEach(row => {
    row.addEventListener('keydown', e => {
      if (e.key === 'Enter' && e.target === row && row.dataset.href) {
        window.location.href = row.dataset.href;
      }
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
          if (breakeven === null && net >= 0) breakeven = mo;
          if (exhausted === null && cash <= 0) exhausted = mo;
          rows.push({ mo, vol: Math.round(active), rev: Math.round(rev), net: Math.round(net), cash: Math.round(cash) });
          newCust *= (1 + growth);
        }
        const unitMargin = price * (1 - feeRate) - vc;
        const ltv = churn > 0 ? unitMargin / churn : null;
        return {
          rows, breakeven,
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
          if (breakeven === null && net >= 0) breakeven = mo;
          if (exhausted === null && cash <= 0) exhausted = mo;
          rows.push({ mo, vol: Math.round(units), rev: Math.round(rev), net: Math.round(net), cash: Math.round(cash) });
          units *= (1 + growth);
        }
        const unitMargin = price * (1 - feeRate) - vc;
        const ltv = unitMargin * repeat;
        return {
          rows, breakeven,
          lowestCash: Math.min(...rows.map(r => r.cash)),
          endingCash: rows[rows.length - 1].cash,
          grossMarginPct: price > 0 ? (unitMargin / price) * 100 : 0,
          ltvCac: cac > 0 ? ltv / cac : null,
          payback: (unitMargin > 0 && cac > 0) ? cac / (unitMargin * repeat) : null,
        };
      }
    }

    function renderSimChart(resMap) {
      const dark = document.documentElement.getAttribute('data-theme') === 'dark';
      const bg = dark ? '#0E1117' : '#F7F6F2';
      const gridCol = dark ? '#262E3D' : '#E4E1D9';
      const axisText = dark ? '#9AA4B2' : '#57534E';
      const legendText = dark ? '#F3F4F6' : '#18181B';
      const colors = dark
        ? { optimistic: '#FBBF24', base: '#60A5FA', pessimistic: '#F87171' }
        : { optimistic: '#1B365D', base: '#B45309', pessimistic: '#B91C1C' };
      const labels = {
        optimistic: LABELS.scenario_opt || 'Optimistic',
        base: LABELS.scenario_base || 'Base',
        pessimistic: LABELS.scenario_pess || 'Pessimistic',
      };
      const w = 660, h = 246, pl = 74, pr = 90, pt = 22, pb = 42;
      const pw = w - pl - pr, ph = h - pt - pb;
      const all = Object.values(resMap).flatMap(r => r.rows.map(x => x.cash)).concat([0]);
      const minV = Math.min(...all), maxV = Math.max(Math.max(...all), minV + 1);
      const xPos = idx => pl + (idx / (months - 1)) * pw;
      const yPos = v => pt + ph - ((v - minV) / (maxV - minV)) * ph;

      let svg = `<svg viewBox="0 0 ${w} ${h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="12-month cash balance simulation"><rect width="${w}" height="${h}" fill="${bg}"/>`;
      for (let s = 0; s <= 4; s++) {
        const v = minV + (maxV - minV) * (s / 4);
        const y = yPos(v).toFixed(1);
        svg += `<line x1="${pl}" y1="${y}" x2="${pl + pw}" y2="${y}" stroke="${gridCol}"/>`;
        svg += `<text x="${pl - 8}" y="${Number(y) + 3}" text-anchor="end" font-size="10" fill="${axisText}" font-family="sans-serif">${fmtShort(v)}</text>`;
      }
      if (minV < 0 && maxV > 0) {
        const y0 = yPos(0).toFixed(1);
        svg += `<line x1="${pl}" y1="${y0}" x2="${pl + pw}" y2="${y0}" stroke="${axisText}" stroke-dasharray="4,3"/>`;
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
        svg += `<text x="${Number(cx) + 7}" y="${Number(cy) + 3}" font-size="10" font-weight="600" fill="${colors[key]}" font-family="sans-serif">${fmtShort(last.cash)}</text>`;
        svg += `<line x1="${lxLegend}" y1="${h - 12}" x2="${lxLegend + 18}" y2="${h - 12}" stroke="${colors[key]}" stroke-width="2.4"${dash}/>`;
        svg += `<text x="${lxLegend + 24}" y="${h - 9}" font-size="10.5" fill="${legendText}" font-family="sans-serif">${labels[key]}</text>`;
        lxLegend += 116;
      });
      for (let m = 1; m <= months; m += 2) {
        svg += `<text x="${xPos(m - 1).toFixed(1)}" y="${pt + ph + 15}" text-anchor="middle" font-size="10" fill="${axisText}" font-family="sans-serif">M${m}</text>`;
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
      document.getElementById('sim-kpis').innerHTML = `
        <div class="kpi-card ${base.breakeven ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.breakeven || 'Break-Even'}</div><div class="kpi-val">${beTxt}</div><div class="kpi-sub">Pess: ${pess.breakeven ? 'M' + pess.breakeven : '-'}</div></div>
        <div class="kpi-card ${base.endingCash > 0 ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.ending_cash || 'Month-12 Cash'}</div><div class="kpi-val">${fmtShort(base.endingCash)}</div><div class="kpi-sub">${LABELS.lowest_cash || 'Lowest'}: ${fmtShort(base.lowestCash)}</div></div>
        <div class="kpi-card ${base.grossMarginPct >= 40 ? 'good' : ''}"><div class="kpi-label">${LABELS.gross_margin || 'Margin'}</div><div class="kpi-val">${base.grossMarginPct.toFixed(1)}%</div><div class="kpi-sub">${LABELS.payback || 'Payback'}: ${pbTxt}</div></div>
        <div class="kpi-card ${(base.ltvCac || 0) >= 3 ? 'good' : 'warn'}"><div class="kpi-label">${LABELS.ltv_cac || 'LTV / CAC'}</div><div class="kpi-val">${ltvTxt}</div><div class="kpi-sub">Pess M12: ${fmtShort(pess.endingCash)}</div></div>
      `;
      document.getElementById('sim-chart').innerHTML = renderSimChart(resMap);
      document.getElementById('sim-table-body').innerHTML = base.rows.map(r =>
        `<tr><td>M${r.mo}</td><td class="num">${fmtNum(r.vol)}</td><td class="num">${fmtNum(r.rev)}</td><td class="num">${fmtNum(r.net)}</td><td class="num"><strong>${fmtNum(r.cash)}</strong></td></tr>`
      ).join('');
    }
    window.__ideaforgeRedrawSim = updateSim;

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
        copyBtn.textContent = LABELS.copied || 'Copied';
        setTimeout(() => { copyBtn.textContent = orig; }, 1600);
      });
    }

    updateSim();
  }
})();
"""


def _theme_switch_html(lang: str) -> str:
    t = I18N[lang]
    return (
        '<div class="theme-switch" role="group" aria-label="Theme">'
        f'<button type="button" class="theme-opt" data-set-theme="light" aria-pressed="true">{SUN_SVG}<span>{html.escape(t["light_label"])}</span></button>'
        f'<button type="button" class="theme-opt" data-set-theme="dark" aria-pressed="false">{MOON_SVG}<span>{html.escape(t["dark_label"])}</span></button>'
        "</div>"
    )


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
            f'<div class="sim-control-head"><label for="{sid}">{html.escape(label)}</label>'
            f'<span class="sim-control-val" id="{sid}-val"></span></div>'
            f'<input id="{sid}" type="range" min="{mn}" max="{mx}" step="{step}" value="{val}">'
            f"</div>"
        )

    vol_label = "New Customers (M1)" if is_saas else "Month-1 Units"
    extra_slider = (
        _slider("sim-churn", "Monthly Churn", churn, 0.0, 0.30, 0.005)
        if is_saas
        else _slider("sim-repeat", "Repeat Orders", repeat, 1.0, 6.0, 0.1)
    )
    controls = "".join(
        [
            _slider("sim-price", f"Price ({currency})", price, max(1.0, round(price * 0.4)), max(10.0, round(price * 2.0)), max(1.0, round(price * 0.02))),
            _slider("sim-volume", vol_label, vol, max(1.0, round(vol * 0.2)), max(20.0, round(vol * 3.0)), 1.0),
            _slider("sim-vc", f"Variable Cost ({currency})", vc, 0.0, max(10.0, round(max(vc, price * 0.5) * 2.0)), max(1.0, round(max(vc, 100.0) * 0.02))),
            _slider("sim-fixed", f"Fixed Costs ({currency})", fixed, 0.0, max(100.0, round(max(fixed, 1000.0) * 2.5)), max(1.0, round(max(fixed, 1000.0) * 0.02))),
            _slider("sim-cac", f"CAC ({currency})", cac, 0.0, max(10.0, round(max(cac, price * 0.5) * 3.0)), max(1.0, round(max(cac, 100.0) * 0.02))),
            _slider("sim-growth", "Monthly Growth", growth, 0.0, 0.40, 0.01),
            extra_slider,
        ]
    )
    vol_col = "Active Cust." if is_saas else "Units"
    return (
        f'<section id="sim-panel" class="doc-panel">'
        f'<h1>{html.escape(t["simulator"])} ({ "SaaS" if is_saas else "Transactional" })</h1>'
        f'<p>{html.escape(t["sim_subtitle"])}</p>'
        f'<div class="sim-workbench">'
        f'  <div class="sim-controls-col">'
        f'    <div class="sim-controls-head"><h3>{html.escape(t["params_heading"])}</h3></div>'
        f'    {controls}'
        f'    <div class="sim-actions">'
        f'      <button type="button" id="sim-reset" class="btn">{html.escape(t["reset_sim"])}</button>'
        f'      <button type="button" id="sim-copy" class="btn btn-primary">{html.escape(t["copy_json"])}</button>'
        f'    </div>'
        f'  </div>'
        f'  <div>'
        f'    <div id="sim-kpis" class="kpi-grid" style="margin-top:0;"></div>'
        f'    <div id="sim-chart" class="sim-chart-box"></div>'
        f'    <details class="sim-details" open>'
        f'      <summary>{html.escape(t["monthly_table"])}</summary>'
        f'      <div class="table-wrap"><table><thead><tr>'
        f'      <th>Month</th><th class="num">{vol_col}</th><th class="num">Revenue ({html.escape(currency)})</th>'
        f'      <th class="num">Net Profit ({html.escape(currency)})</th><th class="num">Cash ({html.escape(currency)})</th>'
        f'      </tr></thead><tbody id="sim-table-body"></tbody></table></div>'
        f'    </details>'
        f'  </div>'
        f'</div>'
        f"</section>"
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
    """Compile one or more Markdown documents into a self-contained editorial Web GUI HTML string."""
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
        body_html = body_html.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")

        for k in tag_counts:
            tag_counts[k] += len(re.findall(rf'class="tag tag-{k}"', body_html))

        rendered_panels.append(f'<article id="{doc["id"]}" class="doc-panel">{body_html}</article>')
        sidebar_docs.append(
            f'<li><button type="button" class="rail-link" data-doc-target="{doc["id"]}">'
            f'<span>{html.escape(doc["label"])}</span></button></li>'
        )
        for level, sec_title, sec_id in toc:
            if level == 2:
                sidebar_sections.append(
                    f'<li><a class="rail-link rail-sub" data-sec-doc="{doc["id"]}" href="#{sec_id}">'
                    f'{html.escape(sec_title)}</a></li>'
                )

    if model_inputs:
        rendered_panels.append(_build_simulator_panel(model_inputs, lang))
        sidebar_docs.append(
            f'<li><button type="button" class="rail-link" data-doc-target="sim-panel">'
            f'<span>{html.escape(t["simulator"])}</span></button></li>'
        )

    # Evidence filter strip (rendered only when tags exist)
    ev_strip_html = ""
    if sum(tag_counts.values()) > 0:
        ev_btns = [f'<button type="button" class="ev-btn active" data-ev-filter="all">{html.escape(t["all_tags"])}</button>']
        for k, label in (("verified", "Verified"), ("estimate", "Estimate"), ("assumption", "Assumption"), ("unverified", "Unverified"), ("stale", "Stale")):
            if tag_counts[k] > 0:
                ev_btns.append(
                    f'<button type="button" class="ev-btn" data-ev-filter="{k}">{label} ({tag_counts[k]})</button>'
                )
        ev_strip_html = (
            f'<div class="evidence-strip">'
            f'<span class="evidence-label">{html.escape(t["evidence_filter"])}</span>'
            f'{"".join(ev_btns)}'
            f"</div>"
        )

    rail_footer_html = ""
    lint_drawer_html = ""
    if lint_info:
        status_cls = "audit-fail" if lint_info["fails"] else ("audit-warn" if lint_info["warns"] else "audit-ok")
        rail_footer_html = (
            f'<div class="rail-footer">'
            f'<button type="button" id="lint-toggle" class="audit-trigger" aria-expanded="false">'
            f'<span>{html.escape(t["quality_gates"])}</span>'
            f'<span class="audit-count {status_cls}">{lint_info["fails"]} FAIL / {lint_info["warns"]} WARN</span>'
            f"</button></div>"
        )
        rows_html = "".join(
            f'<div class="lint-row"><span class="tag tag-{"verified" if item["severity"]=="PASS" else ("assumption" if item["severity"]=="WARN" else "unverified")}">{item["severity"]}</span>'
            f'<span>{html.escape(item["message"])}</span></div>'
            for item in lint_info["items"]
        )
        lint_drawer_html = f'<section id="lint-drawer" class="lint-drawer" aria-label="{html.escape(t["quality_gates"])}">{rows_html}</section>'

    view_toggle_html = ""
    if len(rendered_panels) > 1:
        view_toggle_html = (
            '<div class="seg-control" role="group">'
            f'<button type="button" id="mode-tab">{html.escape(t["tab_view"])}</button>'
            f'<button type="button" id="mode-all">{html.escape(t["all_view"])}</button>'
            "</div>"
        )

    brand_left = (
        f'<a class="brand-link" href="{html.escape(hub_back_url)}">{BRAND_MARK_SVG}<span>{html.escape(t["back_hub"])}</span></a>'
        if hub_back_url
        else f'<span class="brand-link">{BRAND_MARK_SVG}<span>IdeaForge</span></span>'
    )
    dl_html_btn = (
        f'<a class="btn btn-dl-html" href="{html.escape(download_html_url)}">{html.escape(t["download_html"])}</a>'
        if download_html_url
        else ""
    )
    pdf_btn = (
        f'<a class="btn btn-primary" href="{html.escape(export_pdf_url)}">{html.escape(t["export_pdf_btn"])}</a>'
        if export_pdf_url
        else f'<button type="button" class="btn btn-primary" onclick="window.print()">{html.escape(t["print_pdf"])}</button>'
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
<html lang="{html.escape(lang)}" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} | IdeaForge</title>
<style>{WEB_CSS}</style>
</head>
<body>
<a class="skip-link" href="#main-content">Skip to content</a>

<header class="topbar">
  <div class="topbar-left">
    <button type="button" id="menu-toggle" class="btn btn-ghost menu-btn" aria-label="Menu" aria-expanded="false">&#9776;</button>
    {brand_left}
    <span class="crumb-sep">/</span>
    <span class="topbar-doc-name">{html.escape(title)}</span>
  </div>
  <div class="topbar-right">
    <button type="button" id="search-toggle" class="btn btn-ghost search-toggle-btn" aria-label="{html.escape(t['search_hub_placeholder'])}" aria-expanded="false">{SEARCH_SVG}</button>
    <div class="search-box">
      <span class="search-icon">{SEARCH_SVG}</span>
      <input id="search-input" class="search-input" type="search" placeholder="{html.escape(t['search_hub_placeholder'])}" aria-label="{html.escape(t['search_hub_placeholder'])}" autocomplete="off">
      <kbd class="kbd-hint">/</kbd>
    </div>
    {dl_html_btn}
    {pdf_btn}
    {_theme_switch_html(lang)}
  </div>
</header>

<div class="workspace">
  <aside id="sidebar" class="rail" aria-label="Document navigation">
    <div>
      {view_toggle_html}
      <div class="rail-group">
        <p class="rail-label">{html.escape(t['documents'])}</p>
        <ul class="rail-list">{"".join(sidebar_docs)}</ul>
      </div>
      {f'<div class="rail-group"><p class="rail-label">{html.escape(t["sections"])}</p><ul class="rail-list">{"".join(sidebar_sections)}</ul></div>' if sidebar_sections else ''}
    </div>
    {rail_footer_html}
  </aside>

  <main id="main-content" class="content-stage">
    <div class="sheet">
      <header class="doc-masthead">
        <p class="doc-category">{html.escape(kicker)}</p>
        <h1 class="doc-headline">{html.escape(title)}</h1>
        <div class="doc-meta-row">
          <span>{html.escape(meta)}</span>
          <span>{len(docs)} {html.escape(t['files_unit'])}</span>
        </div>
        {ev_strip_html}
      </header>

      {lint_drawer_html}

      <div id="empty-search" class="empty-search" role="status">
        <p style="margin:0 0 10px 0;">{html.escape(t['no_results'])}</p>
        <button type="button" id="clear-search-btn" class="btn">{html.escape(t['reset_search'])}</button>
      </div>

      {"".join(rendered_panels)}
    </div>
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
            latest_mtime = max(p.stat().st_mtime for p in mds)
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
                    "updated_ts": latest_mtime,
                    "updated_date": date.fromtimestamp(latest_mtime).isoformat(),
                }
            )

    _scan_project_root("prps", "prp", "executive")
    _scan_project_root("prds", "prd", "prd")
    _scan_project_root("ideas", "idea", "executive")

    sample_md = base_dir / "examples" / "sample-report" / "sample-executive-report.md"
    if sample_md.is_file():
        sample_mtime = sample_md.stat().st_mtime
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
                "updated_ts": sample_mtime,
                "updated_date": date.fromtimestamp(sample_mtime).isoformat(),
            }
        )
    return items


def _classify_decision(verdict: str | None, score: str | None, t: dict) -> tuple[str, str, str]:
    """Map raw verdict/score to semantic decision key, CSS class, and localized label."""
    if verdict:
        low = verdict.lower()
        if "no-go" in low or "no go" in low or "pivot" in low:
            return "nogo", "dec-nogo", t["dec_nogo"]
        if "condition" in low or "syarat" in low:
            return "conditional", "dec-conditional", t["dec_conditional"]
        if "go" in low:
            return "go", "dec-go", t["dec_go"]
    if score:
        try:
            val = float(score)
            if val >= 4.0:
                return "go", "dec-go", t["dec_go"]
            if val >= 3.0:
                return "conditional", "dec-conditional", t["dec_conditional"]
            return "nogo", "dec-nogo", t["dec_nogo"]
        except ValueError:
            pass
    return "pending", "dec-pending", t["dec_pending"]


def render_portfolio_hub(base_dir: Path, lang: str = "id") -> str:
    """Render the Notion-inspired Workspace Tenang Portfolio Hub for --serve mode."""
    t = I18N[lang]
    items = discover_workspace_items(base_dir)
    counts = {
        "prp": sum(1 for x in items if x["group"] == "prp"),
        "prd": sum(1 for x in items if x["group"] == "prd"),
        "idea": sum(1 for x in items if x["group"] == "idea"),
        "sample": sum(1 for x in items if x["group"] == "sample"),
    }

    type_labels = {
        "prp": "PRP",
        "prd": "PRD",
        "idea": t["tab_ideas"],
        "sample": t["tab_samples"],
    }

    numeric_scores: list[float] = []
    rows_html: list[str] = []
    cards_html: list[str] = []
    cmd_items: list[dict] = []

    for it in items:
        q_path = urllib.parse.quote(it["rel_path"])
        view_url = f'/view?path={q_path}&mode={it["mode"]}'
        dl_url = f'/api/download-html?path={q_path}&mode={it["mode"]}'
        pdf_url = f'/api/export-pdf?path={q_path}&mode={it["mode"]}'

        dec_key, dec_cls, dec_label = _classify_decision(it["verdict"], it["score"], t)

        score_num = -1.0
        if it["score"]:
            try:
                score_num = float(it["score"])
                numeric_scores.append(score_num)
                pct = max(0.0, min(100.0, (score_num / 5.0) * 100.0))
                score_disp = f"{score_num:.2f}"
                score_aria = f"{t['score_label']} {score_disp.replace('.', ',')} dari 5" if lang == "id" else f"Score {score_disp} out of 5"
                score_cell = (
                    f'<div class="score-cell" aria-label="{html.escape(score_aria)}">'
                    f'<div class="score-num">{score_disp}</div>'
                    f'<div class="score-track" aria-hidden="true"><div class="score-fill-bar" style="width:{pct:.0f}%"></div></div>'
                    f"</div>"
                )
            except ValueError:
                score_cell = f'<span class="muted-text">{html.escape(t["no_score"])}</span>'
        else:
            score_cell = f'<span class="muted-text">{html.escape(t["no_score"])}</span>'

        base_type = type_labels.get(it["group"], it["group"].upper())
        combined_type = f"{base_type} · {t['sim_badge']}" if it["has_sim"] else base_type
        type_title = t["sim_tooltip"] if it["has_sim"] else base_type
        type_html = f'<span class="badge-combined" title="{html.escape(type_title)}">{html.escape(combined_type)}</span>'

        decision_html = (
            f'<span class="decision-pill {dec_cls}">'
            f'<span class="decision-dot" aria-hidden="true"></span>'
            f'<span>{html.escape(dec_label)}</span></span>'
        )

        if it["lint"]:
            f_cnt, w_cnt = it["lint"]["fails"], it["lint"]["warns"]
            if f_cnt == 0 and w_cnt == 0:
                audit_html = f'<span class="audit-nowrap muted-text">{html.escape(t["audit_pass"])}</span>'
            elif f_cnt > 0:
                audit_html = f'<span class="audit-nowrap decision-pill dec-nogo">{f_cnt}F · {w_cnt}W</span>'
            else:
                audit_html = f'<span class="audit-nowrap decision-pill dec-conditional">{w_cnt}W</span>'
        else:
            audit_html = f'<span class="audit-nowrap muted-text">{html.escape(t["not_audited"])}</span>'

        rows_html.append(
            f'<tr class="hub-row" tabindex="0" data-href="{view_url}" '
            f'data-track="{it["group"]}" data-decision="{dec_key}" '
            f'data-score="{score_num}" data-title="{html.escape(it["title"].lower())}" '
            f'data-updated="{it["updated_ts"]:.0f}">'
            f'  <td class="db-doc-cell">'
            f'    <div class="db-doc-row">'
            f'      <span class="db-doc-icon">{FILE_SVG}</span>'
            f'      <div class="db-doc-meta">'
            f'        <a class="db-doc-title" href="{view_url}">{html.escape(it["title"])}</a>'
            f'        <div class="db-doc-path" title="{html.escape(it["rel_path"])}">{html.escape(it["rel_path"])}</div>'
            f'      </div>'
            f'    </div>'
            f"  </td>"
            f'  <td>{type_html}</td>'
            f'  <td>{score_cell}</td>'
            f'  <td>{decision_html}</td>'
            f'  <td>{audit_html}</td>'
            f'  <td class="db-actions-cell"><div class="row-actions">'
            f'    <a class="icon-action-btn" href="{dl_url}" title="Unduh HTML" aria-label="Unduh HTML {html.escape(it["title"])}">{DOWNLOAD_SVG}</a>'
            f'    <a class="icon-action-btn" href="{pdf_url}" title="Unduh PDF" aria-label="Unduh PDF {html.escape(it["title"])}">{FILE_SVG}</a>'
            f"  </div></td>"
            f"</tr>"
        )

        cards_html.append(
            f'<article class="gallery-card" tabindex="0" data-href="{view_url}" '
            f'data-track="{it["group"]}" data-decision="{dec_key}" '
            f'data-score="{score_num}" data-title="{html.escape(it["title"].lower())}" '
            f'data-updated="{it["updated_ts"]:.0f}">'
            f'  <div>'
            f'    <div style="margin-bottom:8px;">{type_html}</div>'
            f'    <a class="db-doc-title" href="{view_url}">{html.escape(it["title"])}</a>'
            f'    <div class="db-doc-path" title="{html.escape(it["rel_path"])}">{html.escape(it["rel_path"])}</div>'
            f'  </div>'
            f'  <div style="display:flex;align-items:center;justify-content:space-between;gap:12px;">'
            f'    {score_cell}{decision_html}'
            f'  </div>'
            f'  <div class="gallery-card-foot">'
            f'    {audit_html}'
            f'    <div style="display:inline-flex;gap:6px;">'
            f'      <a class="icon-action-btn" href="{dl_url}" title="Unduh HTML" aria-label="Unduh HTML {html.escape(it["title"])}">{DOWNLOAD_SVG}</a>'
            f'      <a class="icon-action-btn" href="{pdf_url}" title="Unduh PDF" aria-label="Unduh PDF {html.escape(it["title"])}">{FILE_SVG}</a>'
            f'    </div>'
            f'  </div>'
            f"</article>"
        )

        cmd_items.append({"title": it["title"], "path": it["rel_path"], "type": base_type, "href": view_url})

    # Single-line summary below title
    summary_parts = [f'<span class="mono-num">{len(items)}</span> {t["files_unit"]}']
    if numeric_scores:
        avg_s = sum(numeric_scores) / len(numeric_scores)
        avg_str = f"{avg_s:.2f}".replace(".", ",") if lang == "id" else f"{avg_s:.2f}"
        summary_parts.append(f'rata-rata skor <span class="mono-num">{avg_str}</span>' if lang == "id" else f'avg score <span class="mono-num">{avg_str}</span>')
    if items:
        newest_date = max(it["updated_date"] for it in items)
        summary_parts.append(f'diperbarui <span class="mono-num">{html.escape(newest_date)}</span>' if lang == "id" else f'updated <span class="mono-num">{html.escape(newest_date)}</span>')
    summary_line = " &middot; ".join(summary_parts)

    # Sidebar collections & recent items
    collections_nav = [
        ("prp", "PRP", counts["prp"], FOLDER_SVG),
        ("prd", "PRD", counts["prd"], FILE_CHECK_SVG),
        ("idea", t["tab_ideas"], counts["idea"], LIGHTBULB_SVG),
        ("sample", t["tab_samples"], counts["sample"], BOOK_OPEN_SVG),
    ]
    coll_html = "".join(
        f'<li><button type="button" class="nav-item-btn" data-nav-track="{key}" title="{html.escape(lbl)}">'
        f'<span class="nav-item-left">{icon}<span class="nav-label">{html.escape(lbl)}</span></span>'
        f'<span class="nav-count">{cnt}</span></button></li>'
        for key, lbl, cnt, icon in collections_nav
    )

    recent_sorted = sorted(items, key=lambda x: x["updated_ts"], reverse=True)[:5]
    recent_section_html = ""
    if recent_sorted:
        rec_lis = "".join(
            f'<li><a class="nav-item-btn" href="/view?path={urllib.parse.quote(r["rel_path"])}&mode={r["mode"]}" title="{html.escape(r["title"])}">'
            f'<span class="nav-item-left">{FILE_SVG}<span class="nav-label">{html.escape(r["title"])}</span></span></a></li>'
            for r in recent_sorted
        )
        recent_section_html = (
            f'<div class="sidebar-section sidebar-recent-group">'
            f'<p class="sidebar-section-label">Terbaru</p>'
            f'<ul class="sidebar-list">{rec_lis}</ul>'
            f"</div>"
        )

    collections_meta = {
        "all": {"title": "Semua dokumen" if lang == "id" else "All documents", "desc": t["hub_subtitle"], "crumb": "<strong>Semua dokumen</strong>" if lang == "id" else "<strong>All documents</strong>"},
        "prp": {"title": "Koleksi: PRP" if lang == "id" else "Collection: PRP", "desc": "Project Requirements & Plan lengkap untuk produk dan kelayakan bisnis.", "crumb": 'Koleksi / <strong>PRP</strong>'},
        "prd": {"title": "Koleksi: PRD" if lang == "id" else "Collection: PRD", "desc": "Product Requirements Document siap implementasi untuk tim dan coding agent.", "crumb": 'Koleksi / <strong>PRD</strong>'},
        "idea": {"title": "Koleksi: Ide" if lang == "id" else "Collection: Ideas", "desc": "Catatan eksplorasi awal dan ringkasan brainstorming.", "crumb": 'Koleksi / <strong>Ide</strong>'},
        "sample": {"title": "Koleksi: Contoh" if lang == "id" else "Collection: Samples", "desc": "Contoh laporan eksekutif beserta model finansial untuk evaluasi.", "crumb": 'Koleksi / <strong>Contoh</strong>'},
    }

    decision_labels_map = {
        "go": t["dec_go"],
        "conditional": t["dec_conditional"],
        "nogo": t["dec_nogo"],
        "pending": t["dec_pending"],
    }

    table_section = (
        f'<div id="db-table-wrap" class="db-table-wrap">'
        f'<table class="db-table"><thead><tr>'
        f'<th>{html.escape(t["col_project"])}</th>'
        f'<th>{html.escape(t["col_track"])}</th>'
        f'<th>{html.escape(t["col_score"])}</th>'
        f'<th>{html.escape(t["col_decision"])}</th>'
        f'<th>{html.escape(t["col_audit"])}</th>'
        f'<th class="db-actions-cell"></th>'
        f'</tr></thead><tbody id="hub-tbody">{"".join(rows_html)}</tbody></table></div>'
        f'<div id="db-gallery" class="db-gallery">{"".join(cards_html)}</div>'
        if rows_html
        else f'<div class="hub-empty"><p style="margin:0;">{html.escape(t["empty_hub"])}</p></div>'
    )

    hub_payload = {
        "locale": lang,
        "labels": {**t, "theme_light": "Tema: Terang" if lang == "id" else "Theme: Light", "theme_dark": "Tema: Gelap" if lang == "id" else "Theme: Dark"},
        "collections": collections_meta,
        "decisionLabels": decision_labels_map,
        "typeLabels": type_labels,
        "hubItems": cmd_items,
        "sunSvg": SUN_SVG,
        "moonSvg": MOON_SVG,
    }
    safe_hub_json = json.dumps(hub_payload).replace("</", "<\\/")

    return f"""<!DOCTYPE html>
<html lang="{html.escape(lang)}" data-theme="light">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(t['hub_title'])}</title>
<style>{WEB_CSS}</style>
</head>
<body>
<a class="skip-link" href="#main-content">Lewati ke konten utama</a>

<div id="drawer-backdrop" class="drawer-backdrop"></div>

<div id="hub-app" class="hub-app">
  <aside id="hub-sidebar" class="hub-sidebar">
    <div>
      <div class="ws-switcher">
        <a class="ws-brand" href="/">{BRAND_MARK_SVG}<span class="ws-brand-text">IdeaForge</span></a>
        <button type="button" id="hub-collapse-btn" class="collapse-btn" title="Ciutkan sidebar ([)" aria-label="Ciutkan sidebar" aria-expanded="true">{PANEL_LEFT_SVG}</button>
      </div>

      <button type="button" id="hub-search-trigger" class="nav-item-btn" title="Cari (/)">
        <span class="nav-item-left">{SEARCH_SVG}<span class="nav-label">Cari</span></span>
        <kbd class="nav-kbd">/</kbd>
      </button>

      <nav aria-label="Navigasi utama" style="margin-top:8px;">
        <ul class="sidebar-list">
          <li>
            <button type="button" class="nav-item-btn active" data-nav-track="all" aria-current="page" title="Semua dokumen">
              <span class="nav-item-left">{LAYERS_SVG}<span class="nav-label">Semua dokumen</span></span>
              <span class="nav-count">{len(items)}</span>
            </button>
          </li>
        </ul>

        <div class="sidebar-section">
          <p class="sidebar-section-label">Koleksi</p>
          <ul class="sidebar-list">{coll_html}</ul>
        </div>

        {recent_section_html}
      </nav>
    </div>

    <div class="sidebar-footer">
      <button type="button" id="hub-theme-toggle" class="nav-item-btn" title="Ganti tema">
        <span class="nav-item-left">
          <span id="hub-theme-icon" style="display:inline-flex;">{SUN_SVG}</span>
          <span id="hub-theme-label" class="nav-label">Tema: Terang</span>
        </span>
      </button>
      <div class="sidebar-version">IdeaForge v1.0</div>
    </div>
  </aside>

  <div class="hub-main">
    <div class="hub-topbar">
      <div class="hub-topbar-left">
        <button type="button" id="hub-hamburger" class="hub-hamburger" aria-label="Buka menu navigasi" aria-expanded="false">{MENU_SVG}</button>
        <div id="hub-breadcrumb" class="hub-breadcrumb"><strong>Semua dokumen</strong></div>
      </div>
    </div>

    <main id="main-content" class="hub-content">
      <header class="hub-page-header">
        <h1 id="hub-page-title">Semua dokumen</h1>
        <p id="hub-page-desc" class="hub-page-desc">{html.escape(t['hub_subtitle'])}</p>
        <p class="hub-summary-line">{summary_line}</p>
      </header>

      <div class="db-toolbar">
        <div class="view-seg" role="group" aria-label="Mode tampilan">
          <button type="button" id="view-table-btn" class="view-seg-btn" aria-pressed="true">{TABLE_SVG}<span>Tabel</span></button>
          <button type="button" id="view-gallery-btn" class="view-seg-btn" aria-pressed="false">{GRID_SVG}<span>Galeri</span></button>
        </div>

        <div class="db-toolbar-right">
          <div class="popover-anchor">
            <button type="button" id="filter-pop-btn" class="toolbar-btn" aria-expanded="false" aria-haspopup="true">{SLIDERS_SVG}<span>Filter</span></button>
            <div id="filter-popover" class="popover-menu" role="dialog" aria-label="Filter dokumen">
              <div class="pop-group">
                <p class="pop-label">Keputusan</p>
                <button type="button" class="pop-opt active" data-pop-decision="all">Semua keputusan</button>
                <button type="button" class="pop-opt" data-pop-decision="go">{html.escape(t['dec_go'])}</button>
                <button type="button" class="pop-opt" data-pop-decision="conditional">{html.escape(t['dec_conditional'])}</button>
                <button type="button" class="pop-opt" data-pop-decision="nogo">{html.escape(t['dec_nogo'])}</button>
                <button type="button" class="pop-opt" data-pop-decision="pending">{html.escape(t['dec_pending'])}</button>
              </div>
              <div class="pop-group">
                <p class="pop-label">Tipe</p>
                <button type="button" class="pop-opt active" data-pop-type="all">Semua tipe</button>
                <button type="button" class="pop-opt" data-pop-type="prp">PRP</button>
                <button type="button" class="pop-opt" data-pop-type="prd">PRD</button>
                <button type="button" class="pop-opt" data-pop-type="idea">{html.escape(t['tab_ideas'])}</button>
                <button type="button" class="pop-opt" data-pop-type="sample">{html.escape(t['tab_samples'])}</button>
              </div>
            </div>
          </div>

          <div class="popover-anchor">
            <button type="button" id="sort-pop-btn" class="toolbar-btn" aria-expanded="false" aria-haspopup="true">{ARROW_UP_DOWN_SVG}<span>Urutkan</span></button>
            <div id="sort-popover" class="popover-menu" role="dialog" aria-label="Urutkan dokumen">
              <div class="pop-group">
                <p class="pop-label">Urutkan berdasarkan</p>
                <button type="button" class="pop-opt active" data-pop-sort="newest">{html.escape(t['sort_newest'])}</button>
                <button type="button" class="pop-opt" data-pop-sort="score">{html.escape(t['sort_score'])}</button>
                <button type="button" class="pop-opt" data-pop-sort="name">{html.escape(t['sort_name'])}</button>
              </div>
            </div>
          </div>

          <div class="db-local-search">
            {SEARCH_SVG}
            <input id="db-local-search" class="db-local-input" type="search" placeholder="Saring daftar..." aria-label="Saring daftar dokumen" autocomplete="off">
          </div>
        </div>
      </div>

      <div id="active-chips" class="active-chips"></div>

      {table_section}

      <div id="empty-search" class="empty-hub-state" role="status">
        <p id="empty-hub-msg" style="margin:0 0 12px 0;">{html.escape(t['empty_filtered'])}</p>
        <button type="button" id="reset-hub-filters" class="btn">{html.escape(t['reset_filters'])}</button>
      </div>
    </main>
  </div>
</div>

<div id="cmd-backdrop" class="cmd-backdrop" role="dialog" aria-modal="true" aria-label="Pencarian cepat dokumen">
  <div class="cmd-modal">
    <div class="cmd-input-row">
      {SEARCH_SVG}
      <input id="cmd-input" class="cmd-input" type="search" placeholder="Cari dokumen berdasarkan judul atau path..." autocomplete="off">
      <kbd class="nav-kbd">Esc</kbd>
    </div>
    <div id="cmd-results" class="cmd-results"></div>
  </div>
</div>

<script>window.__IDEAFORGE_DATA__ = {safe_hub_json};</script>
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
            return

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
