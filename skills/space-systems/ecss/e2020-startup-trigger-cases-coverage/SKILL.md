---
name: e2020-startup-trigger-cases-coverage
description: "Audit whether the faulted start up evidence for a current limiter reaches both of the ways a start up is triggered, a commanded turn on and a rise of the main bus voltage, under ECSS-E-ST-20C clause 5.2.7.6.1. Use when a verification case set is assessed for completeness: fold each declared trigger onto one of the two routes, build the matrix of declared fault conditions against both, credit a cell only to a case that ran and passed, and name a condition evidenced on one route alone as the gap the clause exists to close. Trigger: ecss, e-st-20c-clause-5-2-7-6-1, faulted-start-up-trigger-coverage, commanded-turn-on-route, rising-bus-voltage-route, limiter-verification-case-matrix, one-route-evidence-gap."
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
  tags: [ecss, e-st-20-electrical-scope, e2020-startup-trigger-cases-coverage, e-st-20c-clause-5-2-7-6-1, faulted-start-up-trigger-coverage, commanded-turn-on-route, rising-bus-voltage-route, limiter-verification-case-matrix, one-route-evidence-gap]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Faulted Start Up Trigger Coverage (space-systems/ecss/e2020-startup-trigger-cases-coverage)

Use when the task is the clause 5.2.7.6.1 question of ECSS-E-ST-20C: the
behaviour required of a current limiter starting into a fault holds whether
the start up came from a command or from the main bus voltage rising, so the
evidence has to reach both routes and not just the one that is easy to run.

## Domain quick reference

- The two routes are not two names for one event. A commanded turn on
  happens with the unit already powered, its control logic awake and its
  status line live. A rise of the bus voltage brings the unit up and turns
  the output on in the same movement, so the limiter is arriving at its
  own threshold while the fault is already on the output.
- That difference is what the clause is about. A design can hold its
  ratings on the commanded route and miss on the rising route, because
  the current limit is not yet established when the output starts
  conducting, so evidence from one route does not carry to the other.
- The commanded route is the one that gets run. It is the easy case to
  set up on a bench, which is why a case set left to itself drifts onto
  it, and why a condition evidenced on that route alone is the specific
  finding worth naming rather than a generic coverage number.
- Coverage is a matrix, not a count. Every declared fault condition has
  to meet both routes, so the required set is the conditions multiplied
  by two, and a high case count concentrated in one column is not
  coverage.
- Only a case that ran and passed covers a cell. A planned case and a
  failed case are both real records and both cover nothing, so they are
  reported rather than dropped, and a failed case stays a finding even
  where a sibling case covers the same cell.
- A trigger that folds onto neither route is refused rather than placed.
  Guessing which route a watchdog-driven or a recovery-driven turn on
  belongs to invents coverage that nobody verified.
- A case naming a fault condition outside the declared set is not
  coverage either. It may be worth having, but it answers a question the
  set did not ask, and it cannot fill a cell.
- The fault condition list and any relaxed required fraction are declared
  project data, so they are stated with the result.

## Workflow

1. Take the declared fault condition list and refuse a repeated entry, so
   that two spellings of one condition cannot look like two conditions.
2. Take the verification case set, refuse repeated case identifiers, and
   fold each case's declared trigger onto the commanded route or the
   rising bus voltage route, keeping the original wording alongside.
3. Build the required matrix as every declared condition against both
   routes, and place each case into its cell by condition and route.
4. Set aside the cases whose condition was never declared, rather than
   letting them fill a cell they do not belong to.
5. Mark a cell covered only where it carries a case that ran and passed;
   record the failed and the still-open cases in the cell without
   crediting them.
6. Name each uncovered cell in the terms of the clause: where the twin
   cell passed, the finding is that the condition is evidenced on one
   route only; where neither passed, the condition has no evidence at
   all.
7. Report the failed cases, the open cases, the undeclared conditions, a
   route with no case anywhere in the set, and the coverage fraction
   against the declared requirement.

## Pitfalls

- Counting cases instead of cells. Four cases on the commanded route look
  like a well-exercised unit and leave half the matrix untouched.
- Folding an unrecognised trigger onto the nearer-sounding route. The
  route decides what the evidence is worth, so an unfoldable trigger is
  refused and sent back to be named.
- Crediting a planned case. A case that has not run is a schedule item,
  and reading it as coverage is how a matrix reports complete before the
  test campaign starts.
- Dropping a failed case once a sibling covers the cell. The failure
  happened on real hardware and remains a finding; a passing twin
  restores coverage, not confidence.
- Letting a case against an undeclared condition fill a cell. It moves
  the coverage number without answering any of the questions the
  condition set asked.
- Reading a relaxed required fraction as a pass. Meeting a declared
  fraction is one of several conditions, and failed cases, open cases and
  undeclared conditions stay findings whatever the fraction says.
- Comparing the coverage fraction with the required fraction by bare
  arithmetic. The requirement is declared as a decimal that need not
  represent exactly, so a set cut exactly to it can be grouped either way
  across platforms unless the comparison carries a named tolerance.

## Behavior contract (gate 3)

The trigger folding with its refusal of an unfoldable route, the condition
and outcome tokenising, the repeated-condition and repeated-identifier
refusals, the conditions-by-routes required matrix, the pass-only crediting
of a cell, the one-route-only versus no-evidence phrasing of an uncovered
cell, the failed and open case findings, the undeclared condition route,
the empty-route finding and the coverage fraction compared through its
named tolerance are exercised by the gate 3 contract test:
scripts/test_e2020_startup_trigger_cases_coverage.py against
scripts/e2020_startup_trigger_cases_coverage_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_startup_trigger_cases_coverage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
