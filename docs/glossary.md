# Aero Agent Skills glossary

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

## DO-330

Software Tool Qualification Considerations. RTCA guidance (EUROCAE
twin ED-215) for qualifying the software tools used in airborne
software and hardware programs: tool criteria 1-5, tool qualification
levels TQL-1..TQL-5, and tool operational requirements. Referenced by
DO-178C; accepted via FAA AC 20-115D. Gated standard: summary-only
referencing. Source: standards-map.yaml (do-330).

## DO-160G

Environmental Conditions and Test Procedures for Airborne Equipment.
RTCA guidance (EUROCAE twin ED-14G) covering environmental test
procedures for airborne equipment: temperature, altitude, humidity,
vibration, EMC, lightning, and other equipment categories and test
conditions. Gated standard: summary-only referencing. Source:
standards-map.yaml (do-160).

## AS9102

Aerospace First Article Inspection Requirements. Developed by IAQG,
published by SAE in the Americas (EN9102 in Europe). Defines the
first article inspection process: Form 1 part accountability, Form 2
material and special processes, Form 3 characteristic accountability,
and delta or partial FAI after changes. Gated standard: summary-only
referencing. Source: standards-map.yaml (as9102).

## MMPDS

Metallic Materials Properties Development and Standardization. SAE
publication, successor to the public-domain MIL-HDBK-5. Statistically
based metallic material design allowables: A-basis (95% confidence,
99% content) and B-basis (95% confidence, 90% content) with
k-factors, plus fastener and joint allowables. Gated standard:
summary-only referencing. Source: standards-map.yaml (mmpsd).

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
rather than as an unverifiable claim. Source: internal research
(compliance-hook doctrine).

## Gated standard

A standard whose map entry sets gated: true, meaning verbatim text
from it must never appear anywhere in this repository. Skills that
reference a gated standard list it as reference-only. DO-178C,
DO-254, ARP4754A, ARP4761A, AS9100, DO-330, DO-160G, AS9102, and
MMPDS are gated; FAR-25, CS-25, ECSS, SEP-2640, and NACA TR-824 are
quotable with attribution. Source: STANDARDS.md; standards-map.yaml.

## Hit@1

Router quality metric from the eval harness: the fraction of corpus
tasks where the expected skill is the top-1 retrieval result. Gate 5
requires all active tasks to resolve to the expected skill using the
deterministic offline router; the corpus carries 66 routed evaluation
tasks across the 27 published skills (58 domain tasks + 8 adversarial
cross-pair tasks). Source: docs/harness-contract.md (gate 5).

## Derived requirement

A requirement added during software or system development (a design
decision, or output of safety analysis) that has no direct higher-level
requirement source. DO-178C requires derived requirements to be
identified and justified; an unidentified derived item shows up as a
silent orphan in the trace matrix. Source: standards-map.yaml
(do-178c); skills/avionics/do178c/development.

## Configuration baseline

A frozen, consistent set of software lifecycle data against which
changes are controlled. DO-178C configuration management records
problem reports, controls changes to baselined data (independent
approval at levels A and B), and maintains archive/recovery; release
requires closed problem reports, a current baseline, and an archive
capability. Source: standards-map.yaml (do-178c);
skills/avionics/do178c/configuration-management.

## Simple and complex AEH

DO-254 classification of airborne electronic hardware. Complex AEH
(programmable logic, processors, significant internal state, or
hardware whose correct behavior cannot be fully established from
top-level data alone) follows the full design assurance process
(PHAC through verification); simple AEH uses a reduced but still
planned process. Safety-significant items are treated as complex
unless a documented justification shows otherwise. Source:
standards-map.yaml (do-254); skills/avionics/do254/hardware-planning.

## PHAC

Plan for Hardware Aspects of Certification, the DO-254 planning
artifact for complex airborne electronic hardware, covering
requirements capture, design, verification, configuration management,
and process assurance. Source: standards-map.yaml (do-254);
skills/avionics/do254/hardware-planning.

## ECSS

European Cooperation for Space Standardization standards series, the
European space procurement baseline. Includes E-ST-10C (systems
engineering), E-ST-40C (software engineering), Q-ST-80C (software
product assurance), and M-ST-40 (configuration management). Freely
downloadable with ESA copyright; cite source and paraphrase.
Source: standards-map.yaml (ecss).

## Software criticality (ECSS)

ECSS-E-ST-40C classification of space software by the consequences of
failure: A = loss of life or total loss of mission, B = major mission
degradation, C = minor degradation, D = negligible effects. Assurance
and verification rigor scale with the category; heritage reuse
demands a heritage assessment with full original verification
evidence at categories A/B. Source: standards-map.yaml (ecss);
skills/space-systems/ecss/software-engineering.

## SEP-2640

The MCP working group's Skills Extension specification (Skills over
MCP): skills are served as resources: skill:// URIs, resources/read,
and directory listing behind the directoryRead capability. An
emerging draft, not yet stable; an adapter layer over the
agentskills.io SKILL.md format, never the source of truth. Open
specification, quotable with citation. Source: standards-map.yaml
(sep-2640); skills/cross-cutting/sep2640/skill-delivery.

## NACA TR-824

Summary of Airfoil Data (Abbott, von Doenhoff, Stivers). NACA report;
US government work, public domain. Classic airfoil section data
(NACA 4/5-digit and 6-series) and wind-tunnel polars used as the
validation anchor for airfoil analysis, e.g. the XFOIL NACA 0012 at
Re=6M band. Quotable with attribution. Source: standards-map.yaml
(naca-tr-824).

## Certification basis

The set of regulations, amendments, and special conditions a type
certification program must show compliance with. For transport
category: 14 CFR Part 25 (FAR-25) under FAA, CS-25 under EASA; the
basis is negotiated with the certification authority and includes
program-specific amendments and special conditions. Source:
standards-map.yaml (far-25, cs-25);
skills/avionics/far-cs25/airworthiness.

## Means of compliance

The accepted way of demonstrating that a requirement is met:
analysis, test (ground and flight), inspection, similarity, and
certification-program demonstrations. Agreed with the certification
authority per area. Source: standards-map.yaml (cs-25);
skills/avionics/far-cs25/airworthiness.

## Model-based systems engineering (MBSE)

A way of executing systems engineering with models as the primary
artifacts: requirements modeled against functional and logical
architectures, functions allocated to design elements, analysis run
on the architecture, and traceability linking requirements through
design to verification (the digital thread). Toolchains include
Capella, OSATE/AADL, and Papyrus. Source:
skills/systems-engineering-safety/mbse/systems-engineering; standards-map.yaml (arp4754a).
