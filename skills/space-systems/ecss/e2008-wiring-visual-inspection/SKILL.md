---
name: e2008-wiring-visual-inspection
description: "Verify that a solar-array harness is free of the wiring faults excluded once acceptance testing is complete under ECSS-E-ST-20-08C clause 5.5.3.2.12: read a bend against the minimum radius the cable category allows in its own diameters, a twisted run against a turns-per-metre allowance, a crease against how round the jacket still is, treat a kink as permanent set in the conductor, grade chafe, nicks and unsupported spans by measurement, and let the inspection stage decide whether a permanent-set fault is a routing rework or an exclusion on a delivered article. Use when a harness has been examined after its acceptance tests and the record needs a disposition. Trigger: ecss, e-st-20-08c, clause-5-5-3-2-12, solar-array-harness-wiring-inspection, post-acceptance-test-wiring-faults, cable-minimum-bend-radius-check, harness-twist-and-crease-exclusion, wiring-jacket-chafe-assessment."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-wiring-visual-inspection, solar-array-harness-wiring-inspection, post-acceptance-test-wiring-faults, cable-minimum-bend-radius-check, harness-twist-and-crease-exclusion, wiring-jacket-chafe-assessment, harness-tie-down-span-limits]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Wiring Visual Inspection (space-systems/ecss/e2008-wiring-visual-inspection)

Use when the task is the wiring examination of ECSS-E-ST-20-08C
clause 5.5.3.2.12 -- looking at the harness again once the acceptance
tests have been run, and excluding the faults that must not be present
on the article that ships.

## Domain quick reference

- Three of the faults the clause names share one property, and it is
  what shapes the whole screen: a sharp bend, a twist and a crease are
  permanent set. The cable does not spring back. Dressing the run
  straight afterwards restores the shape of the harness and not the
  condition of the cable inside it.
- That is why the inspection stage is part of the input and not
  context. The same bend found before the acceptance tests is a
  routing defect to dress out and re-inspect; found afterwards it is an
  excluded fault on an article that has already been through its
  environment with the defect in it.
- A bend is never judged in millimetres alone. What governs is the
  radius in cable outer diameters, and the multiple depends on what is
  inside the jacket: plain insulated wire takes the tightest bend, a
  braid needs more, a coaxial dielectric that takes a set needs more
  again, and a flat laminate bent out of its preferred plane needs the
  most. The same radius passes on one cable and fails on the next.
- Twist is a rate, not a count. Two turns worked into a short run and
  two turns spread down a long one are different conditions, so turns
  are normalised against the run length before any limit applies.
- A crease is read as how round the jacket still is -- the minor axis
  over the major axis of the deformed section -- because that is what
  says the wall has been pressed rather than merely marked.
- Chafe, nicks and unsupported spans are ordinary graded faults: they
  are measured, dispositioned accept, rework or reject, and they are
  not on the exclusion list at any stage. Depth is taken as a fraction
  of the wall so a thin-walled cable is not judged by a thick one's
  allowance.
- A rework found after the acceptance tests carries a retest duty as
  well as a re-inspection duty. Cutting into a tested harness puts it
  back to an untested state for the run that was touched.

## Workflow

1. Open the record against a harness identifier, the cable category
   and its outer diameter, and the inspection stage. Reject a record
   with no stage rather than assuming one, because the stage is what
   separates a rework from an exclusion.
2. Categorize every fault by kind. Reject an unrecognized kind rather
   than defaulting it into a neighbouring one.
3. For a bend, take the minimum radius as the category factor times
   the outer diameter and compare the measured radius against it.
4. For a twisted run, normalise the turns to turns per metre and
   compare against the category allowance.
5. For a crease, take the jacket roundness ratio and compare against
   the minimum; treat a kink as permanent set with no measurement to
   argue about.
6. Escalate any of those four to an exclusion when the stage is after
   acceptance testing, and to a rework when it is before.
7. Grade chafe, nicks and spans on their measurements at either stage.
8. Close with the harness verdict, the excluded fault identifiers
   listed apart, and the retest duty a post-test rework creates.

## Pitfalls

- Judging a bend radius without the cable. The limit is a multiple of
  the outer diameter and the multiple belongs to the cable category, so
  a radius quoted alone cannot be dispositioned at all.
- Counting turns instead of a twist rate. Three turns in a metre and
  three turns in five metres carry the same count and completely
  different strain in the conductors.
- Dressing a post-test bend straight and re-recording it as clean. The
  set is already in the cable, and the record that matters is that it
  was there when the article was tested.
- Treating a crease as a cosmetic jacket mark. The measurement that
  decides it is the flattening of the section, which is the same wall
  that keeps the conductor insulated.
- Reworking a tested harness and closing the record on re-inspection
  alone. The run that was cut into is no longer covered by the
  acceptance test it passed.
- Comparing a measurement with a derived limit by bare arithmetic. The
  minimum bend radius is a product of a factor and a measured
  diameter, so a radius exactly on the limit can evaluate a few units
  in the last place below it; the comparison absorbs that
  representation error while the limit stays untouched.

## Behavior contract (gate 3)

The stage-dependent exclusion, the diameter-scaled bend radius, the
twist rate, the jacket roundness ratio, the graded chafe, nick and span
limits and the harness rollup with its retest duty are exercised by the
gate 3 contract test:
scripts/test_e2008_wiring_visual_inspection.py against
scripts/e2008_wiring_visual_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_wiring_visual_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
