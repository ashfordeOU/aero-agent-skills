---
name: e2008-coverglass-conductivity-test-purpose
description: "Use when scoping or reviewing a conductive-coverglass uniformity survey. Determine what a surface conductivity survey of a conductive coverglass has to deliver under ECSS-E-ST-20-08C clause 6.4.3.13.1: map the declared surface-charging behaviours onto the quantities the coating feeds them, turn surface conductivity into sheet resistance, derive the charge bleed time constant and the potential a poorly conducting region floats to under plasma current, then size the planned probe survey by touched area, site count and grid pitch. Trigger: ecss, e-st-20-08c-clause-6-4-3-13-1, conductive-coverglass-surface-conductivity, coverglass-coating-uniformity-survey, solar-array-differential-surface-charging, coverglass-charge-bleed-time-constant, coating-sheet-resistance-derivation, coverglass-probe-site-coverage."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-coverglass-conductivity-test-purpose, conductive-coverglass-surface-conductivity, coverglass-coating-uniformity-survey, solar-array-differential-surface-charging, coverglass-charge-bleed-time-constant, coating-sheet-resistance-derivation, coverglass-probe-site-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Coverglass Conductivity Test Purpose (space-systems/ecss/e2008-coverglass-conductivity-test-purpose)

Use when the task is to state and defend why the conductivity of a
conductive coverglass is surveyed across its whole outer face under
ECSS-E-ST-20-08C clause 6.4.3.13.1 -- which surface-charging behaviours
the number feeds, whether this coating is resistive enough for any of
them to matter, and whether the planned probe survey can see a
non-uniform face at all.

## Domain quick reference

- A conductive coverglass is insulating glass with a thin conductive
  coating on its outer face. The coating exists so the charge a plasma
  deposits can run sideways to a grounded point instead of sitting
  still. Everything the clause is interested in is a property of that
  sideways path.
- The quantity is per square, not per metre. Surface conductivity and
  its reciprocal, sheet resistance, are what a coating of unknown
  thickness is described in, and they do not need the thickness.
- The survey answers a uniformity question, not a value question. One
  spot measured and one number quoted describes one spot; charge only
  has to find a single high-resistance island to stop moving, and the
  potential that island floats to is what strikes the discharge.
- Three quantities follow from the sheet resistance and are what the
  declared behaviours actually respond to: the bleed time constant of
  the coated face, the differential potential a poorly conducting
  region floats to while the plasma keeps depositing current, and the
  continuity of the path from coating to frame. All three scale with
  the square of the bleed path length, so a coverglass in the middle of
  a large panel is in a different position from one beside the ground
  strap even with an identical coating.
- A coating conductive enough that no region can float to a potential
  worth worrying about does not earn the survey, however many
  behaviours are declared. That is a different outcome from a declared
  behaviour with no survey planned, and both differ again from a survey
  planned that cannot resolve what it was asked to find.
- A survey is only as good as where it touches. Too few sites, sites
  touching too little area, or a grid pitch wide enough to step over a
  dead patch each produce a clean record of a coating nobody looked at.

## Workflow

1. Validate the survey policy first: the potential that makes the
   survey worth running, the touched-area floor, the minimum site count
   and the pitch ceiling. A coverage fraction above one is refused
   rather than used.
2. Group the declared surface-charging behaviours, rejecting an
   unrecognised one rather than ignoring it, and map each to the
   quantity the conductivity feeds it. Append the shared uniformity
   objective whenever any behaviour is present.
3. Convert the declared surface conductivity into sheet resistance --
   the form the bleed path is sized in -- and keep both in the record.
4. Derive the charge bleed time constant of the coated face and the
   differential potential a region floats to under the declared plasma
   current density. These are reported whatever the verdict, because
   they are what the number was wanted for.
5. Decide whether the survey is required at all: a declared behaviour
   present and a differential potential at or above the significance
   trigger. A value landing exactly on the trigger earns the survey;
   the comparison tolerance absorbs representation error and the
   trigger does not move.
6. When it is required and a survey is planned, compute the share of
   the outer face the sites touch and the pitch of an even grid of
   them, then check both against the policy along with the site count.
7. Close on one verdict: uniformity characterisation not required,
   survey not planned, survey inadequate, or surface uniformity
   characterised -- reporting every inadequacy found, not only the
   first.

## Pitfalls

- Quoting a single-site reading as the coating's conductivity. The
  clause is about the whole outer face; one site is a sample of one and
  says nothing about the island next to it.
- Treating sheet resistance as a bulk resistivity. It is per square and
  independent of the square's size, so dividing it by a length or
  multiplying it by a thickness produces a number that belongs to no
  physical quantity.
- Ignoring the bleed path length. The potential and the time constant
  both scale with its square, so the same coating is benign near a
  ground strap and marginal in the middle of a panel.
- Reporting a conductivity without the quantities it was wanted for.
  The bleed time constant and the differential potential are the reason
  the survey exists; the siemens-per-square figure on its own leaves
  every charging analysis to redo the same arithmetic.
- Planning the survey by site count alone. Nine sites that each touch a
  few square micrometres, or nine sites spread over a large panel,
  satisfy a count and resolve nothing.

## Behavior contract (gate 3)

The policy validation, sheet resistance conversion, bleed time constant
and differential potential, the touched-area fraction, the grid pitch,
the behaviour inventory and objective mapping, and the purpose verdict
are exercised by the gate 3 contract test:
scripts/test_e2008_coverglass_conductivity_test_purpose.py against
scripts/e2008_coverglass_conductivity_test_purpose_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_coverglass_conductivity_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
