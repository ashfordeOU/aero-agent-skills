---
name: e2006-electrodynamic-tether-oscillation-hazards
description: "Use when determine whether the Lorentz-force interaction on a deployed electrodynamic-tether can pump a dynamic instability, under ECSS-E-ST-20-06C clause 10.2.6: build the mode table from the orbital mean-motion (gravity-gradient libration, taut-string transverse and axial longitudinal modes), assemble the forcing spectrum from orbital harmonics of the geomagnetic-field variation and from the current-modulation rate, categorize every forcing line as libration-resonance, transverse-string-resonance, longitudinal-resonance or off-resonance inside a detuning band, amplify the quasi-static libration deflection by the resonant quality-factor, then judge it against the dumbbell tumbling-separatrix and the transverse-sag slack-onset limit. Trigger: ecss, e-st-20-electrical-scope, e-st-20-06c-clause-10-2-6, electrodynamic-tether, tether-libration-resonance, lorentz-force-pumping, transverse-string-mode, tether-slack-onset, gravity-gradient-tumbling, current-modulation-rate."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-electrodynamic-tether-oscillation-hazards, electrodynamic-tether, tether-libration-resonance, lorentz-force-pumping, transverse-string-mode, tether-slack-onset, gravity-gradient-tumbling]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Electrodynamic-Tether Oscillation Hazards (space-systems/ecss/e2006-electrodynamic-tether-oscillation-hazards)

Use when the task is the ECSS-E-ST-20-06C clause 10.2.6 question of whether
the electrical interaction of a long deployed tether — current flowing
through the geomagnetic field — can excite a growing oscillation of the
tether or of the tether/spacecraft system as a whole.

## Domain quick reference

- Clause 10.2.6 is a dynamics question raised by an electrical cause. The
  tether current crossed with the geomagnetic field gives a transverse
  Lorentz load distributed along the strand. That load is not steady: the
  field the tether flies through repeats with the orbit, so the load carries
  orbital harmonics, and a switched or duty-cycled current adds a
  modulation line of its own. A deployed tether is a very lightly damped
  structure, so a forcing line that lands on a mode is pumped, orbit after
  orbit, with nothing to bleed the energy away.
- The mode table has three families and they sit decades apart in frequency.
  The gravity-gradient libration modes of the dumbbell are the slowest: the
  in-plane (pitch) mode at sqrt(3) times the orbital mean-motion, the
  out-of-plane (roll) mode at exactly twice it. The taut-string transverse
  modes follow from the tension and the linear density. The axial
  longitudinal modes, set by the strand's axial stiffness, are the fastest
  by orders of magnitude and are reachable only by a fast current switch.
- The second orbital harmonic of the Lorentz load sits exactly on the
  out-of-plane libration mode. That coincidence is the classic
  electrodynamic-tether instability: an unmodulated current in a tether
  whose balance point is offset from mid-span feeds the roll mode at its own
  natural frequency, and the amplitude grows until the current is modulated
  out of phase with it or the libration is damped.
- A uniform transverse load on a symmetric tether produces no net torque
  about the centre-of-mass — it only bows the strand. The libration drive
  therefore scales with how far the balance point sits from mid-span, which
  for a real mission (heavy host spacecraft, light end body) is most of the
  way to one end.
- Two limits close the assessment. The pitch libration separatrix near 65.9
  degrees is where the gravity-gradient restoring torque stops recapturing
  the tether and the system tumbles. The transverse-sag ratio — mid-span
  bow divided by span — marks where the bowed strand loses tension and goes
  slack, after which it can recoil, wrap or foul.

## Workflow

1. Validate the deployed configuration: altitude, deployed length, linear
   density, operating tension, axial stiffness, tether current, local field
   magnitude and incidence, both end masses, and the libration damping
   ratio. Reject a non-physical entry before any mode is computed.
2. Build the mode table: orbital mean-motion from the altitude, the two
   libration modes from it, the transverse modes from tension and linear
   density, the longitudinal modes from axial stiffness and linear density.
3. Assemble the forcing spectrum: one line per orbital harmonic of the
   Lorentz load, plus the current-modulation fundamental and its second
   harmonic when the current is switched rather than continuous.
4. Categorize each forcing line against the nearest mode inside the
   detuning band — libration-resonance, transverse-string-resonance,
   longitudinal-resonance, otherwise off-resonance. A line sitting on the
   band edge is read as resonant.
5. Size the response: net Lorentz torque about the centre-of-mass divided
   by the modal stiffness of the in-plane libration mode, multiplied by the
   resonant quality-factor 1/(2*zeta) when a libration line is resonant and
   by unity when none is.
6. Judge the result: flag every resonant line, flag an amplitude over the
   mission allowable, flag an amplitude past the tumbling separatrix, and
   flag a transverse-sag ratio past the slack-onset limit. The
   configuration is hazard-free only when all four lists are empty.

## Pitfalls

- Checking the libration modes only and skipping the string modes — a fast
  current switch cannot move the libration modes but lands squarely on a
  transverse mode, which fatigues the strand and drives the tip body.
- Treating an unmodulated current as the benign case. The steady current is
  precisely what puts the second orbital harmonic on the out-of-plane
  libration mode; modulation is the mitigation, not the hazard.
- Applying the peak Lorentz load as a static deflection and stopping there.
  At resonance the steady-state amplitude is the quasi-static value times
  1/(2*zeta), and a deployed tether's damping ratio is often below one
  percent — a factor of fifty or more that decides the verdict.
- Reading a symmetric dumbbell's zero libration torque as proof of safety.
  The same load still bows the strand, and the sag check, not the libration
  check, is what catches the slack-onset hazard in that configuration.
- Widening the detuning band to make a marginal line read as off-resonance.
  The band expresses model uncertainty in the mode frequencies; moving it to
  clear a finding removes the only margin the check has.

## Behavior contract (gate 3)

The mode-table, forcing-spectrum, resonance-categorization, libration-response
and slack-onset logic is exercised by the gate 3 contract test:
scripts/test_e2006_electrodynamic_tether_oscillation_hazards.py against
scripts/e2006_electrodynamic_tether_oscillation_hazards_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_electrodynamic_tether_oscillation_hazards.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
