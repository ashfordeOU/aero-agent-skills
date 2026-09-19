---
name: e3301-bearing-preloading
description: "Compute the ball-bearing preload a mechanism needs to survive its mechanical environment under ECSS-E-ST-33-01C clause 4.7.3.4.2. Use when the task is sizing preload so a duplex pair never unloads under the worst-case axial reaction, choosing between a solid and a flexible arrangement and applying the separation factor each one earns, predicting the preload shift differential thermal expansion produces across the hot and cold cases, inferring the installed preload from a measured axial natural frequency, and re-verifying it after mounting against the no-unload floor and the torque-and-life ceiling. Trigger: ecss, e-st-33-01c, duplex-bearing-preload, solid-versus-flexible-preload, bearing-separation-factor, bearing-preload-thermal-shift, axial-preload-stiffness, preload-measurement-reverification, bearing-unload-margin."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-bearing-preloading, duplex-bearing-preload, bearing-separation-factor, bearing-preload-thermal-shift, axial-preload-stiffness, preload-measurement-reverification]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Ball-Bearing Preloading (space-systems/ecss/e3301-bearing-preloading)

Use when the task is the bearing-preload step of ECSS-E-ST-33-01C clause
4.7.3.4.2 — preloading a ball-bearing arrangement against the mechanical
environment it has to survive, and then computing, applying, measuring and
re-verifying that preload, with a solid arrangement and a flexible one treated
as the different designs they are.

## Domain quick reference

- Preload exists so the rolling elements stay seated. The failure it prevents
  is not overload but unloading: a row that lifts lets the balls skid, brinell
  the raceway on the next impact and lose the running-torque predictability
  the mechanism was characterised on.
- How much external load a preload survives depends on the arrangement. A
  solidly preloaded duplex pair shares the external axial load between its two
  rows through the Hertzian load-deflection law, so the unloading row does not
  lift until the external load reaches roughly 2.8 times the preload. A
  flexible (spring) arrangement shares nothing: the row lifts as soon as the
  external load reaches the preload. The same duty therefore needs nearly
  three times the preload on a flexible mount as on a solid one.
- The one-third power law k = C*P**(1/3) is the bridge between preload and
  everything measurable. Stiffness rises with preload but strongly
  sub-linearly, which is why a measured axial natural frequency is a sensitive
  preload witness at low preload and a blunt one at high preload.
- Temperature moves preload. A differential axial growth between housing and
  shaft acts on the stiffness of the preload path, and the path is what the
  arrangement choice really buys: a solid mount presents the whole bearing
  stack, so a few micrometres of mismatch is hundreds of newtons; a flexible
  mount puts a soft spring in series and the same mismatch is tens of newtons.
- Re-verification is a two-sided check. The preload has to stay above the
  no-unload floor at the case that relieves it most, and below the
  torque-and-life ceiling at the case that raises it most; a design verified
  only at one end has been verified at neither.

## Workflow

1. Read the arrangement and take its separation factor. Refuse an arrangement
   name outside the known set rather than defaulting it — the factor is the
   single largest term in the sizing and a default would hide the choice.
2. Size the required preload from the worst-case axial reaction and the safety
   factor, divided by the separation factor.
3. Compute the bearing axial stiffness at the applied preload through the
   one-third power law, and the axial natural frequency of the supported mass
   that follows from it.
4. Build the preload-path stiffness: the bearing stack alone for a solid
   mount, the stack in series with the preload spring for a flexible one.
   Refuse a spring rate on a solid mount and a missing one on a flexible mount.
5. For every thermal case, compute the differential axial growth between
   housing and shaft over the span and the preload it leaves, flooring a fully
   relieved preload at zero rather than reporting a negative one.
6. Grade every case against the no-unload floor and, when one is declared,
   the torque-and-life ceiling, absorbing an exact equality at either bound
   with a named tolerance.
7. Where an axial natural frequency was measured, invert it to an installed
   preload and compare it with the value the assembly procedure intended,
   inside the declared measurement tolerance.
8. Report the required and applied preload, the path stiffness, every thermal
   case with the cases that bound it, the measured preload and the findings.

## Pitfalls

- Carrying a solid-mount separation factor into a flexible design. The spring
  is there to hold preload through thermal excursions, not to share external
  load, and reusing 2.8 under-sizes a flexible preload by a factor of nearly
  three.
- Sizing the preload on the operating load and checking launch afterwards. The
  worst-case axial reaction is usually a launch event, and a preload that
  survives operation can be lifted clean off during the environment it was
  meant to be preloaded against.
- Assuming preload scales stiffness linearly. Doubling preload raises
  stiffness by only about a quarter, so a frequency shift that looks small can
  correspond to a large preload error, and a preload inferred from a frequency
  has to be inverted through the cube, not scaled.
- Checking only the cold case. Thermal shift is signed: the case that relieves
  preload threatens unloading, and the opposite case threatens running torque
  and bearing life. Both ends are part of the same verification.
- Recording the torque applied to the lock nut as the preload. The applied
  preload is what the stack actually carries after settling; a measurement is
  what re-verifies it, and a procedure is not a measurement.
- Relaxing the no-unload floor to absorb an equality at the limit. The
  representation error belongs in the tolerance inside the comparison; the
  floor stays as computed.

## Behavior contract (gate 3)

The separation-factor selection, preload sizing, one-third power-law stiffness
and its inversion from a measured frequency, preload-path construction,
differential thermal growth and the two-sided floor and ceiling grading are
exercised by the gate 3 contract test:
scripts/test_e3301_bearing_preloading.py against
scripts/e3301_bearing_preloading_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3301_bearing_preloading.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
