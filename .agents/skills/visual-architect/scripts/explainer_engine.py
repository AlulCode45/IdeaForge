"""One-Page Visual Explainer Engine (.explainer.md Markdown DSL & JSON fallback).

Supports:
- Conclusion-first lead with reasons list
- 4 editorial presets: institutional, briefing, technical, minimal
- Compact inline diagram directives (@architecture, @workflow, @sequence, @erd)
- Interactive @steps synced with diagram node highlighting
- @callout, @facts, @metric, @source citations, {good/caution/bad} table badges, interactive checklists
- Light/Dark toggle & Print-to-PDF support
"""

from __future__ import annotations

import html
import re
from typing import Any, Callable

from viewer_template import STUDIO_CSS

PRESET_VARS = {
    "institutional": "",
    "briefing": ":root{--bg:#FAF9F6;--primary:#1B365D;--accent:#0F766E;}",
    "technical": ":root{--bg:#F4F6F8;--primary:#0F172A;--accent:#2563EB;}",
    "minimal": ":root{--bg:#FFFFFF;--surface-2:#F7F7F7;--primary:#111111;--accent:#444444;}",
}


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _inline_md(text: str) -> str:
    out = _esc(text)
    out = re.sub(r"\{good:([^}]+)\}", r'<span class="exp-badge b-good">\1</span>', out)
    out = re.sub(r"\{caution:([^}]+)\}", r'<span class="exp-badge b-caution">\1</span>', out)
    out = re.sub(r"\{bad:([^}]+)\}", r'<span class="exp-badge b-bad">\1</span>', out)
    out = re.sub(r"`([^`]+)`", r"<code>\1</code>", out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    return out


def parse_explainer_markdown(md_text: str) -> dict[str, Any]:
    """Parse Archify-style .explainer.md compact directive document into structured panels."""
    lines = md_text.splitlines()
    title = "Visual Explainer"
    conclusion = ""
    reasons: list[str] = []
    sources: dict[str, dict[str, str]] = {}
    panels: list[dict[str, Any]] = []
    cur_panel: dict[str, Any] | None = None

    i = 0
    while i < len(lines):
        ln = lines[i].rstrip()
        s = ln.strip()
        if not s:
            i += 1
            continue
        if s.startswith("# ") and not cur_panel and title == "Visual Explainer":
            title = re.sub(r"\s*\{#[^}]+\}\s*$", "", s[2:]).strip()
            i += 1
            continue
        if s.startswith("@source "):
            m = re.match(r'^@source\s+(\S+)\s+title="([^"]+)"(?:\s+url=(\S+))?', s)
            if m:
                sources[m.group(1)] = {"id": m.group(1), "title": m.group(2), "url": m.group(3) or ""}
            i += 1
            continue
        if s.startswith("## "):
            cur_panel = {"title": re.sub(r"\s*\{#[^}]+\}\s*$", "", s[3:]).strip(), "blocks": []}
            panels.append(cur_panel)
            i += 1
            continue

        # Header intro before first ##
        if cur_panel is None:
            if s.startswith("- "):
                reasons.append(s[2:].strip())
            elif not s.startswith("@") and not conclusion:
                conclusion = s
            i += 1
            continue

        # Inside a panel: inline diagram directives
        m_dir = re.match(r'^@(architecture|workflow|sequence|erd)\s+id=(\S+)(?:\s+title="([^"]+)")?', s)
        if m_dir:
            dtype, did, dtitle = m_dir.group(1), m_dir.group(2), m_dir.group(3) or did
            rows: list[list[str]] = []
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                rows.append(cells)
                i += 1
            cur_panel["blocks"].append({"kind": "diagram", "spec": _rows_to_spec(dtype, dtitle, rows)})
            continue

        if s.startswith("@steps"):
            step_rows: list[dict[str, Any]] = []
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if len(cells) >= 3:
                    focus = [c.strip() for c in cells[4].split(",")] if len(cells) >= 5 and cells[4] else []
                    step_rows.append({"id": cells[0], "title": cells[1], "detail": cells[2], "focusNodes": focus})
                i += 1
            cur_panel["blocks"].append({"kind": "steps", "items": step_rows})
            continue

        if s.startswith("@callout"):
            body_lines: list[str] = []
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith(("@", "##")):
                body_lines.append(lines[i].strip())
                i += 1
            cur_panel["blocks"].append({"kind": "callout", "text": " ".join(body_lines)})
            continue

        if s.startswith("@facts") or s.startswith("@metric"):
            fact_rows: list[tuple[str, str]] = []
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if len(cells) >= 2:
                    fact_rows.append((cells[0], cells[1]))
                i += 1
            cur_panel["blocks"].append({"kind": "facts", "items": fact_rows})
            continue

        if s.startswith("|"):
            tbl_rows: list[list[str]] = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.match(r"^:?-+:?$", c) for c in cells):
                    tbl_rows.append(cells)
                i += 1
            cur_panel["blocks"].append({"kind": "table", "rows": tbl_rows})
            continue

        if s.startswith("- [ ] ") or s.startswith("- [x] "):
            checks: list[tuple[bool, str]] = []
            while i < len(lines) and re.match(r"^- \[[ xX]\] ", lines[i].strip()):
                st = lines[i].strip()
                checks.append((st[3].lower() == "x", st[6:].strip()))
                i += 1
            cur_panel["blocks"].append({"kind": "checklist", "items": checks})
            continue

        cur_panel["blocks"].append({"kind": "prose", "text": s})
        i += 1

    return {"title": title, "conclusion": conclusion, "reasons": reasons, "sources": sources, "panels": panels}


