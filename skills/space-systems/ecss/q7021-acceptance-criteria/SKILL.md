---
name: q7021-acceptance-criteria
description: "Evaluate a flammability screening run against the burn-length and dripping limits the application of the material carries under ECSS-Q-ST-70-21C. Use when a specimen set has been burned and somebody has to say whether the material is screened in for that installation, from a vented equipment bay to a volume the crew occupies. Grades every specimen, counts a value sitting exactly on a limit as compliant through a named tolerance, fails the whole set on one failing specimen, reports a set smaller than the class minimum as inconclusive rather than passing it, and carries the worst-case burn length and its margin. Trigger: ecss, q-st-70-21, flammability-burn-length-limit, flaming-drip-acceptance, flammability-application-class, specimen-set-size-rule, self-extinguishing-criterion, worst-case-burn-length-margin."
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
  tags: [ecss, q-st-70-21-flammability-screening-scope, q7021-acceptance-criteria, flammability-burn-length-limit, flaming-drip-acceptance, flammability-application-class, specimen-set-size-rule, worst-case-burn-length-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability Screening — Acceptance Criteria (space-systems/ecss/q7021-acceptance-criteria)

Use when the task is the acceptance step of the ECSS-Q-ST-70-21C
flammability screening test — deciding whether a burned specimen set
clears the burn length, the dripping behaviour and the after-flame the
material's intended installation allows.

## Domain quick reference

- The limits belong to the installation, not to the material. The same
  tape is comfortably inside the band for a vented equipment bay and
  outside it for a volume the crew occupies, and well outside it where
  the atmosphere is oxygen enriched, so a screening result cannot be
  graded until the destination is named.
- A screening run is a set, not a specimen. Flammability scatters with
  thickness, weave direction and the exact ignition geometry, so one
  clean specimen says very little; the verdict is driven by the worst
  of the set, and one failing specimen fails it.
- A set smaller than the class minimum is inconclusive, and that is a
  different answer from a pass. Reporting two good specimens as a pass
  for a class that needs five turns a sampling shortfall into a
  clearance, and the shortfall is invisible in the verdict afterwards.
- Dripping is a separate hazard from burn length. A short burn that
  sheds flaming material moves the fire somewhere the specimen never
  reached, so a drip that ignites the indicator below is a failure in
  every class, including the ones that tolerate drips that do not
  ignite anything.
- Complete consumption is not a long burn length. A specimen burned
  end to end never demonstrated that it self-extinguishes; its burn
  length merely ran out of specimen, and grading it on that number
  reads a failure as a result inside the limit.
- The reported margin is against the worst specimen. A margin quoted
  from the set average describes a specimen that was never burned.

## Workflow

1. Resolve the application class and read its burn-length limit,
   after-flame limit, dripping allowance and minimum specimen count.
2. Validate each burned specimen: refuse a burn length longer than the
   exposed specimen length, a negative after-flame time, a fractional
   drip count, and an ignited indicator with no drip behind it.
3. Grade the burn length and the after-flame against their limits,
   absorbing floating-point representation error at a bound with a
   named tolerance rather than by relaxing the bound.
4. Fail a fully consumed specimen regardless of its recorded burn
   length, naming the absent self-extinguishing behaviour as the reason.
5. Fail any specimen whose drip ignited the indicator, and fail a
   dripping specimen in a class that allows no drips at all.
6. Refuse a duplicate specimen identifier in the set, since it means two
   different burns are being carried under one record.
7. Take the longest burn of the set as the worst case and report its
   margin to the limit.
8. Assign the set verdict: fail on any failing specimen, inconclusive
   when the set is clean but smaller than the class minimum, pass only
   when it is both clean and large enough.

## Pitfalls

- Grading a materials list against one set of limits. The list spans
  installations, and a single pass clears tape destined for a crew
  volume on equipment-bay numbers.
- Reading a short set as a pass. Below the class minimum the run has no
  statistical standing, and the honest verdict is inconclusive.
- Quoting the average burn length as the result. The set exists because
  the property scatters; the average hides the specimen that decided it.
- Treating a fully consumed specimen as an ordinary long burn. The
  number is bounded by the specimen, not by the material, and the
  failure it represents is qualitative.
- Tolerating a drip that ignited the indicator because the burn length
  was short. The drip carried the fire off the specimen, which is the
  hazard the criterion exists for.
- Widening a limit so a value on the boundary passes. Equality at the
  limit is a representation question, handled by the tolerance inside
  the comparison; the limit itself stays as specified.

## Behavior contract (gate 3)

The class-limit lookup, specimen validation, burn-length and
after-flame comparison with tolerance, full-consumption rule,
drip-ignition rule, worst-case margin and set-size verdict are
exercised by the gate 3 contract test:
scripts/test_q7021_acceptance_criteria.py against
scripts/q7021_acceptance_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7021_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
