---
name: q6012-mmic-thermal-analysis
description: "Estimate the junction temperature of a die-form MMIC and trace the heat flow path through its mounting under ECSS-Q-ST-60-12C clause 7.2.5: walk the stack from the dissipating area downwards, let the heat spread at the declared cone angle, compute each layer's conduction resistance over the footprint it actually sees, sum them, raise the reference surface by the dissipated power, add the peak-to-mean non-uniformity of a multi-finger area, and grade the result against the derated limit. Use when a die attach, carrier or baseplate temperature changes, power is reallocated, or attach voiding is reported. Names the layer that dominates the path. Trigger: ecss, q-st-60-12c, mmic-junction-temperature, mmic-thermal-resistance, die-attach-voiding, mmic-heat-spreading, multi-finger-channel-temperature, mmic-temperature-derating."
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
  tags: [ecss, q-st-60-mmic-scope, q6012-mmic-thermal-analysis, mmic-junction-temperature, mmic-thermal-resistance, die-attach-voiding, mmic-heat-spreading, multi-finger-channel-temperature]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Junction Temperature and Heat Flow Path (space-systems/ecss/q6012-mmic-thermal-analysis)

Use when the task is the thermal analysis of ECSS-Q-ST-60-12C clause
7.2.5 — predicting the junction temperature of a die-form MMIC and
identifying the path its heat takes through the die, the attach and the
mounting on the way to the reference surface.

## Domain quick reference

- Junction temperature is not a property of the die. It is the reference
  surface temperature plus the dissipated power through everything
  between the channel and that surface, so the same die runs at
  different junction temperatures on different carriers, and a thermal
  result quoted without its reference surface is not a result.
- Heat leaving a small dissipating area does not travel as a column. It
  spreads outwards as it descends, so each layer conducts over a larger
  footprint than the one above it and a thin, poor conductor high in the
  stack costs far more than the same material lower down. The spreading
  cone is a modelling assumption, conventionally 45 degrees, and it is
  declared rather than assumed silently.
- The stack is a series chain in which one link normally dominates. On a
  GaAs die over a good attach and a metal carrier that link is usually
  the die itself, because it is both the poorest conductor and the layer
  where the footprint is smallest. Naming the dominant layer turns the
  result into an action; a total alone does not.
- Voiding in the die attach removes contact area rather than thinning
  the layer, so it raises that layer's resistance in proportion to the
  area lost. Past the fraction the attach process allows it is a process
  finding to be fixed, not a derating to be absorbed into the model.
- A multi-finger active area is not isothermal. Each finger is warmed by
  its neighbours, so the hottest finger runs above the mean rise the
  stack resistance predicts, and it is that peak — not the mean — that
  the derated limit applies to. A single finger, and a symmetric pair,
  are uniform by construction.

## Workflow

1. Validate the dissipating footprint and the mounting stack: each
   layer's name, thickness, conductivity and, where it is an attach
   layer, its void fraction. A non-positive dimension or a void fraction
   at or beyond unity is an input error.
2. Reduce each layer's conductivity for the contact area voiding
   removes.
3. Walk the stack downwards, computing each layer's conduction
   resistance over the footprint the heat has spread to by the time it
   arrives, and grow that footprint by the spreading cone before moving
   to the next layer.
4. Sum the layer resistances into a source-to-reference value and record
   each layer's share of it.
5. Raise the reference temperature by the dissipated power through that
   resistance to obtain the mean junction temperature.
6. Apply the peak-to-mean non-uniformity of the multi-finger area to
   obtain the peak channel temperature.
7. Derate the maximum junction temperature by the declared margin and
   compare the peak against it, absorbing floating-point representation
   error at the boundary with a named tolerance rather than by raising
   the limit.
8. Report the total resistance, the dominant layer, the mean and peak
   temperatures, the margin, and every finding: limit exceeded, attach
   voiding beyond process, and a layer carrying most of the path.

## Pitfalls

- Grading the mean junction temperature against the limit. The limit
  applies to the hottest channel, and on a multi-finger device the peak
  sits above the mean; grading the mean passes parts that run hot.
- Quoting a junction temperature without its reference surface. The
  number is a rise added to a baseplate, case or carrier temperature,
  and the same rise on a hotter mounting is a different verdict.
- Modelling each layer over the source footprint. Ignoring spreading
  overstates the resistance of the thick lower layers and hides that the
  thin upper ones are where the design lever actually is.
- Treating attach voiding as a modelling derate. Voiding beyond the
  process allowance is a manufacturing finding; absorbing it into a
  reduced conductivity makes the analysis pass a part that should have
  been rejected.
- Reporting only a total thermal resistance. Without the per-layer
  shares the result gives no direction, and effort goes to the carrier
  when the die or the attach is carrying most of the path.
- Raising the limit so an exact-equality case passes. An equality at the
  limit is a representation question, handled by the tolerance inside
  the comparison, and the derated limit stays as specified.

## Behavior contract (gate 3)

The stack validation, voiding reduction, spreading resistance for both
the square and rectangular source, footprint growth, series summation,
junction and peak channel temperature, derating and the full assessment
are exercised by the gate 3 contract test:
scripts/test_q6012_mmic_thermal_analysis.py against
scripts/q6012_mmic_thermal_analysis_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q6012_mmic_thermal_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
