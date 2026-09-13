---
name: e2007-cable-shield-current-restriction
description: "Use when verify that no cable shield carries intended circuit current under ECSS-E-ST-20-07C clause 4.2.13.2: test each shielded run against the narrow exemption for a coaxial radiofrequency-feed and a coaxial high-speed-data link at or above the exemption data rate, flag a barred run whose shield is declared the return or whose dedicated-return-conductor is missing, bound the incidental current a both-end-bonded shield picks up from the parallel division between shield-resistance and return-resistance, and check an exempt coaxial run for declared characteristic-impedance, both-end outer-conductor bonding and outer-conductor resistance. Trigger: ecss, e-st-20-07c, shield-return-current, coaxial-outer-conductor, high-speed-data-link, incidental-shield-current, dedicated-return-conductor, characteristic-impedance, shield-bonding."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-cable-shield-current-restriction, shield-return-current, coaxial-outer-conductor, high-speed-data-link, incidental-shield-current, dedicated-return-conductor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Cable Shield Current Restriction (space-systems/ecss/e2007-cable-shield-current-restriction)

Use when the task is the shield-current check of ECSS-E-ST-20-07C
clause 4.2.13.2 -- confirming that a cable shield is an electromagnetic
barrier and not a conductor of intended circuit current, and that the
two constructions allowed to break that rule really qualify.

## Domain quick reference

- The default rule is absolute: a shield exists to intercept fields,
  and any current it carries by design turns it into a radiator and
  couples every circuit sharing it. A shield is therefore barred from
  the intended-current path unless the run qualifies for the
  exemption.
- The exemption is narrow and needs two things at once. The
  construction must be coaxial -- the outer conductor is the return by
  geometry, concentric with the inner conductor, so the go and return
  currents cancel. And the use must be either a radiofrequency-feed or
  a high-speed-data link at or above the exemption data rate, where a
  controlled-impedance coaxial return is the only workable topology. A
  coaxial power feed does not qualify, and neither does an
  overbraided-bundle data link however fast it runs.
- A barred run fails in two distinct ways, and both are checked. The
  design may declare the shield as the intended return outright, or it
  may simply omit the dedicated-return-conductor, which forces the
  return current onto the shield whether or not anyone wrote it down.
  The second failure is the one that hides in a schematic.
- Incidental current is a different quantity from intended current. A
  shield bonded at both ends sits in parallel with the dedicated
  return and takes a share of the return current set by the two
  resistances -- the share is the return resistance over the sum of
  both. That share is tolerable while it stays under a small fraction
  of the circuit current, and a measured bond-strap total, when one
  exists, supersedes the prediction. A shield bonded at one end only
  carries no return current at all.
- An exempt coaxial run is not unconditionally acceptable. Its outer
  conductor has to behave like a return: a declared
  characteristic-impedance, continuity bonded at both ends, and an
  outer-conductor resistance under its limit.

## Workflow

1. Validate each cable record: identifier, function, construction,
   shield-as-return flag, dedicated-return flag, bonding at both ends,
   data rate, circuit current, shield and return resistances, declared
   characteristic-impedance, measured bond-strap currents. Reject an
   unknown function or construction.
2. Determine the exemption status and record the reason -- coaxial
   radiofrequency-feed, coaxial high-speed-data link, construction not
   coaxial, data rate below the threshold, or function outside the
   exemption. The reason is part of the evidence, not commentary.
3. For a barred run, flag a declared shield return and a missing
   dedicated-return-conductor separately, and note a data rate that
   fell short of the exemption threshold.
4. For a barred run that does have its own return, take the measured
   bond-strap total when present, otherwise predict the current from
   the parallel division, and compare it against the allowed fraction
   of the circuit current. Treat a total that exceeds the limit only
   by the summation representation error as compliant -- the named
   picoampere tolerance absorbs it and the limit itself is untouched.
5. For an exempt coaxial run, check the declared
   characteristic-impedance, the both-end bonding of the outer
   conductor, and its resistance against the limit.
6. Aggregate: the cable set is compliant only when no run carries a
   finding, and the exempt runs are listed so the exemption is visible
   for review rather than buried.

## Pitfalls

- Reading "coaxial" as sufficient. Construction alone does not exempt
  anything; a coaxial power feed still may not return its current on
  the outer conductor.
- Reading "high-speed" as sufficient. A fast link built as an
  overbraided-bundle or a twisted-shielded-pair keeps the ordinary
  rule, because its return is the paired conductor, not the shield.
- Checking only the declared shield-as-return flag. Omitting the
  dedicated-return-conductor produces exactly the same physics with
  nothing declared, and it is the more common defect.
- Confusing incidental with intended current. A both-end-bonded shield
  always takes some share of the return current; the check is whether
  that share stays under its fraction, not whether it is zero.
- Passing an exempt coaxial run without checking its outer conductor.
  An outer conductor bonded at one end, or too resistive, is not a
  return path, and the exemption assumed it was one.

## Behavior contract (gate 3)

The exemption-status, intended-current, parallel-division,
bond-strap-total, incidental-limit and exempt-coaxial-constraint logic
is exercised by the gate 3 contract test:
scripts/test_e2007_cable_shield_current_restriction.py against
scripts/e2007_cable_shield_current_restriction_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_cable_shield_current_restriction.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
