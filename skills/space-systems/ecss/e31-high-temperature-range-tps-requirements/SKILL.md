---
name: e31-high-temperature-range-tps-requirements
description: "Evaluate a thermal-protection item running above four hundred and seventy kelvin against the high-temperature design constraints of ECSS-E-ST-31 clause 4.2.2 and its thermal-protection annex: compare the uncertainty-inflated peak against the material maximum use temperature, spend the recession allowance over the exposure and check what thickness is left, carry the remaining thickness into a bondline temperature the substrate can survive, and walk the surface optical properties out over the reuse cycles they are qualified for. Use when an ablator, tile or hot structure has been grouped into the high-temperature range and its sizing has to be defended. Trigger: ecss, e-st-31, high-temperature-tcs-design, thermal-protection-item-sizing, tps-recession-allowance, tps-bondline-temperature, tps-reuse-cycle-degradation, tps-maximum-use-temperature."
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
  tags: [ecss, e-st-31-thermal-control-scope, e31-high-temperature-range-tps-requirements, high-temperature-tcs-design, thermal-protection-item-sizing, tps-recession-allowance, tps-bondline-temperature, tps-reuse-cycle-degradation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — High-Temperature Range and Thermal Protection (space-systems/ecss/e31-high-temperature-range-tps-requirements)

Use when the task is the clause 4.2.2 step of ECSS-E-ST-31 and its
thermal-protection annex: an item has been placed in the high-temperature
range, and the engineering requirements on the protection it carries — how
much of it survives the exposure, what the structure behind it sees, and how
many times it can do that — have to be worked out.

## Domain quick reference

- The number the material is compared against is the inflated peak, not the
  predicted one. A prediction and its uncertainty both belong on the hot side
  before the maximum use temperature is consulted, and the maximum use
  temperature itself is a property of the material and its environment, not a
  single catalogue figure to be reused across atmospheres.
- Thermal protection is consumed. An ablator recedes over the exposure, and
  the thickness that matters afterwards is what is left, not what was
  installed. The sizing question is whether the residual thickness still
  meets its requirement once the recession has been spent.
- The residual thickness is also what insulates. Recession and bondline
  temperature are therefore not two independent checks: the thickness the
  bondline sees is the end-of-exposure thickness, and computing the bondline
  on the installed thickness understates it in exactly the case that matters.
- The bondline, not the surface, is usually the limiting item. Adhesives and
  composite substrates fail hundreds of kelvin below the surface material, so
  a protection item that comfortably survives its own peak can still debond.
- Reuse degrades the surface. Emissivity falls and catalycity rises with
  cycles, and a surface qualified for a number of cycles has a declared
  end-of-life optical property that the last flight has to close on, not the
  beginning-of-life value the first analysis used.
- Falling emissivity is a feedback, not a bookkeeping entry. A surface that
  radiates less runs hotter, which is why the end-of-life property is carried
  into the peak check rather than reported next to it.

## Workflow

1. Validate the item and admit only a peak that actually reaches into the
   high-temperature range. An item below the boundary belongs to the
   conventional rules and is refused here rather than graded by the wrong
   rule set.
2. Inflate the predicted peak by its uncertainty and compare with the
   material maximum use temperature, recording the margin.
3. Spend the recession: multiply the recession rate by the exposure duration,
   subtract from the installed thickness, and compare the residual with the
   required minimum residual thickness.
4. Refuse a recession that consumes the whole item — a negative residual is
   not a thin item, it is a burn-through, and it is reported as one.
5. Compute the bondline temperature from the residual thickness, the heat
   flux and the through-thickness conductivity, and compare it with the
   substrate limit.
6. Walk the surface emissivity out over the required cycles at the declared
   degradation per cycle, and compare the end-of-life value with its floor.
7. Compare the required cycles with the qualified cycles, and treat a
   shortfall as a finding in its own right rather than as a consequence of
   the emissivity walk.
8. Report a per-constraint verdict with the margins, so one failing check
   does not hide the state of the others.

## Pitfalls

- Comparing the raw predicted peak with the maximum use temperature. The
  uncertainty belongs on the prediction first, and on the hot side it is the
  whole margin for a marginal item.
- Computing the bondline on the installed thickness. The insulating layer is
  thinner at the end of the exposure, which is the same moment the flux has
  been integrated the longest.
- Declaring a protection item adequate on its surface margin alone. The
  adhesive limit is the one that is usually hit, and it is hundreds of kelvin
  lower.
- Carrying beginning-of-life emissivity into a reuse case. A degraded surface
  radiates less and runs hotter, so the last qualified flight, not the first,
  is the sizing case.
- Reading a negative residual thickness as a very thin item. It is a
  burn-through, and arithmetic that continues past it produces a bondline
  temperature with no physical meaning.
- Treating the maximum use temperature as environment independent. The same
  material has different usable limits in an oxidising and an inert
  atmosphere, and the wrong figure invalidates the whole chain.

## Behavior contract (gate 3)

The high-temperature admission check, uncertainty-inflated peak comparison,
recession allowance and residual thickness, burn-through refusal, bondline
temperature from the residual thickness, emissivity walk over the reuse
cycles and the per-constraint verdict are exercised by the gate 3 contract
test: scripts/test_e31_high_temperature_range_tps_requirements.py against
scripts/e31_high_temperature_range_tps_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e31_high_temperature_range_tps_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
