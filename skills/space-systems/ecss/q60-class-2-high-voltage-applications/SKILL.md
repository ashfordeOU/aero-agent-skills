---
name: q60-class-2-high-voltage-applications
description: "Assess the additional provisions a class 2 EEE part owes when it is applied at high voltage or in a high power microwave chain under ECSS-Q-ST-60C clause 5.6.7: stop a part whose working voltage sits above its own rating, take the voltage utilisation against the class 2 limit, resolve the gas breakdown voltage across the electrode gap at the ambient pressure and the margin it leaves, derive the clearance and creepage the surface condition calls for, and group the frequency-gap product against the multipaction susceptibility band. Use when a class 2 part runs above the high voltage threshold or carries high peak microwave power. Trigger: ecss, q-st-60c-clause-5-6-7, class-2-high-voltage-utilisation, class-2-paschen-breakdown-margin, class-2-creepage-and-clearance-shortfall, class-2-multipaction-susceptibility-band."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-2-high-voltage-applications, class-2-high-voltage-utilisation, class-2-paschen-breakdown-margin, class-2-creepage-and-clearance-shortfall, class-2-multipaction-susceptibility-band, class-2-high-voltage-provision-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — High Voltage and High Power Microwave Applications (space-systems/ecss/q60-class-2-high-voltage-applications)

Use when the task is clause 5.6.7 of ECSS-Q-ST-60C: the provisions a class 2
part owes over and above the ordinary class 2 rules because it is applied at
high voltage or in a high power microwave chain. This leaf measures the stress
the application imposes, names the design findings it raises, and derives the
extra provisions the part still owes.

## Domain quick reference

- The application is admissible before it is assessed. A working voltage above
  the part's own rating is not a derating question; deriving provisions for it
  spends review effort on a part that cannot fly as applied.
- High voltage use halves what the rating buys. At class 2 the working voltage
  may occupy only a fraction of the part rating, and a part sitting exactly on
  that fraction is compliant: the limit belongs to the acceptable side.
- Gas breakdown is a curve, not a threshold. The breakdown voltage across a gap
  falls with the pressure-gap product to a minimum and rises again either side,
  so a gap that is safe in hard vacuum and safe at sea level can be at its
  weakest somewhere on the way up. Left of the sustaining branch the discharge
  cannot build at all, which is a different statement from a high breakdown
  voltage and is reported as its own result rather than as a large margin.
- Clearance and creepage are two distances, not one. Clearance is the shortest
  path through the gas; creepage is the path along the insulating surface, and
  the surface is the one that a conformal coat lengthens and contamination
  shortens.
- A microwave gap has a second failure mode the voltage never shows. The
  frequency-gap product decides whether secondary electrons return in phase,
  and inside that band the stage sustains an avalanche at a voltage far below
  anything the gas breakdown curve predicts.
- Provisions and findings are different outputs. A missing partial discharge
  measurement is work still to do; a creepage shortfall is a design that will
  not pass however much work is done, and the disposition keeps the two apart.

## Workflow

1. Validate the case: the part reference, the rating, the working voltage, the
   electrode gap, the ambient pressure, the built clearance and creepage, the
   surface condition and the enclosure form.
2. Stop at once if the working voltage sits above the part rating — the
   application is not admissible and nothing downstream changes that.
3. Take the voltage utilisation against the class 2 limit.
4. Resolve the gas breakdown voltage across the gap at the ambient pressure and
   take the margin the working voltage leaves; record separately when the
   pressure-gap product is left of the sustaining branch.
5. Derive the clearance and the creepage the working voltage calls for at the
   surface condition and name any shortfall.
6. For a microwave chain, take the frequency-gap product, group it against the
   susceptibility band, and take the peak power utilisation.
7. Assemble the provisions the application owes, subtract what is held, and
   return the disposition in precedence order: not admissible, then design
   nonconforming, then provisions outstanding, then provisions satisfied.

## Pitfalls

- Reading a vacuum gap as a safe gap. The vehicle passes through the pressure
  band where the same geometry is at its weakest, and a part energised during
  ascent meets that band with the voltage already on it.
- Taking a large computed margin from a pressure-gap product that cannot
  sustain a discharge at all. The two results mean different things, and
  folding them together hides the case where a later pressure rise puts the
  gap back onto the curve.
- Sizing the surface by the clearance. The creepage path is longer, the surface
  condition scales it, and the track that forms along a contaminated surface
  does not care how much gas sits between the electrodes.
- Treating a conformal coat as unconditional margin. It buys creepage only
  where it is continuous, and a coat with a void is a surface with a void.
- Assuming a voltage margin covers a microwave stage. Multipaction builds at a
  voltage the gas breakdown curve never flags, and the frequency-gap product is
  the only place that failure mode shows.
- Reporting an outstanding provision as a design defect, or the reverse. One is
  closed by doing the work; the other is closed only by changing the hardware.
- Comparing a computed utilisation, margin or shortfall with its limit by bare
  arithmetic. The breakdown voltage comes through a logarithm that is not
  correctly rounded, so a case sitting exactly on a bound can land a few units
  in the last place the wrong side of it.

## Behavior contract (gate 3)

The policy merge, case validation, admissibility stop, voltage utilisation,
gas breakdown voltage and its sustaining branch, breakdown margin, required
clearance and creepage with their shortfalls, frequency-gap product and
susceptibility grouping, peak power utilisation, provision assembly and the
four-way disposition in precedence order are exercised by the gate 3 contract
test: scripts/test_q60_class_2_high_voltage_applications.py against
scripts/q60_class_2_high_voltage_applications_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_high_voltage_applications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
