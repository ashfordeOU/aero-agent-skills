---
name: e3301-ball-bearings-sizing-hertzian-contact
description: "Size a ball bearing against ECSS-E-ST-33-01C clause 4.7.5.4.6. Use when the peak Hertzian contact stress of a mechanism bearing must be shown inside the allowable for its ring and ball material: forming the ISO 76 basic static load rating from rows, ball count, ball diameter and contact angle, combining the radial and axial limit-load components into a static equivalent load, raising it by the design factor of at least 1.45 before any stress is computed, scaling the peak contact stress off that rating as a cube root of load, and reporting the static safety factor beside the Stribeck ball load. Trigger: ecss, e-st-33-01-mechanisms-scope, ball-bearing-hertzian-contact-stress, iso-76-static-load-rating, bearing-static-equivalent-load, bearing-limit-load-design-factor, stribeck-most-loaded-ball, bearing-ring-material-allowable."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-ball-bearings-sizing-hertzian-contact, ball-bearing-hertzian-contact-stress, iso-76-static-load-rating, bearing-static-equivalent-load, bearing-limit-load-design-factor, stribeck-most-loaded-ball, bearing-ring-material-allowable]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Ball Bearing Sizing to Peak Hertzian Contact Stress (space-systems/ecss/e3301-ball-bearings-sizing-hertzian-contact)

Use when the task is the bearing sizing step of ECSS-E-ST-33-01C clause
4.7.5.4.6 -- deciding whether the ball complement chosen for a
mechanism keeps the peak Hertzian contact stress under the factored
limit load inside what the ring and ball material allows, and what has
to change when it does not.

## Domain quick reference

- The sizing check is a stress check, not a life check. A bearing that
  passes a rolling-contact-fatigue life calculation can still brinell
  its races on a single launch load case, so the peak contact stress
  under the factored limit load is assessed in its own right.
- The limit load is raised by a design factor of at least 1.45 before
  any stress is computed. The factor belongs on the load, not on the
  allowable stress: contact stress grows as the cube root of load, so a
  factor applied to the stress side is roughly three times weaker than
  the same number applied to the load side.
- ISO 76 gives the basic static load rating in the form
  C0 = f0 * i * Z * Dw^2 * cos(alpha), where f0 comes from the bearing
  series rather than from a generic constant, i is the number of rows, Z
  the balls per row, Dw the ball diameter and alpha the nominal contact
  angle. Ball diameter enters squared, so a small ball-size change moves
  the rating far more than one extra ball does.
- ISO 76 defines that rating as the static load producing a fixed
  reference contact stress for the bearing type and material. Because
  Hertzian point-contact pressure grows as the cube root of the ball
  load, the peak stress at any other load follows as
  p0 = sigma_ref * (P0 / C0) ** (1/3). That is the bridge between a
  catalogue rating and the stress the clause is written about.
- The static equivalent load combines the radial and axial components
  with the static factors of the bearing type, and is never taken below
  the radial component alone.
- The allowable is a material property, not a bearing property. A
  corrosion-resistant ring steel carries a lower allowable peak stress
  than a through-hardened bearing steel, and a hybrid ceramic ball
  complement carries a higher one; substituting material without
  redoing the check is how a qualified bearing becomes an unqualified
  one.
- The Stribeck estimate of the most heavily loaded ball is reported
  alongside, because it is the number a detailed contact analysis or a
  test correlation will be built on.

## Workflow

1. Validate the bearing geometry: rows, balls per row, ball diameter and
   nominal contact angle. A contact angle at or beyond ninety degrees, a
   zero ball count or a non-positive ball diameter is an input error.
2. Form the basic static load rating with the static load factor of the
   actual bearing series; do not silently accept the generic default
   when series data exists.
3. Combine the radial and axial limit-load components into the static
   equivalent load, holding it at or above the radial component.
4. Raise the equivalent load by the design factor, refusing any factor
   below 1.45 rather than reporting a non-compliant one.
5. Convert the design equivalent load into a peak Hertzian contact
   stress through the cube-root scaling off the static rating and the
   reference stress of the declared material.
6. Compare that stress with the material allowable, absorbing
   representation error at the boundary with a named tolerance; the cube
   root is not correctly rounded and an exact equality can land either
   side of a strict comparison on a different platform.
7. Report the static safety factor against its requirement and the
   Stribeck most-loaded ball load, with the finding list.

## Pitfalls

- Applying the 1.45 factor to the allowable stress instead of the limit
  load. The cube-root relation makes those two operations very
  different, and the stress-side version is the unconservative one.
- Quoting a catalogue static rating for a bearing whose material has
  been substituted. The rating is tied to a reference contact stress for
  a material; changing the ring steel or going hybrid changes both the
  reference and the allowable.
- Sizing on the static safety factor alone. A comfortable C0/P0 ratio
  still has to be turned into a peak stress and compared with the
  material allowable, which is the check the clause actually asks for.
- Ignoring the contact angle in the rating. It enters through its
  cosine, so an angular-contact bearing sized on the zero-angle form is
  credited with a radial rating it does not have.
- Adding balls to fix a stress exceedance. Ball diameter enters the
  rating squared and the stress as a cube root, so a larger ball is
  usually the shorter path; count changes move the answer slowly.
- Using a strict inequality against the allowable. An exactly-on-limit
  design has to come out compliant on every platform, which means a
  named tolerance inside the comparison rather than a relaxed allowable.

## Behavior contract (gate 3)

The geometry validation, ISO 76 static rating, static equivalent load,
design-factor floor, cube-root peak stress conversion, allowable
comparison, static safety factor and Stribeck ball load are exercised by
the gate 3 contract test:
scripts/test_e3301_ball_bearings_sizing_hertzian_contact.py against
scripts/e3301_ball_bearings_sizing_hertzian_contact_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e3301_ball_bearings_sizing_hertzian_contact.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
