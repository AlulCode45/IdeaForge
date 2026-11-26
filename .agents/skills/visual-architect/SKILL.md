---
name: visual-architect
description: >-
  Create validated, interactive architecture, workflow, sequence, dataflow,
  lifecycle, ERD, tree, class, timeline, and waterfall diagrams as standalone
  Institutional Editorial HTML and dual-theme SVG. Includes Live/Still motion
  flow, Semantic Radar minimap, URL deep-links, Presentation mode, Share Cards
  (1200x630), Story walkthrough + WebM recording, Mermaid transpilation,
  PR/snapshot visual diffing (added/modified/removed), one-page visual
  explainers (.explainer.md DSL in 4 presets), and multi-language repository
  architecture diagnosis with Atlas Star Map and AI fix prompts.
---

# Visual Architect

Turn system ideas, PRPs/PRDs, Mermaid blocks, Git PR diffs, or real repositories into validated, explorable **Institutional Editorial** visuals (`pure Python 3 stdlib`, zero Node/npm dependencies).

## Capabilities (Full Feature Parity & Extensions)

1. **10 Native Interactive Diagram Types**: `architecture`, `workflow`, `sequence`, `dataflow`, `lifecycle`, `erd`, `tree`, `class`, `timeline`, `waterfall` — including inline change-marking (`change: "added" | "modified" | "removed" | "unchanged"`, `emphasis: true`, `previousType`).
2. **Full Interactive Viewer Runtime**:
   - Pan/Zoom, Fit (`0`), Reset, Search (`/`), Keyboard Shortcuts Guide (`?`), Presentation Mode (`P`), Light/Dark toggle.
   - **Live/Still Motion Flow (`L`)**: Animated comet pulses cascading along edges (respects `prefers-reduced-motion`).
   - **Semantic Radar**: Live viewport minimap with click-to-pan navigation.
   - **Semantic Passport**: Click any node **or edge** to inspect metadata, evidence tags, source file links, **before/after payload diffs**, **Upstream/Downstream reach**, and **Copy Deep Link** (`#focus=...`, `#route=a~b`, `#lens=...`, `#theme=dark`, `#present=1`).
   - **BFS Route Tracer**: Trace directed shortest paths between any two nodes.
   - **Story Walkthrough & Browser Video**: Play/Pause/Prev/Next captions + **Record Story (WebM)**.
   - **Canonical & Social Exports**: Dual-Theme SVG (`prefers-color-scheme`), 2x HiDPI PNG, and **1200×630 Route / Reach Share Cards**.
3. **Strict Quality Gates (`validate`)**: Schema, referential integrity, duplicate IDs, cycle detection, orphan checks, and label length validation.
4. **PR Visual Walkthrough & Snapshot Diff (`pr-diff` & `compare`)**:
   - `compare`: Diffs two JSON snapshots (`Before | Delta | After`) into a change-marked merged-superset diagram.
   - `pr-diff`: Runs `git diff --name-status` on a local repo, overlays `added`/`modified`/`removed` onto the architecture diagram, and emits a GitHub/GitLab Markdown pack + dual-theme SVG.
5. **Repository Architecture Diagnosis (`analyze-repo`)**: Scans Python, JS/TS, Go, Rust, Java, and C/C++ repositories for circular dependencies (Tarjan SCC), coupling ($C_a$, $C_e$, Instability $I$), complexity hotspots, **Atlas Dependency Star Map SVG**, and one-click copyable **AI Fix Prompts**.
6. **One-Page Visual Explainer (`explainer`)**: Supports both `.explainer.md` compact Markdown DSL (`@architecture`, `@workflow`, `@sequence`, `@erd`, `@steps`, `@callout`, `@facts`, `@metric`, `@source`, `{good/caution/bad}` table badges, interactive `- [ ]` checklists) and JSON across **4 presets** (`institutional`, `briefing`, `technical`, `minimal`).
7. **Mermaid Transpiler (`from-mermaid`)**: Converts Mermaid `flowchart`, `sequenceDiagram`, `stateDiagram`, and `erDiagram` into structured `.diagram.json` IR.

## CLI Workflow

```bash
# 1. Validate & Render interactive HTML + dual-theme SVG
python3 .agents/skills/visual-architect/scripts/diagram_studio.py validate <project>/assets/system.diagram.json --json
python3 .agents/skills/visual-architect/scripts/diagram_studio.py render <project>/assets/system.diagram.json \
  --output <project>/assets/system.diagram.html --svg-out <project>/assets/system.diagram.svg --lang id

# 2. Convert Mermaid -> JSON IR
python3 .agents/skills/visual-architect/scripts/diagram_studio.py from-mermaid flow.mmd \
  --output <project>/assets/flow.diagram.json --title "Checkout Flow"

# 3. Compare two snapshots (Before | Delta | After) or visualize a Git PR diff
python3 .agents/skills/visual-architect/scripts/diagram_studio.py compare base.json head.json \
  --output delta.html --json-out delta.json
python3 .agents/skills/visual-architect/scripts/diagram_studio.py pr-diff /path/to/repo \
  --base HEAD~1 --head HEAD --out-dir <project>/assets/pr-pack

# 4. Diagnose local repository architecture + Atlas Star Map + Fix Prompts
python3 .agents/skills/visual-architect/scripts/diagram_studio.py analyze-repo /path/to/repo \
  --output <project>/assets/repo-arch.json --html-out <project>/assets/repo-diagnosis.html --lang id

# 5. Render One-Page Visual Explainer (.explainer.md DSL or .json)
python3 .agents/skills/visual-architect/scripts/diagram_studio.py explainer answer.explainer.md \
  --output <project>/assets/answer.html --preset institutional --lang id
```
