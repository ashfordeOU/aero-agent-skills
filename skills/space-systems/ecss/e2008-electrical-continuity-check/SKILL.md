---
name: e2008-electrical-continuity-check
description: "Use when a continuity run has to be accepted, sentenced or repeated. Verify that every circuit on a photovoltaic assembly control drawing actually conducts, under ECSS-E-ST-20-08C clause 5.5.3.3.2: check each reading against the test current, temperature and probe technique the drawing imposes, strip the probe leads from a two-wire reading or refuse to grade it, refer the resistance back to the reference temperature before comparing it with the circuit limit, separate a degraded joint from a true open circuit, and account for every drawing circuit nobody probed. Trigger: ecss, e-st-20-electrical-scope, photovoltaic-assembly-continuity-check, control-drawing-circuit-limit, four-wire-continuity-measurement, continuity-temperature-correction, open-circuit-versus-degraded-joint, continuity-coverage-accounting."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-electrical-continuity-check, photovoltaic-assembly-continuity-check, control-drawing-circuit-limit, four-wire-continuity-measurement, continuity-temperature-correction, open-circuit-versus-degraded-joint, continuity-coverage-accounting]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — Electrical Continuity Check (space-systems/ecss/e2008-electrical-continuity-check)

Use when the task is the continuity check of ECSS-E-ST-20-08C clause
5.5.3.3.2 -- showing that every circuit of a photovoltaic assembly conducts,
with each reading taken under the conditions the control drawing puts on the
measurement rather than under whatever the bay happened to offer.

## Domain quick reference

- The control drawing is the circuit list. A circuit it declares and nobody
  probed is not a pass; it is missing evidence, and it belongs in the coverage
  accounting next to the readings rather than being silently dropped.
- The drawing's conditions are part of the requirement. Test current,
  temperature and probe technique are stated because the number moves with
  them, so a reading taken outside the stated bands is reported as such even
  when the value itself looks comfortable.
- A two-wire probe measures its own leads. Against a milliohm-class limit the
  leads are the same size as the thing being graded, so such a reading is
  usable only when the lead resistance was measured and declared, and is
  otherwise carried as not evaluated rather than as a pass.
- Metallic resistance moves with temperature, so a reading is referred back to
  the drawing's reference temperature before the comparison. A warm bay
  otherwise turns a compliant harness into a finding, and a cold one hides a
  joint that is already degrading.
- Conducting badly and not conducting at all are different defects. A reading
  over the limit is a joint losing section or a contact going resistive; a
  reading above the declared open threshold, or no reading at all, is a break.
  They lead to different repairs, so they are reported separately.
- Limit edges are inclusive. A circuit landing exactly on its drawing limit is
  a pass, so the comparison absorbs representation error instead of moving the
  limit to make the arithmetic tidy.

## Workflow

1. Validate the control drawing: a non-empty circuit list, unique circuit ids,
   two distinct endpoints per circuit and a positive resistance limit on each.
2. Validate the conditions the drawing imposes -- conductor, reference
   temperature, temperature band, test current band and open threshold -- and
   refuse an inverted band or a reference sitting outside its own band.
3. Match the readings to the drawing: record circuits never probed, circuits
   probed twice with no stated reason, and readings taken on circuits the
   drawing does not list.
4. For each reading, raise the condition findings first: test current or
   temperature outside the declared band, or a two-wire probe against a limit
   it cannot resolve.
5. Strip the probe leads from a two-wire reading using the declared lead
   resistance, and refuse a declared lead resistance larger than the reading.
6. Refer the resistance back to the reference temperature with the conductor
   coefficient, then grade it: continuous, above limit, or open.
7. Roll the circuits up into a campaign verdict -- verified only when every
   declared circuit was probed once and every one of them conducts inside its
   limit -- and report the grouped verdicts, the coverage and every finding.

## Pitfalls

- Calling a buzzed-out circuit a pass because the instrument beeped. The
  drawing sets a resistance limit, and a joint that conducts through ten times
  that limit beeps exactly the same way.
- Grading a milliohm limit from a two-wire reading. The leads and the contact
  are inside the number, so the result says more about the probe than about
  the assembly.
- Comparing a warm reading with a limit written at the reference temperature.
  The correction is small per kelvin and the bands are wide enough that the
  uncorrected comparison flips verdicts near the limit.
- Reporting an open circuit and a high-resistance joint as the same finding.
  One is a break to be re-made, the other a contact to be investigated, and
  merging them sends the wrong technician.
- Treating coverage as an administrative detail. A campaign that probed most
  of the drawing and passed everything it probed is not a verified assembly,
  so unprobed circuits hold the verdict at not evaluated.
- Widening a limit so a reading exactly on it counts as a pass. Edges are
  already inclusive; the tolerance belongs inside the comparison, not in the
  limit.

## Behavior contract (gate 3)

The drawing and condition validation, the probe-technique and lead-resistance
handling, the temperature referral, the three circuit verdicts, the coverage
accounting and the campaign roll-up are exercised by the gate 3 contract test:
scripts/test_e2008_electrical_continuity_check.py against
scripts/e2008_electrical_continuity_check_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2008_electrical_continuity_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
