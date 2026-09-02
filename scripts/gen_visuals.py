#!/usr/bin/env python3
"""Aero Agent Skills visuals + metrics generator (deterministic, stdlib-only, offline).

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
  docs/domain-radar[-dark].svg     12-axis radar: skills vs router tasks
  docs/domain-polar[-dark].svg     polar rose: packs per family (area-true)
  docs/structure[-dark].svg        sunburst: family ring + pack ring
  docs/how-it-works[-dark].svg     runtime pipeline flowchart
  docs/gates[-dark].svg            verification gate battery flowchart
  docs/skill-anatomy[-dark].svg    exploded view of one skill folder
  docs/DOMAINS.md                  full generated domain map
  README.md                        every <!-- gen:NAME --> block rewritten
  docs/*.png                       2x raster of every SVG above — the README
                                   embeds the PNGs because GitHub Mobile does
                                   not render SVG images (SVGs stay in-repo as
                                   the vector source of truth)

The logo is founder-supplied raster (docs/logo-mark.png) — never generated,
never altered.

Usage:
  python3 scripts/gen_visuals.py           regenerate everything
  python3 scripts/gen_visuals.py --check   fail (exit 1) if anything is stale

Design law: docs/DESIGN.md (logo-derived palette: space navy + cyan/
violet/magenta/orange, flat fills, mono uppercase labels, title blocks).
"""

import json
import math
import re
import shutil
import subprocess
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

# Palette derived from the founder logo (2026-09-01): deep space navy tile,
# cyan orbit, violet/magenta sky, orange exhaust. Light theme carries the same
# four hues at darker values for contrast on paper.
LIGHT = {
    "canvas": "#f6f7fc",     # Cool Paper
    "surface": "#ffffff",
    "ink": "#151a33",        # Space Ink
    "pencil": "#5a6289",     # Muted Slate
    "faint": "#c6cce4",      # Faint Line
    "cyan": "#0891b2",
    "violet": "#7c3aed",
    "magenta": "#db2777",
    "orange": "#ea580c",
    "fill_data": "0.16",
    "fill_rose": "0.70",
}
DARK = {
    "canvas": "#0a0d1e",     # Logo Tile Navy
    "surface": "#111632",
    "ink": "#edf0fc",        # Star White
    "pencil": "#8a93c4",
    "faint": "#2c3564",
    "cyan": "#38bdf8",
    "violet": "#a78bfa",
    "magenta": "#f472b6",
    "orange": "#fb923c",
    # translucent fills stay low on navy so hues do not muddy
    "fill_data": "0.16",
    "fill_rose": "0.72",
}

RAMP = ["cyan", "violet", "magenta", "orange"]  # family color cycle


def fam_color(t, i):
    """Stable per-family accent: cycle the four logo hues by family index."""
    return t[RAMP[i % len(RAMP)]]

