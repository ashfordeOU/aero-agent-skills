---
name: q7006-data-for-design
description: "Derive the thermal and optical design data a spacecraft needs from a particle and UV radiation campaign under ECSS-Q-ST-70-06C. Use when measured beginning-of-life and end-of-life absorptance and emittance have to become a hot case and a cold case rather than a table. Builds each case from the corner that hurts, raising degraded absorptance by its uncertainty against the lowest emittance lowered by its own, reads both through the absorptance over emittance ratio and the equilibrium temperature, refuses to issue data where the test never reached the mission fluence, dose or temperature extremes, and grades the result against the thermal allocation. Trigger: ecss, q-st-70-06, end-of-life-optical-properties, solar-absorptance-emittance-ratio, thermal-hot-and-cold-case, radiation-test-envelope-coverage, equilibrium-temperature-from-alpha-epsilon, thermal-allocation-grading."
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
  tags: [ecss, q-st-70-06-particle-uv-radiation-testing-scope, q7006-data-for-design, end-of-life-optical-properties, solar-absorptance-emittance-ratio, thermal-hot-and-cold-case, radiation-test-envelope-coverage, thermal-allocation-grading]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Particle and UV Radiation Testing — Data for Design (space-systems/ecss/q7006-data-for-design)

Use when the task is the data step of an ECSS-Q-ST-70-06C particle or UV
campaign — turning the measured beginning-of-life and end-of-life
absorptance and emittance into the hot-case and cold-case numbers a
thermal and optical design can actually be closed on.

## Domain quick reference

- A campaign produces four optical numbers and a design needs two pairs.
  The hot case is the worst absorptance the surface ever has against the
  worst emittance it ever has; the cold case is the opposite corner.
  Pairing a beginning-of-life absorptance with an end-of-life emittance
  describes a spacecraft that does not exist.
- Uncertainty is applied in the direction that hurts, per case. It
  raises the absorptance and lowers the emittance for the hot case and
  does the reverse for the cold one, and it is applied to the design
  value, not averaged into the measurement.
- The ratio of absorptance to emittance is the quantity that sets the
  equilibrium temperature of a sun-facing surface; the temperature
  itself follows from that ratio and the solar flux through a fourth
  root, which is why a ratio that doubles moves the temperature by only
  about nineteen percent.
- Degradation usually moves both numbers and rarely by the same
  fraction. Absorptance climbs steeply under ultraviolet while
  emittance barely shifts, so the ratio growth is the number the thermal
  budget actually feels.
- Design data may only be issued over the range the test reached. A
  mission fluence, ultraviolet dose or temperature extreme beyond the
  tested envelope makes the issued value an extrapolation wearing a
  qualification label.
- Where the programme has allocated an end-of-life absorptance, an
  emittance floor or a ratio, grading the measured data against it
  immediately tells the thermal budget it has moved.

## Workflow

1. Read the material, the four measured optical values, the two
   uncertainties and the solar flux the design is closed at.
2. Compare the tested envelope with the mission envelope on fluence,
   ultraviolet dose and both temperature extremes, and record every axis
   the test did not reach.
3. Build the hot case: the higher absorptance raised by its uncertainty
   against the lower emittance lowered by its own, both clamped into the
   physically available range.
4. Build the cold case from the opposite corner the same way.
5. Compute the ratio and the equilibrium temperature for each case.
6. Compute the ratio at beginning and end of life and the growth
   between them.
7. Grade the hot case against any allocated absorptance, emittance floor
   or ratio the programme has issued.
8. Emit both cases, the ratios, the growth, the envelope shortfalls and
   every finding; data is issuable only when no finding stands.

## Pitfalls

- Issuing the end-of-life absorptance alone. The cold case needs the
  undegraded corner, and a design closed only on the hot case can fail
  its heater budget instead of its radiator budget.
- Averaging the uncertainty into the measured value before building the
  cases. It then pulls both cases toward each other and removes exactly
  the margin it was there to provide.
- Assuming emittance is unaffected. It usually moves less than
  absorptance, not not at all, and the ratio is sensitive to both.
- Issuing data past the tested envelope because the shortfall is small.
  A tenth of a decade of fluence is small until the degradation has not
  saturated, and nothing in the data says whether it has.
- Reporting the ratio growth as a temperature rise. The fourth root
  makes the temperature far less sensitive than the ratio, and quoting
  one for the other alarms or reassures the wrong people.

## Behavior contract (gate 3)

The physical-range clamps, the absorptance over emittance ratio, the
equilibrium temperature, the envelope coverage check, the hot and cold
design pairs, the ratio growth and the allocation grading are exercised
by the gate 3 contract test: scripts/test_q7006_data_for_design.py
against scripts/q7006_data_for_design_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7006_data_for_design.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
