---
name: e2008-blocking-diode-esd-robustness
description: "Use when a blocking diode human-contact ESD robustness stress is planned or its records reviewed. Evaluate whether a blocking diode survives the discharge a charged operator delivers on touching its terminals, under ECSS-E-ST-20-08C clause 12.6.15: hold the discharge capacitance and series resistance inside their bands, derive the peak current, decay constant, transferred charge and stored energy each step voltage produces, walk the ladder from the bottom with both polarities and every planned pulse, read reverse leakage and forward drop against the device's own pre-stress baseline, credit only the highest unbroken run of cleared levels, group it into a withstand band, and take that against the handling environment with margin. Trigger: ecss, e-st-20-08c-clause-12-6-15, blocking-diode-human-contact-esd, blocking-diode-esd-withstand-band, blocking-diode-esd-leakage-drift, blocking-diode-discharge-network-band, blocking-diode-esd-step-ladder."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-blocking-diode-esd-robustness, blocking-diode-human-contact-esd, blocking-diode-esd-withstand-band, blocking-diode-esd-leakage-drift, blocking-diode-discharge-network-band, blocking-diode-esd-step-ladder, blocking-diode-post-esd-parasitic-loss]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Blocking Diodes — Human-Contact ESD Robustness (space-systems/ecss/e2008-blocking-diode-esd-robustness)

Use when the task is the electrostatic robustness stress of
ECSS-E-ST-20-08C clause 12.6.15 -- a solar array blocking diode fired
at with discharges representing a charged person reaching its
terminals. The diode is handled: it is inserted, it is bonded, its
interconnectors are welded, and at each of those moments a hand that
has crossed a floor can reach it. The stress walks a rising sequence of
step voltages and asks what level the device is still sound after.

## Domain quick reference

- The network is the stress. A capacitor charged to the step voltage
  and discharged through a series resistance into the device models the
  charged person, and the four numbers that characterise the pulse fall
  straight out of it: peak current is the step voltage over the total
  resistance the discharge sees, the decay constant is that resistance
  times the capacitance, the charge transferred is the capacitance
  times the step voltage, and the energy the junction absorbs is half
  the capacitance times the square of the step voltage.
- A bench whose capacitance or series resistance has drifted outside
  its band is firing a different pulse than the record claims. Nothing
  done carefully afterwards repairs that, so the band check comes
  before the readings and not after them.
- Failure on a blocking diode is usually not a short. The junction
  takes local damage and the reverse leakage climbs: the device still
  blocks, but it blocks worse. That is the whole point of a blocking
  diode, so leakage growth is the primary signature and the forward
  drop is read alongside it to catch damage that shows the other way.
- The criterion is drift, not an absolute limit. Leakage varies widely
  between sound devices of the same type, so the post-pulse reading is
  taken against that device's own pre-stress baseline; an absolute
  ceiling passes a leaky device that got worse and fails a tight one
  that did not move.
- Both polarities are fired at every level. A junction that survives a
  discharge in one direction can fail the other, and a ladder walked in
  one polarity reports a withstand the part does not have.
- The withstand level is the highest level cleared with every level
  below it also clear. A record that failed at one level and passed a
  higher one is inconsistent, not evidence of a higher withstand, so
  the highest unbroken run is what is credited.
- The number only means something against the environment. A withstand
  is compared to the handling environment the part will actually meet,
  with a margin on top; a device that clears the environment exactly
  has no room for a floor, a glove or a bench that is worse than
  assumed.
- Leakage that grew but stayed inside the criteria still costs
  something. It flows once per string at the worst reverse bias the
  string presents, for the rest of the mission.

## Workflow

1. Validate the network specification and the drift criteria first. A
   tolerance of one or more, a leakage ceiling below the device's own
   baseline, or a required margin below one is refused rather than used.
2. Check the bench the stress actually ran on against its band, and
   report a drifted capacitance and a drifted series resistance
   together so the bench is not repaired one finding at a time.
3. Build the step ladder by repeated multiplication of the declared
   ratio, so every level is a product of exactly rounded steps and the
   ladder is the same sequence on every machine.
4. For each level, derive the pulse the step voltage produces through
   the network in hand: peak current, decay constant, transferred
   charge and stored energy.
5. Read each post-pulse observation against the device's own baseline
   for reverse leakage ratio and forward drop drift, and fail the
   observation outright on a recorded short or open.
6. Require every planned pulse in every planned polarity at a level
   before the level is credited. A level fired short is not a passed
   level, it is an absent one.
7. Credit the highest unbroken run of cleared levels as the withstand,
   flag a pass sitting above an earlier failure, and group the
   withstand into a band.
8. Take the withstand against the handling environment and its margin:
   below the environment is a rejection, above the environment but
   below the margin is a referral.
9. Roll the lot up: hold the stressed share against the sampling floor,
   take the share of devices carrying a finding against the lot
   allowance, carry the lowest withstand in the lot, and keep the lot
   open while any device or bench record is incomplete.

## Pitfalls

- Reading the diode carefully on a bench that was never checked. The
  capacitance and the series resistance define the pulse; a drifted
  network makes every level on the ladder a different stress from the
  one the report names.
- Sentencing on an absolute leakage limit. Sound devices of the same
  type spread over an order of magnitude, so an absolute ceiling both
  passes damage and fails good parts; the device's own pre-stress
  reading is the only stable reference.
- Firing one polarity to save bench time. The junction is not
  symmetric, and the polarity that was skipped is the one that fails in
  the cleanroom.
- Crediting the highest level that happened to pass. A pass above an
  earlier failure is a record defect; treating it as the withstand
  claims robustness the device demonstrably does not have.
- Quoting a withstand with no environment beside it. The level is only
  meaningful against the handling environment it has to survive, and
  the margin is what absorbs the floor and the glove nobody measured.
- Calling a diode that survived with doubled leakage a clean pass. It
  still blocks, but the leakage it now passes is carried once per
  string at the worst reverse bias for the rest of the mission.

## Behavior contract (gate 3)

The network specification and criteria validation, the discharge
network band check, the peak current, decay constant, transferred
charge and stored energy, the geometric step ladder, the baseline-
referred leakage ratio and forward drift, the catastrophic-failure
override, the planned-pulse completeness rule, the highest-unbroken-run
withstand with its inconsistency flag, the band grouping, the handling
environment margin, the post-stress parasitic loss and the lot roll-up
with its sampling floor are exercised by the gate 3 contract test:
scripts/test_e2008_blocking_diode_esd_robustness.py against
scripts/e2008_blocking_diode_esd_robustness_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_blocking_diode_esd_robustness.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
