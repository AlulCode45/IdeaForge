"""Institutional Editorial Viewer Runtime (CSS + JS + HTML shell) for Visual Architect.

Features:
- Pan & Zoom, Fit, Reset, Search (/), Keyboard Shortcuts Guide (?)
- Semantic Passport (Node & Edge inspection, before/after payload diff, Copy Deep Link)
- Upstream/Downstream Reachability & BFS Route Tracer
- Live/Still animated comet flow overlay (respects prefers-reduced-motion)
- Semantic Radar (live viewport minimap)
- Presentation Mode (P) & URL Hash Deep-Links (#focus, #route, #lens, #theme, #present)
- Story Walkthrough Playback + Browser WebM Story Video Recording
- Exports: Dual-Theme SVG, 2x PNG, Route Share Card (1200x630), Reach Share Card (1200x630)
"""

from __future__ import annotations

import html
import json
from typing import Any

STUDIO_CSS = """
:root {
  --bg: #F6F4EF;
  --surface: #FFFFFF;
  --surface-2: #F0EDE6;
  --line: #DDD8CE;
  --text: #1B1F24;
  --text-muted: #5B6470;
  --primary: #12263F;
  --accent: #B5541C;
  --go: #1E6B4A; --go-bg: #E3F0E9;
  --conditional: #8A5A00; --conditional-bg: #F6EBD3;
  --nogo: #9B2C2C; --nogo-bg: #F6E0E0;
  --font-serif: "Source Serif 4", Georgia, "Times New Roman", serif;
  --font-sans: "Inter", system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-mono: ui-monospace, "JetBrains Mono", Menlo, monospace;
}
[data-theme="dark"] {
  --bg: #0E141B;
  --surface: #151D27;
  --surface-2: #1B2531;
  --line: #263241;
  --text: #E7EAEE;
  --text-muted: #9AA5B1;
  --primary: #8FB3E0;
  --accent: #E08A4F;
  --go: #74D4A7; --go-bg: #132A22;
  --conditional: #F2B84B; --conditional-bg: #2A2010;
  --nogo: #F08A8A; --nogo-bg: #2D171A;
}
*, *::before, *::after { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
}
.studio-shell { display: grid; grid-template-rows: auto 1fr; height: 100vh; }
.studio-shell.is-present { grid-template-rows: 1fr; }
.studio-shell.is-present .studio-bar,
.studio-shell.is-present .inspector { display: none; }
.studio-shell.is-present .studio-body { grid-template-columns: 1fr; }
.present-exit {
  display: none !important; position: fixed; top: 14px; right: 16px; z-index: 40;
}
.studio-shell.is-present .present-exit { display: inline-flex !important; }

.studio-bar {
  display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap;
  gap: 8px 12px; padding: 8px 18px; min-height: 52px;
  background: var(--surface); border-bottom: 1px solid var(--line);
}
.studio-brand { display: flex; align-items: baseline; gap: 10px; min-width: 0; }
.studio-title {
  font-family: var(--font-serif); font-size: 17px; font-weight: 600;
  color: var(--primary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.studio-meta { font-family: var(--font-mono); font-size: 11px; color: var(--text-muted); white-space: nowrap; }
.studio-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.btn {
  height: 30px; padding: 0 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--surface); color: var(--text); font-family: inherit;
  font-size: 12px; font-weight: 500; cursor: pointer; display: inline-flex; align-items: center; gap: 5px;
  white-space: nowrap;
}
.btn:hover { background: var(--surface-2); }
.btn.active { border-color: var(--accent); color: var(--accent); font-weight: 600; }
.search-in {
  height: 30px; width: 185px; padding: 0 10px; border: 1px solid var(--line);
  border-radius: 6px; background: var(--bg); color: var(--text); font-family: inherit; font-size: 12px;
}
.export-wrap { position: relative; }
.export-menu {
  display: none; position: absolute; right: 0; top: 36px; z-index: 50;
  min-width: 210px; padding: 6px; background: var(--surface);
  border: 1px solid var(--line); border-radius: 8px; box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.export-menu.open { display: grid; gap: 4px; }
.export-menu .btn { width: 100%; justify-content: flex-start; border-color: transparent; }
.export-menu .btn:hover { background: var(--surface-2); }

.studio-body { display: grid; grid-template-columns: minmax(0, 1fr) 320px; min-height: 0; }
.canvas-wrap { position: relative; overflow: hidden; background: var(--bg); cursor: grab; }
.canvas-wrap:active { cursor: grabbing; }
.canvas-wrap svg { width: 100%; height: 100%; display: block; }

.filter-strip {
  position: absolute; top: 12px; left: 16px; display: flex; gap: 6px; flex-wrap: wrap; z-index: 10;
}
.change-legend {
  position: absolute; top: 12px; right: 16px; display: flex; gap: 8px; align-items: center;
  padding: 5px 10px; background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  font-size: 11px; font-family: var(--font-mono); z-index: 10;
}
.chg-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 4px; }
.chg-added { background: var(--go); }
.chg-modified { background: var(--conditional); }
.chg-removed { background: var(--nogo); }

.radar-box {
  position: absolute; right: 14px; bottom: 14px; width: 168px; height: 112px;
  background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  overflow: hidden; z-index: 12; opacity: 0.92; cursor: pointer;
}
.radar-box svg { width: 100%; height: 100%; pointer-events: none; }
.radar-vp {
  position: absolute; border: 1.5px solid var(--accent); background: rgba(181, 84, 28, 0.08);
  pointer-events: none;
}

.story-bar {
  position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%);
  background: var(--surface); border: 1px solid var(--line); border-radius: 8px;
  padding: 9px 14px; display: flex; align-items: center; gap: 10px; max-width: 720px; z-index: 15;
}
.inspector {
  border-left: 1px solid var(--line); background: var(--surface); padding: 18px; overflow-y: auto;
}
.ins-kicker {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin-bottom: 4px;
}
.ins-title {
  font-family: var(--font-serif); font-size: 19px; font-weight: 600; color: var(--primary); margin: 0 0 10px;
}
.ins-row {
  display: flex; justify-content: space-between; gap: 8px; padding: 6px 0;
  border-bottom: 1px solid var(--line); font-size: 12.5px;
}
.ins-row span:first-child { color: var(--text-muted); }
.ins-chip {
  display: inline-block; margin: 3px 4px 0 0; padding: 2px 8px; border: 1px solid var(--line);
  border-radius: 4px; font-size: 12px; cursor: pointer; background: var(--surface-2);
}
.ins-chip:hover { border-color: var(--accent); }
.diff-box {
  margin-top: 10px; padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px;
  background: var(--bg); font-family: var(--font-mono); font-size: 11px; white-space: pre-wrap; overflow-x: auto;
}
.diff-del { color: var(--nogo); }
.diff-add { color: var(--go); }

.guide-modal {
  display: none; position: fixed; inset: 0; background: rgba(14,20,27,0.5); z-index: 60;
  align-items: center; justify-content: center;
}
.guide-modal.open { display: flex; }
.guide-card {
  width: 440px; max-width: 92vw; background: var(--surface); border: 1px solid var(--line);
  border-radius: 10px; padding: 20px 22px;
}
.guide-card h3 { font-family: var(--font-serif); margin: 0 0 12px; color: var(--primary); }
.kbd-row { display: flex; justify-content: space-between; padding: 5px 0; border-bottom: 1px solid var(--line); font-size: 13px; }
kbd {
  font-family: var(--font-mono); font-size: 11px; padding: 1px 6px;
  border: 1px solid var(--line); border-radius: 4px; background: var(--surface-2);
}

/* SVG Semantic & Change-Mark Styles */
.zone-box { fill: var(--surface-2); stroke: var(--line); stroke-width: 1.2; stroke-dasharray: 5 4; opacity: 0.85; }
.zone-title { font-family: var(--font-mono); font-size: 11px; fill: var(--text-muted); font-weight: 600; letter-spacing: 0.05em; }
.node-box { fill: var(--surface); stroke: var(--line); stroke-width: 1.2; transition: stroke 140ms ease, opacity 140ms ease; }
.node-accent { fill: var(--primary); }
.dg-node.status-ok .node-accent { fill: var(--go); }
.dg-node.status-conditional .node-accent { fill: var(--conditional); }
.dg-node.status-warn .node-accent, .dg-node.status-critical .node-accent { fill: var(--nogo); }
.dg-node.chg-added .node-box { stroke: var(--go); stroke-width: 2; fill: var(--go-bg); }
.dg-node.chg-added .node-accent { fill: var(--go); }
.dg-node.chg-modified .node-box { stroke: var(--conditional); stroke-width: 2; fill: var(--conditional-bg); }
.dg-node.chg-modified .node-accent { fill: var(--conditional); }
.dg-node.chg-removed .node-box { stroke: var(--nogo); stroke-width: 1.6; stroke-dasharray: 4 3; fill: var(--nogo-bg); opacity: 0.72; }
.dg-node.chg-removed .node-accent { fill: var(--nogo); }
.dg-node.is-emphasis .node-box { stroke: var(--accent); stroke-width: 2.4; }
.dg-node { cursor: pointer; }
.dg-node:hover .node-box, .dg-node.is-selected .node-box { stroke: var(--accent); stroke-width: 2.2; }
.dg-node.is-dimmed, .dg-edge.is-dimmed { opacity: 0.16; }
.dg-edge { cursor: pointer; }
.dg-edge.is-highlighted .edge-line { stroke: var(--accent); stroke-width: 2.4; }
.dg-edge.chg-added .edge-line { stroke: var(--go); stroke-width: 2; }
.dg-edge.chg-modified .edge-line { stroke: var(--conditional); stroke-width: 2; }
.dg-edge.chg-removed .edge-line { stroke: var(--nogo); stroke-dasharray: 3 3; opacity: 0.7; }
.node-title { font-family: var(--font-sans); font-size: 13px; font-weight: 600; fill: var(--text); }
.node-sub { font-family: var(--font-mono); font-size: 11px; fill: var(--text-muted); }
.node-mono { font-family: var(--font-mono); font-size: 11px; fill: var(--text); }
.node-sep { stroke: var(--line); stroke-width: 1; }
.edge-line { fill: none; stroke: var(--text-muted); stroke-width: 1.4; }
.dg-edge-dashed .edge-line { stroke-dasharray: 5 4; }
.arrow-fill { fill: var(--text-muted); }
.edge-pill { fill: var(--bg); stroke: var(--line); stroke-width: 1; }
.edge-lbl { font-family: var(--font-mono); font-size: 11px; fill: var(--text-muted); }
.seq-lifeline { stroke: var(--line); stroke-width: 1.2; stroke-dasharray: 4 4; }
.erd-head { fill: var(--primary); }
.erd-title { font-family: var(--font-sans); font-size: 13px; font-weight: 600; fill: #FFFFFF; }
[data-theme="dark"] .erd-title { fill: #0E141B; }
.wf-bar { fill: var(--primary); opacity: 0.88; }
.dg-node.status-warn .wf-bar { fill: var(--nogo); }
.dg-node.status-ok .wf-bar { fill: var(--go); }
.ev-dot.ev-verified { fill: var(--go); }
.ev-dot.ev-estimate { fill: var(--primary); }
.ev-dot.ev-assumption { fill: var(--conditional); }
.ev-dot.ev-unverified { fill: var(--nogo); }
.chg-badge { font-family: var(--font-mono); font-size: 10px; font-weight: 700; }
.comet-dot { fill: var(--accent); opacity: 0.9; pointer-events: none; }
.comet-halo { fill: var(--accent); opacity: 0.25; pointer-events: none; }
@media (max-width: 960px) {
  .studio-body { grid-template-columns: 1fr; grid-template-rows: 1fr 240px; }
  .inspector { border-left: 0; border-top: 1px solid var(--line); }
  .radar-box { display: none; }
}
@media print {
  .studio-bar, .inspector, .filter-strip, .radar-box, .story-bar, .present-exit { display: none !important; }
  .studio-shell, .studio-body { display: block; height: auto; }
}
"""

