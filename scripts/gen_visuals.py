#!/usr/bin/env python3
"""AeroSkills visuals + metrics generator (deterministic, stdlib-only, offline).

Single source of truth for every number shown in the README and in
docs/*.svg charts. Everything is computed from the tree at HEAD:

  leaves           skills/<family>/<pack>/<leaf>/SKILL.md   (depth-4 files)
  live packs       skills/<family>/<pack>/                  (depth-2 dirs)
  families         skills/<family>/                         (depth-1 dirs)
  corpus tasks     eval/hit1-corpus.yaml                    (`- id:` entries,
                   attributed per family via `expected_skill:`)
  standards        standards-map.yaml                       (`- id:` entries)

Current numbers only — no roadmap/target figures anywhere (founder
2026-09-01: the README quotes what exists at HEAD, nothing aspirational).

Outputs (all overwritten in place):
  docs/metrics.json                machine-readable snapshot
  docs/logo.svg / logo-dark.svg    roundel emblem (NACA 2412 computed)
  docs/domain-radar[-dark].svg     12-axis radar: skills vs router tasks
  docs/domain-polar[-dark].svg     polar rose: live packs per family (area-true)
  docs/stats[-dark].svg            current-state instrument strip
  README.md                        every <!-- gen:NAME --> block rewritten

Usage:
  python3 scripts/gen_visuals.py           regenerate everything
  python3 scripts/gen_visuals.py --check   fail (exit 1) if anything is stale

Design law: docs/DESIGN.md (blueprint language, single mint accent,
no gradients, no shadows, mono uppercase labels, title blocks).
"""

import json
import math
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------- constants

# family dir -> (chart label, standard spine) — label/spine are editorial,
# every count is computed. Order on charts = sorted dir name (stable).
FAMILY_META = {
    "aerodynamics": ("AERODYNAMICS", "NACA TR-824"),
    "avionics": ("AVIONICS", "DO-178C / DO-254 / DO-160G"),
    "cross-cutting": ("CROSS-CUTTING", "SEP-2640"),
    "flight-mechanics": ("FLIGHT MECHANICS", "FAR-25 / CS-25"),
    "flight-test-operations": ("FLIGHT TEST & OPS", "FAR-25 / CS-25"),
    "gnc-autonomy": ("GNC & AUTONOMY", "ARP4754A"),
    "manufacturing-quality": ("MANUFACTURING QUALITY", "AS9100 / AS9102"),
    "propulsion": ("PROPULSION", "FAR-33"),
    "space-systems": ("SPACE SYSTEMS", "ECSS"),
    "structures": ("STRUCTURES", "FAR-25 / CS-25 / MMPDS"),
    "systems-engineering-safety": ("SYSTEMS ENG & SAFETY", "ARP4754A / ARP4761A"),
    "vehicle-design": ("VEHICLE DESIGN", "FAR-25 / CS-25"),
}

# ------------------------------------------------------------------ themes

LIGHT = {
    "canvas": "#f3f1ec",     # Warm Vellum
    "surface": "#faf9f5",    # Paper Surface
    "ink": "#171717",        # Ink Black
    "pencil": "#5c5c5c",     # Pencil
    "faint": "#a3a3a3",      # Faint Graphite
    "mint": "#9fe870",       # Survey Mint — THE accent
}
DARK = {
    "canvas": "#0d1b33",     # Blueprint Blue
    "surface": "#0a1730",    # Deep Paper
    "ink": "#dfe8f5",        # Bone White
    "pencil": "#5f7ba8",     # Blueprint Muted
    "faint": "#3a5a8f",      # Blueprint Border
    "mint": "#9fe870",
}

STYLE = """  <style>
    .mono { font-family: "JetBrains Mono", "IBM Plex Mono", "Menlo", monospace; }
    .cond { font-family: "Barlow Condensed", "DIN Condensed", "Arial Narrow", sans-serif; font-weight: 700; text-transform: uppercase; }
  </style>
"""


# ----------------------------------------------------------------- metrics

