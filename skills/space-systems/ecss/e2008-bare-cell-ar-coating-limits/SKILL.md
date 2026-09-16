---
name: e2008-bare-cell-ar-coating-limits
description: "Use when a coated bare cell has been inspected and each coating defect needs a disposition. Assess the antireflective coating of a bare solar cell against clause 7.5.1.4.2 of ECSS-E-ST-20-08C: compute the coatable face left once the contact footprint is taken out, disposition each uncoated patch, coating void and spatter spot on its own limit and on where it sits, total the missing coating against the area ceiling and convert the same share into the reflectance penalty it costs, bound spatter obscuration and the defect counts, and return one cell verdict naming the defects that are not accepted. Trigger: ecss, e-st-20-08c, bare-cell-ar-coating-limits, bare-cell-uncoated-area-ceiling, bare-cell-coating-void-limits, bare-cell-coating-spatter-on-pad, bare-cell-coating-optical-penalty."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-bare-cell-ar-coating-limits, e-st-20-08c, bare-cell-ar-coating-limits, bare-cell-uncoated-area-ceiling, bare-cell-coating-void-limits, bare-cell-coating-spatter-on-pad, bare-cell-coating-optical-penalty, bare-solar-cell-antireflective-coating-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Bare Cell AR Coating Limits (space-systems/ecss/e2008-bare-cell-ar-coating-limits)

Use when the task is clause 7.5.1.4.2 of ECSS-E-ST-20-08C: the ceiling on
uncoated area of a bare solar cell and the limits on spatter and voids in
its antireflective coating. This leaf reads one cell face and the coating
defects observed on it, and returns a disposition per defect plus the
accumulation that decides the cell.

## Domain quick reference

- The denominator is the coatable face, not the cell. The contacts were
  never going to be coated, so charging their footprint to the coating
  makes every cell look worse by the same fixed amount and hides the ones
  that genuinely are.
- The three defect kinds are not interchangeable. A patch and a void both
  take coated area away and both count toward the ceiling; spatter adds
  material, takes no coated area away, and is bounded on its own
  obscuration budget instead.
- A patch and a void fail on different measurements. A patch is a region
  the coating never reached and is bounded on area. A void is a discrete
  hole and is bounded on its largest dimension, because a long thin void
  of small area still cuts a line across the coating.
- Position decides a void as much as size does. A void that reaches the
  cell edge leaves the coating with a free edge, and a free edge is where
  delamination starts under thermal cycling, so it is dispositioned on
  where it sits rather than only on how wide it is.
- Spatter on an interconnect attachment pad is never a cosmetic question.
  An insulating film across a weld or solder pad is a joint that will not
  be made, whatever the size of the spot.
- The geometric ceiling and the optical arm answer different questions.
  The ceiling says how much coating is gone; the optical arm converts the
  same share into the current it actually costs, using the declared
  coated and bare reflectances, so a cell inside the ceiling can still
  fail the penalty when the reflectance step for that coating is large.
- Small accepted flaws still accumulate. The area ceiling, the spatter
  obscuration allowance and the counts per cell catch the cell that
  passed every individual limit and is nevertheless patchy.
- Two measurements of one flaw must agree. An area that cannot fit inside
  the declared largest dimension is a recording error, and grading it
  puts a number nobody measured into the ceiling.

## Workflow

1. Resolve the face: cell dimensions and the contact footprint, and
   derive the coatable area from them. Reject a footprint that leaves no
   coatable face.
2. For each defect, check that its area and its largest dimension can
   describe the same flaw before grading either of them.
3. Disposition an uncoated patch on area, a void on its largest
   dimension, and either of them on whether it reaches the cell edge.
4. Disposition spatter on whether it landed on an attachment pad first,
   and on area only when it did not.
5. Total the missing coating, take it against the coatable face, and
   compare the fraction with the area ceiling.
6. Convert the same fraction into the estimated current penalty using the
   declared reflectances, and compare it with its own allowance.
7. Bound the spatter obscuration fraction and the counts of voids and
   spatter spots, then take the worst disposition, escalate on any
   accumulation finding, and return the cell verdict.

## Pitfalls

- Taking the uncoated fraction against the whole cell. The contacts are
  in that denominator and were never coatable, so the fraction is
  understated on every cell by the same amount.
- Grading a void on area. A narrow void of negligible area can still run
  a long way across the coating, which only the largest dimension shows.
- Grading a void without asking where it ends. A void that reaches the
  edge is a delamination origin, and the same void mid-face is not.
- Treating spatter as lost coating. It is added material, so adding it to
  the uncoated total double counts a face that is still coated underneath
  and understates the flaws that really are missing.
- Grading spatter on size when it sits on an attachment pad. The pad has
  to be welded or soldered, and a film across it stops that at any size.
- Reporting the area ceiling and calling the optical question answered.
  The penalty depends on the reflectance step of this coating, which the
  area fraction alone never carries.
- Accepting a cell because every flaw passed. The ceiling, the spatter
  allowance and the counts exist for exactly that case.
- Comparing a measurement with a derived allowance by bare arithmetic.
  Every allowance here is a product of a criteria share and a measured
  area, so a measurement exactly on it can evaluate a few units in the
  last place above it; the comparison absorbs that representation error
  while the allowance stays untouched.

## Behavior contract (gate 3)

The coatable face derivation, the area-and-dimension consistency check,
the per-kind dispositioning of patches, voids and spatter, the edge-void
rule and its policy waiver, the attachment-pad rule, the uncoated area
ceiling, the reflectance-based current penalty, the spatter obscuration
allowance, the per-kind counts and the cell verdict are exercised by the
gate 3 contract test:
scripts/test_e2008_bare_cell_ar_coating_limits.py against
scripts/e2008_bare_cell_ar_coating_limits_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_bare_cell_ar_coating_limits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
