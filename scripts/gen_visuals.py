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
  gate battery     Makefile                                 (the prerequisite
                   lists of the `validate:` and `attest:` targets — read,
                   never edited, see collect_gates)

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
  python3 scripts/gen_visuals.py --selftest  unit-test the gate-battery
                                          derivation (stdlib unittest)

Design law: docs/DESIGN.md (logo-derived palette: space navy + cyan/
violet/magenta/orange, flat fills, mono uppercase labels, title blocks).
"""

import json
import math
import re
import hashlib
import os
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

# small cardinals, so a spelled-out count in a caption is still computed
NUMWORD = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six",
           7: "seven", 8: "eight", 9: "nine", 10: "ten", 11: "eleven",
           12: "twelve"}

# ------------------------------------------------------------- gate battery
# The size of the verification battery used to be TYPED in this file — "8/8
# gates green" in the statline, a gates-5/5 shields badge, "MAKE VALIDATE ·
# 5/5 REAL GATES" on the chart, "(5/5)" in the roadmap — while `make
# validate` had grown to nine prerequisites. `make visuals-check` could not
# see it: a constant regenerates to itself, so the one figure README.md
# swears is computed was the one figure nobody was computing.
#
# Both counts now come from the Makefile's prerequisite lists at generation
# time. Same definition ops/automation/numbers.yaml registers for its
# validate_gates / attest_gates denominators, but evaluated independently
# here (the register grades this generator; it must not be its input).
MAKEFILE = REPO / "Makefile"

# Chip captions for the gate-battery diagram. Editorial, exactly as
# FAMILY_META's labels are editorial — the COUNT never is. A target with no
# entry still renders: the fallback splits the Makefile target name, so a
# gate wired into `validate:` shows up on the chart without touching this
# file (that is the whole point of reading the Makefile).
GATE_CHIP_LABELS = {
    "lint-spec": ("SPEC", "LINT"),
    "desc-lint": ("DESC", "LINT"),
    "pytest-contract": ("BEHAVIOR", "TESTS"),
    "no-verbatim": ("NO-", "VERBATIM"),
    "hit1": ("HIT@1", None),  # None = second line is the live corpus count
    "independence": ("VERIFY", "INDEPENDENCE"),
    "release-law": ("RELEASE", "LAW"),
    "portability": ("PORT-", "ABILITY"),
    "corpus-naming": ("CORPUS", "NAMING"),
    "number-snapshot-offline": ("NUMBER", "SNAPSHOT"),
    "brief-audit": ("BRIEF", "AUDIT"),
    "content-policy-sweep": ("CONTENT", "POLICY"),
}


def collect_gates():
    """Gate names + counts, read from the Makefile's validate/attest targets.

    Line continuations are folded first so a prerequisite list broken over
    several lines is still one list. `.PHONY: validate ...` cannot match:
    the target name has to start the line.
    """
    src = re.sub(r"\\\n", " ", MAKEFILE.read_text(encoding="utf-8"))
    found = {}
    for target in ("validate", "attest"):
        mo = re.search(rf"^{target}[ \t]*:(?!=)([^\n]*)", src, re.M)
        if mo is None:
            raise SystemExit(f"Makefile: no `{target}:` target — the gate count "
                             f"cannot be derived and will not be typed")
        names = mo.group(1).split("#", 1)[0].split()
        if not names:
            raise SystemExit(f"Makefile: `{target}:` has no prerequisites — "
                             f"refusing to print an empty battery")
        found[target] = names
    return {
        "validate": found["validate"],
        "validate_count": len(found["validate"]),
        "attest": found["attest"],
        "attest_count": len(found["attest"]),
    }


def grp(v):
    """Comma-group an integer for display: 3189 -> "3,189".

    Non-integers pass through untouched, so a value that is already a rendered
    string (gate_ratio returns "16/16") is safe to wrap. Display only -- never
    wrap a value that is about to be used in arithmetic.
    """
    return "{:,}".format(v) if isinstance(v, int) else v


def gate_ratio(g, which="validate"):
    """"9/9" — the battery is green as a whole or it is not green at all."""
    n = g[f"{which}_count"]
    return f"{n}/{n}"


def gate_badge_msg(g, which="validate"):
    """Same ratio, shields.io-encoded (%2F is a literal slash in a message)."""
    n = g[f"{which}_count"]
    return f"{n}%2F{n}"


def gate_ordinal(g, target, fallback):
    """"gate 3" — the position the gate actually holds in `validate:`."""
    try:
        return f"gate {g['validate'].index(target) + 1}"
    except ValueError:
        return fallback


def gate_chip_lines(target, m):
    label = GATE_CHIP_LABELS.get(target)
    if label is None:
        head, _, tail = target.upper().replace("_", "-").partition("-")
        return [head, tail] if tail else [head]
    top, bottom = label
    if bottom is None:
        bottom = f'{grp(m["router_cases"])} CASES'
    return [top, bottom]


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

# The Ashforde OÜ corporate seal, vendored verbatim from the founder's brand
# system (ashforde-site/assets/brand/seal-mono-white.svg — a 512x512 mono
# mark meant for dark grounds) as docs/ashforde-seal.svg. This is the
# COMPANY mark, distinct from docs/logo-mark.png (the Aero Agent Skills
# paper-plane PRODUCT emblem) — founder 2026-09-02, correcting a card that
# had locked the product mark up with "ASHFORDE OÜ" and called it the logo.
#
# LAZY on purpose: docs/ashforde-seal.svg is marketing-only and excluded
# from the public-tree allowlist (release-runbook-ashforde.md 3b), so this
# module must still import cleanly in a public checkout where the file is
# legitimately absent. Its presence is also how outputs() below decides
# whether it is running in dev (generate the social card + launch post) or
# in the exported public tree (skip them, don't fail).
_ASHFORDE_SEAL_SVG_CACHE = None


def ashforde_seal_available():
    return (REPO / "docs" / "ashforde-seal.svg").exists()


def ashforde_seal_svg():
    global _ASHFORDE_SEAL_SVG_CACHE
    if _ASHFORDE_SEAL_SVG_CACHE is None:
        src = (REPO / "docs" / "ashforde-seal.svg").read_text(encoding="utf-8")
        _ASHFORDE_SEAL_SVG_CACHE = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", src.strip())
    return _ASHFORDE_SEAL_SVG_CACHE


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
    # 2026-09-19: this counted `^  - id:` over the WHOLE file, so a future_pins
    # entry counted as a router task (1755 vs 1754). It was only ever correct
    # because the pin was malformed and its id had leaked to the document root;
    # repairing the pin exposed the off-by-one. Count the tasks block only.
    _tasks_block = re.search(r"^tasks:\s*$(.*?)(?=^\w|\Z)", corpus, re.M | re.S)
    tasks = len(re.findall(r"^  - id:", _tasks_block.group(1), re.M)) if _tasks_block else 0
    expected = re.findall(r'expected_skill:\s*"?([a-z-]+)/', corpus)
    # Gate 5 executes the whole eval directory, so the per-family split and
    # the total have to be taken over the whole directory too -- a table whose
    # rows come from one file and whose total comes from all of them does not
    # add up, and the reader cannot tell which figure is wrong.
    frag_cases = 0
    for path in sorted((REPO / "eval").glob("hit1-*.yaml")):
        if path.name == "hit1-corpus.yaml":
            continue
        text = path.read_text(encoding="utf-8")
        frag_cases += len(re.findall(r"^  - id:", text, re.M))
        expected += re.findall(r'expected_skill:\s*"?([a-z-]+)/', text)
    router_cases = tasks + frag_cases
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
        "router_cases": router_cases,
        "standards": standards,
        # the battery that gates all of the above, sized from the Makefile
        "gates": collect_gates(),
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

    # Log radius, not linear. One family carries ~50x the leaves of the next,
    # so a linear axis puts the other eleven inside 2% of the radius -- a knot
    # at the centre with the value labels printed on top of each other. The
    # chart then shows only that space-systems is large, and hides the
    # relative coverage it exists to show.
    #
    # RADAR_FLOOR is one decade below the smallest family, so the smallest
    # value has a visible radius instead of sitting on the origin.
    RADAR_FLOOR = 10.0
    rmax = float(peak)
    _lo, _hi = math.log10(RADAR_FLOOR), math.log10(rmax)

    def radial(value):
        """Radius in px for a count, on the declared log scale."""
        v = max(float(value), RADAR_FLOOR)
        return R * (math.log10(v) - _lo) / (_hi - _lo)

    # Decade and half-decade rings, only those inside the data range.
    rings = [r for r in (10, 50, 100, 500, 1000, 5000) if r <= rmax]
    axes = radar_axes(m)
    ink, mint, pencil, faint = t["ink"], t["cyan"], t["pencil"], t["faint"]

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    # ring grid + spokes
    for rv in rings:
        r = radial(rv)
        pts = [pt(cx, cy, r, a) for _, _, a in axes]
        o.append(poly(pts, fill="none", stroke=faint, stroke_width="0.8", stroke_opacity="0.55"))
    for _, _, a in axes:
        x, y = pt(cx, cy, R, a)
        o.append(f'<line x1="{cx}" y1="{cy}" x2="{x:.1f}" y2="{y:.1f}" '
                 f'stroke="{faint}" stroke-width="0.8" stroke-opacity="0.4"/>')
    # ring value labels on the upper-left inter-axis diagonal (ref: AEI plot);
    # ink at reduced opacity stays readable over the mint fill in both themes
    for rv in rings:
        x, y = pt(cx, cy, radial(rv), -105)
        o.append(txt(x - 4, y - 3, grp(rv), size=10, fill=ink, anchor="end",
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
    task_pts = [pt(cx, cy, radial(f["tasks"]), a) for _, f, a in axes]
    o.append(poly(task_pts, fill=mag, fill_opacity="0.10", stroke=mag, stroke_width="2.2"))
    for x, y in task_pts:
        o.append(f'<rect x="{x - 3.2:.1f}" y="{y - 3.2:.1f}" width="6.4" height="6.4" '
                 f'fill="{t["canvas"]}" stroke="{mag}" stroke-width="1.6"/>')

    # series 2: live verified leaves (cyan)
    live_pts = [pt(cx, cy, radial(f["leaves"]), a) for _, f, a in axes]
    o.append(poly(live_pts, fill=mint, fill_opacity=t["fill_data"], stroke=mint, stroke_width="2.6"))
    for x, y in live_pts:
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.6" fill="{mint}" stroke="{ink}" stroke-width="1.2"/>')

    # task value labels just outside each task vertex
    for (_, f, a), (x, y) in zip(axes, task_pts):
        lx, ly = pt(cx, cy, radial(f["tasks"]) + 14, a)
        o.append(txt(lx, ly + 3, grp(f["tasks"]), size=9.5, fill=mag, anchor="middle"))

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
    o.append(txt(bx + 36, by + 28, f'VERIFIED SKILLS · {grp(m["leaves"])}', size=10.5, fill=ink))
    o.append(f'<rect x="{bx + 18}" y="{by + 44}" width="8" height="8" fill="none" stroke="{t["magenta"]}" stroke-width="1.6"/>')
    o.append(txt(bx + 36, by + 52, f'ROUTER CASES · {grp(m["router_cases"])}', size=10.5, fill=ink))
    rows = [("UNIT", "COUNT PER FAMILY"), ("SCALE", f"LOG10 · {grp(int(RADAR_FLOOR))}–{grp(int(rmax))}"),
            ("GATE", "HIT@1 · DETERMINISTIC"), ("SHEET", "RDR-01 · REV AUTO")]
    for i, (k, v) in enumerate(rows):
        yy = by + 94 + i * 21
        o.append(txt(bx + 14, yy, k, size=9, fill=pencil, ls=1))
        o.append(txt(bx + 66, yy, v, size=9, fill=ink))

    # left-anchored + short so it ends clear of the title block (founder 2026-09-01)
    o.append(txt(48, H - 22, f'{grp(m["leaves"])} VERIFIED SKILLS · {grp(m["live_packs"])} LIVE PACKS · '
                 f'{grp(m["router_cases"])} ROUTER CASES', size=10, fill=pencil, ls=2))
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
                     f'{fam["packs"]}P · {grp(fam["leaves"])} SKILLS', size=10, fill=ink))

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
        o.append(txt(lx, ly + dy + 15, f'{f["packs"]}P · {grp(f["leaves"])}S', size=9.5,
                     fill=c, anchor=anchor, ls=1))
        a = a1 + fam_gap

    # center readout
    o.append(txt(cx, cy - 8, grp(m["leaves"]), cls="cond", size=52, fill=ink,
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
    """The verification battery every commit passes, fail-closed.

    Every chip, and both group headings, come from the Makefile's
    `validate:` / `attest:` prerequisite lists (collect_gates). Nothing
    about the battery is typed here: this chart used to announce "5/5 REAL
    GATES" over five chips while `make validate` ran nine, and no gate
    could see it, because a constant regenerates to itself.
    """
    g = m["gates"]
    ink, pencil, faint = t["ink"], t["pencil"], t["faint"]

    # Chip grid. A battery that grows gets TALLER, never unreadably wide:
    # the strip keeps its width so the README embed keeps its scale.
    per_row, cw, chh, cgx, cgy = 5, 104, 56, 12, 12
    pad_x, pad_top, pad_bot = 14, 30, 30

    def group_geom(n):
        cols = min(n, per_row)
        rows = math.ceil(n / cols)
        return (cols, rows,
                2 * pad_x + cols * cw + (cols - 1) * cgx,
                pad_top + rows * chh + (rows - 1) * cgy + pad_bot)

    vcols, vrows, gw, gh = group_geom(len(g["validate"]))
    acols, arows, aw, ah = group_geom(len(g["attest"]))

    top = 78
    hmax = max(gh, ah)
    mid = top + hmax // 2
    H = top + hmax + 108
    gx = 176                      # make validate group
    ax = gx + gw + 72             # make attest group
    vx = ax + aw + 34             # visuals-fresh chip
    cix = vx + 142                # CI verdict box
    W = cix + 100

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

    def group(bx, bw, bh, cols, heading, accent, names):
        by = mid - bh // 2
        o.append(f'<rect x="{bx}" y="{by}" width="{bw}" height="{bh}" fill="none" '
                 f'stroke="{accent}" stroke-width="1.8"/>')
        o.append(txt(bx + 12, by - 8, heading, size=11, fill=accent, ls=2))
        for i, target in enumerate(names):
            row, col = i // cols, i % cols
            in_row = min(cols, len(names) - row * cols)   # last row centers
            row_w = in_row * cw + (in_row - 1) * cgx
            chip(bx + (bw - row_w) / 2 + col * (cw + cgx),
                 by + pad_top + row * (chh + cgy),
                 cw, chh, gate_chip_lines(target, m), faint)

    chip(40, mid - 34, 96, 68, ["COMMIT"], ink)
    arrow(140, 172, mid)

    group(gx, gw, gh, vcols,
          f'MAKE VALIDATE · {gate_ratio(g)} REAL GATES', t["violet"], g["validate"])
    arrow(gx + gw + 4, gx + gw + 36, mid)

    group(ax, aw, ah, acols,
          f'MAKE ATTEST · {gate_ratio(g, "attest")}', t["magenta"], g["attest"])
    arrow(ax + aw + 4, ax + aw + 36, mid)

    chip(vx, mid - 34, 104, 68, ["VISUALS", "FRESH"], t["orange"], "1.8")
    arrow(vx + 108, vx + 138, mid)
    o.append(f'<rect x="{cix}" y="{mid - 34}" width="92" height="68" fill="{t["cyan"]}" '
             f'fill-opacity="{t["fill_data"]}" stroke="{t["cyan"]}" stroke-width="2.2"/>')
    o.append(txt(cix + 46, mid - 2, "CI", size=11, fill=ink, anchor="middle", ls=1))
    o.append(txt(cix + 46, mid + 14, "GREEN", size=11, fill=ink, anchor="middle", ls=1))

    o.append(f'<line x1="40" y1="{H - 62}" x2="{W - 40}" y2="{H - 62}" '
             f'stroke="{faint}" stroke-width="0.8"/>')
    o.append(txt(40, H - 38, "FAIL-CLOSED: ANY RED GATE BLOCKS THE PUSH · "
                 "DETERMINISTIC · OFFLINE · REPLAY WITH make validate + make attest",
                 size=10.5, fill=pencil, ls=2))
    o.append(ownermark(t, W - 40, H - 38))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------------ skill anatomy

def gen_anatomy(m, t):
    """Exploded view of one skill folder: what each part is for.

    The gate ordinals in the captions ("gate 3", "gate 5") are the
    positions those gates actually hold in the Makefile's `validate:`
    list, and the part count in the subtitle is len(rows) — neither is
    typed, so a reordered or renamed battery re-labels itself.
    """
    g = m["gates"]
    ink, pencil, faint = t["ink"], t["pencil"], t["faint"]

    rows = [
        ("SKILL.md · FRONTMATTER", t["cyan"],
         ["name + trigger description — the ONLY part the router reads.",
          "Loaded on demand: no context cost until the task matches."]),
        ("SKILL.md · BODY", t["violet"],
         ["the workflow the agent follows: steps, standards references,",
          "pitfalls, verification gates, and the human sign-off stop."]),
        ("scripts/test_*.py", t["magenta"],
         ["behavior contract, plain stdlib unittest — "
          f"{gate_ordinal(g, 'pytest-contract', 'the contract gate')} replays it",
          "offline and asserts the skill's decisions (e.g. DAL A-E)."]),
        ("eval corpus tasks", t["orange"],
         [f"Hit@1 assertions — {gate_ordinal(g, 'hit1', 'the Hit@1 gate')} "
          "proves the deterministic router",
          "selects this skill for its trigger queries."]),
    ]
    W, H = 1500, 110 + 82 * len(rows) + 32
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip(),
         f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>']

    o.append(txt(48, 56, "ANATOMY OF A SKILL", cls="cond", size=30, fill=ink, ls=2))
    o.append(txt(48, 80, "skills/avionics/do178c/planning/ — one leaf, "
                 f"{NUMWORD.get(len(rows), len(rows))} load-bearing parts",
                 size=11, fill=pencil, ls=1))

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


# Advance width of the monospace face as a fraction of font-size. Every
# monospace glyph is this wide, so a run's width is exactly computable.
MONO_ADVANCE = 0.62


def statline_text_width(stats):
    """Width in px of the centre-anchored run gen_statline is about to emit.

    Mirrors the span construction below: dx 34 between stats, the figure at
    font-size 34, dx 9, then the label at font-size 13 with 2px tracking.
    """
    run = 0.0
    for k, (value, label, _colour) in enumerate(stats):
        if k:
            run += 34
        run += len(str(value)) * 34 * MONO_ADVANCE
        run += 9
        run += len(label) * (13 * MONO_ADVANCE + 2)
    return run


def gen_statline(m, t):
    H = 74
    stats = [
        (grp(m["leaves"]), "VERIFIED SKILLS", t["cyan"]),
        (grp(m["live_packs"]), "LIVE PACKS", t["violet"]),
        (grp(m["families"]), "FAMILIES", t["magenta"]),
        (grp(m["standards"]), "STANDARDS", t["orange"]),
        (grp(m["router_cases"]), "ROUTER CASES", t["cyan"]),
        (gate_ratio(m["gates"]), "GATES GREEN", t["violet"]),
    ]
    # Never pin this: the figures grow. 1240 stays the floor so the banner
    # keeps its familiar proportions until the content genuinely needs more.
    W = max(1240, int(statline_text_width(stats)) + 64)
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


def ashforde_seal(x, y, size, opacity="1"):
    """The real Ashforde OÜ corporate seal (mono-white variant), sourced from
    the founder's brand system at ashforde-site/assets/brand/seal-mono-white.svg
    and vendored unaltered at docs/ashforde-seal.svg (founder 2026-09-02:
    the Aero Agent Skills paper-plane emblem is the PRODUCT mark, not
    Ashforde's own logo — do not lock the two together and call it
    "Ashforde's logo"). 512x512 viewBox, scaled+translated into place."""
    inner = ashforde_seal_svg()
    s = size / 512.0
    return f'<g transform="translate({x},{y}) scale({s:.5f})" opacity="{opacity}">{inner}</g>'


def gen_social(m, t):
    """LinkedIn/social hero card (1200x627, 1.91:1). MARKETING COLLATERAL —
    dev-repo only, never in the public-tree allowlist (founder 2026-09-02:
    "marketing and branding stuff can't be pushed to public repo" — see
    docs/release-runbook-ashforde.md 3b). Because it never ships in the
    public package it can carry more visual weight than the flat-fill
    README diagrams (docs/DESIGN.md's law governs those, not this).

    Rebuilt 2026-09-02 per founder review of the first draft: (1) the
    per-family bar chart was dead weight — every family is 27 or 28
    leaves, so bars carried no story — replaced with a real diagram (a
    compact two-ring sunburst, same construction as gen_structure) and
    the real how-it-works icon timeline (same icon set as the landing
    page); (2) the product logo (docs/logo-mark.png, the paper-plane
    emblem) was missing near the title — the README hero always leads
    with it, this card now does too; (3) the bottom-corner mark
    wrongly locked the PRODUCT logo up with "ASHFORDE OÜ", implying
    that emblem is Ashforde's own logo — it is not, it is Aero Agent
    Skills' mark. Fixed: the bottom corner now carries the founder's
    actual Ashforde seal (see ashforde_seal() above)."""
    import base64
    W, H = 1200, 900
    ramp = ["#8b5cf6", "#a855f7", "#d946ef", "#ec4899", "#f97316", "#f59e0b"]
    skills = "".join(f'<tspan fill="{c}">{ch}</tspan>'
                     for ch, c in zip("Skills", ramp))
    glow_id = "socialGlow"
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
         f'viewBox="0 0 {W} {H}">', STYLE.rstrip()]
    o.append(f'<defs><radialGradient id="{glow_id}" cx="50%" cy="0%" r="75%">'
              f'<stop offset="0%" stop-color="{t["cyan"]}" stop-opacity="0.16"/>'
              f'<stop offset="45%" stop-color="{t["violet"]}" stop-opacity="0.07"/>'
              f'<stop offset="100%" stop-color="{t["canvas"]}" stop-opacity="0"/>'
              f'</radialGradient></defs>')
    o.append(f'<rect width="{W}" height="{H}" fill="{t["canvas"]}"/>')
    o.append(f'<rect width="{W}" height="{H}" fill="url(#{glow_id})"/>')
    o.append(f'<circle cx="{W + 60}" cy="-40" r="380" fill="none" '
              f'stroke="{t["cyan"]}" stroke-opacity="0.10" stroke-width="2"/>')
    o.append(f'<circle cx="{W + 60}" cy="-40" r="300" fill="none" '
              f'stroke="{t["violet"]}" stroke-opacity="0.08" stroke-width="1.5"/>')

    # --- header: product logo above the title, mirroring the README hero.
    # Founder 2026-09-02: "we need this logo big on the social card" — up
    # from 46 to 130px, the card's dominant top-of-fold visual. ---
    logo_path = REPO / "docs" / "logo-mark.png"
    logo_b64 = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    hero_logo_sz = 130
    o.append(f'<image x="{W / 2 - hero_logo_sz / 2:.1f}" y="18" '
              f'width="{hero_logo_sz}" height="{hero_logo_sz}" '
              f'href="data:image/png;base64,{logo_b64}"/>')
    o.append(f'<text class="mono" x="{W / 2}" y="182" text-anchor="middle" '
              f'font-size="14" letter-spacing="3.5">'
              f'<tspan fill="{t["cyan"]}">AEROSPACE ENGINEERING</tspan>'
              f'<tspan fill="{t["pencil"]}" dx="8">·</tspan>'
              f'<tspan fill="{t["violet"]}" dx="8">BY ASHFORDE OÜ</tspan>'
              f'<tspan fill="{t["pencil"]}" dx="8">·</tspan>'
              f'<tspan fill="{t["orange"]}" dx="8">APACHE-2.0</tspan></text>')
    o.append(f'<text x="{W / 2}" y="244" text-anchor="middle" font-size="58" '
              f'{TITLE_FONT} fill="{t["ink"]}">Aero <tspan fill="{t["cyan"]}">Agent</tspan> '
              f'{skills}</text>')
    o.append(txt(W / 2, 274, "The aerospace knowledge layer for AI agents.",
                 size=16, fill=t["pencil"], anchor="middle"))

    # --- left: compact sunburst (same construction as gen_structure),
    # enlarged with real per-family labels — founder 2026-09-02: the first
    # cut had no family/domain labels and the pack-ring slivers were thin
    # enough to read as overlapping; both fixed by more radius + labels. ---
    fams = m["per_family"]
    names = sorted(fams)
    short = {
        "aerodynamics": "AERO", "avionics": "AVIONICS", "cross-cutting": "X-CUT",
        "flight-mechanics": "FLT MECH", "flight-test-operations": "FLT TEST",
        "gnc-autonomy": "GNC", "manufacturing-quality": "MFG QA",
        "propulsion": "PROPULSION", "space-systems": "SPACE",
        "structures": "STRUCTURES", "systems-engineering-safety": "SYS ENG",
        "vehicle-design": "VEHICLE",
    }
    cx, cy = 330, 490
    r_hole, r_fam, r_pack0, r_pack1 = 46, 78, 82, 128
    fam_gap = 2.8
    total = sum(fams[n]["leaves"] for n in names)
    span = 360.0 - fam_gap * len(names)
    a = -90.0
    for i, name in enumerate(names):
        f = fams[name]
        c = fam_color(t, i)
        fam_span = span * f["leaves"] / total
        a0, a1 = a, a + fam_span
        o.append(annulus(cx, cy, r_hole + 4, r_fam, a0, a1, c, "0.9", t["canvas"], "1.2"))
        pa = a0
        npacks = max(f["packs"], 1)
        pgap = min(1.1, fam_span * 0.25 / max(npacks - 1, 1)) if npacks > 1 else 0.0
        pack_span_total = fam_span - pgap * (npacks - 1)
        weight_total = sum(max(len(v), 1) for v in f["packs_detail"].values()) or 1
        for j, (pack, leaves) in enumerate(f["packs_detail"].items()):
            ps = pack_span_total * max(len(leaves), 1) / weight_total
            o.append(annulus(cx, cy, r_pack0, r_pack1, pa, pa + ps, c,
                             "0.55" if j % 2 == 0 else "0.32", t["canvas"], "0.8"))
            pa += ps + pgap
        mid = (a0 + a1) / 2
        lx, ly = pt(cx, cy, r_pack1 + 16, mid)
        cosm = math.cos(math.radians(mid))
        anchor = "middle" if abs(cosm) < 0.35 else ("start" if cosm > 0 else "end")
        dy = 4 if math.sin(math.radians(mid)) > 0.35 else (-2 if math.sin(math.radians(mid)) < -0.35 else 3)
        o.append(txt(lx, ly + dy, short.get(name, name.upper()), size=9, fill=c, anchor=anchor, ls=1))
        a = a1 + fam_gap
    o.append(txt(cx, cy - 6, grp(m["leaves"]), cls="cond", size=34, fill=t["ink"], anchor="middle", ls=1))
    o.append(txt(cx, cy + 17, "SKILLS", size=10, fill=t["pencil"], anchor="middle", ls=2))
    o.append(txt(cx, 328, "REPOSITORY STRUCTURE", size=12, fill=t["pencil"], anchor="middle", ls=2))
    o.append(txt(cx, 664, f'{m["live_packs"]} PACKS · {m["families"]} FAMILIES · ARC = SKILLS',
                 size=10, fill=t["pencil"], anchor="middle", ls=1))

    # --- right: stat chips, 2x3 grid (companion readout to the diagram) ---
    stats = [
        (grp(m["leaves"]), "VERIFIED SKILLS", t["cyan"]),
        (grp(m["live_packs"]), "LIVE PACKS", t["violet"]),
        (grp(m["families"]), "FAMILIES", t["magenta"]),
        (grp(m["standards"]), "STANDARDS", t["orange"]),
        (grp(m["router_cases"]), "ROUTER CASES", t["cyan"]),
        (gate_ratio(m["gates"]), "GATES GREEN", t["violet"]),
    ]
    gx0, gy0, chip_w, chip_h, ggap = 660, 428, 156, 56, 12
    for i, (v, label, c) in enumerate(stats):
        col, row = i % 3, i // 3
        gx = gx0 + col * (chip_w + ggap)
        gy = gy0 + row * (chip_h + ggap)
        o.append(f'<rect x="{gx}" y="{gy}" width="{chip_w}" height="{chip_h}" rx="10" '
                  f'fill="{c}" fill-opacity="0.12" stroke="{c}" stroke-opacity="0.4" stroke-width="1"/>')
        o.append(f'<text class="mono" x="{gx + 14}" y="{gy + 24}">'
                  f'<tspan font-size="21" font-weight="800" fill="{c}">{v}</tspan></text>')
        o.append(txt(gx + 14, gy + 42, label, size=9.5, fill=t["pencil"], anchor="start", ls=1.3))

    # --- full-width: how-it-works icon timeline (same icon set as the site) ---
    steps = [
        ("01", "AGENT TASK", '<path d="M4 6a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H9l-4 4v-4H6a2 2 0 0 1-2-2z"/><path d="M8 9h8M8 12.5h5"/>'),
        ("02", "ROUTER PICKS SKILL", '<path d="M4 12h6M14 12h6"/><path d="M10 12c2.5 0 2.5-6 5-6h5M10 12c2.5 0 2.5 6 5 6h5"/><path d="M17 3.5L20 6l-3 2.5M17 15.5L20 18l-3 2.5"/>'),
        ("03", "SKILL.MD LOADS", '<path d="M13.5 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z"/><path d="M13.5 3v5.5H19"/><path d="M9 13.5h6M9 17h4"/>'),
        ("04", "STANDARDS CONTEXT", '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15.5H6.5A2.5 2.5 0 0 0 4 21z"/><path d="M4 18.5A2.5 2.5 0 0 1 6.5 16H20"/><path d="M9 8h7M9 11.5h5"/>'),
        ("05", "AGENT EXECUTES", '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M12.5 15H17"/>'),
        ("06", "HUMAN SIGN-OFF", '<path d="M12 3l7 3v5c0 4.6-3 8.2-7 10-4-1.8-7-5.4-7-10V6z"/><path d="M12 8v4M12 15.5v.5"/>'),
    ]
    tl_caption_y, tl_y, tl_r, tl_x0, tl_x1 = 704, 759, 18, 110, 1090
    n = len(steps)
    step = (tl_x1 - tl_x0) / (n - 1)
    o.append(txt(tl_x0, tl_caption_y, "HOW IT WORKS · DETERMINISTIC ROUTER · THE TERMINAL NODE IS ALWAYS A HUMAN",
                 size=10.5, fill=t["pencil"], anchor="start", ls=1.5))
    o.append(f'<line x1="{tl_x0}" y1="{tl_y}" x2="{tl_x1}" y2="{tl_y}" stroke="{t["faint"]}" stroke-width="1"/>')
    for i, (num, label, icon) in enumerate(steps):
        x = tl_x0 + i * step
        accent = t["orange"] if i == n - 1 else t["cyan"]
        o.append(f'<circle cx="{x:.1f}" cy="{tl_y}" r="{tl_r}" fill="{t["canvas"]}" '
                  f'stroke="{accent}" stroke-opacity="0.7" stroke-width="1.6"/>')
        isz = 20
        o.append(f'<svg x="{x - isz / 2:.1f}" y="{tl_y - isz / 2:.1f}" width="{isz}" height="{isz}" '
                  f'viewBox="0 0 24 24" fill="none" stroke="{t["ink"]}" stroke-width="1.6" '
                  f'stroke-linecap="round" stroke-linejoin="round">{icon}</svg>')
        o.append(txt(x, tl_y - tl_r - 10, num, size=9.5, fill=accent, anchor="middle", ls=1.5))
        o.append(txt(x, tl_y + tl_r + 20, label, size=9, fill=t["pencil"], anchor="middle", ls=0.8))

    # --- footer: site link (left) + the ACTUAL Ashforde seal + name (right) ---
    footer_line_y, footer_text_y = 829, 869
    o.append(f'<line x1="110" y1="{footer_line_y}" x2="{W - 110}" y2="{footer_line_y}" '
              f'stroke="{t["faint"]}" stroke-width="1"/>')
    o.append(txt(110, footer_text_y, "ashforde.org/aeroagentskills", size=16, fill=t["cyan"], anchor="start", ls=2))
    seal_sz, name_w, gap = 40, 150, 12
    seal_x = W - 110 - name_w - seal_sz - gap
    seal_y = footer_text_y - seal_sz + 10
    o.append(ashforde_seal(seal_x, seal_y, seal_sz, opacity="0.92"))
    o.append(txt(seal_x + seal_sz + gap, footer_text_y, "ASHFORDE OÜ", size=16,
                 fill=t["ink"], anchor="start", ls=2, extra=' font-weight="600"'))
    o.append("</svg>")
    return "\n".join(o) + "\n"


# ------------------------------------------------------- LinkedIn launch post

def gen_launch_post(m):
    """GO-day LinkedIn post, fully generated so its figures can never go
    stale (the launch draft this replaces was purged with marketing/ in the
    public-readiness cleanup). Posting is FOUNDER-GATED per the runbook."""
    return f"""# Aero Agent Skills: LinkedIn launch post

GENERATED by `make visuals` from the tree at HEAD. Numbers refresh on every
run and `make visuals-check` fails if this file drifts. Do not edit by hand:
edit gen_launch_post() in scripts/gen_visuals.py.

FOUNDER-GATED: post only once the public repo and the real npm publish are
live (docs/release-runbook-ashforde.md amendment 3b). Before posting:
regenerate so the figures match the published tree, and attach
docs/social-card-dark.png as the image.

---

We built the aerospace knowledge layer for AI agents.

Ask a general AI about DO-178C and you get the acronyms. Ask an agent carrying Aero Agent Skills and you get the software level determination, a PSAC draft, and a hard stop where a human signs.

Aero Agent Skills is {grp(m["leaves"])} verified engineering skills in {m["live_packs"]} installable packs across {m["families"]} disciplines: avionics certification, aerodynamics, structures, propulsion, GNC, flight test, space systems, manufacturing quality and more. Each skill encodes the process: when a standard applies, the workflow, the verification gates, and the point where the agent must stop for a human signature.

What makes it different:

- Verified means replayable. Every skill is spec-linted, behavior-tested offline, and router-asserted against a {grp(m["router_cases"])}-case Hit@1 corpus you can run on the commit you are looking at. It is not certification, and the repo says so plainly.
- {m["standards"]} aerospace standards mapped machine-readably: referenced and summarized, never reproduced.
- Every number and chart in the repository is generated from the tree. Nothing is hand-counted, and CI fails on drift.

Use it in Claude Code, OpenAI Codex, Gemini CLI, Cursor and 70+ SKILL.md hosts. Or connect over MCP from JetBrains, Claude Desktop or VS Code. One npm package carries the CLI and the MCP server:

npx aero-agent-skills

Apache-2.0. Built and maintained by Ashforde OÜ.

Repo: https://github.com/ashfordeOU/aero-agent-skills
Site: https://ashforde.org/aeroagentskills
npm: https://www.npmjs.com/package/aero-agent-skills

#aerospace #aiagents #avionics #do178c #systemsengineering #airworthiness #spacecraft
"""


# -------------------------------------------------------------- DOMAINS.md

def gen_domains(m):
    def mid(s):
        return s.replace("-", "_")

    out = [
        "# Aero Agent Skills Domain Map",
        "",
        "Machine-readable source of truth: `skills/` tree. This page is the human",
        f'companion — {m["families"]} families, {m["live_packs"]} live sub-domain packs, '
        f'{grp(m["leaves"])} verified leaves.',
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
            f'*{m["live_packs"]} packs · {grp(m["leaves"])} leaves rendered above.*']
    for name in sorted(fams):
        f = fams[name]
        out += ["", f"## {name}", "",
                f'**{f["packs"]} sub-domain packs · {grp(f["leaves"])} skills**', "",
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

def block_statline(m):
    """The hero statline image line. Its alt text quotes live numbers so
    screen readers + the alt-text scanner never see stale counts (founder
    caught statline alt stuck at 330/674 while badges said 341/696)."""
    return (
        '<p align="center">\n'
        f'  <img src="docs/statline-dark.png" alt="{grp(m["leaves"])} verified skills · '
        f'{m["live_packs"]} live packs · {m["families"]} families · '
        f'{m["standards"]} standards · {grp(m["router_cases"])} router cases · '
        f'{gate_ratio(m["gates"])} gates green" width="100%">\n'
        '</p>'
    )

def block_badges(m):
    def b(label, msg, color, href, alt=None):
        lab = label.replace("-", "--").replace(" ", "_")
        enc = msg.replace("-", "--").replace(" ", "_")
        return (f'  <a href="{href}"><img src="https://img.shields.io/badge/'
                f'{lab}-{enc}-{color}?style=flat&labelColor=1a1e35" alt="{alt or (label + " " + msg)}"></a>')
    g = m["gates"]
    row = [
        b("skills", grp(m["leaves"]), "0ea5e9", "skills/"),
        b("packs", str(m["live_packs"]), "8b5cf6", "docs/DOMAINS.md"),
        b("families", str(m["families"]), "ec4899", "docs/DOMAINS.md"),
        b("standards", str(m["standards"]), "f97316", "STANDARDS.md"),
        b("gates", gate_badge_msg(g), "2ea043", "docs/harness-contract.md",
          alt=f'gates {gate_ratio(g)}'),
        b("attest", gate_badge_msg(g, "attest"), "2ea043", "docs/harness-contract.md",
          alt=f'attest {gate_ratio(g, "attest")}'),
        b("router cases", grp(m["router_cases"]), "0ea5e9", "eval/"),
        b("format", "agentskills.io", "8b5cf6", "https://agentskills.io"),
    ]
    # Distribution row: how the library ships. Static npm badge on purpose —
    # flip to a live shields npm/v badge at public release (runbook 3b).
    dist = [
        b("npm", "aero-agent-skills", "0ea5e9", "https://www.npmjs.com/package/aero-agent-skills"),
        b("cli", "aero-skills", "8b5cf6", "packages/aero-agent-skills/"),
        b("mcp server", "claude_%C2%B7_vscode_%C2%B7_cursor_%C2%B7_windsurf", "ec4899", "docs/harness-integration.md",
          alt="MCP server for Claude Desktop, VS Code, Cursor, Windsurf"),
        b("claude code", "plugin", "f97316", ".claude-plugin/"),
        b("jetbrains", "plugin_34041", "a78bfa", "packages/jetbrains-plugin/",
          alt="JetBrains plugin, live on the Marketplace (com.ashforde.aeroskills)"),
    ]
    return ("<p align=\"center\">\n" + "\n".join(row) + "\n</p>\n"
            + "<p align=\"center\">\n" + "\n".join(dist) + "\n</p>")


def block_overview(m):
    return (f'**{grp(m["leaves"])} verified skills** across **{m["families"]} families** and '
            f'**{m["live_packs"]} live sub-domain packs** — each one spec-linted, '
            f'behavior-tested, and router-asserted against a '
            f'**{grp(m["router_cases"])}-case Hit@1 corpus**. Every figure below is computed '
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
    rows = ["| Family | Standard spine | Packs | Skills | Router cases |", "|---|---|---:|---:|---:|"]
    fams = m["per_family"]
    for name in sorted(fams):
        f = fams[name]
        rows.append(f'| **{pretty_names[name]}** | {f["spine"]} | {f["packs"]} | {grp(f["leaves"])} | '
                    f'{grp(f["tasks"])} |')
    rows.append(f'| **Total** | {m["standards"]} standards mapped | **{m["live_packs"]}** | '
                f'**{grp(m["leaves"])}** | **{grp(m["router_cases"])}** |')
    return "\n".join(rows)


def block_verify_extra(m):
    return (f'| — visuals fresh | charts + README numbers regenerate to zero diff | '
            f'`make visuals-check` |')


def block_roadmap(m):
    return (f'- **Shipped:** {m["leaves"]} verified skills in {m["live_packs"]} packs across '
            f'{m["families"]} disciplines, all gated by `make validate` '
            f'({gate_ratio(m["gates"])}) and `make attest` '
            f'({gate_ratio(m["gates"], "attest")}); '
            f'distribution as an npm CLI + MCP server (`aero-agent-skills`, router parity proven on the '
            f'full {m["router_cases"]}-case corpus) and Claude Code plugin packaging\n'
            f'- **Now:** deepening every live pack and opening new sub-domain packs on the same '
            f'eval-gated pipeline — every addition lands with its behavior contract and router tasks\n'
            f'- **Later:** reference builds; marketplace listings; '
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
    """The PUBLIC artifact set: every file here ships in the public tree
    (release-runbook-ashforde.md 3b) and must exist/regenerate in both the
    dev checkout and an exported public copy. Marketing-only artifacts
    (the social card, the launch post) are NOT here — see
    marketing_outputs() below, which is conditional and best-effort."""
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
        docs / "skill-anatomy.svg": gen_anatomy(m, LIGHT),
        docs / "skill-anatomy-dark.svg": gen_anatomy(m, DARK),
        docs / "DOMAINS.md": gen_domains(m),
    }


def marketing_outputs(m):
    """MARKETING-ONLY artifacts (docs/release-runbook-ashforde.md 3b):
    the social card and the LinkedIn launch post. Gated on
    ashforde_seal_available() — docs/ashforde-seal.svg is excluded from
    the public-tree allowlist by design, so its absence IS the signal
    that this is an exported public checkout, not a missing dependency.
    Returns {} there so make visuals/visuals-check neither generates nor
    requires these files outside dev; a public visuals-check must never
    fail over marketing collateral it was never supposed to ship."""
    if not ashforde_seal_available():
        return {}
    return {
        REPO / "docs" / "social-card-dark.svg": gen_social(m, DARK),
        REPO / "marketing" / "launch-post-linkedin.md": gen_launch_post(m),
    }


# ---------------------------------------------------------------- selftest
# Same shape as tools/figure_audit.py --selftest: stdlib unittest, built
# lazily so the shipped module never imports a test framework. These lock
# down the ONE thing this generator got wrong for its whole life — a figure
# it claimed to compute and did not — so the derivation stays falsifiable.

def _build_gate_selftest():
    import tempfile
    import unittest

    def with_makefile(body):
        """Point collect_gates at a throwaway Makefile (never the repo's)."""
        global MAKEFILE
        keep = MAKEFILE
        fh = tempfile.NamedTemporaryFile("w", suffix=".mk", delete=False,
                                         encoding="utf-8")
        fh.write(body)
        fh.close()
        MAKEFILE = Path(fh.name)
        try:
            return collect_gates()
        finally:
            MAKEFILE = keep
            Path(fh.name).unlink()

    REAL = ("validate: lint-spec desc-lint hit1\n"
            "\t@echo ok\n"
            "attest: brief-audit content-policy-sweep\n")

    class GateBattery(unittest.TestCase):
        def test_counts_come_from_the_prerequisite_lists(self):
            g = with_makefile(REAL)
            self.assertEqual(g["validate_count"], 3)
            self.assertEqual(g["attest_count"], 2)
            self.assertEqual(g["validate"], ["lint-spec", "desc-lint", "hit1"])

        def test_a_gate_added_to_the_makefile_changes_the_count(self):
            # the defect: this used to be a constant, so it could not move
            before = with_makefile(REAL)["validate_count"]
            after = with_makefile(REAL.replace("validate: ", "validate: portability "))
            self.assertEqual(after["validate_count"], before + 1)

        def test_phony_declaration_is_not_the_target(self):
            g = with_makefile(".PHONY: validate a b c d e f g h\n" + REAL)
            self.assertEqual(g["validate_count"], 3)

        def test_continued_prerequisite_list_is_one_list(self):
            g = with_makefile("validate: a b \\\n        c d\n" + REAL.split("\n", 1)[1])
            self.assertEqual(g["validate_count"], 4)

        def test_trailing_comment_is_not_a_gate(self):
            g = with_makefile("validate: a b # c d e\nattest: x\n")
            self.assertEqual(g["validate_count"], 2)

        def test_missing_target_refuses_instead_of_typing_a_number(self):
            with self.assertRaises(SystemExit):
                with_makefile("attest: x\n")

        def test_empty_prerequisite_list_refuses(self):
            with self.assertRaises(SystemExit):
                with_makefile("validate:\n\t@echo ok\nattest: x\n")

        def test_ratio_and_shields_encoding(self):
            g = with_makefile(REAL)
            self.assertEqual(gate_ratio(g), "3/3")
            self.assertEqual(gate_ratio(g, "attest"), "2/2")
            self.assertEqual(gate_badge_msg(g), "3%2F3")

        def test_ordinal_is_the_position_in_validate(self):
            g = with_makefile(REAL)
            self.assertEqual(gate_ordinal(g, "hit1", "x"), "gate 3")
            self.assertEqual(gate_ordinal(g, "renamed", "the Hit@1 gate"),
                             "the Hit@1 gate")

        def test_unregistered_gate_still_gets_a_chip(self):
            self.assertEqual(gate_chip_lines("figure-audit", {"router_cases": 1}),
                             ["FIGURE", "AUDIT"])

        def test_hit1_chip_carries_the_live_case_count(self):
            self.assertEqual(gate_chip_lines("hit1", {"router_cases": 4472})[1],
                             "4,472 CASES")

        def test_displayed_figures_past_a_thousand_are_comma_grouped(self):
            """Lock the house rule in, rather than pinning the old form.

            The chip expectation above was written against the ungrouped
            figure, so it forbade the correct rendering: it went red the
            moment grouping was introduced. Assert the rule itself, so a
            future generator change is graded against the rule and not
            against whatever the output happened to be.
            """
            self.assertEqual(grp(4472), "4,472")
            self.assertEqual(grp(1000), "1,000")
            self.assertEqual(grp(999), "999")       # below the rule, unchanged
            self.assertEqual(grp("16/16"), "16/16")  # already rendered, passes through

        def test_readme_blocks_quote_the_makefile_not_a_constant(self):
            """The test that would have caught the original defect."""
            g = with_makefile(REAL)
            m = {"leaves": 1, "live_packs": 1, "families": 1, "standards": 1,
                 "corpus_tasks": 1, "router_cases": 1, "gates": g}
            self.assertIn("3/3 gates green", block_statline(m))
            self.assertIn("gates-3%2F3-", block_badges(m))
            self.assertIn("attest-2%2F2-", block_badges(m))
            self.assertIn("`make validate` (3/3)", block_roadmap(m))
            for stale in ("8/8", "5%2F5", "5/5"):
                self.assertNotIn(stale, block_statline(m) + block_badges(m)
                                 + block_roadmap(m))

    return GateBattery


def _build_raster_selftest():
    import unittest

    class RasterStaleness(unittest.TestCase):
        """The lock, not the file's existence.

        `--check` used to assert only that the PNG was THERE. A PNG made
        from an SVG that has changed twice since passes that check forever,
        and on a host whose PATH omits /opt/homebrew/bin the generator
        printed WARN, skipped every raster and exited 0 -- so the stale PNG
        was never even written.
        """

        def test_a_current_png_is_not_stale(self):
            self.assertEqual(
                stale_rasters({"a.png": "sha1"}, {"a.png": "sha1"},
                              {"a.png"}), [])

        def test_a_png_made_from_an_older_svg_is_stale(self):
            out = stale_rasters({"a.png": "new"}, {"a.png": "old"}, {"a.png"})
            self.assertEqual(len(out), 1)
            self.assertIn("older SVG", out[0][1])

        def test_a_missing_png_is_stale(self):
            out = stale_rasters({"a.png": "sha"}, {"a.png": "sha"}, set())
            self.assertEqual(out[0][1], "missing")

        def test_a_png_with_no_recorded_source_is_stale(self):
            # The state a machine without a rasterizer leaves behind: the
            # PNG exists from some earlier run, and nothing says what from.
            out = stale_rasters({"a.png": "sha"}, {}, {"a.png"})
            self.assertIn("no recorded source", out[0][1])

        def test_an_empty_lock_does_not_read_as_current(self):
            out = stale_rasters({"a.png": "s", "b.png": "t"}, {},
                                {"a.png", "b.png"})
            self.assertEqual(len(out), 2)

        def test_results_are_ordered_so_the_report_is_stable(self):
            out = stale_rasters({"b.png": "1", "a.png": "1"}, {}, set())
            self.assertEqual([n for n, _ in out], ["a.png", "b.png"])

        def test_the_rasterizer_is_found_without_a_useful_path(self):
            # The launchd / non-login-ssh case. shutil.which fails there;
            # the fallbacks are the whole point.
            self.assertTrue(
                any(os.path.exists(c) for c in RASTERIZER_FALLBACKS)
                or shutil.which("rsvg-convert") is None,
                "no rasterizer anywhere, and the fallback list names none "
                "that exist on this host")

        def test_the_shipped_lock_covers_every_shipped_png(self):
            lock = load_raster_lock()
            if not lock:
                self.skipTest("no lock in this tree yet")
            for name in lock:
                self.assertTrue((REPO / name).exists(),
                                "%s is locked but not present" % name)

    return RasterStaleness


def run_selftest():
    import unittest
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(_build_gate_selftest()),
        loader.loadTestsFromTestCase(_build_raster_selftest()),
    ])
    ok = unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful()
    return 0 if ok else 1



