---
name: e1011-env-ergonomics
description: "Use when assess environmental ergonomics for a crewed space habitat or EVA station under ECSS-E-ST-10-11 §4.6.5: evaluate noise sound-pressure levels against habitable-area and sleep-quarter limits, verify whole-body vibration doses against daily exposure thresholds, confirm illuminance levels suit each operational area type, check atmospheric pressure, oxygen and carbon-dioxide partial pressures, and humidity against habitable limits, verify operative temperature and radiant-asymmetry boundaries, and audit EVA suit internal atmosphere for pressure, oxygen fraction, and CO₂ concentration. Trigger: ecss, e-st-10-system-scope, human-factors, environmental-ergonomics, noise, vibration, lighting, atmosphere, eva."
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
  tags: [ecss, e-st-10-system-scope, human-factors, environmental-ergonomics, noise, vibration, lighting, atmosphere, eva]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Human Factors — Environmental Ergonomics (space-systems/ecss/e1011-env-ergonomics)

Use when the task is the environmental ergonomics assessment of a crewed
space habitat or EVA station under ECSS-E-ST-10-11 §4.6.5 — checking noise,
vibration, lighting, cabin atmosphere, thermal environment, and EVA suit
atmosphere against the defined limits for each domain.

## Domain quick reference

Environmental ergonomics in ECSS-E-ST-10-11 §4.6.5 spans six domains, each
with its own metric and limit set.

- **Noise** — A-weighted sound pressure level (dB(A)) compared against area
  type limits: 55 dB(A) for inhabited operational areas, 50 dB(A) for sleep
  quarters, and 85 dB(A) for short-term intermittent exposure (< 15 min/day).
  Warning alarms must exceed the local background level by at least 10 dB.
- **Vibration** — Frequency-weighted whole-body RMS acceleration (m/s²,
  ISO 2631-1 basis).  The daily action value for exposures ≥ 1 h is 0.5 m/s²;
  for exposures < 1 h the limit rises to 1.0 m/s².
- **Lighting** — Illuminance (lux) matched to the area function: 300–500 lux
  for visual-task areas, ≥ 100 lux for general habitable zones, ≥ 10 lux for
  emergency lighting, and ≤ 50 lux for sleep quarters (adjustable to darkness).
- **Atmosphere** — Four parameters are evaluated simultaneously: total cabin
  pressure (70.3–101.3 kPa), oxygen partial pressure (19.5–23.1 kPa), CO₂
  partial pressure (≤ 0.70 kPa continuous), and relative humidity (25–75 %).
  Each parameter carries its own finding; all four must pass.
- **Temperature** — Operative temperature (18–26 °C), radiant asymmetry
  between the warmest and coolest surface visible to the occupant (≤ 10 °C
  delta), and mean air velocity at the occupant position (≤ 0.20 m/s).
- **EVA suit atmosphere** — Internal suit pressure (25–101.3 kPa), O₂ mole
  fraction (≥ 0.21), and suit CO₂ partial pressure (≤ 1.0 kPa).  These
  limits are independent of the cabin atmosphere checks.

A station passes environmental ergonomics only when every domain returns
compliant; a partial-pass is not a pass.

## Workflow

1. Identify every crewed zone or EVA station to be assessed and assign each
   zone an area type (task, general, emergency, sleep) and an exposure type
   (continuous, sleep, intermittent).
2. For each zone, measure or obtain the six domain inputs: noise SPL, vibration
   RMS, illuminance, atmospheric composition, temperature metrics, and (for EVA
   stations) suit atmosphere parameters.
3. Run the noise check per zone: compare the A-weighted SPL against the limit
   for its exposure type; flag any excess and separately verify alarm audibility
   margin where alarms are fitted.
4. Run the vibration check: apply the short-duration limit (< 1 h) or the 8-h
   reference value as appropriate; report the axis and duration alongside any
   finding.
5. Run the lighting check: verify illuminance falls within the range defined for
   the zone's area type; flag both under-illumination and over-illumination for
   task and sleep areas.
6. Run the atmosphere check with all four parameters in a single call; accumulate
   findings for each parameter that falls outside its range.
7. Run the temperature check: verify operative temperature, radiant asymmetry,
   and air velocity independently; accumulate any findings.
8. For EVA stations, run the EVA suit atmosphere check: pressure, O₂ fraction,
   and suit CO₂; accumulate findings.
9. Aggregate all domain findings per zone.  A zone is ergonomically compliant
   only when every domain's finding list is empty.  Report the count of non-
   compliant zones and list each outstanding finding to drive corrective action.

## Pitfalls

- Applying the 8-h vibration limit to a short-duration exposure understates
  the allowable level; the short-exposure limit (1.0 m/s²) is higher than the
  8-h reference and should not be treated as equivalent.
- Treating the CO₂ check as passed when only a single reading is below the
  limit — the limit is for continuous exposure; a single sample from a quiescent
  period can mask a transient peak that exceeds the threshold.
- Using photopic illuminance alone and neglecting glare or luminance contrast
  — the ECSS check covers the illuminance level, but a surface that meets the
  lux value while introducing high luminance contrast around displays can still
  impair visual performance.
- Running the EVA suit atmosphere check against cabin-atmosphere limits — the
  EVA suit CO₂ limit (1.0 kPa) is more permissive than the habitable-area
  continuous limit (0.70 kPa); applying the cabin limit to the suit gives a
  false non-compliance for nominal suit operations.
- Treating radiant asymmetry as a single absolute temperature rather than the
  differential between the warmest and coolest radiant surface — only the delta
  is compared against the 10 °C limit, not either surface temperature in
  isolation.

## Behavior contract (gate 3)

The noise, vibration, lighting, atmosphere, temperature, and EVA suit logic
is exercised by the gate 3 contract test:
scripts/test_e1011_env_ergonomics.py against
scripts/e1011_env_ergonomics_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1011_env_ergonomics.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
