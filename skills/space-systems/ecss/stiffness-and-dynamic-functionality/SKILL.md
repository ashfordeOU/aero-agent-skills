---
name: stiffness-and-dynamic-functionality
description: "Use when assess stiffness, alignment stability, and dynamic behaviour of a spacecraft structure against ECSS-E-ST-32C clauses 4.3.5–4.3.6: verify that each structural axis meets its minimum fundamental natural frequency requirement, compute the frequency separation margin between structural modes and launch-environment excitation frequencies and flag any margin below the required threshold, confirm that retained modes account for the minimum required fraction of modal effective mass in each direction, and check that alignment drift under combined thermal and mechanical loads stays within the specified tolerance. Trigger: ecss, e-st-32-structures-scope, stiffness, natural-frequency, frequency-separation, alignment-stability, modal-analysis, dynamic-behaviour, modal-effective-mass."
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
  tags: [ecss, e-st-32-structures-scope, stiffness, natural-frequency, frequency-separation, alignment-stability, modal-analysis, dynamic-behaviour, modal-effective-mass]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Stiffness, Alignment Stability and Dynamic Behaviour (space-systems/ecss/stiffness-and-dynamic-functionality)

Use when the task is to assess whether a spacecraft structure satisfies the stiffness,
alignment stability, and dynamic-behaviour (frequency separation) requirements of
ECSS-E-ST-32C clauses 4.3.5–4.3.6 -- verifying fundamental natural frequency
thresholds per axis, checking frequency separation margins between structural modes and
excitation sources, confirming modal effective mass coverage, and verifying alignment
drift under combined loads stays within tolerance.

## Domain quick reference

- ECSS-E-ST-32C clause 4.3.5 requires the structure to meet a minimum fundamental
  natural frequency in each relevant axis (axial, lateral, rotational). The minimum
  threshold is driven by the launch-vehicle interface specification or an internal
  coupling-avoidance requirement; falling below it risks quasi-static load
  amplification and resonant coupling with the launcher.
- Clause 4.3.6 imposes frequency separation between structural modes and the
  excitation frequencies of co-located equipment, the launch environment, or the
  control system. The separation margin is expressed as a fractional gap between the
  structural frequency and the nearest excitation frequency; insufficient margin risks
  resonant amplification of dynamic loads.
- Modal effective mass coverage: the retained modes in the finite-element model must
  account for a defined minimum fraction of the total translational effective mass in
  each direction (typically 90%). A shortfall means the model does not represent the
  true dynamic response and additional modes must be included before verification can
  proceed.
- Alignment stability: under the combined in-orbit thermal and mechanical load
  environment, sensitive structural interfaces (optical benches, antenna reflectors,
  instrument mounting points) must maintain their relative alignment within the
  pointing or performance budget derived from the mission requirement.

## Workflow

1. Collect the minimum natural frequency requirements per axis (axial, lateral, and
   where applicable rotational) from the launch-vehicle interface control document or
   the system-level structural requirements specification. Verify that a minimum is
   defined for every axis that will be dynamically excited; an undefined minimum is
   itself a finding.
2. For each axis, compare the structure's fundamental natural frequency (from finite-
   element analysis or test) against the required minimum. Flag every axis where the
   frequency falls below the minimum and record the shortfall in Hz.
3. Identify every significant excitation frequency in the mission environment --
   launcher acoustic and shock levels, co-located rotating equipment, attitude control
   actuators -- and pair each with the nearest structural mode frequency. For each
   pair, compute the fractional separation margin and compare it against the required
   margin. Flag any pair where the margin is insufficient.
4. Confirm that the retained modes in the finite-element model account for at least
   the required fraction of modal effective mass in the translational x, y, and z
   directions. If any direction is below the threshold, flag it and require that
   additional modes be included before the dynamic analysis result is accepted for
   verification.
5. For each alignment-critical interface, compare the predicted alignment drift
   (thermal plus mechanical) against the allowable derived from the pointing or
   instrument performance budget. Flag any exceedance, noting the excess in arc-
   seconds.
6. Aggregate findings across all four check types; the structure satisfies clauses
   4.3.5–4.3.6 only when all violation lists are empty.

## Pitfalls

- Applying the fundamental frequency check only in the axial direction and skipping
  lateral -- the launch environment excites both axes independently, and the lateral
  threshold is often more stringent for tall or slender structures.
- Confusing frequency separation with an absolute Hz gap -- the separation requirement
  is expressed as a fractional ratio relative to the excitation frequency; a 5 Hz gap
  at 10 Hz excitation (50% margin) is very different from 5 Hz at 100 Hz excitation
  (5% margin).
- Accepting modal analysis results where retained modes do not reach the effective-
  mass threshold -- residual flexibility from omitted high-frequency modes can
  meaningfully affect predicted response at lower frequencies and invalidate the
  verification.
- Checking alignment under thermal load alone and not the combined thermal-plus-
  mechanical case -- the combined environment can shift the alignment well beyond the
  thermal-only prediction and is the correct basis for the compliance check.

## Behavior contract (gate 3)

The fundamental frequency, frequency separation, modal effective mass, and alignment
stability logic is exercised by the gate 3 contract test:
scripts/test_stiffness_and_dynamic_functionality.py against
scripts/stiffness_and_dynamic_functionality_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_stiffness_and_dynamic_functionality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
