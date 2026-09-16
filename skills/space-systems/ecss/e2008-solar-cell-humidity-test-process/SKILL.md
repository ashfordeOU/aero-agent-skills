---
name: e2008-solar-cell-humidity-test-process
description: "Use when a damp heat chamber profile for solar cells is written or reviewed before the soak starts. Verify a subgroup O damp conditioning profile against ECSS-E-ST-20-08C clause 7.5.7.1.2: confirm the cell count actually drawn from subgroup O, hold the chamber at ambient pressure inside its tolerance, derive the dew point the air temperature and relative humidity produce and keep the coldest cell surface above it, hold the ramp rate and the stabilisation dwell, and confirm the soak reaches its full duration. Trigger: ecss, e-st-20-08c-clause-7-5-7-1-2, subgroup-o-cell-sample-plan, ambient-pressure-damp-chamber-profile, damp-storage-dew-point-margin, humidity-chamber-ramp-rate-limit, damp-soak-duration-compliance, cell-surface-condensation-risk."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-solar-cell-humidity-test-process, subgroup-o-cell-sample-plan, ambient-pressure-damp-chamber-profile, damp-storage-dew-point-margin, humidity-chamber-ramp-rate-limit, damp-soak-duration-compliance, cell-surface-condensation-risk]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Humidity Test Process (space-systems/ecss/e2008-solar-cell-humidity-test-process)

Use when the task is clause 7.5.7.1.2 of ECSS-E-ST-20-08C -- driving the
chamber that holds a subgroup O sample through its damp exposure. The
purpose clause says why the cells are stored damp; this one says how the
volume around them is conditioned while they are, and most of the ways
it goes wrong leave a log that reads nominal.

## Domain quick reference

- The sample is drawn from one subgroup. A count made up from another
  subgroup fills the chamber without filling the plan, because the
  cells the statistics were written against are the subgroup O ones.
- The chamber runs at ambient pressure. That is a positive requirement,
  not an absence of one: a volume that drifts into pressure drives
  moisture into an interface by a mechanism the ambient soak never
  exercises, and the result is a different test carrying this test's
  name.
- Relative humidity is a ratio, so it says nothing on its own about
  whether water will form. What decides that is the dew point -- the
  temperature the chamber air saturates at -- and a Magnus relation
  turns the air temperature and the humidity setpoint into it.
- The margin that matters is against the coldest cell surface, not the
  chamber setpoint. Whenever the chamber is still coming up the cells
  lag the air, and a front face below the dew point is under liquid
  water while every logged channel reads the profile as intended.
- Ramp rate is a coverglass concern. The bond between glass and cell
  takes the whole temperature excursion as a shear, so a ramp chosen to
  reach the setpoint quickly can crack a bond the soak was supposed to
  test intact.
- The soak clock does not start when the setpoint is reached. A
  stabilisation dwell has to pass first, or the first hours of the
  recorded soak are hours in which the cells were still climbing.

## Workflow

1. Validate the conditioning policy first: subgroup floor, ambient
   pressure and its tolerance, dew point margin, ramp ceiling,
   stabilisation dwell and soak duration. A tolerance as wide as the
   ambient pressure it qualifies is refused rather than used.
2. Count the cells the plan actually draws from subgroup O, taking a
   label from another subgroup as zero rather than as a substitute, and
   hold the count against its floor.
3. Derive the dew point from the air temperature and relative humidity
   setpoints, and the water the air carries per cubic metre alongside
   it, before any judgement is made.
4. Take the margin between the coldest declared cell surface and that
   dew point. A margin landing exactly on the floor passes; the
   comparison tolerance absorbs representation error and the floor does
   not move.
5. Check the chamber pressure against ambient inside its tolerance, the
   ramp rate against its ceiling, the stabilisation dwell and the soak
   duration against their floors. Report every finding, not the first.
6. Close on one verdict, condensation outranking the rest because it
   changes what the test is: condensation risk, sample plan deficient,
   conditioning deficient, or conditioning accepted.

## Pitfalls

- Filling the chamber to the cell count from whatever subgroup is to
  hand. The count is a subgroup O count, and a mixed load produces a
  result that belongs to no subgroup.
- Reading the humidity setpoint as a condensation check. Eighty-five
  per cent at sixty degrees and eighty-five per cent at twenty degrees
  have completely different dew points, and only one of them threatens
  a cell sitting at room temperature.
- Taking the margin against the chamber setpoint. The cells are the
  coldest thing in the volume during every ramp, so the setpoint margin
  is the one number guaranteed not to catch the condensation.
- Letting the chamber hold a small overpressure because the seal is
  easier that way. It is a different moisture ingress mechanism, and
  nothing downstream will say which one produced the degradation.
- Starting the soak clock at the setpoint. Without the stabilisation
  dwell the early hours are a ramp recorded as a soak, and the exposure
  is short by exactly the amount nobody logged.
- Comparing a derived margin against its floor by bare arithmetic. The
  dew point comes out of a logarithm and a division, which land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the floor itself is never
  relaxed.

## Behavior contract (gate 3)

The policy validation, subgroup O cell count, saturation and partial
vapour pressure, dew point and its margin against the coldest cell
surface, absolute humidity, the ambient pressure window, the ramp rate,
stabilisation dwell and soak duration checks, and the conditioning
verdict are exercised by the gate 3 contract test:
scripts/test_e2008_solar_cell_humidity_test_process.py against
scripts/e2008_solar_cell_humidity_test_process_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_solar_cell_humidity_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
