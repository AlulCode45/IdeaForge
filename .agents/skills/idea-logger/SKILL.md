---
name: idea-logger
description: >-
  Use this skill when the user wants to save, document, archive, or summarize a
  brainstorming session, decision, or idea into a structured Markdown file in
  the `ideas/` directory.
---

# Idea Logger

Persist brainstorming outcomes as clean, searchable Markdown files in `ideas/`.

## Workflow

1. **Determine Filename**:
   - Never save loose files directly in `ideas/`. Group every note in a topic folder: `ideas/<topic-slug>/YYYY-MM-DD-<note>.md` (or scaffold via `python3 scripts/init_project.py --slug <topic-slug> --title "<Title>" --track quick`).
   - Reuse the existing topic folder if one exists; put images in `ideas/<topic-slug>/assets/`.
2. **Use Structured Template**:
   - Include metadata (`Date`, `Track: Quick Brief`, `Category`, `Status`, `Confidentiality`), `Context & Goal`, `Key Options Explored`, `Risks, Open Questions & Pass/Kill Criteria`, and `Decision & Next Steps`.
3. **Privacy & Git Rule**:
   - Save locally in `ideas/`. **Never** push `ideas/` to `origin` unless the user explicitly asks to push project/idea notes.
