---
name: e2008-planar-blocking-diode-acceptance
description: "Audit a proposed planar blocking diode acceptance programme against the tabulated test list of ECSS-E-ST-20-08C clause 12.4.2: hold a mesa or integrated part outside the table, name every tabulated test the programme omits and every test it adds, order the programme against the tabulated sequence and report each inversion, catch a stress with no electrical readout after it, check each test runs at its tabulated basis and sample size, and return one programme verdict. Use when a planar blocking diode acceptance programme, test flow or sampling schedule is drafted or reviewed. Trigger: ecss, e-st-20-08c, planar-blocking-diode-acceptance-programme, planar-blocking-diode-tabulated-test-list, planar-blocking-diode-test-sequence-order, planar-blocking-diode-post-stress-readout, planar-blocking-diode-acceptance-basis."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-planar-blocking-diode-acceptance, planar-blocking-diode-acceptance-programme, planar-blocking-diode-tabulated-test-list, planar-blocking-diode-test-sequence-order, planar-blocking-diode-post-stress-readout, planar-blocking-diode-acceptance-basis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes — Acceptance Programme (space-systems/ecss/e2008-planar-blocking-diode-acceptance)

Use when the task is clause 12.4.2 of ECSS-E-ST-20-08C: the acceptance
programme for a planar blocking diode is taken from the tabulated test list.
This leaf grades a proposed programme against that table on scope, on content,
on order, on readout and on the basis each test runs at.

## Domain quick reference

- The table is a list and a sequence at once, and only the list half gets
  checked. A programme that carries all nine tabulated tests reads as complete,
  and the three remaining axes -- order, readout and basis -- all survive that
  reading untouched.
- Scope runs ahead of content. This table covers the planar construction. A mesa
  blocking diode carries its own acceptance list, and an integrated blocking
  diode is accepted through the assembly it is built into. Grading either one
  here files evidence against a table that does not govern it.
- Content runs both ways and the two ways are different findings. A tabulated
  test the programme omits is coverage the project never bought. A test the
  programme adds is carried on the project's own authority, which is legitimate
  but has to be visible, because it is not evidence the table asked for.
- Order is load bearing, not presentational. The tabulated sequence opens with a
  visual inspection and an electrical measurement, puts the environmental
  stresses in the middle, and closes with a final electrical measurement and a
  final visual inspection. Each stress sits between a measurement that says what
  the diode was and a measurement that says what it became.
- A final electrical measurement moved ahead of the stresses measured a diode
  nothing had happened to yet. The programme still carries the test, the record
  still shows a pass, and the pass is about a diode that was never stressed.
- Three of the tabulated tests are stresses -- thermal shock, high temperature
  reverse bias and mechanical shock -- and a stress with no electrical
  measurement anywhere after it is a stress nobody read. The sample was spent
  and nothing was learned from it.
- A visual inspection after a stress is not a readout. A planar blocking diode
  degrades through its junction and its leakage, and neither is visible; only an
  electrical measurement separates a diode that survived from one that did not.
- Basis is the fourth axis and it cuts both ways. A tabulated every-unit test
  drawn on a sample substitutes the table and accepts the lot on a fraction of
  it. A tabulated sampled test run on every unit is stricter than the table, so
  it is reported for visibility and never held against the programme.
- A sampled test also has to draw enough of the lot to speak for it, and an
  every-unit test has to reach the whole lot. Both are counted against the lot
  size rather than taken from the word on the schedule.

## Workflow

1. Resolve the table the programme is graded against, the sampling floor and the
   completeness floor, refusing an empty table that would pass every programme.
2. Settle scope: only a planar blocking diode is graded against this table.
3. Read the proposed programme in its run order, refusing a test proposed twice,
   an unknown basis or a negative unit count.
4. Compare content both ways: tabulated tests the programme omits, and tests the
   programme adds that the table does not list.
5. Walk the run order against the tabulated order and report every pair the
   programme runs the wrong way round; an untabulated test takes no part.
6. For each stress in the programme, look for an electrical measurement later in
   the run order and name the stresses nobody read.
7. Grade each tabulated test on its basis and its unit count against the lot
   size: substitutions, every-unit tests short of the lot, samples below the
   floor, and tests run stricter than the table.
8. Work out the share of tabulated tests run soundly, hold it against the
   completeness floor with a comparison that absorbs representation error, and
   return one verdict with every finding.

## Pitfalls

- Grading the programme as a checklist. All nine tests present is the easiest
  state to reach and the one that hides the order, the readout and the basis.
- Reviewing a mesa or integrated diode against this table. The construction
  decides which list applies, and the wrong list produces a confident verdict
  about the wrong evidence.
- Treating an added test as harmless coverage. It is real work, and it is real
  work the table did not ask for, so it belongs in the record as a project
  decision rather than as tabulated evidence.
- Reading the tabulated sequence as a presentation order. A measurement moved
  ahead of the stress it was meant to read produces a pass about an unstressed
  diode.
- Accepting a visual inspection as the readout after a stress. Junction damage
  and leakage drift are not visible, so the inspection passes a diode the
  measurement would have caught.
- Counting a stress as evidence because it ran. A stress with nothing measured
  after it consumed the sample and settled nothing.
- Reading the basis off the schedule wording instead of the unit count. A test
  labelled every-unit that ran on thirty-eight of forty diodes did not reach the
  lot.
- Holding a stricter basis against the programme. A sampled test run on every
  unit exceeds the table, and reporting it as a defect pushes the project back
  towards the minimum.
- Comparing a drawn share or the completeness share against its floor by bare
  arithmetic. Both are quotients of counted units and counted tests, so a
  programme drawn exactly to the declared fraction can evaluate a unit in the
  last place under it; the comparison absorbs that while the floor stays as
  written.

## Behavior contract (gate 3)

The table resolution, the planar construction scope check, the programme read in
run order, the two-way content comparison, the run order against the tabulated
order with its inversion pairs, the post-stress electrical readout check, the
basis and unit count grading with its substitution, short-lot, short-sample and
stricter-than-table outcomes, the completeness share against its floor and the
single programme verdict are exercised by the gate 3 contract test:
scripts/test_e2008_planar_blocking_diode_acceptance.py against
scripts/e2008_planar_blocking_diode_acceptance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_planar_blocking_diode_acceptance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
