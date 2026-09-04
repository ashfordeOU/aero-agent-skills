# Wave-33 leaf spec: rotorcraft-lead-lag-dynamics (flight-mechanics, performance pack)

- Path: skills/flight-mechanics/performance/rotorcraft-lead-lag-dynamics/
- Pack: performance. Sibling: rotorcraft-blade-flapping-dynamics (flap
  dynamics: Lock number, coning, flap frequency ratio; its SKILL.md
  explicitly excludes lag dynamics and ground resonance). This leaf is
  the lead-lag complement: lag frequency ratio, fixed-frame multiblade
  lag modes, coincidence rotor speed, ground-resonance clearance.
- Standards id: far-29 (reference-only). Ledger Standard: far-29.
- Family: flight-mechanics

## Claim

Compute the rotating lead-lag frequency ratio of a helicopter rotor
blade (from the lag-hinge offset for an idealized uniform blade, or as a
measured/design input), the fixed-frame multiblade lag mode frequencies
(collective nu Omega, regressing |1 - nu| Omega, advancing (1 + nu)
Omega) for a 3+ bladed rotor, and the Coleman-diagram frequency-
coincidence rotor speed Omega* = omega_F / |1 - nu| where the regressing
lag mode meets the airframe lateral frequency, returning a ground-
resonance clearance verdict against the operating rotor speed. Damping /
coupled eigenvalue stability analysis is explicitly out of scope (the
wave-32 decline receipt): this leaf provides the deterministic
frequency-coincidence and clearance layer only.

Does NOT do: full coupled Coleman ground-resonance stability eigenmodel
(declined wave-32: no closed-form physical anchor at coupled pinned
coefficients in pure stdlib); blade flapping/coning/Lock number
(rotorcraft-blade-flapping-dynamics); flap frequency ratio (same
sibling); control-theory lead/lag phase compensation
(gnc-autonomy/control/lead-lag-compensation); phase lag in handling
qualities (pilot-induced-oscillation / pitch-bandwidth-criteria own
that sense of "lag").

## Model (implement exactly)

Module constants:
- PI = math.pi.

Functions (pure stdlib):

- lag_frequency_ratio_hinge_offset(hinge_offset_fraction) -> nu_zeta =
  sqrt(1.5 e / (1 - e)) where e = lag-hinge offset fraction in [0, 1).
  Idealized uniform blade, centrifugal-potential derivation (the in-plane
  analog of the flap frequency formula; at e = 0 the rotating lag
  frequency is zero - no 1/rev term, unlike flap where nu = 1 at e = 0).
  ValueErrors if e < 0 or e >= 1.
- fixed_frame_lag_modes(nu, omega_rad_s) -> dict {collective_hz:
  nu Omega / 2pi, regressing_hz: |1 - nu| Omega / 2pi, advancing_hz:
  (1 + nu) Omega / 2pi}. ValueErrors on nu < 0 or Omega <= 0.
- regressing_lag_frequency(nu, omega_rad_s) -> |1 - nu| Omega / 2pi
  (Hz). ValueErrors as above.
- coincidence_rotor_speed(nu, airframe_frequency_hz) -> Omega* =
  2 pi omega_F / |1 - nu| (rad/s). ValueErrors on nu < 0, airframe
  frequency <= 0. Note |1 - nu| = 0 (nu = 1) is not physical for lag
  (nu < 1 for realistic offsets); still guard with ValueError.
- ground_resonance_clearance(nu, operating_omega_rad_s,
  airframe_frequency_hz, margin=0.20) -> dict {coincidence_omega,
  operating_omega, clearance_fraction: (Omega* - Omega_op)/Omega_op,
  verdict: "clear" if the coincidence is more than margin away from the
  operating speed, else "resonance-adjacent"}. ValueErrors propagate.
- lead_lag_summary(hinge_offset_or_nu, omega_rad_s,
  airframe_frequency_hz, margin=0.20) -> dict with the lag frequency
  ratio, the three fixed-frame mode frequencies, the coincidence rotor
  speed, and the clearance verdict. Accept either the hinge offset
  (0 <= e < 1) or nu directly (float >= 0) - document the input
  convention precisely; a helper resolves which was passed.

ALL functions deterministic, no RNG, stdlib only.

## Worked example

Typical articulated rotor: lag-hinge offset e = 0.05, operating rotor
speed Omega = 44 rad/s, airframe lateral natural frequency 5.0 Hz.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- lag_frequency_ratio_hinge_offset(0.05) = sqrt(1.5*0.05/0.95) about
  0.2810 (published articulated lag frequencies 0.2-0.4/rev).
