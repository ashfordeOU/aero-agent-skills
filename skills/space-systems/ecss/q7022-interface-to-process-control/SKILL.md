---
name: q7022-interface-to-process-control
description: "Verify that a material issue may enter a controlled process under the ECSS-Q-ST-70-22C interface to the ECSS-Q-ST-70C, -70-16C and -70-31C process flows: build the operation window from the planned start and duration, separate a lot already expired from one expiring part way through, check the stores status and any open deviation, check the process against the lot approved list and the standard cited, bound a mixed material by its pot life, and return release or block with reason codes. Use when kitting, dispatching a work order or wiring a stores gate. Trigger: ecss, q-st-70-22c, expired-material-process-block, shelf-life-process-release-gate, shelf-life-operation-window, adhesive-pot-life-window, shelf-life-reason-codes."
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
  tags: [ecss, q-st-70-22c-limited-shelf-life-control, q-st-70-22c, q7022-interface-to-process-control, expired-material-process-block, shelf-life-process-release-gate, shelf-life-operation-window, adhesive-pot-life-window, shelf-life-reason-codes]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Interface to Process Control (space-systems/ecss/q7022-interface-to-process-control)

Use when the task is the interface clause of ECSS-Q-ST-70-22C: the gate that
stands between shelf-life control and the process standards that consume the
material, so that expired, quarantined or unapproved material cannot be issued
into a controlled operation.

## Domain quick reference

- The gate is an interface, not a report. Shelf-life control knows the lot;
  process control knows the operation; neither of them alone can refuse an
  issue, so the decision is taken where the two meet, at the moment material is
  drawn against a work order.
- The check is against a window, not an instant. Material drawn at 08:00 for a
  four-hour lay-up is in use until 12:00, and a lot whose life ends inside that
  window is not usable even though it was in date when the drum was opened.
- Already expired and expires-during-operation are different refusals with
  different recoveries. The first needs a different lot; the second may only
  need the work rescheduled or the operation split, so the gate keeps them
  apart rather than collapsing both into one refusal.
- Shelf life is not the only reason to refuse. A lot can be perfectly in date
  and still be in quarantine, carry an open deviation, or simply not be
  approved for the process the work order names; each blocks independently and
  all of them are reported, because fixing one does not release the issue.
- The process standard cited by the operation has to be one the interface is
  wired to. An operation quoting a reference the gate does not recognise is
  refused rather than waved through, since an unrecognised reference is exactly
  how an uncontrolled process acquires flight material.
- A mixed or activated material has a second, much shorter clock. Pot life runs
  from the moment of mixing and is independent of shelf life, so a lot two
  years inside its expiry can still be unusable twenty minutes after it was
  stirred.
- The refusal has to be machine-readable. A process-control system acting on
  the answer needs reason codes it can branch on; prose alone forces a human
  back into a loop that exists to be automatic.

## Workflow

1. Build the operation window: parse the planned start as a timestamp and add
   the application duration. A missing or non-positive duration is an input
   error, not a zero-length operation.
2. Take the shelf-life deadline as the end of the expiry day, and compare the
   window against it. A start at or after the deadline yields an already-expired
   refusal; a start before it with an end after it yields an
   expires-during-operation refusal.
3. Check the stores status against the releasable set, and refuse any lot
   carrying an open deviation regardless of status.
4. Check the process identifier against the lot's approved-process list, and
   the cited process standard against the recognised set.
5. Where the lot carries a mix time and a pot life, check whether the pot life
   was already spent at the planned start, and otherwise whether the operation
   runs past it. Demand both fields together: one without the other cannot
   bound the working time.
6. Return release only when no reason code was raised; otherwise return block
   with every code and a matching finding for each, so the caller can act on
   each refusal separately.

## Pitfalls

- Checking the expiry against the issue time only. The operation continues
  after the drum is opened, and a lot that expires mid-lay-up has been used
  outside its life even though the stores transaction was in date.
- Stopping at the first refusal. Reporting only the expiry hides the fact that
  the lot was also in quarantine, so a fresh lot is fetched and the issue is
  refused a second time for the reason nobody was shown.
- Treating pot life as a short shelf life. They run from different events and
  are checked separately; a lot with plenty of shelf life left can be dead in
  the pot, and a lot mixed a minute ago can still be out of date.
- Accepting an unrecognised process standard as a naming variation. The gate is
  wired to a known set, and an unknown reference is the route by which work
  outside the controlled flow gets issued flight material.
- Returning prose to a machine. The calling process-control system branches on
  codes; a sentence forces the refusal back through a human and the gate stops
  being a gate.
- Widening the window to let an operation that ends exactly on the deadline
  through. The equality is a representation question absorbed by the tolerance
  inside the comparison; the shelf life stays where it is.

## Behavior contract (gate 3)

The window construction, shelf-life deadline comparison, status and deviation
checks, approved-process and process-standard checks, pot-life bounding and
the coded release or block decision are exercised by the gate 3 contract test:
scripts/test_q7022_interface_to_process_control.py against
scripts/q7022_interface_to_process_control_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7022_interface_to_process_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
