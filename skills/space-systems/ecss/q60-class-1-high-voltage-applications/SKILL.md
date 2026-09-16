---
name: q60-class-1-high-voltage-applications
description: "Use when a class 1 part is applied above the high voltage threshold or in a high power microwave chain. Evaluate the additional provisions a class 1 EEE part owes when it runs at high voltage or high microwave power under ECSS-Q-ST-60C clause 4.6.7: stop a part whose working voltage sits above its own rating, test the voltage utilisation against the class 1 limit, flag an ambient inside the corona onset window and a sealed cavity with no vent path, derive the partial discharge, corona, venting, multipaction and power handling provisions the application calls for, and return one provisions-satisfied, provisions-outstanding, provisions-nonconforming or application-not-admissible disposition. Trigger: ecss, q-st-60c, class-1-high-voltage-derating, class-1-corona-onset-window, class-1-multipaction-fd-product, class-1-high-voltage-provision-disposition."
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
  tags: [ecss, q-st-60c-eee-component-procurement, q-st-60c, q60-class-1-high-voltage-applications, class-1-high-voltage-derating, class-1-corona-onset-window, class-1-multipaction-fd-product, class-1-high-voltage-provision-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 1 — High Voltage and High Power Microwave Applications (space-systems/ecss/q60-class-1-high-voltage-applications)

Use when the task is clause 4.6.7 of ECSS-Q-ST-60C: the provisions a class 1
part owes over and above the ordinary class 1 rules because it is applied at
high voltage or in a high power microwave chain. This leaf measures the stress
the application imposes, names the design findings it raises, and derives the
extra provisions the part still owes.

## Domain quick reference

- The application is admissible before it is assessed. A part with no
  identity, no stated rating, no stated electrode gap or a working voltage
  above its own rating is not a derating question; deriving provisions for it
  spends review effort on a part that cannot fly as applied.
- High voltage use halves what the rating buys. The working voltage may
  occupy only a fraction of the part rating, and a part sitting exactly on
  that fraction is compliant: the limit belongs to the acceptable side.
- The dangerous ambient is the one in between. A gap is safest in hard vacuum
  and safest again at sea level; the corona onset voltage collapses in the
  band the vehicle passes through on the way up, and both bounds of that band
  belong to it.
- Encapsulation without a vent path is a new failure, not a fix. Potting a
  cavity removes the corona risk and creates a trapped volume that expands
  against the potting as the ambient falls away.
- Multipaction is a geometry problem, not a power problem alone. The
  frequency-gap product decides susceptibility, and a narrow gap carrying
  microwave power is susceptible at a product a wide gap never reaches. Zero
  frequency is a direct current gap and is never susceptible.
- Coverage is a fraction of the owed provisions, not of the work performed.
  Closing a provision the application never owed raises the count of work done
  and moves the part no closer to flight.

## Workflow

1. Test admissibility first: part identity, stated rating, stated electrode
   gap and a working voltage that does not exceed the rating. Report every
   reason, ordered from identity outwards, rather than stopping at the first.
2. Measure the stresses: the voltage utilisation against the rating, the
   pressure-gap product, and the frequency-gap product for the powered gap.
3. Raise the design findings those measurements imply: utilisation above the
   class 1 limit, an unencapsulated gap inside the corona onset window, and a
   sealed cavity with no vent path.
4. Derive the owed provisions from the baseline plus the additions the working
   voltage, ambient pressure, encapsulation state, microwave power and gap
   geometry call for.
5. Compare the provisions already closed against the owed set and return the
   outstanding ones in performance order plus the coverage fraction.
6. Return one disposition: provisions-satisfied, provisions-outstanding,
   provisions-nonconforming or application-not-admissible. Inadmissibility
   overrides everything and a finding outranks outstanding work.

## Pitfalls

- Applying the ordinary class 1 derating to a high voltage application. The
  rating was measured in a laboratory ambient, and the part is not asked to
  hold that voltage in one.
- Assessing corona risk at the orbit ambient only. The vehicle spends minutes
  inside the onset window during ascent, and a part powered through ascent is
  tested there whether the analysis looked or not.
- Treating potting as the end of the question. A sealed cavity with no vent
  path trades a discharge for a delamination, and the second one is found
  later and costs more.
- Deriving multipaction risk from transmitted power alone. A wide gap at high
  power is quiet and a narrow gap at modest power is not; without the
  frequency-gap product the ranking is backwards.
- Reading a bound as excluded. A utilisation exactly on the class 1 limit, an
  ambient exactly on a window bound and a frequency-gap product exactly on the
  susceptibility bound are all inside, and float arithmetic lands on them.
- Counting closed provisions rather than owed ones. Work performed outside the
  derived set inflates progress and clears nothing the part actually needs.

## Behavior contract (gate 3)

The admissibility test, voltage utilisation, pressure-gap product, corona
window test, frequency-gap product, multipaction susceptibility, design
findings, provision derivation, outstanding comparison, coverage fraction and
the disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_1_high_voltage_applications.py against
scripts/q60_class_1_high_voltage_applications_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_1_high_voltage_applications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
