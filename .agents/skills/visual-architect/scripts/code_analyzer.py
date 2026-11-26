"""Repository Architecture Diagnosis (Atlas + Coupling + Cycles + Fix Prompts),
Snapshot Comparison (Before | Delta | After), and Git PR Diff Visual Pack.
"""

from __future__ import annotations

import ast
import html
import math
import os
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any


def detect_cycles(node_ids: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Tarjan SCC to find cycles (>=2 nodes or self-loop)."""
    adj: dict[str, list[str]] = defaultdict(list)
    for u, v in edges:
        adj[u].append(v)

    index = 0
    indices: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[list[str]] = []

    def strongconnect(v: str) -> None:
        nonlocal index
        indices[v] = index
        lowlink[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)
        for w in adj.get(v, ()):
            if w not in indices:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], indices[w])
        if lowlink[v] == indices[v]:
            comp: list[str] = []
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.append(w)
                if w == v:
                    break
            if len(comp) > 1 or (len(comp) == 1 and comp[0] in adj.get(comp[0], ())):
                sccs.append(comp)

    for nid in node_ids:
        if nid not in indices:
            strongconnect(nid)
    return sccs


def analyze_repository(repo_root: Path, title: str | None = None) -> dict[str, Any]:
    """Scan Python, JS/TS, Go, Rust, Java, C/C++ files for coupling, cycles & hotspots."""
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".archify", "target"}
    exts = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".go", ".rs", ".java", ".c", ".cc", ".cpp", ".h", ".hpp"}

    files: list[Path] = []
    for root, dirs, fnames in os.walk(repo_root):
        dirs[:] = sorted(d for d in dirs if d not in skip_dirs and not d.startswith("."))
        for fn in sorted(fnames):
            p = Path(root) / fn
            if p.suffix.lower() in exts:
                files.append(p)

    modules: dict[str, dict[str, Any]] = {}
    stem_to_mod: dict[str, str] = {}

    for p in files:
        rel = p.relative_to(repo_root).as_posix()
        mod_id = re.sub(r"[^A-Za-z0-9_.-]", "_", rel)
        group = rel.split("/")[0] if "/" in rel else "root"
        text = p.read_text(encoding="utf-8", errors="replace")
        loc = len(text.splitlines())
        fn_count = 0
        imports: list[str] = []
        suf = p.suffix.lower()

        if suf == ".py":
            try:
                tree = ast.parse(text)
                fn_count = sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)))
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import):
                        imports.extend(a.name.split(".")[0] for a in n.names)
                    elif isinstance(n, ast.ImportFrom) and n.module:
                        imports.append(n.module.split(".")[0])
            except SyntaxError:
                pass
        elif suf in (".rs",):
            fn_count = len(re.findall(r"\b(?:fn|struct|enum|trait)\b", text))
            imports.extend(re.findall(r"\b(?:use|mod)\s+(?:crate::)?([A-Za-z0-9_]+)", text))
        elif suf in (".java",):
            fn_count = len(re.findall(r"\b(?:class|interface|enum|record)\b", text))
            imports.extend(m.split(".")[-1] for m in re.findall(r"\bimport\s+([A-Za-z0-9_.]+);", text))
        elif suf in (".c", ".cc", ".cpp", ".h", ".hpp"):
            fn_count = len(re.findall(r"\b(?:struct|class)\b", text))
            imports.extend(Path(m).stem for m in re.findall(r'#include\s+"([^"]+)"', text))
        else:
            fn_count = len(re.findall(r"\b(?:function|class|func)\b", text))
            for m in re.findall(r"""(?:from|import|require\()\s*['"]([^'"]+)['"]""", text):
                imports.append(Path(m).stem)

        modules[mod_id] = {
            "id": mod_id, "rel": rel, "label": p.name, "group": group,
            "loc": loc, "symbols": fn_count, "raw_imports": imports, "ext": suf,
        }
        stem_to_mod[p.stem] = mod_id

    edges: list[dict[str, Any]] = []
    edge_pairs: set[tuple[str, str]] = set()
    ca: dict[str, int] = defaultdict(int)
    ce: dict[str, int] = defaultdict(int)

    for mid, info in modules.items():
        for imp in info["raw_imports"]:
            target = stem_to_mod.get(imp)
            if target and target != mid and (mid, target) not in edge_pairs:
                edge_pairs.add((mid, target))
                edges.append({"from": mid, "to": target, "label": "imports"})
                ce[mid] += 1
                ca[target] += 1

    cycles = detect_cycles(list(modules.keys()), list(edge_pairs))
    cycle_members = {m for comp in cycles for m in comp}

    nodes: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    for mid, info in modules.items():
        a, e = ca[mid], ce[mid]
        instability = round(e / (a + e), 2) if (a + e) > 0 else 0.0
        is_hotspot = info["loc"] >= 450 or (a + e) >= 6
        status = "warn" if mid in cycle_members else ("conditional" if is_hotspot else "ok")
        if mid in cycle_members:
            findings.append({
                "severity": "high",
                "title": f"Circular dependency: {info['rel']}",
                "detail": "Module participates in a dependency cycle.",
                "focusNodes": [mid],
                "fix_task": f"Break the circular dependency involving `{info['rel']}` by extracting shared types/interfaces into a lower-level module and reversing one import.",
            })
        elif is_hotspot:
            findings.append({
                "severity": "medium",
                "title": f"Complexity hotspot: {info['rel']}",
                "detail": f"{info['loc']} LOC, {a} incoming / {e} outgoing dependencies (I={instability}).",
                "focusNodes": [mid],
                "fix_task": f"Refactor `{info['rel']}` ({info['loc']} LOC) into smaller cohesive submodules so each module has a single responsibility and lower coupling.",
            })
        nodes.append({
            "id": mid,
            "label": info["label"],
            "sublabel": f"{info['loc']} LOC · I={instability}",
            "group": info["group"],
            "role": f"{info['ext']} module",
            "status": status,
            "evidence": "verified",
            "source": f"{info['rel']}:1",
            "metrics": {
                "LOC": str(info["loc"]),
                "Symbols": str(info["symbols"]),
                "Ca (In)": str(a),
                "Ce (Out)": str(e),
                "Instability": str(instability),
            },
        })

    if not findings:
        findings.append({
            "severity": "low",
            "title": "Clean acyclic dependency graph",
            "detail": f"Scanned {len(nodes)} modules across {len({m['group'] for m in modules.values()})} folders with 0 circular dependencies.",
            "focusNodes": [],
            "fix_task": "No structural refactoring required; preserve acyclic boundaries as new modules are added.",
        })

    return {
        "type": "architecture",
        "title": title or f"Architecture Diagnosis: {repo_root.name}",
        "subtitle": f"{len(nodes)} modules · {len(edges)} internal dependencies · {len(cycles)} cycles",
        "conclusion": (
            f"Detected {len(cycles)} circular dependencies and {sum(1 for f in findings if f['severity']=='medium')} complexity hotspots across {len(nodes)} source files."
            if cycles or any(f["severity"] == "medium" for f in findings)
            else f"Healthy modular structure across {len(nodes)} files with zero circular dependencies."
        ),
        "nodes": nodes,
        "edges": edges,
        "findings": findings,
        "stats": {"modules": len(nodes), "edges": len(edges), "cycles": len(cycles)},
    }


def render_atlas_star_svg(spec: dict[str, Any]) -> str:
    """Render a radial Atlas Dependency Star Map SVG (modules around a ring, chords across)."""
    nodes = spec.get("nodes", [])
    edges = spec.get("edges", [])
    size = 640
    cx, cy, r = size // 2, size // 2, 220
    n = max(1, len(nodes))
    coords: dict[str, tuple[float, float]] = {}
    parts: list[str] = [
        f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="var(--line)" stroke-dasharray="4 4"/>'
    ]
    for i, nd in enumerate(nodes):
        ang = (2 * math.pi * i / n) - math.pi / 2
        x = cx + r * math.cos(ang)
        y = cy + r * math.sin(ang)
        coords[nd["id"]] = (x, y)

    for idx, e in enumerate(edges):
        u, v = e.get("from"), e.get("to")
        if u not in coords or v not in coords:
            continue
        x1, y1 = coords[u]
        x2, y2 = coords[v]
        parts.append(
            f'<g class="dg-edge" data-edge-id="ae-{idx}" data-from="{html.escape(u)}" data-to="{html.escape(v)}">'
            f'<path d="M {x1:.1f} {y1:.1f} Q {cx} {cy} {x2:.1f} {y2:.1f}" class="edge-line" opacity="0.65"/>'
            '</g>'
        )

    for i, nd in enumerate(nodes):
        nid = nd["id"]
        x, y = coords[nid]
        ang = (2 * math.pi * i / n) - math.pi / 2
        lx = cx + (r + 18) * math.cos(ang)
        ly = cy + (r + 18) * math.sin(ang)
        anchor = "start" if math.cos(ang) >= 0 else "end"
        st = nd.get("status", "ok")
        fill = "var(--nogo)" if st == "warn" else ("var(--conditional)" if st == "conditional" else "var(--go)")
        parts.append(
            f'<g class="dg-node" data-node-id="{html.escape(nid)}">'
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{fill}" stroke="var(--surface)" stroke-width="2"/>'
            f'<text x="{lx:.1f}" y="{ly+4:.1f}" text-anchor="{anchor}" class="node-mono">{html.escape(nd.get("label", nid)[:20])}</text>'
            '</g>'
        )
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}" role="img" aria-label="Atlas Dependency Star Map">{"".join(parts)}</svg>'


def compare_diagrams(base: dict[str, Any], head: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compare two architecture/workflow/dataflow snapshots -> (delta_report, merged_superset_spec)."""
    b_nodes = {n["id"]: n for n in base.get("nodes", [])}
    h_nodes = {n["id"]: n for n in head.get("nodes", [])}
    b_edges = {(e["from"], e["to"]): e for e in base.get("edges", [])}
    h_edges = {(e["from"], e["to"]): e for e in head.get("edges", [])}

    merged_nodes: list[dict[str, Any]] = []
    added_n, modified_n, removed_n = [], [], []

    for nid in list(h_nodes.keys()) + [k for k in b_nodes if k not in h_nodes]:
        if nid in h_nodes and nid not in b_nodes:
            merged_nodes.append({**h_nodes[nid], "change": "added"})
            added_n.append(nid)
        elif nid in b_nodes and nid not in h_nodes:
            merged_nodes.append({**b_nodes[nid], "change": "removed"})
            removed_n.append(nid)
        else:
            bn, hn = b_nodes[nid], h_nodes[nid]
            changed = (bn.get("label") != hn.get("label") or bn.get("group") != hn.get("group") or bn.get("tech") != hn.get("tech"))
            if changed:
                merged_nodes.append({**hn, "change": "modified"})
                modified_n.append(nid)
            else:
                merged_nodes.append({**hn, "change": "unchanged"})

    merged_edges: list[dict[str, Any]] = []
    added_e, modified_e, removed_e = [], [], []
    all_keys = list(h_edges.keys()) + [k for k in b_edges if k not in h_edges]
    for k in all_keys:
        if k in h_edges and k not in b_edges:
            merged_edges.append({**h_edges[k], "change": "added"})
            added_e.append(f"{k[0]}->{k[1]}")
        elif k in b_edges and k not in h_edges:
            merged_edges.append({**b_edges[k], "change": "removed"})
            removed_e.append(f"{k[0]}->{k[1]}")
        else:
            be, he = b_edges[k], h_edges[k]
            if be.get("label") != he.get("label") or be.get("kind") != he.get("kind"):
                merged_edges.append({**he, "change": "modified"})
                modified_e.append(f"{k[0]}->{k[1]}")
            else:
                merged_edges.append({**he, "change": "unchanged"})

    report = {
        "before": {"nodes": len(b_nodes), "edges": len(b_edges)},
        "after": {"nodes": len(h_nodes), "edges": len(h_edges)},
        "delta": {
            "added_nodes": added_n, "modified_nodes": modified_n, "removed_nodes": removed_n,
            "added_edges": added_e, "modified_edges": modified_e, "removed_edges": removed_e,
        },
    }
    superset = {
        "type": head.get("type", base.get("type", "architecture")),
        "title": f"Delta: {head.get('title', 'Architecture')}",
        "subtitle": f"+{len(added_n)} added · ~{len(modified_n)} modified · -{len(removed_n)} removed",
        "nodes": merged_nodes,
        "edges": merged_edges,
    }
    return report, superset


def build_pr_diff_pack(repo_root: Path, base_ref: str = "HEAD~1", head_ref: str = "HEAD") -> tuple[dict[str, Any], str]:
    """Run git diff --name-status and overlay change marks onto repository architecture."""
    spec = analyze_repository(repo_root, title=f"PR Visual Diff ({base_ref}..{head_ref})")
    changes_by_rel: dict[str, str] = {}
    try:
        out = subprocess.check_output(
            ["git", "-C", str(repo_root), "diff", "--name-status", f"{base_ref}..{head_ref}"],
            stderr=subprocess.DEVNULL, text=True,
        )
        for line in out.splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                code, path = parts[0][0], parts[-1]
                changes_by_rel[path] = {"A": "added", "M": "modified", "D": "removed", "R": "modified"}.get(code, "modified")
    except Exception:
        pass

    node_by_rel = {n.get("source", "").split(":")[0]: n for n in spec["nodes"]}
    for rel, chg in changes_by_rel.items():
        if rel in node_by_rel:
            node_by_rel[rel]["change"] = chg
        elif chg == "removed":
            rid = re.sub(r"[^A-Za-z0-9_.-]", "_", rel)
            spec["nodes"].append({
                "id": rid, "label": Path(rel).name, "group": rel.split("/")[0] if "/" in rel else "root",
                "role": "removed file", "change": "removed", "source": f"{rel}:1",
            })

    # Mark unchanged on remaining nodes if any change exists
    if changes_by_rel:
        for n in spec["nodes"]:
            n.setdefault("change", "unchanged")

    rows = "\n".join(f"| `{rel}` | `{chg}` |" for rel, chg in sorted(changes_by_rel.items())) or "| *(no git diff detected)* | — |"
    pr_md = (
        f"## Architecture Change Walkthrough (`{base_ref}..{head_ref}`)\n\n"
        f"- **Files changed**: {len(changes_by_rel)}\n"
        f"- **Repository modules**: {len(spec['nodes'])} · **Cycles**: {spec['stats']['cycles']}\n\n"
        "| File | Change |\n|---|---|\n"
        f"{rows}\n"
    )
    return spec, pr_md
