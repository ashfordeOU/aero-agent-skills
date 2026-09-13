---
name: e2007-launch-phase-receiver-overload
description: "Use when verify that an onboard radio-frequency receiver tolerates launch-site emitter overload under ECSS-E-ST-20-07C clause 4.2.2.2: convert each range-radar, pad-telemetry and launcher-transmitter illumination from field-strength to power-density, apply the receiver antenna effective-aperture and the front-end frequency-rejection, sum the coupled level at the antenna-port over every emitter active in the phase, and compare it against the receiver overload-threshold and damage-threshold with the declared margin - for the fairing-enclosed and the fairing-jettisoned configuration alike, so the prelaunch, liftoff and ascent phases are each demonstrated rather than assumed. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, receiver-overload, launch-site-emitter, fairing-attenuation, antenna-port-coupling, front-end-rejection, prelaunch-electromagnetic-environment, damage-threshold-margin."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-launch-phase-receiver-overload, receiver-overload, launch-site-emitter, fairing-attenuation, antenna-port-coupling, front-end-rejection, damage-threshold-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Launch-Phase Receiver Overload (space-systems/ecss/e2007-launch-phase-receiver-overload)

Use when the task is the launch-phase receiver-overload demonstration of
ECSS-E-ST-20-07C clause 4.2.2.2 -- showing that every onboard receiver
survives and recovers from the launch-site electromagnetic environment
throughout prelaunch, liftoff and ascent, in the fairing-enclosed and
the fairing-jettisoned configuration alike.

## Domain quick reference

- The launch site is a dense emitter environment: range-safety and
  tracking radars, pad telemetry and command transmitters, launcher
  transponders and site communications all illuminate the spacecraft
  while it is captive. The clause asks for a demonstration, not an
  assumption, and the demonstration must cover the configuration in
  which the fairing is still on and the configuration after fairing
  jettison, because the jettison removes the only broadband shield the
  receiver antenna has.
- The coupling chain has four steps. A declared field-strength in volts
  per metre becomes a power-density by dividing by the free-space
  impedance. The power-density becomes an intercepted power through the
  receiver antenna effective-aperture, which scales with the square of
  the wavelength at the illuminating frequency and with the antenna
  gain in that direction. The fairing, when present, removes a
  broadband shielding attenuation. The receiver front-end then rejects
  whatever falls outside its passband.
- Front-end rejection is not binary. An emitter inside the receiver
  passband is rejected by nothing at all; an emitter outside it is
  attenuated by the front-end selectivity, rising with frequency offset
  and saturating at the stopband floor of the filter. The model used
  here is a slope in decibels per octave of offset beyond the passband
  edge, capped at a maximum rejection -- a filter does not reject
  without limit, and assuming it does is how an out-of-band radar
  disappears from an assessment it should have dominated.
- Two thresholds are compared, and they are different requirements. The
  overload-threshold is the level above which the receiver saturates
  and loses its function until the environment subsides; the
  damage-threshold is the level above which the front-end is destroyed.
  Exceeding overload during a phase when the link is not needed can be
  acceptable if recovery is demonstrated; exceeding the damage
  threshold never is. The damage-threshold therefore sits at or above
  the overload-threshold, and a record claiming otherwise is rejected.
- Emitters add at the antenna-port in linear power, not in decibels.
  Several emitters each a few decibels below the overload-threshold can
  sum above it, which is exactly the case a per-emitter comparison
  misses.

## Workflow

1. Normalize the emitter inventory: identifier, illuminating frequency,
   field-strength at the vehicle, and the launch phases in which the
   emitter is radiating. Reject a non-positive frequency or
   field-strength and an unrecognised phase before anything is summed.
2. Normalize each receiver: centre frequency, passband width, antenna
   gain, overload-threshold, damage-threshold, required margin and the
   front-end rejection slope and floor. Reject a damage-threshold below
   the overload-threshold and a negative required margin.
3. For each required phase and configuration pair, select the emitters
   radiating in that phase. If none is declared, that is a data gap and
   a finding in its own right, not a pass by absence.
4. For each selected emitter compute the coupled level at the
   antenna-port: field-strength to power-density, power-density times
   effective-aperture, minus the fairing shielding attenuation when the
   configuration is fairing-enclosed (and exactly zero when it is
   jettisoned), minus the front-end rejection at that frequency offset.
5. Sum the per-emitter coupled levels in linear power and convert the
   total back to decibels relative to a milliwatt.
6. Compute the overload margin and the damage margin against the summed
   level, and compare each against the required margin with an explicit
   floating-point tolerance. Report the driving emitter per case.
7. The receiver is demonstrated only when every required phase and
   configuration pair passes both margins; a single missing pair leaves
   the clause unsatisfied regardless of the margins that were computed.

## Pitfalls

- Assessing the fairing-enclosed configuration only: the jettisoned
  case removes tens of decibels of shielding and is usually the sizing
  case, so a demonstration that stops at fairing separation has not
  covered the clause.
- Comparing each emitter separately against the threshold: the port
  sees the linear sum, so several individually-compliant emitters can
  jointly overload the front-end.
- Treating out-of-band emitters as fully rejected: front-end
  selectivity has a stopband floor, and a high-power range radar far
  outside the passband can still dominate once that floor is applied.
- Reusing the receiver centre frequency for the effective-aperture of
  an out-of-band illumination: the aperture follows the wavelength of
  the illuminating emitter, not of the wanted signal.
- Merging the overload-threshold and the damage-threshold into one
  number: recoverable saturation and permanent destruction are
  different findings with different dispositions.
- Testing the margin with a bare greater-or-equal: the margin is a
  difference of decibel quantities built from logarithms, so an exactly
  compliant case can land a few units in the last place below the
  requirement. Absorb the representation error in the comparison, never
  by relaxing the required margin.

## Behavior contract (gate 3)

The emitter and receiver normalization, field-strength to power-density
conversion, effective-aperture, fairing-attenuation, front-end
rejection, linear-sum aggregation and margin logic is exercised by the
gate 3 contract test:
`scripts/test_e2007_launch_phase_receiver_overload.py` against
`scripts/e2007_launch_phase_receiver_overload_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_launch_phase_receiver_overload.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
