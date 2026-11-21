#!/usr/bin/env python3
"""Scenario financial model (transactional & SaaS) with multi-chart SVG generation.

Usage:
  python3 model.py inputs.json [--months 12] [--locale auto|id|en] [--chart-out chart.svg] [--charts-dir assets/] [--json-out summary.json]
"""
import argparse
import json
import sys
from pathlib import Path


def resolve_locale(currency: str, locale_arg: str) -> str:
    if locale_arg in ("id", "en"):
        return locale_arg
    return "id" if currency.upper() == "IDR" else "en"


def fmt_num(val: float, decimals: int = 0, locale: str = "id") -> str:
    s = f"{val:,.{decimals}f}"
    if locale == "id":
        return s.replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def fmt_short(val: float, currency: str, locale: str) -> str:
    av = abs(val)
    if av >= 1_000_000_000:
        return f"{fmt_num(val / 1_000_000_000, 1, locale)}M {currency}".strip()
    if av >= 1_000_000:
        return f"{fmt_num(val / 1_000_000, 1, locale)}jt {currency}".strip() if locale == "id" else f"{fmt_num(val / 1_000_000, 1, locale)}M {currency}".strip()
    if av >= 1_000:
        return f"{fmt_num(val / 1_000, 0, locale)}rb {currency}".strip() if locale == "id" else f"{fmt_num(val / 1_000, 0, locale)}k {currency}".strip()
    return f"{fmt_num(val, 0, locale)} {currency}".strip()


def compute_runway(exhausted_month, cash: float, final_profit: float, months: int) -> str:
    if exhausted_month is not None:
        return f"Month {exhausted_month} (cash exhausted)"
    if final_profit < 0:
        est = months + (cash / abs(final_profit))
        return f"{est:.1f} months"
    return f">{months} months (cash-flow positive)"


def run_transactional(i: dict, m: dict, months: int = 12, price_override=None, units_mult_override=None) -> dict:
    price = float(price_override if price_override is not None else i["price"])
    units_mult = float(units_mult_override if units_mult_override is not None else m.get("units", 1.0))
    units = float(i["month1_units"]) * units_mult
    growth = float(i["monthly_growth"]) * float(m.get("growth", 1.0))
    cost_mult = float(m.get("cost", 1.0))
    vc = float(i["unit_variable_cost"]) * cost_mult
    fixed = float(i["monthly_fixed_costs"]) * cost_mult
    capex = float(i.get("capex", 0.0))
    channel_fee_rate = float(i.get("channel_fee_rate", 0.0))
    tax_rate = float(i.get("tax_rate", 0.0))
    tax_on_profit_rate = float(i.get("tax_on_profit_rate", 0.0))
    cac = float(i.get("cac", 0.0))
    repeat = max(1.0, float(i.get("repeat_orders_per_customer", 1.0)))

    cash = float(i["starting_cash"]) - capex
    rows = []
    breakeven = None
    exhausted_month = 0 if cash <= 0 else None
    final_profit = 0.0

    for mo in range(1, months + 1):
        revenue = units * price
        channel_fee = revenue * channel_fee_rate
        cogs = units * vc
        gross_profit = revenue - cogs - channel_fee
        new_customers = units / repeat
        acq_cost = new_customers * cac
        ebt = gross_profit - fixed - acq_cost
        tax = (revenue * tax_rate) + (max(0.0, ebt) * tax_on_profit_rate)
        net_profit = ebt - tax
        cash += net_profit
        final_profit = net_profit
        if breakeven is None and net_profit >= 0:
            breakeven = mo
        if exhausted_month is None and cash <= 0:
            exhausted_month = mo
        rows.append((mo, round(units), round(revenue), round(net_profit), round(cash)))
        units *= 1.0 + growth

    unit_margin = price * (1.0 - channel_fee_rate) - vc
    ltv = unit_margin * repeat
    gross_margin_pct = (unit_margin / price * 100.0) if price > 0 else 0.0
    payback_months = (cac / (unit_margin * repeat)) if (unit_margin > 0 and cac > 0) else None
    runway = compute_runway(exhausted_month, cash, final_profit, months)

    return {
        "rows": rows,
        "breakeven_month": breakeven,
        "runway": runway,
        "ltv": ltv,
        "cac": cac,
        "ltv_cac": (ltv / cac) if cac > 0 else None,
        "gross_margin_pct": gross_margin_pct,
        "payback_months": payback_months,
        "lowest_cash": min(r[4] for r in rows) if rows else round(cash),
        "ending_cash": rows[-1][4] if rows else round(cash),
        "exhausted_month": exhausted_month,
        "unit_breakdown": {
            "price": price,
            "vc": vc,
            "channel_fee": price * channel_fee_rate,
            "tax": price * tax_rate,
            "margin": max(0.0, unit_margin - price * tax_rate),
        },
    }


