# BrainstormingAgent Instructions (Claude Code)

Follow all guidelines, engagement tracks, skill routing, quality gates, and Git privacy rules in [AGENTS.md](AGENTS.md).

- **Skills directory**: `.agents/skills/*/SKILL.md` (run `python3 scripts/install_skills.py --target claude` if you also want them mirrored into `.claude/skills/`).
- **Templates**: `templates/`
- **Deterministic scripts**: `scripts/init_project.py`, `scripts/lint_project.py`, `.agents/skills/financial-modeler/scripts/model.py`, `.agents/skills/executive-reporter/scripts/export_pdf.py`.
- **Web research**: Use your available web search / fetch tools (`WebSearch`, `WebFetch`, MCP browser, etc.) when running `market-researcher`, `competitor-analyst`, or `compliance-checker`.
