---
name: e2008-humidity-test-sample
description: "Use when verify that the specimen offered for a photovoltaic assembly humidity test is built from flight-equivalent materials by qualified processes under ECSS-E-ST-20-08C clause 5.5.1.4.3: walk the specimen stack-up against the flight stack-up layer by layer, record omitted, added, substituted, out-of-sequence and out-of-thickness layers, credit only approved material equivalents, reduce the walk to a representativeness fraction, check every specimen process held a valid qualification on the build date, and check the specimen population reaches its agreed floor. Refuses a malformed stack-up or qualification window. Trigger: ecss, e-st-20-08c, photovoltaic-humidity-test-specimen, flight-equivalent-materials, qualified-process-window, coupon-representativeness, solar-panel-stackup-comparison, encapsulant-thickness-band."
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
  tags: [ecss, e-st-20-08-photovoltaic-scope, e2008-humidity-test-sample, photovoltaic-humidity-test-specimen, flight-equivalent-materials, qualified-process-window, coupon-representativeness, solar-panel-stackup-comparison]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Humidity Test — Test Sample (space-systems/ecss/e2008-humidity-test-sample)

Use when the task is the specimen step of the humidity test of
ECSS-E-ST-20-08C clause 5.5.1.4.3 — deciding whether the coupon about to enter
the humidity chamber is close enough to the flight photovoltaic assembly, in
materials and in the processes that laid them down, for its result to stand in
for the flight build.

## Domain quick reference

- A photovoltaic assembly is a bonded stack, not a part: coverglass,
  coverglass adhesive, cell, interconnect and substrate bond line. Humidity
  attacks the stack through its organic layers, so the specimen has to
  reproduce the stack in order, in material and in thickness — a coupon with
  the right cell and the wrong adhesive tests almost nothing.
- Thickness is a first-order term, not a dimension to be nominally matched.
  Moisture diffusion time through an encapsulant or an adhesive scales with the
  path through it, so a bond line laid thicker than flight buys the specimen
  time the flight article does not have. The band is relative to the flight
  value and is agreed before the build.
- Material equivalence is granted, never inferred. A different lot of the same
  qualified specification can be an approved equivalent; a different
  specification that merely looks similar is a substitution and a deviation.
  An approved equivalent is still recorded, so the result carries its own
  caveat forward.
- A process qualification is a window in time, not a badge. A process whose
  qualification had lapsed on the build date, or had not yet opened, leaves the
  specimen outside the qualified build even when the material list is perfect.
- One coupon has no spread. Humidity results scatter with bond-line quality and
  edge sealing, so the specimen population has an agreed floor and a count
  below it is a finding in its own right.

## Workflow

1. Validate both stack-ups: ordered, uniquely named layers, each with a
   material specification, a positive thickness and the process that lays it.
   A missing field is an input error, not an implied default.
2. Normalize the approved-equivalent table so every flight specification maps
   to the set of specifications that may stand in for it.
3. Walk the flight stack-up. For each layer find its specimen counterpart and
   record a deviation when it is absent, built at a different position, built
   from an unapproved specification, or laid outside the agreed thickness band.
   Credit an approved equivalent as representative and record the substitution.
4. Sweep the specimen for layers the flight build does not carry and record
   each as an added layer.
5. Reduce the walk to the representativeness fraction — flight layers
   reproduced over flight layers — and compare it with the required value,
   absorbing floating-point representation error with a named tolerance.
6. Take every distinct process in the specimen and check it carries a
   qualification whose window contains the build date.
7. Report the deviations, the approved substitutions, the process findings, the
   specimen count against its floor, and a single verdict.

## Pitfalls

- Matching layers by position alone. A specimen that omits one layer shifts
  everything below it, turning one real deviation into a cascade; layers are
  matched by name and the position is then a deviation of its own.
- Accepting a thicker bond line as conservative. A thicker organic layer slows
  moisture ingress, so an over-thick specimen is optimistic, not conservative,
  and is refused by the same band as an under-thick one.
- Treating a lot change as a material change, or a specification change as a
  lot change. The approved-equivalent table decides, and anything outside it is
  a deviation regardless of how similar the datasheet looks.
- Checking that a process appears on the qualified list without checking the
  date. A lapsed qualification is the common finding on a long build campaign
  and is invisible to a membership test.
- Reading a high representativeness fraction as a pass. The fraction is a
  summary; a single unapproved substitution in the encapsulant still fails the
  specimen, so the deviation list governs and the fraction only adds a finding.
- Running a single coupon because schedule is tight. The population floor is
  part of the sample definition, not a statistical nicety.

## Behavior contract (gate 3)

The layer and stack-up validation, equivalent-table normalization, thickness
band, stack-up walk, representativeness fraction, process-qualification window
and specimen-count floor are exercised by the gate 3 contract test:
scripts/test_e2008_humidity_test_sample.py against
scripts/e2008_humidity_test_sample_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_humidity_test_sample.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
