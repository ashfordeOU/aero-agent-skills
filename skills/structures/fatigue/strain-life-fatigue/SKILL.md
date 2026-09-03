---
name: strain-life-fatigue
description: "Use when you must determine the strain-life (low-cycle fatigue) endurance of an aerospace structure: Coffin-Manson total strain amplitude from reversals to failure, reversals to failure from a fully reversed strain amplitude, the transition life where elastic and plastic amplitudes cross, low-cycle versus high-cycle regime categorization, the Neuber local-strain rule that converts a nominal elastic stress at a notch into local elastic-plastic strain through the cyclic Ramberg-Osgood curve, and the strain-life verdict for a load point. Produces reversals and cycles to failure, local notch strain, and the regime string. Trigger: strain-life-fatigue, coffin-manson, low-cycle-fatigue, reversals-to-failure, transition-life, neuber-local-strain, ramberg-osgood, elastic-plastic-strain, notched-lug."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
  - id: mmpsd
    reference-only: true
gated: false
domain: structures
pack: fatigue
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: fatigue
  tags: [strain-life-fatigue, coffin-manson, low-cycle-fatigue, reversals-to-failure, transition-life, neuber-local-strain, ramberg-osgood, elastic-plastic-strain, notched-lug]
  version: 0.1.0
  author: Aero Agent Skills
---

# Strain-Life Fatigue Analysis (structures/fatigue/strain-life-fatigue)

Use when the load point is a strain (or a nominal stress at a notch)
rather than a nominal elastic stress far from yielding: the Coffin-Manson
relation gives the total strain amplitude as the sum of elastic and
plastic amplitude curves against reversals to failure, the life at a
strain amplitude is found by inverting that relation, and the Neuber
rule bridges the nominal elastic stress at a notch to the local
elastic-plastic strain when the section yields. This is the low-cycle
fatigue (LCF) leaf; it pairs with the high-cycle S-N leaf
structures/fatigue/stress-life-curve (the stress-life counterpart above
the transition), structures/fatigue/notch-sensitivity (source of the
fatigue notch factor k_f input), structures/fatigue/miner-damage and
structures/fatigue/load-spectrum-counting (accumulating damage over
variable loads), and structures/fatigue/goodman-diagram (mean-stress
correction, out of scope here, assumed zero mean).

## Domain quick reference

- Coffin-Manson total strain amplitude at 2N_f reversals to failure:
  eps_a = (sigma_f_prime / E) * (2N_f)^b + eps_f_prime * (2N_f)^c,
  with fatigue strength coefficient sigma_f_prime, fatigue strength
  exponent b < 0, fatigue ductility coefficient eps_f_prime, fatigue
  ductility exponent c < 0, modulus E. The first term is the elastic
  amplitude, the second the plastic amplitude.
- Life from strain: invert eps_a(2N_f) by bisection on log(2N_f), wide
  deterministic bracket (reversals_to_failure).
- Strain from life: direct evaluation of the two terms
  (strain_amplitude).
- Transition life 2N_t: the reversal count where the elastic and
  plastic amplitudes are equal. A load point with 2N_f below 2N_t is
  low-cycle (plastic-dominated); above it, high-cycle
  (elastic-dominated) (regime_classification).
- Ramberg-Osgood cyclic curve: eps = sigma/E +
  (sigma/K_prime)^(1/n_prime), cyclic strength coefficient K_prime,
  cyclic strain hardening exponent n_prime.
- Neuber rule at a notch: sigma_loc * eps_loc = (k_f * S)^2 / E, with
  nominal elastic stress amplitude S, fatigue notch factor k_f (an
  input here, from notch-sensitivity methods elsewhere), solved with
  the Ramberg-Osgood curve for the local stress and strain
  (neuber_local_strain). Fully elastic when the local strain equals
  sigma_loc/E, plastic otherwise.
- Local strain amplitude equals eps_loc for the fully reversed life,
  read through the Coffin-Manson curve with zero mean stress assumed
  (strain_life_point).
- Module material table (representative typicals, reference-only; not
  reproduced from MMPDS):

  | Property | 7075-T6 class aluminum | 4340 class steel |
  |---|---|---|
  | sigma_f_prime (MPa) | 690 | 1750 |
  | b | -0.10 | -0.08 |
  | eps_f_prime | 0.55 | 0.50 |
  | c | -0.60 | -0.70 |
  | E (GPa) | 71.7 | 200 |
  | K_prime (MPa) | 900 | 1800 |
  | n_prime | 0.10 | 0.08 |

  Values are representative magnitudes from the open fatigue
  literature, reference-only. Pass any of the seven constants as a
  property dict to override the defaults for a specific alloy.

## Workflow

1. Identify the load point: a fully reversed strain amplitude eps_a, or
   a nominal elastic stress amplitude S at a notch with fatigue notch
   factor k_f.
2. For a direct strain input, get the life: reversals_to_failure(eps_a)
   returns 2N_f; cycles are 2N_f / 2.
3. Categorize the point: regime_classification(eps_a) returns
   "low-cycle" when 2N_f < 2N_t (transition_reversals) and
   "high-cycle" otherwise.
