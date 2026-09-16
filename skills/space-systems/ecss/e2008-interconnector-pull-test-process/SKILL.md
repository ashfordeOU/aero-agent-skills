---
name: e2008-interconnector-pull-test-process
description: "Use when a pull-test run on a photovoltaic assembly is reviewed from its records: check each tab against the speed window, turn speed and article stiffness into the force ramp rate and the time to the parting force, confirm the recorder places enough samples on the rising ramp and the load cell spans the peak without swamping it, reject a trace that starts pre-loaded or dips on the way up, and reconcile pulled tabs against planned. Verify that an interconnector pull test was driven the way ECSS-E-ST-20-08C clause 6.4.3.10.2 requires: a force that rises steadily on every tab, applied at a crosshead speed inside the declared window until the joint parts. Trigger: ecss, e-st-20-08c, clause-6-4-3-10-2, interconnector-pull-test-process, interconnector-crosshead-speed-window, interconnector-pull-force-ramp-rate, pull-trace-monotonic-rise, pull-load-cell-range-adequacy."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-interconnector-pull-test-process, interconnector-crosshead-speed-window, interconnector-pull-force-ramp-rate, pull-trace-monotonic-rise, pull-load-cell-range-adequacy]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Interconnector Pull Test Process (space-systems/ecss/e2008-interconnector-pull-test-process)

Use when the task is the test-process rule of ECSS-E-ST-20-08C clause
6.4.3.10.2 — judging whether a pull test on the interconnectors of a
photovoltaic assembly was actually carried out the way the clause describes: a
force applied to each tab that rises steadily, at a speed that was declared
before the run rather than read off the machine afterwards.

## Domain quick reference

- The speed is the process variable the clause fixes, because the bond material
  is rate sensitive. A solder or weld joint pulled quickly reads stronger than
  the same joint pulled slowly, so a run outside the declared speed window
  produces numbers that cannot be compared with any other run.
- Crosshead speed is a displacement rate, not a force rate. The force rate the
  joint sees is the speed multiplied by the stiffness of the machine, fixture
  and tab together, and it is the force rate that sets how long the pull lasts
  and therefore how much of it the recorder can see.
- Sampling is judged against the rising ramp, not against the whole file. A pull
  that reaches its parting force in a fraction of a second leaves very few
  points on the way up at a modest sample rate, and a handful of points shows
  that a force was reached, not that it rose steadily.
- A load cell can fail in both directions. One whose range sits under the
  parting force saturates and reports its own range as the result; one whose
  range dwarfs the force puts the whole pull inside the cell's noise band, and
  neither record supports a strength number.
- The trace tells you whether one pull happened or two. A first sample already
  carrying load means the tab was seated against the fixture, and a dip on the
  way up means the joint slipped and was reloaded, so the peak that follows
  belongs to an article that has already been worked.

## Workflow

1. Validate the declared speed window and check the speed of every tab against
   it, treating a speed sitting exactly on either bound as conformant — the
   tolerance belongs on the comparison, never on the window.
2. Turn each tab's speed and the declared article stiffness into the force ramp
   rate, and the ramp rate with the expected parting force into the time the
   pull takes.
3. Multiply that time by the recorder sample rate and compare the result with
   the minimum number of points a rising ramp needs to be reconstructable.
4. Check the load cell from both sides: the parting force must sit inside the
   range, and it must use enough of the range to be resolved rather than
   sitting in the cell's noise.
5. Read each recorded trace: the first sample must be effectively unloaded, and
   the force must not fall anywhere between the start and the peak. Ignore the
   collapse after the peak, which is the joint parting and is what the test is
   for.
6. Reconcile the tabs pulled against the tabs planned, reporting a planned tab
   never pulled, a tab pulled twice and a tab pulled that is not on the plan as
   three distinct findings.
7. Report the per-tab rate, duration, sample count and load-cell use alongside
   every finding and the run verdict.

## Pitfalls

- Reporting the crosshead speed as the loading rate. The joint sees force per
  second, not millimetres per minute, and the conversion runs through a
  stiffness that changes with the fixture; two runs at the same speed on
  different fixtures load the joints at different rates.
- Judging the sample rate against the length of the record. The only part of
  the trace that has to be resolved is the rise to the peak, and that can be a
  few hundred milliseconds even in a run that recorded for a minute.
- Choosing a load cell for its capacity. An interconnector parts at a few
  newtons; a cell sized for the tensile machine's rating turns every pull into
  a noise measurement while every record still looks complete.
- Accepting a trace that dips and recovers. The recovery peak comes from a joint
  that has already slipped, so it understates a good joint and can overstate a
  damaged one; the run gives one number per tab or none.
- Letting a pre-load pass because the peak looks reasonable. A tab already
  seated against its fixture starts the ramp part-way up, which shortens the
  rise, cuts the sample count on it, and moves the rate the joint actually saw.
- Reconciling by count. Three planned and three pulled hides one tab pulled
  twice and one never pulled; the reconciliation is done on the identifiers.

## Behavior contract (gate 3)

The speed-window check, ramp rate and pull duration derivation, sample count on
the rising ramp, two-sided load-cell adequacy, pre-load and monotonic-rise trace
checks and the tab reconciliation are exercised by the gate 3 contract test:
scripts/test_e2008_interconnector_pull_test_process.py against
scripts/e2008_interconnector_pull_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_interconnector_pull_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
