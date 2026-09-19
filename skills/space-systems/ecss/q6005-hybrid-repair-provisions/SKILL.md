---
name: q6005-hybrid-repair-provisions
description: "Assess whether corrective work is open on a partially assembled hybrid microcircuit under ECSS-Q-ST-60-05C clause 10.5: place the unit in the assembly sequence, compare the stage reached with the window in which the requested action can still reach what it works on, decide whether the route is direct, through lid removal, or closed because the area is buried under later assembly, derive the re-screening that route drags with it, and return the permission with its blockers and approvals. Use when a repair is proposed on a part-built or sealed unit. Trigger: ecss, q-st-60-05c, hybrid-repair-permission-by-assembly-stage, pre-cap-repair-window, lid-removal-rescreen-consequence, hybrid-element-replacement-limits, wire-rebond-permission."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-hybrid-repair-provisions, hybrid-repair-permission-by-assembly-stage, pre-cap-repair-window, lid-removal-rescreen-consequence, hybrid-element-replacement-limits, wire-rebond-permission]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Repair Permission and Limits (space-systems/ecss/q6005-hybrid-repair-provisions)

Use when the task is deciding whether a proposed piece of corrective work on
a partially assembled hybrid microcircuit is permitted at all under
ECSS-Q-ST-60-05C clause 10.5 — which actions the stage reached still allows,
what opening a sealed unit costs, and what has to be re-screened afterwards.

## Domain quick reference

- Repair permission is a function of the assembly stage, not of the defect.
  The same lifted bond is a routine rebond before the lid goes on and a major
  concession afterwards, because what changed is access and what has already
  been certified — not the defect.
- Each action has a window that closes when later assembly buries what it
  works on. Substrate metallization can be touched up until elements sit on
  it; an element can be replaced until the bonds are made; a bond can be
  rebonded until the lid goes on; external leads stay reachable after sealing.
- Lid removal recovers exactly one band of work. It reverts the unit to its
  pre-cap state and no further, so it reopens the actions whose window ran to
  pre-cap and nothing earlier. A de-lidded unit is not a bare substrate, and
  no approval makes it one.
- The cost of lid removal is the whole screening sequence. Everything the
  seal certified — hermeticity above all, but also the post-seal electrical
  and visual results — was obtained on a unit that no longer exists in that
  configuration, so it is earned again rather than carried over.
- Work inside the window is not free either. Anything done after the pre-cap
  inspection repeats it, and anything done on a sealed unit repeats the seal
  tests, because the repair itself is a chance to have disturbed the seal.
- A delivered unit has left the line. Work on it is a matter between the
  customer and the manufacturer before it is a matter of assembly stage, and
  the assessment says so rather than quietly treating delivery as one more
  stage.

## Workflow

1. Validate the request: a known action, a known assembly stage, and boolean
   flags for the approved procedure and any customer approval. An unknown
   action or stage is refused rather than defaulted, because both of them
   decide the answer.
2. Place the stage in the assembly sequence and compare it with the action's
   window. Inside the window, the route is direct.
3. Outside the window, ask whether the seal is the only obstacle: the route is
   lid removal when the action's window ran to the pre-cap state and closed
   only because the unit was sealed. Otherwise the route is closed.
4. Collect the blockers by name — a closed window, a missing approved
   procedure, lid removal without customer approval, delivered hardware
   without customer approval — rather than stopping at the first.
5. Derive the re-screening the route drags with it: inspect the repaired area,
   repeat the pre-cap inspection when the unit had passed it, repeat the seal
   tests when the unit was sealed, and repeat the full sequence after any lid
   removal.
6. Return the permission, the route, the window, the blockers, the approvals
   required and the re-screen steps.

## Pitfalls

- Reading an approval as access. Customer approval can authorise opening a
  sealed unit; it cannot un-bury a substrate track under an attached die, and
  a closed window stays closed however senior the signature.
- Carrying post-seal screening results across a lid removal. Those results
  describe a hermetic unit; after de-lidding and re-sealing they describe
  nothing, and re-using them is the single most expensive mistake in this
  clause.
- Treating an external lead repair on a sealed unit as free. The lead is
  reachable without opening anything, but bending or reworking it loads the
  seal, so the seal tests and the external visual are repeated.
- Assuming a rebond is always available. Once the lid is on, a rebond is a
  lid-removal job with a full re-screen behind it, which is frequently more
  expensive than the unit.
- Letting delivery blur into the assembly sequence. A delivered unit is
  outside the manufacturer's control, and work on it needs the customer's
  agreement before any question of stage or window arises.
- Deriving the re-screen from the defect rather than the route. The route is
  what determines which certifications were invalidated; two repairs of the
  same defect at different stages owe different re-screens.

## Behavior contract (gate 3)

The assembly sequence, the per-action repair window, the direct, lid-removal
and closed routes, the re-screen derivation and the approvals and blockers of
a request are exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_repair_provisions.py against
scripts/q6005_hybrid_repair_provisions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_hybrid_repair_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
