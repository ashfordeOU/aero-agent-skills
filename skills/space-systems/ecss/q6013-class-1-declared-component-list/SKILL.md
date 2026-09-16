---
name: q6013-class-1-declared-component-list
description: "Use when a declared component list, part approval package or equipment parts baseline is reviewed. Evaluate the declared component list raised for one equipment under clause 4.1.4 of ECSS-Q-ST-60-13C: confirm the list is scoped to that equipment and carries no orphan line, grade every line on the attributes an approval decision cannot be taken without, route each line to the authority its procurement category obliges, and keep apart an approval never requested, one still open, one refused, and one granted against another equipment or application and therefore not transferable. Weight the released lines by installed quantity, compare that coverage with the release threshold, and return one verdict with ranked findings. Trigger: ecss, q-st-60-13c, declared-component-list-per-equipment, commercial-component-approval-route, dcl-line-attribute-completeness, dcl-approval-coverage-fraction, dcl-release-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-scope, q-st-60-13c, q6013-class-1-declared-component-list, declared-component-list-per-equipment, commercial-component-approval-route, dcl-line-attribute-completeness, dcl-approval-coverage-fraction, dcl-release-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Declared Component List per Equipment (space-systems/ecss/q6013-class-1-declared-component-list)

Use when the task is clause 4.1.4 of ECSS-Q-ST-60-13C: the declared component
list a supplier raises for an equipment, and the route by which each of its
lines is approved. This leaf grades a list on whether it is scoped to one
equipment, whether each line carries what an approval decision needs, and
whether the approval that exists actually covers the line it is filed against.

## Domain quick reference

- The list is issued per equipment, not per supplier and not per programme. A
  single master spreadsheet covering four boxes reads as complete while no box
  has a list of its own, and the reviewer cannot tell which lines the box in
  front of them installs. A line raised against another equipment is an orphan
  on this list even when it is perfectly approved somewhere else.
- Four different situations look identical in an approval column that only
  holds "no": nobody ever raised the request, the request is sitting with the
  authority, the authority refused it, and an approval exists but was granted
  for a different equipment or a different application. The first needs a
  submission, the second needs time, the third needs a different part, and the
  fourth needs a new request against the current use. Collapsing them into one
  count makes the schedule impossible to plan.
- A commercial line owes a customer approval. An already-qualified line is
  carried by a project declaration. Filing a project declaration against a
  commercial line does not discharge it -- the supplier has declared the part
  to itself, which is the state the clause exists to prevent.
- Approval is granted for a use, not for a part number. The same converter
  approved as a bench monitor is a new request when it drives a latch, because
  the stress, the failure consequence and the screening argument all changed.
- A line missing its manufacturer, its category or its quantity is not a
  pending approval. It is an incomplete record: nobody can decide anything
  about it, and counting it as "awaiting approval" hides work that has not
  started.
- Coverage is weighted by installed quantity, because one unapproved line
  fitted forty times is a larger exposure than four unapproved lines fitted
  once, and a line-count percentage reverses that ranking.

## Workflow

1. Validate the equipment identifier the list is raised against; a blank or
   missing identifier is an input error, not a list covering everything.
2. Grade each line against the mandatory attribute set and hold the incomplete
   ones aside as records rather than as approval states.
3. Reject any line whose own equipment identifier differs from the list's, and
   report it as an orphan rather than silently dropping it.
4. Derive the approval route from the procurement category, refusing a
   category the project has not defined instead of defaulting it.
5. Disposition each complete, in-scope line: released, open, refused, missing,
   not transferable, or carrying the wrong route's state.
6. For a granted customer approval, check the equipment and the application the
   approval was granted for against the line's own before crediting it.
7. Sum the installed quantity sitting on released lines, divide by the total
   installed quantity, and compare with the release threshold, absorbing
   floating-point representation error at the boundary with a named tolerance
   rather than by lowering the threshold.
8. Report duplicate line identifiers, rank every finding by severity, and
   return a single release-or-hold verdict for the list.

## Pitfalls

- Reading a granted approval as transferable. The scope of the approval is
  part of the approval; a grant against another equipment or another
  application is evidence that a request was once made, not that this line is
  covered.
- Counting approval coverage by line. Quantity weighting is what makes the
  number track exposure; a list where the one unapproved line is fitted in
  every string scores well on a line count and badly on the measure that
  matters.
- Treating an incomplete record as a pending approval. Nothing is pending: no
  request can be raised until the attributes exist, so the two states have
  different owners and different durations.
- Accepting a project declaration on a commercial line. The routes are not
  interchangeable, and the substitution is invisible unless the route is
  derived from the procurement category rather than read from the approval
  column.
- Lowering the release threshold to close an exactly-met case. An equality at
  the limit is a representation question, handled by the tolerance inside the
  comparison; the agreed threshold stays as agreed.
- Letting a duplicate line identifier stand. Two lines sharing an identifier
  make the approval traceable to neither, and later revisions of the list
  cannot be diffed against this one.

## Behavior contract (gate 3)

The equipment scoping, attribute completeness grading, approval-route
derivation, disposition separation, approval-scope transfer check,
quantity-weighted coverage and release verdict are exercised by the gate 3
contract test:
scripts/test_q6013_class_1_declared_component_list.py against
scripts/q6013_class_1_declared_component_list_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6013_class_1_declared_component_list.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
