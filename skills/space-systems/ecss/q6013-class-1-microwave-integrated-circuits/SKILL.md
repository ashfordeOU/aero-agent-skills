---
name: q6013-class-1-microwave-integrated-circuits
description: "Evaluate a microwave monolithic integrated circuit selected and bought under the highest assurance class of ECSS-Q-ST-60-13C clause 4.6.5: group the supplier line by its space-evaluation standing, compute the die channel temperature from base-plate temperature, dissipated power and thermal resistance, compare it with the ceiling of the die technology, convert it into an Arrhenius median life against the required mission hours, grade the wafer-lot process-control-monitor readings and the RF parameter drift, then return a buy-as-is, buy-with-upscreening or reject disposition. Use when a Class 1 procurement needs a GaAs, GaN, InP or SiGe monolithic die judged before purchase. Trigger: ecss, q-st-60-13c, class-1-mmic-procurement, mmic-channel-temperature-derating, wafer-lot-process-control-monitor, mmic-median-life-arrhenius, gaas-phemt-die-selection, mmic-upscreening-route."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q6013-class-1-microwave-integrated-circuits, class-1-mmic-procurement, mmic-channel-temperature-derating, wafer-lot-process-control-monitor, mmic-median-life-arrhenius, mmic-upscreening-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 1 Microwave Monolithic Circuits — Selection and Purchase (space-systems/ecss/q6013-class-1-microwave-integrated-circuits)

Use when the task is selecting and buying a microwave monolithic
integrated circuit under the highest assurance class of ECSS-Q-ST-60-13C
clause 4.6.5 — deciding whether the supplier line, the thermal operating
point, the wafer-lot monitor data and the measured RF drift together
support a purchase, and on what route.

## Domain quick reference

- The supplier line, not the part number, sets the route. A line already
  taken through space evaluation or space qualification supports a
  direct purchase; a purely commercial line supports one only with an
  upscreening sequence layered on top, and supports nothing at all when
  the upscreening cannot be run.
- Wafer-lot monitor data is a gate that sits in front of both routes.
  Without process-control-monitor readings traceable to the wafer lot
  the die is an unknown, and the standing of the line does not substitute
  for them.
- The governing thermal quantity is the channel temperature of the die,
  not the base-plate or case temperature. It is
  T_channel = T_base + P_dissipated * R_thermal, and the ceiling applied
  to it belongs to the die technology: arsenide and phosphide field-effect
  processes sit lowest, heterojunction bipolar processes higher, and
  gallium-nitride processes highest.
- Life is an Arrhenius consequence of that channel temperature, referred
  to the life point the supplier demonstrated:
  t = t_ref * exp((Ea/k) * (1/T - 1/T_ref)). A die that clears the
  temperature ceiling can still fall short of the mission hours, so the
  ceiling check and the life check are two findings, not one.
- RF drift across burn-in or life is graded as a fraction of the initial
  value and as a magnitude: a gain that climbs is as much a drift finding
  as a gain that falls.
- The routes are procurement outcomes, not quality grades. A
  buy-with-upscreening disposition is a purchase decision that carries an
  obligation, and it is reported as a finding so the obligation travels
  with the decision.

## Workflow

1. Group the supplier line by its space-evaluation standing and confirm
   that wafer-lot monitor data exists; without it the route closes
   whatever the standing.
2. Compute the channel temperature from the base-plate temperature, the
   dissipated power and the thermal resistance of the mounted die.
3. Compare the channel temperature with the ceiling of the die
   technology, absorbing representation error at the boundary with a
   named tolerance rather than by raising the ceiling.
4. Convert the achieved channel temperature into a median life against
   the supplier's reference life point and activation energy, and
   compare it with the required mission hours.
5. Grade every wafer-lot monitor reading against its limit pair, naming
   each parameter that falls outside.
6. Compute the RF parameter drift as a magnitude fraction and compare it
   with the allowance.
7. Return the disposition — buy-as-is, buy-with-upscreening or reject —
   with every finding that drove it.

## Pitfalls

- Derating on case temperature. The ceiling belongs to the channel, and
  the rise across the thermal resistance is where a marginal design
  actually fails; using the base-plate figure hides the whole problem.
- Applying one ceiling to every die technology. A gallium-nitride
  ceiling used on an arsenide field-effect die passes a part that is
  tens of degrees too hot.
- Treating the temperature-ceiling check as the life check. The ceiling
  is an instantaneous limit; the mission hours are an integral over the
  Arrhenius model, and a die can clear one and fail the other.
- Accepting a commercial line because the sample parts measured well.
  Sample measurements are not lot control; the route stays
  buy-with-upscreening and the obligation is reported with it.
- Buying against a line standing when the wafer-lot monitor readings
  were never supplied. The standing describes the process, not the lot
  in front of you.
- Grading RF drift as a signed number. An upward gain shift is a drift
  finding too, so the comparison is made on the magnitude.

## Behavior contract (gate 3)

The line grouping, channel-temperature computation, ceiling comparison,
Arrhenius life conversion, wafer-lot monitor grading, RF drift grading
and route disposition are exercised by the gate 3 contract test:
scripts/test_q6013_class_1_microwave_integrated_circuits.py against
scripts/q6013_class_1_microwave_integrated_circuits_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6013_class_1_microwave_integrated_circuits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
