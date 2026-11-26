#!/usr/bin/env python3
"""Initialize or upgrade a Modular Super PRD under prds/, or a quick brief under ideas/.

Usage:
  # Core PRD (default, coding-agent-ready)
  python3 scripts/init_project.py --slug checkout-v2 --title "Checkout v2" --track prd

  # Super PRD with Technical + Business + Financial Model
  python3 scripts/init_project.py --slug kasir-umkm --title "Kasir UMKM SaaS" --track full --model-type saas

  # Upgrade an existing Core PRD in-place with Technical or Business/Financial modules
  python3 scripts/init_project.py --upgrade prds/2026-11-26-checkout-v2 --add business --model-type saas
"""
import argparse
import re
import shutil
from datetime import date
from pathlib import Path

CORE_PRD_FILES = [
    "PRD.md",
    "13-assumption-register.md",
]

TECH_MODULE_FILES = [
    "03-architecture.md",
    "04-data-model.md",
    "05-roadmap-and-tasks.md",
    "06-risks-and-mitigation.md",
    "17-scorecard-and-decision.md",
]

BUSINESS_MODULE_FILES = [
    "07-market-research.md",
    "15-competitor-analysis.md",
    "14-customer-discovery.md",
    "08-swot.md",
    "09-opportunity-analysis.md",
    "10-management-plan.md",
    "11-financial-plan.md",
    "16-compliance-and-legal.md",
    "12-go-to-market-and-risk.md",
    "17-scorecard-and-decision.md",
    "18-executive-summary.md",
    "19-retrospective.md",
]