DUAL_THEME_SVG_CSS = """
:root { --bg:#F6F4EF;--surface:#FFFFFF;--surface-2:#F0EDE6;--line:#DDD8CE;--text:#1B1F24;--text-muted:#5B6470;--primary:#12263F;--accent:#B5541C;--go:#1E6B4A;--go-bg:#E3F0E9;--conditional:#8A5A00;--conditional-bg:#F6EBD3;--nogo:#9B2C2C;--nogo-bg:#F6E0E0;--font-sans:system-ui,sans-serif;--font-mono:ui-monospace,monospace; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#0E141B;--surface:#151D27;--surface-2:#1B2531;--line:#263241;--text:#E7EAEE;--text-muted:#9AA5B1;--primary:#8FB3E0;--accent:#E08A4F;--go:#74D4A7;--go-bg:#132A22;--conditional:#F2B84B;--conditional-bg:#2A2010;--nogo:#F08A8A;--nogo-bg:#2D171A; }
}
.zone-box{fill:var(--surface-2);stroke:var(--line);stroke-width:1.2;stroke-dasharray:5 4}
.zone-title{font-family:var(--font-mono);font-size:11px;fill:var(--text-muted);font-weight:600}
.node-box{fill:var(--surface);stroke:var(--line);stroke-width:1.2}
.node-accent{fill:var(--primary)}
.dg-node.status-ok .node-accent,.dg-node.chg-added .node-accent{fill:var(--go)}
.dg-node.status-conditional .node-accent,.dg-node.chg-modified .node-accent{fill:var(--conditional)}
.dg-node.status-warn .node-accent,.dg-node.chg-removed .node-accent{fill:var(--nogo)}
.dg-node.chg-added .node-box{stroke:var(--go);stroke-width:2;fill:var(--go-bg)}
.dg-node.chg-modified .node-box{stroke:var(--conditional);stroke-width:2;fill:var(--conditional-bg)}
.dg-node.chg-removed .node-box{stroke:var(--nogo);stroke-dasharray:4 3;fill:var(--nogo-bg);opacity:.72}
.node-title{font-family:var(--font-sans);font-size:13px;font-weight:600;fill:var(--text)}
.node-sub,.edge-lbl{font-family:var(--font-mono);font-size:11px;fill:var(--text-muted)}
.node-mono{font-family:var(--font-mono);font-size:11px;fill:var(--text)}
.edge-line{fill:none;stroke:var(--text-muted);stroke-width:1.4}
.dg-edge-dashed .edge-line{stroke-dasharray:5 4}
.arrow-fill{fill:var(--text-muted)}
.edge-pill{fill:var(--bg);stroke:var(--line);stroke-width:1}
.seq-lifeline{stroke:var(--line);stroke-dasharray:4 4}
.erd-head{fill:var(--primary)}
.erd-title{font-family:var(--font-sans);font-size:13px;font-weight:600;fill:#fff}
.wf-bar{fill:var(--primary);opacity:.88}
"""

