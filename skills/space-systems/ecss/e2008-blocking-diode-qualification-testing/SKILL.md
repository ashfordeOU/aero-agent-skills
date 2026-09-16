---
name: e2008-blocking-diode-qualification-testing
description: "Use when a blocking diode qualification test matrix, sample allocation or lot size is drafted or reviewed. Determine whether a blocking diode qualification campaign carries the minimum sample quantities ECSS-E-ST-20-08C clause 12.5.5 sets for each test: refuse a plan declaring no minimum, compare booked against owed per test with an allocation exactly on the minimum admissible, hold an owed test nobody booked apart from one merely underfed, name samples booked to a test the qualification never owed, add the destructive draws while carrying only the largest surviving draw once, and size the lot against that plus its reserve. Trigger: ecss, e-st-20-08c, blocking-diode-qualification-minimum-sample-quantity, blocking-diode-qualification-test-allocation, blocking-diode-destructive-sample-consumption, blocking-diode-qualification-lot-sizing, blocking-diode-qualification-test-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-qualification-testing, blocking-diode-qualification-minimum-sample-quantity, blocking-diode-qualification-test-allocation, blocking-diode-destructive-sample-consumption, blocking-diode-qualification-lot-sizing, blocking-diode-qualification-test-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Blocking Diode Qualification Testing (space-systems/ecss/e2008-blocking-diode-qualification-testing)

Use when the task is clause 12.5.5 of ECSS-E-ST-20-08C: a blocking diode
qualification is being sized, and every test in it owes both a run and a
minimum number of samples to run on. This leaf grades the campaign on the
quantity booked per test, on the tests it books at all, and on whether the
qualification lot can physically feed what has been booked.

## Domain quick reference

- The minimum quantity is half the requirement, not a footnote to it. A test
  run on fewer parts than its minimum has been run and has produced data, and
  it has still qualified nothing, because one part passing is an anecdote
  about one part.
- An undeclared minimum is not a minimum of zero. A plan that books tests
  without saying how many samples each owes cannot be graded at all, and the
  assessment closes on that rather than passing a campaign whose sizing nobody
  wrote down.
- The judgement is per test. A campaign with plenty of samples in total and
  one test underfed has left that test unqualified; the surplus booked
  somewhere else does not reach it.
- An allocation exactly on the minimum meets the minimum. It is admissible and
  it is also fragile, which is why it earns an advisory rather than a
  finding: one part damaged in handling takes the test below the quantity that
  qualifies it.
- Destructive and surviving tests draw on the lot differently, and this is the
  arithmetic that usually goes wrong. A part consumed destructively is gone,
  so those allocations add up. A part that survives a non-destructive test can
  be presented to the next one, so those do not add up -- the lot only has to
  carry the largest single surviving draw at once. Summing everything
  overstates the lot; summing nothing understates it.
- An owed test with no allocation at all is a coverage hole, not a shortfall
  of some size, and it is reported as its own kind of finding so a plan
  missing a test is never mistaken for a plan that merely underfed one.
- Samples booked to a test the qualification never owed are reported too. They
  are consuming lot that the owed tests need, and they discharge nothing.

## Workflow

1. Validate the sizing policy first: the reserve fraction the lot carries over
   the booked campaign, and the headroom inside which an allocation counts as
   marginal. A reserve above one is a sizing error rather than a policy.
2. Validate the owed test set: a non-blank name, a whole minimum of at least
   one sample, and an explicit destructive flag on every entry. A test owed
   twice is a transcription defect and is refused; an empty owed set is
   refused rather than reported as met.
3. Validate the booked allocations: a non-blank test name and a whole,
   non-negative sample count, with no test booked twice.
4. Grade every owed test on what is booked for it, recording the shortfall and
   separating an unbooked test from an underfed one.
5. Name every allocation booked to a test the qualification never owed.
6. Total the destructive draws, take the largest surviving draw alone, and add
   the two for the smallest lot that can feed the campaign; apply the declared
   reserve on top.
7. Compare the declared lot against that figure, a lot landing exactly on it
   being sufficient, and raise a marginal advisory for every test booked
   inside the policy headroom. Advisories travel with the verdict and do not
   move it.
8. Close on one verdict: minimum sample quantities not declared, qualification
   sample quantity shortfall, qualification lot size not declared,
   qualification lot cannot feed the campaign, or testing meets minimums.

## Pitfalls

- Summing every allocation to size the lot. The surviving tests share parts,
  so the sum buys hardware the campaign never needed and hides the destructive
  demand that actually constrains it.
- Sizing only on the destructive tests. The largest surviving draw still has
  to exist at one moment, and a lot that cannot present it has not fed the
  campaign either.
- Reading an unbooked test as a shortfall of its full minimum and stopping
  there. The repair is different: one plan needs more parts, the other needs a
  test added.
- Treating a test at exactly its minimum as comfortable. It qualifies today
  and one handling loss undoes it, which is worth saying while the plan can
  still change.
- Letting an allocation to an unowed test count towards coverage. It consumes
  lot and discharges nothing the qualification asked for.

## Behavior contract (gate 3)

The policy validation, the owed test and allocation validation, the per-test
shortfall with an allocation on the minimum admitted, the unbooked-versus-
underfed distinction, the unowed allocations, the destructive total and the
single largest surviving draw, the required lot with its reserve, the
coverage share, the worst shortfall, the marginal advisories and the campaign
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_qualification_testing.py against
scripts/e2008_blocking_diode_qualification_testing_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_qualification_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
