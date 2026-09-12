---
name: drd-mass-summary
description: "Use when produce a structure mass summary (SMS) document per ECSS-E-ST-32C Annex N: enumerate every structural component with its dry mass and design maturity code, apply the maturity-dependent margin to each entry to obtain the component mass-with-margin, sum the contributions to derive total dry mass and total mass-with-margin, compare the total against the allocated mass budget, and flag any component missing a recognized maturity code or a valid mass value. Trigger: ecss, e-st-32-structures-scope, mass-summary, sms, dry-mass, mass-margin, maturity-code, drd, mass-budget."
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
  tags: [ecss, e-st-32-structures-scope, mass-summary, sms, dry-mass, mass-margin, maturity-code, drd, mass-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Structure Mass Summary Document (space-systems/ecss/drd-mass-summary)

Use when the task is to produce the Structure Mass Summary (SMS) document
for a space structure per ECSS-E-ST-32C Annex N -- enumerating all
structural components, assigning design maturity codes, applying
maturity-dependent mass margins, and comparing the total mass-with-margin
against the allocated budget.

## Domain quick reference

- The **dry mass** of a component is the mass value at the time of
  assessment, without any margin applied. It is measured, computed, or
  estimated depending on the design stage.
- The **design maturity code** indicates the confidence level in the dry
  mass value and determines the minimum margin fraction to apply. Five
  levels are recognized: A (actual measured mass, lowest margin),
  B (mass from detailed design drawing), C (mass from preliminary design),
  D (mass estimated from analysis), and E (mass estimated from similarity
  or analogy, highest margin). Each code maps to a minimum margin fraction
  that must be applied before the component enters the budget comparison.
- The **mass-with-margin** for a component is
  dry_mass × (1 + margin_fraction). The margin covers growth uncertainty
  inherent at the assessed maturity level.
- The **total mass-with-margin** is the sum of all component
  masses-with-margin in the SMS document. This is the figure compared
  against the allocated mass budget to determine whether the structure
  meets its mass requirement.
- The **allocated mass budget** is the maximum total mass-with-margin
  the structure is permitted to reach, derived from the system-level mass
  allocation and linked to ECSS-E-ST-32C Annex N requirements.

## Workflow

1. Inventory every structural component in the design (panels, brackets,
   fittings, fasteners, adhesive, inserts, and any other mass-bearing
   item) and assign each a unique component identifier.
2. Assign a design maturity code (A–E) to each component reflecting the
   current confidence level in its dry mass value. Reject any entry whose
   maturity code is not in the recognized set before proceeding; an
   unrecognized code must be reconciled with the project mass-management
   plan before the entry can be accepted.
3. Record the dry mass for each component. A component without a dry mass
   value is incomplete; flag it as a finding and do not carry it into the
   margin calculation.
4. Apply the maturity-dependent margin to each component:
   mass_with_margin = dry_mass × (1 + margin_fraction), where
   margin_fraction is at least the minimum value for the assigned maturity
   code. A custom margin fraction below the maturity-code minimum is
   itself a finding.
5. Sum all component dry masses to form the total dry mass, and sum all
   component masses-with-margin to form the total mass-with-margin.
6. If an allocated mass budget is provided, compare the total
   mass-with-margin against it. Flag a budget exceedance. Also flag when
   no budget has been set, as this means the mass requirement has not been
   captured.
7. Check for duplicate component identifiers across the document; a
   duplicate ID makes the SMS ambiguous and is a document-level finding.
8. Aggregate all per-component and document-level findings. The SMS is
   not accepted until every finding is resolved.

## Pitfalls

- Comparing dry mass directly against the budget instead of total
  mass-with-margin -- the margin covers growth uncertainty, and omitting
  it understates the predicted end-of-design mass, which can lead to
  late-programme budget violations.
- Applying a lower margin fraction than the maturity-code minimum -- the
  minimum margin is set to cover statistical scatter in mass estimates at
  that design stage; reducing it without justification produces an
  optimistic SMS that understates real growth risk.
- Treating a component with an unrecognized maturity code as maturity A
  by default -- an unknown code means the design stage has not been mapped
  to the project mass-management framework, and defaulting to the smallest
  margin suppresses the actual uncertainty.
- Leaving the allocated mass budget unset and reading zero findings as
  compliant -- an unset budget means the structural mass requirement was
  never captured, which is itself a finding, not a pass.
- Carrying duplicate component IDs into the SMS -- if two entries share
  an ID it is impossible to trace a mass growth event back to the correct
  component unambiguously.

## Behavior contract (gate 3)

The maturity-code taxonomy, mass-with-margin computation, minimum-margin
enforcement, budget comparison, missing-field detection, and duplicate-ID
check are exercised by the gate 3 contract test:
scripts/test_drd_mass_summary.py against
scripts/drd_mass_summary_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_drd_mass_summary.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
