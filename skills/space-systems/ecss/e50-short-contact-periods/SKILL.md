---
name: e50-short-contact-periods
description: "Size a space link against the contact periods a mission actually gets, under ECSS-E-ST-50C Rev.2 clause 5.6.3. Use when the task is deciding whether short contacts can move the data a spacecraft produces: subtracting link acquisition and setup time from each pass, converting the usable time into a deliverable volume through the coding rate and framing efficiency, walking the schedule so the onboard store fills between passes and drains during them, flagging a pass consumed entirely by its own setup, and reporting overflow and whether the backlog is stable. Trigger: ecss, e-st-50c, short-contact-period, link-acquisition-setup-overhead, pass-data-volume-budget, onboard-storage-backlog, contact-schedule-drain, required-channel-rate."
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
  tags: [ecss, e-st-50-communications-scope, e50-short-contact-periods, short-contact-period, link-acquisition-setup-overhead, pass-data-volume-budget, onboard-storage-backlog, required-channel-rate]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Short Contact Periods (space-systems/ecss/e50-short-contact-periods)

Use when the task is the short-contact provision of ECSS-E-ST-50C
Rev.2 clause 5.6.3 — showing that the space link can move the mission
data inside the contact periods the orbit and the ground network
actually provide, including the short passes where link acquisition
and setup take a visible share of the window.

## Domain quick reference

- A contact period is not transfer time. Acquisition, carrier and
  symbol lock, and protocol setup are paid before the first user bit
  moves, and that cost is fixed per pass rather than per bit. The
  shorter the pass, the larger the share it takes.
- Two failure shapes follow from that. A pass shorter than its own
  setup delivers nothing and should be recognised as a non-contact
  rather than carried in the budget as a small one. A pass where setup
  takes most of the window still delivers, but the effective rate over
  the pass is far below the channel rate and sizing on the channel rate
  alone overstates it.
- The rate on the air is not the rate of user data. The coding rate
  and the framing efficiency each take their share, so the deliverable
  volume of a pass is the usable time times the channel rate times both
  factors.
- The budget closes over a plan, not over one pass. Between contacts
  the onboard store fills at the generation rate; during a contact it
  fills at the same rate while it drains at the delivered rate. The
  question is whether the backlog at the end of the plan is no larger
  than the backlog at the start.
- Storage capacity turns a backlog into a loss. Once the store is full,
  what is generated is dropped, and the dropped volume has to be
  counted rather than absorbed silently into a backlog number that
  looks stable only because the store stopped growing.

## Workflow

1. Validate each contact record: identifier, start time, duration,
   setup time, channel rate, coding rate and framing efficiency. A
   non-positive duration or rate, or a coding or framing factor outside
   its range, is an input error, not a case to clamp.
2. Subtract the setup time from each pass to get the usable transfer
   time, flooring at zero rather than letting a negative time flow into
   the volume arithmetic.
3. Convert the channel rate to a user-data rate through the coding rate
   and the framing efficiency, then multiply by the usable time for the
   deliverable volume of that pass.
4. Raise the per-pass findings: a contact fully consumed by its own
   setup, and a contact where setup takes more than half the window.
5. Order the schedule in time, refusing a duplicate identifier and
   refusing overlapping passes, which are a schedule error rather than
   a pass to merge.
6. Walk the plan: accumulate generation between and during contacts,
   drain what the pass can deliver, clamp at the storage capacity and
   count what is lost when the store is full.
7. Report the final and peak backlog, the lost volume, whether the
   store was ever cleared, and whether the plan is stable, absorbing
   representation error at the capacity boundary with a named
   tolerance.

## Pitfalls

- Sizing a short pass on the channel rate. The effective rate across
  the pass is the deliverable volume divided by the whole contact
  period, and on a short pass the two differ by more than the link
  margin ever will.
- Treating a pass shorter than its setup as a small contact. It is a
  zero contact, and averaging it into a per-pass volume hides both the
  loss and the reason for it.
- Closing the budget on a per-pass basis. A pass can look sufficient
  while the plan still diverges, because generation continues between
  contacts and the gap is where the backlog is built.
- Reporting a stable backlog from a full store. A store at capacity
  stops growing because data is being dropped; the stable-looking
  number is the capacity, and the loss is the finding.
- Ignoring generation during the contact itself. On a long pass with a
  high generation rate, the data produced while the pass runs is a real
  part of what the pass has to carry.

## Behavior contract (gate 3)

The contact validation, usable-time and effective-throughput
computation, deliverable-volume and required-rate inversion, per-pass
findings, time-ordering and overlap refusal, and the backlog walk with
storage clamping are exercised by the gate 3 contract test:
scripts/test_e50_short_contact_periods.py against
scripts/e50_short_contact_periods_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e50_short_contact_periods.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
