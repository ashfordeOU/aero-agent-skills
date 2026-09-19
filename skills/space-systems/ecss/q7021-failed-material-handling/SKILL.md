---
name: q7021-failed-material-handling
description: "Determine the disposition of a material that failed its ECSS-Q-ST-70-21C flammability screening: rejection, redesign of the installation, or a further round of testing. Use when a burned set has come back failing and the programme has to choose between dropping the material, changing the build it sits in, and screening an extended set. Ranks the observed failure modes so the most severe governs, refuses a use-as-is rationale behind a drip ignition or a specimen that never self-extinguished, sizes the extended set from the observed pass fraction in integer arithmetic, and names the actions and evidence each route carries. Trigger: ecss, q-st-70-21, flammability-failure-disposition, flaming-drip-ignition-severity, use-as-is-rationale-refusal, extended-specimen-set-sizing, installation-redesign-route, flammability-mitigation-evidence."
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
  tags: [ecss, q-st-70-21-flammability-screening-scope, q7021-failed-material-handling, flammability-failure-disposition, flaming-drip-ignition-severity, use-as-is-rationale-refusal, extended-specimen-set-sizing, installation-redesign-route]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Flammability Screening — Failed Material Handling (space-systems/ecss/q7021-failed-material-handling)

Use when the task is the evaluation step that follows a failed
ECSS-Q-ST-70-21C flammability screening — deciding whether the material
is withdrawn, the installation around it is changed, or a further round
of testing is owed, and saying what each route has to produce.

## Domain quick reference

- The failure modes are not equivalent, so they are ranked and the most
  severe one governs. A set that both over-burned and shed burning
  material is decided by the burning material, because that is the mode
  that moves the fire somewhere the specimen never reached.
- Two modes describe behaviour that no paperwork changes: a drip that
  ignited the indicator, and a specimen that burned end to end without
  self-extinguishing. A use-as-is rationale behind either of those is
  refused outright, whatever the exceedance figure looks like.
- Whether the installation can be changed is the hinge of the whole
  decision. The same failure ends a material that has to sit exposed and
  merely costs a barrier where the build is still open, so the
  disposition cannot be read off the test result alone.
- An isolated failure and a majority failure are different events. One
  specimen in five is a candidate for an extended set; four in five is
  the material behaving as it does, and burning more of it is waiting
  for a favourable draw rather than gathering evidence.
- An extended set has to be sized, not guessed. If the same rate
  recurs, the set still has to yield the class minimum of clean
  specimens, which fixes the count; when that count runs past a
  practical multiple of the minimum, the retest is not a route.
- A mitigation carries a marginal exceedance, not an arbitrary one, and
  it carries evidence with it: what the mitigation is and what the
  residual exceedance does to the hazard.

## Workflow

1. Validate the record: the material, the observed failure modes, how
   many specimens of how many failed, the exceedance, and whether the
   installation can change or a mitigation exists. Refuse an unknown
   mode and a failure count above the set size.
2. Rank the modes and take the most severe as the governing one,
   breaking a tie on name so the outcome is reproducible.
3. Record a finding when use-as-is is requested behind a severe mode, or
   requested with no rationale reference behind it at all.
4. Compute the observed pass fraction and size the extended set in
   integer arithmetic, so the count does not depend on how a platform
   rounds a division; return no size when the set was wholly consumed by
   failures or the count is impractical.
5. Decide in precedence order: a severe mode redesigns the installation
   where that is possible and rejects the material where it is not; a
   wholly failed set goes the same way; an isolated failure with a
   viable count goes to an extended set; a changeable installation goes
   to a configuration change; a marginal exceedance with a mitigation
   behind it is carried; anything left is a rejection.
6. Emit the actions the route requires and the evidence it owes, so the
   disposition can be audited rather than asserted.

## Pitfalls

- Letting the loudest number govern instead of the worst mode. A large
  burn-length exceedance draws the eye away from a single drip that lit
  the indicator, which is the more severe finding.
- Accepting a use-as-is rationale on a drip ignition. The rationale
  describes intent; the drip described behaviour.
- Retesting a majority failure. The extended set is for an unlucky
  draw, and running it on a material that failed most of its specimens
  buys a second opinion from the same population.
- Sizing the extended set by habit. Doubling the original set has no
  relation to the observed rate; the count follows from needing the
  class minimum of clean specimens back.
- Carrying an arbitrary exceedance on a mitigation. A mitigation covers
  a margin, and past the ceiling it is standing in for a decision
  nobody made.
- Treating a configuration change as a retest. It is a different build,
  so the evidence it owes is a fresh screening run, not a rerun.

## Behavior contract (gate 3)

The record validation, mode ranking, use-as-is refusal, pass-fraction
computation, integer extended-set sizing with its practical cap,
disposition precedence and the actions-and-evidence output are
exercised by the gate 3 contract test:
scripts/test_q7021_failed_material_handling.py against
scripts/q7021_failed_material_handling_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q7021_failed_material_handling.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
