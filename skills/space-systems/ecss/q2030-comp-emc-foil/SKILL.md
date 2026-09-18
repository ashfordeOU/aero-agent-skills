---
name: q2030-comp-emc-foil
description: "Validate a conductive metal foil EMC shield against the complementary application and termination criteria of ECSS-Q-ST-20-30C clause 7.8. Use when the task is sizing the foil thickness against the skin depth of its metal at the lowest frequency the shield must work from, turning a helical wrap overlap into a pitch, a layer count over every point and the tape length the run consumes, confirming the conductive face is applied inward against the drain wire, and costing the drain-wire pigtail in decibels against a full circumferential termination. Trigger: ecss, q-st-20-30c, conductive-foil-emc-shield, foil-skin-depth-sizing, helical-foil-wrap-overlap, foil-drain-wire-termination, shield-pigtail-penalty-db, conductive-face-orientation, foil-tape-length-estimate."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-comp-emc-foil, conductive-foil-emc-shield, foil-skin-depth-sizing, helical-foil-wrap-overlap, foil-drain-wire-termination, shield-pigtail-penalty-db]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary EMC Shielding with Conductive Foil (space-systems/ecss/q2030-comp-emc-foil)

Use when the task is the complementary foil-shielding layer of
ECSS-Q-ST-20-30C clause 7.8 -- applying a conductive metal foil as an EMC
shield over a harness and terminating it, on top of the shielding
workmanship the standard delegates to its adopted chapter.

## Domain quick reference

- Foil is chosen where braid cannot go: it gives close to full coverage
  at almost no mass, it wraps a bundle no braid will slide over, and it
  has no apertures of its own. What it does not give is strength,
  handling tolerance or a way out, which is where every foil requirement
  comes from.
- Thickness is set by physics, not by handling. A shield thinner than the
  skin depth of its metal at the lowest frequency of concern passes field
  rather than reflecting and absorbing it, so the thickness is graded
  against a computed skin depth and the number of skin depths the project
  demands -- and the skin depth grows as the frequency falls, so the
  low-frequency end is what sizes the foil.
- Application geometry is arithmetic. A helically wrapped tape advances
  by its width less its overlap, so the overlap fraction alone fixes both
  the pitch and how many foil layers sit over any point. An overlap of a
  half gives two layers everywhere; a quarter gives less than one and a
  half, and the thin places are where the shield fails.
- Foil tape is not symmetric. The conductive layer sits on a carrier
  film, so a tape wound the wrong way round puts an insulator against the
  drain wire: the shield looks perfect, measures open, and the defect is
  invisible once the outer covering is on.
- Foil cannot terminate itself. It leaves through a drain wire, and that
  drain wire's run between the foil and the backshell is a pigtail whose
  inductive reactance rises with frequency. The reactance against the
  reference impedance of a full circumferential termination is what the
  pigtail costs in decibels, and it is the reason a long drain wire
  undoes the shield it was fitted to complete.

## Workflow

1. Compute the skin depth of the foil metal from its resistivity, its
   relative permeability and the lowest frequency the shield is required
   to work from.
2. Grade the foil thickness against the required number of skin depths,
   absorbing an exact equality with a tolerance instead of rounding the
   thickness.
3. Turn the tape width and overlap fraction into the wrap pitch and the
   number of layers over any point, then grade the layer count against
   the project requirement.
4. Compute the tape length the run consumes from the pitch, the bundle
   circumference and the run length, so the estimate that sizes the
   material is the same arithmetic the inspection uses.
5. Confirm the conductive face is applied inward and that the drain wire
   runs continuously against it for the whole run.
6. Compute the pigtail inductance from the drain-wire length, its
   reactance at the highest frequency of concern, and the decibel penalty
   that reactance carries against the reference impedance.
7. Grade the penalty against what the project allows, then roll the
   application and termination findings into one verdict.

## Pitfalls

- Sizing the foil at the highest frequency in the requirement. Skin depth
  grows as frequency falls, so the low-frequency end is what sets the
  thickness; sizing at the top of the band produces a foil that is thin
  where it matters.
- Reading an overlap percentage as a coverage percentage. The overlap
  sets the layer count; coverage is complete either way until the layer
  count drops below one, at which point there are bare gaps between
  turns.
- Treating tape orientation as a handling preference. Carrier-side inward
  is an open shield with a perfect appearance, and it is found at the EMC
  test after the harness is installed.
- Terminating the foil by folding it back under a clamp. Foil tears and
  cold-flows under clamping load; the drain wire exists because the foil
  itself is not a terminable conductor.
- Leaving the drain wire long because it is convenient to dress. The
  penalty grows with both length and frequency, so a drain wire dressed
  for tidiness can cost more shielding than the foil ever provided.
- Quoting one shielding-effectiveness figure for the run. The figure
  belongs to the foil; the termination has its own cost, and the run is
  only as good as the two together.
- Failing a thickness or a penalty that lands exactly on its bound. The
  equality is a representation question, settled with a tolerance inside
  the comparison and never by moving the bound.

## Behavior contract (gate 3)

The skin-depth computation, the thickness grading, the helical pitch and
layer-count geometry, the tape-length estimate, the conductive-face and
drain-wire continuity checks, the pigtail inductance, reactance and
decibel penalty, and the combined application-plus-termination verdict
are exercised by the gate 3 contract test:
scripts/test_q2030_comp_emc_foil.py against
scripts/q2030_comp_emc_foil_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_emc_foil.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
