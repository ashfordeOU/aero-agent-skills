---
name: q6015-component-radiation-effect-mechanisms
description: "Determine which radiation effect mechanisms are credible for a component and what each demands. Use when the ECSS-Q-ST-60-15C clause 4.2 mechanism set has to be narrowed to one part: take the mechanisms its technology is open to, screen each against the environment so a cumulative effect needs its own driving quantity and a single event needs the environment to reach the part's onset, group the survivors into cumulative and single event families, separate the ones a single occurrence can destroy, and name every verification method the plan is short of. Trigger: ecss, q-st-60-15c-clause-4-2, radiation-effect-mechanisms, cumulative-dose-degradation, displacement-damage-dose, single-event-latchup-screening, linear-energy-transfer-onset, radiation-verification-method-coverage."
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
  tags: [ecss, q-st-60-15-radiation-hardness-assurance-scope, q6015-component-radiation-effect-mechanisms, q-st-60-15c-clause-4-2, radiation-effect-mechanisms, cumulative-dose-degradation, displacement-damage-dose, single-event-latchup-screening, linear-energy-transfer-onset, radiation-verification-method-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Radiation Effects — Component Mechanisms (space-systems/ecss/q6015-component-radiation-effect-mechanisms)

Use when the task is the mechanism overview of ECSS-Q-ST-60-15C clause 4.2 —
which of the cumulative dose, displacement damage and single event effects
actually act on a given component in a given orbit, and what each one obliges
the verification plan to do about it.

## Domain quick reference

- The mechanisms fall into two families that behave nothing alike. A
  cumulative effect accrues: the part drifts with every rad and every particle
  until a parameter leaves its limit. A single event needs one particle, and
  it can happen on the first day or never — the mission length changes the
  probability, not the threshold.
- Technology decides which mechanisms are even open. A bulk silicon part has a
  parasitic four-layer path and can latch; the same function on an insulating
  substrate does not have one, so latchup is not on its list at all. A power
  switch is open to gate rupture and burnout that a logic part is not.
- Displacement damage is a separate axis from ionising dose, not a scaled
  version of it. It acts on the lattice rather than the oxide, so it hits
  optocouplers, detectors and solar cells hard while barely touching a digital
  part that the same ionising dose would degrade.
- Within the single event family the split that matters is whether one
  occurrence destroys the part. An upset is a lost bit and a design problem; a
  latchup or a burnout is a dead unit. They are grouped separately because
  they oblige different test methods and carry different consequences.
- An onset threshold screens the single event mechanisms. If the environment
  never supplies a linear energy transfer the part's onset responds to, the
  mechanism is not credible for that mission — but the equality at the top of
  the available spectrum is met, not screened out.
- Some bipolar and optocoupler technologies degrade worse at the low dose
  rates a mission really delivers than at the rate a laboratory uses. A
  high-rate cumulative test alone therefore does not demonstrate them, and the
  plan owes a low-rate test as well.

## Workflow

1. Validate the component: its part number, its technology, the single event
   onset threshold it declares and the verification methods already in its
   plan.
2. Validate the environment: the cumulative dose, the displacement damage dose
   and the highest linear energy transfer the mission makes available.
3. Take the mechanism set the technology is open to, in its reported order.
4. Screen each mechanism against the environment: a cumulative mechanism needs
   a positive level of its own driving quantity; a single event mechanism
   needs a heavy ion environment that reaches the declared onset, with an
   equality at the maximum counted as reached.
5. Group the credible mechanisms into the cumulative and single event families
   and separate out the ones a single occurrence can destroy.
6. Derive the verification methods the credible set demands, adding the
   low dose rate cumulative test where the technology needs one, and name each
   demanded method the plan does not carry.
7. Report the credible and screened-out sets, the grouping, the demanded
   methods and a verdict that raises an unverified destructive mechanism as
   its own finding.

## Pitfalls

- Carrying the full mechanism list for every part. A mechanism a technology is
  not open to costs test time and hides the ones that matter behind it.
- Screening a mechanism out on mission length. Length changes how likely a
  single event is, never whether the environment can cause one.
- Treating displacement damage as a fraction of ionising dose. The two damage
  different things, and a part can pass one comfortably while failing the
  other.
- Covering latchup with an upset test. A destructive mechanism needs a method
  that can detect and safely interrupt the event, which an upset count does
  not do.
- Demonstrating a low dose rate sensitive technology at laboratory rate only.
  The mission rate is the harsher case for those parts, so the high-rate
  result reads better than the flight condition.
- Discarding a part whose onset sits exactly at the environment maximum. The
  environment reaches it; only the floating-point representation of the
  comparison is in doubt.

## Behavior contract (gate 3)

The mechanism table, technology susceptibility sets, environment validation,
onset screening with its exact-equality tolerance, family grouping,
destructive separation, demanded-method derivation including the low dose rate
case and the plan-coverage verdict are exercised by the gate 3 contract test:
scripts/test_q6015_component_radiation_effect_mechanisms.py against
scripts/q6015_component_radiation_effect_mechanisms_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6015_component_radiation_effect_mechanisms.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
