---
name: e2001-multipactor-verification-routes
description: "Use when determine which permitted route proves the multipactor performance of a radio-frequency unit under ECSS-E-ST-20-01C clause 4.5 -- similarity to a qualified unit, analysis-only, analysis-and-test, or test-only: weigh the analysis-method support against the computed and required multipactor-margin, ratchet a critical unit off the analysis-only route, price the demonstration level in watts from the required-margin, check the facility reaches that level, and confirm the discharge-detection set carries two independent methods with one of them observing the gap locally. Trigger: ecss, e-st-20-electrical-scope, e2001-multipactor-verification-routes, multipactor-verification-route, qualification-by-similarity, analysis-only-justification, demonstration-power-level, discharge-detection-methods, analysis-method-validation."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-multipactor-verification-routes, multipactor-verification-route, qualification-by-similarity, analysis-only-justification, demonstration-power-level, discharge-detection-methods]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Verification Routes (space-systems/ecss/e2001-multipactor-verification-routes)

Use when the task is the route choice of ECSS-E-ST-20-01C clause 4.5 --
deciding whether the multipactor performance of a radio-frequency unit is
proven by similarity, by analysis alone, by analysis backed with a campaign,
or by a campaign alone, and what that choice obliges the programme to do.

## Domain quick reference

- Four routes are permitted, and the choice is driven by evidence, not by
  schedule. Similarity re-uses the evidence of an already-qualified unit.
  Analysis-only stands on a validated method and a margin with room to spare.
  Analysis-and-test is the ordinary route: the analysis sizes the gaps and the
  campaign demonstrates them. Test-only is what remains when no validated
  method covers the geometry, or when the analysis does not reach the required
  multipactor-margin.
- Similarity is an all-or-nothing claim. The candidate must be the same design
  within a gap-geometry tolerance, operate within a frequency tolerance, run
  no harder than the reference, carry the same surface treatment and the same
  manufacturing process, and the reference must actually be qualified. One
  broken element ends the claim; there is no partial similarity.
- Analysis-only needs two things at once: a method validated for that geometry
  (a standard chart, a correlated numeric model), and a margin that clears the
  requirement by an agreed extra. A validated method with a bare pass is not
  enough, because the analysis uncertainty is what the extra pays for.
- Criticality is a one-way ratchet. A critical unit is never proven by
  analysis alone, however large the computed margin. The route drops to
  analysis-and-test and stays there.
- A campaign is priced in watts:
  `P_demo = P_nominal * 10 ** (required_margin_db / 10)`. A 6 dB requirement is
  a four-fold level, and this is where a programme discovers its facility
  cannot reach the level -- which is a finding with a corrective route (a
  dedicated article, a subscale demonstration, an alternative argument), not a
  reason to demonstrate less.
- Breakdown has to be observable to count. At least two independent detection
  methods are required and they cannot both be global: port-level observation
  (forward and reverse power nulling, third-harmonic content, phase-null,
  noise rise) says something happened somewhere, while a local observer
  (electron probe, optical emission, close-electron detection) says it
  happened at the gap.

## Workflow

1. Assemble the inputs: analysis-method support (validated method, engineering
   estimate, or none applicable), the computed margin, the required
   multipactor-margin from the equipment type group, the nominal carrier
   power, the criticality of the unit, the facility capability, the planned
   detection methods, and any similarity claim with its candidate and
   reference.
2. Judge the similarity claim first, when there is one: gap-geometry delta,
   frequency delta, power ratio, surface treatment, manufacturing process and
   reference qualification. Name each shortfall; take the similarity route
   only when the list is empty.
3. Otherwise pick the analysis route. No applicable method means test-only. A
   computed margin below the requirement means test-only plus a recorded
   finding -- redesign, or demonstrate what the hardware actually does. An
   engineering estimate means analysis-and-test.
4. With a validated method, take analysis-only when the margin clears the
   requirement plus the agreed extra, and demote to analysis-and-test when the
   unit is critical. Compare margins with a named tolerance so a case exactly
   on the bar passes, and never by relaxing the bar itself.
5. Where a campaign is in the route, compute the demonstration level from the
   required margin, compare it against the facility capability with the same
   tie-safe comparison, and flag an undeclared capability as its own finding.
6. Audit the detection set for two independent methods with at least one local
   and one global observer.
7. Report the route, the rationale, the demonstration level, the findings and
   the actions. The route is executable as declared only when the finding list
   is empty; a rejected similarity claim is reported alongside, since it
   explains the route without blocking it.

## Pitfalls

- Claiming similarity on a unit that runs hotter, faster or wider than its
  reference. Same design is not the same case; the operating point is part of
  the claim.
- Taking analysis-only on a bare pass. The extra above the requirement is the
  price of the analysis uncertainty, and a method that only just clears is the
  one most likely to be wrong.
- Letting a comfortable computed margin excuse a critical unit from a
  campaign. The ratchet exists because the analysis models the design, not the
  hardware that was actually built.
- Demonstrating at the nominal level and calling the required margin proven.
  The demonstration level is the nominal power raised by the margin, and
  6 dB means four times the power, not a little more.
- Running a campaign with a single global detector. A port-level null tells
  you something changed; without a local observer it cannot be separated from
  a connector arc or an instrumentation artefact.
- Treating an unreachable facility as an acceptable reduced demonstration.
  Either the article changes, or the argument changes, but the required level
  does not quietly move.

## Behavior contract (gate 3)

The similarity assessment, route selection, demonstration-level, facility and
detection logic is exercised by the gate 3 contract test:
scripts/test_e2001_multipactor_verification_routes.py against
scripts/e2001_multipactor_verification_routes_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_multipactor_verification_routes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
