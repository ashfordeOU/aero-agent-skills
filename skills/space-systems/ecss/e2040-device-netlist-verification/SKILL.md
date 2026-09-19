---
name: e2040-device-netlist-verification
description: "Verify the synthesised netlist against the design intent as ECSS-E-ST-20-40C clause 5.5.3 requires, and record what the check found: hold every comparison point in one of equivalent, not-equivalent, unmapped or waived rather than folding the unmapped in with the equivalent, demand a justification on each waiver, report every source-level test never re-run on the netlist and every one that passed before and fails now, compare equivalence against the goal so a value landing exactly on it passes, and refuse a verified outcome the evidence does not carry. Use when a netlist check is planned, run or minuted. Trigger: ecss, e-st-20-electrical-scope, device-netlist-verification, netlist-equivalence-point, unmapped-comparison-point, gate-level-test-rerun, netlist-waiver-justification."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-device-netlist-verification, device-netlist-verification, netlist-equivalence-point, unmapped-comparison-point, gate-level-test-rerun, netlist-waiver-justification, netlist-verification-outcome]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Requirements — Netlist Verification (space-systems/ecss/e2040-device-netlist-verification)

Use when the task is the checking duty of ECSS-E-ST-20-40C clause
5.5.3 -- saying whether the netlist synthesis produced still carries
the design intent it was made from, and recording the outcome in a
form the next phase can rely on.

## Domain quick reference

- Two kinds of evidence close this check and neither is sufficient
  alone. An equivalence comparison relates points in the source
  description to points in the netlist; a re-run of the source-level
  tests on the netlist exercises the parts the comparison abstracts
  away.
- A comparison point has four states, not two: equivalent,
  not-equivalent, unmapped and waived. The unmapped points are the
  defect this check exists for -- they are the points the comparison
  could not relate at all, and folding them in with the equivalent
  produces a clean report over an unexamined region of the netlist.
- A waiver is a decision, so it carries a justification. A waived
  point with nothing written against it is indistinguishable from a
  point somebody marked to make the report finish.
- Every test that passed against the source description has to be run
  again on the netlist. A test not re-run is not a test that passed;
  it is evidence that does not exist, and it reads as coverage in
  every summary that counts test cases rather than results.
- A test that passed before and fails now is the highest-value finding
  in the phase, because the difference isolates the synthesis. It has
  to stay separate from a test that was already failing, which proves
  nothing about the netlist at all.
- Equivalence is a fraction of the comparison points. A goal met
  exactly is met, so the comparison absorbs representation error: a
  three-in-four landing on a 0.75 goal is a pass, and a strict
  comparison against a computed division is what fails a netlist that
  is exactly on target.
- The outcome is recorded, or the work did not happen as far as the
  next phase is concerned. A verified outcome the evidence does not
  carry is worse than no outcome, because it stops anyone looking
  again.

## Workflow

1. Resolve the comparison points: unique identifier, state folded onto
   one of the four, and a justification where waived. Refuse a
   repeated identifier or an unknown key as an input defect.
2. Report every not-equivalent point and, separately, every unmapped
   one, never folding the second into the equivalent count.
3. Report every waived point carrying no justification.
4. Resolve the test cases with their source-level and netlist results,
   and report every test that passed against the source and was not
   re-run on the netlist.
5. Report every test that passed against the source and fails on the
   netlist, keeping it distinct from one already failing beforehand.
6. Compute equivalence over the comparison points and compare it
   against the goal, absorbing representation error.
7. Derive the outcome, refuse a verified outcome the evidence does not
   carry, and report an outcome nobody recorded.

## Pitfalls

- Counting unmapped points as equivalent. The report reads clean over
  the region the comparison never related, and that region is where a
  synthesis difference would sit.
- Accepting a waiver with nothing written against it. It cannot be
  told apart from a point marked to make the report finish, and it
  will be inherited by the next run unchallenged.
- Reading a test that was not re-run as a test that passed. Summaries
  that count test cases rather than results show full coverage, and
  the missing run is invisible until integration.
- Folding a test that was already failing in with one the synthesis
  broke. The second isolates the netlist and the first does not, and
  mixing them destroys the only signal the re-run produces.
- Declaring the netlist verified while unmapped points or failing
  re-runs remain. The outcome is the thing the next phase reads, and
  an overstated one stops anybody looking again.

## Behavior contract (gate 3)

The comparison-point and test resolution, four-state folding, waiver
justification check, re-run completeness, source-versus-netlist result
comparison, equivalence-goal comparison and the recorded outcome are
exercised by the gate 3 contract test:
scripts/test_e2040_device_netlist_verification.py against
scripts/e2040_device_netlist_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_device_netlist_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
