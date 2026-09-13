---
name: e2008-interconnector-pull-test-purpose
description: "Assess whether an interconnector pull-test campaign does what ECSS-E-ST-20-08C clause 6.4.3.10.1 asks of it: monitor the bond strength of the interconnector-to-cell joints under a rising load, then confirm the surviving circuit is still electrically stable. Use when such a campaign on a photovoltaic assembly coupon is scoped or its results are graded: derive the strength floor from the handling and deployment load with its factor, form the mean, spread and one-sided lower tolerance bound of the measured pull forces, grade every tab and the population bound against that floor, compare pre-test and post-test circuit resistance against the drift allowance, and name the weakest joint with a campaign verdict. Trigger: ecss, e-st-20-08c, clause-6-4-3-10-1, interconnector-pull-test-purpose, interconnector-bond-strength-monitoring, interconnector-population-lower-bound, post-pull-electrical-stability, solar-cell-interconnector-joint-strength."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e-st-20-08c, e2008-interconnector-pull-test-purpose, interconnector-bond-strength-monitoring, interconnector-population-lower-bound, post-pull-electrical-stability, solar-cell-interconnector-joint-strength]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies — Interconnector Pull Test Purpose (space-systems/ecss/e2008-interconnector-pull-test-purpose)

Use when the task is the purpose rule of ECSS-E-ST-20-08C clause 6.4.3.10.1 —
showing that a pull test on the interconnectors of a photovoltaic assembly
actually monitors the strength of the bonds while a load is applied to them and
confirms that what survives is still electrically stable, rather than returning
a list of forces nobody compares with anything.

## Domain quick reference

- The interconnector is the thin metal tab that carries a cell's current to its
  neighbour and absorbs the differential expansion between them. Its bonds are
  the weakest mechanical link on the assembly, so their strength is the quantity
  the test exists to watch.
- The strength floor is derived, never chosen. It comes from the load the joint
  sees in handling, stacking, launch and deployment, multiplied by the factor
  applied to that load; a floor taken from a supplier data sheet describes the
  process, not the application.
- A sample does not speak for the population. The mean and the sample spread
  together give a one-sided lower tolerance bound, and it is that bound, not the
  mean, that states what the untested joints are good for. A sample of three has
  a factor above seven precisely because three pulls say so little.
- A tab is destroyed by the pull that measures it, so the pulled population and
  the delivered population are disjoint by construction. That is why the sample
  size is part of the purpose: too few pulls and the bound collapses below the
  floor however strong each individual joint read.
- Electrical stability is a separate finding from strength. Neighbouring joints
  take the reaction load of the pull, and a joint that is cracked but still
  touching passes a continuity check while reading high; the pre-test and
  post-test resistance of the monitored circuit is the measurement that catches
  it.

## Workflow

1. Derive the strength floor from the declared handling and deployment load and
   the factor applied to it. Reject a factor below unity: an unfactored load is
   not a qualification floor.
2. Grade every pulled tab against the floor, treating a force sitting exactly on
   it as compliant — the tolerance belongs on the comparison, never on the
   floor — and reject a tab identifier that appears twice, since two records for
   one joint make the population ambiguous.
3. Form the sample statistics: count, mean, sample standard deviation with the
   n-1 divisor, and the weakest pull.
4. Take the one-sided lower tolerance factor for that sample size, using the
   next smaller tabulated size when the count falls between entries so the
   factor is the conservative one, and form the population lower bound.
5. Compare the bound with the same floor. A sample whose every member clears the
   floor but whose bound does not is a wide-spread process, and it is reported
   as a shortfall rather than passed on its minimum.
6. Check the sample size against the campaign minimum separately, so a small
   sample is visible as a small sample and not only as a wide bound.
7. Compare pre-test and post-test resistance on every monitored circuit against
   the drift allowance, in both directions, and report the derived floor, the
   statistics, the weakest joint, every finding and the verdict.

## Pitfalls

- Reporting the sample mean as the demonstrated strength. The delivered joints
  were never pulled; only the lower tolerance bound says anything about them,
  and mean-versus-floor hides exactly the wide-spread process the test is there
  to find.
- Taking the strength floor from the interconnector supplier. The floor is a
  property of the loads this assembly sees, so a generic bond-strength figure
  can sit either side of the real requirement without anyone noticing.
- Pulling three tabs and calling the lot qualified. The tolerance factor grows
  sharply as the sample shrinks, so a three-pull sample needs an enormous margin
  before it demonstrates anything about the untested joints.
- Skipping the post-test resistance because nothing came off in the pull. The
  reaction load lands on the neighbouring joints; a cracked joint still in
  contact reads as continuous and only shows up as resistance drift.
- Watching resistance rise and ignoring a fall. A large drop is as much a sign
  that the circuit moved as a rise is, so the allowance is applied to the
  magnitude of the drift.
- Averaging a weak tab away. One joint below the floor is a finding on its own
  terms; the population statistics are computed alongside it, never instead
  of it.

## Behavior contract (gate 3)

The strength-floor derivation, per-tab grading, sample statistics, tolerance
factor and population lower bound, sample-size check and the resistance-drift
stability check are exercised by the gate 3 contract test:
scripts/test_e2008_interconnector_pull_test_purpose.py against
scripts/e2008_interconnector_pull_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_interconnector_pull_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
