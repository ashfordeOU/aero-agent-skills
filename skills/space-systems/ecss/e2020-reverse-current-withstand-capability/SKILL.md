---
name: e2020-reverse-current-withstand-capability
description: "Verify that a power outlet tolerates the current its load pushes back in both the conducting and the latched-off state, for ECSS-E-ST-20-20C clause 5.2.11.1.1: derive the recommended withstand level per state from the rated output current, convert the reverse pulse shape into charge, absorbed energy and repetitive rms current, raise the output-node excursion the charge drives into the holdup capacitance, then grade each state separately against its declared withstand peak, duration and overvoltage limit. Use when an inductive or regenerative load can drive current back into a distribution outlet. Trigger: ecss, e-st-20-20c, reverse-current-withstand, off-state-reverse-current, on-state-reverse-current, reverse-pulse-charge, output-node-overvoltage, blocking-element-need."
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
  tags: [ecss, e-st-20-20c, e2020-reverse-current-withstand-capability, reverse-current-withstand, off-state-reverse-current, on-state-reverse-current, reverse-pulse-charge, output-node-overvoltage, blocking-element-need]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution — Reverse-Current Withstand Capability (space-systems/ecss/e2020-reverse-current-withstand-capability)

Use when the task is the reverse-current tolerance of a power outlet under
ECSS-E-ST-20-20C clause 5.2.11.1.1 -- the recommended level of current an
outlet should take from a load that pushes current back up the feed, assessed
in the conducting state and in the latched-off state as two separate cases.

## Domain quick reference

- Reverse current is not a fault the load has; it is what a load ordinarily
  does. A winding that is de-energised returns its stored energy, a motor that
  is still turning generates, a capacitive load that sits above the rail
  discharges into it. The outlet is on the receiving end of all three.
- The two states are genuinely different circuits. With the outlet conducting,
  the reverse current returns through the pass element that is already carrying
  load current, and the recommended level is naturally referred to the outlet's
  own rating. With the outlet latched off, that path is gone and only whatever
  clamp, body diode or deliberate bypass the design provided remains, so the
  recommended level is lower and has to be declared separately.
- The recommended levels are a declared policy expressed as fractions of the
  rated output current, not physical constants, so they are carried with the
  result and can be re-declared for a programme that sets them differently.
- The peak is not the whole pulse. What reaches the holdup capacitance is
  charge, and charge depends on shape: a triangular pulse of the same peak and
  duration delivers half what a rectangular one does, while an exponential one
  read at its decay time constant delivers the full product. Grading a pulse on
  peak alone therefore over- or under-states the node excursion it causes.
- The charge sets the excursion the output node takes, the clamping voltage
  times that charge sets the energy the clamp has to absorb, and the repetition
  rate sets the root-mean-square current the return path carries continuously.
  Those are three different limits and a design can pass any two of them.
- Where the latched-off outlet cannot take what the load delivers, the answer
  is a blocking or bypass element in the return path rather than a larger
  clamp, because a clamp large enough to absorb the pulse is being asked to
  conduct in a state the outlet is supposed to be isolating in.

## Workflow

1. Validate the outlet rating, the holdup capacitance, the permitted output
   excursion and the clamp voltage, and require a pulse and a declared
   capability for both states. A capability shown in one state is not evidence
   about the other and is refused as a substitute.
2. Derive the recommended withstand level for each state from the rated output
   current and the policy fractions, and compare it with the capability the
   design actually claims.
3. Convert each reverse pulse into charge, absorbed clamp energy and, where a
   repetition period is declared, root-mean-square current, driving the
   conversion from the declared pulse shape rather than from the peak alone.
4. Raise the output-node excursion the charge drives into the holdup
   capacitance and compare it with the permitted excursion.
5. Grade each state on its own five checks -- recommended-level coverage,
   applied peak, applied duration, node excursion and repetitive current --
   and name the state in every finding so a reader knows which one failed.
6. Combine the two into an outlet verdict, and recommend a blocking or bypass
   element exactly when the latched-off state is the one that cannot take the
   reverse current the load delivers.

## Pitfalls

- Demonstrating the conducting state and calling the outlet done. The off state
  has a different return path and a lower recommended level, and it is the one
  that is exercised every time the outlet trips on a load that is still
  carrying energy.
- Grading the pulse on its peak. The node excursion follows charge, so the
  shape and duration decide the answer, and two pulses with the same peak can
  sit on opposite sides of the excursion limit.
- Sizing the clamp and stopping there. The clamp energy, the node excursion and
  the repetitive root-mean-square current are separate limits; a clamp that
  absorbs the pulse comfortably can still leave the node above its permitted
  excursion or the return path above its continuous rating.
- Treating a repetitive reverse pulse as a single event. A load that kicks back
  on every switching cycle puts a continuous current into the return path, and
  the single-shot withstand figure says nothing about it.
- Answering an off-state shortfall with a bigger clamp. That asks the outlet to
  conduct in the state it is meant to be isolating in; a blocking or bypass
  element is the design answer.
- Widening a declared limit so a case that lands exactly on it passes. An
  equality at a limit is a representation question, handled by the tolerance
  inside the comparison; the declared value stays as it was declared.

## Behavior contract (gate 3)

The policy validation, per-state recommended levels, pulse-shape conversion to
charge, energy and repetitive current, node-excursion computation, per-state
grading and the blocking-element decision are exercised by the gate 3 contract
test: scripts/test_e2020_reverse_current_withstand_capability.py against
scripts/e2020_reverse_current_withstand_capability_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_reverse_current_withstand_capability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
