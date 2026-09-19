---
name: q7021-equipment-and-facility-control
description: "Verify that a flammability test facility is fit to run an ECSS-Q-ST-70-21C screening before any specimen is burned: chamber, gas supply and ignition source. Use when a test date is being confirmed and the calibration status, the delivered oxygen concentration and the igniter settings all have to be shown inside their windows on that date. Computes the oxygen fraction the supply lines actually deliver from their purities and set flows rather than trusting the set point, compares it with the target through a named tolerance, grades every calibration against the planned date, checks flame height, application time and chamber leak rate, and separates a blocking finding from an advisory one. Trigger: ecss, q-st-70-21, flammability-facility-readiness, blended-oxygen-concentration, supply-gas-purity, igniter-flame-calibration, calibration-due-date-check, chamber-leak-rate-limit."
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
  tags: [ecss, q-st-70-21-flammability-screening-scope, q7021-equipment-and-facility-control, flammability-facility-readiness, blended-oxygen-concentration, supply-gas-purity, igniter-flame-calibration, chamber-leak-rate-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability Screening — Equipment and Facility Control (space-systems/ecss/q7021-equipment-and-facility-control)

Use when the task is the quality-assurance step that stands in front of
an ECSS-Q-ST-70-21C screening run — showing that the chamber, the gas
supply and the ignition source were under control on the day the
specimens were burned, so the result describes the material rather than
the installation.

## Domain quick reference

- The atmosphere the specimens see is not the flow-controller set
  point. It is what the two supply lines deliver together, so the
  purity of the oxygen line and the oxygen carried as an impurity in
  the diluent both enter the arithmetic, and at a tight tolerance the
  impurity term is often the one that decides.
- The concentration tolerance is two sided and narrow. Flammability
  rises steeply with oxygen, so a blend a few tenths of a percentage
  point rich turns a screening result into a slightly different test,
  and one a few tenths lean quietly clears materials that should not
  have cleared.
- A calibration is graded against the planned test date, not against
  the day somebody looked. A certificate that is valid today and
  expires before the campaign runs is an expired calibration for that
  run, and the distinction is invisible in a folder of certificates.
- Expiring inside the campaign is worth saying out loud without
  stopping the run. It is the finding that lets a campaign be
  rescheduled rather than repeated.
- The ignition source is an input, not a fixture. Flame height and
  application time both sit in windows, and an igniter drifting out of
  one of them changes the energy the specimen receives, which changes
  the burn length that is then compared with a limit.
- A leaking chamber cannot hold the atmosphere that was blended for it.
  The leak rate is therefore part of the atmosphere check, not a
  separate housekeeping item.

## Workflow

1. Resolve the planned test date; everything else is graded against it.
2. Compute the delivered oxygen fraction from the set flows, the oxygen
   line purity and the oxygen impurity in the diluent, refusing a
   negative flow, a purity outside zero to one, and a pair of lines
   delivering nothing at all.
3. Compare the delivered concentration with the target through the
   two-sided tolerance, counting a deviation exactly on the tolerance
   as inside it rather than moving the tolerance.
4. Grade each declared calibration against the planned date: expired
   when it falls before the run, due soon when it falls inside the
   warning window, in date otherwise.
5. Check the ignition source against its flame-height and
   application-time windows, counting a value exactly on a window edge
   as inside it, and report each parameter that sits outside.
6. Check the chamber leak rate against its limit on the same
   convention.
7. Sort the findings: an off-target atmosphere, an expired calibration,
   an out-of-window igniter and a leaking chamber block the run; a
   calibration falling due inside the campaign is advisory. The
   facility is ready only when nothing blocks.

## Pitfalls

- Recording the flow-controller set point as the test atmosphere. It is
  a demand, not a measurement, and the supply purities sit between the
  two.
- Ignoring the oxygen carried in the diluent. Industrial nitrogen is
  not oxygen free, and at a half-point tolerance that impurity alone
  can put the blend outside it.
- Grading calibration certificates against today. The run is in the
  future, and a certificate expiring between the two is expired for the
  run.
- Treating the igniter as a fixture that needs no record. It sets the
  energy delivered to the specimen, so an igniter drift is a burn
  length shift in every result of the campaign.
- Filing the chamber leak rate under housekeeping. A chamber that
  cannot hold the blend was never running the atmosphere the report
  will claim.
- Widening a window so a value on its edge passes. Equality at the edge
  is a representation question, handled by the tolerance inside the
  comparison; the window itself stays as specified.

## Behavior contract (gate 3)

The blend arithmetic, two-sided concentration tolerance,
calibration grading against the planned test date, warning-window
handling, ignition-source window checks, leak-rate comparison and the
blocking-versus-advisory split are exercised by the gate 3 contract
test: scripts/test_q7021_equipment_and_facility_control.py against
scripts/q7021_equipment_and_facility_control_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_q7021_equipment_and_facility_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