4. For a notch load point, bridge the stress to the local strain:
   neuber_local_strain(k_f, S) returns sigma_loc, eps_loc and a plastic
   flag from the Neuber identity on the Ramberg-Osgood curve.
5. Read the local strain back through the curve:
   reversals_to_failure(eps_loc) gives the local notch life.
6. Run the one-call summary strain_life_point(S, k_f) for sigma_loc,
   eps_loc, reversals and cycles to failure, regime and verdict.
7. Confirm the deterministic checks with the contract test
   scripts/test_strain_life_fatigue.py.

## Worked example

Representative aluminum (default table), fully reversed loading.

- eps_a = 0.01: reversals_to_failure(0.01) = 2135 reversals (1068
  cycles). Since 2135 < 2N_t = 3266 reversals, regime_classification
  returns "low-cycle". The 0.01 life sits in the low-cycle band
  (between 1e3 and 1e5 reversals).
- eps_a = 0.002: reversals_to_failure(0.002) = 8.11e6 reversals, well
  above both the 0.01 life and 2N_t, so the point is "high-cycle"
  (elastic-dominated).
- Transition: 2N_t = 3266 reversals (1633 cycles); at that point
  eps_e = eps_p = 4.285e-3, and the total amplitude is 8.569e-3.
- Monotonicity: over the strain ladder 0.004, 0.006, 0.008, 0.012,
  0.015 the predicted lives fall strictly: 5.63e4, 1.01e4, 3.99e3,
  1.34e3, 788 reversals.
- Neuber rule, k_f = 2.5, S = 200 MPa: neuber_local_strain(2.5, 200e6)
  returns sigma_loc = 459.1 MPa, eps_loc = 7.60e-3, plastic flag True.
  The local strain exceeds the nominal elastic value S/E = 2.79e-3,
  and the Neuber identity holds: sigma_loc * eps_loc = 3.487e6 Pa =
  (k_f * S)^2 / E. Reading the local strain through the curve gives
  4664 reversals, just above 2N_t, so this notch point is categorized
  high-cycle even though the notch root yields; the summary notes that.
- Same notch at S = 300 MPa: strain_life_point(300e6, 2.5) returns
  sigma_loc = 546.0 MPa, eps_loc = 1.437e-2, plastic flag True,
  reversals to failure 870 (435 cycles), regime "low-cycle", verdict
  "low-cycle plastic-dominated fatigue life".
- Steel contrast: for the 4340 entry 2N_t = 682 reversals and
  reversals_to_failure(0.01) = 752 reversals, showing the shorter
  ductile transition of the higher strength steel.

## Verification

- reversals_to_failure(0.01) returns 2135.47 reversals (between 1e3
  and 1e5) and regime_classification(0.01) == "low-cycle".
- reversals_to_failure(0.002) returns 8.11e6 reversals and the regime
  is "high-cycle"; predicted life falls monotonically as eps_a rises
  over five ladder points.
- At 2N_t = 3266 the elastic and plastic amplitudes agree to 1e-6
  relative.
- neuber_local_strain(2.5, 200e6): sigma_loc * eps_loc equals
  (k_f * S)^2 / E to 1e-9 relative, eps_loc > S/E, plastic flag True;
  with k_f = 1.0 and S = 30 MPa the flag is False and sigma_loc = S.
- Round trip: strain_amplitude(reversals_to_failure(eps_a)) recovers
  eps_a for the ladder points.
- ValueError rejection: non-positive or non-finite strain, stress,
  modulus or reversals, k_f < 1, unknown material names, n_prime
  outside (0, 1), K_prime <= 0.
- Run the contract test offline: python3
  scripts/test_strain_life_fatigue.py (34 tests, deterministic).

## Related leaves

- structures/fatigue/stress-life-curve: the high-cycle S-N counterpart
  for loads far below yield.
- structures/fatigue/notch-sensitivity: fatigue notch factor k_f from
  k_t and material sensitivity, the input the Neuber bridge needs.
- structures/fatigue/goodman-diagram: mean-stress correction, assumed
  zero mean in this leaf.
- structures/fatigue/miner-damage and
  structures/fatigue/load-spectrum-counting: damage accumulation over
  the variable amplitude spectrum once each point life is known.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_strain_life_fatigue.py

The test covers the Coffin-Manson amplitude and its monotonic fall with
life, the 0.01 and 0.002 worked-example lives and their regime strings,
the transition life with elastic-plastic equality at 2N_t, monotonic
life over five strain points, the Ramberg-Osgood curve values and
bounds, the Neuber anchor (local stress and strain, plastic flag,
product identity to 1e-9 relative, elastic limit with k_f = 1), the
property-dict override path, and ValueError rejection of non-positive,
non-finite, out-of-range and unknown inputs.

## Compliance

- Standards referenced by name, not reproduced: FAR 25 (damage
  tolerance and fatigue evaluation practice), CS-25 (EASA
  counterpart), MMPDS (material allowables context). The material
  constants in this leaf are representative typicals stated in this
  document, not MMPDS table values, and the equations are standard
  engineering methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