def _dedupe(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


TRACK_FILES = {
    "prd": list(CORE_PRD_FILES),
    "tech": _dedupe(CORE_PRD_FILES + TECH_MODULE_FILES),
    "business": _dedupe(CORE_PRD_FILES + BUSINESS_MODULE_FILES),
    "full": _dedupe(CORE_PRD_FILES + TECH_MODULE_FILES + BUSINESS_MODULE_FILES),
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
            "One row per PRD or project. Update status whenever a stage finishes.\n\n"
            "| Project | Folder | Track | Stage reached | Decision | Score | Last updated |\n"
            "|---|---|---|---|---|---|---|\n",
            encoding="utf-8",
        )
    content = index_path.read_text(encoding="utf-8")
    if folder_rel in content:
        return
    header_line = next((ln for ln in content.splitlines() if ln.startswith("| Project ")), "")
    cols = header_line.count("|") - 1
    if cols >= 7:
        row = f"| {title} | `{folder_rel}` | {track} | Initialized | Pending | - | {today} |\n"
    else:
        row = f"| {title} | `{folder_rel}` | Initialized ({track}) | Pending | - | {today} |\n"
    if not content.endswith("\n"):
        content += "\n"
    index_path.write_text(content + row, encoding="utf-8")


def _copy_model_inputs(root: Path, proj_dir: Path, model_type: str, force: bool = False) -> None:
    (proj_dir / "model").mkdir(parents=True, exist_ok=True)
    inputs_dest = proj_dir / "model" / "inputs.json"
    if not inputs_dest.exists() or force:
        src_name = "example_saas_inputs.json" if model_type == "saas" else "example_inputs.json"
        src_path = root / ".agents" / "skills" / "financial-modeler" / "scripts" / src_name
        if src_path.exists():
            shutil.copyfile(src_path, inputs_dest)


def upgrade_project(root: Path, proj_dir: Path, add_track: str, model_type: str, today: str, force: bool = False) -> None:
    """Upgrade an existing PRD project in-place by adding technical or business/financial modules."""
    if not proj_dir.is_dir():
        raise FileNotFoundError(f"Project directory not found: {proj_dir}")
    for sub in ("decisions", "assets"):
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    new_files = TRACK_FILES[add_track]
    if add_track in ("business", "full"):
        _copy_model_inputs(root, proj_dir, model_type, force=force)

    readme_path = proj_dir / "README.md"
    if readme_path.exists():
        content = readme_path.read_text(encoding="utf-8")
        missing_lines = [f"- [ ] `{f}`" for f in new_files if f"`{f}`" not in content]
        if missing_lines:
            section = f"\n## Added Modules (`{add_track}` — {today})\n\n" + "\n".join(missing_lines) + "\n"
            if not content.endswith("\n"):
                content += "\n"
            readme_path.write_text(content + section, encoding="utf-8")

    changelog_path = proj_dir / "CHANGELOG.md"
    if changelog_path.exists():
        cl = changelog_path.read_text(encoding="utf-8")
        if not cl.endswith("\n"):
            cl += "\n"
        cl += f"\n## Upgrade ({add_track}) - {today}\n- Added `{add_track}` extension modules to PRD project.\n"
        changelog_path.write_text(cl, encoding="utf-8")

    print(f"Upgraded PRD project ({add_track}): {proj_dir}")


def main():
    ap = argparse.ArgumentParser(description="Initialize or upgrade a Modular Super PRD or Quick Brief.")
    ap.add_argument("--slug", help="Lowercase hyphenated project slug (required unless using --upgrade)")
    ap.add_argument("--title", help="Human-readable project title (required unless using --upgrade)")
    ap.add_argument("--track", choices=["quick", "prd", "tech", "business", "full"], default="prd", help="PRD module tier or quick brief")
    ap.add_argument("--upgrade", help="Existing PRD folder path to upgrade in-place (e.g. prds/2026-11-26-kasir-fb)")
    ap.add_argument("--add", choices=["tech", "business", "full"], default="full", help="Extension module pack to add when using --upgrade")
    ap.add_argument("--date", default=date.today().isoformat(), help="ISO date YYYY-MM-DD")
    ap.add_argument("--currency", default="IDR", help="Default currency (e.g., IDR, USD)")
    ap.add_argument("--jurisdiction", default="Indonesia", help="Default legal jurisdiction")
    ap.add_argument("--model-type", choices=["transactional", "saas"], default="transactional", help="Financial model template type")
    ap.add_argument("--base-dir", default=".", help="Workspace root directory")
    ap.add_argument("--force", action="store_true", help="Overwrite existing scaffold files if present")
    args = ap.parse_args()

    root = Path(args.base_dir).resolve()

    if args.upgrade:
        target_dir = Path(args.upgrade)
        if not target_dir.is_absolute():
            target_dir = (root / target_dir).resolve()
        upgrade_project(root, target_dir, args.add, args.model_type, args.date, force=args.force)
        return

    if not args.slug or not args.title:
        ap.error("--slug and --title are required unless using --upgrade.")

    slug = sanitize_slug(args.slug)
    templates_dir = root / "templates"

    if args.track == "quick":
        topic_dir = root / "ideas" / slug
        (topic_dir / "assets").mkdir(parents=True, exist_ok=True)
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
    base_folder = "prds"
    proj_dir = root / base_folder / folder_name
    has_model = args.track in ("business", "full")
    subfolders = ("decisions", "model", "assets") if has_model else ("decisions", "assets")
    for sub in subfolders:
        (proj_dir / sub).mkdir(parents=True, exist_ok=True)

    # README.md
    readme_path = proj_dir / "README.md"
    if not readme_path.exists() or args.force:
        checklist = "\n".join(f"- [ ] `{f}`" for f in TRACK_FILES[args.track])
        model_line = f"- **Model Type**: `{args.model_type}`\n" if has_model else ""
        model_folder_line = "- `model/` — `inputs.json` and `summary.json` for `financial-modeler`\n" if has_model else ""
        readme_path.write_text(
            f"# {args.title}\n\n"
            f"- **PRD Tier**: `{args.track}`\n"
            f"- **Created**: {args.date}\n"
            f"- **Currency**: {args.currency}\n"
            f"- **Jurisdiction**: {args.jurisdiction}\n"
            f"{model_line}"
            f"- **Confidentiality**: Local-only (never push `{base_folder}/` to `origin` without explicit approval)\n\n"
            f"## Documents ({args.track} PRD)\n\n"
            f"{checklist}\n\n"
            "## Folders\n"
            "- `decisions/` — Architecture & strategic Decision Records (`ADR-NNN-<slug>.md`)\n"
            f"{model_folder_line}"
            "- `assets/` — Interactive flows, SVG charts, and exported PDFs/HTML\n",
            encoding="utf-8",
        )

    # CHANGELOG.md
    changelog_path = proj_dir / "CHANGELOG.md"
    if not changelog_path.exists() or args.force:
        tpl = templates_dir / "changelog.md"
        if tpl.exists():
            text = tpl.read_text(encoding="utf-8").replace("<Project>", args.title).replace("YYYY-MM-DD", args.date).replace("vX.Y", "v0.1")
        else:
            text = f"# Changelog - {args.title}\n\n## v0.1 - {args.date}\n- Initialized Modular PRD ({args.track}).\n"
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

    # PRD.md (core document for EVERY project track)
    prd_path = proj_dir / "PRD.md"
    if not prd_path.exists() or args.force:
        tpl = templates_dir / "prd.md"
        if tpl.exists():
            text = tpl.read_text(encoding="utf-8").replace("<Project>", args.title).replace("YYYY-MM-DD", args.date)
        else:
            text = f"# Product Requirements Document (PRD) - {args.title}\n\nDate: {args.date}\n"
        prd_path.write_text(text, encoding="utf-8")

    # model/inputs.json for business/full tracks
    if has_model:
        _copy_model_inputs(root, proj_dir, args.model_type, force=args.force)

    update_index(root / base_folder / "INDEX.md", args.title, f"{base_folder}/{folder_name}", args.track, args.date)
    print(f"Initialized PRD ({args.track}): {proj_dir}")


if __name__ == "__main__":
    main()
