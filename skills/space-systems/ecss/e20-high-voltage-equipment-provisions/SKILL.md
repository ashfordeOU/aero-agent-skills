---
name: e20-high-voltage-equipment-provisions
description: "Use when determine whether unpotted, unpressurised high voltage hardware may be energised at a given ambient pressure under ECSS-E-ST-20C clause 5.10: categorize the operating state by ambient regime, confirm the provision bites because the item is neither encapsulated nor sealed behind a pressurised wall, evaluate the gas breakdown voltage of the gap from its pressure-times-gap product, bracket the critical pressure window in which the applied voltage can strike a discharge, check that the energisation inhibit releases only below that window, and time the venting profile so the enclosure falls clear of the window before power is applied. Trigger: ecss, e-st-20-electrical-scope, high-voltage-equipment-provisions, critical-pressure-range, paschen-breakdown-voltage, corona-inception-margin, energisation-inhibit-pressure, unpotted-high-voltage-hardware, depressurisation-profile."
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
  tags: [ecss, e-st-20-electrical-scope, e20-high-voltage-equipment-provisions, critical-pressure-range, paschen-breakdown-voltage, corona-inception-margin, energisation-inhibit-pressure, unpotted-high-voltage-hardware, depressurisation-profile]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- High Voltage Equipment Provisions (space-systems/ecss/e20-high-voltage-equipment-provisions)

Use when the task is the clause 5.10 provision of ECSS-E-ST-20C for
high voltage hardware that is neither encapsulated nor held behind a
sealed pressurised wall -- deciding the ambient pressure band in which
such hardware must not be operating, and the design precautions that
have to be in place if it will pass through that band energised.

## Domain quick reference

- The provision bites on exactly one configuration: unpotted and
  unpressurised. Encapsulation removes the gas from the gap and a
  sealed pressurised enclosure holds the gap far away from the
  vulnerable band, so either choice answers the clause by
  construction. Everything else sees the ambient pressure directly,
  through every vent and every seam.
- Gas breakdown across a uniform gap is a similarity law in the
  product of pressure and gap length, not in pressure alone. The
  breakdown voltage falls as that product rises from near zero,
  reaches a minimum, and rises again as the gas gets dense. Below the
  minimum the mean free path is so long that too few ionising
  collisions occur for an avalanche to build, and the model returns no
  finite breakdown voltage at all -- that branch is why hard vacuum is
  a comfortable place for high voltage and a few hundred pascal is
  not.
- The minimum of the curve has a closed form: the product at which
  breakdown is easiest depends only on the ionisation coefficient and
  the secondary-emission coefficient of the cathode, and the voltage
  there is that product times the field coefficient. An applied
  voltage below that minimum can never strike a discharge at any
  pressure, so for that gap no critical window exists.
- An applied voltage above the minimum defines a critical pressure
  window: the band whose two edges are the pressures at which the
  breakdown voltage equals the applied voltage. Inside it the gap
  breaks down. Because the law is in the product, the window scales
  inversely with gap length -- widening the gap moves the same window
  to lower pressures rather than removing it.
- Operating states fall into three ambient regimes: dense gas (on the
  ground, or inside a sealed pressurised enclosure), transitional
  pressure (launch ascent venting, early-orbit outgassing, a thin
  planetary atmosphere) and vacuum. The transitional regime is the one
  that crosses the window.
- Two provisions follow. An energisation inhibit must hold the item
  unpowered until the ambient pressure is at or below the lower edge
  of the window, and the venting profile must reach that pressure
  before the inhibit releases. Separately, the breakdown voltage at
  the actual operating pressure has to stand above the applied voltage
  by the required margin.

## Workflow

1. Categorize the declared operating state into its ambient regime;
   raise on a state that is not a recognized clause 5.10 state.
2. Decide whether the provision applies: potted or pressurised
   hardware is out of scope and carries no pressure finding.
3. Compute the minimum of the breakdown curve for the gas and cathode
   in question, and compare the applied voltage against it; a lower
   applied voltage means no critical window exists for that gap.
4. Bracket the critical pressure window by solving the breakdown
   relation on each side of the minimum for the applied voltage.
5. Flag an item whose operating pressure falls inside the window,
   counting either edge as inside -- at an edge the breakdown voltage
   equals the applied voltage, which is not a pass.
6. Flag an item with no energisation inhibit on record, and an inhibit
   that releases above the lower edge of the window.
7. Where a venting profile is declared, compute the time the enclosure
   needs to fall clear of the window and flag a release earlier than
   that, and a release pressure still above the lower edge.
8. Compute the breakdown margin at the operating pressure and flag a
   margin below the requirement; then confirm at least one recognized
   design precaution is declared. The equipment is compliant only when
   no item carries a finding.

## Pitfalls

- Reasoning in pressure alone. A gap that is safe at one millimetre is
  not safe at three at the same pressure; the law is in the product,
  and the window moves with the gap.
- Treating vacuum as the only safe place and the ground as the only
  other case. The dangerous band lies between them, and a vehicle
  spends its ascent crossing it.
- Widening a gap to fix a breakdown finding. That shifts the window to
  lower pressures, which can move it straight onto the early-orbit
  outgassing pressure the hardware will actually see.
- Fitting an energisation inhibit and never checking when it releases.
  An inhibit that drops out at the top of the window energises the
  item exactly where the gap is weakest.
- Reading a pressure sitting on an edge of the window as compliant.
  At an edge the breakdown voltage equals the applied voltage, so the
  margin is one and the gap is at its threshold.
- Taking a vented enclosure's internal pressure to be the external
  ambient during ascent. The vent has a time constant, and the
  relevant number is the pressure inside the enclosure when power is
  applied.

## Behavior contract (gate 3)

The operating-state categorization, scope, breakdown-model,
curve-minimum, critical-window, inhibit-release, venting-profile,
breakdown-margin and declared-precaution logic is exercised by the
gate 3 contract test:
scripts/test_e20_high_voltage_equipment_provisions.py against
scripts/e20_high_voltage_equipment_provisions_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_high_voltage_equipment_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
