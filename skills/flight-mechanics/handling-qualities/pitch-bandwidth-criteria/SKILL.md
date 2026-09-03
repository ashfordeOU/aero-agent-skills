---
name: pitch-bandwidth-criteria
description: "Use when you must assess the pitch-axis flying qualities of an aircraft with the MIL-STD-1797A bandwidth and phase-delay criterion: model the pitch attitude response as a short period transfer function with a control anticipation numerator time constant and an actuator lag, evaluate the frequency response, find the bandwidth frequency omega_BW as the lower of the 45 degree phase margin frequency and the 6 dB gain margin frequency, read the -180 degree frequency, compute the phase delay tau_p from the phase at twice omega_180, and grade the Category A Level 1, 2 and 3 boundaries. Produces omega_BW, omega_180, tau_p, the flying qualities level and the limiting criterion. Trigger: pitch bandwidth criterion, phase delay tau, bandwidth frequency, phase margin 45 degrees, mil-std-1797a bandwidth, short period transfer function, actuator lag, flying qualities level."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mil-std-1797a
    reference-only: true
gated: false
domain: flight-mechanics
pack: handling-qualities
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-mechanics
  subdomain: handling-qualities
  tags: [pitch-bandwidth-criteria, bandwidth-frequency, phase-delay, phase-margin, mil-std-1797a-bandwidth, short-period-transfer-function, actuator-lag, flying-qualities-level]
  version: 0.1.0
  author: AeroSkills
---

# Pitch Bandwidth Criteria (flight-mechanics/handling-qualities/pitch-bandwidth-criteria)

Use when the task is assessing pitch-axis flying qualities with the
MIL-STD-1797A bandwidth and phase-delay criterion, the frequency-domain
method that grades the pitch attitude response directly from its open
loop frequency response. This leaf models the pitch attitude transfer
function as a short period mode plus a control anticipation numerator
time constant and an actuator lag, evaluates the response, extracts the
bandwidth frequency omega_BW and the phase delay tau_p, and returns the
Level 1, 2 or 3 verdict with the limiting criterion. It is the
companion to the modal level tables in the mil-std-1797a leaf: same
standard, different assessment method (frequency-domain bandwidth
instead of per-mode damping tables). Implementation is pure Python,
stdlib only, deterministic and offline.

## Domain quick reference

- Pitch attitude model (K normalized to 1.0, the criterion uses phase
  and gain ratio only): G(s) = (1 + T_th2*s) / (s * (s^2 + 2*zeta*wn*s +
  wn^2) * (1 + s/w_act)), with wn the short period natural frequency
  (rad/s), zeta the short period damping, T_th2 the control anticipation
  time constant (s) and w_act the actuator lag frequency (rad/s).
- Unwrapped phase: phase = atan(w*T_th2) - 90 - atan2(2*zeta*wn*w,
  wn^2 - w^2) - atan(w/w_act) degrees, continuous from -90 degrees at
  the origin (the lead term can lift it a fraction of a degree just
  above zero before the mode lag dominates). The module unwraps the
  principal phase numerically over a fine 0.01 rad/s grid and refines
  every crossing with a bisection root finder.
- Bandwidth definition: omega_BW is the lower of the frequency at
  which the phase margin is 45 degrees (phase equals -135 degrees,
  omega_135) and the 6 dB gain margin frequency (omega_GM6). A -6 dB
  gain crossing counts only when it sits at or beyond the -180 degree
  phase crossing, the region where gain margin actually limits the
  loop; the low frequency crossing of the normalized response (phase
  near -93 degrees) never limits bandwidth and is reported as None.
  Documented assumption of this leaf, recorded because the gain is
  normalized to unity.
- Phase delay: tau_p = -(phase(2*omega_180) + 180) / (2*omega_180) *
  (pi/180) seconds, from the unwrapped phase at twice the -180 degree
  frequency. None when omega_180 does not exist.
- Level boundaries (representative Category A pitch values from
  MIL-STD-1797A 4.5.1, class dependent in the standard; verify against
  the current revision before certifying an airframe): Level 1 needs
  omega_BW >= 3.5 rad/s and tau_p <= 0.2 s; Level 2 needs omega_BW >=
  2.5 rad/s and tau_p <= 0.2 s; otherwise Level 3. The limiting
  criterion is bandwidth, phase delay or both.
- ValueErrors: wn <= 0, zeta <= 0 or >= 1, T_th2 <= 0, w_act <= wn,
  and a non-positive evaluation frequency are rejected.

## Workflow

