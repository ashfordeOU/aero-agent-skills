---
name: e2008-blocking-diode-testing-overview
description: "Use when a planar blocking diode test matrix, qualification campaign or lot procurement plan has to be reviewed. Map the qualification and procurement test sets a planar blocking diode owes under ECSS-E-ST-20-08C clause 12.2.1: split every recorded test into the set that owns it and refuse one booked to a set that never owed it, stop a test the two sets share from being discharged twice by a single campaign run, grade each set on the owed tests it actually passed, hold a similarity claim to the heritage part and delta justification it rests on, keep an absent record apart from one recorded as not run and from a failure, and roll the design campaign and every delivered lot into one programme verdict. Trigger: ecss, e-st-20-08c, planar-blocking-diode-test-sets, blocking-diode-qualification-test-set, blocking-diode-procurement-test-set, blocking-diode-shared-test-double-count, blocking-diode-test-set-coverage, blocking-diode-programme-verdict."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-testing-overview, planar-blocking-diode-test-sets, blocking-diode-qualification-test-set, blocking-diode-procurement-test-set, blocking-diode-shared-test-double-count, blocking-diode-test-set-coverage, blocking-diode-programme-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Testing Overview (space-systems/ecss/e2008-blocking-diode-testing-overview)

Use when the task is clause 12.2.1 of ECSS-E-ST-20-08C: a planar blocking
diode carries two test sets, one run against the design and one run again on
every procured lot. This leaf grades a test programme on whether both sets are
reached, on the population each of them is owed by.

## Domain quick reference

- The clause hands over two sets, not one list. The qualification set is owed
  once against the design and shows the part can survive the mission it was
  bought for. The procurement set is owed again on every delivered lot and
  shows the lot in front of you was built to the design that was qualified.
- They are answered by different hardware at different times. Qualification
  parts are consumed by the campaign; they are not shipped, and they cannot
  speak for a lot that was never in the chamber.
- Some tests sit in both sets. A visual inspection and an electrical
  characterisation are run in the campaign and again on each lot. That overlap
  is the trap: a shared test with a campaign record and no lot record reads as
  covered while the lot has no acceptance evidence of its own.
- A test booked against the set that does not owe it is a misfiled record, not
  coverage. A life test entered on a lot traveller neither discharges the lot
  nor tells the campaign anything, and accepting it hides a real gap.
- Coverage is graded on what the set owes, not on what somebody wrote down.
  Dividing passes by recorded entries lets a thin traveller score full marks.
- Four record states are kept apart because different people disposition them.
  No record at all is the worst: nobody can tell whether the work was skipped,
  lost or never scheduled. A test recorded as not yet run is a schedule item.
  A recorded failure is known and can be dispositioned.
- Qualification by similarity is a legitimate route and an evidence-bearing
  one. It rests on a named heritage part and a delta justification, and
  without both it is an assertion. Whether the project takes that route at all
  is a project position, so the claim is graded and the acceptance is read
  from policy rather than assumed either way.
- An open or absent design qualification is not a lot problem, but it does
  open the programme: the lots are being procured against a build standard
  nobody has demonstrated yet.

## Workflow

1. Resolve policy: the coverage minimum, whether similarity is accepted in
   place of the qualification set, and whether a dispositioned failure is
   carried. All three are project positions rather than physical constants.
2. Validate each record book against the set it belongs to. Refuse an unknown
   test, an unknown outcome and a test the set does not owe rather than
   counting any of them as coverage.
3. Grade the qualification set: what has no record, what is recorded as not
   run, what failed, what passed, and the coverage that leaves against the
   declared minimum.
4. Read the qualification route. For a similarity claim, check the heritage
   part and the delta justification are both there, then read acceptance from
   policy. For an open or absent campaign, report it as its own finding.
5. Grade every delivered lot against the procurement set the same way, keeping
   each lot's findings under its own identifier.
6. For each lot, name the shared tests that carry a campaign record and no lot
   record. Those are the runs being counted twice.
7. Report the programme: lots grouped by set verdict, the weakest lot, the
   qualification result and every finding in order.

## Pitfalls

- Reading the two sets as one matrix. The programme then closes on a design
  demonstration while the delivered lots carry no acceptance evidence at all.
- Letting a shared test run once. The campaign parts were consumed, so that
  run says nothing about the lot, and the matrix reads complete anyway.
- Counting a misfiled test as coverage. A procurement-only test entered on the
  qualification side inflates both sets and closes neither.
- Grading coverage over recorded entries instead of owed tests. A traveller
  carrying two of four procurement tests then scores a clean sheet.
- Collapsing absence into failure. They are dispositioned by different people
  through different paperwork, so the verdict keeps them apart.
- Accepting a similarity claim on the word alone. Without the heritage part
  and the delta justification there is nothing for the design to be similar
  to and nothing dispositioning the differences.
- Refusing similarity outright. It is a route the project may legitimately
  take, so acceptance is read from policy rather than decided here.
- Assuming a failed test closes the programme. Whether a dispositioned failure
  is carried is a project position, and assuming either answer produces a
  verdict the project did not agree to.
- Judging a coverage figure that lands exactly on its declared minimum by bare
  arithmetic. It is a quotient of two test counts, so a campaign that ran
  exactly the owed number can evaluate a unit in the last place below the
  minimum; the comparison absorbs that while the minimum stays as declared.

## Behavior contract (gate 3)

The set membership lookup, the misfiled record refusal, the four record
states, the coverage figure against the declared minimum, the shared test
double-count detector, the similarity route with its heritage part and delta
justification, the failure policy and the rolled-up programme verdict are
exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_testing_overview.py against
scripts/e2008_blocking_diode_testing_overview_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2008_blocking_diode_testing_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