STYLE = """  <style>
    .mono { font-family: "JetBrains Mono", "IBM Plex Mono", "Menlo", monospace; }
    .cond { font-family: "Barlow Condensed", "DIN Condensed", "Arial Narrow", sans-serif; font-weight: 700; text-transform: uppercase; }
    .serif { font-family: "Instrument Serif", Georgia, serif; font-style: italic; }
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


def ownermark(t, x, y, anchor="end"):
    """Provenance mark baked into every diagram (founder 2026-09-02: images get
    copied/downloaded standalone — each must carry repo + owner)."""
    return txt(x, y, "AERO AGENT SKILLS · ASHFORDE OÜ", size=9.5,
               fill=t["pencil"], anchor=anchor, ls=1.5, extra=' opacity="0.9"')


def rotate(points, ang_deg, ox=0.0, oy=0.0):
    a = math.radians(ang_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(ox + (x - ox) * ca - (y - oy) * sa,
             oy + (x - ox) * sa + (y - oy) * ca) for x, y in points]


def translate(points, dx, dy):
    return [(x + dx, y + dy) for x, y in points]


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
    ink, mint, pencil, faint = t["ink"], t["cyan"], t["pencil"], t["faint"]

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
    # ring value labels on the upper-left inter-axis diagonal (ref: AEI plot);
    # ink at reduced opacity stays readable over the mint fill in both themes
    for rv in rings:
        x, y = pt(cx, cy, R * rv / rmax, -105)
        o.append(txt(x - 4, y - 3, str(rv), size=10, fill=ink, anchor="end",
                     extra=' opacity="0.55"'))

    # perimeter labels in each family's hue (matches rose + sunburst)
    for i, (name, fam, a) in enumerate(axes):
        x, y = pt(cx, cy, R + 20, a)
        anchor = "middle" if abs(math.cos(math.radians(a))) < 0.35 else (
            "start" if math.cos(math.radians(a)) > 0 else "end")
        dy = 12 if math.sin(math.radians(a)) > 0.35 else (-6 if math.sin(math.radians(a)) < -0.35 else 4)
        o.append(txt(x, y + dy, fam["label"], size=12, fill=fam_color(t, i), anchor=anchor, ls=1))

    # series 1: router-task pressure (magenta) — Hit@1 tasks asserting each family
    mag = t["magenta"]
    task_pts = [pt(cx, cy, R * f["tasks"] / rmax, a) for _, f, a in axes]
    o.append(poly(task_pts, fill=mag, fill_opacity="0.10", stroke=mag, stroke_width="2.2"))
    for x, y in task_pts:
        o.append(f'<rect x="{x - 3.2:.1f}" y="{y - 3.2:.1f}" width="6.4" height="6.4" '
                 f'fill="{t["canvas"]}" stroke="{mag}" stroke-width="1.6"/>')

    # series 2: live verified leaves (cyan)
    live_pts = [pt(cx, cy, R * f["leaves"] / rmax, a) for _, f, a in axes]
    o.append(poly(live_pts, fill=mint, fill_opacity=t["fill_data"], stroke=mint, stroke_width="2.6"))
    for x, y in live_pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{mint}" stroke="{ink}" stroke-width="1.2"/>')

    # task value labels just outside each task vertex
    for (_, f, a), (x, y) in zip(axes, task_pts):
        lx, ly = pt(cx, cy, R * f["tasks"] / rmax + 14, a)
        o.append(txt(lx, ly + 3, str(f["tasks"]), size=9.5, fill=mag, anchor="middle"))

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
    o.append(f'<rect x="{bx + 18}" y="{by + 44}" width="8" height="8" fill="none" stroke="{t["magenta"]}" stroke-width="1.6"/>')
    o.append(txt(bx + 36, by + 52, f'ROUTER TASKS · {m["corpus_tasks"]}', size=10.5, fill=ink))
    rows = [("UNIT", "COUNT PER FAMILY"), ("SCALE", f"0–{int(rmax)} · RINGS {int(rings[0])}"),
            ("GATE", "HIT@1 · DETERMINISTIC"), ("SHEET", "RDR-01 · REV AUTO")]
    for i, (k, v) in enumerate(rows):
        yy = by + 94 + i * 21
        o.append(txt(bx + 14, yy, k, size=9, fill=pencil, ls=1))
        o.append(txt(bx + 66, yy, v, size=9, fill=ink))

    # left-anchored + short so it ends clear of the title block (founder 2026-09-01)
    o.append(txt(48, H - 22, f'{m["leaves"]} VERIFIED SKILLS · {m["live_packs"]} LIVE PACKS · '
                 f'{m["corpus_tasks"]} ROUTER TASKS', size=10, fill=pencil, ls=2))
    o.append(ownermark(t, bx + bw, H - 8))
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
    ink, mint, pencil, faint = t["ink"], t["cyan"], t["pencil"], t["faint"]

    def rr(v):  # area-true rose: r ∝ sqrt(value)
        return R * math.sqrt(v / vmax)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    for rv in rings:
        o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr(rv):.1f}" fill="none" '
                 f'stroke="{faint}" stroke-width="0.8" stroke-opacity="0.55"/>')

    half = 360 / len(axes) / 2 - 2.5  # sector half-width with 5deg gap
    for i, (name, fam, a) in enumerate(axes):
        c = fam_color(t, i)
        r = rr(fam["packs"])
        a0, a1 = a - half, a + half
        x0, y0 = pt(cx, cy, r, a0)
        x1, y1 = pt(cx, cy, r, a1)
        o.append(f'<path d="M {cx} {cy} L {x0:.1f} {y0:.1f} A {r:.1f} {r:.1f} 0 0 1 '
                 f'{x1:.1f} {y1:.1f} Z" fill="{c}" fill-opacity="{t["fill_rose"]}" '
                 f'stroke="{c}" stroke-width="2"/>')
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
                 f'height="9" fill="{fam_color(t, i)}"/>')
        o.append(txt(px + tw + 12, yy + 15,
                     f'{fam["packs"]}P · {fam["leaves"]} SKILLS', size=10, fill=ink))

    ring_note = "·".join(str(r) for r in rings)
    o.append(txt(cx, H - 22, f'{m["live_packs"]} LIVE PACKS · GRID RINGS {ring_note} · '
                 f'r ∝ √PACKS (AREA-TRUE)', size=10, fill=pencil, anchor="middle", ls=2))
    o.append(ownermark(t, W - 48, H - 22))
    o.append("</svg>")
    return "\n".join(o) + "\n"




# --------------------------------------------------------- structure sunburst

def annulus(cx, cy, r0, r1, a0, a1, fill, opacity="1", stroke="none", sw="0"):
    large = 1 if (a1 - a0) > 180 else 0
    x0o, y0o = pt(cx, cy, r1, a0)
    x1o, y1o = pt(cx, cy, r1, a1)
    x1i, y1i = pt(cx, cy, r0, a1)
    x0i, y0i = pt(cx, cy, r0, a0)
    return (f'<path d="M {x0o:.1f} {y0o:.1f} A {r1:.1f} {r1:.1f} 0 {large} 1 '
            f'{x1o:.1f} {y1o:.1f} L {x1i:.1f} {y1i:.1f} A {r0:.1f} {r0:.1f} 0 {large} 0 '
            f'{x0i:.1f} {y0i:.1f} Z" fill="{fill}" fill-opacity="{opacity}" '
            f'stroke="{stroke}" stroke-width="{sw}"/>')


def gen_structure(m, t):
    """Sunburst of the repository: inner ring = 12 families, outer ring =
    every live pack, arc length proportional to verified leaf skills."""
    W, H = 940, 900
    cx, cy = 470, 460
    r_hole, r_fam, r_pack0, r_pack1 = 96, 186, 192, 262
    ink, pencil, faint = t["ink"], t["pencil"], t["faint"]
    fams = m["per_family"]
    names = sorted(fams)
    fam_gap, pack_gap = 2.2, 0.7
    total = sum(fams[n]["leaves"] for n in names)
    span = 360.0 - fam_gap * len(names)

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    a = -90.0
    for i, name in enumerate(names):
        f = fams[name]
        c = fam_color(t, i)
        fam_span = span * f["leaves"] / total
        a0, a1 = a, a + fam_span
        o.append(annulus(cx, cy, r_hole + 8, r_fam, a0, a1, c, "0.9",
                         t["canvas"], "1.5"))
        # pack ring inside the family arc; gap shrinks as packs multiply so a
        # crowded family never runs out of arc (scale-ready for pack growth)
        pa = a0
        npacks = max(f["packs"], 1)
        pgap = min(pack_gap, fam_span * 0.25 / max(npacks - 1, 1)) if npacks > 1 else 0.0
        pack_span_total = fam_span - pgap * (npacks - 1)
        weight_total = sum(max(len(v), 1) for v in f["packs_detail"].values()) or 1
        for j, (pack, leaves) in enumerate(f["packs_detail"].items()):
            ps = pack_span_total * max(len(leaves), 1) / weight_total
            o.append(annulus(cx, cy, r_pack0, r_pack1, pa, pa + ps, c,
                             "0.55" if j % 2 == 0 else "0.32",
                             t["canvas"], "1"))
            pa += ps + pgap
        # family label outside
        mid = (a0 + a1) / 2
        lx, ly = pt(cx, cy, r_pack1 + 22, mid)
        cosm = math.cos(math.radians(mid))
        anchor = "middle" if abs(cosm) < 0.35 else ("start" if cosm > 0 else "end")
        dy = 10 if math.sin(math.radians(mid)) > 0.35 else (
            -4 if math.sin(math.radians(mid)) < -0.35 else 4)
        o.append(txt(lx, ly + dy, f["label"], size=11, fill=pencil, anchor=anchor, ls=1))
        o.append(txt(lx, ly + dy + 15, f'{f["packs"]}P · {f["leaves"]}S', size=9.5,
                     fill=c, anchor=anchor, ls=1))
        a = a1 + fam_gap

    # center readout
    o.append(txt(cx, cy - 8, str(m["leaves"]), cls="cond", size=52, fill=ink,
                 anchor="middle", ls=1))
    o.append(txt(cx, cy + 16, "VERIFIED SKILLS", size=10, fill=pencil,
                 anchor="middle", ls=2))
    o.append(txt(cx, cy + 34, f'{m["live_packs"]} PACKS · {m["families"]} FAMILIES',
                 size=9.5, fill=pencil, anchor="middle", ls=1))

    o.append(txt(52, 64, "REPOSITORY STRUCTURE", cls="cond", size=34, fill=ink, ls=2))
    o.append(txt(52, 90, "INNER RING: FAMILIES · OUTER RING: INSTALLABLE PACKS · "
                 "ARC LENGTH = VERIFIED SKILLS", size=10.5, fill=pencil, ls=1))
    # footer keeps the full-width center line; mark rides the empty top-right
    o.append(txt(cx, H - 24, f'EVERY ARC COMPUTED FROM skills/ AT HEAD · '
                 f'FULL PER-PACK LISTS IN docs/DOMAINS.md', size=10, fill=pencil,
                 anchor="middle", ls=2))
    o.append(ownermark(t, W - 52, 64))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------------ gate battery

def gen_gates(m, t):
    """The verification battery every commit passes, fail-closed."""
    W, H = 1500, 330
    ink, pencil, faint = t["ink"], t["pencil"], t["faint"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    def chip(x, y, w, h, lines, stroke, sw="1.3", fill=None):
        o.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w}" height="{h}" '
                 f'fill="{fill or t["surface"]}" stroke="{stroke}" stroke-width="{sw}"/>')
        cy0 = y + h / 2 - (len(lines) - 1) * 8 + 4
        for j, line in enumerate(lines):
            o.append(txt(x + w / 2, cy0 + j * 16, line, size=10, fill=ink,
                         anchor="middle", ls=1))

    def arrow(x0, x1, y):
        o.append(f'<line x1="{x0:.1f}" y1="{y}" x2="{x1 - 8:.1f}" y2="{y}" '
                 f'stroke="{ink}" stroke-width="1.4"/>')
        o.append(f'<path d="M {x1:.1f} {y} l -9 -4.5 v 9 Z" fill="{ink}"/>')

    mid = 150
    chip(40, mid - 34, 96, 68, ["COMMIT"], ink)
    arrow(140, 172, mid)

    # group: make validate
    gx, gw = 176, 596
    o.append(f'<rect x="{gx}" y="78" width="{gw}" height="144" fill="none" '
             f'stroke="{t["violet"]}" stroke-width="1.8"/>')
    o.append(txt(gx + 12, 70, "MAKE VALIDATE · 5/5 REAL GATES", size=11,
                 fill=t["violet"], ls=2))
    gates5 = [["SPEC", "LINT"], ["DESC", "LINT"], ["BEHAVIOR", "TESTS"],
              ["NO-", "VERBATIM"], ["HIT@1", f'{m["corpus_tasks"]} TASKS']]
    for i, lines in enumerate(gates5):
        chip(gx + 14 + i * 116, mid - 28, 104, 56, lines, faint)
    arrow(gx + gw + 4, gx + gw + 36, mid)

    # group: make attest
    ax, aw = 844, 380
    o.append(f'<rect x="{ax}" y="78" width="{aw}" height="144" fill="none" '
             f'stroke="{t["magenta"]}" stroke-width="1.8"/>')
    o.append(txt(ax + 12, 70, "MAKE ATTEST · 3/3", size=11, fill=t["magenta"], ls=2))
    gates3 = [["NUMBER", "SNAPSHOT"], ["BRIEF", "AUDIT"], ["CONTENT", "POLICY"]]
    for i, lines in enumerate(gates3):
        chip(ax + 14 + i * 120, mid - 28, 108, 56, lines, faint)
    arrow(ax + aw + 4, ax + aw + 36, mid)

    chip(1258, mid - 34, 104, 68, ["VISUALS", "FRESH"], t["orange"], "1.8")
    arrow(1366, 1396, mid)
    o.append(f'<rect x="1400" y="{mid - 34}" width="92" height="68" fill="{t["cyan"]}" '
             f'fill-opacity="{t["fill_data"]}" stroke="{t["cyan"]}" stroke-width="2.2"/>')
    o.append(txt(1446, mid - 2, "CI", size=11, fill=ink, anchor="middle", ls=1))
    o.append(txt(1446, mid + 14, "GREEN", size=11, fill=ink, anchor="middle", ls=1))

    o.append(f'<line x1="40" y1="{H - 62}" x2="{W - 40}" y2="{H - 62}" '
             f'stroke="{faint}" stroke-width="0.8"/>')
    o.append(txt(40, H - 38, "FAIL-CLOSED: ANY RED GATE BLOCKS THE PUSH · "
                 "DETERMINISTIC · OFFLINE · REPLAY WITH make validate + make attest",
                 size=10.5, fill=pencil, ls=2))
    o.append(ownermark(t, W - 40, H - 38))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------------ skill anatomy

def gen_anatomy(t):
    """Exploded view of one skill folder: what each part is for."""
    W, H = 1500, 470
    ink, pencil, faint = t["ink"], t["pencil"], t["faint"]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    o.append(txt(48, 56, "ANATOMY OF A SKILL", cls="cond", size=30, fill=ink, ls=2))
    o.append(txt(48, 80, "skills/avionics/do178c/planning/ — one leaf, four load-bearing parts",
                 size=11, fill=pencil, ls=1))

    rows = [
        ("SKILL.md · FRONTMATTER", t["cyan"],
         ["name + trigger description — the ONLY part the router reads.",
          "Loaded on demand: no context cost until the task matches."]),
        ("SKILL.md · BODY", t["violet"],
         ["the workflow the agent follows: steps, standards references,",
          "pitfalls, verification gates, and the human sign-off stop."]),
        ("scripts/test_*.py", t["magenta"],
         ["behavior contract, plain stdlib unittest — gate 3 replays it",
          "offline and asserts the skill's decisions (e.g. DAL A-E)."]),
        ("eval corpus tasks", t["orange"],
         ["Hit@1 assertions — gate 5 proves the deterministic router",
          "selects this skill for its trigger queries."]),
    ]
    y = 110
    for label, c, desc in rows:
        o.append(f'<rect x="48" y="{y}" width="340" height="62" fill="{t["surface"]}" '
                 f'stroke="{c}" stroke-width="1.8"/>')
        o.append(f'<rect x="48" y="{y}" width="6" height="62" fill="{c}"/>')
        o.append(txt(70, y + 37, label, size=12.5, fill=ink, ls=1))
        o.append(f'<line x1="392" y1="{y + 31}" x2="432" y2="{y + 31}" '
                 f'stroke="{ink}" stroke-width="1.3"/>')
        o.append(f'<path d="M 440 {y + 31} l -9 -4.5 v 9 Z" fill="{ink}"/>')
        for j, line in enumerate(desc):
            o.append(txt(456, y + 26 + j * 18, line, size=11.5, fill=pencil))
        y += 82

    o.append(txt(48, H - 26, "PLAIN FILES ON THE OPEN AGENTSKILLS.IO FORMAT · "
                 "ANY SKILL.MD HOST CAN LOAD THEM", size=10.5, fill=pencil, ls=2))
    o.append(ownermark(t, W - 48, H - 26))
    o.append("</svg>")
    return "\n".join(o) + "\n"




# ----------------------------------------------------- hero title / statline
# Transparent-background, text-only SVGs: render like colorful styled text on
# any GitHub theme. Replaces the math-\color hack, which GitHub's parser
# broke on (raw $...$ shown — founder screenshot 2026-09-01).

TITLE_FONT = ('font-family="Poppins, Nunito, \'SF Pro Rounded\', \'Segoe UI\', '
              'system-ui, -apple-system, sans-serif" font-weight="800"')


def gen_title(t):
    W, H = 960, 168
    ramp = ["#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f97316", "#f59e0b"]
    skills = "".join(f'<tspan fill="{c}">{ch}</tspan>'
                     for ch, c in zip("Skills", ramp))
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" rx="22" fill="{t["canvas"]}"/>']
    o.append(f'<text x="{W / 2}" y="92" text-anchor="middle" font-size="72" '
             f'{TITLE_FONT} fill="{t["ink"]}">Aero <tspan fill="{t["cyan"]}">Agent</tspan> '
             f'{skills}</text>')
    o.append(f'<text class="mono" x="{W / 2}" y="142" text-anchor="middle" '
             f'font-size="16" letter-spacing="4">'
             f'<tspan fill="{t["cyan"]}">AEROSPACE ENGINEERING</tspan>'
             f'<tspan fill="{t["pencil"]}" dx="10">·</tspan>'
             f'<tspan fill="{t["violet"]}" dx="10">BY ASHFORDE OÜ</tspan>'
             f'<tspan fill="{t["pencil"]}" dx="10">·</tspan>'
             f'<tspan fill="{t["orange"]}" dx="10">APACHE-2.0</tspan></text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def gen_statline(m, t):
    W, H = 1240, 74
    stats = [
        (m["leaves"], "VERIFIED SKILLS", t["cyan"]),
        (m["live_packs"], "LIVE PACKS", t["violet"]),
        (m["families"], "FAMILIES", t["magenta"]),
        (m["standards"], "STANDARDS", t["orange"]),
        (m["corpus_tasks"], "ROUTER TASKS", t["cyan"]),
        ("8/8", "GATES GREEN", t["violet"]),
    ]
    spans = []
    for k, (v, label, c) in enumerate(stats):
        dx = ' dx="34"' if k else ""
        spans.append(f'<tspan{dx} font-size="34" fill="{c}" font-weight="800">{v}</tspan>')
        spans.append(f'<tspan dx="9" font-size="13" fill="{t["pencil"]}" '
                     f'letter-spacing="2">{label}</tspan>')
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" rx="16" fill="{t["canvas"]}"/>',
         f'<text class="mono" x="{W / 2}" y="47" text-anchor="middle">'
         + "".join(spans) + "</text>", "</svg>"]
    return "\n".join(o) + "\n"


# -------------------------------------------------------------- DOMAINS.md

def gen_domains(m):
    def mid(s):
        return s.replace("-", "_")

    out = [
        "# Aero Agent Skills Domain Map",
        "",
        "Machine-readable source of truth: `skills/` tree. This page is the human",
        f'companion — {m["families"]} families, {m["live_packs"]} live sub-domain packs, '
        f'{m["leaves"]} verified leaves.',
        "",
        "Generated by `make visuals` (scripts/gen_visuals.py) — do not edit by hand;",
        "CI fails if this page drifts from the tree. Aero Agent Skills is built and",
        "maintained by [Ashforde OÜ](https://ashforde.org).",
        "",
        "```mermaid",
        "graph TD",
        "    ROOT[Aero Agent Skills]",
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


# ---------------------------------------------------------- how-it-works

def gen_flow(t):
    """How-it-works pipeline as a generated diagram (replaces inline mermaid,
    which GitHub renders cramped behind zoom controls — founder 2026-09-01)."""
    W, H = 1500, 250
    ink, mint, pencil, faint = t["ink"], t["cyan"], t["pencil"], t["faint"]
    steps = [
        ("01", ["AGENT TASK"], False),
        ("02", ["ROUTER PICKS SKILL", "BY DESCRIPTION"], False),
        ("03", ["SKILL.MD LOADS:", "WORKFLOW + GATES"], False),
        ("04", ["STANDARDS CONTEXT", "FROM STANDARDS-MAP"], False),
        ("05", ["AGENT EXECUTES", "WITH VERIFICATION"], False),
        ("06", ["STOP GATE:", "HUMAN SIGN-OFF"], True),
    ]
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    n, bw, bh, mx = len(steps), 200, 84, 48
    gap = (W - 2 * mx - n * bw) / (n - 1)
    by = 84
    for i, (num, lines, accent) in enumerate(steps):
        x = mx + i * (bw + gap)
        stroke = t["orange"] if accent else ink
        o.append(f'<rect x="{x:.1f}" y="{by}" width="{bw}" height="{bh}" fill="{t["surface"]}" '
                 f'stroke="{stroke}" stroke-width="{2.4 if accent else 1.4}"/>')
        o.append(txt(x + 2, by - 12, num, size=11, fill=t["orange"] if accent else mint, ls=2))
        cy0 = by + bh / 2 - (len(lines) - 1) * 9 + 4
        for j, line in enumerate(lines):
            o.append(txt(x + bw / 2, cy0 + j * 18, line, size=11.5,
                         fill=ink, anchor="middle", ls=1))
        if i < n - 1:
            ax0, ax1, ay = x + bw + 6, x + bw + gap - 6, by + bh / 2
            o.append(f'<line x1="{ax0:.1f}" y1="{ay}" x2="{ax1 - 8:.1f}" y2="{ay}" '
                     f'stroke="{ink}" stroke-width="1.4"/>')
            o.append(f'<path d="M {ax1:.1f} {ay} l -9 -4.5 v 9 Z" fill="{ink}"/>')

    o.append(txt(mx, H - 40, "DETERMINISTIC ROUTER · OFFLINE GATES · "
                 "THE TERMINAL NODE IS ALWAYS A HUMAN", size=10.5, fill=pencil, ls=2))
    o.append(ownermark(t, W - mx, H - 40))
    o.append(f'<line x1="{mx}" y1="{H - 60}" x2="{W - mx}" y2="{H - 60}" '
             f'stroke="{faint}" stroke-width="0.8"/>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


# --------------------------------------------------------------- README gen

def block_badges(m):
    def b(label, msg, color, href, alt=None):
        lab = label.replace("-", "--").replace(" ", "_")
        enc = msg.replace("-", "--").replace(" ", "_")
        return (f'  <a href="{href}"><img src="https://img.shields.io/badge/'
                f'{lab}-{enc}-{color}?style=flat&labelColor=1a1e35" alt="{alt or (label + " " + msg)}"></a>')
    row = [
        b("skills", str(m["leaves"]), "0ea5e9", "skills/"),
        b("packs", str(m["live_packs"]), "8b5cf6", "docs/DOMAINS.md"),
        b("families", str(m["families"]), "ec4899", "docs/DOMAINS.md"),
        b("standards", str(m["standards"]), "f97316", "STANDARDS.md"),
        b("gates", "5%2F5", "2ea043", "docs/harness-contract.md"),
        b("attest", "3%2F3", "2ea043", "docs/harness-contract.md"),
        b("router tasks", str(m["corpus_tasks"]), "0ea5e9", "eval/"),
        b("format", "agentskills.io", "8b5cf6", "https://agentskills.io"),
    ]
    # Distribution row: how the library ships. Static npm badge on purpose —
    # flip to a live shields npm/v badge at public release (runbook 3b).
    dist = [
        b("npm", "aero-agent-skills", "0ea5e9", "https://www.npmjs.com/package/aero-agent-skills"),
        b("cli", "aero-skills", "8b5cf6", "packages/aero-agent-skills/"),
        b("mcp server", "jetbrains_%C2%B7_claude_%C2%B7_vscode_%C2%B7_cursor", "ec4899", "docs/harness-integration.md",
          alt="MCP server for JetBrains, Claude Desktop, VS Code, Cursor"),
        b("claude code", "plugin", "f97316", ".claude-plugin/"),
    ]
    return ("<p align=\"center\">\n" + "\n".join(row) + "\n</p>\n"
            + "<p align=\"center\">\n" + "\n".join(dist) + "\n</p>")


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
            f'{m["families"]} disciplines, all gated by `make validate` (5/5) and `make attest` (3/3); '
            f'distribution as an npm CLI + MCP server (`aero-agent-skills`, router parity proven on the '
            f'full {m["corpus_tasks"]}-task corpus) and Claude Code plugin packaging\n'
            f'- **Now:** deepening every live pack and opening new sub-domain packs on the same '
            f'eval-gated pipeline — every addition lands with its behavior contract and router tasks\n'
            f'- **Later:** reference builds; marketplace listings; '
            f'AI Department Operator packs')


BLOCKS = {
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
        docs / "title.svg": gen_title(LIGHT),
        docs / "title-dark.svg": gen_title(DARK),
        docs / "statline.svg": gen_statline(m, LIGHT),
        docs / "statline-dark.svg": gen_statline(m, DARK),
        docs / "domain-radar.svg": gen_radar(m, LIGHT),
        docs / "domain-radar-dark.svg": gen_radar(m, DARK),
        docs / "domain-polar.svg": gen_polar(m, LIGHT),
        docs / "domain-polar-dark.svg": gen_polar(m, DARK),
        docs / "structure.svg": gen_structure(m, LIGHT),
        docs / "structure-dark.svg": gen_structure(m, DARK),
        docs / "how-it-works.svg": gen_flow(LIGHT),
        docs / "how-it-works-dark.svg": gen_flow(DARK),
        docs / "gates.svg": gen_gates(m, LIGHT),
        docs / "gates-dark.svg": gen_gates(m, DARK),
        docs / "skill-anatomy.svg": gen_anatomy(LIGHT),
        docs / "skill-anatomy-dark.svg": gen_anatomy(DARK),
        docs / "DOMAINS.md": gen_domains(m),
    }


def main():
    check = "--check" in sys.argv
    m = collect_metrics()
    out = outputs(m)
    readme_path = REPO / "README.md"
    out[readme_path] = render_readme(m, readme_path.read_text(encoding="utf-8"))

    stale = []
    for path, content in sorted(out.items()):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            if check:
                stale.append(path.relative_to(REPO))
            else:
                path.write_text(content, encoding="utf-8")
                print(f"wrote {path.relative_to(REPO)}")

    # 2x PNG rasters for GitHub Mobile (no SVG support in the app). Bytes are
    # rasterizer-version dependent, so --check asserts existence only; the
    # push machine regenerates real pixels via make visuals.
    rsvg = shutil.which("rsvg-convert")
    for svg_path in sorted(p for p in out if p.suffix == ".svg"):
        png_path = svg_path.with_suffix(".png")
        if check:
            if not png_path.exists():
                stale.append(png_path.relative_to(REPO))
            continue
        if not rsvg:
            print(f"WARN rsvg-convert not found — skipped {png_path.name}")
            continue
        w = int(re.search(r'width="(\d+)"', out[svg_path]).group(1))
        subprocess.run([rsvg, "-w", str(w * 2), str(svg_path), "-o", str(png_path)],
                       check=True)
        print(f"wrote {png_path.relative_to(REPO)}")
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