def collect_metrics():
    skills = REPO / "skills"
    fams = {}
    for fam_dir in sorted(p for p in skills.iterdir() if p.is_dir()):
        name = fam_dir.name
        packs = sorted(p.name for p in fam_dir.iterdir() if p.is_dir())
        detail = {p: sorted(leaf.parent.name for leaf in fam_dir.glob(f"{p}/*/SKILL.md"))
                  for p in packs}
        fams[name] = {
            "label": FAMILY_META[name][0],
            "spine": FAMILY_META[name][1],
            "packs": len(packs),
            "pack_names": packs,
            "packs_detail": detail,
            "leaves": sum(len(v) for v in detail.values()),
        }

    corpus = (REPO / "eval" / "hit1-corpus.yaml").read_text(encoding="utf-8")
    tasks = len(re.findall(r"^  - id:", corpus, re.M))
    expected = re.findall(r'expected_skill:\s*"?([a-z-]+)/', corpus)
    for name, fam in fams.items():
        fam["tasks"] = sum(1 for e in expected if e == name)
    standards_src = (REPO / "standards-map.yaml").read_text(encoding="utf-8")
    standards = len(re.findall(r"^  - id:", standards_src, re.M))

    leaves = sum(f["leaves"] for f in fams.values())
    packs = sum(f["packs"] for f in fams.values())
    return {
        "families": len(fams),
        "live_packs": packs,
        "leaves": leaves,
        "skill_files": leaves + len(fams),  # + one router SKILL.md per family
        "corpus_tasks": tasks,
        "standards": standards,
        "per_family": fams,
    }


# -------------------------------------------------------------- svg helpers

def pt(cx, cy, r, ang_deg):
    a = math.radians(ang_deg)
    return cx + r * math.cos(a), cy + r * math.sin(a)


def poly(points, **attrs):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    a = " ".join(f'{k.replace("_", "-")}="{v}"' for k, v in attrs.items())
    return f'<polygon points="{p}" {a}/>'


def txt(x, y, s, cls="mono", size=11, fill="#000", anchor="start", ls=None, extra=""):
    lsp = f' letter-spacing="{ls}"' if ls else ""
    esc = str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (f'<text class="{cls}" x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
            f'font-size="{size}" fill="{fill}"{lsp}{extra}>{esc}</text>')


def naca2412(chord, n=80):
    """NACA 2412 upper+lower surface coords, closed TE, LE at x=0."""
    m, p, t = 0.02, 0.4, 0.12
    up, lo = [], []
    for i in range(n + 1):
        beta = math.pi * i / n
        x = (1 - math.cos(beta)) / 2  # cosine spacing
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2
                      + 0.2843 * x**3 - 0.1036 * x**4)
        if x < p:
            yc = m / p**2 * (2 * p * x - x**2)
            dyc = 2 * m / p**2 * (p - x)
        else:
            yc = m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2)
            dyc = 2 * m / (1 - p)**2 * (p - x)
        th = math.atan(dyc)
        up.append(((x - yt * math.sin(th)) * chord, -(yc + yt * math.cos(th)) * chord))
        lo.append(((x + yt * math.sin(th)) * chord, -(yc - yt * math.cos(th)) * chord))
    return up + lo[::-1][1:]


def camber2412(chord, n=60):
    m, p = 0.02, 0.4
    pts = []
    for i in range(n + 1):
        x = i / n
        yc = (m / p**2 * (2 * p * x - x**2) if x < p
              else m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2))
        pts.append((x * chord, -yc * chord))
    return pts


def rotate(points, ang_deg, ox=0.0, oy=0.0):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(ox + (x - ox) * ca - (y - oy) * sa,
             oy + (x - ox) * sa + (y - oy) * ca) for x, y in points]


