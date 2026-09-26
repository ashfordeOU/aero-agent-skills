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
clauses:
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.1
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.2
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.3
    items: [a, b]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.4
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.5
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.6
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.9.7
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.10.1
    items: [a, b]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.10.2
    items: [a]
    relation: verifies
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.10.3
    items: [a]
    relation: implements
  - standard: ECSS-Q-ST-80C Rev.2
    clause: 6.2.10.4
    items: [a]
    relation: implements
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

1. Open the software product assurance plan (SPAP) and confirm it has a
   security assurance part, in its own section or by reference to the
   security management plan. A plan that says nothing about security
   assurance is the first finding, raised before anything is graded.
2. Settle how the software security analysis will be done before doing it:
   name the techniques (for example security requirements analysis, risk
   analysis, design review, code analysis), the sensitivity scale and the
   threshold, and record the customer's agreement to them. Techniques the
   customer has not agreed are proposals, not the method.
3. Start from the system-level security analysis the software belongs to.
   Take each component's confidentiality, integrity and availability impact
   from it and run `determine_sensitivity` with the agreed threshold. The
   sensitivity it returns per component is the core result of the software
   security analysis.
4. Run `sensitivity_clauses` for the product to get the clause list, and
   merge it into the tailoring matrix.
5. Model the component links and run `propagate_sensitivity`. For every
   link a failure can cross, whether it is accidental or provoked by an
   attacker, write down the segregation, partitioning or fail-secure
   isolation that stops it, and check that the measure is built, not only
   drawn. For every conflict the propagation reports, where one component
   is the more critical and its neighbour the more sensitive, analyse what
   the critical one failing does to security and what the sensitive one
   failing does to safety and dependability, and record how the conflict
   was resolved.
6. Use the results to cut the sensitive set down and treat what remains:
   propose design changes that take components out of it (moving key
   handling into one isolated component, say) and mitigations for the
   components that stay sensitive. Log each as a recommendation with an
   owner.
7. Grade the measures in the security management plan with
   `check_security_measures`. Each sensitive component needs measures on
   top of those already chosen for critical software, a written reason for
   each, and a report showing it was applied.
8. For each change since the last baseline, call `change_impact`. A change
   in what the platform hardware does, in any tool that takes part in
   producing the executable, or in the security of the operating
   environment the software is fielded in orders a regression run of the
   sensitive software (a binary comparison can stand in for a minor tool
   change).
9. For the other triggers, record an analysis of whether more
   verification and validation is needed: a change in platform function or
   performance, in the surroundings the software or its hardware run in,
   in what is known about threats, vulnerabilities or the system's
   sensitivity, or in the build infrastructure and its tools.
10. At every milestone from the preliminary design review on, re-run steps
    3 and 5 on the current design and state, component by component,
    whether its sensitivity and security risks still hold.
11. In the same report, give the status of every recommendation from step
    6: implemented or not, verified or not.
12. Send the system security analyst what the software level found that
    the system level did not: new security failure modes or
    vulnerabilities, and recommendations for system activities or system
    changes, new or changed requirements included.
13. Check open nonconformances with `check_board_security` and each
    supplier package with `check_supplier_security_package`.
14. Hand the results to the reviewer as a draft.

## Obligations

| Item | Step |
|---|---|
| ECSS-Q-ST-80C Rev.2 6.2.9.1a | 1 |
| ECSS-Q-ST-80C Rev.2 6.2.9.2a | 3 |
| ECSS-Q-ST-80C Rev.2 6.2.9.3a | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.9.3b | 2 |
| ECSS-Q-ST-80C Rev.2 6.2.9.4a | 6 |
| ECSS-Q-ST-80C Rev.2 6.2.9.5a | 11 |
| ECSS-Q-ST-80C Rev.2 6.2.9.6a | 10 |
| ECSS-Q-ST-80C Rev.2 6.2.9.7a | 12 |
| ECSS-Q-ST-80C Rev.2 6.2.10.1a | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.10.1b | 5 |
| ECSS-Q-ST-80C Rev.2 6.2.10.2a | 7 |
| ECSS-Q-ST-80C Rev.2 6.2.10.3a | 8 |
| ECSS-Q-ST-80C Rev.2 6.2.10.4a | 9 |

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
