---
name: pfci-fci-flli-lists
description: "Use when document, compile, and verify the ECSS-E-ST-32C clause 6.4.2 fracture control item lists (PFCIL, FCIL, FLLIL): categorize each structural item as Potentially Fracture Critical (PFCI), Fracture Critical (FCI), or Flight Limited Life (FLLI) based on fracture sensitivity and demonstrated compliance, confirm required documentation is present for each item category, and verify that each list carries an issue number, approval date, and authorised signatory before submission to configuration control. Trigger: ecss, e-st-32-structures-scope, fracture-control, pfcil, fcil, fllil, flight-limited-life, configuration-control, fracture-critical-items."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, pfcil, fcil, fllil, flight-limited-life, configuration-control, fracture-critical-items]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — PFCIL / FCIL / FLLIL Documentation and Configuration Control (space-systems/ecss/pfci-fci-flli-lists)

Use when the task is compiling, verifying, and maintaining the fracture
control item lists required by ECSS-E-ST-32C clause 6.4.2 — the
Potentially Fracture Critical Items List (PFCIL), the Fracture Critical
Items List (FCIL), and the Flight Limited Life Items List (FLLIL) — and
placing them under configuration control.

## Domain quick reference

- Clause 6.4.2 of ECSS-E-ST-32C requires three controlled lists to be
  compiled, maintained, and submitted for approval at defined programme
  milestones. The PFCIL captures every structural item that is fracture
  sensitive and whose failure consequence is critical or catastrophic;
  the FCIL is the subset of PFCIL where fracture compliance cannot be
  demonstrated through analysis or proof test alone (safe-life ratio
  below 4.0); the FLLIL is the subset of FCIL where a specific life
  limit is assigned and the item must be retired or replaced before that
  limit is reached.
- An item enters the PFCIL through a screening step: if its material is
  fracture sensitive (low fracture toughness, pre-existing flaw
  sensitivity) and its failure consequence is critical or catastrophic,
  it is placed on the PFCIL. Items whose failure consequence is
  non-critical are exempt from all three lists.
- An item on the PFCIL escalates to the FCIL if the fracture control
  analysis or proof test cannot demonstrate a safe-life ratio of at
  least 4.0 (safe life divided by design life). Items that achieve
  the required ratio remain on the PFCIL as compliant and do not
  escalate further.
- An item on the FCIL receives a life limit when crack growth analysis
  yields a finite safe life shorter than the design life; that item
  then moves to the FLLIL and requires a defined replacement or
  retirement plan with a stated life limit in cycles or flight hours.
- Each list must carry an issue number, an approval date, and the name
  of the authorised signatory. Items added to or removed from a list
  require documented justification; removal without justification is a
  configuration control finding.

## Workflow

1. Screen every primary and secondary structural item for fracture
   sensitivity (material fracture toughness, flaw sensitivity, stress
   concentration) and failure consequence (catastrophic, critical, or
   non-critical). Items with non-critical failure consequence are exempt
   and excluded from all three lists. Place all remaining items on the
   PFCIL with an entry recording the basis for their fracture-sensitive
   designation.
2. For each item on the PFCIL, evaluate the fracture control compliance
   method: analyse using fracture mechanics (crack growth from the
   initial assumed flaw under the full load spectrum) or perform a
   proof test. Compute the safe-life ratio (demonstrated safe life
   divided by design life). An item achieving a ratio of 4.0 or greater
   is compliant and stays on the PFCIL without further escalation; an
   item below 4.0 escalates to the FCIL.
3. For each item on the FCIL, determine whether a finite life limit can
   be derived from the crack growth analysis. If a life limit is
   defined, move the item to the FLLIL and record the life limit in
   cycles or flight hours; define the replacement or retirement plan.
   Items on the FCIL without a life limit remain pending a compliance
   demonstration or design change.
4. Verify documentation for each item's category against the required
   document set: PFCIL items need a screening record and a fracture
   sensitivity justification; FCIL items additionally need a fracture
   control analysis, an initial flaw assumption, and an inspection
   plan; FLLIL items additionally need a life-limit calculation and a
   replacement or retirement plan. Flag every missing document before
   the list is submitted.
5. Verify each list at the list level: confirm an issue number, an
   approval date, and an authorised signatory are recorded. Confirm
   that any item removed since the previous issue has a removal
   justification on file. Confirm there are no duplicate item
   identifiers within a list.
6. Deliver the three lists to the programme configuration control
   board together with the per-item documentation evidence package.
   The lists are compliant when all documentation findings are
   resolved and all list-level configuration control findings are
   cleared.

## Pitfalls

- Treating the PFCIL as a pass/fail verdict rather than a mandatory
  screening list — every fracture-sensitive item with critical failure
  consequence must appear on it regardless of whether compliance is
  later demonstrated; an empty or minimal PFCIL almost always means
  the screening was incomplete.
- Stopping at the PFCIL when items have not yet completed the
  compliance step — items with no analysis or proof test on record
  must stay on the PFCIL as pending, not be removed as "no concern".
- Confusing the FCIL and the FLLIL: an item with a defined life limit
  belongs on the FLLIL rather than the FCIL; failure to make this
  distinction misrepresents the programme's fracture risk profile.
- Accepting a list without an issue number or approval date as "draft
  acceptable" — unsigned, unissued lists are not under configuration
  control and cannot serve as the programme fracture control record.
- Removing an item from a list without a formal justification and
  approval — undocumented removals break the traceability chain and
  are treated as findings in any independent review or audit.

## Behavior contract (gate 3)

The item categorization, list compilation, documentation check, and
configuration control check logic is exercised by the gate 3 contract
test: scripts/test_pfci_fci_flli_lists.py against
scripts/pfci_fci_flli_lists_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_pfci_fci_flli_lists.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
