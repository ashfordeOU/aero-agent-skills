---
name: e2008-reverse-bias-test-criteria
description: "Evaluate the reverse-bias measurement settings an assembly drawing sets under ECSS-E-ST-20-08C clause 6.4.3.14.3. Use when a reverse-bias run has to be read against its drawing: compare the hold temperature as a band, the hold time as a floor and the current limit as a ceiling rather than treating all three alike, report a setting the drawing never set as an absent criterion instead of filling it in from custom, flag a run that sat on its current limiter, and separate a demonstrated breach from a specification gap. Trigger: ecss, e-st-20-08c-clause-6-4-3-14-3, solar-cell-assembly-reverse-bias-criteria, reverse-bias-hold-temperature-band, reverse-bias-hold-time-floor, reverse-bias-current-limit-ceiling, drawing-set-measurement-settings, reverse-bias-limiter-reached."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-reverse-bias-test-criteria, solar-cell-assembly-reverse-bias-criteria, reverse-bias-hold-temperature-band, reverse-bias-hold-time-floor, reverse-bias-current-limit-ceiling, drawing-set-measurement-settings]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Reverse-Bias Test Criteria (space-systems/ecss/e2008-reverse-bias-test-criteria)

Use when the task is the clause 6.4.3.14.3 measurement settings of
ECSS-E-ST-20-08C -- the hold temperature, the hold time and the current
limit that the assembly drawing, not the test house, is the authority on,
and whether a completed reverse-bias run was carried out at them.

## Domain quick reference

- The drawing is the source of the settings. A run executed impeccably at
  a temperature nobody specified still has nothing to be read against, so
  an absent setting is a specification finding in its own right and not a
  gap to be filled in from house custom.
- The three settings are compared in three different directions, and
  treating them alike is how a bad run passes on paper.
- Temperature is a band. Reverse behaviour is strongly temperature
  dependent in both directions, so too cold is as far off-drawing as too
  hot.
- Hold time is a floor. The hold exists to let the assembly settle into the
  state being measured, so longer than drawn still satisfies the criterion
  while shorter does not.
- Current limit is a ceiling. Lower than drawn is conservative and
  acceptable; higher lets the supply push more into the assembly than the
  drawing permits, which is the condition the limit exists to prevent.
- A limit that was actually reached is a separate fact from a limit that
  was set correctly. Once the limiter is in control the assembly sits at
  the limiter's condition, so the recorded hold describes that and not the
  drawn one, even when every declared number matches.

## Workflow

1. Validate the drawing: each setting carries a value and a non-negative
   tolerance, hold time and current limit are positive, temperature is
   signed, and no setting is drawn twice under two spellings.
2. List the required settings the drawing does not carry; each is a missing
   criterion, reported against the drawing.
3. Reject an applied value for a setting the drawing does not set rather
   than inventing a bound to judge it with.
4. Compare each applied value in the direction its setting demands --
   band, floor or ceiling -- absorbing representation error at the bound
   with a named tolerance instead of widening what the drawing set.
5. Record the signed deviation alongside the verdict, so a run that sat one
   tenth outside a band reads differently from one that sat ten degrees
   outside it.
6. List the settings the drawing sets that the run never recorded.
7. Report an outcome in which a demonstrated breach, including a run that
   reached its current limit, outranks an incomplete drawing, which in turn
   outranks an incomplete record.

## Pitfalls

- Comparing every setting symmetrically. A symmetric check on hold time
  turns a deliberately long, conservative hold into a failure; a symmetric
  check on current limit turns a conservative limit into one too.
- Reading a one-sided setting as a target. The drawn current limit is the
  most the supply may be allowed, not the value it must be set to.
- Filling an absent setting from the last similar drawing. The missing
  setting is the finding; substituting one hides a drawing defect and
  fabricates a criterion the programme never agreed.
- Passing a run that sat on its limiter because the limit value matched.
  The setting was right and the measurement still describes the limiter
  rather than the assembly.
- Reporting only the first problem. An incomplete drawing and an
  off-drawing run are different defects with different owners, and each has
  to appear in the report even when one outranks the other.

## Behavior contract (gate 3)

The drawing validation, per-direction comparison, absent-setting and
unrecorded-setting listing, signed deviation, limiter-reached flag and the
outcome precedence are exercised by the gate 3 contract test:
scripts/test_e2008_reverse_bias_test_criteria.py against
scripts/e2008_reverse_bias_test_criteria_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_reverse_bias_test_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
