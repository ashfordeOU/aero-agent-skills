---
name: e2008-humidity-test-general-provisions
description: "Use when verify that the mission-specific environmental conditions of a photovoltaic assembly humidity test are captured in the assembly control drawing before the test starts, under ECSS-E-ST-20-08C clause 5.5.1.4.2: envelope the declared ground phases into a worst-case relative-humidity, air-temperature and cumulative-exposure requirement, apply the agreed margin factors, check the drawing declaration carries and covers every parameter without over-testing, and confirm the drawing revision was issued no later than the test start date. Refuses a malformed mission phase and flags omissions, shortfalls, over-declaration and late capture. Trigger: ecss, e-st-20-08c, photovoltaic-assembly-humidity-test, assembly-control-drawing, mission-environmental-envelope, humidity-exposure-declaration, pre-test-capture, ground-phase-exposure-duration."
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
  tags: [ecss, e-st-20-08-photovoltaic-scope, e2008-humidity-test-general-provisions, photovoltaic-assembly-humidity-test, assembly-control-drawing, mission-environmental-envelope, humidity-exposure-declaration, pre-test-capture]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Humidity Test — General Provisions (space-systems/ecss/e2008-humidity-test-general-provisions)

Use when the task is the preparatory step of the humidity test of
ECSS-E-ST-20-08C clause 5.5.1.4.2 — deciding whether the assembly control
drawing of a photovoltaic assembly already carries the mission-specific
environmental conditions the test is to be run at, and carries them from a
revision issued before the test starts.

## Domain quick reference

- The humidity exposure a photovoltaic assembly has to survive is a ground
  phase, not an orbit phase: warehouse storage, road or sea transport,
  integration-hall dwell and launch-site stand-by. Each phase contributes its
  own relative humidity, air temperature and duration, and the test condition
  is the envelope of the set, not the worst single phase read in isolation.
- Humidity and temperature envelope by maximum; exposure duration envelopes by
  sum. A build that spends three short spells at 85 % relative humidity has the
  same peak as one long spell but a different accumulated dose, and moisture
  ingress through the encapsulant is dose-driven.
- The drawing declares a margined condition, not the raw envelope. Peak
  humidity and temperature are already worst cases so they usually carry unit
  uplift, while duration carries a schedule reserve because ground campaigns
  slip. Relative humidity is capped at saturation however generous the agreed
  factor is — beyond it the exposure is condensing, which is a different test.
- Over-declaration is a real defect, not conservatism. A humidity level or a
  dwell far above the margined requirement stresses the encapsulant, the
  interconnect and the coverglass adhesive for no mission reason, and can
  induce a failure the flight article would never have seen.
- Capture order is what the clause buys. A drawing revision issued after the
  test has started records what was done rather than defining what was to be
  done, so the revision date is compared with the test start date.

## Workflow

1. Validate each declared mission phase: a named phase carrying a relative
   humidity within saturation, an air temperature above absolute zero and a
   positive duration. A missing quantity is an input error, not a zero.
2. Envelope the phases — maximum humidity, maximum temperature, summed
   duration — and record which phase drives the peak so the envelope can be
   traced back to a mission event.
3. Apply the agreed per-parameter margin factors to obtain the condition the
   drawing has to declare, capping relative humidity at saturation. Refuse a
   factor below unity: a margin never shrinks the mission value.
4. Read the declaration off the drawing revision and list any required
   parameter it omits; an omitted parameter is reported, never defaulted.
5. Compare each declared value with its margined requirement, absorbing
   floating-point representation error at the boundary with a named relative
   tolerance rather than by moving the requirement.
6. Flag any declared value above the margined requirement by more than the
   agreed over-test factor.
7. Compare the revision date with the test start date and report the whole
   assessment: envelope, required declaration, per-parameter comparison, and
   every finding — omission, shortfall, over-declaration, late capture.

## Pitfalls

- Taking the worst single phase as the test condition. The peak is right for
  humidity and temperature but wrong for duration; the assembly accumulates
  dose across every ground phase, so the durations are summed.
- Defaulting an omitted parameter to a house value. A drawing that does not
  declare the exposure duration has not defined the test, and silently filling
  it in destroys the very traceability the clause exists for.
- Treating a large declared value as automatically safe. Over-declaration is
  reported alongside shortfall, because an over-test can fail an assembly that
  would have flown.
- Allowing a margin factor below unity to reconcile a drawing with a mission
  that outgrew it. The finding is the shortfall; the fix is a new revision, not
  a smaller factor.
- Accepting a revision issued during or after the test run. The conditions have
  to exist on the drawing before testing, so the revision date is part of the
  assessment and not a bookkeeping detail.
- Reading relative humidity above saturation as a stronger requirement. It is a
  malformed input and is refused, because condensing exposure is tested and
  declared differently.

## Behavior contract (gate 3)

The phase validation, envelope construction, margin application, omission
detection, per-parameter comparison, over-test detection and capture-order
check are exercised by the gate 3 contract test:
scripts/test_e2008_humidity_test_general_provisions.py against
scripts/e2008_humidity_test_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_humidity_test_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
