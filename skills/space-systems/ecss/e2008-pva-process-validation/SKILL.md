---
name: e2008-pva-process-validation
description: "Use when a production go-ahead turns on validation coverage. Screen every project design configuration for manufacturing and integration process validation before a photovoltaic assembly enters production, per ECSS-E-ST-20-08C clause 5.4.1: build a governing signature for each configuration from cell assembly, interconnect, substrate, adhesive, layout edge condition and coverglass thickness; test whether any validation run speaks for it, matching the numeric attribute against a validated range rather than a single value; admit a run only when it passed, carried enough coupons, sits inside its validity window and has not been overtaken by a process change; then group the configurations left open by signature into the smallest honest set of further runs. Trigger: ecss, e-st-20-electrical-scope, pva-process-validation, photovoltaic-assembly-process-qualification, design-configuration-coverage, validation-run-admissibility, process-change-supersession, production-release-readiness."
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
  tags: [ecss, e-st-20-electrical-scope, e2008-pva-process-validation, pva-process-validation, photovoltaic-assembly-process-qualification, design-configuration-coverage, validation-run-admissibility, process-change-supersession, production-release-readiness]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic — PVA Process Validation (space-systems/ecss/e2008-pva-process-validation)

Use when the task is the process validation of ECSS-E-ST-20-08C clause
5.4.1 -- showing, before a photovoltaic assembly goes into production,
that the manufacturing and integration processes have been validated
against every design configuration the project actually builds, not
against a representative one.

## Domain quick reference

- A panel programme almost never has a single configuration. Edge
  strings differ from field strings, a thicker coverglass sits over the
  outer rows, the yoke panel uses a different substrate construction.
  Each of those is a configuration in its own right and each needs
  validation evidence of its own.
- The governing attributes are the ones a process has to be re-proven
  against: cell assembly type, interconnect design, substrate
  construction, bonding adhesive, layout edge condition and coverglass
  thickness. Together they are the configuration's signature.
- Categorical attributes match exactly. Coverglass thickness is
  numeric, so a run validates a range and a configuration is covered
  when its thickness falls inside that range -- which is what lets one
  run legitimately speak for several thicknesses.
- Coverage is only half the question. A run also has to be admissible:
  it has to have passed, to have carried at least the declared number of
  coupons, to sit inside its validity window, and to postdate the latest
  process change. A run that matches perfectly but was carried out
  before the adhesive mix changed validates nothing.
- A process change withdraws every earlier run at once. That is the
  case that turns a fully covered programme into a fully open one
  overnight, and it is why the change index is carried with the run
  rather than inferred from its date.
- Configurations that share a signature can be closed by a single run,
  so the outstanding work is counted in distinct signatures, not in
  configurations. That count is the honest schedule impact.
- The validity window, the coupon minimum and the release rule are a
  declared project policy rather than physical constants, so they are
  stated with the result.

## Workflow

1. Enumerate the design configurations the project will actually build
   and reject any that leaves a governing attribute undeclared. A
   configuration nobody wrote down is the one that reaches production
   unvalidated.
2. Reject a repeated configuration identifier rather than merging the
   two records, because a silently merged pair hides one of the two
   builds from the coverage count.
3. For each configuration, look for a run that speaks for it: every
   categorical attribute equal, and the coverglass thickness inside the
   run's validated range.
4. Test each covering run for admissibility -- passed, enough coupons,
   inside the validity window, not superseded by a process change --
   and record why an otherwise matching run was set aside.
5. Group the configurations still open by signature and report one
   further run per distinct signature, with the attributes that run has
   to be carried out on.
6. Withhold the production release while any configuration is open, and
   report the coverage fraction with the reasons rather than a bare
   verdict, so the shortest path to release is visible.

## Pitfalls

- Validating the representative configuration and treating the rest as
  covered. The whole point of the clause is that every configuration the
  project builds is validated; the edge string and the yoke panel are
  where an unvalidated process actually escapes.
- Matching a coverglass thickness by equality. A run validates a range,
  and forcing exact equality invents work that the evidence already
  covers -- while forcing no check at all would credit a run for a
  thickness it never saw.
- Counting a matching run as evidence without checking it passed. A
  failed run is still a run on the right configuration, and a coverage
  matrix built on identifiers alone will show it green.
- Letting a process change sit outside the coverage question. A change
  to the adhesive, the tooling or the cure supersedes every earlier
  run, and a programme that only re-validates the configuration it
  thought was affected keeps the rest on withdrawn evidence.
- Counting outstanding work per configuration. Configurations sharing a
  governing signature close together, so a per-configuration count
  overstates the schedule and hides the fact that one run clears
  several rows.

## Behavior contract (gate 3)

The configuration signature, run coverage including the numeric range,
run admissibility, process-change supersession, the outstanding-run
plan and the production-release verdict are exercised by the gate 3
contract test:
scripts/test_e2008_pva_process_validation.py against
scripts/e2008_pva_process_validation_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_pva_process_validation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
