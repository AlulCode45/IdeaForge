#!/usr/bin/env python3
"""Initialize a structured project folder under prps/, a standalone PRD under prds/, or a quick brief under ideas/.

Usage:
  python3 scripts/init_project.py --slug kasir-umkm --title "Kasir UMKM SaaS" --track full --model-type saas
  python3 scripts/init_project.py --slug checkout-v2 --title "Checkout v2" --track prd
"""
import argparse
import re
import shutil
from datetime import date
from pathlib import Path

TRACK_FILES = {
    "prd": [
        "PRD.md",
        "13-assumption-register.md",
    ],
    "tech": [
        "00-overview.md",
        "01-users-and-flows.md",
        "02-requirements.md",
        "03-architecture.md",
        "04-data-model.md",
        "05-roadmap-and-tasks.md",
        "06-risks-and-mitigation.md",
        "13-assumption-register.md",
        "17-scorecard-and-decision.md",
    ],
    "business": [
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
        "17-scorecard-and-decision.md",
        "18-executive-summary.md",
        "19-retrospective.md",
    ],
    "full": [
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
        "18-executive-summary.md",
        "19-retrospective.md",
    ],
}


def sanitize_slug(raw: str) -> str:
    slug = re.sub(r"[^a-z0-9-]+", "-", raw.strip().lower()).strip("-")
    if not slug:
        raise ValueError("Slug cannot be empty.")
    return slug


