---
name: q7045-test-environment-conditions
description: "Validate the laboratory environment a metallic mechanical test was run in against ECSS-Q-ST-70-45C: grade the recorded temperature and relative humidity series against their permitted bands, measure how long and how far each excursion ran before deciding whether it invalidates the run, derive the conditioning time a moisture-sensitive or cold-soaked piece owes before loading, and confirm the surrounding atmosphere suits a material that oxidises. Use when reviewing a laboratory environmental log, accepting a test report from a supplier or deciding whether an out-of-band excursion costs the result. Trigger: ecss, q-st-70-45c, metallic-test-laboratory-environment, test-ambient-temperature-band, test-relative-humidity-control, test-environment-excursion, test-piece-conditioning-time."
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
  tags: [ecss, q-st-70-45c-metallic-mechanical-testing, q-st-70-45c, q7045-test-environment-conditions, metallic-test-laboratory-environment, test-ambient-temperature-band, test-relative-humidity-control, test-environment-excursion]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Metallic Mechanical Testing — Test Environment Conditions (space-systems/ecss/q7045-test-environment-conditions)

Use when the task is the environmental-conditions clause of
ECSS-Q-ST-70-45C: what the laboratory around the test has to be held at, how
an excursion outside that band is judged, and what conditioning the piece owes
before the machine takes up load.

## Domain quick reference

- The permitted band and the reported reference are two different things. A
  laboratory is allowed a range, but the result is reported against a stated
  reference condition, so a run legitimately inside the band still carries the
  temperature it actually happened at.
- An excursion is judged on depth and duration together. A momentary blip a
  fraction of a degree outside the band while the machine is idle is not the
  same event as a sustained departure during loading, and grading on the peak
  reading alone throws away good runs and keeps bad ones.
- What matters is the environment during the loaded part of the run. The
  conditioning period and the loaded period are different windows, and an
  excursion in the first is recoverable by extending the soak while one in the
  second is not.
- Humidity is not a comfort parameter for every material. Magnesium alloys and
  some high-strength steels respond to moisture, and a stress-corrosion or
  sustained-load test in an uncontrolled room is measuring the room.
- Condensation is a hard stop, not a humidity reading. A piece brought up from
  a cold soak into a humid room wets, and a wetted gauge length changes both
  the surface state and any strain gauge bonded to it, so the dew point is
  checked against the piece temperature, not against the room temperature.
- Conditioning time follows the section, because it is a thermal-equilibration
  problem. A thin strip reaches room temperature in minutes and a thick block
  does not, and a piece loaded before equilibrium carries a gradient the
  extensometer will read as strain.
- Atmosphere is a material question above a threshold temperature. An alloy
  that oxidises or takes up gas at temperature cannot be tested in air and
  have the result attributed to the material rather than to the surface it
  grew during the soak.

## Workflow

1. Validate the recorded series: each sample needs a time, a temperature and,
   where humidity is controlled, a relative humidity, and the series has to be
   in increasing time order.
2. Grade each sample against the permitted temperature band and, where the
   material or the test type calls for it, the permitted humidity band.
3. Group consecutive out-of-band samples into excursions and measure each
   one's depth and duration rather than reporting a worst reading.
4. Decide each excursion against its own allowance, and separate an excursion
   in the conditioning window from one in the loaded window, because only the
   first is recoverable.
5. Check the dew point against the test-piece temperature, and treat a piece
   at or below the dew point as a condensation stop regardless of the room
   humidity reading.
6. Derive the conditioning time the section owes and compare it with the soak
   actually held before loading.
7. Decide the atmosphere from the material's sensitivity and the test
   temperature, and close with a verdict naming every finding that bears on
   whether the result is attributable.

## Pitfalls

- Grading the environment on the peak reading. Depth without duration
  condemns a momentary blip and excuses a slow drift that sat just outside the
  band for the whole loaded run.
- Applying the conditioning-window allowance to the loaded window. The soak
  can be extended; the loading cannot be re-run in a different room.
- Reading humidity compliance as freedom from condensation. The room can be
  comfortably inside its humidity band while a piece just out of a cold soak
  is below the dew point and wetting.
- Conditioning by the clock rather than by the section. The same soak that
  equilibrates a thin strip leaves a thick block with a gradient, and the
  gradient reads as strain.
- Testing an oxidation-sensitive alloy hot in air and attributing the result
  to the material. Above the threshold the surface grown during the soak is
  part of what was pulled.
- Widening the band to absorb a reading that sits exactly on it. The equality
  is a representation question handled by the tolerance inside the comparison;
  the environmental limits stay as specified.

## Behavior contract (gate 3)

The series validation, band grading, excursion grouping with depth and
duration, the conditioning-versus-loaded window rule, the dew-point
condensation stop, the section-derived conditioning time and the atmosphere
decision are exercised by the gate 3 contract test:
scripts/test_q7045_test_environment_conditions.py against
scripts/q7045_test_environment_conditions_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7045_test_environment_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
