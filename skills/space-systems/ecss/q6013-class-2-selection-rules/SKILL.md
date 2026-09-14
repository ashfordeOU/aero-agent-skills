---
name: q6013-class-2-selection-rules
description: "Determine whether a candidate commercial EEE part may enter a design at the intermediate assurance class under ECSS-Q-ST-60-13C clause 5.2.2.1: run the baseline rules for provenance, manufacturer quality system, procurement route, flight lot homogeneity, temperature envelope with margin, change notification and declared radiation capability; bar the part outright on provenance; carry any other failure only on the measure recognised for that rule, an uprating assessment holding to a kelvin cap; then refuse a part whose stacked residual risk passes the ceiling. Returns the shortfall in kelvin and one verdict. Use when a real part meets the rule set. Trigger: ecss, q-st-60-13c-clause-5-2-2-1, class-two-commercial-part-admissibility, baseline-rule-mitigation-measure, part-uprating-assessment-kelvin-cap, open-market-procurement-mitigation, class-two-stacked-residual-risk-ceiling, authentic-provenance-hard-bar."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q6013-class-2-selection-rules, class-two-commercial-part-admissibility, baseline-rule-mitigation-measure, part-uprating-assessment-kelvin-cap, open-market-procurement-mitigation, class-two-stacked-residual-risk-ceiling, authentic-provenance-hard-bar]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE Components -- Class 2 Baseline Selection Rules (space-systems/ecss/q6013-class-2-selection-rules)

Use when the task is clause 5.2.2.1 of ECSS-Q-ST-60-13C at the
intermediate assurance class: putting a named candidate commercial part
through the baseline rules that steer whether it may be chosen at all.
The framing clause says what the selection owes; this is the rule set a
real part is measured against, and it is the step where the intermediate
class stops being the highest class with softer numbers.

## Domain quick reference

- Seven baseline rules are applied: authentic provenance, a certified
  manufacturer quality system, a controlled procurement route, flight lot
  homogeneity, a rated temperature range enveloping the mission range
  with its declared margin, a change-notification agreement, and a
  declared radiation capability.
- One rule is a hard bar and the rest are carried. Provenance that
  cannot be established bars the part, because every other rule is a
  statement about a part whose identity is assumed. The remaining six
  admit a declared mitigation, which is the mechanism the highest class
  does not offer at all.
- A mitigation is recognised per rule, not in general. Lot-by-lot
  acceptance testing carries a lot homogeneity failure and nothing else;
  a construction audit carries a missing change-notification agreement
  and nothing else. Attaching the wrong measure to a rule is not a
  partial credit, it is an unmitigated failure.
- The uprating route carries a temperature shortfall only so far. Past
  the declared kelvin cap the assessment is no longer an assessment of
  the same part, and the shortfall is reported in kelvin so the reviewer
  can see how far past the cap the design actually sits.
- Residual risk stacks. Each carried rule leaves a declared share
  behind, and a part held up by four individually valid mitigations is
  refused on the total even though no single mitigation was wrong. The
  ceiling is what stops the class becoming a way to admit anything with
  enough paperwork.
- A mitigation attached to a rule the part already meets is reported,
  not counted. It costs the programme money and it hides which rules the
  part actually failed.

## Workflow

1. Validate the candidate: every rule fact declared true or false, a
   recognised procurement route, and a temperature case whose rated and
   mission ranges are both real ranges.
2. Compute the temperature shortfall in kelvin from the mission range
   extended by its declared margin, summing the hot and cold ends.
3. Evaluate the seven baseline rules and collect the failures.
4. Validate each mitigation record, refusing one attached to the hard
   bar and refusing two records on one rule.
5. For every failed rule, accept the mitigation only when it is the
   measure recognised for that rule and inside the limit the measure
   carries; the uprating route is compared with the kelvin cap, treating
   an exactly-met cap as met through a named tolerance.
6. Sum the residual shares of the carried rules and compare the total
   with the declared ceiling under the same tolerance.
7. Report mitigations attached to rules the part already meets.
8. Return ranked findings, the shortfall in kelvin, the residual risk
   and one verdict: admissible, admissible with mitigation, or not
   admissible.

## Pitfalls

- Letting a mitigation carry the provenance rule. A part of unknown
  origin is not a part with a gap in its paperwork, and every other rule
  is silently conditioned on the identity that rule establishes.
- Accepting any declared mitigation for any failed rule. The measure is
  recognised per rule; a generic quality argument attached to a lot
  homogeneity failure changes nothing about the lots that will fly.
- Uprating past the cap because the shortfall is only a few kelvin over.
  The cap is the point the measure stops being evidence, and the
  shortfall is reported in kelvin precisely so that decision is visible
  rather than buried in a pass.
- Judging each mitigation alone. Individually valid measures stack into
  a part nobody would have chosen on its merits, which is what the
  residual ceiling exists to catch.
- Reading margin as optional. A rated range that just touches the
  mission range fails, and dropping the margin turns a real shortfall
  into a clean pass.
- Treating an undeclared rule fact as a met rule. Unknown is not true;
  the candidate is refused until the fact is declared.
- Leaving mitigations attached to rules the part passes. They inflate
  the apparent effort and obscure the failures the reviewer came for.

## Behavior contract (gate 3)

The candidate validation, temperature shortfall, baseline rule
evaluation, mitigation validation, per-rule recognition, uprating cap,
residual risk summation, ceiling comparison, unused mitigation report
and admissibility verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_2_selection_rules.py against
scripts/q6013_class_2_selection_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_2_selection_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
