---
name: e2008-thermal-cycling-qualification-coupon
description: "Record and check the definition of the coupon a solar-array thermal-cycling run is performed on, anchored at ECSS-E-ST-20-08C clause 5.5.1.3.3. Use when the task is establishing or reviewing that definition: build the coupon register, require every feature family the assembly needs - cell, interconnect, coverglass, adhesive, substrate and wiring termination - to be declared, resolve each entry to a drawing reference or a definition-matrix cell and refuse a free-text note that is neither, group the register by the medium it was recorded in, measure the coverage of the required families, and name every flight feature the coupon leaves out or adds. Trigger: ecss, e-st-20-08c, solar-array-cycling-coupon, coupon-definition-record, coupon-drawing-reference, coupon-definition-matrix, coupon-representativeness-coverage, missing-feature-family."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-thermal-cycling-qualification-coupon, solar-array-cycling-coupon, coupon-definition-record, coupon-drawing-reference, coupon-definition-matrix, coupon-representativeness-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Thermal Cycling Qualification Coupon (space-systems/ecss/e2008-thermal-cycling-qualification-coupon)

Use when the task is the coupon rule of ECSS-E-ST-20-08C clause
5.5.1.3.3 — fixing what the cycled article actually is, feature by
feature, and tying each feature to the drawing or the definition-matrix
cell that specifies it, so a cycling result can be attributed to a
build rather than to a bench sample nobody can reconstruct.

## Domain quick reference

- The coupon is the article the endurance evidence attaches to. Every
  conclusion drawn from the run is a conclusion about the build that was
  cycled, so a feature left undefined is a feature the result says
  nothing about, however many cycles the coupon survived.
- Six families have to be declared for a photovoltaic assembly: the
  cell, the interconnect, the coverglass, the adhesive, the substrate
  and the wiring termination. They are the load path of the thermal
  strain and they fail differently, so an incomplete register is not a
  tidier record, it is a narrower qualification.
- Two record media are allowed and they are equivalent: a drawing
  reference, or a cell of a definition matrix that fixes the variant
  chosen for the coupon. What is not allowed is a free-text note; a
  description written into the test report cannot be reissued, revised
  or checked against the flight build.
- Representativeness runs in both directions. A flight feature with no
  counterpart on the coupon is unqualified. A coupon feature the flight
  assembly does not carry — a handling tab, an instrumentation lead, a
  stiffener added to survive the fixture — changes the stiffness and the
  strain the joints see, so it makes the coupon a different article, not
  a conservative one.
- The coverage of the required families is a number, and a programme
  that accepts a partial coupon states the minimum it accepts in
  advance. A coverage landing exactly on that minimum is accepted; the
  tolerance sits on the comparison, not on the minimum.

## Workflow

1. Normalise every declared feature name so that spacing, case and
   separators cannot make one family look like two, and refuse a blank
   or non-textual name.
2. Resolve the reference of each entry: a matrix cell first, then a
   drawing reference. Anything else is refused outright rather than
   recorded as an unresolved note.
3. Build the register, refusing a family declared twice — a second entry
   for the same family means two builds are being described, and the
   cycling applies to one.
4. Compare the register with the required families and name the ones
   missing; carry each as its own finding, so a report shows what is
   unqualified rather than a single count.
5. Measure the coverage of the required families and compare it with the
   declared minimum, absorbing representation error at the boundary.
6. When the flight feature set is declared, name every flight feature
   without a counterpart on the coupon and every coupon feature the
   flight assembly does not carry.
7. Report the register, the grouping by record medium, the coverage and
   every finding. The coupon is defined only when the finding list is
   empty.

## Pitfalls

- Recording the coupon in prose in the test report. Prose is not a
  configuration record: it carries no revision, it cannot be compared
  with the flight drawing set, and the sample it describes cannot be
  rebuilt when the result is challenged years later.
- Declaring only the families that failed, or only the ones that
  interest the analyst. The register fixes the whole article, and the
  unremarkable families are exactly the ones a later investigation needs
  in order to rule them out.
- Treating an extra feature on the coupon as harmless. Tabs, fixture
  stiffeners and instrumentation leads change the strain the joints see;
  the coupon then endures a different load than the flight assembly, in
  either direction.
- Letting a family be declared twice with different references. Two
  entries describe two builds, and the run qualifies neither until the
  variant that was actually cycled is identified.
- Accepting a partial coupon without stating the minimum coverage
  first. A minimum chosen after the register is built is a minimum
  chosen to pass, and the families left out stay unqualified either way.
- Relaxing the minimum to absorb a boundary case. A coverage exactly on
  the minimum is accepted already, by the tolerance inside the
  comparison.

## Behavior contract (gate 3)

The feature normalisation, drawing and definition-matrix reference
resolution, register construction, required-family coverage and the
two-way flight comparison are exercised by the gate 3 contract test:
scripts/test_e2008_thermal_cycling_qualification_coupon.py against
scripts/e2008_thermal_cycling_qualification_coupon_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_thermal_cycling_qualification_coupon.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
