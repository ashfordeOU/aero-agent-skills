---
name: e2007-emc-general-system-requirements
description: "Use when audit the system-level electromagnetic-compatibility policy of ECSS-E-ST-20-07C clause 4.1: confirm every mandated policy element is on record - the emc-control-plan, the electromagnetic-effects-verification-plan, the grounding-and-bonding policy, the magnetic-cleanliness policy, the radiation-hazard policy and the spacecraft-charging protection programme - each carrying a named owner, an accepted release state and a baselining milestone no later than the one the programme allows, categorize every unit as an intentional-emitter, an intentional-receiver, a non-intentional-source or a susceptible-victim, and derive from the mission orbit-regime which surface-charging and internal-charging protection tasks the programme owes. Trigger: ecss, e-st-20-07c, e-st-20-electrical-scope, emc-control-plan, electromagnetic-compatibility-policy, spacecraft-charging-protection, grounding-and-bonding-policy, magnetic-cleanliness-policy, emc-programme-audit, orbit-regime-charging-tasks."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-emc-general-system-requirements, emc-control-plan, electromagnetic-compatibility-policy, spacecraft-charging-protection, grounding-and-bonding-policy, magnetic-cleanliness-policy, emc-programme-audit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — General System Requirements (space-systems/ecss/e2007-emc-general-system-requirements)

Use when the task is the system-level electromagnetic policy audit of
ECSS-E-ST-20-07C clause 4.1 -- proving that the programme carries a
complete, owned and baselined set of electromagnetic policy elements,
that every unit has an electromagnetic role on record, and that the
spacecraft-charging protection programme owes the tasks the mission
orbit-regime actually drives.

## Domain quick reference

- Clause 4.1 is the pointer clause: it does not itself set a limit, it
  requires that a system-level electromagnetic policy exists and that
  the charging-protection programme is declared. The auditable objects
  are therefore documents and assignments, not field strengths. Six
  policy elements are treated as mandatory here: the emc-control-plan,
  the electromagnetic-effects-verification-plan, the
  grounding-and-bonding policy, the magnetic-cleanliness policy, the
  radiation-hazard policy and the charging-protection programme.
  Two further elements (intersystem-compatibility policy,
  lightning-protection policy) are recognised but optional; an
  unrecognised element type is rejected rather than silently counted.
- Each element carries three attributes that make it auditable: an
  owner (a named organisational actor, never blank), a release state
  (draft, released, baselined or withdrawn -- only released and
  baselined count as on record), and the review milestone at which it
  reached that state. The milestone sequence is srr, pdr, cdr, qr, ar,
  and each mandatory element has a latest milestone by which it must
  be baselined: the emc-control-plan and the grounding-and-bonding
  policy by pdr, the verification plan, the magnetic-cleanliness
  policy and the charging-protection programme by cdr, the
  radiation-hazard policy by qr. An element baselined later than its
  allowed milestone is a finding even though it exists.
- Every unit is given at least one electromagnetic role so the
  control plan knows what to constrain: an intentional-emitter
  (declared transmit power above zero), an intentional-receiver
  (declared receive sensitivity), a non-intentional-source (a
  switching converter, motor drive or clocked digital unit) and a
  susceptible-victim (a declared susceptibility threshold). A unit may
  hold several roles at once; a unit that declares none of these
  attributes is uncategorized and is rejected, because an
  uncategorized unit silently escapes the control plan.
- The charging-protection tasks follow the orbit-regime, not the
  spacecraft size: a low-inclination low-Earth regime drives only the
  ram-wake and auroral-free baseline task set, a polar low-Earth
  regime adds auroral-charging protection, and the meo, geo and
  highly-elliptical regimes add internal (deep-dielectric) charging
  protection because the energetic-electron environment penetrates
  behind the outer surface. Surface-charging protection is owed by
  every regime except the low-inclination low-Earth one.

## Workflow

1. Normalize each declared policy element: reject a blank identifier,
   an unrecognised element type, an unrecognised release state, a
   missing owner and an unrecognised milestone before anything is
   counted.
2. List the mandatory element types with no entry at all, and
   separately the mandatory types that exist but sit in a draft or
   withdrawn state -- these are distinct findings and must not be
   merged, because an absent plan and an unapproved plan are repaired
   by different actions.
3. For each mandatory element that is on record, compare the milestone
   at which it was baselined against the latest milestone the
   programme allows for that element and raise a late-baseline finding
   when it is later.
4. Categorize every unit into its electromagnetic roles from its
   declared attributes; reject a unit that declares none. Keep the
   per-role inventory: it is the input the emc-control-plan needs in
   order to allocate emission and susceptibility limits.
5. Derive the charging-protection task set from the mission
   orbit-regime and compare it against the tasks the programme
   declares; a task that the regime drives but the programme omits is
   a finding, and a declared task that the regime does not drive is
   reported as an over-declaration rather than an error.
6. Compute the policy coverage ratio (mandatory elements on record
   divided by mandatory elements required) and compare it against the
   programme target with an explicit floating-point tolerance. The
   system is policy-compliant only when every finding list is empty.

## Pitfalls

- Counting a draft element as coverage: a draft emc-control-plan
  carries no configuration control, so the coverage ratio must only
  credit released or baselined elements, and the draft state must
  surface as its own finding rather than as a missing element.
- Accepting an element with no named owner: an unowned policy element
  has no actor to close its actions, which is why a blank owner is a
  normalization error and not a warning.
- Reading "the plan exists" as "the plan exists in time": an
  emc-control-plan baselined at qr arrives after the design is frozen
  and cannot shape it, so the milestone comparison is a mandatory part
  of the audit and not an optional extra.
- Letting a unit through with no electromagnetic role: an
  uncategorized unit never receives an emission or susceptibility
  allocation, and the gap is invisible at system level until an
  integration-level surprise. Reject it at normalization.
- Copying the charging-protection task set from a previous mission of
  a different orbit-regime: internal charging protection is driven by
  the energetic-electron environment of meo, geo and
  highly-elliptical regimes, and is not interchangeable with the
  surface-charging task set of a low-Earth mission.
- Comparing the coverage ratio with a bare equality or a bare
  greater-or-equal: the ratio is a quotient of small integers and the
  programme target is a decimal, so an exactly-met target can land a
  few units in the last place below the limit. Absorb that in the
  comparison, never by lowering the target.

## Behavior contract (gate 3)

The element-normalization, mandatory-coverage, late-baseline,
unit-role-categorization, orbit-regime charging-task and coverage-ratio
logic is exercised by the gate 3 contract test:
`scripts/test_e2007_emc_general_system_requirements.py` against
`scripts/e2007_emc_general_system_requirements_logic.py` (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_emc_general_system_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
