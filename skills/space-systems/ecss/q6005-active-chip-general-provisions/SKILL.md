---
name: q6005-active-chip-general-provisions
description: "Assess whether an active die purchase declaration covers the baseline provisions every such purchase carries under ECSS-Q-ST-60-05C clause 8.3.1, irrespective of device function or technology. Use when the task is separating the provisions that hold for all active dice from the ones a technology or a device function conditions in, computing the baseline coverage of a declaration, testing each waiver for an entitled authority and an unexpired validity date, and refusing a device-specific provision offered in place of a baseline one. Trigger: ecss, q-st-60-05c, active-die-baseline-provisions, hybrid-die-purchase-declaration, die-provision-applicability, die-provision-waiver-validity, die-baseline-coverage, die-provision-substitution."
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
  tags: [ecss, q-st-60-05-hybrid-scope, q6005-active-chip-general-provisions, active-die-baseline-provisions, hybrid-die-purchase-declaration, die-provision-applicability, die-provision-waiver-validity, die-baseline-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrid Procurement — Active Chip General Provisions (space-systems/ecss/q6005-active-chip-general-provisions)

Use when the task is the baseline layer of ECSS-Q-ST-60-05C clause
8.3.1 — establishing what every purchase of active dice owes before
anything about the particular device is taken into account, and whether
a given purchase declaration actually carries it.

## Domain quick reference

- A provision is baseline only when it holds whatever the device does
  and whatever process made it. That test is strict in both directions:
  a provision naming a technology is not baseline however widely that
  technology is used, and a record claiming to cover every purchase
  while also naming a condition is internally inconsistent rather than
  generously scoped, so it is refused rather than read charitably.
- The baseline and the conditioned provisions add; they never trade. A
  purchase of a compound-semiconductor die owes the backside metal
  inspection its technology conditions in on top of the whole baseline,
  not instead of part of it. Reporting the two sets separately is what
  keeps that visible, because a single merged count hides which layer a
  gap sits in.
- Not every baseline provision may be waived. The ones establishing the
  identity of the dice — the traceability back to a diffusion lot, the
  visual inspection made before the die disappears under a lid, the
  handling regime against electrostatic discharge — cannot be, because
  waiving them removes the ability to review anything else about the
  purchase afterwards.
- A waiver is tested, not counted. It has to name a provision that may
  be waived, come from an authority entitled to grant it, and still be
  inside its validity date on the day the purchase is assessed. A
  supplier granting itself relief from a provision written to constrain
  it is not a weak waiver; it is an open gap with a signature on it.
- A device-specific provision offered in place of a baseline one trades
  a requirement that holds everywhere for one that holds in a single
  case. The baseline member stays open, and the substitution is itself
  reported so the trade is visible to a reviewer rather than absorbed
  into a coverage number.

## Workflow

1. Validate each provision record: identifier, scope and condition. A
   universal scope carrying a condition, a conditioned scope without
   one, and an unknown technology or device function named as a
   condition are input errors.
2. Resolve what the purchase owes: the whole baseline set, plus each
   conditioned provision whose technology or device function the
   purchase matches.
3. Validate the declaration: identifier, technology, device function,
   the provisions declared, the waivers offered and any substitution
   proposed. A provision nobody defines is an input error, not a gap.
4. Test every waiver against the assessment date — waivable provision,
   entitled authority, unexpired validity — and treat a waiver on its
   last valid day as still valid.
5. Compute the baseline gap as the provisions neither declared nor
   relieved by a waiver that passed that test, and the coverage as the
   share of the baseline closed, absorbing the quotient representation
   error with a named tolerance rather than rounding a real gap away.
6. Report the conditioned gaps separately from the baseline gaps, and
   report each substitution by the baseline provision it was offered
   against.
7. Aggregate the purchase set: acceptable and open declarations listed
   separately, with the weakest declaration and its coverage named.

## Pitfalls

- Reading a widely applicable provision as baseline. Wide is not
  universal; a provision conditioned on a technology stops applying the
  moment the purchase changes technology, and a baseline one does not.
- Letting a conditioned provision stand in for a baseline member.
  The two layers add, and a screen written for one device function
  cannot discharge a requirement written for every purchase.
- Counting waivers instead of testing them. An expired waiver, an
  unentitled authority and a waiver against a provision that may not be
  waived all look identical in a total, and none of them closes a gap.
- Accepting a waiver signed by the party it constrains. Self-granted
  relief is the gap it was meant to close, with a signature added.
- Reporting a single coverage figure. Baseline gaps and conditioned
  gaps have different consequences, and a merged percentage cannot say
  which layer is open.

## Behavior contract (gate 3)

The scope validation, applicability resolution, waiver testing, baseline
gap and coverage computation, substitution reporting and purchase-set
aggregation are exercised by the gate 3 contract test:
scripts/test_q6005_active_chip_general_provisions.py against
scripts/q6005_active_chip_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6005_active_chip_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
