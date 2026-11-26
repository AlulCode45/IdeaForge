#!/usr/bin/env python3
"""IdeaForge Visual Architect Studio (Pure Python 3 stdlib).

Feature-complete visual architecture studio matching and extending Archify:
- 10 interactive diagram types with change-marking (added/modified/removed) & emphasis
- Institutional Editorial Light/Dark Viewer: Pan/Zoom, Search, Live/Still Comet Flow,
  Semantic Radar minimap, Semantic Passport (nodes + edges + payload diffs),
  Upstream/Downstream Reach, BFS Route Tracer, URL Hash Deep-Links, Presentation Mode,
  Story Walkthrough + WebM Video Recording, Dual-Theme SVG, 2x PNG, 1200x630 Share Cards
- Strict Quality Gates (validate)
- Mermaid Transpiler (from-mermaid)
- Snapshot Comparison (compare: Before | Delta | After) & Git PR Visual Diff (pr-diff)
- Multi-Language Repository Architecture Diagnosis + Atlas Star Map + AI Fix Prompts (analyze-repo)
- One-Page Visual Explainer supporting both .explainer.md DSL & JSON with 4 presets (explainer)
"""

from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from code_analyzer import (
    analyze_repository,
    build_pr_diff_pack,
    compare_diagrams,
    detect_cycles,
    render_atlas_star_svg,
)
from explainer_engine import parse_explainer_markdown, render_explainer_page
from viewer_template import DUAL_THEME_SVG_CSS, build_viewer_html

DIAGRAM_TYPES = (
    "architecture",
    "workflow",
    "sequence",
    "dataflow",
    "lifecycle",
    "erd",
    "tree",
    "class",
    "timeline",
    "waterfall",
)

I18N = {
    "id": {
        "search_placeholder": "Cari node, grup, ID (/)...",
        "theme_light": "Terang",
        "theme_dark": "Gelap",
        "fit": "Pas Layar",
        "reset": "Reset",
        "present": "Presentasi",
        "exit_present": "Keluar Presentasi (P)",
        "motion_live": "Live",
        "motion_still": "Still",
        "trace_route": "Lacak Rute",
        "trace_pick_src": "Pilih asal...",
        "trace_pick_dst": "Pilih tujuan...",
        "story_play": "Putar Cerita",
        "story_pause": "Jeda",
        "story_prev": "Sebelumnya",
        "story_next": "Berikutnya",
        "export_menu": "Ekspor ▾",
        "export_svg": "Unduh SVG",
        "export_png": "Unduh PNG",
        "share_card": "Share Card (1200×630)",
        "export_video": "Rekam Story (WebM)",
        "copy_link": "Salin Tautan",
        "copied": "Tersalin",
        "all_groups": "Semua",
        "inspector_title": "Paspor Semantik",
        "group": "Grup / Zona",
        "tech": "Teknologi",
        "evidence": "Bukti",
        "source": "Sumber Kode",
        "upstream": "Hulu (Upstream)",
        "downstream": "Hilir (Downstream)",
        "drilldown": "Buka Detail",
        "no_selection": "Klik node atau relasi mana saja untuk melihat detail, dependensi hulu/hilir, diff payload, dan sumber kode.",
        "nodes_lbl": "node",
        "edges_lbl": "relasi",
    },
    "en": {
        "search_placeholder": "Search nodes, groups, ID (/)...",
        "theme_light": "Light",
        "theme_dark": "Dark",
        "fit": "Fit",
        "reset": "Reset",
        "present": "Present",
        "exit_present": "Exit Present (P)",
        "motion_live": "Live",
        "motion_still": "Still",
        "trace_route": "Trace Route",
        "trace_pick_src": "Pick source...",
        "trace_pick_dst": "Pick target...",
        "story_play": "Play Story",
        "story_pause": "Pause",
        "story_prev": "Prev",
        "story_next": "Next",
        "export_menu": "Export ▾",
        "export_svg": "Download SVG",
        "export_png": "Download PNG",
        "share_card": "Share Card (1200×630)",
        "export_video": "Record Story (WebM)",
        "copy_link": "Copy Link",
        "copied": "Copied",
        "all_groups": "All",
        "inspector_title": "Semantic Passport",
        "group": "Group / Zone",
        "tech": "Stack",
        "evidence": "Evidence",
        "source": "Source",
        "upstream": "Upstream",
        "downstream": "Downstream",
        "drilldown": "Open Detail",
        "no_selection": "Click any node or edge to inspect details, upstream/downstream reach, payload diff, and source links.",
        "nodes_lbl": "nodes",
        "edges_lbl": "edges",
    },
}


# ---------------------------------------------------------------------------
# Validation & Quality Gates
# ---------------------------------------------------------------------------