# --- the raster staleness lock ---------------------------------------------
#
# PNG BYTES CANNOT BE THE EVIDENCE. librsvg renders the same SVG to different
# bytes across versions, so a recorded PNG digest would go red on a machine
# that merely has a different librsvg. That is why --check only ever asserted
# that the PNG EXISTED -- and an existence check passes forever over a PNG
# made from an SVG that has since changed twice.
#
# The SVG's digest is rasterizer-independent and answers the actual question:
# "was this PNG made from THIS SVG?" So each conversion records the sha256 of
# its source, and --check compares that against the source as it stands now.
RASTER_LOCK = REPO / "docs" / "visuals.lock.json"
RASTER_LOCK_CONTEXT = "aero-visuals-raster-lock/v1"

# shutil.which() alone is not enough here. launchd and a non-login ssh shell
# both run with a PATH that omits /opt/homebrew/bin, and rsvg-convert IS
# installed on this machine -- so the generator printed WARN, skipped every
# PNG and exited 0, and the check that only asked whether the file existed
# said nothing. A tool that is present must not read as absent.
RASTERIZER_FALLBACKS = (
    "/opt/homebrew/bin/rsvg-convert",
    "/usr/local/bin/rsvg-convert",
    "/usr/bin/rsvg-convert",
    "/opt/local/bin/rsvg-convert",
)


