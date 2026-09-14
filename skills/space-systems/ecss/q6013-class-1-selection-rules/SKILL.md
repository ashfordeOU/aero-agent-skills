---
name: q6013-class-1-selection-rules
description: "Evaluate whether a candidate commercial EEE part may enter a Class 1 design under ECSS-Q-ST-60-13C clause 4.2.2.1. Use when the baseline rule set has to be applied to a real part: a certified manufacturer quality system, a franchised distribution path with no open-market broker, one wafer and one assembly lot for the flight build, a rated temperature range enveloping the mission range with declared margin, a change-notification agreement, and either qualification heritage or the evaluation plan replacing it. Returns admissible, admissible-with-evaluation or not-admissible, naming every failed rule and the temperature shortfall in kelvin. Trigger: ecss, q-st-60-13c, class-1-commercial-part-admissibility, franchised-distribution-path, flight-lot-homogeneity, part-temperature-range-envelope, part-change-notification-agreement, commercial-part-evaluation-plan, manufacturer-quality-system."
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
  tags: [ecss, q-st-60-commercial-eee-scope, q6013-class-1-selection-rules, class-1-commercial-part-admissibility, franchised-distribution-path, flight-lot-homogeneity, part-temperature-range-envelope, part-change-notification-agreement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 1 Baseline Selection Rules (space-systems/ecss/q6013-class-1-selection-rules)

Use when the task is the baseline rule step of ECSS-Q-ST-60-13C clause
4.2.2.1 — putting a named candidate commercial part through the rules
that decide whether it may enter a Class 1 design at all. The framing
clause says what the selection owes; this is the rule set a real part
is measured against.

## Domain quick reference

- Six baseline rules are applied: a certified manufacturer quality
  system, a franchised distribution path, flight lot homogeneity, the
  rated temperature range enveloping the mission range with declared
  margin, a change-notification agreement, and qualification heritage
  or the evaluation plan that replaces it.
- The rules are not interchangeable. Five are hard — a failure bars the
  part. Only the heritage rule is conditional, and it resolves to a
  verdict of its own: a part with no heritage but a declared evaluation
  plan is admitted subject to that evaluation, which is a different
  outcome from a clean admission and is reported as one.
- The distribution path is where a part is lost or saved. A part from
  an open-market broker or an unknown source has no chain of custody
  back to the maker, so every rule below it is being applied to a claim
  rather than to a part. The correct response is refusal, not a finding
  followed by the rest of the sweep.
- Lot homogeneity is counted on two axes — wafer lots and assembly lots
  — because a single wafer lot split across two assembly sites is two
  populations wearing one part number.
- The temperature rule is arithmetic in kelvin: cold margin is the
  mission minimum less the rated minimum, hot margin is the rated
  maximum less the mission maximum, and both must reach the declared
  margin. A commercial part rated exactly to the mission range gives a
  margin of exactly zero, which passes a zero declared margin; that
  equality is absorbed by a named tolerance and never turned into a
  failure by the last bit of a subtraction.

## Workflow

1. Validate the candidate: a non-empty part identifier, a known quality
   system state and distribution path, whole positive lot counts, two
   ordered temperature spans, and boolean agreement, heritage and plan
   flags. A missing or ill-typed input is an error, not a default.
2. Resolve project policy — the declared temperature margin, the flight
   lot limit, and whether an evaluation plan may stand in for heritage.
3. Apply the five hard rules and record each as satisfied or failed with
   a finding that says what was wrong, not merely that something was.
4. Compute both temperature margins and compare each with the declared
   margin, absorbing representation error at the boundary.
5. Apply the conditional heritage rule last, and separate its three
   outcomes: heritage held, heritage replaced by a declared evaluation
   plan, neither.
6. Return admissible only when every hard rule passed and heritage was
   held; admissible-with-evaluation when the plan carried it; otherwise
   not-admissible with every failed rule named.
7. Roll a whole design part set up: group parts by verdict, list the
   evaluations the design has just committed to, name the weakest part,
   and bar the set when any part is barred.

## Pitfalls

- Treating the distribution path as a preference and continuing the
  sweep. The remaining rules then grade a broker's paperwork, and a
  clean-looking rule table is produced for a part nobody can trace.
- Collapsing admissible-with-evaluation into a plain pass. The project
  has committed to an evaluation campaign at that moment, and a pass
  verdict loses the only record that it is owed.
- Counting one lot axis. Wafer lot and assembly lot are separate
  populations, and a build homogeneous on one can be split on the other.
- Reading the temperature rule off the rated range alone. The rule is
  about the pair; a part rated far wider than the mission at the hot end
  can still be short at the cold end, and the shortfall belongs in the
  finding with its size in kelvin.
- Widening the declared margin or the lot limit to admit a part that
  sits exactly on the bound. An equality at the limit is a
  representation question, handled by the tolerance inside the
  comparison; the declared value stays as specified.

## Behavior contract (gate 3)

The candidate validation, the five hard rules, the temperature envelope
arithmetic including the exact-boundary case, the conditional
heritage-or-evaluation rule and its distinct verdict, the policy
overrides and the design roll-up are exercised by the gate 3 contract
test: scripts/test_q6013_class_1_selection_rules.py against
scripts/q6013_class_1_selection_rules_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_selection_rules.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
