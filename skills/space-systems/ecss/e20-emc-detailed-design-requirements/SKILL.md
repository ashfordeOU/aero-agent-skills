---
name: e20-emc-detailed-design-requirements
description: "Use when derive and check the detailed electromagnetic compatibility design of spacecraft equipment under ECSS-E-ST-20C clause 6.3.9: categorize each requirement as conducted emission, conducted susceptibility, radiated emission, radiated susceptibility or electrostatic discharge immunity; read the applicable level off a piecewise limit line interpolated against the logarithm of frequency and compare the measured level with it; power-sum the conducted emission of every unit sharing a bus before judging the bus; compute the electromagnetic safety margin between a susceptibility threshold and the environment level and hold it against what the criticality demands; and derive the shielding effectiveness an enclosure owes. Trigger: ecss, e-st-20-electrical-scope, emc-detailed-design-requirements, emc-safety-margin, emission-limit-line-interpolation, conducted-emission-power-sum, radiated-susceptibility-threshold, shielding-effectiveness-requirement, electrostatic-discharge-immunity."
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
  tags: [ecss, e-st-20-electrical-scope, e20-emc-detailed-design-requirements, emc-detailed-design-requirements, emc-safety-margin, emission-limit-line-interpolation, conducted-emission-power-sum, radiated-susceptibility-threshold, shielding-effectiveness-requirement, electrostatic-discharge-immunity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- EMC Detailed Design Requirements (space-systems/ecss/e20-emc-detailed-design-requirements)

Use when the task is the clause 6.3.9 detailed electromagnetic
compatibility design of ECSS-E-ST-20C -- turning the electromagnetic
design clause it refers to into numbers a unit can be built against,
and showing that the emission levels, the susceptibility thresholds and
the enclosure shielding hold those numbers with the margin the
criticality of the function demands.

## Domain quick reference

- Every requirement belongs to exactly one family: conducted emission
  (power leads, common mode), conducted susceptibility (bus ripple,
  transient), radiated emission (electric field, magnetic field),
  radiated susceptibility (electric field, magnetic field) or
  electrostatic discharge immunity. The family decides which check
  applies, and a requirement kind that belongs to no family is a gap
  in the specification.
- An emission requirement is a limit line, not a single number. The
  line is a sequence of frequency and level break points, and the
  applicable level at an arbitrary frequency is interpolated linearly
  in decibels against the base-ten logarithm of frequency, because
  that is the space the line is drawn in. Interpolating against linear
  frequency reads the limit several decibels wrong in the middle of
  every decade.
- Several units share one power bus, so the bus sees their conducted
  emission together. Uncorrelated emissions add as power, not as
  voltage: convert each level out of decibels, add, convert back. Two
  equal emitters cost roughly three decibels, not six, and not zero.
- A susceptibility requirement is a threshold, and what matters is its
  distance above the environment the unit actually sits in. That
  distance is the electromagnetic safety margin. A standard function
  carries the ordinary margin; a safety-critical function, ordnance
  above all, carries a much larger one. Asking for a safety margin on
  an emission family is a category error: emission is judged against a
  limit line, not against a margin.
- Where the unit cannot meet a radiated requirement on its own, the
  enclosure makes up the difference. The shielding effectiveness it
  owes is the external field level minus the internal allowable level;
  when the environment is already below the allowable, nothing is
  owed, and the answer is zero rather than a negative requirement.

## Workflow

1. Categorize every requirement into its family; reject a kind that
   belongs to none before it reaches the numeric checks.
2. For each emission requirement, interpolate the limit line at the
   measurement frequency and flag a measured level above it; reject a
   frequency outside the range the line covers rather than
   extrapolating.
3. Power-sum the conducted emission of every unit on a shared bus and
   flag an aggregate above the bus limit, even where each unit passes
   alone.
4. For each susceptibility requirement, compute the safety margin
   between the threshold and the environment level, look up the margin
   the function criticality demands, and flag a shortfall.
5. Derive the shielding effectiveness each enclosure owes and flag an
   enclosure whose achieved effectiveness falls short.
6. Aggregate the family, emission, bus, susceptibility and shielding
   findings; the detailed design is compatible only when every list is
   empty.

## Pitfalls

- Interpolating a limit line against linear frequency. The line is
  drawn against the logarithm of frequency, and a linear read is worst
  exactly where most break points sit.
- Extrapolating past the ends of the limit line rather than refusing.
  A level read outside the covered range is not a conservative
  estimate, it is an invented requirement.
- Judging each unit against the bus limit on its own. The bus carries
  the power sum, so a set of individually compliant units can still
  put the bus over, and the aggregate has to be computed explicitly.
- Adding emission levels in decibels as if they were voltages, or
  taking the worst of them. Uncorrelated sources add as power; two
  equal contributors cost about three decibels.
- Applying the standard margin to an ordnance or safety-critical
  function. That margin is much larger, and the criticality has to be
  carried into the check rather than assumed.
- Reporting a negative shielding requirement when the environment sits
  below the allowable. Nothing is owed, and a negative number invites
  a credit that does not exist.

## Behavior contract (gate 3)

The requirement-family categorization, limit-line interpolation,
power-sum aggregation, safety-margin and shielding-effectiveness logic
is exercised by the gate 3 contract test:
scripts/test_e20_emc_detailed_design_requirements.py against
scripts/e20_emc_detailed_design_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_emc_detailed_design_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
