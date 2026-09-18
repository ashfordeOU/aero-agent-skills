---
name: q7031-surface-preparation
description: "Derive and audit the substrate preparation a paint system owes under ECSS-Q-ST-70-31C: build the ordered degrease, abrade, rinse, chemical conversion, dry and mask sequence the substrate and the item's keep-out areas demand, compare the as-performed sequence against it for missing, unrecognised, repeated or out-of-order steps, apply the prepared-to-first-coat time window, confirm every declared bare area is actually masked, and close on ready-to-coat, rework-required or re-prepare. Use when a surface is about to be painted or a preparation traveller is being reviewed. Trigger: ecss, q-st-70-31c, paint-surface-preparation-sequence, paint-conversion-treatment-step, prepared-to-coat-window, paint-keep-out-masking, paint-preparation-disposition."
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
  tags: [ecss, q-st-70-31c-paint-application, q-st-70-31c, q7031-surface-preparation, paint-surface-preparation-sequence, paint-conversion-treatment-step, prepared-to-coat-window, paint-keep-out-masking, paint-preparation-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Paints — Surface Preparation (space-systems/ecss/q7031-surface-preparation)

Use when the task is the surface-preparation clause of ECSS-Q-ST-70-31C: the
ordered work that turns a delivered substrate into a surface a paint system
will actually bond to, and the audit of a traveller that claims it was done.

## Domain quick reference

- Preparation is a sequence, not a checklist. Degreasing after abrading drives
  the contaminant the degreasing was meant to remove into the fresh profile the
  abrasion just opened, so the same set of steps in the wrong order leaves a
  worse surface than the one it started from.
- The substrate decides whether a chemical conversion treatment is owed. A
  light alloy gets one because bare metal oxide is neither stable nor a good
  adhesion base; a laminate gets none, and inserting one is not a conservative
  extra but a process nobody qualified on that material.
- Rinsing is the one step that legitimately repeats. Every other repetition in
  a traveller means either the step failed and was redone without a record, or
  two travellers were merged.
- A prepared surface has a shelf life measured in hours. Oxide regrows,
  airborne contamination lands, and absorbed moisture returns, so the window
  from final preparation to first coat is part of the process and a surface
  that missed it is prepared again rather than coated late.
- Masking is a two-sided record. A declared keep-out area that was not masked
  is paint where there must be none; a masked area nobody declared is bare
  substrate where paint was expected, and both are findings.
- The difference between rework and re-preparation matters. A masking gap can
  be corrected locally; a broken or stale sequence cannot, because the surface
  state the rest of the process assumed no longer exists.

## Workflow

1. Derive the required sequence from the substrate and the declared keep-out
   areas, adding the conversion treatment only where the substrate owes one and
   masking only where something has to stay bare.
2. Normalise the as-performed steps and reject a step that is not a string or
   an empty sequence outright.
3. Compare performed against required: missing steps, unrecognised steps,
   repetition of a non-repeatable step, and order violations among the steps
   that carry the sequence.
4. Apply the prepared-to-first-coat window for the substrate, or the per-item
   override, treating an elapsed time exactly at the window as inside it.
5. Compare declared keep-out areas against the masking record in both
   directions.
6. Close with one disposition: re-prepare for a broken sequence or a missed
   window, rework-required for a masking gap alone, ready-to-coat otherwise.

## Pitfalls

- Auditing the set of steps rather than their order. All the right steps in the
  wrong order is a failure mode this check exists to catch, and a set
  comparison cannot see it.
- Adding a conversion treatment to a laminate because a metallic traveller was
  used as the template. That is an unqualified process on that substrate, not a
  cautious extra.
- Recording a long wait before the first coat and coating anyway. The window is
  a process parameter; missing it invalidates the preparation rather than the
  paperwork.
- Treating an undeclared masked area as harmless. Something was protected that
  the drawing expected to be painted, and the reason needs to be known before
  the mask comes off.
- Collapsing a repeated abrasion into one step. The second pass changed the
  surface profile, and the record needs to say so.

## Behavior contract (gate 3)

The required-sequence derivation, sequence comparison, repeatable-step rule,
order check, prepared-to-coat window, two-way masking comparison and the
readiness disposition are exercised by the gate 3 contract test:
scripts/test_q7031_surface_preparation.py against
scripts/q7031_surface_preparation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7031_surface_preparation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
