---
name: q7045-compression-and-shear-testing
description: "Determine whether a compression or shear run can deliver the metallic property it was asked for, and whether the specimen let it. Use when the methods clause of ECSS-Q-ST-70-45 is applied beyond tension: map the required property onto the arrangement that measures it, reject one no arrangement covers, check a compression specimen against the short-column length-to-diameter band, compare its peak stress with the Euler stress of that slenderness so a buckled strut is never reported as strength, and divide a shear load by every plane that carried it. Trigger: ecss, q-st-70-45, compression-specimen-slenderness-band, compression-euler-buckling-utilisation, double-shear-plane-area, single-shear-coupon-strength, compression-shear-method-applicability."
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
  tags: [ecss, q-st-70-45-mechanical-testing-scope, q7045-compression-and-shear-testing, compression-specimen-slenderness-band, compression-euler-buckling-utilisation, double-shear-plane-area, single-shear-coupon-strength, compression-shear-method-applicability]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanical Testing of Metals -- Compression and Shear (space-systems/ecss/q7045-compression-and-shear-testing)

Use when the methods clause of ECSS-Q-ST-70-45 is being applied to something
other than a tension test: a property has been requested, a compression or
shear arrangement has been proposed or already run, and the question is
whether that arrangement can deliver the property and whether the specimen
that was used lets the recorded load mean what the report says it means.

## Domain quick reference

- Applicability comes before arithmetic. A pin shear rig does not produce a
  shear modulus and a lap coupon does not produce a compressive yield; a
  number computed from the wrong arrangement is wrong before the first
  division.
- A compression specimen is a short column. Outside the short-specimen
  length-to-diameter band the peak load is the buckling load of a strut, and
  the load trace of a buckling strut and a yielding cylinder look alike.
- Buckling is a matter of degree. A peak stress that reaches half the Euler
  stress of its own slenderness is already contaminated, long before the
  specimen visibly bows.
- Shear strength depends on the number of planes. A double-shear pin presents
  two areas, and dividing by one of them reports twice the strength the
  material has.
- A contaminated run is still a run. It is reported with its finding, not
  quietly corrected into a strength it never measured, because the correction
  would need a buckling analysis the test did not perform.

## Workflow

1. Map the required property onto the arrangement that measures it, and stop
   with a finding when no arrangement in the set can deliver it.
2. Compare the arrangement that was actually used with that mapping, and
   report the mismatch rather than reducing the run anyway.
3. For compression, compute the length-to-diameter ratio and test it against
   the short-specimen band with an inclusive comparison at the edges.
4. Compute the slenderness from the radius of gyration of the section, the
   Euler stress at that slenderness and the declared end fixity, and express
   the recorded peak as a fraction of it.
5. For shear, resolve the arrangement to its plane count, build the total
   area from every plane, and reconcile it with the plane count the operator
   declared.
6. Report the strength beside the findings, so a buckling-limited or
   wrong-arrangement result is visible next to the number it produced.

## Pitfalls

- Dividing a double-shear load by one plane area. The answer is twice the
  real strength and it is the conservative-looking direction that hides it.
- Reducing the run before checking applicability. A clean division of a
  correct load by a correct area still returns a property the arrangement
  cannot measure.
- Judging buckling by eye. A specimen that never visibly bowed can still have
  had half its peak set by column behaviour.
- Ignoring end fixity. The same specimen in fixed ends carries four times the
  Euler stress, so a fixity assumption silently moves the verdict.
- Treating a length-to-diameter ratio that lands exactly on the band edge as
  out of band. Representation of the edge failed, not the specimen.

## Behavior contract (gate 3)

The property-to-arrangement mapping, slenderness and radius of gyration, the
Euler stress with end fixity, the buckling utilisation finding, single and
double shear plane areas and strengths, the declared plane-count
reconciliation and the delivered-property verdict are exercised by the gate 3
contract test: scripts/test_q7045_compression_and_shear_testing.py against
scripts/q7045_compression_and_shear_testing_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q7045_compression_and_shear_testing.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
