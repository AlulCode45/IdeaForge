#!/usr/bin/env python3
"""Lint an IdeaForge project folder for structural, arithmetic, and evidence quality gates.

Usage:
  python3 scripts/lint_project.py prps/<project-slug> [--index prps/INDEX.md] [--strict] [--max-age-days 365]
"""
import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

SLOP_TERMS = [
    "revolutionary",
    "game-changer",
    "game changer",
    "disruptive",
    "100% pasti",
    "tanpa risiko",
    "guaranteed success",
]
EVIDENCE_TAGS = ("[Verified]", "[Estimate]", "[Assumption]", "[Unverified]")


def check_core_files(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    for fname in ("README.md", "CHANGELOG.md", "13-assumption-register.md"):
        if (proj_dir / fname).exists():
            findings.append(("PASS", f"Core file present: {fname}"))
        else:
            findings.append(("FAIL", f"Missing core file: {fname}"))


def check_links(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    broken = []
    link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
    for md in sorted(proj_dir.rglob("*.md")):
        text = md.read_text(encoding="utf-8")
        for target in link_re.findall(text):
            target = target.strip().split()[0]
            if target.startswith(("http://", "https://", "mailto:", "#", "file://")):
                continue
            target_no_anchor = target.split("#")[0]
            if not target_no_anchor:
                continue
            resolved = (md.parent / target_no_anchor).resolve()
            if not resolved.exists():
                broken.append(f"{md.name} -> {target}")
    if broken:
        for b in broken:
            findings.append(("FAIL", f"Broken relative link: {b}"))
    else:
        findings.append(("PASS", "All relative Markdown links resolve."))


def check_scorecard(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    sc_path = proj_dir / "17-scorecard-and-decision.md"
    if not sc_path.exists():
        return
    text = sc_path.read_text(encoding="utf-8")
    weight_sum = 0.0
    calc_total = 0.0
    stated_total = None
    row_count = 0

    for line in text.splitlines():
        s = line.strip()
        if not s.startswith("|") or "---" in s:
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 4:
            continue
        crit = cells[0].lower()
        if crit in ("criterion", "kriteria"):
            continue
        if "total" in crit:
            m = re.search(r"(\d+(?:[.,]\d+)?)", cells[3])
            if m:
                stated_total = float(m.group(1).replace(",", "."))
            continue
        w_m = re.search(r"(\d+(?:[.,]\d+)?)", cells[1])
        sc_m = re.search(r"(\d+(?:[.,]\d+)?)", cells[2])
        wt_m = re.search(r"(\d+(?:[.,]\d+)?)", cells[3])
        if w_m and sc_m and wt_m:
            row_count += 1
            w = float(w_m.group(1).replace(",", "."))
            sc = float(sc_m.group(1).replace(",", "."))
            wt = float(wt_m.group(1).replace(",", "."))
            weight_sum += w
            expected = round(w * sc / 100.0, 4)
            calc_total += expected
            if abs(wt - expected) > 0.02:
                findings.append(("FAIL", f"Scorecard row '{cells[0]}' weighted={wt} != {w}*{sc}/100 ({expected:.2f})"))

    if row_count == 0:
        findings.append(("WARN", "Scorecard file exists but no numeric rows were parsed."))
        return

    if abs(weight_sum - 100.0) > 0.1:
        findings.append(("FAIL", f"Scorecard weights sum to {weight_sum:.1f}, expected 100."))
    else:
        findings.append(("PASS", "Scorecard weights sum to 100."))

    if stated_total is not None and abs(stated_total - calc_total) > 0.05:
        findings.append(("FAIL", f"Scorecard stated total {stated_total:.2f} != calculated {calc_total:.2f}."))

    # Check verdict alignment
    verdict_m = re.search(r"##\s*Verdict\s*\n+([^\n#]+)", text, flags=re.I)
    if verdict_m:
        verdict_line = verdict_m.group(1).lower()
        if calc_total >= 4.0 and "no-go" in verdict_line:
            findings.append(("FAIL", f"Score {calc_total:.2f} >= 4.0 contradicts No-Go verdict."))
        elif calc_total < 3.0 and "go" in verdict_line and "no-go" not in verdict_line and "condition" not in verdict_line:
            findings.append(("FAIL", f"Score {calc_total:.2f} < 3.0 contradicts unconditional Go verdict."))


def check_stale_dates(proj_dir: Path, max_age_days: int, findings: list[tuple[str, str]]) -> None:
    today = date.today()
    date_re = re.compile(r"\b(20\d{2}-\d{2}-\d{2})\b")
    stale_hits = []
    for fname in ("07-market-research.md", "15-competitor-analysis.md", "16-compliance-and-legal.md"):
        p = proj_dir / fname
        if not p.exists():
            continue
        for idx, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if "[Stale]" in line or "Last reviewed" in line:
                continue
            if "http" in line or "accessed" in line.lower() or "source" in line.lower():
                for d_str in date_re.findall(line):
                    try:
                        d_val = datetime.strptime(d_str, "%Y-%m-%d").date()
                        if (today - d_val).days > max_age_days:
                            stale_hits.append(f"{fname}:{idx} ({d_str})")
                    except ValueError:
                        pass
    if stale_hits:
        findings.append(("WARN", f"Potentially stale source dates (>{max_age_days}d) without [Stale]: {', '.join(stale_hits[:5])}"))
    else:
        findings.append(("PASS", f"No unmarked stale source dates (>{max_age_days}d)."))


def check_evidence_labels(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    num_claim_re = re.compile(r"(?:IDR|Rp|USD|\$)\s*\d|\d+(?:[.,]\d+)?%")
    for fname in ("07-market-research.md", "11-financial-plan.md", "15-competitor-analysis.md", "18-executive-summary.md"):
        p = proj_dir / fname
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8")
        if num_claim_re.search(text) and not any(tag in text for tag in EVIDENCE_TAGS):
            findings.append(("WARN", f"{fname} has numeric/currency claims but zero evidence tags ({', '.join(EVIDENCE_TAGS)})."))


def check_financial_consistency(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    sum_path = proj_dir / "model" / "summary.json"
    exec_path = proj_dir / "18-executive-summary.md"
    if not (sum_path.exists() and exec_path.exists()):
        return
    summary = json.loads(sum_path.read_text(encoding="utf-8"))
    exec_text = exec_path.read_text(encoding="utf-8")
    base = summary.get("scenarios", {}).get("base")
    if not base:
        return
    be = base.get("breakeven_month")
    if be is not None:
        if not re.search(rf"\b(?:bulan ke-|month\s+){be}\b", exec_text, flags=re.I):
            findings.append(("WARN", f"18-executive-summary.md does not mention base break-even Month {be} from model/summary.json."))
        else:
            findings.append(("PASS", f"18-executive-summary.md matches base break-even Month {be}."))


def check_anti_slop(proj_dir: Path, findings: list[tuple[str, str]]) -> None:
    exec_path = proj_dir / "18-executive-summary.md"
    if not exec_path.exists():
        return
    text = exec_path.read_text(encoding="utf-8")
    issues = []
    if "\u2014" in text:
        issues.append("em-dash (—)")
    for term in SLOP_TERMS:
        if term in text.lower():
            issues.append(f"hype term '{term}'")
    if issues:
        findings.append(("WARN", f"Editorial slop detected in 18-executive-summary.md: {', '.join(issues)}"))
    else:
        findings.append(("PASS", "18-executive-summary.md passes anti-slop check."))


def check_index_registration(proj_dir: Path, index_path: Path, findings: list[tuple[str, str]]) -> None:
    if not index_path.exists():
        findings.append(("WARN", f"Portfolio index not found: {index_path}"))
        return
    if proj_dir.name in index_path.read_text(encoding="utf-8"):
        findings.append(("PASS", f"Project registered in {index_path.name}."))
    else:
        findings.append(("WARN", f"Project '{proj_dir.name}' is not listed in {index_path}."))


def main():
    ap = argparse.ArgumentParser(description="Lint an IdeaForge project directory.")
    ap.add_argument("project_dir", help="Path to prps/<project-slug>")
    ap.add_argument("--index", help="Path to prps/INDEX.md (default: <project_dir>/../INDEX.md)")
    ap.add_argument("--strict", action="store_true", help="Exit 1 on warnings as well as failures")
    ap.add_argument("--max-age-days", type=int, default=365, help="Max age in days before source dates are flagged")
    args = ap.parse_args()

    proj_dir = Path(args.project_dir).resolve()
    if not proj_dir.is_dir():
        print(f"[FAIL] Project directory does not exist: {proj_dir}", file=sys.stderr)
        sys.exit(1)

    index_path = Path(args.index).resolve() if args.index else (proj_dir.parent / "INDEX.md")
    findings: list[tuple[str, str]] = []

    check_core_files(proj_dir, findings)
    check_links(proj_dir, findings)
    check_scorecard(proj_dir, findings)
    check_stale_dates(proj_dir, args.max_age_days, findings)
    check_evidence_labels(proj_dir, findings)
    check_financial_consistency(proj_dir, findings)
    check_anti_slop(proj_dir, findings)
    check_index_registration(proj_dir, index_path, findings)

    fails = sum(1 for sev, _ in findings if sev == "FAIL")
    warns = sum(1 for sev, _ in findings if sev == "WARN")
    for sev, msg in findings:
        print(f"[{sev}] {msg}")
    print(f"\nSummary: {fails} FAIL, {warns} WARN")

    if fails > 0 or (args.strict and warns > 0):
        sys.exit(1)


if __name__ == "__main__":
    main()