STUDIO_JS = """
(function() {
  const DATA = window.__DIAG_DATA__ || {};
  const T = window.__DIAG_I18N__ || {};
  const shell = document.getElementById('studio-shell');
  const svg = document.getElementById('dg-svg');
  const vp = document.getElementById('dg-viewport');
  const wrap = document.getElementById('canvas-wrap');
  const insBody = document.getElementById('inspector-body');
  const searchIn = document.getElementById('dg-search');
  const radarBox = document.getElementById('radar-box');
  const radarVp = document.getElementById('radar-vp');
  if (!svg || !vp) return;

  // State
  let scale = 1, tx = 0, ty = 0, dragging = false, sx = 0, sy = 0;
  let activeFocus = null, activeRoute = null, activeLens = '__all__', liveMotion = false;
  let motionRaf = null;

  const origW = svg.viewBox.baseVal.width || Number(svg.getAttribute('width')) || 960;
  const origH = svg.viewBox.baseVal.height || Number(svg.getAttribute('height')) || 540;

  function updateRadar() {
    if (!radarBox || !radarVp) return;
    const r = wrap.getBoundingClientRect();
    const rb = radarBox.getBoundingClientRect();
    if (!origW || !r.width || !rb.width) return;
    const rx = rb.width / origW, ry = rb.height / origH;
    const vx = (-tx / scale) * rx, vy = (-ty / scale) * ry;
    const vw = (r.width / scale) * rx, vh = (r.height / scale) * ry;
    radarVp.style.left = Math.max(0, Math.min(rb.width - 10, vx)) + 'px';
    radarVp.style.top = Math.max(0, Math.min(rb.height - 10, vy)) + 'px';
    radarVp.style.width = Math.min(rb.width, Math.max(12, vw)) + 'px';
    radarVp.style.height = Math.min(rb.height, Math.max(12, vh)) + 'px';
  }

  function applyTransform() {
    vp.setAttribute('transform', `translate(${tx.toFixed(1)}, ${ty.toFixed(1)}) scale(${scale.toFixed(3)})`);
    updateRadar();
  }

  function fitCanvas() {
    const rect = wrap.getBoundingClientRect();
    if (!origW || !rect.width) return;
    svg.setAttribute('viewBox', `0 0 ${rect.width} ${rect.height}`);
    scale = Math.min(1.05, Math.min(rect.width / origW, (rect.height - 70) / origH) * 0.88);
    tx = (rect.width - origW * scale) / 2;
    ty = (rect.height - 40 - origH * scale) / 2;
    applyTransform();
  }

  // Clone SVG into radar minimap
  if (radarBox) {
    const mini = svg.cloneNode(true);
    mini.removeAttribute('id');
    mini.setAttribute('viewBox', `0 0 ${origW} ${origH}`);
    mini.querySelectorAll('[id]').forEach(el => el.removeAttribute('id'));
    radarBox.insertBefore(mini, radarVp);
    radarBox.addEventListener('click', e => {
      const rb = radarBox.getBoundingClientRect();
      const r = wrap.getBoundingClientRect();
      const cx = ((e.clientX - rb.left) / rb.width) * origW;
      const cy = ((e.clientY - rb.top) / rb.height) * origH;
      tx = r.width / 2 - cx * scale;
      ty = r.height / 2 - cy * scale;
      applyTransform();
    });
  }

  fitCanvas();
  window.addEventListener('resize', fitCanvas);
  wrap.addEventListener('wheel', e => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    const rect = wrap.getBoundingClientRect();
    const mx = e.clientX - rect.left, my = e.clientY - rect.top;
    tx = mx - (mx - tx) * factor;
    ty = my - (my - ty) * factor;
    scale = Math.max(0.25, Math.min(4, scale * factor));
    applyTransform();
  }, { passive: false });
  wrap.addEventListener('mousedown', e => {
    if (e.target.closest('.dg-node, .dg-edge, .radar-box, .story-bar, .filter-strip')) return;
    dragging = true; sx = e.clientX - tx; sy = e.clientY - ty;
  });
  window.addEventListener('mousemove', e => {
    if (!dragging) return;
    tx = e.clientX - sx; ty = e.clientY - sy; applyTransform();
  });
  window.addEventListener('mouseup', () => { dragging = false; });

  document.getElementById('btn-fit')?.addEventListener('click', fitCanvas);
  document.getElementById('btn-reset')?.addEventListener('click', () => { clearHighlight(); fitCanvas(); });

  // Theme toggle
  function setTheme(nxt) {
    document.documentElement.setAttribute('data-theme', nxt);
    const btn = document.getElementById('btn-theme');
    if (btn) btn.textContent = nxt === 'dark' ? T.theme_light : T.theme_dark;
  }
  document.getElementById('btn-theme')?.addEventListener('click', () => {
    setTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
  });

  // Presentation mode
  function togglePresent(force) {
    const on = typeof force === 'boolean' ? force : !shell.classList.contains('is-present');
    shell.classList.toggle('is-present', on);
    setTimeout(fitCanvas, 30);
  }
  document.getElementById('btn-present')?.addEventListener('click', () => togglePresent());
  document.getElementById('btn-exit-present')?.addEventListener('click', () => togglePresent(false));

  // Export popover
  const expBtn = document.getElementById('btn-export-pop');
  const expMenu = document.getElementById('export-menu');
  expBtn?.addEventListener('click', e => { e.stopPropagation(); expMenu?.classList.toggle('open'); });
  document.addEventListener('click', () => expMenu?.classList.remove('open'));

  // Guide modal (?)
  const guideModal = document.getElementById('guide-modal');
  document.getElementById('btn-guide')?.addEventListener('click', () => guideModal?.classList.add('open'));
  document.getElementById('btn-close-guide')?.addEventListener('click', () => guideModal?.classList.remove('open'));
  guideModal?.addEventListener('click', e => { if (e.target === guideModal) guideModal.classList.remove('open'); });

  // Graph adjacency
  const edges = Array.from(document.querySelectorAll('.dg-edge')).map(el => ({
    el, id: el.dataset.edgeId, from: el.dataset.from, to: el.dataset.to,
    pathEl: el.querySelector('path.edge-line')
  }));
  const nodes = Array.from(document.querySelectorAll('.dg-node'));
  const fwd = {}, rev = {};
  edges.forEach(e => {
    (fwd[e.from] = fwd[e.from] || []).push(e);
    (rev[e.to] = rev[e.to] || []).push(e);
  });

  // Live / Still comet motion overlay
  const motionLayer = document.createElementNS('http://www.w3.org/2000/svg', 'g');
  motionLayer.setAttribute('id', 'dg-motion-layer');
  vp.appendChild(motionLayer);
  const comets = [];
  edges.forEach((e, idx) => {
    if (!e.pathEl || typeof e.pathEl.getTotalLength !== 'function') return;
    const len = e.pathEl.getTotalLength();
    if (!len || len < 12) return;
    const halo = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    halo.setAttribute('r', '7'); halo.setAttribute('class', 'comet-halo');
    const dot = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    dot.setAttribute('r', '3.2'); dot.setAttribute('class', 'comet-dot');
    motionLayer.appendChild(halo); motionLayer.appendChild(dot);
    comets.push({ path: e.pathEl, len, halo, dot, phase: (idx * 0.19) % 1, edgeEl: e.el });
  });
  motionLayer.style.display = 'none';

  function tickMotion(ts) {
    if (!liveMotion) return;
    const t = (ts / 2600) % 1;
    comets.forEach(c => {
      const dimmed = c.edgeEl.classList.contains('is-dimmed');
      c.halo.style.display = dimmed ? 'none' : '';
      c.dot.style.display = dimmed ? 'none' : '';
      if (dimmed) return;
      const p = c.path.getPointAtLength(((t + c.phase) % 1) * c.len);
      c.halo.setAttribute('cx', p.x.toFixed(1)); c.halo.setAttribute('cy', p.y.toFixed(1));
      c.dot.setAttribute('cx', p.x.toFixed(1)); c.dot.setAttribute('cy', p.y.toFixed(1));
    });
    motionRaf = requestAnimationFrame(tickMotion);
  }
  const liveBtn = document.getElementById('btn-live');
  function setLive(on) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) on = false;
    liveMotion = !!on;
    motionLayer.style.display = liveMotion ? '' : 'none';
    liveBtn?.classList.toggle('active', liveMotion);
    if (liveBtn) liveBtn.textContent = liveMotion ? (T.motion_live || 'Live') : (T.motion_still || 'Still');
    if (liveMotion) { cancelAnimationFrame(motionRaf); motionRaf = requestAnimationFrame(tickMotion); }
    else { cancelAnimationFrame(motionRaf); }
  }
  liveBtn?.addEventListener('click', () => setLive(!liveMotion));

  function bfsReach(start, adj) {
    const seen = new Set([start]), q = [start], hitEdges = new Set();
    while (q.length) {
      const u = q.shift();
      (adj[u] || []).forEach(e => {
        hitEdges.add(e.id);
        const nxt = adj === fwd ? e.to : e.from;
        if (!seen.has(nxt)) { seen.add(nxt); q.push(nxt); }
      });
    }
    return { nodes: seen, edges: hitEdges };
  }

  function clearHighlight() {
    activeFocus = null; activeRoute = null;
    nodes.forEach(n => n.classList.remove('is-selected', 'is-dimmed'));
    edges.forEach(e => e.el.classList.remove('is-highlighted', 'is-dimmed'));
    if (insBody) insBody.innerHTML = `<p style="color:var(--text-muted)">${T.no_selection || ''}</p>`;
    try { history.replaceState(null, '', '#'); } catch(e) {}
  }

  function copyLink(hashStr, btn) {
    const url = location.href.split('#')[0] + '#' + hashStr;
    if (navigator.clipboard) navigator.clipboard.writeText(url);
    if (btn) { const o = btn.textContent; btn.textContent = T.copied || 'Copied'; setTimeout(() => btn.textContent = o, 1400); }
  }

  function selectNode(nid) {
    const meta = (DATA.nodeMeta || {})[nid];
    if (!meta) return;
    activeFocus = nid; activeRoute = null;
    const up = bfsReach(nid, rev);
    const dn = bfsReach(nid, fwd);
    const keepNodes = new Set([...up.nodes, ...dn.nodes]);
    const keepEdges = new Set([...up.edges, ...dn.edges]);
    nodes.forEach(n => {
      const id = n.dataset.nodeId;
      n.classList.toggle('is-selected', id === nid);
      n.classList.toggle('is-dimmed', !keepNodes.has(id));
    });
    edges.forEach(e => {
      e.el.classList.toggle('is-highlighted', keepEdges.has(e.id));
      e.el.classList.toggle('is-dimmed', !keepEdges.has(e.id));
    });
    try { history.replaceState(null, '', '#focus=' + encodeURIComponent(nid)); } catch(e) {}
    if (!insBody) return;
    const upList = Array.from(up.nodes).filter(x => x !== nid);
    const dnList = Array.from(dn.nodes).filter(x => x !== nid);
    const metricsHtml = meta.metrics ? Object.entries(meta.metrics).map(([k, v]) => `<div class="ins-row"><span>${k}</span><strong>${v}</strong></div>`).join('') : '';
    insBody.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:6px;margin-bottom:6px">
        <div class="ins-kicker" style="margin:0">${meta.role || DATA.type || ''}</div>
        <button type="button" class="btn" id="btn-copy-link" style="height:24px;font-size:11px">${T.copy_link || 'Copy Link'}</button>
      </div>
      <h2 class="ins-title">${meta.label || nid}</h2>
      ${meta.change ? `<div class="ins-row"><span>Change</span><strong>${meta.change}</strong></div>` : ''}
      ${meta.description ? `<p style="margin:0 0 12px;color:var(--text-muted)">${meta.description}</p>` : ''}
      ${meta.group ? `<div class="ins-row"><span>${T.group}</span><strong>${meta.group}</strong></div>` : ''}
      ${meta.tech ? `<div class="ins-row"><span>${T.tech}</span><strong>${meta.tech}</strong></div>` : ''}
      ${meta.evidence ? `<div class="ins-row"><span>${T.evidence}</span><strong>${meta.evidence}</strong></div>` : ''}
      ${meta.source ? `<div class="ins-row"><span>${T.source}</span><code style="font-family:var(--font-mono);font-size:11px">${meta.source}</code></div>` : ''}
      ${metricsHtml}
      ${upList.length ? `<div style="margin-top:12px"><div class="ins-kicker">${T.upstream}</div>${upList.map(id => `<span class="ins-chip" data-jump="${id}">${(DATA.nodeMeta[id]||{}).label||id}</span>`).join('')}</div>` : ''}
      ${dnList.length ? `<div style="margin-top:12px"><div class="ins-kicker">${T.downstream}</div>${dnList.map(id => `<span class="ins-chip" data-jump="${id}">${(DATA.nodeMeta[id]||{}).label||id}</span>`).join('')}</div>` : ''}
      ${meta.href ? `<div style="margin-top:14px"><a class="btn" style="text-decoration:none" href="${meta.href}">${T.drilldown}</a></div>` : ''}
    `;
    insBody.querySelectorAll('[data-jump]').forEach(ch => ch.addEventListener('click', () => selectNode(ch.dataset.jump)));
    document.getElementById('btn-copy-link')?.addEventListener('click', e => copyLink('focus=' + encodeURIComponent(nid), e.target));
  }

  function selectEdge(eid) {
    const em = (DATA.edgeMeta || {})[eid];
    if (!em || !insBody) return;
    nodes.forEach(n => n.classList.toggle('is-dimmed', n.dataset.nodeId !== em.from && n.dataset.nodeId !== em.to));
    edges.forEach(e => {
      e.el.classList.toggle('is-highlighted', e.id === eid);
      e.el.classList.toggle('is-dimmed', e.id !== eid);
    });
    const payload = em.payload || null;
    let payloadHtml = '';
    if (payload) {
      payloadHtml = '<div class="diff-box">';
      if (payload.before) payloadHtml += `<div class="diff-del">- ${JSON.stringify(payload.before, null, 2)}</div>`;
      if (payload.after) payloadHtml += `<div class="diff-add">+ ${JSON.stringify(payload.after, null, 2)}</div>`;
      if (payload.sample && !payload.before && !payload.after) payloadHtml += JSON.stringify(payload.sample, null, 2);
      payloadHtml += '</div>';
    }
    insBody.innerHTML = `
      <div class="ins-kicker">Relationship</div>
      <h2 class="ins-title">${em.label || (em.from + ' → ' + em.to)}</h2>
      <div class="ins-row"><span>From</span><strong>${em.from}</strong></div>
      <div class="ins-row"><span>To</span><strong>${em.to}</strong></div>
      ${em.kind ? `<div class="ins-row"><span>Kind</span><strong>${em.kind}</strong></div>` : ''}
      ${em.change ? `<div class="ins-row"><span>Change</span><strong>${em.change}</strong></div>` : ''}
      ${payloadHtml}
    `;
  }

  // Route tracer
  let routeMode = false, routeSrc = null;
  const routeBtn = document.getElementById('btn-route');
  routeBtn?.addEventListener('click', () => {
    routeMode = !routeMode; routeSrc = null;
    routeBtn.classList.toggle('active', routeMode);
    routeBtn.textContent = routeMode ? T.trace_pick_src : T.trace_route;
  });

  function highlightShortestPath(src, dst) {
    const q = [[src]], seen = new Set([src]);
    let found = null;
    while (q.length) {
      const path = q.shift();
      const u = path[path.length - 1];
      if (u === dst) { found = path; break; }
      (fwd[u] || []).forEach(e => {
        if (!seen.has(e.to)) { seen.add(e.to); q.push([...path, e.to]); }
      });
    }
    if (!found) return;
    activeRoute = found; activeFocus = null;
    const pNodes = new Set(found);
    nodes.forEach(n => {
      n.classList.toggle('is-selected', n.dataset.nodeId === src || n.dataset.nodeId === dst);
      n.classList.toggle('is-dimmed', !pNodes.has(n.dataset.nodeId));
    });
    edges.forEach(e => {
      const idx = found.indexOf(e.from);
      const onPath = idx >= 0 && found[idx + 1] === e.to;
      e.el.classList.toggle('is-highlighted', onPath);
      e.el.classList.toggle('is-dimmed', !onPath);
    });
    try { history.replaceState(null, '', '#route=' + encodeURIComponent(src) + '~' + encodeURIComponent(dst)); } catch(e) {}
  }

  nodes.forEach(n => {
    n.addEventListener('click', () => {
      const nid = n.dataset.nodeId;
      if (routeMode) {
        if (!routeSrc) { routeSrc = nid; if (routeBtn) routeBtn.textContent = T.trace_pick_dst; return; }
        highlightShortestPath(routeSrc, nid);
        routeMode = false; routeSrc = null;
        if (routeBtn) { routeBtn.classList.remove('active'); routeBtn.textContent = T.trace_route; }
        return;
      }
      selectNode(nid);
    });
  });
  edges.forEach(e => e.el.addEventListener('click', () => selectEdge(e.id)));

  // Keyboard shortcuts
  document.addEventListener('keydown', e => {
    if (e.target && ['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {
      if (e.key === 'Escape') { e.target.blur(); }
      return;
    }
    if (e.key === '/') { e.preventDefault(); searchIn?.focus(); }
    else if (e.key === 'Escape') { guideModal?.classList.remove('open'); clearHighlight(); }
    else if (e.key === '?') { guideModal?.classList.toggle('open'); }
    else if (e.key === 'p' || e.key === 'P') { togglePresent(); }
    else if (e.key === 'l' || e.key === 'L') { setLive(!liveMotion); }
    else if (e.key === '0') { fitCanvas(); }
  });

  searchIn?.addEventListener('input', () => {
    const q = searchIn.value.trim().toLowerCase();
    if (!q) { clearHighlight(); return; }
    nodes.forEach(n => {
      const meta = (DATA.nodeMeta || {})[n.dataset.nodeId] || {};
      const hay = `${meta.label||''} ${meta.group||''} ${meta.role||''} ${n.dataset.nodeId}`.toLowerCase();
      n.classList.toggle('is-dimmed', !hay.includes(q));
    });
  });

  // Group lens filter
  document.querySelectorAll('[data-filter-group]').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-filter-group]').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeLens = btn.dataset.filterGroup;
      if (activeLens === '__all__') { clearHighlight(); return; }
      nodes.forEach(n => n.classList.toggle('is-dimmed', n.dataset.group !== activeLens));
      try { history.replaceState(null, '', '#lens=' + encodeURIComponent(activeLens)); } catch(e) {}
    });
  });

  // Story mode playback
  const steps = DATA.steps || [];
  let stepIdx = 0, storyTimer = null;
  function applyStep(i) {
    if (!steps.length) return;
    stepIdx = (i + steps.length) % steps.length;
    const st = steps[stepIdx];
    const lbl = document.getElementById('story-caption');
    if (lbl) lbl.textContent = `${stepIdx + 1}/${steps.length} · ${st.title || ''}: ${st.caption || ''}`;
    const fset = new Set(st.focusNodes || []);
    if (fset.size) {
      nodes.forEach(n => {
        const hit = fset.has(n.dataset.nodeId);
        n.classList.toggle('is-selected', hit);
        n.classList.toggle('is-dimmed', !hit);
      });
    }
  }
  if (steps.length) applyStep(0);
  document.getElementById('story-prev')?.addEventListener('click', () => applyStep(stepIdx - 1));
  document.getElementById('story-next')?.addEventListener('click', () => applyStep(stepIdx + 1));
  document.getElementById('story-play')?.addEventListener('click', e => {
    if (storyTimer) { clearInterval(storyTimer); storyTimer = null; e.target.textContent = T.story_play; }
    else { storyTimer = setInterval(() => applyStep(stepIdx + 1), 2400); e.target.textContent = T.story_pause; }
  });

  // Export helpers (Dual-Theme SVG, 2x PNG, 1200x630 Share Card, Story WebM)
  function cloneCanonicalSvg(keepState) {
    const clone = svg.cloneNode(true);
    clone.setAttribute('viewBox', `0 0 ${origW} ${origH}`);
    clone.setAttribute('width', String(origW));
    clone.setAttribute('height', String(origH));
    const mLayer = clone.querySelector('#dg-motion-layer');
    if (mLayer) mLayer.remove();
    const cvp = clone.querySelector('#dg-viewport');
    if (cvp) cvp.removeAttribute('transform');
    if (!keepState) {
      clone.querySelectorAll('.is-dimmed, .is-selected, .is-highlighted').forEach(el => {
        el.classList.remove('is-dimmed', 'is-selected', 'is-highlighted');
      });
    }
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = keepState ? document.querySelector('style').textContent : (DATA.dualThemeCss || document.querySelector('style').textContent);
    clone.insertBefore(style, clone.firstChild);
    return clone;
  }

  function downloadRaster(filename, width, height, keepState, cardSubtitle) {
    const clone = cloneCanonicalSvg(keepState);
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml' }));
    const img = new Image();
    img.onload = () => {
      const c = document.createElement('canvas');
      c.width = width; c.height = height;
      const ctx = c.getContext('2d');
      const cs = getComputedStyle(document.documentElement);
      ctx.fillStyle = cs.getPropertyValue('--bg').trim() || '#F6F4EF';
      ctx.fillRect(0, 0, width, height);
      let topPad = 0;
      if (cardSubtitle) {
        topPad = 84;
        ctx.fillStyle = cs.getPropertyValue('--primary').trim() || '#12263F';
        ctx.font = '600 28px Georgia, serif';
        ctx.fillText(DATA.title || 'Diagram', 40, 44);
        ctx.fillStyle = cs.getPropertyValue('--accent').trim() || '#B5541C';
        ctx.font = '500 15px monospace';
        ctx.fillText(cardSubtitle, 40, 68);
      }
      const availW = width - 48, availH = height - topPad - 32;
      const ratio = Math.min(availW / img.width, availH / img.height);
      const dw = img.width * ratio, dh = img.height * ratio;
      ctx.drawImage(img, (width - dw) / 2, topPad + (availH - dh) / 2, dw, dh);
      const a = document.createElement('a'); a.href = c.toDataURL('image/png'); a.download = filename; a.click();
      URL.revokeObjectURL(url);
    };
    img.src = url;
  }

  document.getElementById('btn-svg')?.addEventListener('click', () => {
    const blob = new Blob([new XMLSerializer().serializeToString(cloneCanonicalSvg(false))], { type: 'image/svg+xml' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'diagram-dual-theme.svg'; a.click();
  });
  document.getElementById('btn-png')?.addEventListener('click', () => {
    const vb = svg.viewBox.baseVal;
    downloadRaster('diagram.png', (vb.width || 1200) * 2, (vb.height || 800) * 2, false, null);
  });
  document.getElementById('btn-share-card')?.addEventListener('click', () => {
    const sub = activeRoute ? ('ROUTE: ' + activeRoute.join(' → ')) : (activeFocus ? ('REACH: ' + activeFocus) : ('ARCHITECTURE OVERVIEW · ' + (DATA.type || '')));
    downloadRaster('share-card-1200x630.png', 1200, 630, !!(activeRoute || activeFocus), sub);
  });
  document.getElementById('btn-video')?.addEventListener('click', async () => {
    if (!steps.length || typeof MediaRecorder === 'undefined') return;
    const c = document.createElement('canvas'); c.width = 1280; c.height = 720;
    const ctx = c.getContext('2d');
    const stream = c.captureStream(10);
    const rec = new MediaRecorder(stream, { mimeType: 'video/webm' });
    const chunks = [];
    rec.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    rec.onstop = () => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(new Blob(chunks, { type: 'video/webm' }));
      a.download = 'story-walkthrough.webm'; a.click();
    };
    rec.start();
    for (let i = 0; i < steps.length; i++) {
      applyStep(i);
      const clone = cloneCanonicalSvg(true);
      const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml' }));
      await new Promise(res => {
        const img = new Image();
        img.onload = () => {
          ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--bg').trim() || '#F6F4EF';
          ctx.fillRect(0, 0, 1280, 720);
          const ratio = Math.min(1180 / img.width, 560 / img.height);
          ctx.drawImage(img, (1280 - img.width * ratio) / 2, 48, img.width * ratio, img.height * ratio);
          ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#1B1F24';
          ctx.font = '600 20px Georgia, serif';
          ctx.fillText(`${i + 1}/${steps.length} · ${steps[i].title || ''}`, 48, 650);
          ctx.font = '400 15px sans-serif';
          ctx.fillText(steps[i].caption || '', 48, 682);
          URL.revokeObjectURL(url);
          setTimeout(res, 1500);
        };
        img.src = url;
      });
    }
    rec.stop();
  });

  // Restore URL hash state (#focus=..., #route=a~b, #lens=..., #theme=dark, #present=1)
  function restoreHash() {
    const raw = (location.hash || '').replace(/^#/, '');
    if (!raw) return;
    const params = new URLSearchParams(raw);
    if (params.get('theme') === 'dark' || params.get('theme') === 'light') setTheme(params.get('theme'));
    if (params.get('present') === '1') togglePresent(true);
    if (params.get('focus')) selectNode(params.get('focus'));
    if (params.get('route') && params.get('route').includes('~')) {
      const [s, d] = params.get('route').split('~');
      highlightShortestPath(s, d);
    }
    if (params.get('lens')) {
      const b = document.querySelector(`[data-filter-group="${params.get('lens')}"]`);
      if (b) b.click();
    }
  }
  restoreHash();
})();
"""