def validate_diagram(spec: dict[str, Any], strict: bool = False) -> dict[str, Any]:
    """Validate diagram IR against schema, referential integrity, and structural gates."""
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    if not isinstance(spec, dict):
        return {"ok": False, "errors": [{"code": "schema/root", "message": "Root JSON must be an object."}], "warnings": []}

    dtype = str(spec.get("type", "architecture")).lower()
    if dtype not in DIAGRAM_TYPES:
        errors.append({"code": "schema/type", "message": f"Unsupported diagram type '{dtype}'. Expected one of {DIAGRAM_TYPES}."})

    if not str(spec.get("title", "")).strip():
        warnings.append({"code": "meta/title", "message": "Missing diagram 'title'."})

    node_ids: list[str] = []
    seen_ids: set[str] = set()

    def reg_id(raw_id: Any, ctx: str) -> str | None:
        if not raw_id or not isinstance(raw_id, str):
            errors.append({"code": "schema/id", "message": f"Missing string 'id' in {ctx}."})
            return None
        if raw_id in seen_ids:
            errors.append({"code": "schema/dup-id", "message": f"Duplicate id '{raw_id}' in {ctx}."})
            return None
        seen_ids.add(raw_id)
        node_ids.append(raw_id)
        return raw_id

    if dtype == "sequence":
        for idx, p in enumerate(spec.get("participants", spec.get("nodes", []))):
            reg_id(p.get("id"), f"participants[{idx}]")
        for idx, m in enumerate(spec.get("messages", spec.get("edges", []))):
            if m.get("from") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"messages[{idx}].from '{m.get('from')}' not found."})
            if m.get("to") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"messages[{idx}].to '{m.get('to')}' not found."})
    elif dtype == "erd":
        for idx, ent in enumerate(spec.get("entities", spec.get("nodes", []))):
            eid = reg_id(ent.get("id"), f"entities[{idx}]")
            if eid and not ent.get("attributes"):
                warnings.append({"code": "erd/empty-entity", "message": f"Entity '{eid}' has no attributes."})
        for idx, rel in enumerate(spec.get("relationships", spec.get("edges", []))):
            if rel.get("from") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"relationships[{idx}].from '{rel.get('from')}' not found."})
            if rel.get("to") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"relationships[{idx}].to '{rel.get('to')}' not found."})
    elif dtype == "class":
        for idx, cls in enumerate(spec.get("classes", spec.get("nodes", []))):
            reg_id(cls.get("id"), f"classes[{idx}]")
        for idx, rel in enumerate(spec.get("relationships", spec.get("edges", []))):
            if rel.get("from") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"relationships[{idx}].from '{rel.get('from')}' not found."})
            if rel.get("to") not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"relationships[{idx}].to '{rel.get('to')}' not found."})
    elif dtype in ("timeline", "waterfall"):
        items = spec.get("events" if dtype == "timeline" else "spans", spec.get("nodes", []))
        if not items:
            errors.append({"code": f"schema/{dtype}-empty", "message": f"'{dtype}' requires at least one item."})
        for idx, it in enumerate(items):
            reg_id(it.get("id") or f"item-{idx}", f"items[{idx}]")
            if dtype == "waterfall":
                dur = it.get("duration", 0)
                if not isinstance(dur, (int, float)) or dur < 0:
                    errors.append({"code": "waterfall/duration", "message": f"spans[{idx}] duration must be >= 0."})
    else:
        nodes = spec.get("nodes", [])
        edges = spec.get("edges", spec.get("relationships", []))
        if not nodes:
            errors.append({"code": "schema/nodes-empty", "message": f"'{dtype}' requires a non-empty 'nodes' list."})
        for idx, n in enumerate(nodes):
            nid = reg_id(n.get("id"), f"nodes[{idx}]")
            if len(str(n.get("label", ""))) > 48:
                warnings.append({"code": "layout/long-label", "message": f"Node '{nid}' label exceeds 48 chars."})
        edge_pairs: list[tuple[str, str]] = []
        for idx, e in enumerate(edges):
            src, dst = e.get("from"), e.get("to")
            if src not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"edges[{idx}].from '{src}' not found."})
            if dst not in seen_ids:
                errors.append({"code": "ref/dangling", "message": f"edges[{idx}].to '{dst}' not found."})
            if src in seen_ids and dst in seen_ids:
                edge_pairs.append((src, dst))
        if dtype in ("dataflow", "tree"):
            cycles = detect_cycles(node_ids, edge_pairs)
            if cycles:
                (errors if dtype == "tree" else warnings).append({"code": "graph/cycle", "message": f"Cycle detected in {dtype}: {cycles[0]}"})
        if len(nodes) > 1 and edges:
            connected = {u for u, _ in edge_pairs} | {v for _, v in edge_pairs}
            orphans = [nid for nid in node_ids if nid not in connected]
            if orphans:
                warnings.append({"code": "graph/orphans", "message": f"Disconnected nodes: {', '.join(orphans[:5])}"})

    for idx, st in enumerate(spec.get("steps", [])):
        for fn in st.get("focusNodes", []):
            if fn not in seen_ids:
                warnings.append({"code": "story/ref", "message": f"steps[{idx}].focusNodes '{fn}' not found."})

    ok = len(errors) == 0 and (not strict or len(warnings) == 0)
    return {"ok": ok, "type": dtype, "node_count": len(node_ids), "errors": errors, "warnings": warnings}


# ---------------------------------------------------------------------------
# Mermaid -> Diagram IR Transpiler
# ---------------------------------------------------------------------------

def _clean_mmd_label(raw: str) -> str:
    raw = raw.strip()
    for lq, rq in (('["', '"]'), ('[', ']'), ('("', '")'), ('(', ')'), ('{"', '"}'), ('{', '}'), ('((', '))')):
        if raw.startswith(lq) and raw.endswith(rq) and len(raw) > len(lq) + len(rq):
            return raw[len(lq):-len(rq)].strip().strip('"')
    return raw.strip('"')


