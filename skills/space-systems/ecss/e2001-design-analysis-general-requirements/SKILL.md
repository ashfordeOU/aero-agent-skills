---
name: e2001-design-analysis-general-requirements
description: "Use when determine which equipment the multipaction design-analysis of ECSS-E-ST-20-01C clause 5.3.2.1 applies to and what coverage each carrier case demands: categorize every transmit-chain item by equipment-type, route a vacuum-exposed RF region to the multipaction case and a sealed pressurised region to the gas-discharge case, derive the coherent peak-envelope power of a multicarrier set, screen out an item whose peak gap-voltage cannot reach the lowest breakdown-voltage threshold, then compare the demanded single-carrier and multicarrier coverage against what the design file declares and flag every gap in either direction. Trigger: ecss, e-st-20-01c, multipaction-design-analysis, equipment-type-categorisation, single-carrier-case, multicarrier-case, peak-envelope-power, gap-voltage-screening, coverage-gap."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-design-analysis-general-requirements, multipaction, equipment-type-categorisation, single-carrier-case, multicarrier-case, peak-envelope-power]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Design Analysis Applicability (space-systems/ecss/e2001-design-analysis-general-requirements)

Use when the task is the general-requirements step of the multipaction
design analysis of ECSS-E-ST-20-01C clause 5.3.2.1 — deciding which
equipment the analysis is owed on, and whether the single-carrier case,
the multicarrier case, or both have to be covered for each item.

## Domain quick reference

- Applicability has two independent gates. The first is the
  equipment-type gate: only an item that carries RF power through a gap
  can develop the gap voltage that starts an electron avalanche, so a
  waveguide filter, an output multiplexer, a rotary joint, a switch, a
  feed chain, a radiating element or an amplifier output section is in
  the family, while a DC harness, a digital unit or a sensor harness is
  not. The second is the environment gate: the RF region has to reach
  vacuum. A vented or open region takes the multipaction route; a
  hermetically sealed pressurised region or a gas-filled waveguide takes
  the gas-discharge route instead, which is a different analysis and has
  to be declared as such rather than quietly omitted.
- The carrier case follows from the declared carrier set, not from the
  equipment-type. One carrier is the single-carrier case. Several
  carriers are the multicarrier case, whose worst-case envelope is the
  coherent sum of the carrier amplitudes: P_peak = (sum sqrt(P_i))^2.
  Four equal carriers of P therefore peak at 16P, not 4P, which is why
  the summed average power is never the analysis quantity.
- A multicarrier item still owes the single-carrier coverage: the
  envelope case and the steady single-carrier case stress the gap
  differently, so both are demanded and one does not substitute for the
  other.
- Screening is a legitimate exit, but only as a computed result. If the
  peak gap voltage V = M * sqrt(2 * Z * P_peak) stays under the lowest
  tabulated breakdown-voltage threshold of the surface, no analysis is
  demanded — and that computation is itself the evidence, recorded with
  the item.
- Coverage is a two-way comparison. A demanded analysis that is not
  declared is a gap; a declared analysis on an item that demands none is
  also worth reporting, because it usually means the item was
  categorized wrongly.

## Workflow

1. Take the equipment list and normalise each item's equipment-type and
   operating environment against the recognised sets; an unrecognised
   value is an input error, not an item to skip.
2. Apply the two applicability gates: RF-power-carrying type, and a
   vacuum-exposed RF region. Record the route implied by the
   environment so a sealed pressurised item is visibly handed to the gas
   discharge analysis rather than dropped.
3. Determine the carrier case from the carrier set and compute both the
   coherent peak-envelope power and the summed average power; keep the
   envelope for the voltage calculation.
4. Convert the envelope power into the peak gap voltage through the
   local impedance and the declared voltage-magnification factor, and
   screen the item against the lowest tabulated breakdown-voltage
   threshold; absorb floating-point representation error at the equality
   with a named tolerance instead of moving the threshold.
5. Derive the demanded coverage: nothing for an out-of-scope or screened
   item, the single-carrier item for a one-carrier item, and both items
   for a multicarrier item.
6. Compare demanded against declared in both directions and aggregate
   the findings; the equipment set is not compliant with clause 5.3.2.1
   until that list is empty.

## Pitfalls

- Using the summed average power of a multicarrier set as the analysis
  level. The coherent envelope is N times higher for N equal carriers,
  so averaging understates the gap voltage by a factor that grows with
  carrier count.
- Treating the multicarrier analysis as covering the single-carrier
  case. They are separate demands on a multicarrier item, and satisfying
  one leaves the other outstanding.
- Reading "sealed unit" as "no breakdown analysis". A pressurised region
  simply moves the item to the gas discharge route; the absence of a
  multipaction analysis then has to be justified by that route, not by
  silence.
- Screening an item on its nominal power rather than its peak gap
  voltage. Impedance and field concentration both enter the voltage, so
  two items at the same power screen differently.
- Letting an unrecognised equipment-type fall through as out of scope. A
  type that is not in the recognised set has not been assessed at all,
  and defaulting it to "no analysis" hides the omission.

## Behavior contract (gate 3)

The equipment-type and environment categorisation, carrier-case
determination, peak-envelope power, gap-voltage screening and the
two-way coverage comparison are exercised by the gate 3 contract test:
scripts/test_e2001_design_analysis_general_requirements.py against
scripts/e2001_design_analysis_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_design_analysis_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