def _esc(s: Any) -> str:
    return html.escape(str(s if s is not None else ""))


def build_viewer_html(
    spec: dict[str, Any],
    svg_str: str,
    node_meta: dict[str, dict[str, Any]],
    edge_meta: dict[str, dict[str, Any]],
    t: dict[str, str],
    lang: str = "id",
    theme: str = "light",
) -> str:
    """Assemble the complete standalone interactive HTML studio viewer."""
    groups = sorted({str(m.get("group")) for m in node_meta.values() if m.get("group")})
    steps = spec.get("steps", [])
    has_changes = any(m.get("change") for m in node_meta.values()) or any(m.get("change") for m in edge_meta.values())

    filter_html = ""
    if groups:
        btns = [f'<button type="button" class="btn active" data-filter-group="__all__">{_esc(t["all_groups"])}</button>']
        btns.extend(f'<button type="button" class="btn" data-filter-group="{_esc(g)}">{_esc(g)}</button>' for g in groups)
        filter_html = f'<div class="filter-strip">{"".join(btns)}</div>'

    change_legend_html = ""
    if has_changes:
        change_legend_html = (
            '<div class="change-legend" aria-label="Change Legend">'
            '<span><i class="chg-dot chg-added"></i>+ Added</span>'
            '<span><i class="chg-dot chg-modified"></i>~ Modified</span>'
            '<span><i class="chg-dot chg-removed"></i>− Removed</span>'
            '</div>'
        )

    story_html = ""
    if steps:
        story_html = (
            '<div class="story-bar">'
            f'<button type="button" id="story-prev" class="btn">{_esc(t["story_prev"])}</button>'
            f'<button type="button" id="story-play" class="btn active">{_esc(t["story_play"])}</button>'
            f'<button type="button" id="story-next" class="btn">{_esc(t["story_next"])}</button>'
            '<span id="story-caption" style="font-size:13px"></span>'
            '</div>'
        )

    video_btn_html = (
        f'<button type="button" id="btn-video" class="btn">{_esc(t.get("export_video", "Story Video (WebM)"))}</button>'
        if steps else ""
    )

    payload = json.dumps({
        "title": spec.get("title", "Diagram"),
        "type": spec.get("type", "architecture"),
        "nodeMeta": node_meta,
        "edgeMeta": edge_meta,
        "steps": steps,
        "dualThemeCss": DUAL_THEME_SVG_CSS,
    }, ensure_ascii=False)
    i18n_json = json.dumps(t, ensure_ascii=False)
    other_theme_lbl = t["theme_light"] if theme == "dark" else t["theme_dark"]

    return (
        f'<!DOCTYPE html>\n<html lang="{_esc(lang)}" data-theme="{_esc(theme)}">\n<head>\n'
        '<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n'
        f'<title>{_esc(spec.get("title", "IdeaForge Visual Architect"))}</title>\n'
        f'<style>{STUDIO_CSS}</style>\n</head>\n<body>\n'
        '<div id="studio-shell" class="studio-shell">\n'
        f'  <button type="button" id="btn-exit-present" class="btn present-exit">{_esc(t.get("exit_present", "Exit Present (P)"))}</button>\n'
        '  <header class="studio-bar">\n'
        '    <div class="studio-brand">\n'
        f'      <span class="studio-title">{_esc(spec.get("title", "Diagram"))}</span>\n'
        f'      <span class="studio-meta">{_esc(spec.get("type", "architecture"))} · {len(node_meta)} {_esc(t["nodes_lbl"])} · {len(edge_meta)} {_esc(t["edges_lbl"])}</span>\n'
        '    </div>\n'
        '    <div class="studio-actions">\n'
        f'      <input id="dg-search" class="search-in" type="search" placeholder="{_esc(t["search_placeholder"])}">\n'
        f'      <button type="button" id="btn-live" class="btn">{_esc(t.get("motion_still", "Still"))}</button>\n'
        f'      <button type="button" id="btn-route" class="btn">{_esc(t["trace_route"])}</button>\n'
        f'      <button type="button" id="btn-fit" class="btn">{_esc(t["fit"])}</button>\n'
        f'      <button type="button" id="btn-reset" class="btn">{_esc(t["reset"])}</button>\n'
        f'      <button type="button" id="btn-present" class="btn">{_esc(t.get("present", "Present"))}</button>\n'
        '      <div class="export-wrap">\n'
        f'        <button type="button" id="btn-export-pop" class="btn">{_esc(t.get("export_menu", "Ekspor ▾"))}</button>\n'
        '        <div id="export-menu" class="export-menu">\n'
        f'          <button type="button" id="btn-svg" class="btn">{_esc(t["export_svg"])} (Dual-Theme)</button>\n'
        f'          <button type="button" id="btn-png" class="btn">{_esc(t["export_png"])} (2x HiDPI)</button>\n'
        f'          <button type="button" id="btn-share-card" class="btn">{_esc(t.get("share_card", "Share Card (1200×630)"))}</button>\n'
        f'          {video_btn_html}\n'
        '        </div>\n'
        '      </div>\n'
        f'      <button type="button" id="btn-theme" class="btn">{_esc(other_theme_lbl)}</button>\n'
        '      <button type="button" id="btn-guide" class="btn" title="Shortcuts">?</button>\n'
        '    </div>\n'
        '  </header>\n'
        '  <div class="studio-body">\n'
        f'    <main id="canvas-wrap" class="canvas-wrap">{filter_html}{change_legend_html}{svg_str}{story_html}'
        '      <div id="radar-box" class="radar-box" title="Semantic Radar"><div id="radar-vp" class="radar-vp"></div></div>'
        '    </main>\n'
        '    <aside class="inspector">\n'
        f'      <div class="ins-kicker">{_esc(t["inspector_title"])}</div>\n'
        f'      <div id="inspector-body"><p style="color:var(--text-muted)">{_esc(t["no_selection"])}</p></div>\n'
        '    </aside>\n'
        '  </div>\n'
        '</div>\n'
        '<div id="guide-modal" class="guide-modal" role="dialog" aria-label="Diagram Guide">\n'
        '  <div class="guide-card">\n'
        '    <h3>Diagram Guide &amp; Shortcuts</h3>\n'
        '    <div class="kbd-row"><span>Search nodes</span><kbd>/</kbd></div>\n'
        '    <div class="kbd-row"><span>Toggle Live / Still flow</span><kbd>L</kbd></div>\n'
        '    <div class="kbd-row"><span>Presentation mode</span><kbd>P</kbd></div>\n'
        '    <div class="kbd-row"><span>Fit canvas</span><kbd>0</kbd></div>\n'
        '    <div class="kbd-row"><span>Clear focus / close</span><kbd>Esc</kbd></div>\n'
        '    <div style="margin-top:14px;text-align:right"><button type="button" id="btn-close-guide" class="btn">Close</button></div>\n'
        '  </div>\n'
        '</div>\n'
        f'<script>window.__DIAG_DATA__={payload};window.__DIAG_I18N__={i18n_json};</script>\n'
        f'<script>{STUDIO_JS}</script>\n</body>\n</html>\n'
    )
