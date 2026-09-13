---
name: e2008-coverglass-adhesive-visual-inspection
description: "Audit the coverglass adhesive of a solar cell assembly for delamination and discolouration under ECSS-E-ST-20-08C clause 5.5.3.2.7: place each indication in the active cell area, the edge margin or the bond line over the rear weld footprint, spend the weld-area allowance on the delamination the welding heat is expected to cause, count everything beyond it against the bonded area, weight each discoloured patch by its grade into a transmission loss for the cell, and return accept, rework or reject with the allowance accounting attached. Use when a coverglassed cell has been examined and the adhesive record needs a disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-7, coverglass-adhesive-delamination-inspection, adhesive-discolouration-grading, rear-weld-area-delamination-allowance, bond-line-void-limits, adhesive-transmission-loss-estimate."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-adhesive-visual-inspection, coverglass-adhesive-delamination-inspection, adhesive-discolouration-grading, rear-weld-area-delamination-allowance, bond-line-void-limits, adhesive-transmission-loss-estimate, solar-cell-assembly-bond-line]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Coverglass Adhesive Visual Inspection (space-systems/ecss/e2008-coverglass-adhesive-visual-inspection)

Use when the task is the adhesive examination of ECSS-E-ST-20-08C
clause 5.5.3.2.7 -- looking through the coverglass at the bond line for
delamination and for discolouration, and applying the allowance that
the region over the rear weld areas carries.

## Domain quick reference

- Two mechanisms are looked for and they fail the assembly in
  different ways. Delamination is mechanical: the bond has let go, the
  void traps gas, and it grows under thermal cycling until the glass
  is no longer held or the cell is no longer protected. Discolouration
  is optical: the adhesive still holds, and it now absorbs part of the
  light on its way to the cell.
- Because they fail differently they are counted differently.
  Delamination is counted as an area fraction of the bonded area and
  on the size of the single worst void; discolouration is counted as
  the light it costs, which is its area weighted by how dark it is.
- The bond line over the rear weld footprint is the exception the
  clause carries. Welding the interconnectors puts heat into that
  region, so delamination there is expected and is allowed up to what
  the footprint buys. The allowance is a pool, not a per-indication
  pass: several voids over the welds draw on the same pool, and
  anything beyond it counts against the bond line like any other void.
- The allowance is bounded by the weld footprint itself. An allowance
  larger than the area it covers would let a void anywhere near the
  welds pass, which is why the fraction cannot exceed one.
- The rear-weld exception applies to delamination, not to the single-
  void size rule: a wide void over the welds is within the allowance,
  while the same void in the middle of the cell is a growing defect
  whatever the total area says.
- Where a stain sits decides whether it costs anything. Discolouration
  in the optical path over the active cell area darkens the light the
  cell receives; the same stain on the edge margin is recorded and
  costs the cell nothing, so it never inflates the loss figure.
- Grades are ordered and the ordering is checked. A darker grade must
  never cost less light than a lighter one, or the criteria set itself
  is inconsistent.

## Workflow

1. Open the record against a cell identifier, the bonded area, the
   active cell area and the rear weld footprint area. Reject an active
   area larger than the bonded area or a footprint larger than the
   bond line, because both make the accounting meaningless.
2. Categorize each indication as delamination or discolouration and
   place it in the active area, the edge margin or the weld region.
   Delamination carries a largest dimension; discolouration carries a
   grade. Reject an indication that is missing its measurement.
3. Spend the weld allowance in record order: each weld-region void
   draws from the pool, and the spill beyond it is counted.
4. Add the counted delamination area, take the fraction of the bonded
   area, and compare it against the rework and reject fractions.
5. Flag any single void outside the weld region wider than the
   single-void limit; that rejects on its own.
6. Weight each optical-path stain by its grade factor, divide by the
   active area, and compare the transmission loss against the rework
   and reject limits.
7. Close with the worse of the two verdicts, the allowance used and
   remaining, and the counted area and loss the verdict rests on.

## Pitfalls

- Treating the weld-area allowance as a per-void pass. It is a pool
  sized by the footprint, and the second void over the welds draws on
  what the first one left.
- Extending the allowance to the single-void size rule. A wide void in
  the middle of the bond line still rejects; the allowance forgives
  where the heat went, not how far a void has grown.
- Counting a stain on the edge margin as lost light. It is outside the
  optical path, and folding it into the loss figure condemns hardware
  that is fully functional.
- Grading discolouration by area alone. A small dark patch can cost
  more light than a large faint one, which is why the area is weighted
  by grade before anything is compared.
- Reading delamination and discolouration as one pooled defect area.
  They have separate limits because they fail the assembly by separate
  mechanisms, and pooling them hides both.
- Comparing a counted area with a derived limit by bare arithmetic.
  The limit is a product of a criteria fraction and a measured area,
  so a value exactly on it can evaluate a few units in the last place
  above it; the comparison absorbs that representation error while the
  limit stays untouched.

## Behavior contract (gate 3)

The indication categorization, rear-weld allowance accounting,
delamination area fraction, single-void rule, grade-weighted
transmission loss and cell verdict are exercised by the gate 3 contract
test: scripts/test_e2008_coverglass_adhesive_visual_inspection.py
against scripts/e2008_coverglass_adhesive_visual_inspection_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e2008_coverglass_adhesive_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
