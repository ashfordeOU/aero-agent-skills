---
name: e2007-susceptibility-threshold-determination
description: "Determine the susceptibility threshold of a unit under test. Use when a disturbance appears during an EMC susceptibility run under ECSS-E-ST-20-07C clause 5.2.10.3: validate the descending injected-level search, locate the level at which the indication ceases, carry the bracket between the last disturbed and first undisturbed step as the resolution of the result, reject a search whose disturbance returns further down, compare every recorded threshold with the required immunity level, confirm the affected function and modulation are recorded beside the level, and reduce the set of frequencies to the governing one. Trigger: ecss, e-st-20-07c, susceptibility-threshold-determination, descending-level-search, disturbance-cessation-level, susceptibility-margin-to-requirement, emc-susceptibility-run-record."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-susceptibility-threshold-determination, susceptibility-threshold-determination, descending-level-search, disturbance-cessation-level, susceptibility-margin-to-requirement, susceptibility-search-bracket, emc-susceptibility-run-record]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC Susceptibility — Threshold Determination (space-systems/ecss/e2007-susceptibility-threshold-determination)

Use when the task is the susceptibility threshold of ECSS-E-ST-20-07C
clause 5.2.10.3 -- finding the injected level at which an observed
disturbance ceases, recording it with the conditions that produced it,
and reading it against the level the unit is required to withstand, so
that a susceptibility indication becomes a number a reviewer can act on
rather than a note that something happened.

## Domain quick reference

- The threshold is found by coming down, not by going up. Once an
  indication appears the injected level is reduced step by step until
  the indication is no longer observed, and it is that level -- the one
  where the disturbance disappears -- which is recorded.
- A search only means something if it starts disturbed and ends
  undisturbed. A sequence that never disturbed the unit has no threshold
  in it; a sequence still disturbed at its lowest level has not yet
  bracketed one.
- A threshold is never exact; it is known to a bracket. The step between
  the last disturbed level and the first undisturbed one is the
  resolution of the result, and a coarse step means the threshold is
  bracketed rather than resolved. Carry the bracket with the number.
- An indication that ceases and then returns further down is not a
  threshold, it is an inconsistent search: the responding mechanism is
  not monotonic in level, or the monitoring missed a step. Such a search
  cannot be reduced to one number.
- The function has to be watched while the level comes down. If the
  monitored parameter is only sampled at the end of the run, the level
  at which it recovered was never observed.
- The recorded threshold is graded by its margin over the required
  immunity level, not by its absolute value. A margin at or below zero
  means the unit was disturbed at or under the level it must withstand,
  which is a susceptibility finding; a positive but short margin is a
  limitation to carry.
- The conditions belong with the number. Frequency, modulation, the
  affected function and the parameter that moved are what make one
  threshold comparable with another.

## Workflow

1. Validate the run context: a recognized susceptibility run type,
   continuous monitoring of the affected function, a non-negative
   required margin and a positive bracket bound.
2. Validate each observation: positive frequency, recognized modulation,
   a named affected function and observed parameter, the required
   immunity level, and the level search itself.
3. Validate the search: at least two steps, strictly falling levels, a
   disturbed first step, at least one undisturbed step, and no return of
   the indication below the step where it ceased.
4. Reduce the search to the cessation level -- the recorded threshold --
   and to the bracket across the transition. Compare the bracket with
   the bound; absorb representation error at the bound with a named
   decibel tolerance and mark the threshold resolved or merely
   bracketed.
5. Compute the margin as threshold minus required level and categorize
   it: susceptible at or below zero, compliant when the required margin
   is met, marginal in between. Never lower the required margin to move
   a category.
6. Reduce the set of observations to the governing frequency -- the
   smallest margin -- and aggregate the findings (susceptible
   frequencies) and limitations (short margins, unresolved brackets).

## Pitfalls

- Recording the level at which the disturbance appeared on the way up
  instead of the level at which it ceased on the way down. Hysteresis in
  the responding circuit makes the two different numbers.
- Quoting a threshold without its bracket. A 14 dB step between the
  disturbed and undisturbed level gives a number that is barely a
  bracket, let alone a threshold.
- Accepting a search in which the indication comes back lower down. That
  is a second mechanism or a missed observation, not one threshold.
- Sampling the monitored parameter only before and after the sweep. The
  cessation level is then inferred rather than observed.
- Reporting an absolute threshold with no requirement beside it. Whether
  the number is good news depends entirely on the level the unit has to
  withstand.

## Behavior contract (gate 3)

The context validation, search validation, cessation and bracket
reduction, margin categorization and governing-frequency aggregation
logic is exercised by the gate 3 contract test:
scripts/test_e2007_susceptibility_threshold_determination.py against
scripts/e2007_susceptibility_threshold_determination_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_susceptibility_threshold_determination.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
