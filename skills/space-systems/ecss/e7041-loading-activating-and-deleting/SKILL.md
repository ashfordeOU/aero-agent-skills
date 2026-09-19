---
name: e7041-loading-activating-and-deleting
description: "Manage the loading, activation and deletion of on-board control procedures under ECSS-E-ST-70-41C clause 6.18.4.4. Use when the task is deciding which of those commands the spacecraft should refuse and why: checking an uplinked image against its checksum before it is admitted, telling a repeated uplink apart from a version conflict on an occupied id, sizing an image against both the engine limit and the free store, refusing a second activation of a procedure already running, holding the engine to its concurrency limit, and blocking deletion of a running or permanent procedure. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-loading-and-deletion, obcp-activation-precondition, obcp-uplink-checksum-refusal, obcp-store-capacity-refusal, obcp-engine-slot-limit."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-loading-activating-and-deleting, obcp-loading-and-deletion, obcp-activation-precondition, obcp-uplink-checksum-refusal, obcp-store-capacity-refusal, obcp-engine-slot-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Loading, Activating and Deleting (space-systems/ecss/e7041-loading-activating-and-deleting)

Use when the task is the load, activate and delete moves of
ECSS-E-ST-70-41C clause 6.18.4.4 -- getting an on-board control
procedure aboard, starting it, and taking it off again, and deciding
which of those commands the spacecraft has to refuse for itself.

## Domain quick reference

- The ground is a round trip away. By the time it learns a command was
  wrong the wrong thing has already happened, so every precondition
  here is enforced on board and answered with a reason, not with a
  single failure code.
- Loading checks three separate things: the image arrived intact, it
  fits the engine's per-procedure limit and the store's free space, and
  the id it claims is free. A store that answers "it did not work"
  makes the ground guess between a corrupted uplink, a full store and
  an id collision -- three problems with three different fixes.
- A checksum is the gate, not a formality. An uplink that flipped a bit
  produces something that is still syntactically a procedure and
  behaviourally another one. An image with no declared checksum
  promises nothing, so nothing can contradict it, and the operator
  carries that risk knowingly.
- A repeated uplink and a version conflict are different events. The
  first is a retransmission and needs no action; the second means the
  ground is trying to replace a procedure that is still aboard and has
  to delete it first.
- Activation is not idempotent. Activating a running procedure a second
  time would be a second run of the same sequence, and for a
  deployment that is the difference between one release and two
  attempts. Refuse it; do not quietly treat it as a no-op.
- An engine has a fixed number of slots. Refusing the activation that
  would exceed them is the engine's job, and a plan that assumes
  otherwise discovers the limit at the worst moment.
- Deletion has two blockers, not one. A running procedure cannot be
  deleted, and neither can one the mission marked permanent -- the
  safing chain that must still be aboard after a memory tidy-up.
- Order matters and can be reasoned about: stop, then delete, then load
  the new version. Each step unlocks exactly the next one.

## Workflow

1. Validate the uplink: a non-empty id, a version of at least one, a
   non-empty code image, a boolean permanence flag, and a declared
   checksum if one is claimed.
2. Compute the image size and checksum from the image itself. Never
   take a declared size on trust; it is the thing most likely to be
   wrong when something else already is.
3. On load, resolve the id first. Occupied by the same version is a
   repeated uplink; occupied by another version is a conflict.
4. Then check the engine's per-procedure limit, then the checksum, then
   the free store. Report whichever refuses, and refuse before the
   store is touched -- a refused load consumes nothing.
5. On activate, require the procedure aboard, not already running, and
   an engine slot free. Treat the slot count as exact: demand equal to
   the limit is full.
6. On stop, require it to be running. Stopping an idle procedure is a
   refusal, and stopping an absent one is a different refusal again.
7. On delete, require it aboard, stopped, and not permanent. Return its
   octets to the free space and free its id.
8. For a command sequence, apply the moves in order, keep every outcome
   with its id, group the outcomes, and name the first refusal -- it is
   usually the one that explains the rest.

## Pitfalls

- Trusting a declared image size instead of measuring the image. The
  declared field is exactly what a bad uplink corrupts.
- Collapsing the refusals into one code. Re-uplinking into a full store
  fails identically every time, and the operator cannot tell that from
  the answer.
- Treating a repeat activation as harmless. It is a second execution,
  and for anything irreversible that is the whole incident.
- Deleting a running procedure to make room. The store frees octets the
  engine is still reading from, which is a fault with no clean report.
- Forgetting the permanent flag when sizing a memory tidy-up. The
  octets held by procedures that cannot be deleted are not reclaimable
  space, and a plan that counts them frees less than it promised.
- Refusing an image that is exactly at the engine limit or exactly
  fills the store. Both bounds are inclusive; a strict comparison
  throws away a procedure that fits.
- Comparing a fill fraction against capacity. Occupancy is exact in
  octets, so admit on the integers and keep the fraction for reporting.

## Behavior contract (gate 3)

The upload validation, measured size and checksum, intactness test,
store validation, the load refusals for repeated uplink, version
conflict, engine limit, checksum mismatch and full store, the
activation refusals for absent, already running and no free slot, the
stop refusals, the deletion refusals for running and permanent
procedures, octet and id reclamation, ordered sequence application and
the grouped store report are exercised by the gate 3 contract test:
scripts/test_e7041_loading_activating_and_deleting.py against
scripts/e7041_loading_activating_and_deleting_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e7041_loading_activating_and_deleting.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