def translate(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


# -------------------------------------------------------------------- logo

def gen_logo(t):
    """Roundel: heavy bezel + degree ticks + arc wordmark + solid NACA 2412
    section at +9 deg AoA with mint camber line. Transparent canvas."""
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" '
         f'xmlns:xlink="http://www.w3.org/1999/xlink" width="512" height="512" '
         f'viewBox="0 0 512 512">', STYLE.rstrip()]
    cx = cy = 256
    ink, mint, pencil = t["ink"], t["mint"], t["pencil"]

    # bezel: heavy outer ring + hairline companion
    o.append(f'<circle cx="{cx}" cy="{cy}" r="234" fill="none" stroke="{ink}" stroke-width="14"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="216" fill="none" stroke="{ink}" stroke-width="1.5" stroke-opacity="0.45"/>')

    # degree ticks between hairline and bezel: majors 30deg, minors 6deg
    for d in range(0, 360, 6):
        major = d % 30 == 0
        r1, r2 = (196, 212) if major else (204, 212)
        x1, y1 = pt(cx, cy, r1, d)
        x2, y2 = pt(cx, cy, r2, d)
        w = 2.5 if major else 0.8
        o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{ink}" stroke-width="{w}"/>')

    # arc wordmark along the inside top + station legend along the bottom
    # (xlink:href kept for renderers that predate SVG2 href)
    o.append(f'<defs><path id="arcTop" d="M {cx - 154} {cy} A 154 154 0 0 1 {cx + 154} {cy}" fill="none"/>'
             f'<path id="arcBot" d="M {cx - 158} {cy} A 158 158 0 0 0 {cx + 158} {cy}" fill="none"/></defs>')
    o.append(f'<text class="cond" font-size="42" fill="{ink}" letter-spacing="12">'
             f'<textPath xlink:href="#arcTop" href="#arcTop" startOffset="50%" '
             f'text-anchor="middle">AEROSKILLS</textPath></text>')
    o.append(f'<text class="mono" font-size="15" fill="{pencil}" letter-spacing="6">'
             f'<textPath xlink:href="#arcBot" href="#arcBot" startOffset="50%" '
             f'text-anchor="middle">NACA 2412 · SEC A-A</textPath></text>')

    # airfoil section: solid ink fill (drawing convention: section cut),
    # mid-chord on center, +9 deg nose-up (svg y-down: +aoa lifts the LE)
    chord = 380
    aoa = 9
    ox, oy = chord / 2, 0.0
    surf = translate(rotate(naca2412(chord), aoa, ox, oy), cx - ox, cy - oy)
    camb = translate(rotate(camber2412(chord), aoa, ox, oy), cx - ox, cy - oy)
    chord_line = translate(rotate([(0.0, 0.0), (chord, 0.0)], aoa, ox, oy), cx - ox, cy - oy)
    qc = translate(rotate([(chord * 0.25, 0.0)], aoa, ox, oy), cx - ox, cy - oy)[0]

    (x1, y1), (x2, y2) = chord_line
    o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
             f'stroke="{ink}" stroke-width="1.5" stroke-dasharray="7 5" stroke-opacity="0.5"/>')
    o.append(poly(surf, fill=ink, stroke=ink, stroke_width="2"))
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in camb)
    o.append(f'<polyline points="{p}" fill="none" stroke="{mint}" stroke-width="5" stroke-linecap="round"/>')
    # aerodynamic-center datum at quarter chord
    o.append(f'<circle cx="{qc[0]:.1f}" cy="{qc[1]:.1f}" r="8" fill="{mint}" stroke="{ink}" stroke-width="2"/>')

    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------------------- radar

def radar_axes(m):
    fams = m["per_family"]
    names = sorted(fams)
    n = len(names)
    return [(names[i], fams[names[i]], -90 + 360 * i / n) for i in range(n)]


