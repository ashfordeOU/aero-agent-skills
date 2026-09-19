---
name: q7053-worst-case-cycle-definition
description: "Derive the worst-case cycle a sterilization compatibility test has to be run at, out of the nominal process recipe, its tolerances, the number of cycles the hardware may see and the over-test factor the programme applies. Use when a dry-heat, radiation or chemical process has a nominal recipe and the test level must be fixed before specimens are committed to the chamber. Pushes each parameter along its declared severity direction, scales the cumulative parameters by the cycle count and the over-test factor, compares the derived level with the declared material capability, and reports the margin, the driving parameter and any shortfall. Trigger: ecss, q-st-70-53, worst-case-sterilization-cycle, parameter-severity-direction, cumulative-cycle-scaling, sterilization-over-test-factor, material-capability-margin, nominal-recipe-tolerance."
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
  tags: [ecss, q-st-70-53-sterilization-compatibility-scope, q7053-worst-case-cycle-definition, worst-case-sterilization-cycle, parameter-severity-direction, cumulative-cycle-scaling, sterilization-over-test-factor, material-capability-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Sterilization Compatibility — Worst-Case Cycle Definition (space-systems/ecss/q7053-worst-case-cycle-definition)

Use when the task is the procedure step that fixes the level of a
sterilization compatibility test: turning a nominal process recipe into
the worst-case cycle the specimens are actually exposed to, so the
qualification covers every cycle the flight hardware can see.

## Domain quick reference

- The nominal recipe is not the test level. A facility runs inside a
  tolerance band, and the hardware experiences the worst corner of that
  band, so each parameter is pushed along its severity direction before
  anything else is done to it.
- Severity has a direction and it is declared, not guessed. Higher is
  worse for temperature, dose and agent concentration; lower is worse
  for a parameter whose whole purpose is to protect the part, such as a
  minimum chamber humidity that keeps a material from embrittling. A
  parameter with no declared direction cannot be pushed and is an input
  error.
- Cumulative and instantaneous parameters do not scale alike. Dwell
  time and dose accumulate over every cycle the hardware may see, so
  they carry the cycle count; temperature and concentration do not
  accumulate, and multiplying a temperature by a cycle count produces a
  level that means nothing.
- The over-test factor is a deliberate margin on the accumulated
  quantities, applied once on top of the cycle count. It is never a
  factor below one, which would define a test weaker than the process
  it qualifies.
- The comparison against material capability has a direction too. For
  an upward severity the capability is a ceiling, for a downward one it
  is a floor, and a margin at exactly zero is a representation question
  absorbed by a named tolerance rather than by moving the capability.

## Workflow

1. Validate the campaign: a cycle count of at least one and an
   over-test factor of at least one. A factor below one defines a test
   weaker than the process and is an input error.
2. Validate each parameter: a name, a nominal value, a non-negative
   tolerance, a severity direction, whether it is cumulative, and an
   optional declared material capability.
3. Push the parameter to its worst corner: nominal plus tolerance for
   an upward severity, nominal minus tolerance for a downward one.
4. Scale the cumulative parameters by the cycle count and the over-test
   factor; leave the instantaneous parameters at their worst corner.
5. Compute the margin against the declared capability in the sense the
   direction implies, as the unused fraction of capability, and leave
   it undefined when no capability was declared rather than assuming
   one.
6. Identify the driving parameter, the one with the least margin, and
   mark the definition acceptable only when no declared margin is
   negative past the tolerance.
7. Report the derived worst-case level per parameter, its margin, the
   driving parameter and every finding, including each parameter left
   without a declared capability.

## Pitfalls

- Testing at the nominal recipe. Half the facility's tolerance band is
  more severe than nominal, so a nominal test qualifies nothing that
  actually ran hot.
- Applying the cycle count to an instantaneous parameter. Twenty cycles
  at 125 degrees is not a cycle at 2500 degrees, and a scaling rule
  that does not ask whether the quantity accumulates produces exactly
  that.
- Applying the over-test factor twice, once in the tolerance and again
  as a factor. The tolerance describes the facility, the factor is the
  programme's deliberate margin, and conflating them inflates the test
  level until no material passes.
- Comparing a downward-severity parameter against its capability as
  though the capability were a ceiling. The sign of the margin flips
  with the direction, and a floor read as a ceiling reports comfortable
  margin on the parameter that is about to fail.
- Filling in a missing material capability with a plausible number. An
  undeclared capability leaves the margin undefined and is a finding,
  not a gap to be closed with judgement.

## Behavior contract (gate 3)

The campaign validation, per-parameter worst-corner derivation,
cumulative scaling, direction-aware margin, driving-parameter selection
and findings are exercised by the gate 3 contract test:
scripts/test_q7053_worst_case_cycle_definition.py against
scripts/q7053_worst_case_cycle_definition_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7053_worst_case_cycle_definition.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
