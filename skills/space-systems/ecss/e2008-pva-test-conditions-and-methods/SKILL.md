---
name: e2008-pva-test-conditions-and-methods
description: "Verify that each test declared for a photovoltaic assembly is governed by its source control drawing the way clause 5.2 of ECSS-E-ST-20-08C requires: check the cited document actually carries the authority of the drawing, decide whether the method is drawing-named, drawing-invoked or an equivalent standing on an approved deviation, convert a measured irradiance into a fraction of the reference spectrum before any band is applied, measure how much of each declared tolerance band the condition consumes, and name the mandatory condition the test never declared at all. Use when a PVA test matrix, acceptance procedure or laboratory report has to be shown traceable to the drawing. Trigger: ecss, e-st-20-08c, pva-test-condition-governance, source-control-drawing-test-method, pva-test-tolerance-band, am0-illumination-condition, pva-method-deviation-approval, pva-test-matrix-governance."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-test-conditions-and-methods, e-st-20-08c, pva-test-condition-governance, source-control-drawing-test-method, pva-test-tolerance-band, am0-illumination-condition, pva-method-deviation-approval, pva-test-matrix-governance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Test Conditions and Methods (space-systems/ecss/e2008-pva-test-conditions-and-methods)

Use when the task is clause 5.2 of ECSS-E-ST-20-08C: the tests run on a
photovoltaic assembly and the conditions they are run at are set by the
source control drawing, not by the laboratory. This leaf grades a
declared test matrix against that drawing and says, test by test, what
would stop a result standing as evidence.

## Domain quick reference

- Three things have to line up before a result counts: the document the
  test cites has to carry the authority of the drawing, the method has
  to be one the drawing allows, and every declared condition has to sit
  inside the band the drawing sets. A defect in the first outranks
  anything found in the other two, because a test run outside the
  drawing is not a test of the drawing.
- A method is admissible when the drawing names it, when the drawing
  invokes it through a standard, or when an equivalent is substituted
  under an approved deviation. A method described as an approved
  substitution but citing no approval is an input contradiction and is
  rejected rather than downgraded. A supplier-internal method with no
  approval is simply not admissible.
- Conditions are declared as a specified value with a tolerance, and
  the interesting quantity is not the pass flag but the fraction of the
  band consumed. A test sitting at nine tenths of its band is formally
  compliant and practically fragile, and that is what ranks the
  conditions against each other.
- Illumination is the condition most often mis-stated, because the
  drawing specifies it as a fraction of the reference solar spectrum
  while the laboratory records watt per square metre. The measured
  irradiance is converted to the ratio first; comparing raw irradiance
  against a fractional tolerance is a unit error that reads as a
  catastrophic deviation.
- A zero tolerance is legitimate and means the specified value exactly
  -- a cycle count, a sample size. It is handled as an exact match
  rather than a division, which has no meaning at a zero band.
- The mandatory condition set follows the purpose of the test. An
  electrical performance measurement is meaningless without a
  temperature and an illumination condition; a cycling test is
  meaningless without a temperature and a cycle count. An absent
  condition produces no deviation, so the set is checked separately.

## Workflow

1. Take each declared test with its purpose, the document it cites, the
   method it uses and its condition list. Reject a test that declares
   no conditions rather than passing it on an empty set.
2. Decide whether the cited document governs. A drawing or a
   specification the drawing invokes governs; a supplier-internal
   procedure does not, and that verdict is returned before the method
   and the conditions are looked at.
3. Resolve the method. Demand an approval reference from a method
   declared as an approved substitution, and record the substitution as
   a finding so it travels with the result.
4. Evaluate every condition: convert an irradiance into a fraction of
   the reference spectrum, take the signed deviation from the specified
   value, apply the band, and record the fraction of the band consumed
   so the conditions can be ranked.
5. Check the declared condition kinds against the kinds the purpose
   demands and name the ones that are missing.
6. Return one verdict per test in that precedence -- governance,
   method, condition set, condition band -- then roll the matrix up into
   a programme verdict with the ungoverned tests named and the governing
   condition of each test identified.

## Pitfalls

- Grading conditions on a test that was never governed by the drawing.
  Every band can be green on a run whose procedure the customer never
  saw, and reporting that as compliance is the whole failure mode the
  clause exists to prevent.
- Comparing a measured irradiance in watt per square metre against a
  tolerance expressed as a fraction of the reference spectrum. The
  deviation comes out three orders of magnitude wrong, which is at
  least loud; the reverse error, a ratio compared against a watt
  tolerance, passes silently.
- Reading an absent condition as a satisfied one. A cycling test that
  declares no cycle count raises no deviation, so a check that only
  grades declared conditions returns a clean sheet on a test whose
  duration nobody fixed.
- Accepting a method described as an approved equivalent with no
  approval cited. The name asserts the approval exists; without the
  reference the assertion is unverifiable, and treating it as a minor
  finding lets it travel into the report.
- Dividing by a zero tolerance to report band usage. A zero band means
  the specified value exactly, and it is checked as an exact match.
- Judging a deviation that lands exactly on the tolerance by bare
  arithmetic. The deviation is a subtraction of two declared values and
  can miss the bound by a few units in the last place; the comparison
  absorbs that while the drawing tolerance stays as specified.

## Behavior contract (gate 3)

The document governance check, method admissibility, irradiance
conversion, tolerance-band evaluation, mandatory condition-set coverage
and the rolled-up matrix verdict are exercised by the gate 3 contract
test: scripts/test_e2008_pva_test_conditions_and_methods.py against
scripts/e2008_pva_test_conditions_and_methods_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_pva_test_conditions_and_methods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
