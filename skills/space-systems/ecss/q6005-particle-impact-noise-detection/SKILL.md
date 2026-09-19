---
name: q6005-particle-impact-noise-detection
description: "Assess a particle impact noise detection run on a sealed-cavity hybrid under ECSS-Q-ST-60-05C clause 10.3.6. Use when the task is deciding whether the package even presents a cavity to listen into, bounding the shock and vibration excitation by peak, frequency and the stroke it implies, counting the shock-and-listen cycles a quiet result owes, deriving the particle mass that can bridge the smallest conductor spacing, and withdrawing a block of quiet units when the closing sensitivity check fails. Trigger: ecss, q-st-60-05c, hybrid-cavity-particle-noise, pind-excitation-condition, pind-vibration-stroke-demand, pind-bridging-particle-mass, pind-sensitivity-block-withdrawal, pind-indication-rejection."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-particle-impact-noise-detection, hybrid-cavity-particle-noise, pind-excitation-condition, pind-vibration-stroke-demand, pind-bridging-particle-mass, pind-sensitivity-block-withdrawal]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Screening — Particle Impact Noise Detection (space-systems/ecss/q6005-particle-impact-noise-detection)

Use when the task is the loose-debris screen of ECSS-Q-ST-60-05C clause
10.3.6 — shaking a sealed hybrid while a transducer listens for
something rattling inside it, and deciding whether a quiet result was
earned or merely recorded.

## Domain quick reference

- The method needs a cavity. It hears debris striking the inside of a
  sealed enclosure, so a solid encapsulated body or an open coated
  assembly has nothing to hear: a quiet result on one of those is not a
  passed screen, it is a screen that never applied, and the package
  style decides that before any level is set.
- The excitation is a shock and a vibration doing two different jobs.
  The shock dislodges a particle that has settled or stuck; the
  vibration then keeps it moving while the transducer listens. Both
  peaks belong to the condition and neither substitutes for the other.
- A vibration peak is not a fixture requirement until it is paired with
  a frequency. The stroke a sinusoidal excitation implies falls with the
  square of frequency, so the same peak at the bottom of the band asks
  the shaker for many times the displacement it needs at the top. A
  fixture that cannot deliver the stroke silently delivers a lower peak.
- One cycle can miss a particle sitting in a corner. The method owes
  several shock-and-listen cycles, and a unit that ran fewer has been
  listened to less thoroughly than the paperwork claims.
- What matters is not any particle but a particle large enough to bridge
  the smallest conductor spacing in the cavity. That bridging size
  implies a mass, and the mass depends on the debris: a gold wire
  offcut and an epoxy flake of the same diameter are not the same
  target. A system whose threshold sits above that mass returns clean
  results that mean nothing.
- The sensitivity verification brackets a block, not a unit. If the
  check that closes the block fails, every unit listened to since the
  opening check was heard by an instrument of unknown sensitivity, so
  the whole block is withdrawn rather than the last unit alone.
- An indication is final for that unit. A quiet unit may be re-run
  inside a stated allowance to clear a suspected artefact, but a unit
  that ever indicated is rejected: a later quiet run does not unhear
  the first one.

## Workflow

1. Validate each unit record: identifier, package style, condition,
   vibration peak and frequency, shock peak, cycles run, conductor
   spacing, system threshold, run count and the indication flag. An
   unknown package style, an unknown condition, an unknown debris
   material and a non-positive level or cycle count are input errors.
2. Decide applicability from the package style before grading anything
   else, so a body with no cavity is reported as out of scope rather
   than as a pass.
3. Bound the excitation: the vibration peak and the shock peak against
   the condition, the frequency against its band, and the cycle count
   against the minimum the method owes.
4. Compute the stroke the peak and frequency together demand, so the
   fixture requirement is stated rather than assumed.
5. Derive the bridging particle mass from the smallest conductor
   spacing and the debris density, and compare the system threshold
   with it, absorbing the boundary with a named tolerance.
6. Grade indications and re-runs: an indication rejects the unit, a run
   count above the allowance is its own finding, and re-running a unit
   that already indicated is a third.
7. Close the block: apply the closing sensitivity check to the whole
   block, name every withdrawn unit, and report indicating units, the
   indication fraction and the lot disposition separately.

## Pitfalls

- Recording a clean result on a solid encapsulated part. The method
  cannot fail on a body with no cavity, so the clean result carries no
  information and the flow shows a screen that was never performed.
- Specifying the vibration peak alone. At the low end of the band the
  same peak needs many times the stroke, and a shaker that cannot
  deliver it quietly delivers less peak than the report states.
- Running one cycle to save time. A particle resting in a corner is not
  dislodged every time, and a single quiet cycle is the weakest
  evidence the method can produce.
- Accepting the system threshold from the instrument's datasheet
  without comparing it with the particle the cavity actually cares
  about. A threshold above the bridging mass makes every unit quiet.
- Keeping a block of quiet results after the closing sensitivity check
  failed. The instrument was of unknown sensitivity for the whole
  block, so withdrawing only the last unit keeps results that were
  never demonstrated.
- Re-running an indicating unit until it goes quiet. The allowance
  exists to clear artefacts on quiet units, not to argue with an
  indication that has already been recorded.

## Behavior contract (gate 3)

The applicability decision, excitation bounding, stroke computation,
bridging-particle mass derivation, sensitivity comparison, indication
and re-run grading, block withdrawal and lot aggregation are exercised
by the gate 3 contract test:
scripts/test_q6005_particle_impact_noise_detection.py against
scripts/q6005_particle_impact_noise_detection_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_particle_impact_noise_detection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
