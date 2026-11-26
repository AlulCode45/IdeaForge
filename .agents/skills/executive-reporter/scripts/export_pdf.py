#!/usr/bin/env python3
"""Export a Markdown report, PRD folder, or PRP folder to an interactive, visual, print-ready PDF.

Uses only Python stdlib + headless Chromium (Brave / Chrome) --print-to-pdf.
Usage:
  python3 export_pdf.py --input report.md --output report.pdf [--title "Title"] [--toc]
  python3 export_pdf.py --project prps/<slug> --output prps/<slug>/assets/report.pdf [--mode executive|technical|full|prd]
  python3 export_pdf.py --project prds/<slug> --output prds/<slug>/assets/prd.pdf --mode prd
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

BROWSER_CANDIDATES = [
    os.environ.get("PDF_BROWSER"),
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    shutil.which("google-chrome"),
    shutil.which("chromium"),
    shutil.which("brave-browser"),
]

SECTION_MODES = {
    "executive": [
        "18-executive-summary.md",
        "17-scorecard-and-decision.md",
        "PRD.md",
        "00-overview.md",
        "07-market-research.md",
        "15-competitor-analysis.md",
        "14-customer-discovery.md",
        "08-swot.md",
        "09-opportunity-analysis.md",
        "10-management-plan.md",
        "11-financial-plan.md",
        "16-compliance-and-legal.md",
        "12-go-to-market-and-risk.md",
        "13-assumption-register.md",
        "19-retrospective.md",
    ],
    "prd": [
        "PRD.md",
        "00-overview.md",
        "01-users-and-flows.md",
        "02-requirements.md",
        "13-assumption-register.md",
    ],
    "technical": [
        "00-overview.md",
        "01-users-and-flows.md",
        "02-requirements.md",
        "PRD.md",
        "03-architecture.md",
        "04-data-model.md",
        "05-roadmap-and-tasks.md",
        "06-risks-and-mitigation.md",
        "13-assumption-register.md",
        "17-scorecard-and-decision.md",
    ],
    "full": [
        "18-executive-summary.md",
        "PRD.md",
        "00-overview.md",
        "01-users-and-flows.md",
        "02-requirements.md",
        "03-architecture.md",
        "04-data-model.md",
        "05-roadmap-and-tasks.md",
        "06-risks-and-mitigation.md",
        "07-market-research.md",
        "15-competitor-analysis.md",
        "14-customer-discovery.md",
        "08-swot.md",
        "09-opportunity-analysis.md",
        "10-management-plan.md",
        "11-financial-plan.md",
        "16-compliance-and-legal.md",
        "12-go-to-market-and-risk.md",
        "13-assumption-register.md",
        "17-scorecard-and-decision.md",
        "19-retrospective.md",
    ],
}

BASE_CSS = """
@page {
  size: A4;
  margin: 20mm;
  @bottom-left {
    content: "__FOOTER_TITLE__";
    font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 8pt;
    color: #5B6470;
  }
  @bottom-right {
    content: "__PAGE_LABEL__";
    font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 8pt;
    color: #5B6470;
  }
}
@page :first {
  @bottom-left { content: none; }
}
* { box-sizing: border-box; }
body {
  font-family: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  font-size: 9.8pt;
  line-height: 1.6;
  color: #1B1F24;
  margin: 0;
  padding: 0;
  background: #FFFFFF;
}
.cover-page {
  border-top: 3px solid #12263F;
  padding-top: 24px;
  margin-bottom: 18px;
}
.doc-header {
  border-bottom: 1.5px solid #DDD8CE;
  padding-bottom: 12px;
  margin-bottom: 18px;
}
.doc-kicker {
  font-size: 8.5pt;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #5B6470;
  margin: 0 0 6px 0;
}
.doc-title {
  font-family: "Source Serif 4", Georgia, "Times New Roman", serif;
  font-size: 20pt;
  font-weight: 600;
  line-height: 1.2;
  letter-spacing: -0.01em;
  color: #12263F;
  margin: 0 0 8px 0;
}
.doc-meta {
  font-size: 8.5pt;
  color: #5B6470;
  margin: 0;
}
.toc-box {
  background: #F8FAFC;
  border: 1px solid #D9DEE5;
  border-left: 4px solid #1B365D;
  padding: 14px 18px;
  margin: 14px 0 20px 0;
  break-inside: avoid;
}
.toc-title {
  font-size: 9.5pt;
  font-weight: 700;
  color: #1B365D;
  margin: 0 0 8px 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.toc-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 9pt;
  column-count: 1;
}
.toc-list li {
  margin: 4px 0;
  padding: 2px 0;
  border-bottom: 1px dotted #E2E8F0;
}
.toc-list li.toc-h2 {
  padding-left: 14px;
  color: #4B5563;
  font-size: 8.5pt;
  border-bottom: none;
}
.toc-list a {
  color: #1B365D;
  text-decoration: none;
  font-weight: 600;
}
.toc-list li.toc-h2 a { font-weight: 400; color: #374151; }
h1 {
  font-size: 14.5pt;
  font-weight: 700;
  color: #111317;
  border-bottom: 1.5px solid #1B365D;
  padding-bottom: 5px;
  margin: 20px 0 10px 0;
  break-after: avoid;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}
.back-toc {
  font-size: 7.5pt;
  font-weight: 500;
  color: #6B7280;
  text-decoration: none;
  margin-left: 12px;
  white-space: nowrap;
}
h2 {
  font-size: 11.5pt;
  font-weight: 700;
  color: #1B365D;
  margin: 16px 0 8px 0;
  break-after: avoid;
}
h3 {
  font-size: 10pt;
  font-weight: 600;
  color: #1A1D21;
  margin: 12px 0 6px 0;
  break-after: avoid;
}
h4 {
  font-size: 9.5pt;
  font-weight: 600;
  color: #374151;
  margin: 10px 0 4px 0;
  break-after: avoid;
}
p { margin: 0 0 8px 0; }
ul, ol { margin: 0 0 10px 0; padding-left: 18px; }
li { margin-bottom: 4px; }
.callout-rec {
  background: #EFF6FF;
  border: 1px solid #BFDBFE;
  border-left: 4px solid #1B365D;
  padding: 10px 14px;
  margin: 10px 0 14px 0;
  border-radius: 3px;
  break-inside: avoid;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin: 10px 0 14px 0;
  break-inside: avoid;
}
.kpi-card {
  background: #F8FAFC;
  border: 1px solid #E2E8F0;
  border-top: 3px solid #1B365D;
  padding: 8px 10px;
  border-radius: 2px;
}
.kpi-card.warn { border-top-color: #B91C1C; background: #FEF2F2; }
.kpi-card.good { border-top-color: #15803D; background: #F0FDF4; }
.kpi-label {
  font-size: 7.5pt;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #64748B;
  margin-bottom: 2px;
}
.kpi-val {
  font-size: 11.5pt;
  font-weight: 700;
  color: #0F172A;
}
.kpi-sub {
  font-size: 7.5pt;
  color: #475569;
  margin-top: 2px;
}
blockquote {
  margin: 10px 0;
  padding: 9px 13px;
  background: #F8FAFC;
  border-left: 3.5px solid #1B365D;
  color: #2C313A;
  font-size: 9.2pt;
  break-inside: avoid;
}
blockquote.callout-warn {
  background: #FEF2F2;
  border-left-color: #B91C1C;
  color: #7F1D1D;
}
blockquote p:last-child { margin-bottom: 0; }
table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px 0;
  font-size: 8.8pt;
}
thead { display: table-header-group; }
tr { break-inside: avoid; }
th {
  background: #F1F5F9;
  color: #0F172A;
  font-weight: 600;
  text-align: left;
  padding: 6px 8px;
  border-top: 1.5px solid #1B365D;
  border-bottom: 1px solid #B8C0CC;
}
td {
  padding: 6px 8px;
  border-bottom: 1px solid #E5E8ED;
  vertical-align: top;
}
tr:last-child td { border-bottom: 1px solid #B8C0CC; }
td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
.score-bar-wrap {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.score-bar {
  width: 48px;
  height: 7px;
  background: #E2E8F0;
  border-radius: 3px;
  overflow: hidden;
  display: inline-block;
}
.score-fill {
  height: 100%;
  background: #1B365D;
}
code {
  font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
  font-size: 8.3pt;
  background: #F4F6F8;
  padding: 1px 4px;
  border-radius: 2px;
}
pre {
  background: #F7F8FA;
  border: 1px solid #E5E8ED;
  padding: 10px 12px;
  font-size: 8.3pt;
  overflow-x: auto;
  break-inside: avoid;
}
pre code { background: none; padding: 0; }
.mermaid-block {
  margin: 12px 0;
  text-align: center;
  break-inside: avoid;
}
.mermaid-fallback {
  text-align: left;
  background: #F7F8FA;
  border: 1px solid #D9DEE5;
  padding: 10px 12px;
  font-family: "SF Mono", Menlo, monospace;
  font-size: 8pt;
  white-space: pre-wrap;
}
hr {
  border: 0;
  border-top: 1px solid #D9DEE5;
  margin: 16px 0;
}
img, svg {
  max-width: 100%;
  height: auto;
  display: block;
  margin: 10px auto;
  break-inside: avoid;
}
.tag {
  font-family: "SF Mono", Menlo, monospace;
  font-size: 7.2pt;
  font-weight: 600;
  padding: 1px 5px;
  border: 1px solid #CBD5E1;
  color: #334155;
  background: #F8FAFC;
  border-radius: 3px;
  white-space: nowrap;
}
.tag-verified { background: #DCFCE7; border-color: #86EFAC; color: #166534; }
.tag-estimate { background: #DBEAFE; border-color: #93C5FD; color: #1E40AF; }
.tag-assumption { background: #FEF3C7; border-color: #FCD34D; color: #92400E; }
.tag-unverified, .tag-stale { background: #FEE2E2; border-color: #FCA5A5; color: #991B1B; }
.page-break { break-before: page; }
a { color: #1B365D; text-decoration: none; }
"""


def find_browser() -> str:
    for path in BROWSER_CANDIDATES:
        if path and os.path.exists(path):
            return path
    raise RuntimeError("No Chromium-based browser (Brave/Chrome) found for PDF export.")


def format_inline(text: str) -> str:
    text = html.escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)

    def _tag_repl(m):
        lbl = m.group(1)
        cls = f"tag tag-{lbl.lower()}"
        return f'<span class="{cls}">{lbl}</span>'

    text = re.sub(r"\[(Verified|Estimate|Assumption|Unverified|Stale|Contoh)\]", _tag_repl, text)
    return text


def is_numeric_cell(cell: str) -> bool:
    s = cell.strip().replace(",", "").replace(".", "").replace("%", "").replace("+", "").replace("-", "")
    return bool(s) and s.isdigit()


def slugify(text: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    return re.sub(r"[\s-]+", "-", s) or "section"


def md_to_html(md_text: str, base_dir: Path, add_back_to_toc: bool = False, lang: str = "id") -> tuple[str, list[tuple[int, str, str]], bool]:
    lines = md_text.splitlines()
    out = []
    toc = []
    has_mermaid = False
    list_stack: list[tuple[str, int]] = []
    seen_ids: dict[str, int] = {}
    i = 0

    def close_lists(target_indent: int = -1):
        while list_stack and list_stack[-1][1] >= target_indent:
            tag, _ = list_stack.pop()
            out.append(f"</{tag}>")

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        # KPI Grid block: <!-- kpi-grid --> ... <!-- /kpi-grid -->
        # Lines inside: Label | Value | Subtext | tone(optional: good/warn)
        if stripped == "<!-- kpi-grid -->":
            close_lists()
            cards = []
            i += 1
            while i < len(lines) and lines[i].strip() != "<!-- /kpi-grid -->":
                row = lines[i].strip()
                if row and "|" in row:
                    parts = [p.strip() for p in row.split("|")]
                    lbl = html.escape(parts[0])
                    val = html.escape(parts[1]) if len(parts) > 1 else ""
                    sub = html.escape(parts[2]) if len(parts) > 2 else ""
                    tone = parts[3].lower() if len(parts) > 3 and parts[3].lower() in ("good", "warn") else ""
                    cls = f"kpi-card {tone}".strip()
                    cards.append(
                        f'<div class="{cls}">'
                        f'<div class="kpi-label">{lbl}</div>'
                        f'<div class="kpi-val">{val}</div>'
                        f'<div class="kpi-sub">{sub}</div>'
                        f"</div>"
                    )
                i += 1
            out.append('<div class="kpi-grid">' + "".join(cards) + "</div>")
            i += 1
            continue

        # Raw SVG block passthrough
        if stripped.startswith("<svg"):
            close_lists()
            svg_lines = [line]
            while i + 1 < len(lines) and "</svg>" not in lines[i]:
                i += 1
                svg_lines.append(lines[i])
            out.append("\n".join(svg_lines))
            i += 1
            continue

        # Page break marker
        if stripped == "<!-- pagebreak -->":
            close_lists()
            out.append('<div class="page-break"></div>')
            i += 1
            continue

        # Fenced code block (including mermaid)
        if stripped.startswith("```"):
            close_lists()
            fence_lang = stripped[3:].strip().lower()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            if fence_lang == "mermaid":
                has_mermaid = True
                src = html.escape("\n".join(code_lines))
                out.append(f'<div class="mermaid-block"><div class="mermaid">{src}</div></div>')
            elif fence_lang:
                out.append(f'<pre><code class="language-{html.escape(fence_lang)}">' + html.escape("\n".join(code_lines)) + "</code></pre>")
            else:
                out.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
            i += 1
            continue

        # Blank line
        if not stripped:
            close_lists()
            i += 1
            continue

        # Horizontal rule
        if stripped in ("---", "***", "___"):
            close_lists()
            out.append("<hr>")
            i += 1
            continue

        # Headings (# to ####)
        m = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if m:
            close_lists()
            level = len(m.group(1))
            raw_title = m.group(2).strip()
            base_id = slugify(raw_title)
            count = seen_ids.get(base_id, 0) + 1
            seen_ids[base_id] = count
            sec_id = base_id if count == 1 else f"{base_id}-{count}"
            if level <= 2:
                toc.append((level, raw_title, sec_id))
            back_label = "&#8593; Contents" if lang == "en" else "&#8593; Daftar Isi"
            back_link = f'<a class="back-toc" href="#toc-top">{back_label}</a>' if (level == 1 and add_back_to_toc) else ""
            out.append(f'<h{level} id="{sec_id}"><span>{format_inline(raw_title)}</span>{back_link}</h{level}>')
            i += 1
            continue

        # Image
        img_m = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)$", stripped)
        if img_m:
            close_lists()
            alt = html.escape(img_m.group(1))
            src = img_m.group(2)
            if not src.startswith(("http://", "https://", "file://", "/")):
                src = (base_dir / src).resolve().as_uri()
            out.append(f'<img src="{src}" alt="{alt}">')
            i += 1
            continue

        # Markdown table (with automatic score bar if column header is Score (1-5) / Skor (1-5))
        if "|" in stripped and i + 1 < len(lines) and re.match(r"^\|?[\s:|-]+\|[\s:|-]*$", lines[i + 1].strip()):
            close_lists()
            headers = [c.strip() for c in stripped.strip("|").split("|")]
            i += 2
            rows = []
            while i < len(lines) and "|" in lines[i].strip():
                row = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(row)
                i += 1
            num_cols = set()
            score_col = None
            for col_idx, h_txt in enumerate(headers):
                if "score (1-5)" in h_txt.lower() or "skor (1-5)" in h_txt.lower():
                    score_col = col_idx
                elif rows and all(col_idx < len(r) and is_numeric_cell(r[col_idx]) for r in rows):
                    num_cols.add(col_idx)
            tbl = ["<table><thead><tr>"]
            for idx, h in enumerate(headers):
                cls = ' class="num"' if idx in num_cols else ""
                tbl.append(f'<th scope="col"{cls}>{format_inline(h)}</th>')
            tbl.append("</tr></thead><tbody>")
            for r in rows:
                tbl.append("<tr>")
                for idx in range(len(headers)):
                    val = r[idx] if idx < len(r) else ""
                    if idx == score_col and re.fullmatch(r"\d+(?:[.,]\d+)?", val.strip()):
                        sc = float(val.strip().replace(",", "."))
                        pct = max(0.0, min(100.0, sc / 5.0 * 100.0))
                        cell_html = (
                            f'<span class="score-bar-wrap"><strong>{html.escape(val)}</strong>'
                            f'<span class="score-bar"><span class="score-fill" style="width:{pct:.0f}%"></span></span></span>'
                        )
                        tbl.append(f"<td>{cell_html}</td>")
                    else:
                        cls = ' class="num"' if idx in num_cols else ""
                        tbl.append(f"<td{cls}>{format_inline(val)}</td>")
                tbl.append("</tr>")
            tbl.append("</tbody></table>")
            out.append("".join(tbl))
            continue

        # Blockquote (highlight warning/kritis blockquotes)
        if stripped.startswith(">"):
            close_lists()
            bq_lines = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                bq_lines.append(format_inline(lines[i].strip().lstrip(">").strip()))
                i += 1
            joined = "<br>".join(bq_lines)
            is_warn = any(k in joined.lower() for k in ("kritis", "warning", "bahaya", "blocker", "shortfall"))
            cls = ' class="callout-warn"' if is_warn else ""
            out.append(f"<blockquote{cls}><p>{joined}</p></blockquote>")
            continue

        # Unordered or Ordered list (with nesting support)
        ul_m = re.match(r"^[-*]\s+(.*)$", stripped)
        ol_m = re.match(r"^\d+\.\s+(.*)$", stripped)
        if ul_m or ol_m:
            tag = "ul" if ul_m else "ol"
            raw_item = ul_m.group(1) if ul_m else ol_m.group(1)
            while list_stack and list_stack[-1][1] > indent:
                closed_tag, _ = list_stack.pop()
                out.append(f"</{closed_tag}>")
            if list_stack and list_stack[-1][1] == indent and list_stack[-1][0] != tag:
                closed_tag, _ = list_stack.pop()
                out.append(f"</{closed_tag}>")
            if not list_stack or list_stack[-1][1] < indent:
                list_stack.append((tag, indent))
                out.append(f"<{tag}>")
            prefix = ""
            if ul_m:
                if re.match(r"^\[ \]\s+", raw_item):
                    raw_item = re.sub(r"^\[ \]\s+", "", raw_item)
                    prefix = "&#9744; "
                elif re.match(r"^\[x\]\s+", raw_item, flags=re.I):
                    raw_item = re.sub(r"^\[x\]\s+", "", raw_item, flags=re.I)
                    prefix = "&#9745; "
            out.append(f"<li>{prefix}{format_inline(raw_item)}</li>")
            i += 1
            continue

        # Paragraph (highlight Recommendation / Rekomendasi callouts)
        close_lists()
        para = [stripped]
        while (
            i + 1 < len(lines)
            and lines[i + 1].strip()
            and not re.match(r"^(#{1,4}\s|[-*]\s|\d+\.\s|>|```|---|\*\*\*|<svg|<!--)", lines[i + 1].strip())
            and "|" not in lines[i + 1]
        ):
            i += 1
            para.append(lines[i].strip())
        para_text = " ".join(para)
        if re.match(r"^\*\*(Recommendation|Rekomendasi)\*\*:", para_text):
            out.append(f'<div class="callout-rec">{format_inline(para_text)}</div>')
        else:
            out.append(f"<p>{format_inline(para_text)}</p>")
        i += 1

    close_lists()
    return "\n".join(out), toc, has_mermaid


def load_project_markdown(project_dir: Path, mode: str) -> str:
    parts = []
    for fname in SECTION_MODES[mode]:
        p = project_dir / fname
        if p.exists():
            parts.append(p.read_text(encoding="utf-8").strip())
    if mode in ("prd", "technical", "full"):
        sub_prds = project_dir / "prds"
        if sub_prds.is_dir():
            for prd_doc in sorted(sub_prds.glob("*.md")):
                parts.append(prd_doc.read_text(encoding="utf-8").strip())
        decisions_dir = project_dir / "decisions"
        if decisions_dir.is_dir():
            for adr in sorted(decisions_dir.glob("ADR-*.md")):
                parts.append(adr.read_text(encoding="utf-8").strip())
    if not parts:
        raise FileNotFoundError(f"No PRD/PRP markdown files found in {project_dir}")
    return "\n\n<!-- pagebreak -->\n\n".join(parts)


def build_toc_html(toc: list[tuple[int, str, str]], lang: str = "id") -> str:
    if not toc:
        return ""
    items = []
    for level, title, sec_id in toc:
        cls = ' class="toc-h2"' if level == 2 else ""
        items.append(f'<li{cls}><a href="#{sec_id}">{html.escape(title)}</a></li>')
    toc_heading = "Table of Contents (Click to Navigate)" if lang == "en" else "Daftar Isi (Klik untuk Navigasi)"
    return (
        '<nav id="toc-top" class="toc-box">'
        f'<p class="toc-title">{toc_heading}</p>'
        f'<ul class="toc-list">{"".join(items)}</ul>'
        "</nav>"
    )


def build_mermaid_script(mermaid_js: str | None) -> str:
    src = Path(mermaid_js).resolve().as_uri() if mermaid_js else "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"
    return f"""
<script>
(function() {{
  function fallbackAll() {{
    document.querySelectorAll('.mermaid').forEach(function(el) {{
      if (!el.querySelector('svg')) {{
        el.className = 'mermaid-fallback';
      }}
    }});
  }}
  var s = document.createElement('script');
  s.src = {src!r};
  s.onload = function() {{
    if (window.mermaid) {{
      window.mermaid.initialize({{ startOnLoad: true, theme: 'neutral', securityLevel: 'loose' }});
    }} else {{
      fallbackAll();
    }}
  }};
  s.onerror = fallbackAll;
  document.head.appendChild(s);
  setTimeout(fallbackAll, 6000);
}})();
</script>
"""


def build_html(
    body_html: str,
    title: str,
    kicker: str,
    meta: str,
    toc: list[tuple[int, str, str]],
    include_cover: bool,
    include_toc: bool,
    has_mermaid: bool,
    mermaid_js: str | None,
    lang: str = "id",
) -> str:
    safe_footer = title.replace("\\", "\\\\").replace('"', '\\"')
    page_lbl = '"Page " counter(page) " of " counter(pages)' if lang == "en" else '"Halaman " counter(page) " dari " counter(pages)'
    css = BASE_CSS.replace("__FOOTER_TITLE__", safe_footer).replace('"__PAGE_LABEL__"', page_lbl)
    toc_html = build_toc_html(toc, lang=lang) if include_toc else ""
    header_cls = "cover-page doc-header" if include_cover else "doc-header"
    page_break_after_cover = '<div class="page-break"></div>' if (include_cover and include_toc and toc_html) else ""
    mermaid_script = build_mermaid_script(mermaid_js) if has_mermaid else ""

    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{css}</style>
</head>
<body>
<header class="{header_cls}">
  <p class="doc-kicker">{html.escape(kicker)}</p>
  <h1 class="doc-title" style="border:none;margin:0 0 6px 0;padding:0;display:block;">{html.escape(title)}</h1>
  <p class="doc-meta">{html.escape(meta)}</p>
</header>
{toc_html}
{page_break_after_cover}
{body_html}
{mermaid_script}
</body>
</html>
"""


def count_pdf_pages(pdf_path: Path) -> int:
    data = pdf_path.read_bytes()
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", data))


def main():
    ap = argparse.ArgumentParser(description="Export Markdown or PRP folder to PDF.")
    ap.add_argument("--input", help="Path to a Markdown file")
    ap.add_argument("--project", help="Path to a prps/<project> or prds/<project> folder")
    ap.add_argument("--output", required=True, help="Output PDF path")
    ap.add_argument("--title", help="Document title")
    ap.add_argument("--kicker", default=None, help="Top label above title")
    ap.add_argument("--meta", default=f"Tanggal: {date.today().isoformat()}", help="Subtitle metadata")
    ap.add_argument("--mode", choices=["executive", "technical", "full", "prd"], default="executive", help="Section profile for --project")
    ap.add_argument("--cover", dest="cover", action="store_true", default=None, help="Include cover header styling")
    ap.add_argument("--no-cover", dest="cover", action="store_false", help="Disable cover header styling")
    ap.add_argument("--toc", dest="toc", action="store_true", default=None, help="Include automatic Table of Contents")
    ap.add_argument("--no-toc", dest="toc", action="store_false", help="Disable Table of Contents")
    ap.add_argument("--mermaid-js", default=os.environ.get("MERMAID_JS"), help="Optional local path to mermaid.min.js")
    ap.add_argument("--lang", choices=["id", "en"], default="id", help="UI label language for TOC and page footer")
    args = ap.parse_args()

    if not args.input and not args.project:
        ap.error("Provide either --input or --project.")

    is_project = bool(args.project)
    include_cover = args.cover if args.cover is not None else is_project
    include_toc = args.toc if args.toc is not None else is_project

    if args.input:
        in_path = Path(args.input).resolve()
        md_text = in_path.read_text(encoding="utf-8")
        base_dir = in_path.parent
        default_title = in_path.stem.replace("-", " ").title()
    else:
        proj_dir = Path(args.project).resolve()
        md_text = load_project_markdown(proj_dir, args.mode)
        base_dir = proj_dir
        default_title = proj_dir.name.replace("-", " ").title()

    title = args.title or default_title
    kicker = args.kicker if args.kicker is not None else ("Product Requirements Document (PRD)" if args.mode == "prd" else "Strategic Analysis Report")
    body_html, toc, has_mermaid = md_to_html(md_text, base_dir, add_back_to_toc=include_toc, lang=args.lang)
    full_html = build_html(
        body_html=body_html,
        title=title,
        kicker=kicker,
        meta=args.meta,
        toc=toc,
        include_cover=include_cover,
        include_toc=include_toc,
        has_mermaid=has_mermaid,
        mermaid_js=args.mermaid_js,
        lang=args.lang,
    )

    out_path = Path(args.output).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    browser = find_browser()
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(full_html)
        tmp_path = Path(tmp.name)

    try:
        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
        ]
        if has_mermaid:
            cmd.append("--virtual-time-budget=8000")
        cmd.extend([f"--print-to-pdf={out_path}", tmp_path.as_uri()])
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if res.returncode != 0 or not out_path.exists():
            print(res.stderr, file=sys.stderr)
            sys.exit(1)
        pages = count_pdf_pages(out_path)
        print(f"PDF generated: {out_path} ({out_path.stat().st_size:,} bytes, {pages} pages)")
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