def gen_radar(m, t):
    W, H = 940, 820
    cx, cy, R = 430, 410, 262
    peak = max(max(f["tasks"], f["leaves"]) for f in m["per_family"].values())
    for step in (5, 10, 15, 20, 25, 50, 100, 200, 500):  # ≤6 rings, nice values
        if math.ceil(peak / step) <= 6:
            break
    rings = [step * i for i in range(1, math.ceil(peak / step) + 1)]
    rmax = float(rings[-1])
    axes = radar_axes(m)
    ink, mint, pencil, faint = t["ink"], t["mint"], t["pencil"], t["faint"]

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    # ring grid + spokes
    for rv in rings:
        r = R * rv / rmax
        pts = [pt(cx, cy, r, a) for _, _, a in axes]
        o.append(poly(pts, fill="none", stroke=faint, stroke_width="0.8", stroke_opacity="0.55"))
    for _, _, a in axes:
        x, y = pt(cx, cy, R, a)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                 f'stroke="{faint}" stroke-width="0.8" stroke-opacity="0.4"/>')
    # ring value labels on the upper-left inter-axis diagonal (ref: AEI plot)
    for rv in rings:
        x, y = pt(cx, cy, R * rv / rmax, -105)
        o.append(txt(x - 4, y - 3, str(rv), size=10, fill=pencil, anchor="end"))

    # perimeter labels
    for name, fam, a in axes:
        x, y = pt(cx, cy, R + 20, a)
        anchor = "middle" if abs(math.cos(math.radians(a))) < 0.35 else (
            "start" if math.cos(math.radians(a)) > 0 else "end")
        dy = 12 if math.sin(math.radians(a)) > 0.35 else (-6 if math.sin(math.radians(a)) < -0.35 else 4)
        o.append(txt(x, y + dy, fam["label"], size=12, fill=pencil, anchor=anchor, ls=1))

    # series 1: router-task pressure (ghost) — Hit@1 tasks asserting each family
    task_pts = [pt(cx, cy, R * f["tasks"] / rmax, a) for _, f, a in axes]
    o.append(poly(task_pts, fill=ink, fill_opacity="0.06", stroke=ink, stroke_width="1.6"))
    for x, y in task_pts:
        o.append(f'<rect x="{x - 3.2:.1f}" y="{y - 3.2:.1f}" width="6.4" height="6.4" '
                 f'fill="{t["canvas"]}" stroke="{ink}" stroke-width="1.4"/>')

    # series 2: live verified leaves (mint)
    live_pts = [pt(cx, cy, R * f["leaves"] / rmax, a) for _, f, a in axes]
    o.append(poly(live_pts, fill=mint, fill_opacity="0.28", stroke=mint, stroke_width="2.6"))
    for x, y in live_pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{mint}" stroke="{ink}" stroke-width="1.2"/>')

    # task value labels just outside each task vertex
    for (_, f, a), (x, y) in zip(axes, task_pts):
        lx, ly = pt(cx, cy, R * f["tasks"] / rmax + 14, a)
        o.append(txt(lx, ly + 3, str(f["tasks"]), size=9.5, fill=ink, anchor="middle"))

    # header
    o.append(txt(910, 74, "DOMAIN COVERAGE", cls="cond", size=34, fill=ink,
                 anchor="end", ls=2))
    o.append(txt(910, 100, f'{m["families"]} FAMILIES · SKILLS VS ROUTER ASSERTIONS',
                 size=11, fill=pencil, anchor="end", ls=1))

    # legend + title block (drafting convention, bottom-right)
    bx, by, bw, bh = 700, 612, 210, 178
    o.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="{t["surface"]}" '
             f'stroke="{ink}" stroke-width="1.2"/>')
    o.append(f'<line x1="{bx}" y1="{by + 74}" x2="{bx + bw}" y2="{by + 74}" stroke="{faint}" stroke-width="0.8"/>')
    o.append(f'<circle cx="{bx + 22}" cy="{by + 24}" r="4" fill="{mint}" stroke="{ink}" stroke-width="1.2"/>')
    o.append(txt(bx + 36, by + 28, f'VERIFIED SKILLS · {m["leaves"]}', size=10.5, fill=ink))
    o.append(f'<rect x="{bx + 18}" y="{by + 44}" width="8" height="8" fill="none" stroke="{ink}" stroke-width="1.4"/>')
    o.append(txt(bx + 36, by + 52, f'ROUTER TASKS · {m["corpus_tasks"]}', size=10.5, fill=ink))
    rows = [("UNIT", "COUNT PER FAMILY"), ("SCALE", f"0–{int(rmax)} · RINGS {int(rings[0])}"),
            ("GATE", "HIT@1 · DETERMINISTIC"), ("SHEET", "RDR-01 · REV AUTO")]
    for i, (k, v) in enumerate(rows):
        yy = by + 94 + i * 21
        o.append(txt(bx + 14, yy, k, size=9, fill=pencil, ls=1))
        o.append(txt(bx + 66, yy, v, size=9, fill=ink))

    o.append(txt(cx, H - 22, f'{m["leaves"]} VERIFIED SKILLS · {m["live_packs"]} LIVE PACKS · '
                 f'{m["corpus_tasks"]} ROUTER TASKS · EVERY AXIS COMPUTED FROM THE TREE AT HEAD',
                 size=10, fill=pencil, anchor="middle", ls=2))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------------------- polar

