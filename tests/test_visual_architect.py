import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/visual-architect/scripts"))
import diagram_studio as ds


class TestVisualArchitect(unittest.TestCase):
    def test_validate_catches_dangling_edge_and_tree_cycle(self):
        bad = {
            "type": "tree",
            "title": "Bad Tree",
            "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
            "edges": [{"from": "a", "to": "b"}, {"from": "b", "to": "a"}, {"from": "a", "to": "missing"}],
        }
        res = ds.validate_diagram(bad)
        self.assertFalse(res["ok"])
        codes = {e["code"] for e in res["errors"]}
        self.assertIn("ref/dangling", codes)
        self.assertIn("graph/cycle", codes)

    def test_all_10_diagram_types_and_viewer_runtime_features(self):
        samples = [
            {
                "type": "architecture",
                "title": "Arch",
                "nodes": [
                    {"id": "web", "label": "Web", "group": "Edge", "evidence": "verified", "change": "added"},
                    {"id": "api", "label": "API", "group": "Core", "emphasis": True},
                ],
                "edges": [{"from": "web", "to": "api", "label": "HTTPS", "payload": {"before": {"v": 1}, "after": {"v": 2}}}],
                "steps": [{"title": "Step 1", "caption": "Client hits API", "focusNodes": ["web", "api"]}],
            },
            {"type": "workflow", "title": "Flow", "nodes": [{"id": "s", "label": "Start", "kind": "start"}, {"id": "d", "label": "Approve?", "kind": "decision"}], "edges": [{"from": "s", "to": "d", "label": "submit"}]},
            {"type": "sequence", "title": "Seq", "participants": [{"id": "u", "label": "User"}, {"id": "s", "label": "Server"}], "messages": [{"from": "u", "to": "s", "label": "POST /pay", "kind": "sync"}, {"from": "s", "to": "u", "label": "200 OK", "kind": "return"}]},
            {"type": "dataflow", "title": "ETL", "nodes": [{"id": "src", "label": "POS"}, {"id": "dw", "label": "Warehouse"}], "edges": [{"from": "src", "to": "dw", "label": "events"}]},
            {"type": "lifecycle", "title": "Order", "nodes": [{"id": "new", "label": "New", "kind": "start"}, {"id": "paid", "label": "Paid", "status": "ok"}], "edges": [{"from": "new", "to": "paid", "label": "pay"}]},
            {"type": "erd", "title": "Schema", "entities": [{"id": "orders", "label": "orders", "attributes": [{"name": "id", "type": "uuid", "key": ["pk"], "previousType": "int"}]}, {"id": "items", "label": "order_items", "attributes": [{"name": "order_id", "type": "uuid", "key": ["fk"]}]}], "relationships": [{"from": "orders", "to": "items", "cardinality": "1:N", "label": "contains"}]},
            {"type": "tree", "title": "Org", "nodes": [{"id": "root", "label": "CEO"}, {"id": "eng", "label": "Engineering"}, {"id": "ops", "label": "Ops"}], "edges": [{"from": "root", "to": "eng"}, {"from": "root", "to": "ops"}]},
            {"type": "class", "title": "Domain", "classes": [{"id": "Cart", "label": "Cart", "attributes": ["+items: List"], "methods": ["+total(): Money"]}], "relationships": []},
            {"type": "timeline", "title": "Rollout", "events": [{"id": "m1", "label": "Pilot", "date": "2026-01", "status": "ok"}, {"id": "m2", "label": "GA", "date": "2026-03"}]},
            {"type": "waterfall", "title": "Trace", "unit": "ms", "spans": [{"id": "s1", "label": "Auth", "start": 0, "duration": 25, "status": "ok"}, {"id": "s2", "label": "DB Query", "start": 25, "duration": 60, "status": "warn"}]},
        ]
        for spec in samples:
            val = ds.validate_diagram(spec)
            self.assertTrue(val["ok"], f"{spec['type']} failed validation: {val}")
            svg, w, h, _ = ds.render_svg(spec, dual_theme_style=True)
            self.assertIn("<svg", svg)
            self.assertIn("prefers-color-scheme: dark", svg)
            self.assertGreater(w, 0)
            self.assertGreater(h, 0)
            html_doc = ds.render_html(spec, lang="id")
            self.assertIn("Paspor Semantik", html_doc)
            self.assertIn("radar-box", html_doc)
            self.assertIn("btn-live", html_doc)
            self.assertIn("btn-share-card", html_doc)
            self.assertIn("btn-present", html_doc)
            self.assertIn("guide-modal", html_doc)

    def test_from_mermaid_flowchart_and_sequence(self):
        flow_mmd = "flowchart LR\n  A[Kasir] -->|checkout| B{Online?}\n  B -->|Ya| C[Sync Cloud]"
        spec = ds.parse_mermaid(flow_mmd, title="Kasir Flow")
        self.assertEqual(spec["type"], "workflow")
        self.assertEqual(len(spec["nodes"]), 3)
        self.assertEqual(len(spec["edges"]), 2)

        seq_mmd = "sequenceDiagram\n  Client->>API: Login\n  API-->>Client: JWT"
        seq = ds.parse_mermaid(seq_mmd, title="Auth")
        self.assertEqual(seq["type"], "sequence")
        self.assertEqual(len(seq["participants"]), 2)
        self.assertEqual(seq["messages"][1]["kind"], "return")

    def test_compare_and_pr_diff_change_marking(self):
        base = {
            "type": "architecture",
            "title": "System",
            "nodes": [{"id": "web", "label": "Web"}, {"id": "legacy", "label": "Legacy"}],
            "edges": [{"from": "web", "to": "legacy", "label": "RPC"}],
        }
        head = {
            "type": "architecture",
            "title": "System",
            "nodes": [{"id": "web", "label": "Web App"}, {"id": "api", "label": "API"}],
            "edges": [{"from": "web", "to": "api", "label": "REST"}],
        }
        report, superset = ds.compare_diagrams(base, head)
        self.assertEqual(report["delta"]["added_nodes"], ["api"])
        self.assertEqual(report["delta"]["removed_nodes"], ["legacy"])
        self.assertEqual(report["delta"]["modified_nodes"], ["web"])
        html_doc = ds.render_html(superset, lang="en")
        self.assertIn("Change Legend", html_doc)
        self.assertIn("chg-added", html_doc)
        self.assertIn("chg-removed", html_doc)

        pr_spec, pr_md = ds.build_pr_diff_pack(ROOT, base_ref="HEAD~1", head_ref="HEAD")
        self.assertIn("Architecture Change Walkthrough", pr_md)
        self.assertEqual(pr_spec["type"], "architecture")

    def test_analyze_repository_atlas_and_explainer_markdown_dsl(self):
        spec = ds.analyze_repository(ROOT / "scripts")
        self.assertEqual(spec["type"], "architecture")
        self.assertGreaterEqual(len(spec["nodes"]), 2)
        self.assertTrue(spec["findings"][0].get("fix_task"))
        exp_html = ds.render_explainer_html(spec, lang="en")
        self.assertIn("Atlas Dependency Star Map", exp_html)
        self.assertIn("Copy Fix Task", exp_html)

        md_dsl = """# Why Offline-First POS Wins {#pos-offline}

Local SQLite queue guarantees **zero checkout downtime** during Wi-Fi drops.

- Transactions commit locally in < 20ms.
- Background worker syncs idempotently when online.

@source spec title="POS Offline Spec" url=https://example.test/spec

## Checkout Flow {#flow}

@sequence id=pos-seq title="Offline Checkout"
| actor kasir | Kasir | frontend |
| actor sqlite | SQLite | database |
| kasir | sqlite | Save Order |
| sqlite | kasir | Receipt Ready | return |

@steps id=pos-steps
| s1 | Save Order | Persists order locally first. | pos-seq | kasir |
| s2 | Receipt Ready | Prints thermal receipt immediately. | pos-seq | sqlite |

## Comparison {#cmp}

| Metric | Cloud-Only | Offline-First |
| --- | --- | --- |
| Checkout when offline | Blocked {bad:Downtime} | Instant {good:Zero Downtime} |

- [ ] Verify idempotency key on sync
"""
        parsed = ds.parse_explainer_markdown(md_dsl)
        md_html = ds.render_explainer_html(parsed, lang="en", preset="briefing")
        self.assertIn("Why Offline-First POS Wins", md_html)
        self.assertIn("b-good", md_html)
        self.assertIn("b-bad", md_html)
        self.assertIn("type=\"checkbox\"", md_html)
        self.assertIn("<svg", md_html)


if __name__ == "__main__":
    unittest.main()
