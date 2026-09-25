---
name: q80-software-security-assurance
description: "Assess software security assurance under ECSS-Q-ST-80C Rev.2, the transversal security-sensitivity dimension that Revision 2 added beside the criticality category: decide which components are security sensitive from their confidentiality, integrity and availability impacts, list the security clauses that apply, including those that return for category D, spread sensitivity over links without segregation and flag criticality versus sensitivity conflicts, check the extra measures chosen for sensitive software, decide regression or further verification after a change, and check the review board and the supplier security package. Use when a software security analysis or security management plan is prepared or audited. Trigger: security-sensitive-software, software-security-analysis, security-sensitivity, q80-security-assurance, security-regression-trigger, fuzzing-penetration-testing."
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
  tags: [ecss, q-st-80c, q80-software-security-assurance, q80-security-assurance, security-sensitive-software, software-security-analysis, security-sensitivity, security-regression-trigger, fuzzing-penetration-testing]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Software Security Assurance (space-systems/ecss/q80-software-security-assurance)

Use when the task is the security side of ECSS-Q-ST-80C Rev.2 (30 April
2025). Revision 2 added a software security analysis (clause 6.2.9) and
rules for handling security sensitive software (clause 6.2.10), and
threaded security through the review board, supplier control, integrity
protection and existing software. In the tailoring annex those clauses do
not follow the category letters; they apply according to the security
assurance and sensitivity levels. This skill works that second dimension;
the category itself belongs to `q80-software-criticality-tailoring`.

## Domain quick reference

- Sensitivity is set by the security analysis, from the system analysis
  down to components, and is re-confirmed at each milestone. The scale and
  the threshold come from the project and the security engineering
  standard it calls up; agree them with the customer before grading.
- Security is independent of criticality. A category D ground tool that
  holds keys can be highly sensitive; for such software the review of
  coding standards against security needs and the agreed test coverage
  goals come back even at category D.
- Failures can cross component boundaries by accident or by deliberate
  action. Segregation, partitioning or fail-secure isolation is what stops
  them; where nothing stops them, sensitivity spreads.
- Where one component is more critical and its neighbour more sensitive,
  the security effect of the first failing and the safety effect of the
  second failing are both analysed and any conflict is resolved.
- Sensitive software gets measures on top of the critical-software ones:
  secure coding rules, a security baseline, fuzzing, static and dynamic
  security testing, vulnerability assessment, penetration testing. Each is
  chosen, justified and shown applied.
- Regression testing is owed after a change in platform function, in the
  tools that build the executable, or in the security of the operating
  environment; a binary comparison can cover a minor tool change. Other
  changes, including new knowledge of threats, trigger an analysis of
  whether more verification is needed.
- A nonconformance with a possible security impact needs a software
  security representative on the review board.

## Workflow

1. Take the component impacts from the security analysis and run
   `determine_sensitivity` with the agreed threshold.
2. Run `sensitivity_clauses` for the product to get the clause list, and
   merge it into the tailoring matrix.
3. Model the component links and run `propagate_sensitivity`; open an
   analysis action for every conflict it reports.
4. Grade the measures in the security management plan with
   `check_security_measures`.
5. For each change since the last baseline, call `change_impact` and plan
   the regression run or the analysis it asks for.
6. Check open nonconformances with `check_board_security` and each
   supplier package with `check_supplier_security_package`.
7. Hand the results to the reviewer as a draft.

## Pitfalls

- Reading category D as "no security work". Sensitivity switches work back
  on regardless of the category letter.
- Setting sensitivity once at the preliminary design review and never
  revisiting it after new vulnerabilities are published.
- Listing fuzzing or penetration testing in the plan with no report behind
  them.
- Treating a compiler patch as harmless without either a regression run or
  a recorded binary comparison.
- Sending suppliers the category but not the sensitivity and the attack
  scenarios their product sits in.

## Stop gate: human sign-off required

The agent drafts; it does not decide. Stop and hand the draft to a named
human before any of these leave the working folder:

- A sensitivity level or the threshold behind it.
- A decision that a change needs no regression run.
- The software security analysis report, the security management plan or
  a nonconformance disposition with a security impact.

Mark every such output as a draft, list the open questions for the
reviewer, and end with the line: STOP: human sign-off required before
submission.

## Behavior contract (gate 3)

The sensitivity decision, the sensitivity clause list with the category D
returns, the propagation and conflict check, the measure grading, the
change impact rules and the board and supplier package checks are
exercised by the gate 3 contract test:
scripts/test_q80_software_security_assurance.py against
scripts/q80_software_security_assurance_logic.py (stdlib unittest,
offline).
Run: python3 scripts/test_q80_software_security_assurance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite ECSS-Q-ST-80C Rev.2
  (30 April 2025) as the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
