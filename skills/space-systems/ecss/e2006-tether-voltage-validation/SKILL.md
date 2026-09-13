---
name: e2006-tether-voltage-validation
description: "Use when bound the largest potential difference expected between the two ends of a deployed tether and validate the declared design voltage against that bound, under ECSS-E-ST-20-06C clause 10.3: take the relative plasma speed as orbital speed less the along-track corotation, take the field magnitude from a centred-dipole estimate at the orbit radius and magnetic latitude, project the induced field along the deployed line, sweep the magnetic-latitude range and the attitude envelope so the worst sample sets the bound, add supply bias and subtract the circuit and plasma-contact drops, then categorize the bound into a design regime and check it against the declared design voltage and the insulation-withstand margin. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-10-3, tether-end-to-end-potential, worst-case-voltage-envelope, open-circuit-bounding-case, corotating-plasma-velocity, insulation-withstand-margin, declared-design-voltage."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-voltage-validation, tether-end-to-end-potential, worst-case-voltage-envelope, open-circuit-bounding-case, corotating-plasma-velocity, insulation-withstand-margin, declared-design-voltage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Tether End-to-End Voltage Validation (space-systems/ecss/e2006-tether-voltage-validation)

Use when the task is the ECSS-E-ST-20-06C clause 10.3 calculation that bounds
the largest potential difference expected between the two ends of a deployed
tether, and the validation of the declared design voltage and insulation
withstand rating against that bound.

## Domain quick reference

- Clause 10.3 asks for a bound, not a nominal value. The answer is the
  largest end-to-end potential the tether can reach anywhere in its declared
  operating envelope, so the calculation is a sweep whose maximum is the
  deliverable — a single nominal-attitude, equatorial-crossing number
  understates it and is not an answer to the clause.
- The driving term is the field induced along a line moving through the
  geomagnetic field. Its strength follows the speed of the tether relative
  to the plasma it flies through, not the inertial orbital speed: the
  ionosphere corotates with the planet, so the along-track part of that
  corotation cancels. A prograde low-inclination orbit loses the most that
  way; a polar orbit loses none of it, and a retrograde orbit adds it.
- The field magnitude itself varies around the orbit. A centred-dipole
  estimate at the orbit radius falls with the cube of radius and rises by a
  factor of two between the magnetic equator and the magnetic pole, so the
  magnetic latitude the orbit actually reaches — set by the inclination —
  is part of the envelope, not a detail.
- Projection matters twice: once from the velocity-field geometry into the
  induced field, once from that field onto the deployed line. Only the
  component along the tether contributes to the end-to-end value, so the
  attitude envelope (nominal alignment plus the pointing deviation the
  mission allows) has to be swept rather than assumed at nominal.
- The open-circuit condition is bounding. With no current flowing there is
  nothing for the circuit resistance or the two plasma contacts to drop, so
  the ends see the full induced value plus any applied supply bias. Under
  load those drops subtract, and when they exceed the drive no current flows
  at all and the ends return to the open-circuit value. Drops therefore
  never raise the bound, and a calculation that reports only the loaded
  operating point understates the insulation duty.
- The bound then has to be compared to something. Three comparisons close
  the clause: the declared design voltage must cover the bound, the
  insulation withstand rating must carry the required margin over it, and
  the design regime the bound lands in must match the high-voltage
  provisions the design actually declares.

## Workflow

1. Validate the case: altitude, inclination, deployed length, nominal
   alignment and attitude deviation, circuit resistance, operating current,
   both plasma-contact drops, applied bias, declared design voltage and
   insulation withstand rating. Reject a non-physical entry first.
2. Build the sweep grid: magnetic latitudes from the equator out to the
   reach the inclination allows, crossed with the alignment samples the
   attitude envelope permits.
3. For each sample compute the relative plasma speed (orbital speed less
   the along-track corotation), the dipole field magnitude, the induced
   field, and the end-to-end electromotive force projected onto the line.
4. Add the applied bias and form both circuit conditions: the open-circuit
   value and the loaded value after the resistive and plasma-contact drops,
   with no current when the drops exceed the drive. Keep the larger.
5. Take the maximum over the whole grid as the bound, and keep the sample
   that produced it so the result is traceable to a latitude and attitude.
6. Validate: categorize the bound into its design regime, check the
   declared design voltage covers it, check the withstand margin meets the
   requirement, and check the high-voltage provisions match the regime. The
   case passes only when no check raises a finding.

## Pitfalls

- Using the inertial orbital speed as the crossing speed. The plasma
  corotates, and on a low-inclination prograde orbit that removes several
  percent of the induced field — the error is small but it is in the
  unconservative direction for insulation sizing.
- Evaluating at the magnetic equator only. The dipole field doubles at the
  magnetic pole, so an inclined orbit's bound can be nearly twice the
  equatorial value; the reach follows the inclination, and a retrograde
  inclination folds onto its supplement.
- Reporting the loaded operating point as the answer. Circuit and contact
  drops only ever subtract, so the open-circuit case is the bound, and the
  insulation between the ends has to survive it — including the deployment
  and safe-mode conditions where no current is drawn at all.
- Sweeping the attitude but taking only the nominal alignment as the worst
  case. The alignment closest to the induced field inside the declared
  deviation is the worst one, and it is rarely the nominal.
- Treating a declared design voltage that merely equals the bound as a
  margin. It covers the bound, which is what the clause requires, but the
  withstand margin is a separate check against the insulation rating.

## Behavior contract (gate 3)

The relative-velocity, dipole-field, induced-field, envelope-sweep,
regime-categorization and withstand-margin logic is exercised by the gate 3
contract test: scripts/test_e2006_tether_voltage_validation.py against
scripts/e2006_tether_voltage_validation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e2006_tether_voltage_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