def find_rasterizer():
    found = shutil.which("rsvg-convert")
    if found:
        return found
    for candidate in RASTERIZER_FALLBACKS:
        if os.path.exists(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return None


def _sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_raster_lock():
    if not RASTER_LOCK.exists():
        return {}
    try:
        doc = json.loads(RASTER_LOCK.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    if doc.get("context") != RASTER_LOCK_CONTEXT:
        return {}
    return doc.get("rasters", {})


def save_raster_lock(rasters):
    RASTER_LOCK.parent.mkdir(parents=True, exist_ok=True)
    RASTER_LOCK.write_text(json.dumps(
        {"context": RASTER_LOCK_CONTEXT,
         "note": ("sha256 of the SVG each PNG was rasterised from. PNG bytes "
                  "are librsvg-version dependent and cannot be compared; the "
                  "source can."),
         "rasters": dict(sorted(rasters.items()))},
        indent=2, sort_keys=False) + "\n", encoding="utf-8")


def stale_rasters(svg_shas, lock, existing):
    """Which PNGs are missing or were made from a different SVG.

    Pure, so the interesting cases are testable without a rasterizer --
    which is the whole point, since the machine that could not rasterize was
    the one that silently skipped the work.

    svg_shas  png-name -> sha256 of the SVG as it stands NOW
    lock      png-name -> sha256 recorded when the PNG was made
    existing  set of png-names present on disk
    """
    out = []
    for name in sorted(svg_shas):
        if name not in existing:
            out.append((name, "missing"))
        elif name not in lock:
            out.append((name, "no recorded source -- run `make visuals` once "
                              "to establish it"))
        elif lock[name] != svg_shas[name]:
            out.append((name, "made from an older SVG"))
    return out


def main():
    if "--selftest" in sys.argv:
        return run_selftest()
    check = "--check" in sys.argv
    m = collect_metrics()
    out = outputs(m)
    mktg = marketing_outputs(m)
    if mktg:
        out.update(mktg)
    elif not check:
        print("skip marketing artifacts (docs/ashforde-seal.svg absent — public tree, by design)")
    readme_path = REPO / "README.md"
    out[readme_path] = render_readme(m, readme_path.read_text(encoding="utf-8"))

    stale = []
    for path, content in sorted(out.items()):
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current != content:
            if check:
                stale.append(path.relative_to(REPO))
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
                print(f"wrote {path.relative_to(REPO)}")

    # 2x PNG rasters for GitHub Mobile (no SVG support in the app).
    #
    # --check no longer asks only whether the file exists. It asks whether
    # the PNG was made from the SVG that is there NOW, by comparing the
    # source digest recorded at conversion time. See RASTER_LOCK above for
    # why the PNG's own bytes cannot be the evidence.
    rsvg = find_rasterizer()
    lock = load_raster_lock()
    svg_shas, existing = {}, set()
    for svg_path in sorted(p for p in out if p.suffix == ".svg"):
        png_path = svg_path.with_suffix(".png")
        name = png_path.relative_to(REPO).as_posix()
        svg_shas[name] = _sha256_text(out[svg_path])
        if png_path.exists():
            existing.add(name)

    if check:
        for name, why in stale_rasters(svg_shas, lock, existing):
            stale.append("%s (%s)" % (name, why))
    else:
        if not rsvg:
            # Loud, and it does NOT touch the lock: leaving the recorded
            # source alone is what makes the next --check go red instead of
            # inheriting a green from a PNG nobody regenerated.
            print("SKIPPED rasters: no rsvg-convert on PATH or at any of %s. "
                  "The PNGs were NOT regenerated and the lock was NOT "
                  "updated, so `make visuals-check` will now fail rather "
                  "than pass over stale rasters."
                  % ", ".join(RASTERIZER_FALLBACKS))
        else:
            for svg_path in sorted(p for p in out if p.suffix == ".svg"):
                png_path = svg_path.with_suffix(".png")
                name = png_path.relative_to(REPO).as_posix()
                w = int(re.search(r'width="(\d+)"', out[svg_path]).group(1))
                subprocess.run([rsvg, "-w", str(w * 2), str(svg_path),
                                "-o", str(png_path)], check=True)
                lock[name] = svg_shas[name]
                print(f"wrote {png_path.relative_to(REPO)}")
            save_raster_lock(lock)
            print(f"wrote {RASTER_LOCK.relative_to(REPO)} "
                  f"({len(svg_shas)} raster source digest(s))")
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
