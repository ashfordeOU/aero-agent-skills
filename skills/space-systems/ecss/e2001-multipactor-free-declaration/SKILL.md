---
name: e2001-multipactor-free-declaration
description: "Use when verify that a radio-frequency unit may be declared free of multipactor up to the drive level actually applied, under ECSS-E-ST-20-01C clause 8.5.2: confirm the run reached the required level derived from the maximum-operating-power and the verification-margin-decibels, confirm the detection-capability carried at least one global-detection-method and one local-detection-method with sensitivity-verified and calibration-in-date, confirm electron-seeding was active with effectiveness-verified, confirm the vacuum-condition and the temperature-envelope covered the operational worst-case, and derive the declared-free level and the qualified-operating level, capping both strictly below any recorded onset. Trigger: ecss, e-st-20-electrical-scope, e2001-multipactor-free-declaration, multipactor-free-declaration, declared-free-power-level, detection-capability-evidence, electron-seeding-effectiveness, verification-margin-decibels, onset-capped-declaration."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-free-declaration, multipactor-free-declaration, declared-free-power-level, detection-capability-evidence, electron-seeding-effectiveness, verification-margin-decibels]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Multipactor-Free Declaration (space-systems/ecss/e2001-multipactor-free-declaration)

Use when the task is deciding whether the evidence from a multipactor
qualification run supports the declaration of ECSS-E-ST-20-01C clause 8.5.2 --
that the unit is free of multipactor up to the drive level actually reached --
and deriving the level the declaration may name.

## Domain quick reference

- The declaration is bounded by what the run demonstrated, never by what the
  design predicted. Its ceiling is the highest drive level applied with no
  multipactor observation on record; everything above that level is simply
  untested, and the declaration is silent there.
- A run only *demonstrates* anything if it was able to see a multipactor
  onset had one occurred. Three prerequisites carry that burden: a
  detection-capability of at least one global-detection-method (forward and
  reflected drive comparison, harmonic detection, nulling) plus at least one
  local-detection-method (electron-probe, optical-detection,
  charged-particle-collection), each with sensitivity-verified and
  calibration-in-date; active electron-seeding with effectiveness-verified,
  so free electrons were available to start multiplication; and a
  vacuum-condition at or below the declared limit.
- The environment of the run must envelope the operational worst-case. A
  temperature-envelope narrower than the operational range leaves a corner of
  the operating box undemonstrated, and the declaration cannot be extended
  into it.
- The required drive level is the maximum-operating-power raised by the
  verification-margin-decibels. Powers combine multiplicatively in the linear
  domain and additively in decibels; a margin of three decibels is a factor
  of about two.
- The qualified-operating level is the declared-free level taken back down by
  the same margin -- the operating point the declaration supports once the
  margin is released.
- If any multipactor observation was recorded, the declaration is capped
  strictly below that onset, regardless of how high the ramp later went.

## Workflow

1. Validate the record: a positive maximum-operating-power, a non-negative
   verification-margin-decibels, a non-empty run log of drive levels each
   flagged for a multipactor observation, a detection-method list, a seeding
   entry and an environment entry. Reject a malformed record rather than
   defaulting a missing field to a pass.
2. Derive the required drive level from the maximum-operating-power and the
   verification-margin-decibels, and take the highest level in the run log
   that carries no multipactor observation.
3. Compare the two. The comparison is inclusive and absorbs representation
   error at the boundary -- a level reached by summing two contributions
   lands a few units in the last place under a level reached by one
   multiplication -- but the margin itself is never reduced to make a run
   fit.
4. Check the detection-capability: at least two methods, at least one of each
   family, every one sensitivity-verified and calibration-in-date. A run
   watched by a single family cannot support the declaration.
5. Check the electron-seeding: a recognised source, active during the run,
   with effectiveness-verified. Absence of an observation without seeding
   evidence is not evidence of absence.
6. Check the environment: vacuum-condition at or below the declared limit,
   and a temperature-envelope covering the operational worst-case at both
   ends.
7. Derive the declared-free level. With no observation on record it is the
   highest level applied; with an observation it is capped strictly below the
   lowest onset. Then derive the qualified-operating level by releasing the
   margin. Emit the declaration only when the findings list is empty.

## Pitfalls

- Declaring up to the predicted design level rather than the level reached.
  The clause ties the statement to the drive actually applied; extrapolating
  above it is a claim the run never supported.
- Reading a quiet run as multipactor-free when seeding was inactive or its
  effectiveness was never shown. With no seed electrons the multiplication
  may simply never have been started.
- Accepting a detection-capability of two methods from the same family. A
  pair of global methods shares a blind spot for a localised onset confined
  to one gap.
- Treating an onset seen part-way up the ramp as cleared because a later
  point was quiet. The declaration is capped below the lowest recorded onset,
  not at the top of the ramp.
- Running the vacuum-condition or temperature-envelope narrower than the
  operational worst-case and declaring across the whole operating box.
- Widening the verification-margin-decibels so a short run passes. Absorb
  floating-point error at the boundary; never relax the margin.

## Behavior contract (gate 3)

The decibel conversion, required-level derivation, run-log scan,
detection-capability check, seeding check, environment-envelope check and
declaration derivation are exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_free_declaration.py against
scripts/e2001_multipactor_free_declaration_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multipactor_free_declaration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