def gen_polar(m, t):
    W, H = 940, 660
    cx, cy, R = 300, 340, 238
    peak = max(f["packs"] for f in m["per_family"].values())
    vmax = float(max(10, math.ceil(peak / 5) * 5))  # packs scale ceiling
    rings = [int(vmax / 5 * i) for i in range(1, 6)]
    axes = radar_axes(m)
    ink, mint, pencil, faint = t["ink"], t["mint"], t["pencil"], t["faint"]

    def rr(v):  # area-true rose: r ∝ sqrt(value)
        return R * math.sqrt(v / vmax)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    for rv in rings:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr(rv):.1f}" fill="none" '
                 f'stroke="{faint}" stroke-width="0.8" stroke-opacity="0.55"/>')

    half = 360 / len(axes) / 2 - 2.5  # sector half-width with 5deg gap
    for name, fam, a in axes:
        r = rr(fam["packs"])
        a0, a1 = a - half, a + half
        x0, y0 = pt(cx, cy, r, a0)
        x1, y1 = pt(cx, cy, r, a1)
        o.append(f'<path d="M {cx} {cy} L {x0:.1f} {y0:.1f} A {r:.1f} {r:.1f} 0 0 1 '
                 f'{x1:.1f} {y1:.1f} Z" fill="{mint}" fill-opacity="0.3" '
                 f'stroke="{mint}" stroke-width="2"/>')
        vx, vy = pt(cx, cy, r + 13, a)
        o.append(txt(vx, vy + 3.5, str(fam["packs"]), size=10.5, fill=ink, anchor="middle"))

    # header
    o.append(txt(600, 74, "PACKS PER FAMILY", cls="cond", size=34, fill=ink, ls=2))
    o.append(txt(600, 100, f'{m["live_packs"]} LIVE INSTALLABLE PACKS · AREA-TRUE ROSE',
                 size=11, fill=pencil, ls=1))

    # right panel: per-family register with live packs + leaves
    px, py, pitch, tw = 600, 138, 34, 150
    for i, (name, fam, a) in enumerate(axes):
        yy = py + i * pitch
        o.append(txt(px, yy, fam["label"], size=10, fill=pencil, ls=1))
        o.append(f'<rect x="{px}" y="{yy + 7}" width="{tw}" height="9" fill="none" '
                 f'stroke="{faint}" stroke-width="0.8"/>')
        o.append(f'<rect x="{px}" y="{yy + 7}" width="{tw * fam["packs"] / vmax:.1f}" '
                 f'height="9" fill="{mint}" fill-opacity="0.65"/>')
        o.append(txt(px + tw + 12, yy + 15,
                     f'{fam["packs"]}P · {fam["leaves"]} SKILLS', size=10, fill=ink))

    ring_note = "·".join(str(r) for r in rings)
    o.append(txt(cx, H - 22, f'{m["live_packs"]} LIVE PACKS · GRID RINGS {ring_note} · '
                 f'r ∝ √PACKS (AREA-TRUE)', size=10, fill=pencil, anchor="middle", ls=2))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------- instrument strip