def run_saas(i: dict, m: dict, months: int = 12, price_override=None, churn_mult_override=None) -> dict:
    price = float(price_override if price_override is not None else i["price"])
    new_cust = float(i.get("month1_new_customers", i.get("month1_units", 0))) * float(m.get("units", 1.0))
    growth = float(i["monthly_growth"]) * float(m.get("growth", 1.0))
    churn_mult = float(churn_mult_override if churn_mult_override is not None else m.get("churn", 1.0))
    churn = min(0.99, max(0.0, float(i.get("monthly_churn_rate", 0.05)) * churn_mult))
    cost_mult = float(m.get("cost", 1.0))
    vc = float(i["unit_variable_cost"]) * cost_mult
    fixed = float(i["monthly_fixed_costs"]) * cost_mult
    capex = float(i.get("capex", 0.0))
    channel_fee_rate = float(i.get("channel_fee_rate", 0.0))
    tax_rate = float(i.get("tax_rate", 0.0))
    tax_on_profit_rate = float(i.get("tax_on_profit_rate", 0.0))
    cac = float(i.get("cac", 0.0))

    active = float(i.get("starting_active_customers", 0.0))
    cash = float(i["starting_cash"]) - capex
    rows = []
    breakeven = None
    exhausted_month = 0 if cash <= 0 else None
    final_profit = 0.0

    for mo in range(1, months + 1):
        churned = active * churn
        active = max(0.0, active - churned + new_cust)
        revenue = active * price
        channel_fee = revenue * channel_fee_rate
        cogs = active * vc
        gross_profit = revenue - cogs - channel_fee
        acq_cost = new_cust * cac
        ebt = gross_profit - fixed - acq_cost
        tax = (revenue * tax_rate) + (max(0.0, ebt) * tax_on_profit_rate)
        net_profit = ebt - tax
        cash += net_profit
        final_profit = net_profit
        if breakeven is None and net_profit >= 0:
            breakeven = mo
        if exhausted_month is None and cash <= 0:
            exhausted_month = mo
        rows.append((mo, round(active), round(revenue), round(net_profit), round(cash)))
        new_cust *= 1.0 + growth

    unit_margin = price * (1.0 - channel_fee_rate) - vc
    ltv = (unit_margin / churn) if churn > 0 else None
    gross_margin_pct = (unit_margin / price * 100.0) if price > 0 else 0.0
    payback_months = (cac / unit_margin) if (unit_margin > 0 and cac > 0) else None
    runway = compute_runway(exhausted_month, cash, final_profit, months)

    return {
        "rows": rows,
        "breakeven_month": breakeven,
        "runway": runway,
        "ltv": ltv,
        "cac": cac,
        "ltv_cac": (ltv / cac) if (cac > 0 and ltv is not None) else None,
        "gross_margin_pct": gross_margin_pct,
        "payback_months": payback_months,
        "lowest_cash": min(r[4] for r in rows) if rows else round(cash),
        "ending_cash": rows[-1][4] if rows else round(cash),
        "exhausted_month": exhausted_month,
        "unit_breakdown": {
            "price": price,
            "vc": vc,
            "channel_fee": price * channel_fee_rate,
            "tax": price * tax_rate,
            "margin": max(0.0, unit_margin - price * tax_rate),
        },
    }


def run_scenario(i: dict, m: dict, months: int = 12, **kwargs) -> dict:
    model_type = i.get("model_type", "transactional").lower()
    if model_type == "saas":
        return run_saas(i, m, months=months, **kwargs)
    return run_transactional(i, m, months=months, **kwargs)


