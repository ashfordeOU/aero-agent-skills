---
name: q6015-displacement-damage-dose-assurance
description: "Evaluate the non-ionising dose a part takes and the margin it leaves. Use when ECSS-Q-ST-60-15C clause 5.2 has to be applied to a displacement-damage case: accumulate the dose over direction by a statistical solid-angle sector ray trace or by a Monte Carlo ray sample, judge that sampled mean by its own ray count and standard error, divide the demonstrated displacement capability by the dose and hold it to the minimum design margin of this clause, and require a displacement damage test wherever the part family's function rests on minority-carrier lifetime. Trigger: ecss, q-st-60-15c-clause-5-2, displacement-damage-dose-assurance, non-ionising-dose-margin, solid-angle-sector-ray-trace, monte-carlo-ray-trace-sampling, displacement-damage-test-requirement, minimum-displacement-design-margin."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-displacement-damage-dose-assurance, q-st-60-15c-clause-5-2, non-ionising-dose-margin, solid-angle-sector-ray-trace, monte-carlo-ray-trace-sampling, displacement-damage-test-requirement, minimum-displacement-design-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Hardness Assurance — Displacement Damage Dose (space-systems/ecss/q6015-displacement-damage-dose-assurance)

Use when the task is the displacement damage part of ECSS-Q-ST-60-15C
clause 5.2 — working out the non-ionising dose a part accumulates
through the structure around it, saying how much that number is worth
when it came out of a sampled ray trace, and holding the part to the
minimum margin with a test behind it.

## Domain quick reference

- Displacement damage is a different currency from ionising dose. It
  is bookkept as non-ionising energy deposited per unit mass, and a
  part with a comfortable ionising dose margin can still be finished
  by displacement damage, because the two mechanisms damage different
  things in the device.
- The shielding around a part is directional. A single equivalent
  thickness is an average that nothing in the structure actually has,
  so the dose is accumulated over direction: the sphere is divided
  into solid-angle sectors, each sector carries its own equivalent
  aluminium thickness, and the sector doses are combined weighted by
  the fraction of the sphere they subtend. Those fractions must close
  the sphere, or a slice of sky has been left out or counted twice.
- A Monte Carlo ray trace answers the same question by sampling. That
  makes the answer a sampled mean with a standard error, and both the
  number of rays and the spread they returned decide whether it is an
  answer yet. A thin-spot structure returns a wide spread and needs
  far more rays than a uniform box before its mean settles.
- The two methods are not interchangeable at the margin. A sector
  trace is reproducible and coarse; a ray trace is fine and only as
  good as its sample. Reporting which one produced a dose is part of
  reporting the dose.
- The margin is the demonstrated displacement capability over that
  dose, held to one minimum for every part. Unlike ionising dose, the
  interesting question is less the size of the margin than whether any
  displacement test exists at all.
- Families whose function depends on minority-carrier lifetime --
  optocouplers, bipolar parts, imaging detectors, solar cells, laser
  diodes -- owe a displacement damage test of their own. Ionising dose
  data says nothing about them here, and a margin computed on a
  capability with no such test behind it is arithmetic without
  evidence.

## Workflow

1. Validate the displacement-dose depth curve: at least two points,
   thickness strictly ascending and positive, dose positive and never
   rising with shielding.
2. For a sector trace, validate the sector set: every solid-angle
   fraction positive, every thickness positive, and the fractions
   closing the sphere within a named tolerance.
3. Read each sector's dose off the curve by log-log interpolation,
   refusing a thickness outside the tabulated span rather than
   extrapolating, and sum the sector doses weighted by solid angle.
4. For a Monte Carlo trace, convert every ray thickness to a dose, take
   the sample mean, and compute the sample standard deviation and the
   standard error of the mean.
5. Raise the sampling findings: a ray count below the minimum, and a
   relative standard error above the ceiling.
6. Divide the demonstrated displacement capability by the dose and
   compare with the minimum design margin, letting an exact equality
   pass under a named relative tolerance.
7. Raise the test finding where the family owes a displacement damage
   test and no test reference is on record.
8. Report the per-part dose, method, sampling statistics, margin and
   findings, plus the tightest part and one verdict.

## Pitfalls

- Treating a single equivalent thickness as the shielding. Directional
  structure is the whole reason the sector and ray-trace methods exist,
  and the average thickness under-doses the thin spots.
- Sector fractions that do not close the sphere. The sum is the check
  that every direction was accounted for exactly once; a set summing
  near one is a set with a gap or an overlap in it.
- Accepting a Monte Carlo mean on its ray count alone. The count and
  the spread decide together; a uniform box settles in tens of rays
  and a thin-spot structure does not settle in hundreds.
- Carrying an ionising dose capability across as a displacement
  capability. They are different test results about different damage,
  and the sensitive families are exactly where the substitution fails.
- Letting a wide margin excuse a missing displacement test. The
  capability is the claim under examination, so the quotient built on
  it inherits the gap.
- Moving the minimum margin to clear a part that lands exactly on it.
  The equality is settled by the tolerance inside the comparison.

## Behavior contract (gate 3)

The curve validation, log-log interpolation with its refusal outside
the tabulated span, sector-set closure check, solid-angle weighted
dose, Monte Carlo mean with its standard error and sampling findings,
the minimum-margin comparison at exact equality, the sensitive-family
test rule and the aggregation are exercised by the gate 3 contract
test: scripts/test_q6015_displacement_damage_dose_assurance.py against
scripts/q6015_displacement_damage_dose_assurance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6015_displacement_damage_dose_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
