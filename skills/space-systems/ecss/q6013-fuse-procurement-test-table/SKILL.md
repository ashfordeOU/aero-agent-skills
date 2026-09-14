---
name: q6013-fuse-procurement-test-table
description: "Evaluate a commercial fuse lot against its procurement test matrix under ECSS-Q-ST-60-13C Table 8-4: validate each row's method, sample size and accept number, size the destructive sample budget so units consumed by fusing and breaking-capacity runs are bought on top of the flight quantity, judge voltage-drop readings against their limit, check every fusing time against the window declared for the overload multiple, treat a unit that opens during the rated-current endurance run as an outright reject, and weigh row failures as a percent defective against the allowance. Use when fuse procurement test results have to become a lot verdict. Trigger: ecss, q-st-60-13c-table-8-4, fuse-procurement-test-matrix, fuse-destructive-sample-budget, fusing-time-current-window, fuse-voltage-drop-limit, fuse-endurance-no-open-rule, fuse-lot-accept-number."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-fuse-procurement-test-table, q-st-60-13c-table-8-4, fuse-procurement-test-matrix, fuse-destructive-sample-budget, fusing-time-current-window, fuse-voltage-drop-limit, fuse-endurance-no-open-rule]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial Parts — Fuse Procurement Test Table (space-systems/ecss/q6013-fuse-procurement-test-table)

Use when the task is the fuse row of the procurement testing provisions of
ECSS-Q-ST-60-13C Table 8-4 — taking the test methods, sample sizes and
acceptance limits the table sets for a fuse family and turning an executed
campaign on one purchased lot into an accept-or-hold verdict.

## Domain quick reference

- A fuse is the one commercial part whose qualifying tests destroy it. Every
  unit taken to its fusing point or its breaking capacity is consumed, so the
  sample sizes in the table are a purchase-quantity input: the order carries
  the flight quantity plus the destroyed units, and a lot sized on the flight
  need alone cannot deliver after the matrix has run.
- The acceptance limits are of three different shapes and cannot share one
  comparison. Voltage drop and cold resistance carry a maximum. The fusing
  time carries a two-sided window. The rated-current endurance run carries no
  number at all: it is a no-open rule.
- The time-current window is two-sided for a physical reason. A fuse that
  opens faster than the window nuisance-trips on inrush and strands the load;
  one that opens slower stops protecting the harness it was put there for.
  Recording only the slow side loses half the acceptance criterion.
- A fusing time is meaningful only against the overload multiple the sample
  was run at. The same element opening in 1 s at twice rated current and in
  1 s at ten times rated current are opposite results, so the multiple travels
  with the reading and a run below rated current is not a fusing test.
- An endurance opening is not a row failure to be counted against an accept
  number. A fuse that opens while carrying the current it is rated for has
  failed the part definition, and that holds the lot on its own.

## Workflow

1. Validate each matrix row: a sample larger than the lot, a zero sample, an
   accept number above the sample or more failures than units sampled is an
   input error, not a degenerate case to clamp. Refuse a matrix that repeats
   a method, so every row is judged once.
2. Mark the rows that consume their units, taking the declared flag where the
   buyer gave one and the method default otherwise, and sum the destructive
   samples into the minimum purchase quantity against the flight need.
3. Compare voltage-drop readings with their maximum, absorbing floating-point
   representation error at the boundary with a named tolerance rather than by
   relaxing the limit.
4. Check each fusing time against both sides of the declared window and report
   early openings separately from late ones; refuse an inverted window and an
   overload multiple at or below rated current.
5. Run the rated-current endurance result as a no-open rule, holding the lot
   for a single opening whatever the row accept numbers allow.
6. Convert each row's failures into a percent defective, compare it with the
   allowance as well as the accept number, and report every rejecting row
   with a marginal-row advisory where an accepted row used up its allowance.

## Pitfalls

- Ordering the flight quantity and nothing more. The destructive rows eat
  their samples; the shortfall surfaces at delivery, after the lot has been
  bought and the date code can no longer be matched.
- Applying the voltage-drop comparison to the fusing time. A maximum passes
  every fast fuse, and the early-opening population the window exists to
  catch never appears in the record.
- Reading a fusing time without its overload multiple. The number alone is
  not a result, and a sample run at a different multiple cannot be pooled
  with the rest of the row.
- Counting an endurance opening against a row accept number. It is not a rate
  to be tolerated; one unit opening at rated current holds the lot.
- Widening a limit to pass an exact-equality case. An equality at the limit is
  a representation question handled by the tolerance inside the comparison;
  the declared limit stays as specified.

## Behavior contract (gate 3)

The row validation, destructive sample budget, voltage-drop limit, fusing
time-current window, rated-current endurance rule and the overall
accept-or-hold disposition are exercised by the gate 3 contract test:
scripts/test_q6013_fuse_procurement_test_table.py against
scripts/q6013_fuse_procurement_test_table_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6013_fuse_procurement_test_table.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
