# R1 view: Verification + Legal + Finance lens (Bheem)

**Date:** 2026-08-31 · **Status:** review note, at founder fence
**Related:** research/briefs/00-CEO-REPORT.md, 04-gtm-pricing.md,
06-legal-export-control.md, 08-defense-procurement.md, 09-competitor-deepdive.md,
10-tool-ecosystem-licensing.md; README.md; AGENTS.md; legal/README.md;
finance/README.md

## Verification

**STRONG**
- Brief 06 is primary-source grounded (22 CFR 120.33(b)/(a), 120.34; EAR
  734.7; Reg (EU) 2021/821 Annex I GTN; Estonian Strategic Goods Act).
  Publish-safe line is correct: methodology = general engineering
  principles, technical data is not, disclaimer never decontrols.
- Whitespace direction holds under my own live check (below): aerospace
  category is tiny; adjacent winners are large.

**WEAK**
- "Audited" (00-CEO-REPORT.md) is prose, not replayable. The audit table
  resolved 31,136 vs 31,246 as non-material drift without ever snapshotting
  live. My live check via GitHub API on 2026-08-31:
  - K-Dense-AI/scientific-agent-skills: 39,109 stars, 3,653 forks
    (pushed 2026-08-29)
  - mukul975/Anthropic-Cybersecurity-Skills: 31,700 stars, 3,817 forks
    (pushed 2026-08-24)
  Repo claims: K-Dense 31.9k (00, 09), cybersecurity 31.1-31.2k (04, 09,
  00 audit table). K-Dense is stale by ~7.2k stars (~22%). No repo number
  matches live at publish time. Intel's 39,082 was closest; Ops 37,955
  and Scout 38k bracket it. Replay: `curl -s
  https://api.github.com/repos/K-Dense-AI/scientific-agent-skills | grep
  stargazers_count`.
- "Verified against primary sources" (brief 10 header) has no artifact:
  no scripts dir, no CI (.github/workflows absent), no eval harness, no
  snapshot. Self-attestation only.
- CEO report claims ~322KB / 2,647 lines; actual .md total is 2,617 lines
  across 12 briefs (360K dir includes the HTML). Minor, same pattern:
  quoted numbers drift.
- Clean-at-rest broken: research/briefs/00-CEO-REPORT.html is untracked
  (AGENTS.md rule).

**Replayable-attestation requirement for the publish plan**
Every buyer-facing number ships with: command or URL + snapshot timestamp
+ expected value + exit code (the kb-audit.py / verify-demo.sh shape from
Veda). Minimum gate set before Phase 1 GO:
1. number-snapshot.sh — GitHub API stars for K-Dense / cybersecurity /
   aerospace list, timestamped output, exit 0 on expected-range check.
2. brief-audit.sh — cross-brief number agreement (31.9k vs live must
   surface, not resolve in prose).
3. content-policy-sweep.sh — red-flag terms per brief 06 8.3.6: part
   numbers, classified markings, "ITAR" on public files, verbatim
   standards text (RTCA/SAE/IAQG tables).
No number, no compliance banner, no compliance hook ships without its
gate passing. That is my attestation requirement.

## Legal

**STRONG**
- Brief 06 is legally sound as research: correct cites, correct
  standards-copyright matrix (RTCA/SAE/IAQG proprietary single-user,
  FAR 25 public domain, CS-25 attribution-only), contributor
  certification (8.3.4), mis-marking rule (8.3.9: never mark public
  content as ITAR/EAR-controlled), counsel thresholds (8.3.8).
- Tool licensing (brief 10) is sound: skill = text, not derivative work;
  never vendor GPL/LGPL/NOSA source; Abaqus human-skill-value clause is
  the one genuine tripwire.

**WEAK**
- Brief 06 is research, not policy. No effective date, no owner, no
  review cadence, no ratification signature. Founder "legal sign-off"
  must ratify a policy instrument, not a brief.
- Enforcement stack absent: no LICENSE (Apache-2.0), no CONTRIBUTING.md
  certification, no SECURITY.md, no STANDARDS.md, no NOTICE, no per-skill
  frontmatter standard, no sweep, no GATED/. legal/ is a README stub;
  contracts/, licenses/, ip/ do not exist.
- Claim language: publishable copy must use the 06 8.3.9 formulation
  ("not controlled technical data as published, verify before use"),
  never "ITAR-compliant" or "certified". Brief 08 6.3 "ITAR-free" is an
  architecture claim; keep it out of buyer-facing copy until the content
  policy is enforced and swept.
- My sign-off is blocked on artifacts, not on analysis.

**Missing for RATIFIED policy**
1. Founder GO (publish VETO domain).
2. Policy instrument (legal/policy/export-control-policy.md): effective
   date, owner, review cycle, adopting 06 8.1-8.4 by reference.
3. The 06 8.3 stack implemented, with sweep as a CI gate.
4. Counsel consultation recorded before any gated/USML-adjacent tier is
   populated (06 8.3.8 tripwire).

## Finance

**STRONG**
- Brief 04 anchors are labeled and sourced (Monetizely, DollarPocket,
  CompareTiers, 500k.io, StrongMocha, SkillExchange, MathWorks/Vendr).
  Blended EUR 10k MRR path is honestly labeled: "achievable only with
  founder network + aggressive 1:1 outreach".
- Navier 5.6M USD seed CONFIRMED live (BusinessWire, Dec 15 2025, GV /
  HCVC / YC) — Intel's competitor read checks out. Navier Stella/Stokes/
  Ferro confirms a funded platform anchor exists.

**WEAK**
- Vecteur pricing (200-1,200 EUR/seat/mo per Intel) is NOT in the repo;
  brief 01 names Vecteur but carries no pricing. I could not verify it
  live (search backend down). It stands as Intel's live observation only.
  The gap vs brief-04 team tier (29-99 EUR/user/mo) must be documented
  in a pricing model: either AeroSkills is the library layer under a
  Vecteur-class platform, or the tier math changes.
- Zero financial artifacts: finance/ledger/ and finance/pricing/ do not
  exist. No cost baseline, no runway, no unit economics (cost per skill,
  free-tier maintenance, marketplace fees 15-30%), no invoice record.
- VETO-domain future spend unlabeled: AIAA SciTech 3-10K USD (04 4.2.5),
  C3PAO 40-100K USD, FedRAMP 180K+ USD consulting (08 3.1/4.3). All
  >50 EUR = founder VETO. Any money ask enters a ledger before the gate.

## VETO exposure
Phase 1 GO, public-first GO, legal sign-off, outreach GO are all founder
VETO gates. Correct. Publish GO must not pass on prose: it passes on the
attestation gate + the legal stack.

## Group post (sent 2026-08-31, telegram team channel)
see below.

## Evidence
- GitHub API live (2026-08-31): K-Dense 39,109/3,653; cybersecurity
  31,700/3,817. Commands as recorded above.
- wc -l research/briefs/*.md = 2,617 lines; du -sh = 360K (incl. HTML).
- git status: ?? research/briefs/00-CEO-REPORT.html.
- find: no LICENSE, CONTRIBUTING, SECURITY.md, NOTICE, STANDARDS.md;
  no .github/workflows; finance/ and legal/ contain README.md only.
- BusinessWire 2025-12-15: Navier 5.6M seed, GV/HCVC/YC.
