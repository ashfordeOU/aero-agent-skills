---
name: export-control-awareness
description: "Use when an aerospace engineer or agent must decide whether an item, data set, or task is export controlled under ITAR or EAR: it produces an export control assessment, screens restricted topics for red flags (turbine blade alloys, gas turbine engines, guidance systems for missiles, propulsion, sensors, avionics, spacecraft), and returns a verdict class (defense article, dual-use, public domain, not controlled) with handling guidance including deemed export checks for foreign collaborators. Trigger: ITAR, EAR, USML, EAR99, 600-series, defense articles, technical data, export control, deemed export, fundamental research, public domain, compliance review, sharing data with foreign collaborators."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: itar-ear
    reference-only: true
gated: false
domain: cross-cutting
pack: export-control
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: export-control
  tags: [export-control, export, control, itar, ear, usml, ear99, defense-articles, technical-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# Export Control Awareness (cross-cutting/export-control/export-control-awareness)

Use when an aerospace engineering task touches data or items that may be
export controlled: sharing a specification with a foreign collaborator,
publishing a report, releasing design data to a vendor, or starting work
on propulsion, guidance, sensor, or materials topics. The skill screens
the topic for red flags and returns a conservative verdict class with
handling guidance. It is a screening aid, not a legal opinion: every
verdict must be confirmed by the organization's trade compliance office
before any release of controlled data.

## Domain quick reference

- Jurisdiction split: items described by the US Munitions List (USML,
  22 CFR part 121) are defense articles under ITAR. Items under EAR
  jurisdiction are described by the Commerce Control List (CCL,
  15 CFR 774) or fall to EAR99, the default for items not elsewhere
  specified.
- USML categories that matter for aerospace: IV (launch vehicles,
  guided missiles, ballistic missiles, rockets, torpedoes, bombs and
  mines), VIII (aircraft and related articles), XII (fire control,
  laser, imaging and guidance equipment), XIII (materials), XV
  (spacecraft and related articles), XVIII (directed energy weapons),
  plus the catch-alls XVII and XXI. Category XIX is reserved.
- EAR 600-series: export control reform moved most defense articles
  from the USML to 600-series ECCNs. Aerospace examples: 9A610
  (military aircraft), 9A619 (military gas turbine engines), 9D610 and
  9E610 (software and technology for those), 8A609 (marine gas turbine
  engines), 0A606 (military ground vehicles). Verify each ECCN against
  the current regulation.
- EAR99: the default classification for items with no CCL entry. EAR99
  is not a free pass: end-use and end-user screening still applies, and
  supporting a restricted end use or end user is prohibited.
- Technical data (ITAR): information required for the design,
  development, production, manufacture, assembly, operation, repair,
  testing, maintenance, or modification of defense articles, including
  blueprints, drawings, photographs, plans, and instructions. General
  scientific and mathematical principles commonly taught, and public
  domain information, are excluded.
- Public domain (ITAR 22 CFR 120.34, EAR 15 CFR 734.7 through 734.8):
  information published and sold without restriction, published patents,
  unlimited-distribution conference material, and fundamental research
  results. The fundamental research exclusion is lost when the research
  agreement restricts publication or sharing.
- Deemed export: releasing technical data or technology to a foreign
  person inside the US is treated as an export to their country of
  nationality and may require authorization.
- Red-flag topics (screened by flag_restricted_topic): turbine blade
  alloys and high-temperature materials, propulsion technology,
  missiles and rockets, controlled sensors and seekers, avionics and
  navigation, low-observable design, spacecraft, unmanned aerial
  systems, radiation-hardened electronics, cryptographic items,
  hypersonics, directed energy, specialty composites, energetic
  materials, fire control, military aircraft and engines, and defense
  services. A red flag means stop and verify, not "controlled".

## Workflow

1. Describe the item or data set in one free-text string: what it is,
   what it is made of, and what it does.
2. Screen the topic: `flag_restricted_topic(item)` returns matched red
   flags with reasons. Any hit is a stop-and-verify signal.
3. Establish the information basis: `is_public_domain(source=...)` with
   source one of published, textbook, patent, conference,
   fundamental-research, unpublished. Pass `restricted_agreement=True`
   when a research agreement restricts publication or sharing.
4. Run the tree: `export_decision_tree(item, audience, purpose, ...)`
   with audience one of us-person, foreign-person, public, and purpose
   one of internal-engineering, sharing, publication, teaching,
   fundamental-research, procurement, foreign-release. The verdict is
   defense-article, dual-use, public-domain, or not-controlled, with
   jurisdiction, risk, red flags, and actions.
5. Follow the actions and escalate: never release controlled data
   without authorization, and never mark anything as compliant on your
   own authority.

All functions validate their inputs and raise ValueError on unknown
audience, purpose, source, or USML category values.

## Worked example

An engineer wants to share a single-crystal turbine blade alloy
specification with a foreign collaborator.

```python
from export_control_logic import export_decision_tree, flag_restricted_topic

item = "single crystal turbine blade alloy for the high pressure turbine"
print(flag_restricted_topic(item))
result = export_decision_tree(
    item=item,
    audience="foreign-person",
    purpose="sharing",
    ear_600_series=True,
)
print(result["verdict"], result["jurisdiction"], result["risk"])
```

Output: the topic flags "turbine blade alloys and high-temperature
materials", and the tree returns verdict `dual-use`, jurisdiction `EAR`,
risk `medium`, with a deemed export action: releasing the data to a
foreign person inside the US is a deemed export to their country of
nationality, so authorization is required before sharing.

A second example: a lift coefficient formula from a published textbook
classifies as `public-domain` (`is_public_domain(source="textbook")`
returns True), because published textbooks are public domain information.

## Pitfalls

- Treating a red-flag topic hit as a verdict: flag_restricted_topic is
  a stop-and-verify signal, not an automatic denial, and a clean topic
  screen does not by itself clear a release.
- Marking anything as compliant on your own authority: the tree returns
  jurisdiction, risk, and actions, but releasing controlled data still
  requires authorization, and only the compliance office can certify
  anything.
- Forgetting the deemed export rule: sharing technical data with a
  foreign person inside the US is a release to their country of
  nationality and needs the same authorization as an export.
- Assuming "published" implies public domain: only the listed sources
  (published, textbook, patent, conference, fundamental-research)
  classify as public domain, and unpublished results under a restricted
  research agreement do not.
- Passing unknown audience, purpose, source, or USML category values:
  the functions raise ValueError, so mis-typed inputs fail loudly
  instead of defaulting to a permissive verdict.
- Skipping the handling checklist before a release: the checklist in
  assets/export-handling-checklist.md must be worked through and the
  verdict confirmed by the trade compliance office first.

## Verification checklist

Use the handling checklist in assets/export-handling-checklist.md and
verify before committing any release:

- [ ] Topic screened with `flag_restricted_topic`, red flags recorded.
- [ ] Public domain basis checked with `is_public_domain`; restricted
      agreement status confirmed with the research office.
- [ ] Decision tree run with the real audience and purpose; verdict,
      jurisdiction, and risk recorded.
- [ ] Foreign-person releases checked for deemed export implications.
- [ ] Verdict confirmed by the trade compliance office before release.
- [ ] No controlled data exported or shared without authorization.
- [ ] Nothing marked or represented as compliant or certified except by
      the compliance office.

## Scripts and references

- scripts/export_control_logic.py - pure Python logic module:
  `classify_export_status()`, `is_defense_article()`,
  `is_public_domain()`, `flag_restricted_topic()`,
  `export_decision_tree()`.
- scripts/test_export_control.py - offline contract test (stdlib
  unittest, deterministic): turbine blade alloy topics return a
  restricted red flag, published textbook formulas classify as
  public-domain, and invalid inputs raise ValueError. Run with
  `python3 scripts/test_export_control.py`.
- references/itar-ear-overview.md - regulatory overview: USML category
  table, EAR 600-series examples, technical data and public domain
  definitions, fundamental research exclusion, deemed exports, and the
  red-flag topic table with citations.

## Related skills

- cross-cutting/documentation/engineering-report - report writing that
  must carry export control review records.
- cross-cutting/documentation/engineering-margins - engineering margin
  analyses whose results may be technical data.
- cross-cutting/data-sources/aeronautical-data-sources - sourcing
  aeronautical data, some of which is restricted.

## Behavior contract (gate 3)

The export-classification logic (topic red flags, public-domain basis,
and the export decision tree) is exercised by the gate 3 contract test:
scripts/test_export_control.py against scripts/export_control_logic.py
(stdlib unittest, offline). Run:

python3 scripts/test_export_control.py