def _rows_to_spec(dtype: str, title: str, rows: list[list[str]]) -> dict[str, Any]:
    if dtype == "sequence":
        parts, msgs = [], []
        for r in rows:
            if r and r[0].startswith("actor "):
                parts.append({"id": r[0][6:].strip(), "label": r[1] if len(r) > 1 else r[0][6:], "role": r[2] if len(r) > 2 else ""})
            elif len(r) >= 3:
                msgs.append({"from": r[0], "to": r[1], "label": r[2], "kind": r[3] if len(r) > 3 else "sync"})
        return {"type": "sequence", "title": title, "participants": parts, "messages": msgs}
    if dtype == "erd":
        ents: dict[str, dict[str, Any]] = {}
        rels: list[dict[str, Any]] = []
        for r in rows:
            if len(r) >= 3 and ">" in r[0]:
                u, v = [x.strip() for x in r[0].split(">", 1)]
                rels.append({"from": u, "to": v, "cardinality": r[1], "label": r[2]})
            elif len(r) >= 2:
                eid = r[0]
                ents.setdefault(eid, {"id": eid, "label": eid, "attributes": []})
                ents[eid]["attributes"].append({"name": r[1], "type": r[2] if len(r) > 2 else "text", "key": r[3].split(",") if len(r) > 3 and r[3] else []})
        return {"type": "erd", "title": title, "entities": list(ents.values()), "relationships": rels}
    nodes, edges = [], []
    for r in rows:
        if r and ">" in r[0]:
            u, v = [x.strip() for x in r[0].split(">", 1)]
            edges.append({"from": u, "to": v, "label": r[1] if len(r) > 1 else "", "kind": r[2] if len(r) > 2 else "sync"})
        elif len(r) >= 2:
            nodes.append({"id": r[0], "label": r[1], "role": r[2] if len(r) > 2 else "", "group": r[3] if len(r) > 3 else ""})
    return {"type": dtype, "title": title, "nodes": nodes, "edges": edges}


