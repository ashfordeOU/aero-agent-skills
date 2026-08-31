# AeroSkills Phase 1 — Joint Report

Team discussion round · Phase A R1 (6 views) + R2 (6 answers) · 2026-08-31
Project: AeroSkills activation (repo `arjun-0077/aeroskills`, 9 departments, 12 research briefs)
Protocol: `discussion-rounds` skill — bounded R1/R2, convergence, scores, finalize.

---

## 1. Consensus

The team converges on five points across all six lenses:

1. **The whitespace thesis holds, verified live.** Total aerospace-skills attempts
   on GitHub ≈ 228 stars; largest active aerospace repo measured 22 stars
   (Bheem live check 2026-08-31). Adjacent-domain winners: cybersecurity skills
   31,700 stars, K-Dense scientific-agent-skills 39,111. Nobody ships a
   standards-mapped, verified, cross-harness aerospace skills library. The
   category is empty at any star count.
2. **The moat is the standards map + compliance hooks + evals + CI** — the proven
   cyber/science playbook, with no aerospace analog yet. The ASD-STE100 race is
   the defining data point: same idea, same week, 2,937 stars (with evals +
   distribution) vs 1,574 vs 0.
3. **The build is not ready, and that is a sequence problem, not a content
   problem.** No CI, no legal stack, no skills/ directory, no eval harness, no
   standards-map YAML. The full Phase 0 sequence is committed with dates.
4. **The founder gates stay VETO-gated and correct.** Phase 1 GO, public vs
   private-first, legal sign-off, outreach GO. Publish GO must pass on gates
   (attestation), never on prose.
5. **'Verified' and 'audited' are currently prose, not replayable.** Every number
   and claim must ship with its command, snapshot timestamp, and exit code
   before anything public.

## 2. Viewpoints (6 lenses)

### Scout (Research)
Strong: evidence grounding is real (primary-source legal texts, measured star
counts with uncertainty labels); brief 06 is the most decision-ready piece;
brief 03 is technically honest about router limits; briefs 05/10 are
domain-actionable; pricing anchored to real numbers.
Weak: number-split audit gap (K-Dense 38.0k vs 31.9k); demand inferred not
measured; no eval-harness design; 7/9 departments scaffold-only; repo not clean
at rest.
Next-phase: freeze the fact sheet, eval harness before 12 seed skills,
standards map as machine-readable YAML.

### Intel (Market + Competitive)
Strong: OSS wedge whitespace verified live via GitHub API; positioning for the
free wedge defensible; brief 04 Pro tier well-anchored.
Weak: demand inferred, zero WTP checks; Operator-SKU competitors unanalyzed —
Navier (5.6M USD seed, GV/HCVC/YC, ex-SpaceX/Tesla/Aurora) is funded and
shipping; Vecteur's live pricing (200-1,200 EUR/seat/mo, air-gapped 200k/yr)
puts brief 04's enterprise anchor 10-100x below the market; number hygiene
breaks the 'audited' claim.
Verdict: positioning holds for the wedge, not the paid tier as written.

### Market Strategist (Strategy + Marketing + GTM)
Strong: GTM spine coherent (free OSS wedge → Pro packs → enterprise → Operator
SKUs; router as compounding asset).
Weak: timing breaks — 11 weeks to €10k MRR unreachable on organic baseline;
needs founder-led sales sprint; outreach before the repo is live and evals exist
is marketing a promise.
Answer on Vecteur: platform anchor, not library anchor — two products, two
pricing logics. Library tier stays at org-license rates (2-10k/yr beachhead);
Operator SKU anchors at Vecteur's band when it ships.
Positioning: the knowledge layer, never the platform.
Phase 1 GO plan: 12 seed skills (DO-178C spine first), router port, CI/evals
from day 1, legal content policy, publish OSS, outreach GO last.

### Ops Manager (Feasibility/Ops + Security/Compliance/Privacy)
Strong: harness-first sequence is feasible and required; concrete first-skill
verification target (avionics/do178c/planning, 3 machine gates); router port
feasible (BM25+tags only at launch, dense rerank deferred to 100-600 skills).
Weak: build is NOT ready — no CI, no legal stack, no skills dir, no eval
harness, no standards-map YAML; router artifact not locatable from this host;
K-Dense unreconciled; repo not clean at rest.
Phase 0 sequence (committed dates): standards-map.yaml → eval harness →
seed skills. Harness DoD: `make validate` exits 0 on 5 gates (spec lint,
description lint, per-skill pytest/DAL test, no-verbatim standards grep, Hit@1
corpus). Contract + standards-map in repo 2026-09-02; green on skill 1 by
2026-09-04; attestation gate + legal stack green 2026-09-07; founder gate
review target 2026-09-07.

