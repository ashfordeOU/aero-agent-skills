---
name: q2030-comp-sleeving
description: "Evaluate the insulation sleeving applied over terminated contacts against the complementary requirements of ECSS-Q-ST-20-30C clause 7.5. Use when the task is choosing a sleeve size that will pass over the largest diameter on its assembly path and still close onto the diameter it must grip, sizing the cut length from the covered span, the overlap owed at each end and the longitudinal shrinkage, confirming the installed sleeve clears the contact retention and mating features, and deciding whether an opaque sleeve has left a joint without an inspection record. Trigger: ecss, q-st-20-30c, complementary-insulation-sleeving, sleeve-recovery-ratio, sleeve-cut-length-sizing, sleeve-end-overlap, contact-retention-feature-clearance, opaque-sleeve-inspectability, longitudinal-sleeve-shrinkage."
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
  tags: [ecss, q-st-20-electrical-harness-scope, q-st-20-30c, q2030-comp-sleeving, complementary-insulation-sleeving, sleeve-recovery-ratio, sleeve-cut-length-sizing, contact-retention-feature-clearance, opaque-sleeve-inspectability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Harness Manufacturing — Complementary Insulation Sleeving (space-systems/ecss/q2030-comp-sleeving)

Use when the task is the complementary sleeving layer of ECSS-Q-ST-20-30C
clause 7.5 -- the space-specific requirements on the insulation sleeving
that goes over a terminated contact, on top of the workmanship criteria
the standard delegates to its adopted chapter.

## Domain quick reference

- A heat-shrinkable sleeve has to satisfy two diameters at once, and they
  pull in opposite directions. Unshrunk it must clear the largest thing on
  its assembly path -- usually the contact body or the backshell it was
  threaded over, not the wire -- and recovered it must close onto the
  smallest thing it grips. Only a sleeve whose recovery ratio spans both
  is selectable, which is why an oversize sleeve that slides on easily is
  so often the wrong one.
- The recovered inside diameter is the supplied bore divided by the
  recovery ratio, and that is a free-shrink figure. Recovery stops early
  on anything it grips, so the grip is counted only when the free-shrink
  diameter sits a named margin below the diameter it has to hold.
- Sleeve length is a cut length, not an installed length. Recovery pulls
  the sleeve back longitudinally as well as radially, so the cut has to
  carry the covered span, the overlap owed at each end, and the
  longitudinal shrinkage on top; a sleeve cut to the installed dimension
  arrives short and exposes exactly the transition it was there to cover.
- The sleeve also has a place it may not reach. Running it onto the
  contact's mating face, over its retention or release geometry, or into
  the connector cavity it would bottom out in turns an insulation part
  into an assembly defect, so the end position is a dimension with a
  minimum clearance and not a workmanship impression.
- Sleeving hides what it covers. An opaque sleeve over a joint whose
  inspection was never separately recorded removes the evidence that the
  joint was ever inspected, so the opacity is only acceptable against a
  recorded inspection taken before the sleeve went on.

## Workflow

1. Validate each sleeve record: an identifier, the supplied bore and
   recovery ratio, the largest path diameter, the smallest gripped
   diameter, the covered span, the overlap owed and the cut length.
2. Compute the recovered inside diameter, then decide selectability from
   both directions -- slides on unshrunk, grips once recovered with the
   named margin -- and report each failure separately so the size change
   that fixes it is obvious.
3. Size the required cut length from the span, both overlaps and the
   longitudinal shrinkage, and compute what the supplied cut length will
   actually settle at once it recovers.
4. Confirm the installed length still covers the span plus both overlaps,
   absorbing an exact equality with a tolerance rather than by shaving the
   overlap.
5. Where an end position and a restricted feature are given, compute the
   clearance between them and grade it against the minimum.
6. Where the sleeve is opaque, confirm a separate joint inspection was
   recorded before it was installed.
7. Roll every record up into one verdict with the conforming count and
   the findings named.

## Pitfalls

- Selecting on the recovered diameter alone. A sleeve that grips
  beautifully may never have passed over the backshell, and that is
  discovered at the bench with the termination already made.
- Cutting to the installed dimension. Longitudinal shrinkage is not a
  rounding error on a short sleeve; ignoring it is the usual reason a
  sleeve ends up a millimetre or two shy of its overlap.
- Treating the overlap as one total rather than one at each end. The
  overlap is owed on both sides of the transition, so the span carries it
  twice.
- Running the sleeve up to the contact shoulder because it looks tidier.
  A sleeve over the retention or release geometry stops the contact
  seating or stops it ever coming out, and both are found at integration.
- Accepting an opaque sleeve because the joint underneath was "obviously
  fine". Once covered, the joint has only the record that was made before
  the sleeve went on; no record means no inspection evidence.
- Failing a sleeve whose installed length lands exactly on the needed
  length. The equality is a representation question, settled with a
  tolerance inside the comparison and never by moving the overlap.
- Reusing one sleeve size across a connector because most contacts take
  it. The path and gripped diameters change with the wire gauge, so a
  mixed-gauge connector generally needs more than one size.

## Behavior contract (gate 3)

The recovered-diameter computation, the slide-on and grip decisions, the
selectability verdict, the cut-length sizing with longitudinal shrinkage,
the installed-length and span-coverage grading, the restricted-feature
clearance and the opaque-sleeve inspectability finding are exercised by
the gate 3 contract test: scripts/test_q2030_comp_sleeving.py against
scripts/q2030_comp_sleeving_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2030_comp_sleeving.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
