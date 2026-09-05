# Wave-40 leaf spec: ssa-closure (systems-engineering-safety, arp4761a pack)

- Path: skills/systems-engineering-safety/arp4761a/ssa-closure/
- Pack: arp4761a. Closest siblings: safety-assessment (the process
  umbrella; its Domain quick reference fixes the sequence, "FHA
  (functional hazard assessment) identifies failure conditions and
  classifies severity; PSSA (preliminary system safety assessment) shows
  the proposed architecture meets safety requirements; SSA (system safety
  assessment) confirms the implemented system does", its Pitfalls warn
  "Running the SSA before the architecture is fixed (sequence error)", and
  its workflow step 5 is "After implementation, run the SSA and close the
  safety requirements"; its logic covers severity classification helpers,
  phase ordering and the analysis set, no margin or gate math),
  functional-hazard-assessment (owns the per-row worksheet: its Pitfalls
  state "the FHA identifies, rates, and targets failure conditions; it
  does not run the PSSA/SSA or build the fault trees" and its workflow
  step 6 "Populate the worksheet rows; flag any row where the assessed
  probability misses the target for follow-up"; severity classification
  and the single-row meets flag live there, with the strict target rule
  "1e-3 does not meet the Minor target (p < 1e-3, not p <= 1e-3)"),
  preliminary-system-safety-assessment (owns requirement derivation and
  target allocation: its Pitfalls fix the handoff, "the PSSA is an
  analytical argument at the proposed-architecture stage, and the SSA
  later confirms the implemented system meets the allocated requirements -
  the two steps are not interchangeable"; its allocation margin is the
  per-channel budget check, not a condition-level verdict),
  in-service-safety-assessment (continued-airworthiness pack, field-data
  review per ARP5150A/ARP5151: "ARP5150A and ARP5151 continue the
  ARP4761A assessment process into the in-service phase, so the predicted
  rates consumed here come from the development safety assessment"; it
  compares observed fleet rates, not implemented-system predictions),
  arp4754a requirements-traceability and configuration-management
  (their "closure" is the traceability-closure matrix of requirements to
  design and verification artifacts, not a safety verdict). Whole-tree
  greps at prep: "post-implementation", "closure-gate", "condition
  margin" and "rollup" of assessed-probability verdicts = 0 owning hits in
  skills/ (rollup hits are zonal-safety zone findings and MBSE
  requirement rollups). GENUINE SES gap: no leaf closes the multi-row
  post-implementation verdict.
- Standards id: arp4761a (reference-only). Ledger Standard: arp4761a.
- Family: systems-engineering-safety

## Claim

Close out the post-implementation safety assessment over the assessed
condition set: look up the quantitative probability target per hour for
the severity class of each condition from module constants, compute the
per-condition margin (target / predicted) and the strict meets verdict,
roll every condition up into the multi-condition closure verdict with the
closed and open counts, the open condition ids, the per-severity-class
closure fraction and the overall closure-gate, and roll the safety
requirement statuses into the verified/open closure list. Produces the
target lookup, per-condition margins, the closure-gate verdict dict and
the requirement closure list that gate the close-out statement. Inputs
are the analyst-supplied post-implementation predicted probabilities
(e.g. from updated fault tree runs on the implemented system) and
verification statuses. Does NOT do: severity classification of a
condition from its effects, single-row worksheet population or the
probability-target band table as a deliverable (functional-hazard-
assessment); derivation or allocation of safety requirements, FDAL/IDAL
assignment (preliminary-system-safety-assessment); the FHA-PSSA-SSA
sequence plan and analysis-set scoping (safety-assessment); field event
rates and Poisson significance from service data (in-service-safety-
assessment); traceability matrices of design artifacts (arp4754a).

## Model (implement exactly)

Functions (pure stdlib):
- severity_target(severity) -> float probability per flight hour from
  module constants TARGET_CATASTROPHIC = 1e-9, TARGET_HAZARDOUS = 1e-7,
  TARGET_MAJOR = 1e-5, TARGET_MINOR = 1e-3 (the ARP4761A-style severity
  target table, name and paraphrase only, never reproduced verbatim);
  accepts exactly the strings "catastrophic", "hazardous", "major",
  "minor"; ValueError on any other string, including "no safety effect",
  because that class carries no quantitative target and cannot be closed
  against a number.
- condition_margin(predicted_q, severity) -> dict {"meets": predicted_q <
  target, "margin": target / predicted_q}; the comparison is strict
  (equality fails, mirroring the FHA strict-target rule) and the margin is
  1.0 exactly at equality; ValueError if predicted_q <= 0 or the severity
  is unknown.
- closure_rollup(conditions) where conditions is a list of dicts {id,
  severity, predicted_q} -> dict {"total": n, "closed": number meeting,
  "open": number missing, "open_conditions": ids in input order,
  "meets_by_severity": {severity: closed / total for that severity},
  "overall_gate": "CLOSED" if every condition meets its target else
  "OPEN"}. Only severities present in the input appear in
  meets_by_severity, ordered catastrophic, hazardous, major, minor.
  ValueError if conditions is empty (nothing to close), any severity is
  unknown or any predicted_q <= 0.
- requirement_closure(requirements) where requirements is a list of dicts
  {id, status} with status in {"verified", "open"} -> dict {"total",
  "verified", "open", "open_requirements": ids in input order}; an empty
  list is valid and returns zeros with an empty list; ValueError on any
  status outside {"verified", "open"}.