1. Fix the airframe response parameters: short period wn and zeta
   (from the stability leaves or a flight test short period fit), the
   control anticipation time constant T_th2 and the actuator lag
   frequency w_act. Check that w_act > wn.
2. Evaluate the criterion metrics with bandwidth(wn, zeta, T_th2,
   w_act): it returns omega_135, omega_GM6, omega_BW, omega_180 and
   tau_p. The unwrapped phase comes from phase_deg and the magnitude
   from mag_db; crossings are located by find_root_phase over the dense
   unwrapped phase table with bisection refinement.
3. Grade the result with level_verdict(omega_BW, tau_p), which returns
   the level, the limiting criterion (bandwidth, phase delay or both)
   and any metric that could not be computed. Verify the numerical
   building blocks separately when needed: transfer for the complex
   response and unwrap_phase_deg for phase series continuity.
4. State the verdict with the governing metric. When the level
   boundaries sit near the computed values, recheck the aircraft class
   and flight phase category against the current MIL-STD-1797A revision
   because the representative boundaries used here are Category A
   values and are class dependent.
5. Confirm the deterministic checks with the contract test
   scripts/test_pitch_bandwidth_criteria.py.

## Worked example

Case A: wn = 4.0 rad/s, zeta = 0.7, T_th2 = 0.5 s, w_act = 25 rad/s.

- omega_135 = 4.58 rad/s: the 45 degree phase margin crossing. The
  6 dB gain margin crossing is not reached in the stability relevant
  band (omega_GM6 is None), so omega_BW = omega_135 = 4.58 rad/s.
- omega_180 = 10.13 rad/s; the phase at twice omega_180 gives
  tau_p = 0.0247 s.
- Verdict: Level 1 (omega_BW 4.58 >= 3.5 and tau_p 0.0247 <= 0.2),
  limiting criterion bandwidth.

Case B: wn = 3.0 rad/s, zeta = 0.6, T_th2 = 0.7 s, w_act = 20 rad/s.

- omega_135 = 3.43 rad/s, omega_BW = 3.43 rad/s, omega_180 = 7.23
  rad/s, tau_p = 0.0325 s.
- Verdict: Level 2 (omega_BW 3.43 is below the Level 1 floor of 3.5
  but above 2.5; tau_p is fine), limiting criterion bandwidth.

## Verification

- bandwidth(4.0, 0.7, 0.5, 25.0) returns omega_135 4.5832 rad/s,
  omega_180 10.1290 rad/s, tau_p 0.0246 s, omega_GM6 None and omega_BW
  equal to omega_135; level_verdict gives Level 1, limiting bandwidth.
- bandwidth(3.0, 0.6, 0.7, 20.0) returns omega_135 3.4315 rad/s,
  omega_180 7.2257 rad/s, tau_p 0.0325 s and a Level 2 verdict.
- Confirm the lightly damped trend: at zeta 0.35 the phase drops faster
  and omega_135 is below the zeta 0.7 value at the same wn.
- Confirm every non-positive wn and w, zeta outside (0, 1), T_th2 <= 0
  and w_act <= wn raises ValueError.
- Run the contract test offline: python3
  scripts/test_pitch_bandwidth_criteria.py (35 tests, deterministic,
  passes in under a second).

## Related leaves

- flight-mechanics/handling-qualities/mil-std-1797a: the modal level
  table companion criterion from the same standard; this leaf applies
  the frequency-domain bandwidth method instead of the per-mode tables.
- flight-mechanics/handling-qualities/pilot-induced-oscillation:
  phase-related neighbor for pilot-in-the-loop coupling risk.
- flight-mechanics/handling-qualities/cooper-harper-rating: pilot
  rating scale for the piloted evaluation that complements the level
  verdicts.
- flight-mechanics/stability-control/short-period-mode-analysis: source
  of the short period wn and zeta inputs to the model.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_pitch_bandwidth_criteria.py

The test covers the Case A and Case B worked examples against the spec
reference numbers within tolerance, the lightly damped and low
frequency trends, the gain margin branch (very low wn), the unwrapped
phase helper and its consistency with the branch-corrected analytic
phase, the bisection root finder on reachable and unreachable targets,
magnitude versus transfer self consistency, the Level 1/2/3 verdict
boundaries and missing metric reporting, and ValueError rejection of
non-physical parameters and frequencies.

## Compliance

- Standards referenced, not reproduced: MIL-STD-1797A section 4.5.1
  frames the bandwidth and phase-delay criterion. The level boundaries
  coded in this leaf are representative Category A values and are class
  dependent in the standard, so verify them against the current
  revision before a certification-grade assessment. The transfer model
  and relations above are standard engineering methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
