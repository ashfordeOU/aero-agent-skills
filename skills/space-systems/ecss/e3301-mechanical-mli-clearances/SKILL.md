---
name: e3301-mechanical-mli-clearances
description: "Verify the mechanical clearances of a mechanism against ECSS-E-ST-33-01C clauses 4.7.5.4.8 and 4.7.5.4.9. Use when moving parts, adjacent static parts and multi-layer insulation must be shown never to touch: combining each interface tolerance stack as an arithmetic worst case or a root-sum-square, subtracting thermal distortion, load deflection and mechanism excursion from the nominal gap, raising the MLI requirement to the inflated blanket envelope plus its standoff rather than the compressed thickness, and naming the governing interface. Trigger: ecss, e-st-33-01-mechanisms-scope, mechanism-moving-part-clearance, mli-blanket-clearance, mli-ballooning-envelope, clearance-tolerance-stack, mechanism-excursion-closure, governing-clearance-interface."
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
  tags: [ecss, e-st-33-01-mechanisms-scope, e3301-mechanical-mli-clearances, mechanism-moving-part-clearance, mli-blanket-clearance, mli-ballooning-envelope, clearance-tolerance-stack, mechanism-excursion-closure, governing-clearance-interface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Mechanical and MLI Clearances (space-systems/ecss/e3301-mechanical-mli-clearances)

Use when the task is the clearance case of ECSS-E-ST-33-01C clauses
4.7.5.4.8 and 4.7.5.4.9 -- proving that nothing in a mechanism touches
anything it is not meant to touch, across the tolerance stack, the
thermal distortion, the load deflection and the full travel of the
moving parts, with the separate and larger rule that applies wherever
multi-layer insulation is one of the two surfaces.

## Domain quick reference

- A clearance is not the drawing gap. It is the drawing gap less
  everything that closes it: the manufacturing and assembly tolerance
  stack, the thermal distortion between the two parts, the deflection
  each sees under its load case, and the excursion the mechanism
  actually travels through.
- The tolerance stack may be taken arithmetically or as a root-sum-square,
  and the choice is a justification, not a preference. A
  root-sum-square is a statistical statement about independent
  contributions; with only one or two contributors it is not a statistic
  at all, it is an arithmetic stack with an unearned reduction applied.
- A moving-to-static pair and a static-to-static adjacent pair do not
  carry the same floor. The moving pair has to survive every position of
  the travel, every repeat of it, and any overtravel the stops allow, so
  its floor is the larger of the two.
- MLI is the special case, and it is special because the blanket that is
  measured on the bench is not the blanket that flies. Trapped gas
  leaves during ascent and the layers separate, so the blanket inflates
  well beyond its compressed thickness. The clearance is held against
  that inflated envelope plus a standoff, never against the thickness a
  caliper reads.
- Every interface is declared, including the ones that look obviously
  generous. An interface nobody wrote down is an interface nobody
  checked, and the governing case is frequently one that was assumed
  comfortable.
- A negative worst-case clearance is contact, and contact is reported as
  contact rather than as a large negative margin -- the two lead to
  different corrective actions.

## Workflow

1. Enumerate every interface of the mechanism and give each a name, a
   kind -- moving, adjacent, or MLI -- and a nominal gap. Refuse a set
   that declares no interface, and refuse duplicate names, because a
   duplicate silently overwrites a real interface in any report built
   from the set.
2. For each interface, combine the tolerance contributions by the
   declared method, rejecting a root-sum-square that does not have
   enough independent contributions to justify it.
3. Subtract the tolerance, the thermal distortion, the deflection and
   the mechanism excursion from the nominal gap. A moving interface must
   state its excursion explicitly, even when it is zero, so that a
   forgotten travel cannot read as no travel.
4. Derive the required clearance from the kind. For an MLI interface,
   inflate the blanket thickness by the ballooning factor and add the
   standoff; for the others, take the floor of that kind unless a
   project-specific value overrides it.
5. Take the margin as the worst-case clearance less the requirement,
   absorbing representation error at zero with a named tolerance rather
   than by relaxing the floor.
6. Report every interface with its margin, name the governing one, and
   separate the contact findings from the insufficient-margin findings.

## Pitfalls

- Holding the clearance against the compressed MLI thickness. The
  blanket inflates on ascent; a gap sized on bench thickness is closed
  before the mechanism has been commanded once.
- Using a root-sum-square stack to recover a failing margin. It is only
  valid where the contributions are genuinely independent and numerous
  enough, and switching methods to pass is a finding rather than a fix.
- Checking clearance at the stowed position only. The governing position
  is somewhere in the travel, often at an overtravel stop, and the
  stowed gap says nothing about it.
- Omitting thermal distortion because both parts are the same material.
  They are rarely at the same temperature, and a gradient across an
  assembly closes gaps just as a material mismatch does.
- Reporting a negative clearance as a margin. Contact is a different
  finding with a different disposition, and burying it in a margin
  column loses that distinction.
- Leaving an interface undeclared because it looks generous. The set is
  only as complete as the enumeration, and an interface that was never
  listed has never been assessed at any margin.

## Behavior contract (gate 3)

The interface validation, tolerance-stack combination and its
root-sum-square guard, gap-closure arithmetic, MLI inflated-envelope
requirement, per-kind clearance floors, margin comparison, contact
detection and governing-interface selection are exercised by the gate 3
contract test: scripts/test_e3301_mechanical_mli_clearances.py against
scripts/e3301_mechanical_mli_clearances_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e3301_mechanical_mli_clearances.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