### Content Writer (Messaging + Content/Support)
Strong: buyer-correct spine exists in briefs 09/11 (knowledge layer, never
platform); legal brief 06 ships the exact README compliance banner; tool
brief is ready-made troubleshooting content.
Weak: zero buyer-facing artifacts exist; README is an internal org chart, not a
pitch; 'standards-mapped, verified, cross-harness' is roadmap, not artifact;
term discipline is legal-adjacent (never 'certified', never export-compliance claims);
K-Dense unreconciled; clean-at-rest broken.
Preparing at the fence (no publish): positioning 1-pager, README v0.1 with
compliance banner, docs/FAQ/glossary skeleton, troubleshooting from canonical
failure modes. 'Verified' copy unblocks when the eval harness is green
(2026-09-04).

### Bheem (Verification + Legal + Finance)
Strong: brief 06 primary-source sound; whitespace confirmed under own live
check; brief 04 anchors labeled; Navier seed confirmed live (BusinessWire,
2025-12-15).
Weak: 'audited' is prose — K-Dense stale by ~7.2k stars (22%); 'verified' has
no artifact; brief 06 is research, not policy (no LICENSE, CONTRIBUTING,
SECURITY.md, STANDARDS.md, frontmatter, sweep); finance has zero artifacts
(no ledger, no pricing model, no unit economics); Vecteur pricing unverified
by Bheem (search backend down).
Replayable-attestation requirement: every published number ships with command +
snapshot timestamp + expected value + exit code (kb-audit/verify-demo shape).
No banner, no compliance hook ships without its gate.

## 3. R2 Answers (tagged questions resolved)

| From | To | Question | Answer |
|---|---|---|---|
| Scout | Ops Manager | Does Phase 0 sequence the eval harness + standards spine before seed skills? First skill verification target? | YES — harness-first, feasibility not preference. First skill avionics/do178c/planning: spec lint + DAL A-E test + no-verbatim RTCA grep. |
| Intel | Market Strategist | Does Vecteur's live pricing re-anchor our enterprise tier? | Platform anchor, not library anchor. Two products, two pricing logics. Operator SKU anchors at Vecteur band when it ships. |
| Market Strategist | Scout | Spec the eval harness (5 baseline tasks, before/after metric, Hit@1 target) | 5 tasks with exact pass criteria (CubeSat battery, weight-and-balance, engine-overhaul, DO-178C coverage, XFOIL polar); before/after delta (task success, Hit@1, hallucination count); Hit@1 ≥95% launch, ≥74% past 600 skills. |
| Ops Manager | builder (self) | Harness contract in repo before skill 1, skill 1 gated on it | Acknowledged as committed plan with dates (contract 09-02, green 09-04). |
| Content Writer | Ops Manager | Definition of done for the eval harness + by when | 5-gate DoD, deterministic, no network calls. Contract 09-02, green on skill 1 by 09-04. |
| Bheem | Ops Manager | DoD + date for attestation gate + legal stack before founder legal sign-off | 3 scripts green 09-07; legal stack artifacts green 09-07; founder sign-off VETO, ratification package at next gate review (target 09-07). |

## 4. Open Items (carried, non-blocking for Phase 1 GO sequencing)

1. **Number hygiene** — K-Dense split (31.9k vs 38.0k vs 39,111 live) must be
   reconciled by brief-audit.sh against a canonical numbers.yaml before any
   public figure ships. (Owner: Ops, gate 09-07)
2. **Demand unmeasured** — 5-10 practitioner interviews needed to convert
   inferred demand into measured WTP before outreach GO. (Owner: Scout, with
   founder GO on outreach)
3. **Operator-SKU competitor deep-dive** — Navier/Vecteur/AwerX/Deepsky as
   Operator competitors unanalyzed; one more brief before Operator integration
   planning. (Owner: Intel)
4. **Vecteur pricing unverified by Bheem** — stands as Intel's live observation;
   must be re-verified and documented in a pricing model. (Owner: Bheem/Finance)
5. **7/9 departments scaffold-only** — no marketing strategy, finance ledger,
   legal artifacts, ops runbooks; three founder gates have no department work
   products behind them yet. (All owners, Phase 1)
6. **Repo not clean at rest** — research/briefs/00-CEO-REPORT.html untracked.
   (Owner: Ops, immediate)
7. **Router artifact not locatable from AeroSkills host** — port depends on
   exporting skill-router.py from Veda first. (Owner: Ops)
8. **Founder gates** — Phase 1 GO / public vs private-first / legal sign-off /
   outreach GO all VETO-gated and open. Legal sign-off must precede any
   compliance-hook content.

## 5. Recommendation

Proceed to **Phase 1 GO recommendation** for the founder with the Phase 0
sequence as the committed build plan: standards-map YAML → eval harness →
12 seed skills, with the attestation gate + legal stack as the publish
prerequisites. The team's scoring follows; all six lenses rate the project
≥7 on the strength of the research and the committed, dated Phase 0 plan —
with the explicit condition that **publish GO passes on gates, not prose**.

Team: Scout · Intel · Market Strategist · Ops Manager · Content Writer · Bheem
