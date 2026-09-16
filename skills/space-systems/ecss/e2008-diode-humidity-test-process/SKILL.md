---
name: e2008-diode-humidity-test-process
description: "Use when a damp exposure loading for protection diodes is written or audited before the soak starts. Verify how a subgroup O protection diode load is arranged inside an ambient pressure chamber under ECSS-E-ST-20-08C clause 9.6.6.1.2: confirm the device count actually drawn from subgroup O, hold the chamber inside its ambient pressure band, derive the dew point the air temperature and humidity produce and keep the coldest package case above it, check the free flow left on the tray and the gap between packages, and hold the stabilisation dwell and the exposure duration. Trigger: ecss, e-st-20-08c-clause-9-6-6-1-2, subgroup-o-protection-diode-sample, protection-diode-damp-chamber-loading, diode-case-dew-point-margin, diode-tray-free-flow-fraction, protection-diode-package-spacing, protection-diode-exposure-duration."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-diode-humidity-test-process, subgroup-o-protection-diode-sample, protection-diode-damp-chamber-loading, diode-case-dew-point-margin, diode-tray-free-flow-fraction, protection-diode-package-spacing, protection-diode-exposure-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Diode Humidity Test Process (space-systems/ecss/e2008-diode-humidity-test-process)

Use when the task is clause 9.6.6.1.2 of ECSS-E-ST-20-08C -- how a
subgroup O protection diode load actually sits in the chamber while its
damp exposure runs. The purpose clause says why the devices are stored
damp; this one says how the volume around them is loaded and driven, and
a diode load is not a cell load: the parts are small, three-dimensional
and carry terminals that stand proud of the package.

## Domain quick reference

- The sample is drawn from one subgroup. Devices counted in from another
  subgroup fill the tray without filling the plan, because the
  statistics were written against the subgroup O population.
- The chamber runs inside a band around ambient. That is a positive
  requirement, not an absence of one: a volume that drifts out of the
  band pushes moisture through a package seal by a route the ambient
  soak never exercises, and the result is a different test wearing this
  test's name.
- Loading geometry is part of the exposure, not housekeeping. A diode
  shadows its neighbour, so the tray carries a free flow floor and every
  package carries a gap. Packed edge to edge, the outer row is
  conditioned and the inner rows are merely warm.
- Relative humidity is a ratio, so it says nothing on its own about
  whether water forms. What decides that is the dew point -- the
  temperature the chamber air saturates at -- and a Magnus relation
  turns the air temperature and the humidity setpoint into it.
- The margin that matters is against the coldest package case, not the
  chamber setpoint. A case below the dew point carries a water film
  bridging its terminals, and the leakage measured afterwards is a
  wet-surface artefact rather than the junction degradation the exposure
  was run to find.
- The exposure clock does not start when the setpoint is reached. A
  stabilisation dwell has to pass first, or the early hours of the
  recorded exposure are hours in which the packages were still climbing.

## Workflow

1. Validate the loading policy first: subgroup floor, ambient pressure
   band, dew point margin, tray free flow floor, package gap,
   stabilisation dwell and exposure duration. A band whose lower edge
   sits above its upper edge is refused rather than used.
2. Count the devices the plan actually draws from subgroup O, taking a
   label from another subgroup as zero rather than as a substitute, and
   hold the count against its floor.
3. Derive the tray free flow fraction and the even-spacing package gap
   from the declared geometry, refusing a load that does not fit the
   tray or a row too short to space its packages.
4. Derive the dew point from the air temperature and relative humidity
   setpoints before any judgement is made, then take the margin between
   the coldest declared package case and it. A margin landing exactly on
   the floor passes; the comparison tolerance absorbs representation
   error and the floor does not move.
5. Check the loaded device count against the planned count, the chamber
   pressure against its band, the free flow and gap against their
   floors, and the dwell and exposure against theirs. Report every
   finding, not the first.
6. Close on one verdict, condensation outranking the rest because it
   changes what the exposure measures: terminal condensation risk,
   sample plan deficient, chamber loading deficient, or chamber loading
   accepted.

## Pitfalls

- Filling the tray to the device count from whatever subgroup is to
  hand. The count is a subgroup O count, and a mixed load produces a
  result that belongs to no subgroup.
- Treating the tray layout as housekeeping. Free flow and package gap
  decide which devices were exposed at all, and a crowded tray returns a
  pass earned by the outer row alone.
- Reading the humidity setpoint as a condensation check. Eighty-five per
  cent at sixty degrees and eighty-five per cent at twenty degrees have
  completely different dew points, and only one of them threatens a
  package sitting at room temperature.
- Taking the margin against the chamber setpoint. The devices are the
  coldest thing in the volume during every ramp, so the setpoint margin
  is the one number guaranteed not to catch the condensation.
- Letting the chamber hold a small overpressure because the seal is
  easier that way. It is a different ingress mechanism through the
  package, and nothing downstream will say which one produced the drift.
- Starting the exposure clock at the setpoint. Without the stabilisation
  dwell the early hours are a ramp recorded as an exposure, and the soak
  is short by exactly the amount nobody logged.
- Comparing a derived margin against its floor by bare arithmetic. The
  dew point comes out of a logarithm and a division, which land a few
  units in the last place either side of a limit on different hosts, so
  the comparison absorbs that error while the floor itself is never
  relaxed.

## Behavior contract (gate 3)

The policy validation, subgroup O device count, saturation pressure, dew
point and its margin against the coldest package case, the tray free
flow fraction and package gap, the ambient pressure band, the loaded
count against the planned count, the stabilisation dwell and exposure
duration checks, and the loading verdict are exercised by the gate 3
contract test: scripts/test_e2008_diode_humidity_test_process.py against
scripts/e2008_diode_humidity_test_process_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_diode_humidity_test_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
