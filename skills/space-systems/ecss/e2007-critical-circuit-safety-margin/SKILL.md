---
name: e2007-critical-circuit-safety-margin
description: "Evaluate the safety margin demonstrated for critical circuits and electro-explosive device firing lines under ECSS-E-ST-20-07C clause 5.3.2. Use when induced levels have been measured on a firing line or a safety-critical circuit: convert threshold and induced level into decibels with the amplitude or power multiplier, derate the no-fire level before the comparison, apply the margin required for the circuit category, report the shortfall and the worst-case line, and hold the verification while any line falls short. Trigger: ecss, e-st-20-electrical-scope, eed-firing-line-margin, no-fire-current-derating, critical-circuit-safety-margin-db, induced-level-margin-check, worst-case-circuit-margin, firing-line-verification-hold."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-critical-circuit-safety-margin, eed-firing-line-margin, no-fire-current-derating, critical-circuit-safety-margin-db, induced-level-margin-check, worst-case-circuit-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Verification — Safety Margin for Critical Circuits and EED Firing Lines (space-systems/ecss/e2007-critical-circuit-safety-margin)

Use when the task is the ECSS-E-ST-20-07C clause 5.3.2 demonstration of
margin on a critical circuit or an electro-explosive device firing line --
turning a response threshold and a measured induced level into a margin in
decibels, derating the no-fire level first, grading each circuit against the
requirement for its category, and holding the verification on the worst line.

## Domain quick reference

- Surviving the test is not the demonstration. A circuit that failed to
  respond at the levels that happened to be applied has shown nothing about
  how close it came. The deliverable is the distance in decibels between
  the level induced on the circuit and the level at which it responds.
- The multiplier follows the quantity, not the habit. An amplitude reading
  -- a current or a voltage -- takes twenty times the base-ten logarithm of
  the ratio; a power reading takes ten. Applying the amplitude form to a
  power reading doubles the claimed margin and is the common way a line is
  reported safe when it is not.
- A firing line is never compared with the bare no-fire level. The no-fire
  level is derated first, so the spread across a bridgewire population and
  the measurement uncertainty sit inside the demonstration instead of being
  argued around it afterwards.
- The requirement follows what the circuit does. A firing line and a
  safety-critical circuit carry the largest requirement, a mission-critical
  circuit less, a non-critical circuit least; all of them are specification
  values and all of them are overridable for a programme that sets its own.
- A negative margin is a real result, not an input error. An induced level
  above the threshold is reported as a negative margin and a shortfall, so
  the record shows how far the line is inside its response region.
- The demonstration is graded on the worst line, and the report names it.
  An average margin over a set of circuits describes no circuit at all.
- A vehicle carrying initiators shows a firing line on the record. A
  demonstration listing only signal circuits has not covered the lines that
  fire something.

## Workflow

1. Resolve the margin specification: the required margin for each circuit
   category and the derating factor applied to a no-fire level. Reject an
   unrecognized key, a negative requirement, or a derating factor outside
   the unit interval.
2. For each circuit, read its category and quantity kind and select the
   decibel multiplier from the quantity kind, never from the category.
3. Derate the threshold where the category calls for it, and keep both the
   stated threshold and the applied threshold on the record.
4. Compute the margin from the applied threshold and the induced level, and
   compare it with the requirement for the category through a named
   tolerance so a boundary case decides the same way on every host.
5. Record the shortfall for every circuit that falls short, and rank the
   set by margin remaining above each circuit's own requirement.
6. Confirm a firing line is on the record when the vehicle carries
   initiators, then aggregate the findings and emit the gate token. Only an
   empty finding list declares the margin demonstrated.

## Pitfalls

- Grading a power measurement with the amplitude multiplier. The claimed
  margin doubles, and a line that holds 10 dB is reported as holding 20.
- Comparing an induced level with the bare no-fire level. The derating is
  what covers the bridgewire spread, and skipping it moves an uncertainty
  out of the numbers and into an argument.
- Ranking circuits by raw margin. A non-critical line holding 8 dB against
  a 6 dB requirement is healthier than a firing line holding 18 dB against
  20, so the ranking is on margin remaining above each requirement.
- Reporting an average margin for the set. The demonstration is only as
  good as the worst line, which is why that line is named.
- Treating an induced level above the threshold as bad data. It is a
  negative margin and belongs in the report as one.
- Asserting a strict inequality on a decibel value that should land exactly
  on its requirement. A base-ten logarithm is not correctly rounded, so the
  comparison is made through a named tolerance and the boundary case is
  asserted on the decision, not on the rounding direction.
- Listing only signal circuits on a vehicle that carries initiators. The
  lines that fire something are the ones the clause exists for.

## Behavior contract (gate 3)

The specification resolution, quantity-kind multiplier, no-fire derating,
decibel margin, category requirement, shortfall, worst-case ranking and
gate-token logic is exercised by the gate 3 contract test:
`scripts/test_e2007_critical_circuit_safety_margin.py` against
`scripts/e2007_critical_circuit_safety_margin_logic.py` (stdlib unittest,
offline).
Run: python3 scripts/test_e2007_critical_circuit_safety_margin.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
