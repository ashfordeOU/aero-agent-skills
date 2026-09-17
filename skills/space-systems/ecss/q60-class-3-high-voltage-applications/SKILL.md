---
name: q60-class-3-high-voltage-applications
description: "Assess the additional provisions a Class 3 EEE part owes when it is applied at high voltage or in a high power microwave chain under ECSS-Q-ST-60C clause 6.6.7: stop a part whose working voltage or peak power sits above its own rating, resolve the pressure regime that decides whether gas breakdown or a resonant electron avalanche governs, take the voltage utilisation against the Class 3 limit, resolve the breakdown voltage across the electrode gap and the margin left against it, price the clearance and creepage the surface calls for, group the frequency-gap product against the susceptibility bands, then subtract the provisions already held. Use when a Class 3 part runs well above a hundred volts or drives a high power microwave stage. Trigger: ecss, q-st-60c, q60-class-3-high-voltage-applications, q60-c3-hv-pressure-regime, q60-c3-hv-paschen-breakdown-margin, q60-c3-hv-multipaction-susceptibility-band."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-3-high-voltage-applications, q60-c3-hv-pressure-regime, q60-c3-hv-paschen-breakdown-margin, q60-c3-hv-creepage-and-clearance-shortfall, q60-c3-hv-multipaction-susceptibility-band, q60-c3-hv-provision-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 3 — High Voltage and High Power Applications (space-systems/ecss/q60-class-3-high-voltage-applications)

Use when the task is clause 6.6.7 of ECSS-Q-ST-60C: a Class 3 part is applied
at high voltage or in a high power microwave chain, and the question is what
that application owes over and above the ordinary Class 3 rules.

## Domain quick reference

- High voltage use changes what a rating buys. The part is still a Class 3
  part and still owes everything Class 3 asks; the application adds a second
  set of questions the ordinary rules never put, and those questions attach to
  where the part sits rather than to what it is.
- Which question governs is decided by pressure, not by voltage. Near ambient
  the gas is dense and breakdown wants a high field. Around the Paschen
  minimum a few hundred volts across a millimetre is enough — and an ascent
  spends minutes passing through exactly that band. In hard vacuum there is no
  gas left to break down, and what remains is a resonant electron avalanche
  between two surfaces.
- The gas breakdown curve has a left branch as well as a right one. Below the
  minimum there are too few molecules in the gap to sustain an avalanche at
  any voltage the design could reach; that is reported as no gas breakdown
  rather than as a small number, because a small number there would read as a
  danger that is not present.
- Clearance and creepage are two different budgets. One is measured through
  air and one along a surface, and the surface one is spent or bought by what
  the surface is: a conformal coat buys creepage, contamination and outgassing
  residue spend it.
- Multipaction sits on a frequency-gap product, not on a frequency and not on
  a gap. Two stages with the same power and very different geometry can land
  in different bands, and the band decides whether the chain owes an analysis,
  an analysis and a test, or neither.
- A sealed cavity with no vent path is a design finding in its own right. It
  carries its own atmosphere out of the dense regime and into the band where
  breakdown is cheapest, and stays there.
- Provisions are a list to be subtracted, not a verdict. What the application
  owes is derived from the voltage, the regime, the enclosure, the surface and
  the chain; what is held is taken off; what is left is the finding.

## Workflow

1. Validate the case: the working and rated voltage, the electrode gap, the
   ambient pressure, the built clearance and creepage, the surface condition,
   the enclosure form, the provisions held and — for a microwave chain — the
   frequency, the peak power and the rated peak power.
2. Decide admissibility first: a working voltage above the part rating, or a
   peak power above the rated peak power, is not a derating question.
3. Resolve the pressure regime and so which breakdown mechanism governs.
4. Take the voltage utilisation against the Class 3 limit.
5. Resolve the gas breakdown voltage across the gap and the margin the working
   voltage leaves against it, skipping the check where there is no gas.
6. Price the clearance and creepage the working voltage calls for at this
   surface, and name any shortfall.
7. For a microwave chain, take the frequency-gap product, group it against the
   susceptibility bands, and take the peak power utilisation.
8. Assemble the provisions owed, subtract what is held, and return the
   disposition in precedence order: not admissible, then design
   nonconforming, then provisions outstanding, then provisions satisfied.

## Pitfalls

- Running the gas breakdown check at the wrong pressure. A design graded at
  sea level looks comfortable and a design graded in vacuum looks untouchable;
  the band between them is where the hardware actually spends the ascent.
- Reading a left-branch result as a low breakdown voltage. Below the minimum
  the Townsend form stops being defined, and a number produced there is an
  artefact rather than a margin.
- Grading clearance and creepage as one dimension. They are measured along
  different paths, and a generous air gap does nothing for a surface that has
  a track forming across it.
- Pricing creepage on a clean surface for hardware that will not be clean.
  Outgassing residue and handling contamination both spend surface, and the
  design that was exactly adequate on paper is short in the box.
- Judging multipaction on frequency alone. The susceptibility sits on the
  frequency-gap product, so narrowing a gap to save mass can walk a stage into
  the band it was safely above.
- Treating a hermetic seal as a high voltage safeguard. A sealed unvented
  cavity takes its own atmosphere down to the pressure where breakdown is
  cheapest and holds it there for the mission.
- Comparing a computed utilisation, margin or shortfall with its limit by bare
  arithmetic. The breakdown form runs through a logarithm that is not
  correctly rounded, so a case sitting exactly on a limit can land a few units
  in the last place the wrong side of it.

## Behavior contract (gate 3)

The policy merge, case validation, pressure regime resolution, voltage
utilisation, gas breakdown voltage and its left-branch guard, breakdown
margin, required clearance and creepage with their shortfalls, the
frequency-gap product and its susceptibility band, microwave power
utilisation, the derived provision list, the outstanding provisions and the
four-way disposition in precedence order are exercised by the gate 3 contract
test: scripts/test_q60_class_3_high_voltage_applications.py against
scripts/q60_class_3_high_voltage_applications_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q60_class_3_high_voltage_applications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
