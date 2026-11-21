#!/usr/bin/env python3
"""Mirror or install .agents/skills/ for other AI coding tools (Claude Code, Codex, Gemini CLI, Antigravity).

Usage:
  python3 scripts/install_skills.py --target claude [--scope project|global] [--mode copy|symlink]
  python3 scripts/install_skills.py --target all --scope project
"""
import argparse
import os
import shutil
from pathlib import Path

TARGET_PATHS = {
    "claude": {"project": ".claude/skills", "global": "~/.claude/skills"},
    "codex": {"project": ".codex/skills", "global": "~/.codex/skills"},
    "gemini": {"project": ".gemini/skills", "global": "~/.gemini/skills"},
    "antigravity": {"project": ".agents/skills", "global": "~/.gemini/config/skills"},
}


def install_to_target(src_skills: Path, dest_dir: Path, mode: str) -> int:
    dest_dir.mkdir(parents=True, exist_ok=True)
    count = 0
    for skill_dir in sorted(p for p in src_skills.iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
        dest_skill = dest_dir / skill_dir.name
        if dest_skill.is_symlink() or dest_skill.is_file():
            dest_skill.unlink()
        elif dest_skill.is_dir():
            shutil.rmtree(dest_skill)

        if mode == "symlink":
            os.symlink(skill_dir.resolve(), dest_skill)
        else:
            shutil.copytree(skill_dir, dest_skill)
        count += 1
    return count


def main():
    ap = argparse.ArgumentParser(description="Install .agents/skills/ for Claude Code, Codex, Gemini CLI, or Antigravity.")
    ap.add_argument("--target", choices=["claude", "codex", "gemini", "antigravity", "all"], required=True, help="Target AI tool")
    ap.add_argument("--scope", choices=["project", "global"], default="project", help="Install into current repo or user home")
    ap.add_argument("--mode", choices=["copy", "symlink"], default="copy", help="Copy files (portable) or symlink")
    ap.add_argument("--base-dir", default=".", help="Workspace root directory")
    args = ap.parse_args()

    root = Path(args.base_dir).resolve()
    src_skills = root / ".agents" / "skills"
    if not src_skills.is_dir():
        raise FileNotFoundError(f"Source skills directory not found: {src_skills}")

    targets = ["claude", "codex", "gemini", "antigravity"] if args.target == "all" else [args.target]
    for t in targets:
        raw_dest = TARGET_PATHS[t][args.scope]
        dest_dir = Path(raw_dest).expanduser() if raw_dest.startswith("~") else (root / raw_dest)
        if dest_dir.resolve() == src_skills.resolve():
            print(f"[SKIP] {t} ({args.scope}): already at {dest_dir}")
            continue
        n = install_to_target(src_skills, dest_dir, args.mode)
        print(f"[OK] Installed {n} skills for {t} ({args.scope}, {args.mode}) -> {dest_dir}")


if __name__ == "__main__":
    main()
