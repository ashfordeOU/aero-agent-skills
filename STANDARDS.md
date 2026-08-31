# AeroSkills Standards Reference (STANDARDS.md)

Human-readable companion to `standards-map.yaml` (the machine-readable
source of truth; every skill's `standards:` frontmatter entries resolve
against it). This file must agree with the map.

## The summary-not-copy rule

The only allowed way to reference any mapped standard is
**summary-not-copy**: name + paraphrase + short attributed quotes
(<100 words) + link to the publisher's official channel. Never reproduce
objective tables, appendix text, or multi-line verbatim blocks; never
include standards PDFs; never include material from illegally hosted
copies.

`gated: true` in the map means **verbatim text from that standard must
NEVER appear anywhere in this repository** — a skill that references a
gated standard must list it as `reference-only` (or carry `gated: true`).
`gated: false` means the text is quotable with attribution (paraphrase
still preferred).

The standards themselves remain the copyrighted works of their publishers
(RTCA/EUROCAE, SAE International, IAQG, EASA, FAA, ESA, the MCP working
group) and must be purchased or accessed through the publishers' official
channels. Purchase links live in `standards-map.yaml` (`purchase:`).

## Mapped standards

| id | Standard | Family | Publisher | Status | Domain | Gated |
|---|---|---|---|---|---|---|
| far-25 | 14 CFR Part 25: Airworthiness Standards for Transport Category Airplanes | regulation | FAA (US Government) | public-domain | airworthiness certification; aircraft design; systems safety (25.1309) | no |
| cs-25 | CS-25: Certification Specifications and Acceptable Means of Compliance for Large Aeroplanes | regulation | EASA | free-download | airworthiness certification; large aeroplane design | no |
| arp4754a | ARP4754A: Guidelines for Development of Civil Aircraft and Systems | guidance | SAE International | proprietary-sold | systems engineering; development assurance (FDAL/IDAL) | yes |
| arp4761a | ARP4761A: Guidelines for Conducting the Safety Assessment Process on Civil Aircraft, Systems, and Equipment | guidance | SAE International | proprietary-sold | systems safety; FHA/PSSA/SSA/CCA; DAL determination | yes |
| do-178c | DO-178C: Software Considerations in Airborne Systems and Equipment Certification | guidance | RTCA (joint EUROCAE twin ED-12C) | proprietary-sold | avionics flight software; airborne software certification | yes |
| do-254 | DO-254: Design Assurance Guidance for Airborne Electronic Hardware | guidance | RTCA (joint EUROCAE twin ED-80) | proprietary-sold | avionics hardware; complex airborne electronic hardware (AEH) | yes |
| as9100 | AS9100: Quality Management Systems: Requirements for Aviation, Space and Defense Organizations | quality | IAQG (develops) / SAE (publishes Americas; EN9100 Europe) | proprietary-sold | manufacturing and quality; QMS; production assurance | yes |
| ecss | ECSS standards series (E-ST-10C SE, E-ST-40C SW, Q-ST-80C SW assurance, M-ST-40 CM) | space | European Cooperation for Space Standardization (ESA) | free-download | space systems; spacecraft engineering and software | no |
| sep-2640 | SEP-2640: Skills-over-MCP specification (MCP working group) | open-spec | MCP Skills-over-MCP working group | open-spec | skill delivery; router interoperability; agentskills.io alignment | no |

## Applicability

| id | Applicability | Summary-not-copy detail |
|---|---|---|
| far-25 | Type-certification basis for transport-category airplanes; airframe loads and structures, systems, flight characteristics, safety assessment | US government work (17 U.S.C. 105); quotable with citation; paraphrase preferred for clarity |
| cs-25 | EASA certification basis for large aeroplanes; mirrors FAR-25 with EU amendments; AMC-25 acceptable means | Reproduction authorised provided source is acknowledged (EASA copyright notice); free PDFs; paraphrase preferred |
| arp4754a | System development process and development assurance; aircraft and systems certification coordination; FDAL/IDAL assignment; ARP4754B (2023) supersedes | Proprietary (SAE). Name + paraphrase + short attributed quotes (<100 words) + link only; no verbatim tables or sections |
| arp4761a | Safety assessment process: FHA, PSSA, SSA, CCA (ZSA/PRA/CMA), FTA/FMEA; severity-to-DAL propagation (A-E) | Proprietary (SAE). Name + paraphrase + short attributed quotes + link only; no verbatim tables or sections |
| do-178c | Software lifecycle (planning/development/verification/configuration management/airworthiness liaison); software levels A-E; coverage depth per level; objectives tables A-1..A-10; supplements DO-330/331/332/333; accepted via AC 20-115D | Proprietary (RTCA, DRM-protected, single-user license). Name + paraphrase + short attributed quotes + link only; never reproduce objective tables, appendix text, or multi-line verbatim blocks |
| do-254 | Hardware design assurance: simple vs complex AEH, PHAC, requirements capture, verification, configuration management; accepted via AC 20-152A | Proprietary (RTCA). Name + paraphrase + short attributed quotes + link only; no verbatim tables or sections |
| as9100 | QMS requirements: ISO 9001:2015 plus aerospace clauses (8.1.1 operational risk, 8.1.2 configuration mgmt, 8.1.3 product safety, 8.1.4 counterfeit prevention, 8.4.1 external providers, 8.5.1.3 special processes) | Proprietary (IAQG/SAE). Name + paraphrase + short attributed quotes + link only; no verbatim clause text |
| ecss | Space project engineering/software/quality/management standards; European space procurement baseline | Freely downloadable; copyright ESA; cite source; paraphrase preferred |
| sep-2640 | Standardizing skill representation and discovery inside MCP; emerging, not yet stable; adapter layer, never the source of truth | Open specification; quote with citation; note status (emerging, not yet stable) |

## Gated standards — verbatim text must NEVER appear

- **do-178c** (DO-178C, RTCA/EUROCAE) — gated
- **do-254** (DO-254, RTCA/EUROCAE) — gated
- **arp4754a** (ARP4754A, SAE) — gated
- **arp4761a** (ARP4761A, SAE) — gated
- **as9100** (AS9100, IAQG/SAE) — gated

## Reference-only standards — quotable with citation

- **far-25** (public domain, US government work)
- **cs-25** (EASA, attribution-only reproduction)
- **ecss** (ESA, cite source)
- **sep-2640** (open specification, cite with status note)

## Frontmatter enforcement

Gate 1 spec lint (docs/harness-contract.md) enforces per SKILL.md:
`license: Apache-2.0`, `compliance` in {none, ITAR-GATED, EAR-GATED,
STANDARDS-REF}, a non-empty `standards:` list whose entries resolve
against standards-map.yaml, `gated` as a boolean consistent with the map
(a gated standard must be listed `reference-only` unless the skill is
`gated: true`), and `metadata.version` + `metadata.author`.
