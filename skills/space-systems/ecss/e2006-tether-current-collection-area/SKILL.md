---
name: e2006-tether-current-collection-area
description: "Use when size the plasma-contacting surface a tether needs to carry its operating current, per ECSS-E-ST-20-06C clause 10.2.2: compute the ambient random-flux current-density from electron-density and electron-temperature, apply the orbital-motion-limited enhancement for the collector geometry — sphere, cylinder or flat-tape — at its applied bias-potential, invert that into the collecting-area the intended application demands with its sizing margin, confirm the area on record covers it, then confirm the resulting surface-current-density stays inside the collector's erosion and thermal rating and inside the thin-sheath validity of the closed form. Trigger: ecss, e-st-20-electrical-scope, e2006-tether-current-collection-area, electrodynamic-tether, current-collection, orbital-motion-limited, plasma-contactor, collecting-area-sizing, debye-length."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-tether-current-collection-area, electrodynamic-tether, current-collection, orbital-motion-limited, plasma-contactor, collecting-area-sizing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Design — Tether Collecting-Surface Sizing (space-systems/ecss/e2006-tether-current-collection-area)

Use when the task is the sizing requirement of ECSS-E-ST-20-06C clause
10.2.2 — demonstrating that the surface a tether presents to the
ambient plasma is large enough to exchange the current the intended
application actually operates at, and that it survives doing so.

## Domain quick reference

- A surface sitting at the ambient plasma potential collects the random
  flux of the electron population: the elementary charge times the
  electron density times the mean one-sided flux speed of a maxwellian
  at the electron temperature. In a typical low orbit that is under a
  milliampere per square metre, which is why an unbiased surface can
  never carry an electrodynamic duty.
- Bias is what makes the surface useful, and the geometry decides how
  much it buys. In the orbital-motion-limited regime a sphere collects
  in proportion to the bias energy measured in units of the electron
  temperature; a cylinder collects as the square root of it, scaled by
  a geometric factor; a broad flat surface gains essentially nothing,
  because its sheath expands over an area it already captured. At a
  few hundred volts over a tenth-of-an-electronvolt plasma the sphere
  is two orders of magnitude ahead of the cylinder, and that single
  choice dominates the area that comes out.
- The closed form only holds while the sheath is thin compared with the
  collector, which in practice means the collector's characteristic
  radius stays at or below the electron Debye length of the ambient
  plasma. Past that the sheath geometry, not orbital motion, limits the
  collection and the closed form overstates what the surface draws —
  an optimistic error, so it must be checked rather than assumed.
- Sizing is not the same as capability. The area has to cover the
  operating current with the required margin, and separately the
  current density that the operating current puts on that area has to
  stay inside the erosion and thermal rating of the collector material.
  A surface can be large enough on the sizing check and still be
  disqualified by the second one when the duty is concentrated.
- The plasma condition is an input, not a constant. Density and
  temperature swing by more than an order of magnitude between day and
  night, solar minimum and maximum, and the sizing case is the worst
  credible operating condition, not the mean.

## Workflow

1. Collect the inputs: operating current, the collecting area on
   record, ambient electron density and temperature for the sizing
   case, applied bias, collector geometry, the material current-density
   rating, and the collector's characteristic radius. Reject a
   non-positive density, temperature, current or area, and reject a
   negative bias rather than silently treating it as the ion-collection
   branch, which this procedure does not cover.
2. Compute the random-flux current density from density and
   temperature.
3. Apply the orbital-motion-limited enhancement for the declared
   geometry at the applied bias to get the effective current density
   the biased surface actually draws.
4. Divide the operating current by that effective density to get the
   bare collecting area, then multiply by the required sizing margin to
   get the area the design has to show.
5. Compare the area on record against the sized area. Treat an
   exact-boundary case as compliant by absorbing the representation
   error in the comparison, never by reducing the margin.
6. Separately confirm the area on record actually draws at least the
   operating current — that check catches a sizing case that was built
   on a different plasma condition from the one supplied.
7. Divide the operating current by the area on record and compare
   against the material current-density rating.
8. Compare the collector's characteristic radius against the ambient
   Debye length and flag a collector that has left the thin-sheath
   regime the enhancement law assumes.
9. Report the configuration as compliant only when the area, the
   delivered current, the material rating and the sheath validity all
   hold.

## Pitfalls

- Sizing on the random flux alone and concluding a tether cannot work,
  or sizing on the enhancement alone and forgetting the flux the
  enhancement multiplies. Both halves are needed and neither is the
  answer.
- Carrying a sphere's enhancement law across to a cylindrical or tape
  collector. The exponent is different, and the resulting area is wrong
  by a factor that grows with bias — in the reference low-orbit case,
  by a factor near forty.
- Applying the closed form to a collector far larger than the Debye
  length. The law was derived for the thin-sheath regime; outside it
  the result is optimistic, which is the dangerous direction.
- Reading a passed sizing check as a passed design. The same area that
  satisfies the sizing margin can exceed the material's current-density
  rating, and the two checks fail independently.
- Sizing on mean plasma conditions. The requirement is to carry the
  operating current in the worst credible condition of the intended
  application, and the night-side density is the case that sets it.
- Relaxing the sizing margin to make an exact-boundary area pass. The
  boundary case is an arithmetic artefact; absorb it in the comparison
  and leave the margin where the design set it.

## Behavior contract (gate 3)

The random-flux, enhancement, area-inversion, margin, material-rating
and thin-sheath logic is exercised by the gate 3 contract test:
scripts/test_e2006_tether_current_collection_area.py against
scripts/e2006_tether_current_collection_area_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_tether_current_collection_area.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