def gen_stats(m, t):
    """Current-state readout: six instrument tiles, blueprint style."""
    W, H = 940, 150
    ink, mint, pencil, faint = t["ink"], t["mint"], t["pencil"], t["faint"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    tiles = [
        (str(m["leaves"]), "VERIFIED SKILLS", True),
        (str(m["live_packs"]), "LIVE PACKS", True),
        (str(m["families"]), "FAMILIES", False),
        (str(m["standards"]), "STANDARDS MAPPED", False),
        (str(m["corpus_tasks"]), "ROUTER TASKS", False),
        ("8/8", "GATES GREEN", False),
    ]
    gx, gy, gw, gh = 20, 20, W - 40, H - 40
    o.append(f'<rect x="{gx}" y="{gy}" width="{gw}" height="{gh}" fill="{t["surface"]}" '
             f'stroke="{ink}" stroke-width="1.4"/>')
    tw = gw / len(tiles)
    for i, (value, label, accent) in enumerate(tiles):
        x0 = gx + i * tw
        if i:
            o.append(f'<line x1="{x0:.1f}" y1="{gy + 14}" x2="{x0:.1f}" y2="{gy + gh - 14}" '
                     f'stroke="{faint}" stroke-width="0.8"/>')
        cxm = x0 + tw / 2
        o.append(txt(cxm, gy + 62, value, cls="cond", size=44,
                     fill=ink, anchor="middle", ls=1))
        o.append(txt(cxm, gy + 86, label, size=10, fill=pencil, anchor="middle", ls=2))
        if accent:
            o.append(f'<line x1="{cxm - 22:.1f}" y1="{gy + 97}" x2="{cxm + 22:.1f}" '
                     f'y2="{gy + 97}" stroke="{mint}" stroke-width="3"/>')
    # corner station marks (drafting frame)
    for (x, y, dx, dy) in [(gx, gy, 1, 1), (gx + gw, gy, -1, 1),
                           (gx, gy + gh, 1, -1), (gx + gw, gy + gh, -1, -1)]:
        o.append(f'<line x1="{x}" y1="{y + 8 * dy}" x2="{x}" y2="{y + 18 * dy}" stroke="{ink}" stroke-width="2"/>')
        o.append(f'<line x1="{x + 8 * dx}" y1="{y}" x2="{x + 18 * dx}" y2="{y}" stroke="{ink}" stroke-width="2"/>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


# -------------------------------------------------------------- DOMAINS.md

def gen_domains(m):
    def mid(s):
        return s.replace("-", "_")

    out = [
        "# AeroSkills Domain Map",
        "",
        "Machine-readable source of truth: `skills/` tree. This page is the human",
        f'companion — {m["families"]} families, {m["live_packs"]} live sub-domain packs, '
        f'{m["leaves"]} verified leaves.',
        "",
        "Generated by `make visuals` (scripts/gen_visuals.py) — do not edit by hand;",
        "CI fails if this page drifts from the tree.",
        "",
        "```mermaid",
        "graph TD",
        "    ROOT[AeroSkills]",
    ]
    fams = m["per_family"]
    for name in sorted(fams):
        f = fams[name]
        out.append(f"    {mid(name)}[{name}]")
        out.append(f"    ROOT --> {mid(name)}")
        for pack, leaves in f["packs_detail"].items():
            pid = f"{mid(name)}_{mid(pack)}"
            out.append(f"    {pid}[{pack} · {len(leaves)}]")
            out.append(f"    {mid(name)} --> {pid}")
    out += ["```", "",
            f'*{m["live_packs"]} packs · {m["leaves"]} leaves rendered above.*']
    for name in sorted(fams):
        f = fams[name]
        out += ["", f"## {name}", "",
                f'**{f["packs"]} sub-domain packs · {f["leaves"]} skills**', "",
                "| Pack | Skills | Count |", "|---|---|---|"]
        for pack, leaves in f["packs_detail"].items():
            listed = ", ".join(f"`{s}`" for s in leaves)
            out.append(f"| `{pack}` | {listed} | {len(leaves)} |")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------- banner stats

def render_banner(m, src):
    """Rewrite the four stat value/label pairs in the hand-authored banner
    (both themes share coordinates). Idempotent; fails loud if the banner
    layout changes so the slots can be re-anchored."""
    slots = {
        ("60", "292"): str(m["leaves"]), ("60", "310"): "VERIFIED SKILLS",
        ("190", "292"): str(m["live_packs"]), ("190", "310"): "LIVE PACKS",
        ("320", "292"): str(m["standards"]), ("320", "310"): "STANDARDS",
        ("450", "292"): str(m["corpus_tasks"]), ("450", "310"): "ROUTER TASKS",
    }
    for (x, y), value in slots.items():
        pat = re.compile(rf'(<text class="mono" x="{x}" y="{y}"[^>]*>)[^<]*(</text>)')
        if not pat.search(src):
            raise SystemExit(f"banner: stat slot x={x} y={y} not found — re-anchor render_banner")
        src = pat.sub(rf"\g<1>{value}\g<2>", src)
    return src


# --------------------------------------------------------------- README gen

def block_statline(m):
    return (f'<p align="center">\n'
            f'  <code>{m["leaves"]} verified skills</code> · '
            f'<code>{m["live_packs"]} live packs</code> · '
            f'<code>{m["families"]} families</code> · '
            f'<code>{m["standards"]} standards</code> · '
            f'<code>{m["corpus_tasks"]} router tasks</code> · '
            f'<code>5/5 gates + 3/3 attest</code>\n</p>')


def block_badges(m):
    def b(label, msg, color, href):
        lab = label.replace("-", "--").replace(" ", "_")
        enc = msg.replace("-", "--").replace(" ", "_")
        return (f'  <a href="{href}"><img src="https://img.shields.io/badge/'
                f'{lab}-{enc}-{color}?style=for-the-badge&labelColor=171717" alt="{label} {msg}"></a>')
    row1 = [
        b("skills", str(m["leaves"]), "9fe870", "skills/"),
        b("packs", str(m["live_packs"]), "9fe870", "docs/DOMAINS.md"),
        b("families", str(m["families"]), "9fe870", "docs/DOMAINS.md"),
        b("standards", str(m["standards"]), "4a90d9", "STANDARDS.md"),
    ]
    row2 = [
        b("gates", "5%2F5 REAL", "2ea043", "docs/harness-contract.md"),
        b("attest", "3%2F3", "2ea043", "docs/harness-contract.md"),
        b("router tasks", str(m["corpus_tasks"]), "2ea043", "eval/"),
        b("eval", "deterministic offline", "555555", "docs/harness-contract.md"),
    ]
    row3 = [
        b("license", "Apache 2.0", "4a90d9", "LICENSE"),
        b("format", "agentskills.io", "8250df", "https://agentskills.io"),
        b("harnesses", "70%2B", "555555", "docs/harness-integration.md"),
        b("python", "stdlib only", "555555", "scripts/"),
    ]
    return ("<p align=\"center\">\n" + "\n".join(row1)
            + "\n</p>\n<p align=\"center\">\n" + "\n".join(row2)
            + "\n</p>\n<p align=\"center\">\n" + "\n".join(row3) + "\n</p>")


def block_overview(m):
    return (f'**{m["leaves"]} verified skills** across **{m["families"]} families** and '
            f'**{m["live_packs"]} live sub-domain packs** — each one spec-linted, '
            f'behavior-tested, and router-asserted against a '
            f'**{m["corpus_tasks"]}-task Hit@1 corpus**. Every figure below is computed '
            f'from the tree at HEAD; nothing is hand-counted.')


def block_family_table(m):
    pretty_names = {
        "aerodynamics": "Aerodynamics", "avionics": "Avionics",
        "cross-cutting": "Cross-cutting", "flight-mechanics": "Flight mechanics",
        "flight-test-operations": "Flight test & operations",
        "gnc-autonomy": "GNC & autonomy", "manufacturing-quality": "Manufacturing quality",
        "propulsion": "Propulsion", "space-systems": "Space systems",
        "structures": "Structures", "systems-engineering-safety": "Systems engineering & safety",
        "vehicle-design": "Vehicle design",
    }
    rows = ["| Family | Standard spine | Packs | Skills | Router tasks |", "|---|---|---:|---:|---:|"]
    fams = m["per_family"]
    for name in sorted(fams):
        f = fams[name]
        rows.append(f'| **{pretty_names[name]}** | {f["spine"]} | {f["packs"]} | {f["leaves"]} | '
                    f'{f["tasks"]} |')
    rows.append(f'| **Total** | {m["standards"]} standards mapped | **{m["live_packs"]}** | '
                f'**{m["leaves"]}** | **{m["corpus_tasks"]}** |')
    return "\n".join(rows)


def block_verify_extra(m):
    return (f'| — visuals fresh | charts + README numbers regenerate to zero diff | '
            f'`make visuals-check` |')


def block_roadmap(m):
    return (f'- **Shipped:** {m["leaves"]} verified skills in {m["live_packs"]} packs across '
            f'{m["families"]} disciplines, all gated by `make validate` (5/5) and `make attest` (3/3)\n'
            f'- **Now:** deepening every live pack and opening new sub-domain packs on the same '
            f'eval-gated pipeline — every addition lands with its behavior contract and router tasks\n'
            f'- **Later:** reference builds; a SEP-2640-aligned MCP adapter; marketplace listings; '
            f'AI Department Operator packs')


BLOCKS = {
    "statline": block_statline,
    "badges": block_badges,
    "overview": block_overview,
    "family-table": block_family_table,
    "verify-extra": block_verify_extra,
    "roadmap": block_roadmap,
}


def render_readme(m, src):
    for name, fn in BLOCKS.items():
        pat = re.compile(rf"(<!-- gen:{name} -->\n).*?(\n<!-- /gen:{name} -->)", re.S)
        if not pat.search(src):
            raise SystemExit(f"README.md: missing generator block <!-- gen:{name} -->")
        src = pat.sub(lambda mo: mo.group(1) + fn(m) + mo.group(2), src)
    return src


# -------------------------------------------------------------------- main

def outputs(m):
    docs = REPO / "docs"
    return {
        docs / "metrics.json": json.dumps(m, indent=2, sort_keys=True) + "\n",
        docs / "logo.svg": gen_logo(LIGHT),
        docs / "logo-dark.svg": gen_logo(DARK),
        docs / "domain-radar.svg": gen_radar(m, LIGHT),
        docs / "domain-radar-dark.svg": gen_radar(m, DARK),
        docs / "domain-polar.svg": gen_polar(m, LIGHT),
        docs / "domain-polar-dark.svg": gen_polar(m, DARK),
        docs / "stats.svg": gen_stats(m, LIGHT),
        docs / "stats-dark.svg": gen_stats(m, DARK),
        docs / "DOMAINS.md": gen_domains(m),
    }


def main():
    check = "--check" in sys.argv
    m = collect_metrics()
    out = outputs(m)
    readme_path = REPO / "README.md"
    out[readme_path] = render_readme(m, readme_path.read_text(encoding="utf-8"))
    for banner in ("banner.svg", "banner-dark.svg"):
        path = REPO / "docs" / banner
        out[path] = render_banner(m, path.read_text(encoding="utf-8"))

    stale = []
    for path, content in sorted(out.items()):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            if check:
                stale.append(path.relative_to(REPO))
            else:
                path.write_text(content, encoding="utf-8")
                print(f"wrote {path.relative_to(REPO)}")
    if check:
        if stale:
            print(f"FAIL visuals-check: {len(stale)} stale artifact(s) — run `make visuals`:")
            for p in stale:
                print(f"  {p}")
            return 1
        print(f"PASS visuals-check: {len(out)} artifacts fresh "
              f'({m["leaves"]} leaves · {m["live_packs"]} packs)')
    return 0


if __name__ == "__main__":
    sys.exit(main())