Module constants: TARGET_CATASTROPHIC = 1e-9, TARGET_HAZARDOUS = 1e-7,
TARGET_MAJOR = 1e-5, TARGET_MINOR = 1e-3.

Identity to test: condition_margin at predicted_q == target gives meets
False and margin 1.0 exactly; predicted_q half the target gives margin
2.0; the overall_gate is CLOSED iff open_conditions is empty; the
per-severity fractions of meets_by_severity sum with the open counts to
the totals per class; meets is monotone in predicted_q (lower predicted
probability never flips a meet to a miss).

## Worked example

Six assessed conditions on the implemented system, targets per flight
hour (predicted probabilities are analyst-supplied post-implementation
estimates):
- FC-01 catastrophic q = 5e-10 vs 1e-9: meets True, margin 2.0.
- FC-02 catastrophic q = 2e-9 vs 1e-9: meets False, margin 0.5.
- FC-03 hazardous q = 3e-7 vs 1e-7: meets False, margin 0.333333.
- FC-04 hazardous q = 2e-8 vs 1e-7: meets True, margin 5.0.
- FC-05 major q = 4e-6 vs 1e-5: meets True, margin 2.5.
- FC-06 minor q = 9e-4 vs 1e-3: meets True, margin 1.11111.
closure_rollup: total 6, closed 4, open 2, open_conditions [FC-02,
FC-03], meets_by_severity catastrophic 0.5, hazardous 0.5, major 1.0,
minor 1.0, overall_gate OPEN (two conditions miss, one per the two
highest classes, so the close-out stays open).
requirement_closure over five requirements, REQ-1..REQ-3 verified and
REQ-4, REQ-5 open: total 5, verified 3, open 2, open_requirements
[REQ-4, REQ-5].
Run your module and take the real outputs as assert targets; the anchors
above are prep-verified bounds, computed by running the prep anchor
script /tmp/w40spec/anchor_ssa_closure.py (prep-verified by stdlib math).

## Validation list (contract test must include)

- severity_target spot values: catastrophic 1e-9, hazardous 1e-7, major
  1e-5, minor 1e-3.
- ValueErrors: severity "none", "no safety effect", "catastrophic " with
  whitespace, empty string, "Severe".
- condition_margin(5e-10, "catastrophic") = meets True, margin 2.0 within
  1e-12; (2e-9, "catastrophic") meets False margin 0.5.
- Strict-boundary identity: condition_margin(1e-3, "minor") meets False,
  margin 1.0 exactly; condition_margin(9.999e-4, "minor") meets True.
- Worked-example margins 0.333333, 5.0, 2.5, 1.11111 within 1e-6.
- closure_rollup on the six conditions: total 6, closed 4, open 2,
  open_conditions exactly [FC-02, FC-03], gate OPEN; meets_by_severity
  catastrophic 0.5, hazardous 0.5, major 1.0, minor 1.0.
- All-meeting rollup returns gate CLOSED with empty open_conditions; an
  all-failing rollup reports gate OPEN and open == total.
- meets_by_severity contains only severities present in the input.
- requirement_closure on the five requirements: verified 3, open 2,
  open_requirements [REQ-4, REQ-5]; empty list returns zeros and an empty
  open_requirements.
- ValueErrors: closure_rollup([]), unknown severity in a condition,
  predicted_q 0 and negative; requirement_closure with status "closed"
  and with status "in review".
- Determinism: open_conditions and open_requirements keep input order;
  dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave40-ssa-closure.yaml)

Query 1 (copy verbatim):
  "compute the ssa-closure rollup and the closure-gate verdict from the post-implementation-safety-verdict margins of the assessed conditions"
  intent: "systems-engineering-safety; multi-condition closure-gate rollup of the post-implementation margins"
  expected_skill: "systems-engineering-safety/arp4761a/ssa-closure"
Query 2 (copy verbatim):
  "produce the ssa-closure close-out with the requirement-closure-status list of verified and open items before the closure-gate is declared"
  intent: "systems-engineering-safety; verified and open requirement closure statuses at the safety assessment close-out"
  expected_skill: "systems-engineering-safety/arp4761a/ssa-closure"
Task ids: w40-ssa-closure-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must close out the post-implementation
safety assessment over the assessed condition set:" and include the
outputs in the Claim. First tag: ssa-closure. Additional tags ONLY:
closure-gate, post-implementation-safety-verdict, requirement-closure-
status, condition-margin. NEVER single generic words (closure, gate,
verdict, margin, condition, requirement, severity, safety, assessment,
status). 50-150 words, <=1000 chars, no em dash, no "classified", action
verb present.

FORBIDDEN TOKENS (belong to siblings): fha-worksheet, severity-
classification, probability-target band, A-FHA, S-FHA, safety-objective
(functional-hazard-assessment); pssa, fdal, idal, safety-target-
allocation, allocate, derived-requirement, development-assurance-level
(preliminary-system-safety-assessment); sequence-error, analysis-set,
safety-assessment-plan (safety-assessment); arp5150, service-difficulty-
report, field-event-rate, fleet-exposure, single-event-rule, observed-
versus-predicted-rate, airworthiness-directive-request (in-service-safety-
assessment); traceability-closure matrix, change-control, baseline release
(arp4754a configuration-management and requirements-traceability).
