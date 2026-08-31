# AeroSkills glossary

Terms as used in this repository. Sources: standards-map.yaml,
STANDARDS.md, docs/harness-contract.md, and the seed skill
skills/avionics/do178c/planning/SKILL.md.

## DAL (Development Assurance Level), A-E

The level of rigor applied to an airborne function or item, driven by
the severity of the worst failure condition. A = Catastrophic,
B = Hazardous, C = Major, D = Minor, E = No safety effect. Coverage
depth scales with level: A requires MC/DC, B requires decision
coverage, C requires statement coverage, D and E require none.
Source: seed skill domain quick reference; standards-map.yaml
(arp4761a, do-178c).

## FDAL and IDAL

ARP4754A terms. FDAL (function development assurance level) is
assigned to functions; IDAL (item development assurance level) is
assigned to items. An item's IDAL is the highest FDAL among the
functions it implements. Source: seed skill; standards-map.yaml
(arp4754a).

## DO-178C

Software Considerations in Airborne Systems and Equipment
Certification. RTCA guidance, jointly published as EUROCAE ED-12C,
for the software lifecycle: planning, development, verification,
configuration management, airworthiness liaison. Defines software
levels A-E and an objectives-based process. Accepted via FAA AC
20-115D. Gated standard: summary-only referencing. Source:
standards-map.yaml (do-178c).

## DO-254

Design Assurance Guidance for Airborne Electronic Hardware. RTCA
guidance (EUROCAE twin ED-80) for simple versus complex airborne
electronic hardware, requirements capture, verification, and
configuration management. Accepted via FAA AC 20-152A. Gated
standard: summary-only referencing. Source: standards-map.yaml
(do-254).

## ARP4754A

Guidelines for Development of Civil Aircraft and Systems. SAE
International guidance for the system development process and
development assurance, including FDAL/IDAL assignment. ARP4754B
(2023) supersedes it. Gated standard: summary-only referencing.
Source: standards-map.yaml (arp4754a).

## ARP4761A

Guidelines for Conducting the Safety Assessment Process on Civil
Aircraft, Systems, and Equipment. SAE International guidance for the
safety assessment process: FHA, PSSA, SSA, CCA (ZSA/PRA/CMA), FTA,
FMEA; severity-to-DAL propagation. Gated standard: summary-only
referencing. Source: standards-map.yaml (arp4761a).

## AS9100

Quality Management Systems: Requirements for Aviation, Space and
Defense Organizations. Developed by IAQG, published by SAE in the
Americas (EN9100 in Europe). ISO 9001:2015 plus aerospace clauses
covering operational risk, configuration management, product safety,
counterfeit prevention, external providers, and special processes.
Gated standard: summary-only referencing. Source: standards-map.yaml
(as9100).

## V&V

Verification and validation. Verification checks that the product
meets its requirements; validation checks that the requirements meet
the need. Both are lifecycle activities in the mapped standards,
with verification depth scaled to the development assurance level.
Source: standards-map.yaml (do-178c, arp4754a); seed skill workflow.

## PSSA and SSA

Safety assessment activities from ARP4761A. FHA (functional hazard
assessment) identifies failure conditions and severities; PSSA
(preliminary system safety assessment) shows the proposed architecture
meets safety requirements; SSA (system safety assessment) confirms
the implemented system does. Source: standards-map.yaml (arp4761a).

## Trace matrix

The mapping that connects each requirement across levels: system to
item, item to software or hardware, and down to the tests that verify
it. The seed skill lists traceability gaps as a pitfall; the mapped
standards require the matrix as evidence. Source: seed skill pitfalls;
standards-map.yaml (do-178c, arp4754a).

## Compliance hook

The point in a skill where the workflow must stop and check against a
standard or regulation before producing a number: a DAL-level
awareness note, a coverage margin, an export-control verify-before-use
step. Compliance hooks are why a skill output is usable as evidence
rather than as an unverifiable claim. Source: research/briefs/11 §1.2;
research/briefs/06 §8.1.

## Gated standard

A standard whose map entry sets gated: true, meaning verbatim text
from it must never appear anywhere in this repository. Skills that
reference a gated standard list it as reference-only. DO-178C,
DO-254, ARP4754A, ARP4761A, and AS9100 are gated; FAR-25, CS-25,
ECSS, and SEP-2640 are quotable with attribution. Source:
STANDARDS.md; standards-map.yaml.

## Hit@1

Router quality metric from the eval harness: the fraction of corpus
tasks where the expected skill is the top-1 retrieval result. Gate 5
requires 3/3 pinned tasks to resolve to the expected skill using the
deterministic offline router. Source: docs/harness-contract.md
(gate 5).