def parse_mermaid(text: str, force_type: str = "auto", title: str = "Diagram") -> dict[str, Any]:
    """Transpile Mermaid (flowchart/graph, sequence, state, er, class) into Diagram IR."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.strip().startswith("%%")]
    header = lines[0].lower() if lines else ""

    if force_type != "auto":
        dtype = force_type
    elif header.startswith("sequencediagram"):
        dtype = "sequence"
    elif header.startswith("erdiagram"):
        dtype = "erd"
    elif header.startswith("statediagram"):
        dtype = "lifecycle"
    elif header.startswith("classdiagram"):
        dtype = "class"
    else:
        dtype = "workflow"

    if dtype == "sequence":
        participants: dict[str, dict[str, Any]] = {}
        messages: list[dict[str, Any]] = []
        for ln in lines[1:]:
            m_part = re.match(r"^(?:participant|actor)\s+([A-Za-z0-9_.]+)(?:\s+as\s+(.+))?$", ln, re.I)
            if m_part:
                pid = m_part.group(1)
                participants[pid] = {"id": pid, "label": (m_part.group(2) or pid).strip(), "role": "Actor" if ln.lower().startswith("actor") else "Service"}
                continue
            m_msg = re.match(r"^([A-Za-z0-9_.]+)\s*(-->>|->>|-->|->|--\)|-\))\s*([A-Za-z0-9_.]+)\s*:\s*(.+)$", ln)
            if m_msg:
                src, arrow, dst, lbl = m_msg.groups()
                for p in (src, dst):
                    participants.setdefault(p, {"id": p, "label": p, "role": "Participant"})
                messages.append({
                    "from": src, "to": dst, "label": lbl.strip(),
                    "kind": "return" if arrow.startswith("--") else ("async" if ")" in arrow else "sync"),
                })
        return {"type": "sequence", "title": title, "participants": list(participants.values()), "messages": messages}

    if dtype == "erd":
        entities: dict[str, dict[str, Any]] = {}
        rels: list[dict[str, Any]] = []
        cur_ent: str | None = None
        for ln in lines[1:]:
            if ln == "}":
                cur_ent = None
                continue
            m_ent = re.match(r"^([A-Za-z0-9_.]+)\s*\{$", ln)
            if m_ent:
                cur_ent = m_ent.group(1)
                entities.setdefault(cur_ent, {"id": cur_ent, "label": cur_ent, "attributes": []})
                continue
            if cur_ent:
                parts = ln.split()
                if len(parts) >= 2:
                    key = [k.lower() for k in parts[2:] if k.upper() in ("PK", "FK", "UK")]
                    entities[cur_ent]["attributes"].append({"name": parts[1], "type": parts[0], "key": key})
                continue
            m_rel = re.match(r"^([A-Za-z0-9_.]+)\s+([|o}{]+--[|o}{]+)\s+([A-Za-z0-9_.]+)\s*:\s*(.+)$", ln)
            if m_rel:
                src, card, dst, lbl = m_rel.groups()
                for e in (src, dst):
                    entities.setdefault(e, {"id": e, "label": e, "attributes": []})
                rels.append({"from": src, "to": dst, "label": lbl.strip().strip('"'), "cardinality": card})
        return {"type": "erd", "title": title, "entities": list(entities.values()), "relationships": rels}

    nodes: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    cur_group: str | None = None

    def ensure_node(token: str) -> str:
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*(\[.*\]|\(.*\)|\{.*\})$", token.strip())
        if m:
            nid, shape = m.group(1), m.group(2)
            kind = "decision" if shape.startswith("{") else "process"
            lbl = _clean_mmd_label(shape)
        else:
            nid = re.sub(r"[^A-Za-z0-9_.-]", "_", token.strip()) or "node"
            kind, lbl = "process", token.strip()
        if nid not in nodes:
            nodes[nid] = {"id": nid, "label": lbl, "kind": kind}
            if cur_group:
                nodes[nid]["group"] = cur_group
        elif lbl != nid and nodes[nid]["label"] == nid:
            nodes[nid]["label"] = lbl
            nodes[nid]["kind"] = kind
        return nid

    for ln in lines[1:]:
        if ln.lower().startswith("subgraph "):
            cur_group = ln[9:].strip().strip('"')
            continue
        if ln.lower() == "end":
            cur_group = None
            continue
        m_edge = re.match(r"^(.+?)\s*(?:-->|-.->|==>)\s*(?:\|([^|]+)\|)?\s*(.+)$", ln)
        if m_edge:
            lhs, elbl, rhs = m_edge.groups()
            edges.append({"from": ensure_node(lhs), "to": ensure_node(rhs), "label": (elbl or "").strip()})
            continue
        m_lbl_edge = re.match(r"^(.+?)\s+--\s+(.+?)\s+-->\s+(.+)$", ln)
        if m_lbl_edge:
            lhs, elbl, rhs = m_lbl_edge.groups()
            edges.append({"from": ensure_node(lhs), "to": ensure_node(rhs), "label": elbl.strip()})
            continue
        m_state = re.match(r"^([A-Za-z0-9_.*\[\]-]+)\s*-->\s*([A-Za-z0-9_.*\[\]-]+)(?:\s*:\s*(.+))?$", ln)
        if m_state:
            s_raw, d_raw, slbl = m_state.groups()
            s_id = "start" if s_raw == "[*]" else s_raw
            d_id = "end" if d_raw == "[*]" else d_raw
            nodes.setdefault(s_id, {"id": s_id, "label": "Start" if s_id == "start" else s_id, "kind": "start" if s_id == "start" else "state"})
            nodes.setdefault(d_id, {"id": d_id, "label": "End" if d_id == "end" else d_id, "kind": "terminal" if d_id == "end" else "state"})
            edges.append({"from": s_id, "to": d_id, "label": (slbl or "").strip()})

    return {"type": dtype, "title": title, "nodes": list(nodes.values()), "edges": edges}


# ---------------------------------------------------------------------------
# Deterministic Layout & SVG Renderers (All 10 Types + Change Marks)
# ---------------------------------------------------------------------------

def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def _wrap_text(text: str, max_chars: int = 24) -> list[str]:
    words = str(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        if len(cur) + 1 + len(w) <= max_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines[:3]


def _chg_classes(item: dict[str, Any]) -> str:
    cls = []
    chg = str(item.get("change", "")).lower()
    if chg in ("added", "modified", "removed"):
        cls.append(f"chg-{chg}")
    if item.get("emphasis"):
        cls.append("is-emphasis")
    return (" " + " ".join(cls)) if cls else ""


def _chg_badge_svg(item: dict[str, Any], rx: float, ry: float) -> str:
    chg = str(item.get("change", "")).lower()
    sym = {"added": "+", "modified": "~", "removed": "−"}.get(chg)
    if not sym:
        return ""
    col = {"added": "var(--go)", "modified": "var(--conditional)", "removed": "var(--nogo)"}[chg]
    return f'<text x="{rx:.1f}" y="{ry:.1f}" text-anchor="end" class="chg-badge" fill="{col}">{sym}</text>'


def _render_layered_graph_svg(spec: dict[str, Any]) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    dtype = spec.get("type", "architecture")
    raw_nodes = spec.get("classes" if dtype == "class" else "nodes", [])
    raw_edges = spec.get("relationships" if dtype == "class" else "edges", spec.get("relationships", []))

    nodes_map = {n["id"]: dict(n) for n in raw_nodes}
    adj: dict[str, list[str]] = defaultdict(list)
    indeg: dict[str, int] = {n["id"]: 0 for n in raw_nodes}
    for e in raw_edges:
        u, v = e.get("from"), e.get("to")
        if u in nodes_map and v in nodes_map and u != v:
            adj[u].append(v)
            indeg[v] += 1

    rank: dict[str, int] = {nid: 0 for nid in nodes_map}
    q = deque([nid for nid, d in indeg.items() if d == 0])
    visited: set[str] = set()
    while q:
        u = q.popleft()
        visited.add(u)
        for v in adj[u]:
            rank[v] = max(rank[v], rank[u] + 1)
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    for nid in nodes_map:
        if nid not in visited:
            for v in adj[nid]:
                if rank[v] <= rank[nid]:
                    rank[v] = rank[nid] + 1

    layers: dict[int, list[str]] = defaultdict(list)
    for n in raw_nodes:
        layers[rank[n["id"]]].append(n["id"])
    for r in layers:
        layers[r].sort(key=lambda nid: (str(nodes_map[nid].get("group", "")), nid))

    card_w = 216 if dtype == "class" else 200
    gap_x, gap_y, pad_x, pad_y = 124, 52, 56, 56

    def node_height(n: dict[str, Any]) -> int:
        if dtype == "class":
            return 44 + max(1, len(n.get("attributes", []))) * 18 + max(1, len(n.get("methods", []))) * 18 + 14
        sub = 16 if n.get("sublabel") or n.get("role") else 0
        return max(64, 34 + len(_wrap_text(n.get("label", n["id"]), 22)) * 18 + sub)

    max_layer_h = 0
    layer_x: dict[int, int] = {}
    sorted_ranks = sorted(layers.keys())
    for idx, r in enumerate(sorted_ranks):
        layer_x[r] = pad_x + idx * (card_w + gap_x)
        h_sum = sum(node_height(nodes_map[nid]) for nid in layers[r]) + max(0, len(layers[r]) - 1) * gap_y
        max_layer_h = max(max_layer_h, h_sum)

    pos: dict[str, tuple[int, int, int, int]] = {}
    for r in sorted_ranks:
        nids = layers[r]
        h_sum = sum(node_height(nodes_map[nid]) for nid in nids) + max(0, len(nids) - 1) * gap_y
        y = pad_y + max(0, (max_layer_h - h_sum) // 2)
        for nid in nids:
            nh = node_height(nodes_map[nid])
            pos[nid] = (layer_x[r], y, card_w, nh)
            y += nh + gap_y

    total_w = max(720, pad_x * 2 + max(1, len(sorted_ranks)) * card_w + max(0, len(sorted_ranks) - 1) * gap_x)
    total_h = max(420, pad_y * 2 + max_layer_h)
    svg_parts: list[str] = []

    groups: dict[str, list[tuple[int, int, int, int]]] = defaultdict(list)
    for nid, rect in pos.items():
        if nodes_map[nid].get("group"):
            groups[str(nodes_map[nid]["group"])].append(rect)
    for gname, rects in groups.items():
        gx0, gy0 = min(r[0] for r in rects) - 18, min(r[1] for r in rects) - 30
        gx1, gy1 = max(r[0] + r[2] for r in rects) + 18, max(r[1] + r[3] for r in rects) + 18
        svg_parts.append(
            f'<g class="dg-zone" data-group="{_esc(gname)}">'
            f'<rect x="{gx0}" y="{gy0}" width="{gx1-gx0}" height="{gy1-gy0}" rx="8" class="zone-box"/>'
            f'<text x="{gx0+12}" y="{gy0+19}" class="zone-title">{_esc(gname.upper())}</text></g>'
        )

    edge_meta: dict[str, Any] = {}
    for idx, e in enumerate(raw_edges):
        u, v = e.get("from"), e.get("to")
        if u not in pos or v not in pos:
            continue
        eid = f"e-{idx}"
        edge_meta[eid] = dict(e)
        ux, uy, uw, uh = pos[u]
        vx, vy, vw, vh = pos[v]
        if ux < vx:
            x1, y1, x2, y2 = ux + uw, uy + uh // 2, vx, vy + vh // 2
            dx = max(40, (x2 - x1) * 0.5)
            path = f"M {x1} {y1} C {x1+dx:.1f} {y1}, {x2-dx:.1f} {y2}, {x2} {y2}"
        elif ux > vx:
            x1, y1, x2, y2 = ux, uy + uh // 2, vx + vw, vy + vh // 2
            dx = max(40, (x1 - x2) * 0.5)
            path = f"M {x1} {y1} C {x1-dx:.1f} {y1}, {x2+dx:.1f} {y2}, {x2} {y2}"
        else:
            x1, y1, x2, y2 = ux + uw // 2, uy + uh, vx + vw // 2, vy
            dy = max(32, abs(y2 - y1) * 0.45)
            path = f"M {x1} {y1} C {x1+36} {y1+dy:.1f}, {x2+36} {y2-dy:.1f}, {x2} {y2}"

        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        elbl = str(e.get("label", "")).strip()
        dashed = " dg-edge-dashed" if e.get("kind") in ("async", "optional", "return") else ""
        lbl_svg = ""
        if elbl:
            pw = min(140, max(44, len(elbl) * 6.5 + 14))
            lbl_svg = (
                f'<rect x="{mx-pw/2:.1f}" y="{my-10:.1f}" width="{pw:.1f}" height="20" rx="4" class="edge-pill"/>'
                f'<text x="{mx:.1f}" y="{my+3.5:.1f}" text-anchor="middle" class="edge-lbl">{_esc(elbl[:20])}</text>'
            )
        svg_parts.append(
            f'<g class="dg-edge{dashed}{_chg_classes(e)}" data-edge-id="{eid}" data-from="{_esc(u)}" data-to="{_esc(v)}">'
            f'<path d="{path}" class="edge-line" marker-end="url(#arrow-head)"/>{lbl_svg}</g>'
        )

    node_meta: dict[str, Any] = {}
    for nid, (nx, ny, nw, nh) in pos.items():
        n = nodes_map[nid]
        status = str(n.get("status", "default")).lower()
        rx = 24 if str(n.get("kind", "")).lower() in ("start", "terminal") else 6
        lines = _wrap_text(n.get("label", nid), 22)
        sub = str(n.get("sublabel") or n.get("role") or "")
        ev = str(n.get("evidence", "")).lower()
        body_svg = ""
        if dtype == "class":
            y_cur = ny + 24
            body_svg += f'<text x="{nx+nw/2}" y="{y_cur}" text-anchor="middle" class="node-title">{_esc(n.get("label", nid))}</text>'
            y_cur += 12
            body_svg += f'<line x1="{nx}" y1="{y_cur}" x2="{nx+nw}" y2="{y_cur}" class="node-sep"/>'
            for a in (n.get("attributes") or ["—"]):
                y_cur += 16
                body_svg += f'<text x="{nx+10}" y="{y_cur}" class="node-mono">{_esc(a)}</text>'
            y_cur += 8
            body_svg += f'<line x1="{nx}" y1="{y_cur}" x2="{nx+nw}" y2="{y_cur}" class="node-sep"/>'
            for m in (n.get("methods") or ["—"]):
                y_cur += 16
                body_svg += f'<text x="{nx+10}" y="{y_cur}" class="node-mono">{_esc(m)}</text>'
        else:
            ty = ny + (26 if sub else 30)
            for li, ltxt in enumerate(lines):
                body_svg += f'<text x="{nx+14}" y="{ty+li*18}" class="node-title">{_esc(ltxt)}</text>'
            if sub:
                body_svg += f'<text x="{nx+14}" y="{ny+nh-13}" class="node-sub">{_esc(sub[:28])}</text>'
            if ev and not n.get("change"):
                body_svg += f'<circle cx="{nx+nw-12}" cy="{ny+14}" r="4" class="ev-dot ev-{_esc(ev)}"/>'
            body_svg += _chg_badge_svg(n, nx + nw - 10, ny + 18)

        svg_parts.append(
            f'<g class="dg-node status-{_esc(status)}{_chg_classes(n)}" data-node-id="{_esc(nid)}" data-group="{_esc(n.get("group", ""))}" tabindex="0" role="button">'
            f'<rect x="{nx}" y="{ny}" width="{nw}" height="{nh}" rx="{rx}" class="node-box"/>'
            f'<rect x="{nx}" y="{ny}" width="3.5" height="{nh}" rx="2" class="node-accent"/>{body_svg}</g>'
        )
        node_meta[nid] = {**n, "cx": nx + nw / 2, "cy": ny + nh / 2, "x": nx, "y": ny, "w": nw, "h": nh}

    return "\n".join(svg_parts), total_w, total_h, node_meta, edge_meta


def _render_sequence_svg(spec: dict[str, Any]) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    parts = spec.get("participants", spec.get("nodes", []))
    msgs = spec.get("messages", spec.get("edges", []))
    col_w, pad_x, top_y, row_h = 180, 60, 40, 54
    px_map: dict[str, int] = {}
    svg_parts: list[str] = []
    node_meta: dict[str, Any] = {}
    edge_meta: dict[str, Any] = {}
    total_h = top_y + 70 + max(1, len(msgs)) * row_h + 40
    total_w = max(720, pad_x * 2 + max(1, len(parts)) * col_w)

    for idx, p in enumerate(parts):
        pid = p["id"]
        cx = pad_x + idx * col_w + col_w // 2
        px_map[pid] = cx
        svg_parts.append(f'<line x1="{cx}" y1="{top_y+44}" x2="{cx}" y2="{total_h-30}" class="seq-lifeline"/>')
        svg_parts.append(
            f'<g class="dg-node{_chg_classes(p)}" data-node-id="{_esc(pid)}" tabindex="0" role="button">'
            f'<rect x="{cx-74}" y="{top_y}" width="148" height="44" rx="6" class="node-box"/>'
            f'<text x="{cx}" y="{top_y+27}" text-anchor="middle" class="node-title">{_esc(p.get("label", pid))}</text></g>'
        )
        node_meta[pid] = {**p, "cx": cx, "cy": top_y + 22}

    for idx, m in enumerate(msgs):
        u, v = m.get("from"), m.get("to")
        if u not in px_map or v not in px_map:
            continue
        eid = f"e-{idx}"
        edge_meta[eid] = dict(m)
        x1, x2, y = px_map[u], px_map[v], top_y + 84 + idx * row_h
        dashed = " dg-edge-dashed" if m.get("kind") in ("return", "async") else ""
        lbl = f"{idx+1}. {m.get('label', '')}"
        path = f"M {x1} {y} C {x1+56} {y}, {x1+56} {y+26}, {x1} {y+26}" if x1 == x2 else f"M {x1} {y} L {x2} {y}"
        lx, ly = (x1 + 62, y + 16) if x1 == x2 else ((x1 + x2) / 2, y - 8)
        svg_parts.append(
            f'<g class="dg-edge{dashed}{_chg_classes(m)}" data-edge-id="{eid}" data-from="{_esc(u)}" data-to="{_esc(v)}">'
            f'<path d="{path}" class="edge-line" marker-end="url(#arrow-head)"/>'
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" class="edge-lbl">{_esc(lbl)}</text></g>'
        )
    return "\n".join(svg_parts), total_w, total_h, node_meta, edge_meta


def _render_erd_svg(spec: dict[str, Any]) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    entities = spec.get("entities", spec.get("nodes", []))
    rels = spec.get("relationships", spec.get("edges", []))
    cols = max(1, min(3, math.ceil(math.sqrt(max(1, len(entities))))))
    ent_w, gap_x, gap_y, pad = 250, 70, 56, 48

    def ent_h(e: dict[str, Any]) -> int:
        return 42 + max(1, len(e.get("attributes", []))) * 22 + 12

    pos: dict[str, tuple[int, int, int, int]] = {}
    row_y = pad
    for r_start in range(0, len(entities), cols):
        chunk = entities[r_start:r_start + cols]
        max_h = max(ent_h(e) for e in chunk)
        for c_idx, e in enumerate(chunk):
            pos[e["id"]] = (pad + c_idx * (ent_w + gap_x), row_y, ent_w, ent_h(e))
        row_y += max_h + gap_y

    total_w, total_h = max(720, pad * 2 + cols * ent_w + (cols - 1) * gap_x), max(400, row_y + pad)
    svg_parts, node_meta, edge_meta = [], {}, {}

    for idx, rel in enumerate(rels):
        u, v = rel.get("from"), rel.get("to")
        if u not in pos or v not in pos:
            continue
        eid = f"e-{idx}"
        edge_meta[eid] = dict(rel)
        ux, uy, uw, uh = pos[u]
        vx, vy, vw, vh = pos[v]
        x1, y1, x2, y2 = ux + uw // 2, uy + uh // 2, vx + vw // 2, vy + vh // 2
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        lbl = f"{rel.get('cardinality', '')} {rel.get('label', '')}".strip()
        svg_parts.append(
            f'<g class="dg-edge{_chg_classes(rel)}" data-edge-id="{eid}" data-from="{_esc(u)}" data-to="{_esc(v)}">'
            f'<path d="M {x1} {y1} L {x2} {y2}" class="edge-line" marker-end="url(#arrow-head)"/>'
            f'<rect x="{mx-45:.1f}" y="{my-10:.1f}" width="90" height="20" rx="4" class="edge-pill"/>'
            f'<text x="{mx:.1f}" y="{my+3.5:.1f}" text-anchor="middle" class="edge-lbl">{_esc(lbl[:18])}</text></g>'
        )

    for e in entities:
        eid = e["id"]
        x, y, w, h = pos[eid]
        rows_svg, ry = "", y + 40
        for col in e.get("attributes", []):
            keys = col.get("key", [])
            if isinstance(keys, str):
                keys = [keys]
            k_badge = "/".join(k.upper() for k in keys)
            prev_t = f"{col['previousType']}→" if col.get("previousType") else ""
            rows_svg += (
                f'<text x="{x+12}" y="{ry+14}" class="node-mono">{_esc(col.get("name", ""))}</text>'
                f'<text x="{x+w-12}" y="{ry+14}" text-anchor="end" class="node-sub">{_esc((k_badge + " " if k_badge else "") + prev_t + col.get("type", ""))}</text>'
            )
            ry += 22
        svg_parts.append(
            f'<g class="dg-node{_chg_classes(e)}" data-node-id="{_esc(eid)}" tabindex="0" role="button">'
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" class="node-box"/>'
            f'<rect x="{x}" y="{y}" width="{w}" height="34" rx="6" class="erd-head"/>'
            f'<text x="{x+12}" y="{y+22}" class="erd-title">{_esc(e.get("label", eid))}</text>{rows_svg}</g>'
        )
        node_meta[eid] = {**e, "cx": x + w / 2, "cy": y + h / 2}
    return "\n".join(svg_parts), total_w, total_h, node_meta, edge_meta


def _render_tree_svg(spec: dict[str, Any]) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    nodes, edges = spec.get("nodes", []), spec.get("edges", [])
    children: dict[str, list[str]] = defaultdict(list)
    has_parent: set[str] = set()
    for e in edges:
        children[e["from"]].append(e["to"])
        has_parent.add(e["to"])
    roots = [n["id"] for n in nodes if n["id"] not in has_parent] or ([nodes[0]["id"]] if nodes else [])
    nmap = {n["id"]: n for n in nodes}
    leaf_x, box_w, box_h, gap_x, gap_y = 0, 174, 62, 26, 56
    coords: dict[str, tuple[int, int]] = {}

    def place(nid: str, depth: int) -> float:
        nonlocal leaf_x
        ch = children.get(nid, [])
        if not ch:
            cx = 48 + leaf_x * (box_w + gap_x)
            leaf_x += 1
        else:
            cx = sum(place(c, depth + 1) for c in ch) / len(ch)
        coords[nid] = (int(cx), 48 + depth * (box_h + gap_y))
        return cx

    for r in roots:
        place(r, 0)

    total_w = max(720, max((x + box_w + 48 for x, _ in coords.values()), default=720))
    total_h = max(380, max((y + box_h + 48 for _, y in coords.values()), default=380))
    svg_parts, node_meta, edge_meta = [], {}, {}

    for idx, e in enumerate(edges):
        u, v = e["from"], e["to"]
        if u not in coords or v not in coords:
            continue
        eid = f"e-{idx}"
        edge_meta[eid] = dict(e)
        ux, uy = coords[u]
        vx, vy = coords[v]
        x1, y1, x2, y2 = ux + box_w // 2, uy + box_h, vx + box_w // 2, vy
        my = (y1 + y2) // 2
        svg_parts.append(
            f'<g class="dg-edge{_chg_classes(e)}" data-edge-id="{eid}" data-from="{_esc(u)}" data-to="{_esc(v)}">'
            f'<path d="M {x1} {y1} L {x1} {my} L {x2} {my} L {x2} {y2}" class="edge-line" marker-end="url(#arrow-head)"/></g>'
        )

    for nid, (x, y) in coords.items():
        n = nmap[nid]
        svg_parts.append(
            f'<g class="dg-node{_chg_classes(n)}" data-node-id="{_esc(nid)}" tabindex="0" role="button">'
            f'<rect x="{x}" y="{y}" width="{box_w}" height="{box_h}" rx="6" class="node-box"/>'
            f'<rect x="{x}" y="{y}" width="3.5" height="{box_h}" rx="2" class="node-accent"/>'
            f'<text x="{x+14}" y="{y+28}" class="node-title">{_esc(n.get("label", nid)[:20])}</text>'
            f'<text x="{x+14}" y="{y+48}" class="node-sub">{_esc(str(n.get("role", n.get("sublabel", "")))[:22])}</text></g>'
        )
        node_meta[nid] = {**n, "cx": x + box_w / 2, "cy": y + box_h / 2}
    return "\n".join(svg_parts), total_w, total_h, node_meta, edge_meta


def _render_timeline_waterfall_svg(spec: dict[str, Any]) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    dtype = spec.get("type", "timeline")
    items = spec.get("events" if dtype == "timeline" else "spans", spec.get("nodes", []))
    pad_l, pad_r, pad_t, row_h, chart_w = 200, 48, 52, 46, 640
    total_w, total_h = pad_l + chart_w + pad_r, max(320, pad_t + len(items) * row_h + 60)
    max_end = max((float(it.get("start", 0)) + float(it.get("duration", 1)) for it in items), default=100.0) or 1.0 if dtype == "waterfall" else max(1.0, float(len(items)))
    svg_parts = [f'<line x1="{pad_l}" y1="{pad_t}" x2="{pad_l+chart_w}" y2="{pad_t}" class="seq-lifeline"/>']
    node_meta: dict[str, Any] = {}

    for idx, it in enumerate(items):
        iid = str(it.get("id") or f"item-{idx}")
        y = pad_t + 22 + idx * row_h
        if dtype == "waterfall":
            bx = pad_l + (float(it.get("start", 0)) / max_end) * chart_w
            bw = max(14, (max(0.02 * max_end, float(it.get("duration", 1))) / max_end) * chart_w)
            meta_txt = f"{it.get('duration', 0)} {spec.get('unit', 'ms')}"
        else:
            bx, bw = pad_l + (idx / max(1, len(items))) * (chart_w - 140), 130
            meta_txt = str(it.get("date", it.get("time", f"T+{idx+1}")))
        status = str(it.get("status", "default")).lower()
        svg_parts.append(
            f'<g class="dg-node status-{_esc(status)}{_chg_classes(it)}" data-node-id="{_esc(iid)}" tabindex="0" role="button">'
            f'<text x="{pad_l-14}" y="{y+18}" text-anchor="end" class="node-title">{_esc(str(it.get("label", iid))[:24])}</text>'
            f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="26" rx="4" class="wf-bar"/>'
            f'<text x="{bx+bw+8:.1f}" y="{y+17}" class="node-mono">{_esc(meta_txt)}</text></g>'
        )
        node_meta[iid] = {**it, "id": iid, "cx": bx + bw / 2, "cy": y + 13}
    return "\n".join(svg_parts), total_w, total_h, node_meta, {}


def render_svg(spec: dict[str, Any], dual_theme_style: bool = False) -> tuple[str, int, int, dict[str, Any]]:
    """Render diagram spec to SVG (returns svg, width, height, node_meta)."""
    svg, w, h, nmeta, _ = _render_svg_full(spec, dual_theme_style=dual_theme_style)
    return svg, w, h, nmeta


def _render_svg_full(spec: dict[str, Any], dual_theme_style: bool = False) -> tuple[str, int, int, dict[str, Any], dict[str, Any]]:
    dtype = str(spec.get("type", "architecture")).lower()
    if dtype == "sequence":
        inner, w, h, nmeta, emeta = _render_sequence_svg(spec)
    elif dtype == "erd":
        inner, w, h, nmeta, emeta = _render_erd_svg(spec)
    elif dtype == "tree":
        inner, w, h, nmeta, emeta = _render_tree_svg(spec)
    elif dtype in ("timeline", "waterfall"):
        inner, w, h, nmeta, emeta = _render_timeline_waterfall_svg(spec)
    else:
        inner, w, h, nmeta, emeta = _render_layered_graph_svg(spec)

    style_block = f"<style>{DUAL_THEME_SVG_CSS}</style>\n" if dual_theme_style else ""
    svg = (
        f'<svg id="dg-svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
        f'role="img" aria-label="{_esc(spec.get("title", "Diagram"))}">\n'
        f'{style_block}<defs>\n'
        '  <marker id="arrow-head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">\n'
        '    <path d="M 0 1.5 L 9 5 L 0 8.5 z" class="arrow-fill"/>\n'
        '  </marker>\n</defs>\n'
        f'<g id="dg-viewport">\n{inner}\n</g>\n</svg>'
    )
    return svg, w, h, nmeta, emeta


def render_html(spec: dict[str, Any], lang: str = "id", theme: str = "light") -> str:
    """Render full standalone interactive HTML studio viewer."""
    t = I18N.get(lang, I18N["id"])
    svg_str, _, _, nmeta, emeta = _render_svg_full(spec, dual_theme_style=False)
    return build_viewer_html(spec, svg_str, nmeta, emeta, t, lang=lang, theme=theme)


def render_explainer_html(spec: dict[str, Any], lang: str = "id", theme: str = "light", preset: str = "institutional") -> str:
    """Render One-Page Visual Explainer from JSON spec or parsed .explainer.md doc."""
    atlas = render_atlas_star_svg(spec) if spec.get("findings") and spec.get("nodes") else ""
    return render_explainer_page(spec, render_svg, atlas_svg=atlas, lang=lang, theme=theme, preset=preset)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="IdeaForge Visual Architect Studio")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_val = sub.add_parser("validate", help="Validate diagram JSON IR")
    p_val.add_argument("input", type=Path)
    p_val.add_argument("--strict", action="store_true")
    p_val.add_argument("--json", action="store_true")

    p_ren = sub.add_parser("render", help="Render diagram JSON IR to interactive HTML & dual-theme SVG")
    p_ren.add_argument("input", type=Path)
    p_ren.add_argument("--output", type=Path, required=True)
    p_ren.add_argument("--svg-out", type=Path)
    p_ren.add_argument("--lang", choices=["id", "en"], default="id")
    p_ren.add_argument("--theme", choices=["light", "dark"], default="light")

    p_mmd = sub.add_parser("from-mermaid", help="Convert Mermaid diagram to JSON IR")
    p_mmd.add_argument("input", type=Path)
    p_mmd.add_argument("--output", type=Path, required=True)
    p_mmd.add_argument("--type", default="auto")
    p_mmd.add_argument("--title", default="Diagram")

    p_cmp = sub.add_parser("compare", help="Compare two diagram snapshots (Before | Delta | After)")
    p_cmp.add_argument("base", type=Path)
    p_cmp.add_argument("head", type=Path)
    p_cmp.add_argument("--output", type=Path, help="Output merged change-marked HTML")
    p_cmp.add_argument("--json-out", type=Path, help="Output delta JSON report")
    p_cmp.add_argument("--lang", choices=["id", "en"], default="id")

    p_pr = sub.add_parser("pr-diff", help="Build Git PR visual change-marked architecture & Markdown pack")
    p_pr.add_argument("repo_dir", type=Path)
    p_pr.add_argument("--base", default="HEAD~1")
    p_pr.add_argument("--head", default="HEAD")
    p_pr.add_argument("--out-dir", type=Path, required=True)
    p_pr.add_argument("--lang", choices=["id", "en"], default="id")

    p_repo = sub.add_parser("analyze-repo", help="Diagnose local repository architecture + Atlas Star Map")
    p_repo.add_argument("repo_dir", type=Path)
    p_repo.add_argument("--output", type=Path, required=True)
    p_repo.add_argument("--html-out", type=Path)
    p_repo.add_argument("--lang", choices=["id", "en"], default="id")

    p_exp = sub.add_parser("explainer", help="Render conclusion-first one-page explainer (.explainer.md or .json)")
    p_exp.add_argument("input", type=Path)
    p_exp.add_argument("--output", type=Path, required=True)
    p_exp.add_argument("--lang", choices=["id", "en"], default="id")
    p_exp.add_argument("--theme", choices=["light", "dark"], default="light")
    p_exp.add_argument("--preset", choices=["institutional", "briefing", "technical", "minimal"], default="institutional")

    args = parser.parse_args()

    if args.cmd == "validate":
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        res = validate_diagram(spec, strict=args.strict)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["ok"] else 1

    if args.cmd == "render":
        spec = json.loads(args.input.read_text(encoding="utf-8"))
        res = validate_diagram(spec)
        if not res["ok"]:
            print(json.dumps(res, indent=2, ensure_ascii=False), file=sys.stderr)
            return 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_html(spec, lang=args.lang, theme=args.theme), encoding="utf-8")
        if args.svg_out:
            svg_str, _, _, _ = render_svg(spec, dual_theme_style=True)
            args.svg_out.parent.mkdir(parents=True, exist_ok=True)
            args.svg_out.write_text(svg_str, encoding="utf-8")
        print(f"Rendered {spec.get('type')} -> {args.output}")
        return 0

    if args.cmd == "from-mermaid":
        spec = parse_mermaid(args.input.read_text(encoding="utf-8"), force_type=args.type, title=args.title)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Converted Mermaid ({spec['type']}) -> {args.output}")
        return 0

    if args.cmd == "compare":
        base = json.loads(args.base.read_text(encoding="utf-8"))
        head = json.loads(args.head.read_text(encoding="utf-8"))
        report, superset = compare_diagrams(base, head)
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(render_html(superset, lang=args.lang), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    if args.cmd == "pr-diff":
        spec, pr_md = build_pr_diff_pack(args.repo_dir.resolve(), base_ref=args.base, head_ref=args.head)
        args.out_dir.mkdir(parents=True, exist_ok=True)
        (args.out_dir / "pr-diff.diagram.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        (args.out_dir / "pr-diff.diagram.html").write_text(render_html(spec, lang=args.lang), encoding="utf-8")
        svg_s, _, _, _ = render_svg(spec, dual_theme_style=True)
        (args.out_dir / "pr-diff.diagram.svg").write_text(svg_s, encoding="utf-8")
        (args.out_dir / "pr-walkthrough.md").write_text(pr_md, encoding="utf-8")
        print(f"PR visual pack generated in {args.out_dir}")
        return 0

    if args.cmd == "analyze-repo":
        spec = analyze_repository(args.repo_dir.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
        if args.html_out:
            args.html_out.parent.mkdir(parents=True, exist_ok=True)
            args.html_out.write_text(render_explainer_html(spec, lang=args.lang), encoding="utf-8")
        print(f"Analyzed {args.repo_dir} -> {args.output} ({len(spec['nodes'])} modules, {len(spec['edges'])} edges)")
        return 0

    if args.cmd == "explainer":
        raw = args.input.read_text(encoding="utf-8")
        doc = parse_explainer_markdown(raw) if args.input.suffix.lower() in (".md", ".markdown") else json.loads(raw)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_explainer_html(doc, lang=args.lang, theme=args.theme, preset=args.preset), encoding="utf-8")
        print(f"Explainer -> {args.output}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