def render_explainer_page(
    doc: dict[str, Any],
    render_svg_fn: Callable[[dict[str, Any]], tuple[str, int, int, dict[str, Any]]],
    atlas_svg: str = "",
    lang: str = "id",
    theme: str = "light",
    preset: str = "institutional",
) -> str:
    """Render either a parsed .explainer.md document OR a JSON diagram/diagnosis spec into HTML."""
    kicker = "Ringkasan & Kesimpulan Utama" if lang == "id" else "Key Conclusion"
    panels_html_parts: list[str] = []

    if "panels" in doc and doc["panels"] and isinstance(doc["panels"][0], dict) and "blocks" in doc["panels"][0]:
        # Rich Markdown DSL mode
        for p in doc["panels"]:
            b_parts: list[str] = []
            for b in p["blocks"]:
                bk = b["kind"]
                if bk == "diagram":
                    svg_s, _, _, _ = render_svg_fn(b["spec"])
                    b_parts.append(f'<div class="exp-stage">{svg_s}</div>')
                elif bk == "steps":
                    s_cards = "".join(
                        f'<div class="exp-step" data-focus="{_esc(",".join(it.get("focusNodes", [])))}">'
                        f'<strong>{_esc(it["title"])}</strong><div>{_inline_md(it["detail"])}</div></div>'
                        for it in b["items"]
                    )
                    b_parts.append(f'<div class="exp-steps">{s_cards}</div>')
                elif bk == "callout":
                    b_parts.append(f'<div class="exp-callout">{_inline_md(b["text"])}</div>')
                elif bk == "facts":
                    f_items = "".join(f'<div class="fact-item"><span>{_esc(k)}</span><strong>{_inline_md(v)}</strong></div>' for k, v in b["items"])
                    b_parts.append(f'<div class="facts-grid">{f_items}</div>')
                elif bk == "table" and b["rows"]:
                    hdr = "".join(f"<th>{_inline_md(c)}</th>" for c in b["rows"][0])
                    body = "".join("<tr>" + "".join(f"<td>{_inline_md(c)}</td>" for c in r) + "</tr>" for r in b["rows"][1:])
                    b_parts.append(f'<div class="tbl-wrap"><table class="exp-tbl"><thead><tr>{hdr}</tr></thead><tbody>{body}</tbody></table></div>')
                elif bk == "checklist":
                    cks = "".join(
                        f'<label class="ck-row"><input type="checkbox"{" checked" if done else ""}><span>{_inline_md(txt)}</span></label>'
                        for done, txt in b["items"]
                    )
                    b_parts.append(f'<div class="ck-list">{cks}</div>')
                else:
                    b_parts.append(f'<p>{_inline_md(b["text"])}</p>')
            panels_html_parts.append(f'<section class="exp-panel"><h2>{_esc(p["title"])}</h2>{"".join(b_parts)}</section>')
    else:
        # JSON spec (diagram or repo diagnosis) mode
        svg_str, _, _, _ = render_svg_fn(doc)
        items = doc.get("findings") or [
            {"title": s.get("title", ""), "detail": s.get("caption", ""), "focusNodes": s.get("focusNodes", [])}
            for s in doc.get("steps", [])
        ]
        cards_html = ""
        for idx, it in enumerate(items):
            fix = it.get("fix_task", "")
            fix_btn = (
                f'<button type="button" class="btn copy-fix" data-fix="{_esc(fix)}" style="margin-top:8px;height:24px;font-size:11px">'
                f'{"Salin Tugas Perbaikan" if lang == "id" else "Copy Fix Task"}</button>'
                if fix else ""
            )
            cards_html += (
                f'<article class="exp-card" data-focus="{_esc(",".join(it.get("focusNodes", [])))}">'
                f'<h3>{_esc(it.get("title", f"Item {idx+1}"))}</h3>'
                f'<p>{_esc(it.get("detail", it.get("body", "")))}</p>{fix_btn}</article>'
            )
        atlas_tab = f'<div class="exp-stage" style="margin-top:16px"><div class="ins-kicker">Atlas Dependency Star Map</div>{atlas_svg}</div>' if atlas_svg else ""
        panels_html_parts.append(
            f'<div class="exp-grid"><div>{cards_html}</div><div><div class="exp-stage">{svg_str}</div>{atlas_tab}</div></div>'
        )

    reasons_html = ""
    if doc.get("reasons"):
        reasons_html = '<ul class="exp-reasons">' + "".join(f"<li>{_inline_md(r)}</li>" for r in doc["reasons"]) + "</ul>"

    sources_html = ""
    if doc.get("sources"):
        s_li = "".join(
            f'<li><code>[{_esc(sid)}]</code> '
            + (f'<a href="{_esc(s["url"])}" target="_blank" rel="noopener">{_esc(s["title"])}</a>' if s.get("url") else _esc(s["title"]))
            + "</li>"
            for sid, s in doc["sources"].items()
        )
        sources_html = f'<footer class="exp-sources"><div class="ins-kicker">Sources</div><ul>{s_li}</ul></footer>'

    return (
        f'<!DOCTYPE html>\n<html lang="{_esc(lang)}" data-theme="{_esc(theme)}">\n<head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{_esc(doc.get("title", "Visual Explainer"))}</title>\n'
        f'<style>{STUDIO_CSS}\n{PRESET_VARS.get(preset, "")}\n'
        '.exp-page{max-width:1240px;margin:0 auto;padding:28px 24px 64px;}\n'
        '.exp-top{display:flex;justify-content:flex-end;gap:8px;margin-bottom:14px;}\n'
        '.exp-lead{padding:22px 26px;background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;margin-bottom:24px;}\n'
        '.exp-lead h1{font-family:var(--font-serif);font-size:28px;margin:4px 0 10px;color:var(--primary);}\n'
        '.exp-reasons{margin:10px 0 0;padding-left:20px;color:var(--text-muted);}\n'
        '.exp-panel{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:20px 24px;margin-bottom:20px;}\n'
        '.exp-panel h2{font-family:var(--font-serif);font-size:20px;margin:0 0 14px;color:var(--primary);}\n'
        '.exp-grid{display:grid;grid-template-columns:380px minmax(0,1fr);gap:24px;align-items:start;}\n'
        '.exp-card,.exp-step{padding:13px 15px;background:var(--surface);border:1px solid var(--line);border-radius:8px;margin-bottom:10px;cursor:pointer;}\n'
        '.exp-card:hover,.exp-card.active,.exp-step:hover,.exp-step.active{border-color:var(--accent);}\n'
        '.exp-card h3{margin:0 0 6px;font-size:15px;color:var(--primary);}\n'
        '.exp-card p{margin:0;color:var(--text-muted);font-size:13px;}\n'
        '.exp-stage{background:var(--surface);border:1px solid var(--line);border-radius:8px;padding:14px;overflow:auto;}\n'
        '.exp-callout{padding:12px 14px;border-left:3px solid var(--accent);background:var(--surface-2);border-radius:4px;margin:12px 0;}\n'
        '.facts-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin:12px 0;}\n'
        '.fact-item{padding:10px 12px;border:1px solid var(--line);border-radius:6px;background:var(--bg);display:flex;flex-direction:column;gap:4px;}\n'
        '.fact-item span{font-size:11px;color:var(--text-muted);text-transform:uppercase;}\n'
        '.exp-tbl{width:100%;border-collapse:collapse;font-size:13px;margin:10px 0;}\n'
        '.exp-tbl th,.exp-tbl td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;}\n'
        '.exp-tbl th{font-weight:600;color:var(--primary);background:var(--surface-2);}\n'
        '.exp-badge{display:inline-block;padding:1px 7px;border-radius:4px;font-size:11px;font-weight:600;}\n'
        '.b-good{background:var(--go-bg);color:var(--go);}\n'
        '.b-caution{background:var(--conditional-bg);color:var(--conditional);}\n'
        '.b-bad{background:var(--nogo-bg);color:var(--nogo);}\n'
        '.ck-row{display:flex;gap:8px;align-items:center;padding:5px 0;cursor:pointer;}\n'
        '.exp-sources{margin-top:24px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;color:var(--text-muted);}\n'
        '@media(max-width:960px){.exp-grid{grid-template-columns:1fr;}}\n'
        '@media print{.exp-top{display:none!important;}}\n'
        '</style>\n</head>\n<body>\n'
        '<main class="exp-page">\n'
        '  <div class="exp-top">'
        '    <button type="button" class="btn" onclick="window.print()">PDF / Print</button>'
        '    <button type="button" class="btn" onclick="document.documentElement.setAttribute(\'data-theme\',document.documentElement.getAttribute(\'data-theme\')===\'dark\'?\'light\':\'dark\')">Tema</button>'
        '  </div>\n'
        '  <section class="exp-lead">\n'
        f'    <div class="ins-kicker">{_esc(kicker)}</div>\n'
        f'    <h1>{_esc(doc.get("title", "Explainer"))}</h1>\n'
        f'    <p style="margin:0">{_inline_md(doc.get("conclusion") or doc.get("subtitle") or "")}</p>\n'
        f'    {reasons_html}\n'
        '  </section>\n'
        f'  {"".join(panels_html_parts)}\n'
        f'  {sources_html}\n'
        '</main>\n'
        '<script>\n'
        'document.querySelectorAll(".exp-card,.exp-step").forEach(c=>c.addEventListener("click",()=>{\n'
        '  document.querySelectorAll(".exp-card,.exp-step").forEach(x=>x.classList.remove("active"));\n'
        '  c.classList.add("active");\n'
        '  const f=new Set((c.dataset.focus||"").split(",").filter(Boolean));\n'
        '  document.querySelectorAll(".dg-node").forEach(n=>n.classList.toggle("is-dimmed",f.size&&!f.has(n.dataset.nodeId)));\n'
        '}));\n'
        'document.querySelectorAll(".copy-fix").forEach(b=>b.addEventListener("click",e=>{\n'
        '  e.stopPropagation(); if(navigator.clipboard) navigator.clipboard.writeText(b.dataset.fix||"");\n'
        '  const o=b.textContent; b.textContent="Copied"; setTimeout(()=>b.textContent=o,1400);\n'
        '}));\n'
        '</script>\n</body>\n</html>\n'
    )
