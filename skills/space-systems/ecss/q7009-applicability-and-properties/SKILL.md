---
name: q7009-applicability-and-properties
description: "Determine whether a thermal-control surface sits inside the applicability envelope of the ECSS-Q-ST-70-09C thermo-optical property measurements, and which of solar absorptance and infrared emittance that surface can actually yield. Use when a specimen set mixes diffuse coatings, specular metallized finishes, semi-transparent films and textured surfaces, and the campaign owes a defensible scope statement before a port is opened. Screens opacity against the transmittance floor, checks the specimen overfills the measurement port and spans enough pattern periods across it, and refuses a reflectance-only absorptance on a transmitting film. Trigger: ecss, q-st-70-09, thermo-optical-property-applicability, solar-absorptance-scope, infrared-emittance-scope, semi-transparent-film-opacity-floor, measurement-port-overfill, patterned-surface-representativeness."
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
  tags: [ecss, q-st-70-thermo-optical-scope, q7009-applicability-and-properties, thermo-optical-property-applicability, solar-absorptance-scope, infrared-emittance-scope, semi-transparent-film-opacity-floor, measurement-port-overfill]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermo-Optical Measurement — Applicability and Properties (space-systems/ecss/q7009-applicability-and-properties)

Use when the task is the framework step of ECSS-Q-ST-70-09C — deciding
which surfaces the thermo-optical property measurements cover, which of
solar absorptance and infrared emittance each surface can yield, and
under what method constraints, before any specimen reaches an
instrument.

## Domain quick reference

- The two properties are a pair, not one measurement. Solar absorptance
  is weighted over the solar spectrum; infrared emittance is weighted
  over the thermal emission of the surface at its own temperature. A
  surface can be perfectly measurable for one and not the other, so the
  scope statement names properties, not specimens.
- Every method closes an energy balance. For an opaque surface that
  balance is absorptance equals one minus reflectance, and reflectance
  alone is enough. Once a surface transmits above the instrument's
  stray-light floor the transmitted term is real, and a reflectance-only
  absorptance is short by exactly that term.
- A transmitting film with nothing behind it is not a measurable
  article. What the instrument sees is the film plus whatever the
  background happens to be, so the film must be reported on its declared
  substrate and the pair named as the measured article.
- The specimen has to overfill the measurement port. A specimen smaller
  than the port puts the port surround inside the field of view, and the
  reading is an area-weighted average of the specimen and the
  instrument.
- A textured or patterned surface has a length scale. Reading it over a
  couple of pattern periods reports one cell; the port has to span
  enough periods for the average to be the surface, and the port
  position relative to the pattern is part of the record.
- Surface families differ in what the instrument can collect. A
  specular finish puts nearly all its reflected energy in one direction,
  so a trap left open removes most of the signal. A flown, contaminated
  surface is reported as received, because cleaning it measures the
  cleaning.

## Workflow

1. Validate each specimen record: identifier, surface family,
   transmittance, specimen and port extents, and pattern pitch where the
   surface is textured. A family outside the covered set, a
   transmittance outside the unit interval or a non-positive dimension
   is an input error, not a value to clamp.
2. Screen opacity: a transmittance at or under the floor is opaque, and
   anything above it transmits. Compare the measured state against the
   declared family and report a disagreement rather than trusting the
   declaration.
3. Compute the port overfill ratio and compare it with the required
   margin, absorbing representation error at the boundary with a named
   tolerance.
4. For a textured surface, compute how many pattern periods the port
   spans and require the minimum before the reading counts as
   representative.
5. Decide the obtainable properties: both for an opaque surface and for
   a transmitting film on its declared substrate, neither for a free
   transmitting film.
6. Separate blocking findings from method constraints. A constraint
   tells the operator how to measure; a finding says the specimen is not
   yet inside the envelope.
7. Roll the specimen set up: counts per property, duplicate identifiers,
   and a campaign scope statement that is clean only when every specimen
   is.

## Pitfalls

- Treating a low transmittance as zero. A film transmitting a few
  percent is well above the stray-light floor, and dropping the term
  biases every absorptance in the campaign the same way, so the error
  hides inside a consistent-looking data set.
- Measuring a free film and reporting the film. The substrate behind it
  is part of the measured article; changing the backing changes the
  answer without changing the specimen.
- Letting a specimen sit inside the port. The reading is then a mixture
  of the specimen and the port surround, and it moves whenever the
  specimen is repositioned — which reads as poor repeatability rather
  than as a geometry error.
- Averaging a patterned surface over one or two periods. The result
  depends on where the port landed, and a re-measurement at a different
  position disagrees with it for reasons the data set cannot show.
- Opening the specular trap for a mirrored finish. Most of the reflected
  energy leaves in the specular direction, so the collected signal
  reports a dark surface that does not exist.
- Cleaning a returned, contaminated specimen before measuring. The
  purpose of the measurement is the surface that flew, and the cleaning
  step is the one thing guaranteed not to be representative of it.

## Behavior contract (gate 3)

The specimen validation, opacity screening, port-overfill and
pattern-period geometry, energy-balance absorptance and the
property-availability decision are exercised by the gate 3 contract
test: scripts/test_q7009_applicability_and_properties.py against
scripts/q7009_applicability_and_properties_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7009_applicability_and_properties.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