- At Omega = 44 rad/s: collective lag mode about 1.968 Hz, regressing
  about 5.035 Hz (0.719/rev), advancing about 8.970 Hz.
- coincidence_rotor_speed(nu=0.2810, airframe 5.0 Hz) = 2 pi 5.0 /
  (1 - 0.2810) about 43.69 rad/s -> 0.7% below the operating 44 rad/s
  -> verdict resonance-adjacent (the classic ground-resonance exposure).
- airframe 3.5 Hz -> Omega* about 30.58 rad/s (about 30.5% below
  operating) -> clear.
- Sibling cross-check: the flap frequency ratio formula at e = 0.05
  gives 1.03872 (this leaf must NOT reproduce flap nu; cite it only).

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: e < 0 or e >= 1; nu < 0; Omega <= 0; airframe frequency
  <= 0; |1 - nu| == 0.
- lag_frequency_ratio_hinge_offset(0.05) about 0.2810; e = 0 gives
  exactly 0.0; larger e gives larger nu; e -> 0.5 gives
  sqrt(1.5*0.5/0.5) = sqrt(1.5) about 1.2247.
- Fixed-frame identities: collective + regressing frequencies satisfy
  the multiblade relations (regressing = (1-nu)Omega/2pi etc.);
  regressing decreases with nu, advancing increases with nu.
- Coincidence math: airframe 5.0 Hz, nu 0.2810 -> about 43.69 rad/s;
  ground_resonance_clearance with the worked numbers returns
  resonance-adjacent; a clearly separated airframe frequency (e.g.
  3.5 Hz) returns clear; margin parameter changes the verdict boundary.
- Determinism: identical floats run-to-run.
- Convenience dict contains exactly the documented keys.

## Corpus fragment (eval/hit1-wave33-rotorcraft-lead-lag-dynamics.yaml)

Query 1 (copy verbatim):
  "compute the regressing lead-lag mode frequency per revolution and the coincidence rotor speed where it crosses the airframe lateral frequency for ground resonance clearance"
  intent: "flight-mechanics; rotorcraft regressing lag mode frequency and ground-resonance coincidence rotor speed"
  expected_skill: "flight-mechanics/performance/rotorcraft-lead-lag-dynamics"
Query 2 (copy verbatim):
  "estimate the rotating lead-lag frequency ratio from the lag hinge offset and list the fixed frame collective advancing and regressing lag mode frequencies"
  intent: "flight-mechanics; rotorcraft lag frequency ratio from hinge offset and multiblade fixed-frame modes"
  expected_skill: "flight-mechanics/performance/rotorcraft-lead-lag-dynamics"
Task ids: w33-rotorcraft-lead-lag-dynamics-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must compute the lead-lag dynamics
of a helicopter main rotor:" and include the outputs in the Claim.
First tag: rotorcraft-lead-lag-dynamics. Additional tags ONLY:
lead-lag-frequency, lag-hinge-offset, regressing-lag-mode,
ground-resonance-clearance, coincidence-rotor-speed, multiblade-modes.
NEVER single generic words (lag, rotor, blade, dynamics, resonance,
frequency, mode). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): Lock number, coning angle, flap
frequency ratio, flap hinge offset (rotorcraft-blade-flapping-dynamics);
hover power, thrust coefficient, torque coefficient, collective pitch
(BET hover leaf); momentum theory, induced velocity (hover/axial
leaves); autorotation, descent rate; lead lag compensation, phase lead
(gnc lead-lag-compensation); phase lag, PIO (handling-qualities). The
tokens "lead-lag", "lag hinge offset", "regressing", "ground resonance
clearance", "coincidence rotor speed" are this leaf's own. The words
"ground resonance" may appear only in the clearance-verdict sense, never
as a stability-eigenvalue claim.

Tags: [rotorcraft-lead-lag-dynamics, lead-lag-frequency,
lag-hinge-offset, regressing-lag-mode, ground-resonance-clearance,
coincidence-rotor-speed, multiblade-modes]

Sibling-citation lines for Related leaves:
flight-mechanics/performance/rotorcraft-blade-flapping-dynamics (the
flap-dynamics sibling; flap frequency formula at e = 0.05 -> 1.03872 is
cited there, lag nu is this leaf's own),
flight-mechanics/performance/rotorcraft-blade-element-hover-performance,
flight-mechanics/stability-control/spin-recovery (fixed-wing
autorotation, a different topic).

Ledger Standard: far-29.
