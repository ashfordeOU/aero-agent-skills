---
name: q7022-expiry-date-control
description: "Evaluate the expiry status of limited-shelf-life stock under ECSS-Q-ST-70-22 and say what leaves the shelf: derive the nominal date by adding calendar months to manufacture with end-of-month clamping, charge the excess for time spent outside controlled storage, apply an extension only when an approval reference backs it, then grade each item in-date, expiring inside the alert window, expired, or overridden by a recorded storage non-conformance, and return the quarantine list. Use when stock is reviewed, an alert fires, or an issue request is checked. Trigger: ecss, q-st-70-22, shelf-life-expiry-date-derivation, shelf-life-alert-window, expired-material-quarantine, out-of-store-shelf-life-penalty."
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
  tags: [ecss, q-st-70-22-limited-shelf-life-materials, q-st-70-22, q7022-expiry-date-control, shelf-life-expiry-date-derivation, shelf-life-alert-window, expired-material-quarantine, out-of-store-shelf-life-penalty, shelf-life-extension-approval-reference]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Limited Shelf Life — Expiry Date Control (space-systems/ecss/q7022-expiry-date-control)

Use when the task is the expiry side of ECSS-Q-ST-70-22 stock control: deriving
the date a limited-shelf-life item runs out on, tracking it against a review
date, and getting expired material off the issuable shelf.

## Domain quick reference

- Shelf life is declared in calendar months, and calendar months are not fixed
  spans. Adding them has to clamp at the end of the month: a lot made on the
  31st and given one month expires on the 28th or 29th, never on the 1st or 2nd
  of the month after. Converting months to a nominal thirty days instead drifts
  by days a year, always in the unsafe direction for a long shelf life.
- The declared shelf life presumes the declared storage. Time the item spends
  outside controlled storage is consumed faster, so the excess above one-for-one
  is charged against the date and the effective expiry moves in. Rounding that
  charge up to a whole day keeps the arithmetic conservative.
- An extension is a date change backed by an approval, not a number in a field.
  An extension with no approval reference stays unapplied and is reported as a
  finding — silently honouring it is how an expired lot becomes issuable.
- The expiry day itself is still inside the shelf life; expired starts the day
  after. Off-by-one here scraps usable material or issues unusable material,
  depending on which way it is wrong.
- A recorded storage non-conformance outranks the arithmetic entirely. The date
  was derived for a regime the item did not get, so the answer is
  quarantine-pending-review, not a recomputed date.

## Workflow

1. Validate each item: identity and material present, manufacture date
   parsable, shelf life a positive whole number of months, out-of-store days a
   non-negative integer, acceleration factor at least one-for-one.
2. Derive the nominal expiry by adding the shelf-life months to the manufacture
   date with end-of-month clamping.
3. Compute the out-of-store penalty as the excess of the factor over
   one-for-one across the recorded days, rounded up to whole days.
4. Apply an extension only when an approval reference is present; record an
   unbacked extension as a finding and leave the date alone.
5. Form the effective expiry and the remaining days at the review date.
6. Grade the item: storage non-conformance first, then expired, then inside the
   alert window, then in-date.
7. Map the status to its stock action and roll the holding up into a quarantine
   list, an expiring-soon list and per-status counts.

## Pitfalls

- Treating a month as thirty days. It compounds, and a twenty-four month shelf
  life derived that way ends up over a fortnight late.
- Rolling the 31st into the next month. A clamp is the only arithmetic that
  keeps the derived date inside the declared life.
- Charging the whole out-of-store period against the shelf life. Only the
  excess above the in-store rate is extra consumption; charging all of it
  scraps material that is still good.
- Applying an extension because the field is populated. The approval reference
  is what makes it an extension; without it the number is a proposal.
- Counting the expiry day as expired, or the day after as still in date. State
  the convention in the comparison and test both sides of it.
- Recomputing a date around a storage non-conformance. The item needs a review,
  not better arithmetic.

## Behavior contract (gate 3)

The clamped month arithmetic, item validation, out-of-store penalty, approval-
gated extension, remaining-day count, status precedence and the quarantine
roll-up are exercised by the gate 3 contract test:
scripts/test_q7022_expiry_date_control.py against
scripts/q7022_expiry_date_control_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q7022_expiry_date_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
