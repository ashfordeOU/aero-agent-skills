---
name: ballooning
description: "Use when you must balloon the characteristics of an engineering drawing for an AS9102 first article inspection: assign sequential balloon numbers to every characteristic, map each verification method label to the AS9102 method code (measuring, attribute, functional, visual, analytical), classify each characteristic as key, critical, or standard, and reconcile the balloon count against the form 3 line items and the D-list accountability matrix. Produce the numbered characteristic list, the method code column, and the accountability verdict that feed the FAI characteristic accountability form. Trigger: ballooning, characteristic numbering, balloon number, D-list, accountability matrix, verification method code, drawing characteristics."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9102
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9102
  tags: [ballooning, balloon-number, characteristic-numbering, d-list, accountability-matrix, verification-method-code, as9102, fai, drawing-characteristics]
  version: 0.1.0
  author: AeroSkills
---

# Drawing Characteristic Ballooning (manufacturing-quality/as9102/ballooning)

Use when the task is ballooning the characteristics of an engineering
drawing for an AS9102 first article inspection: unique balloon
numbers, the D-list accountability matrix, and the verification method
codes that feed form 3 characteristic accountability.

## Domain quick reference

- Ballooning marks every design characteristic on the drawing with a
  unique balloon number; the same number appears on the D-list (the
  accountability matrix that ties each balloon to its characteristic,
  method, and classification) and on form 3 characteristic
  accountability.
- The verification method code maps how each characteristic is
  verified against the design definition (AS9102 method codes,
  summarized):
  - 1 = measuring / variable: a measured value compared with the
    tolerance.
  - 2 = attribute / go-no-go: a pass-fail check, typically with a
    gauge or fixture.
  - 3 = functional: a functional or operational test of the article.
  - 4 = visual: an inspection by eye, with or without magnification.
  - 5 = analytical: an analysis such as a calculation or simulation
    instead of a direct measurement.
- Characteristic classification follows the design definition: key
  characteristic (flagged by the customer or design authority as
  safety or fit/function critical), critical characteristic (safety
  or regulatory critical), or standard (all other characteristics).
- Every ballooned characteristic needs a method code and a
  classification; a balloon without either makes the accountability
  matrix incomplete.
- The balloon count must reconcile with form 3: the number of
  ballooned characteristics equals the form 3 line items, otherwise
  the characteristic accountability is not complete.

## Workflow

1. Collect the drawing characteristics to balloon (identifier, kind,
   and verification method label).
2. Assign unique sequential balloon numbers with
   assign_balloon_numbers(characteristics), starting at 1 in drawing
   order.
3. Map every method label to its AS9102 code with
   verification_method_code(method_label).
4. Classify every characteristic with classify_characteristic(kind) as
   key characteristic, critical characteristic, or standard.
5. Build the D-list accountability matrix and verify it with
   accountability_matrix_verdict(balloons): every balloon must carry a
   valid method and classification.
6. Reconcile the balloon count against the form 3 line items with
   balloon_count_reconciliation(balloon_count, form_line_items) and
   resolve any mismatch before the FAI is accepted.

## Pitfalls

- Numbering by hand out of drawing order: assign_balloon_numbers
  returns one sequential number per characteristic and rejects
  duplicates, so the matrix stays traceable to the drawing.
- Duplicating a balloon number across two characteristics: each
  balloon number must be unique; a duplicate breaks the D-list to form
  3 trace.
- Writing a method code from memory: the code is 1 to 5 (measuring,
  attribute, functional, visual, analytical); an unknown label raises
  ValueError instead of silently passing.
- Leaving a balloon without a method or classification: the
  accountability matrix is incomplete until every balloon has both.
- Signing off form 3 with a balloon count that differs from the line
  items: the reconciliation verdict must be a match.
- Copying AS9102 text into the D-list template: the standard is
  proprietary, so the matrix wording is the organization's own
  paraphrase.

## Behavior contract (gate 3)

The ballooning logic is exercised by the gate 3 contract test:
scripts/test_ballooning.py against scripts/ballooning.py (stdlib
unittest, offline). Run:
python3 scripts/test_ballooning.py

## Compliance

- Standards referenced, not reproduced: AS9102 text is proprietary
  (IAQG/SAE); the method codes and workflow above are a summary-only
  paraphrase per standards-map.yaml and brief 06.
- compliance: STANDARDS-REF, gated: false.
