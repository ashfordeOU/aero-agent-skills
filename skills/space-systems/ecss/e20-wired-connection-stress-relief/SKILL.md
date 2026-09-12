---
name: e20-wired-connection-stress-relief
description: "Use when verify that a wired connection on space electrical hardware carries the strain-relief provisions of ECSS-E-ST-20C clause 4.2.5: categorize the relief fitted as restraining (clamp, backshell relief, tie to a support, potted transition) or non-restraining, compute the quasi-static inertial load the unsupported harness span imposes on the wire, compare it against the conductor tensile and termination pull-out allowables at the required margin, derive the clamp spacing that load permits, check the relief does not force the bundle inside its minimum bend radius, and flag a soldered joint left as the primary load path. Trigger: ecss, e-st-20-electrical-scope, wired-connection-stress-relief, harness-strain-relief, conductor-tensile-load, termination-pull-out-load, unsupported-span-limit, minimum-bend-radius, soldered-joint-load-path."
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
  tags: [ecss, e-st-20-electrical-scope, e20-wired-connection-stress-relief, harness-strain-relief, conductor-tensile-load, termination-pull-out-load, unsupported-span-limit, minimum-bend-radius]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Wired Connection Stress Relief (space-systems/ecss/e20-wired-connection-stress-relief)

Use when the task is the strain-relief review of ECSS-E-ST-20C clause
4.2.5 -- checking that a wired connection is restrained so the wire and
its termination are not left carrying the mechanical load of the
harness, that the load actually applied sits inside the conductor and
termination allowables at the required margin, and that the relief
hardware itself does not damage the bundle it holds.

## Domain quick reference

- Clause 4.2.5 is about where the load goes, not only about how much
  of it there is. Relief provisions split into two families.
  Restraining: a clamp or saddle onto structure, a connector backshell
  relief, a lacing tie to a defined support, a potted transition, a
  bonded service loop -- each reacts the harness inertial load into
  structure upstream of the wire. Non-restraining: nothing fitted, an
  adhesive dot, a free-hanging loop, sleeving over the wire -- these
  appear on a drawing as a provision and react no load at all.
- The load is the quasi-static inertial load of the harness mass
  between restraint points: segment mass x design acceleration x
  standard gravity x design safety factor. Segment mass follows from
  the unsupported span and the harness mass per metre, so the same
  expression inverts into the clamp spacing a given allowable permits
  -- the maximum unsupported span is the allowable divided by the load
  per metre. That inversion is the design output; the margin alone is
  only the verdict.
- There are two allowables, not one. The conductor's tensile allowable
  is its cross-sectional area times its allowable stress. The
  termination's pull-out allowable is a fraction of that: a crimped
  contact or a resistance weld retains most of the conductor's
  capability, while a solder cup, solder lug or wire wrap retains far
  less. The governing allowable is the smaller of the two, which for a
  soldered termination is essentially always the joint.
- A soldered joint is not a primary structural element. A connection
  carrying more than a de-minimis mechanical load with no restraining
  provision is a finding on its own; when that connection is soldered,
  the joint in the load path is a second, separate finding, and a
  positive computed margin does not retire it.
- Relief has a geometric failure mode too. A clamp or backshell that
  holds the bundle below its minimum bend radius -- a multiple of the
  bundle outer diameter -- damages insulation and conductors while
  scoring perfectly on every load check.

## Workflow

1. For each wired connection record the relief provision fitted, the
   termination type, the conductor area and allowable stress, the
   unsupported span and harness mass per metre, the design acceleration
   and safety factor, the required margin, and the bend radius and
   bundle outer diameter at the relief. Reject an unrecognized
   provision or termination type before it enters the review.
2. Categorize the provision as restraining or non-restraining, and
   compute the applied quasi-static load from the span, mass per metre,
   acceleration and safety factor.
3. Derive the conductor tensile allowable and the termination pull-out
   allowable, then take the margin of each over the applied load
   against the required margin. Report each shortfall separately -- a
   sound conductor on an overloaded termination is a termination
   finding, not a wire finding.
4. Invert the load expression on the governing allowable to get the
   maximum unsupported span, and flag a span longer than it; that
   number is the clamp spacing the design owes.
5. Check the bend radius at the relief against the minimum multiple of
   the bundle outer diameter and flag a relief that forces the bundle
   tighter.
6. Flag any connection above the de-minimis load with a non-restraining
   provision, and flag the joint separately when that connection is
   soldered. Aggregate the four groups: the connection is not
   relief-compliant until all of them are empty.

## Pitfalls

- Treating a positive strength margin as closing the clause. Clause
  4.2.5 asks for a relief provision; a wire that survives the load
  while being the load path is still an unrelieved connection, and the
  margin is the wrong instrument for that question.
- Crediting sleeving, an adhesive dot or a free-hanging service loop as
  strain relief because the drawing carries a note in that column --
  none of them reacts load into structure.
- Grading a soldered termination against the conductor allowable. The
  joint retains a fraction of the conductor's capability, so the
  governing allowable is the smaller one and using the conductor's
  number overstates capability by roughly a factor of three.
- Reporting a span exceedance without the permissible span. The load
  expression inverts exactly, so the required clamp spacing is
  computable and belongs in the finding.
- Omitting the bend-radius check because the load numbers are
  comfortable -- an over-tight clamp is a relief provision that damages
  the very connection it protects, and no load margin reveals it.
- Applying a safety factor below unity, which relieves the design
  instead of covering it; the factor is rejected at input, not quietly
  absorbed into the margin.

## Behavior contract (gate 3)

The provision categorization, inertial-load accounting, conductor and
termination allowable derivation, margin, maximum-span inversion,
bend-radius, load-path and aggregated review logic is exercised by the
gate 3 contract test:
scripts/test_e20_wired_connection_stress_relief.py against
scripts/e20_wired_connection_stress_relief_logic.py (stdlib unittest,
offline). Run:
`python3 scripts/test_e20_wired_connection_stress_relief.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
