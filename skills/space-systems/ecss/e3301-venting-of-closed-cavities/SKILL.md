---
name: e3301-venting-of-closed-cavities
description: "Verify that every closed cavity of a mechanism is vented, per ECSS-E-ST-33-01C clause 4.7.5.4.11. Use when ascent depressurization must not burst, distort or contaminate a sealed volume: enumerating the cavities and reporting an unvented one before any arithmetic, reducing vent hole area by discharge and deep-channel losses, forming the choked-flow venting time constant, multiplying it by the peak depressurization rate for the differential the cavity lags ambient by, applying the vent-area-per-litre screen independently, and flagging blockage-prone holes, blind pockets and unscreened discharges. Trigger: ecss, e-st-33-01-mechanisms-scope, closed-cavity-venting, cavity-venting-time-constant, ascent-depressurization-differential, vent-area-per-litre-screen, vent-path-contamination-trap, unvented-cavity-detection."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-venting-of-closed-cavities, closed-cavity-venting, cavity-venting-time-constant, ascent-depressurization-differential, vent-area-per-litre-screen, vent-path-contamination-trap, unvented-cavity-detection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Venting of Closed Cavities (space-systems/ecss/e3301-venting-of-closed-cavities)

Use when the task is the venting case of ECSS-E-ST-33-01C clause
4.7.5.4.11 -- showing that no volume inside a mechanism stays sealed
through ascent, that the differential pressure each vented cavity sees
is inside what its structure allows, and that the vent path solving the
pressure problem has not created a contamination problem.

## Domain quick reference

- The first question is not how big the vent is, it is whether there is
  one. A cavity with no vent is a finding in its own right; running it
  through a flow calculation with zero area yields an infinity, not an
  answer, and hides the defect behind an arithmetic error.
- A vent hole does not flow its geometric area. The discharge
  coefficient of a plain drilled hole takes roughly a third of it, and a
  hole through a thick wall loses more as its length-to-diameter ratio
  grows, so the effective area is what enters every downstream number.
- During ascent the flow through the vent is choked for most of the
  profile, which makes the venting behaviour a first-order lag with a
  time constant tau = V / (A_eff * c*), where c* is the critical
  discharge velocity of the gas at its temperature. Bigger cavity, slower
  vent; more effective area, faster vent.
- The differential pressure the cavity sees is that time constant
  multiplied by the peak depressurization rate of the ascent profile. It
  is a lag, not a leak rate, and it scales linearly with a launcher
  profile change.
- The heritage vent-area-per-litre screen is kept as a second,
  independent check. It carries no assumption about the ascent rate, so
  it still catches a cavity that passed the lag calculation only because
  a favourable profile was assumed.
- A vent is also a path in and out for contamination. A hole small
  enough to be blocked by handling debris is not a vent; a blind pocket
  traps cleaning fluid and particulate whatever its area; and a vent
  discharging at an optical or a bearing surface needs a screen or a
  different exit.

## Workflow

1. Enumerate every closed cavity with a name, a volume, its vent hole
   set, the differential pressure its structure allows and the peak
   depressurization rate of the ascent profile. Refuse an empty set and
   refuse duplicate names.
2. For each cavity with no vent hole, report it as unvented and stop
   there; do not compute a time constant for it.
3. Reduce the geometric hole area by the discharge coefficient and by
   the deep-channel loss of the vent length.
4. Form the choked-flow venting time constant from the cavity volume,
   the effective area and the critical discharge velocity at the
   declared gas temperature.
5. Multiply by the peak depressurization rate and compare the result
   with the allowable differential, absorbing representation error at
   the boundary with a named tolerance.
6. Compute the effective vent area per litre and apply the heritage
   screen independently of the pressure result.
7. Screen the vent path for blockage-prone diameters, blind pockets and
   unscreened discharges at sensitive surfaces, then report every
   cavity, the governing one among the vented, and the unvented count.

## Pitfalls

- Sizing on the geometric hole area. Discharge and channel losses take a
  large and very unevenly distributed bite; two vents of the same
  drilled diameter in walls of different thickness do not flow the same.
- Treating an unvented cavity as a zero-area cavity. It is a design
  finding to be fixed, not a number to be reported, and a zero divides
  rather than warns.
- Passing the pressure check and skipping the area screen. The pressure
  check inherits whatever ascent rate was assumed; the area screen does
  not, which is exactly why both are kept.
- Forgetting that the launcher sets the rate. A cavity qualified against
  one ascent profile is not qualified against a steeper one, and the
  differential scales linearly with the rate.
- Solving the pressure problem with many tiny holes. Total area rises
  while every individual hole moves closer to the diameter at which
  handling debris blocks it, and a blocked hole contributes nothing.
- Venting into the nearest convenient space. The exit matters: a vent
  discharging at an optic, a detector or an open bearing turns a
  pressure fix into a contamination path unless it is screened or
  rerouted.

## Behavior contract (gate 3)

The cavity enumeration and unvented detection, discharge and
deep-channel area losses, critical discharge velocity, choked-flow time
constant, depressurization-lag differential, vent-area-per-litre screen,
contamination-trap screen and governing-cavity selection are exercised
by the gate 3 contract test:
scripts/test_e3301_venting_of_closed_cavities.py against
scripts/e3301_venting_of_closed_cavities_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_venting_of_closed_cavities.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