def update_index(index_path: Path, title: str, folder_rel: str, track: str, today: str) -> None:
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(
            "# Portfolio Index\n\n"
            "One row per project or idea. Update status whenever a stage finishes.\n\n"
            "| Project | Folder | Track | Stage reached | Decision | Score | Last updated |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    content = index_path.read_text(encoding="utf-8")
    if folder_rel in content:
        return
    # Match existing 6-column or 7-column index table
    header_line = next((ln for ln in content.splitlines() if ln.startswith("| Project ")), "")
    cols = header_line.count("|") - 1
    if cols >= 7:
        row = f"| {title} | `{folder_rel}` | {track} | Initialized | Pending | - | {today} |\n"
    else:
        row = f"| {title} | `{folder_rel}` | Initialized ({track}) | Pending | - | {today} |\n"
    if not content.endswith("\n"):
        content += "\n"
    index_path.write_text(content + row, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Initialize an IdeaForge project or quick brief.")
    ap.add_argument("--slug", required=True, help="Lowercase hyphenated project slug")
    ap.add_argument("--title", required=True, help="Human-readable project title")
    ap.add_argument("--track", choices=["quick", "prd", "tech", "business", "full"], default="full", help="Engagement track")
    ap.add_argument("--date", default=date.today().isoformat(), help="ISO date YYYY-MM-DD")
    ap.add_argument("--currency", default="IDR", help="Default currency (e.g., IDR, USD)")
    ap.add_argument("--jurisdiction", default="Indonesia", help="Default legal jurisdiction")
    ap.add_argument("--model-type", choices=["transactional", "saas"], default="transactional", help="Financial model template type")
    ap.add_argument("--base-dir", default=".", help="Workspace root directory")
    ap.add_argument("--force", action="store_true", help="Overwrite existing scaffold files if present")
    args = ap.parse_args()

    slug = sanitize_slug(args.slug)
    root = Path(args.base_dir).resolve()
    templates_dir = root / "templates"

    if args.track == "quick":
        topic_dir = root / "ideas" / slug
        assets_dir = topic_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        brief_path = topic_dir / f"{args.date}-brief.md"
        if brief_path.exists() and not args.force:
            print(f"Already exists: {brief_path}")
            return
        brief_path.write_text(
            f"# {args.title}\n\n"
            f"- **Date**: {args.date}\n"
            f"- **Track**: Quick Brief\n"
            f"- **Currency**: {args.currency} | **Jurisdiction**: {args.jurisdiction}\n"
            f"- **Confidentiality**: Local-only (do not push without explicit approval)\n"
            f"- **Status**: Exploring\n\n"
            "## Context & Goal\n\n\n"
            "## Key Options Explored\n- **Option A**:\n- **Option B**:\n\n"
            "## Top Risks & Pass/Kill Criteria\n- \n\n"
            "## Decision & Next Steps\n- [ ] \n",
            encoding="utf-8",
        )
        print(f"Initialized Quick Brief: {brief_path}")
        return

    folder_name = f"{args.date}-{slug}"
    is_prd = args.track == "prd"
    base_folder = "prds" if is_prd else "prps"
    proj_dir = root / base_folder / folder_name
    subfolders = ("decisions", "assets") if is_prd else ("decisions", "model", "assets")
    for sub in subfolders:
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    # README.md
    readme_path = proj_dir / "README.md"
    if not readme_path.exists() or args.force:
        checklist = "\n".join(f"- [ ] `{f}`" for f in TRACK_FILES[args.track])
        model_line = "" if is_prd else f"- **Model Type**: `{args.model_type}`\n"
        model_folder_line = "" if is_prd else "- `model/` — `inputs.json` and `summary.json` for `financial-modeler`\n"
        readme_path.write_text(
            f"# {args.title}\n\n"
            f"- **Track**: `{args.track}`\n"
            f"- **Created**: {args.date}\n"
            f"- **Currency**: {args.currency}\n"
            f"- **Jurisdiction**: {args.jurisdiction}\n"
            f"{model_line}"
            f"- **Confidentiality**: Local-only (never push `{base_folder}/` to `origin` without explicit approval)\n\n"
            f"## Documents ({args.track} track)\n\n"
            f"{checklist}\n\n"
            "## Folders\n"
            "- `decisions/` — Architecture & strategic Decision Records (`ADR-NNN-<slug>.md`)\n"
            f"{model_folder_line}"
            "- `assets/` — SVG charts, illustrations, and exported PDFs\n",
            encoding="utf-8",
        )

    # CHANGELOG.md
    changelog_path = proj_dir / "CHANGELOG.md"
    if not changelog_path.exists() or args.force:
        tpl = templates_dir / "changelog.md"
        if tpl.exists():
            text = tpl.read_text(encoding="utf-8").replace("<Project>", args.title).replace("YYYY-MM-DD", args.date).replace("vX.Y", "v0.1")
        else:
            text = f"# Changelog - {args.title}\n\n## v0.1 - {args.date}\n- Initialized project ({args.track} track).\n"
        changelog_path.write_text(text, encoding="utf-8")

    # 13-assumption-register.md
    ar_path = proj_dir / "13-assumption-register.md"
    if not ar_path.exists() or args.force:
        tpl = templates_dir / "assumption-register.md"
        if tpl.exists():
            text = tpl.read_text(encoding="utf-8").replace("<Project>", args.title).replace("YYYY-MM-DD", args.date)
        else:
            text = f"# Assumption Register - {args.title}\n\nLast reviewed: {args.date}\n"
        ar_path.write_text(text, encoding="utf-8")

    # PRD.md for standalone prd track
    if is_prd:
        prd_path = proj_dir / "PRD.md"
        if not prd_path.exists() or args.force:
            tpl = templates_dir / "prd.md"
            if tpl.exists():
                text = tpl.read_text(encoding="utf-8").replace("<Project>", args.title).replace("YYYY-MM-DD", args.date)
            else:
                text = f"# Product Requirements Document (PRD) - {args.title}\n\nDate: {args.date}\n"
            prd_path.write_text(text, encoding="utf-8")

    # model/inputs.json for business/full tracks
    if args.track in ("business", "full"):
        inputs_dest = proj_dir / "model" / "inputs.json"
        if not inputs_dest.exists() or args.force:
            src_name = "example_saas_inputs.json" if args.model_type == "saas" else "example_inputs.json"
            src_path = root / ".agents" / "skills" / "financial-modeler" / "scripts" / src_name
            if src_path.exists():
                shutil.copyfile(src_path, inputs_dest)

    update_index(root / base_folder / "INDEX.md", args.title, f"{base_folder}/{folder_name}", args.track, args.date)
    label = "PRD project" if is_prd else "project"
    print(f"Initialized {label}: {proj_dir}")


if __name__ == "__main__":
    main()