def generate_svg_chart(results: dict, currency: str, months: int, locale: str) -> str:
    w, h = 680, 270
    pad_l, pad_r, pad_t, pad_b = 72, 95, 42, 48
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b

    all_vals = [r[4] for res in results.values() for r in res["rows"]] or [0]
    min_v = min(min(all_vals), 0)
    max_v = max(max(all_vals), 1)
    if max_v == min_v:
        max_v = min_v + 1

    max_abs = max(abs(min_v), abs(max_v))
    if max_abs >= 1_000_000:
        scale, unit_label = 1_000_000.0, f"Juta {currency}" if locale == "id" else f"M {currency}"
    elif max_abs >= 1_000:
        scale, unit_label = 1_000.0, f"Ribu {currency}" if locale == "id" else f"k {currency}"
    else:
        scale, unit_label = 1.0, currency

    def x_pos(idx: int, total: int) -> float:
        return pad_l if total <= 1 else pad_l + (idx / (total - 1)) * plot_w

    def y_pos(val: float) -> float:
        return pad_t + plot_h - ((val - min_v) / (max_v - min_v)) * plot_h

    styles = {
        "optimistic": ("#1B365D", "2.4", ""),
        "base": ("#2563EB", "2.2", ""),
        "pessimistic": ("#B91C1C", "2.0", ' stroke-dasharray="5,3"'),
    }
    fallback_colors = ["#1B365D", "#2563EB", "#B91C1C", "#374151"]

    lines = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Cash Projection Chart">',
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#FFFFFF"/>',
        f'  <text x="{pad_l}" y="22" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="12" font-weight="700" fill="#111317">1. Proyeksi Saldo Kas {months} Bulan ({unit_label})</text>',
        f'  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#B8C0CC" stroke-width="1"/>',
        f'  <line x1="{pad_l}" y1="{pad_t + plot_h}" x2="{pad_l + plot_w}" y2="{pad_t + plot_h}" stroke="#B8C0CC" stroke-width="1"/>',
    ]

    for step in range(5):
        v = min_v + (max_v - min_v) * (step / 4.0)
        yp = y_pos(v)
        lbl = fmt_num(v / scale, decimals=1 if scale > 1 and abs(v / scale) < 10 else 0, locale=locale)
        lines.append(f'  <line x1="{pad_l}" y1="{yp:.1f}" x2="{pad_l + plot_w}" y2="{yp:.1f}" stroke="#EEF1F4" stroke-width="1"/>')
        lines.append(f'  <text x="{pad_l - 8}" y="{yp + 3:.1f}" text-anchor="end" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#525866">{lbl}</text>')

    if min_v < 0 < max_v:
        y0 = y_pos(0)
        lines.append(f'  <line x1="{pad_l}" y1="{y0:.1f}" x2="{pad_l + plot_w}" y2="{y0:.1f}" stroke="#6B7280" stroke-width="1" stroke-dasharray="3,3"/>')

    legend_x = pad_l
    for idx, (name, res) in enumerate(results.items()):
        color, width, dash = styles.get(name, (fallback_colors[idx % len(fallback_colors)], "2.0", ""))
        pts = " ".join(f"{x_pos(j, len(res['rows'])):.1f},{y_pos(r[4]):.1f}" for j, r in enumerate(res["rows"]))
        lines.append(f'  <polyline fill="none" stroke="{color}" stroke-width="{width}"{dash} points="{pts}"/>')
        if res["rows"]:
            lx, ly = x_pos(len(res["rows"]) - 1, len(res["rows"])), y_pos(res["rows"][-1][4])
            lines.append(f'  <circle cx="{lx:.1f}" cy="{ly:.1f}" r="3" fill="{color}"/>')
            end_lbl = fmt_short(res["rows"][-1][4], "", locale)
            lines.append(f'  <text x="{lx + 7:.1f}" y="{ly + 3:.1f}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="8.5" font-weight="600" fill="{color}">{end_lbl}</text>')
        lines.append(f'  <line x1="{legend_x}" y1="{h - 14}" x2="{legend_x + 18}" y2="{h - 14}" stroke="{color}" stroke-width="{width}"{dash}/>')
        lines.append(f'  <text x="{legend_x + 24}" y="{h - 11}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#1A1D21">{name}</text>')
        legend_x += 105

    lines.append(f'  <text x="{pad_l}" y="{pad_t + plot_h + 14}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#525866">M1</text>')
    mid_x = x_pos((months - 1) // 2, months)
    lines.append(f'  <text x="{mid_x:.1f}" y="{pad_t + plot_h + 14}" text-anchor="middle" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#525866">M{(months + 1) // 2}</text>')
    lines.append(f'  <text x="{pad_l + plot_w}" y="{pad_t + plot_h + 14}" text-anchor="end" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#525866">M{months}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def generate_revenue_profit_svg(base_res: dict, currency: str, months: int, locale: str) -> str:
    w, h = 680, 250
    pad_l, pad_r, pad_t, pad_b = 72, 24, 42, 46
    plot_w = w - pad_l - pad_r
    plot_h = h - pad_t - pad_b
    rows = base_res["rows"]
    vals = [r[2] for r in rows] + [r[3] for r in rows] + [0]
    min_v, max_v = min(vals), max(max(vals), 1)
    if max_v == min_v:
        max_v = min_v + 1

    max_abs = max(abs(min_v), abs(max_v))
    scale = 1_000_000.0 if max_abs >= 1_000_000 else (1_000.0 if max_abs >= 1_000 else 1.0)
    unit_label = (f"Juta {currency}" if scale == 1_000_000 else f"Ribu {currency}" if scale == 1_000 else currency) if locale == "id" else (f"M {currency}" if scale == 1_000_000 else f"k {currency}" if scale == 1_000 else currency)

    def y_pos(v: float) -> float:
        return pad_t + plot_h - ((v - min_v) / (max_v - min_v)) * plot_h

    y0 = y_pos(0)
    group_w = plot_w / max(1, len(rows))
    bar_w = max(4.0, group_w * 0.34)

    lines = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Revenue vs Net Profit">',
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#FFFFFF"/>',
        f'  <text x="{pad_l}" y="22" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="12" font-weight="700" fill="#111317">2. Omzet vs Laba Bersih Bulanan — Skenario Dasar ({unit_label})</text>',
        f'  <line x1="{pad_l}" y1="{pad_t}" x2="{pad_l}" y2="{pad_t + plot_h}" stroke="#B8C0CC" stroke-width="1"/>',
    ]
    for step in range(5):
        v = min_v + (max_v - min_v) * (step / 4.0)
        yp = y_pos(v)
        lbl = fmt_num(v / scale, decimals=1 if scale > 1 and abs(v / scale) < 10 else 0, locale=locale)
        lines.append(f'  <line x1="{pad_l}" y1="{yp:.1f}" x2="{pad_l + plot_w}" y2="{yp:.1f}" stroke="#EEF1F4" stroke-width="1"/>')
        lines.append(f'  <text x="{pad_l - 8}" y="{yp + 3:.1f}" text-anchor="end" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#525866">{lbl}</text>')

    lines.append(f'  <line x1="{pad_l}" y1="{y0:.1f}" x2="{pad_l + plot_w}" y2="{y0:.1f}" stroke="#6B7280" stroke-width="1"/>')

    for idx, (mo, _, rev, prof, _) in enumerate(rows):
        gx = pad_l + idx * group_w + group_w * 0.14
        # Revenue bar
        ry = y_pos(rev)
        rh = max(1.0, abs(y0 - ry))
        lines.append(f'  <rect x="{gx:.1f}" y="{min(ry, y0):.1f}" width="{bar_w:.1f}" height="{rh:.1f}" fill="#4B6A9B" rx="1"/>')
        # Profit bar
        py = y_pos(prof)
        ph = max(1.0, abs(y0 - py))
        p_color = "#15803D" if prof >= 0 else "#B91C1C"
        lines.append(f'  <rect x="{gx + bar_w + 2:.1f}" y="{min(py, y0):.1f}" width="{bar_w:.1f}" height="{ph:.1f}" fill="{p_color}" rx="1"/>')
        lines.append(f'  <text x="{gx + bar_w:.1f}" y="{pad_t + plot_h + 13}" text-anchor="middle" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="8.5" fill="#525866">M{mo}</text>')

    lines.append(f'  <rect x="{pad_l}" y="{h - 17}" width="10" height="10" fill="#4B6A9B" rx="1"/><text x="{pad_l + 15}" y="{h - 9}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#1A1D21">Omzet</text>')
    lines.append(f'  <rect x="{pad_l + 75}" y="{h - 17}" width="10" height="10" fill="#15803D" rx="1"/><text x="{pad_l + 90}" y="{h - 9}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#1A1D21">Laba Bersih (+)</text>')
    lines.append(f'  <rect x="{pad_l + 190}" y="{h - 17}" width="10" height="10" fill="#B91C1C" rx="1"/><text x="{pad_l + 205}" y="{h - 9}" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#1A1D21">Rugi (-)</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def generate_unit_economics_svg(base_res: dict, currency: str, locale: str) -> str:
    w, h = 680, 195
    ub = base_res["unit_breakdown"]
    price = max(1.0, ub["price"])
    bar_x, bar_w, bar_y, bar_h = 40, 600, 56, 30

    parts = [
        ("COGS", ub["vc"], "#64748B"),
        ("Channel Fee", ub["channel_fee"], "#D97706"),
        ("Pajak", ub["tax"], "#94A3B8"),
        ("Margin Bersih", ub["margin"], "#15803D"),
    ]

    lines = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Unit Economics Breakdown">',
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#FFFFFF"/>',
        f'  <text x="40" y="22" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="12" font-weight="700" fill="#111317">3. Struktur Ekonomi Unit ({fmt_short(price, currency, locale)}/unit) &amp; Rasio LTV vs CAC</text>',
        f'  <text x="40" y="46" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9.5" fill="#4B5563">Komposisi Harga Jual per Unit:</text>',
    ]
    cx = float(bar_x)
    lx = 40
    for label, val, color in parts:
        pw = (val / price) * bar_w
        if pw > 0:
            lines.append(f'  <rect x="{cx:.1f}" y="{bar_y}" width="{pw:.1f}" height="{bar_h}" fill="{color}"/>')
            if pw > 55:
                pct = val / price * 100
                lines.append(f'  <text x="{cx + pw / 2:.1f}" y="{bar_y + 19}" text-anchor="middle" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" font-weight="600" fill="#FFFFFF">{pct:.0f}%</text>')
            cx += pw
        lines.append(f'  <rect x="{lx}" y="96" width="9" height="9" fill="{color}" rx="1"/>')
        lines.append(f'  <text x="{lx + 13}" y="104" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="8.5" fill="#1A1D21">{label}: {fmt_short(val, currency, locale)}</text>')
        lx += 148

    # LTV vs CAC comparison bars
    ltv = base_res["ltv"] or 0.0
    cac = base_res["cac"] or 0.0
    max_lc = max(ltv, cac, 1.0)
    ltv_w = (ltv / max_lc) * 420
    cac_w = (cac / max_lc) * 420
    ratio_txt = f"{fmt_num(base_res['ltv_cac'], 1, locale)}x" if base_res["ltv_cac"] is not None else "n/a"

    lines.append(f'  <text x="40" y="134" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9.5" font-weight="600" fill="#111317">LTV vs CAC (Rasio: {ratio_txt}):</text>')
    lines.append(f'  <rect x="95" y="144" width="{ltv_w:.1f}" height="16" fill="#1B365D" rx="2"/>')
    lines.append(f'  <text x="40" y="156" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#374151">LTV</text>')
    lines.append(f'  <text x="{102 + ltv_w:.1f}" y="156" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" font-weight="600" fill="#1B365D">{fmt_short(ltv, currency, locale)}</text>')

    lines.append(f'  <rect x="95" y="166" width="{max(2.0, cac_w):.1f}" height="16" fill="#D97706" rx="2"/>')
    lines.append(f'  <text x="40" y="178" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" fill="#374151">CAC</text>')
    lines.append(f'  <text x="{102 + max(2.0, cac_w):.1f}" y="178" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" font-weight="600" fill="#B45309">{fmt_short(cac, currency, locale)}</text>')
    lines.append("</svg>")
    return "\n".join(lines)


def generate_sensitivity_heatmap_svg(title: str, row_labels: list[str], col_labels: list[str], matrix: list[list[float]], currency: str, locale: str) -> str:
    w, h = 680, 225
    start_x, start_y = 95, 58
    cell_w, cell_h = 112, 28
    flat = [v for row in matrix for v in row]
    max_pos = max([v for v in flat if v > 0] or [1.0])
    min_neg = min([v for v in flat if v < 0] or [-1.0])

    lines = [
        f'<svg viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Sensitivity Heatmap">',
        f'  <rect x="0" y="0" width="{w}" height="{h}" fill="#FFFFFF"/>',
        f'  <text x="40" y="22" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="12" font-weight="700" fill="#111317">4. Peta Sensitivitas Kas Bulan Akhir ({title})</text>',
        f'  <text x="40" y="38" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="8.5" fill="#6B7280">Hijau/Biru = kas positif aman | Merah = defisit kas (bahaya)</text>',
    ]
    for ci, cl in enumerate(col_labels):
        cx = start_x + ci * cell_w + cell_w / 2
        lines.append(f'  <text x="{cx:.1f}" y="{start_y - 8}" text-anchor="middle" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" font-weight="600" fill="#1B365D">{cl}</text>')

    for ri, rl in enumerate(row_labels):
        ry = start_y + ri * cell_h
        lines.append(f'  <text x="{start_x - 10}" y="{ry + 18}" text-anchor="end" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="9" font-weight="600" fill="#374151">{rl}</text>')
        for ci, val in enumerate(matrix[ri]):
            rx = start_x + ci * cell_w
            if val < 0:
                intensity = min(1.0, abs(val) / abs(min_neg))
                bg = "#FEE2E2" if intensity < 0.45 else "#FECACA"
                fg = "#991B1B"
            else:
                ratio = val / max_pos
                bg = "#ECFDF5" if ratio < 0.4 else ("#D1FAE5" if ratio < 0.75 else "#A7F3D0")
                fg = "#065F46"
            border = "2" if (rl == "+0%" and "1x" in col_labels[ci]) else "1"
            stroke = "#1B365D" if border == "2" else "#FFFFFF"
            lines.append(f'  <rect x="{rx}" y="{ry}" width="{cell_w - 2}" height="{cell_h - 2}" fill="{bg}" stroke="{stroke}" stroke-width="{border}" rx="3"/>')
            lines.append(f'  <text x="{rx + cell_w / 2 - 1:.1f}" y="{ry + 18}" text-anchor="middle" font-family="-apple-system, Helvetica Neue, Arial, sans-serif" font-size="8.5" font-weight="600" fill="{fg}">{fmt_short(val, currency, locale)}</text>')

    lines.append("</svg>")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Scenario financial model (transactional & SaaS).")
    ap.add_argument("inputs", help="Path to inputs.json")
    ap.add_argument("--months", type=int, default=12, help="Projection horizon in months (default: 12)")
    ap.add_argument("--locale", choices=["auto", "id", "en"], default="auto", help="Number formatting locale")
    ap.add_argument("--chart-out", help="Optional path to save cash projection SVG chart")
    ap.add_argument("--charts-dir", help="Optional directory to save all 4 SVG charts")
    ap.add_argument("--json-out", help="Optional path to save computed JSON summary")
    args = ap.parse_args()

    i = json.loads(Path(args.inputs).read_text(encoding="utf-8"))
    currency = i.get("currency", "")
    locale = resolve_locale(currency, args.locale)
    model_type = i.get("model_type", "transactional").lower()
    vol_header = "Active Users" if model_type == "saas" else "Units"

    results = {}
    print(f"# Model Output ({currency} | mode: {model_type})\n")

    for name, m in i["scenario_multipliers"].items():
        res = run_scenario(i, m, months=args.months)
        results[name] = res
        print(f"## Scenario: {name}\n")
        print(f"| Month | {vol_header} | Revenue | Net Profit | Cash |")
        print("|---|---|---|---|---|")
        for r in res["rows"]:
            vals = [str(r[0])] + [fmt_num(x, 0, locale) for x in r[1:]]
            print("| " + " | ".join(vals) + " |")
        be = f"Month {res['breakeven_month']}" if res["breakeven_month"] else f"not within {args.months} months"
        low_status = "CASH SHORTFALL" if res["lowest_cash"] < 0 else "ok"
        print(f"\n- Break-even month: {be}")
        print(f"- Lowest cash point: {fmt_num(res['lowest_cash'], 0, locale)} ({low_status})")
        print(f"- Runway: {res['runway']}")
        print(f"- Gross margin: {fmt_num(res['gross_margin_pct'], 1, locale)}%")
        ltv_str = fmt_num(res["ltv"], 0, locale) if res["ltv"] is not None else "n/a"
        cac_str = fmt_num(res["cac"], 0, locale)
        ratio_str = f"{fmt_num(res['ltv_cac'], 1, locale)}x" if res["ltv_cac"] is not None else "n/a (CAC = 0 or LTV n/a)"
        payback_str = f"{fmt_num(res['payback_months'], 1, locale)} months" if res["payback_months"] is not None else "n/a"
        print(f"- LTV: {ltv_str} | CAC: {cac_str} | LTV/CAC: {ratio_str} | Payback: {payback_str}\n")

    base_key = "base" if "base" in i["scenario_multipliers"] else next(iter(i["scenario_multipliers"]))
    base_m = i["scenario_multipliers"][base_key]
    price_deltas = (-0.2, -0.1, 0.0, 0.1, 0.2)
    row_labels = [f"{d:+.0%}" for d in price_deltas]
    sens_matrix = []

    if model_type == "saas":
        col_mults = (0.5, 0.75, 1.0, 1.25, 1.5)
        col_labels = [f"{cm:g}x churn" for cm in col_mults]
        sens_title = "ARPU vs Churn"
        print(f"## 2-Way Sensitivity ({base_key} scenario, Month-{args.months} cash: {sens_title})\n")
        print("| ARPU \\ Churn | " + " | ".join(col_labels) + " |")
        print("|---|" + "|".join("---" for _ in col_mults) + "|")
        for d in price_deltas:
            row_vals = []
            for cm in col_mults:
                sres = run_scenario(i, base_m, months=args.months, price_override=i["price"] * (1 + d), churn_mult_override=cm)
                row_vals.append(float(sres["ending_cash"]))
            sens_matrix.append(row_vals)
            print(f"| {d:+.0%} | " + " | ".join(fmt_num(v, 0, locale) for v in row_vals) + " |")
    else:
        col_mults = (0.7, 0.85, 1.0, 1.15, 1.3)
        col_labels = [f"{vm:g}x vol" for vm in col_mults]
        sens_title = "Harga vs Volume" if locale == "id" else "Price vs Volume"
        print(f"## 2-Way Sensitivity ({base_key} scenario, Month-{args.months} cash: {sens_title})\n")
        print("| Price \\ Volume | " + " | ".join(col_labels) + " |")
        print("|---|" + "|".join("---" for _ in col_mults) + "|")
        for d in price_deltas:
            row_vals = []
            for vm in col_mults:
                sres = run_scenario(i, base_m, months=args.months, price_override=i["price"] * (1 + d), units_mult_override=base_m.get("units", 1.0) * vm)
                row_vals.append(float(sres["ending_cash"]))
            sens_matrix.append(row_vals)
            print(f"| {d:+.0%} | " + " | ".join(fmt_num(v, 0, locale) for v in row_vals) + " |")

    if args.chart_out:
        chart_path = Path(args.chart_out)
        chart_path.parent.mkdir(parents=True, exist_ok=True)
        chart_path.write_text(generate_svg_chart(results, currency, args.months, locale), encoding="utf-8")

    if args.charts_dir:
        cdir = Path(args.charts_dir)
        cdir.mkdir(parents=True, exist_ok=True)
        (cdir / "cash-projection.svg").write_text(generate_svg_chart(results, currency, args.months, locale), encoding="utf-8")
        (cdir / "revenue-profit.svg").write_text(generate_revenue_profit_svg(results[base_key], currency, args.months, locale), encoding="utf-8")
        (cdir / "unit-economics.svg").write_text(generate_unit_economics_svg(results[base_key], currency, locale), encoding="utf-8")
        (cdir / "sensitivity-heatmap.svg").write_text(generate_sensitivity_heatmap_svg(sens_title, row_labels, col_labels, sens_matrix, currency, locale), encoding="utf-8")

    if args.json_out:
        summary = {
            "currency": currency,
            "model_type": model_type,
            "months": args.months,
            "price": i["price"],
            "scenarios": {
                k: {
                    "breakeven_month": v["breakeven_month"],
                    "lowest_cash": v["lowest_cash"],
                    "ending_cash": v["ending_cash"],
                    "runway": v["runway"],
                    "gross_margin_pct": round(v["gross_margin_pct"], 2),
                    "ltv": round(v["ltv"], 2) if v["ltv"] is not None else None,
                    "cac": v["cac"],
                    "ltv_cac": round(v["ltv_cac"], 2) if v["ltv_cac"] is not None else None,
                    "payback_months": round(v["payback_months"], 2) if v["payback_months"] is not None else None,
                }
                for k, v in results.items()
            },
        }
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
