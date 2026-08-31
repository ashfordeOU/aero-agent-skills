# AeroSkills P3.1 — Distribution / GTM plan (draft, founder-gated)

**Date:** 2026-08-31 · **Status:** DRAFT for founder review. Nothing in
this plan executes without founder GO (publish = VETO; external sends =
VETO). Pricing HOLD: no prices are set or proposed here.
**Sources:** research/briefs/04, 06, 09, 11; marketing/positioning-1pager.md;
README.md; docs/harness-contract.md; ops/automation/numbers.yaml
(canonical register, live 2026-08-31 — every market number below
resolves against it).

## 0. Standing constraints (term discipline)

- Never claim certification, never claim export-control compliance,
  never claim ITAR compliance approval. The library is educational
  methodology (brief 06 §8.3.9); mis-marking public content is itself
  a compliance failure.
- "Verified" means exactly one thing: the replayable gates pass on the
  commit you are looking at (`make validate` 5/5 + `make attest`).
  It does not mean certified, approved, or airworthy
  (positioning-1pager.md).
- Pricing HOLD until founder lifts it (founder VETO domain).
- Nothing ships before founder legal sign-off + publish GO.

## 1. Launch posture: private-first, executable-on-GO

The repo is private (github.com/arjun-0077/aeroskills). The public flip
IS the GO event — one commit, one toggle, everything else pre-staged.

The plan is a runbook: it must be executable the moment the founder
says GO, but no action in it happens before. All preparation is
in-tree (store-first, AGENTS.md).

Legal sign-off checklist (from brief 06): README compliance banner ✓
in-tree, STANDARDS.md summary-not-copy ✓, SECURITY.md ✓, Apache-2.0 ✓.
Remaining: founder/legal review of the publish package as a whole —
that review is the gate, and it is the only blocker to GO.

## 2. Channels ranked for THIS product

Ranked by (expected star/traction impact × fit with an eval-gated
standards library ÷ effort). Evidence column cites the canonical
register + briefs.

| Rank | Channel | Why this product | Evidence |
|---|---|---|---|
| 1 | **GitHub public flip + stars strategy** | The README is the landing page for an OSS skills library; star count is the social proof that compounds (cyber 31.7k★, K-Dense 39.5k★, anthropics/skills ≈172k★). K-Dense runs a star-request banner in its README and auto-versioned releases — both copied into our README/release plan. | brief 09 §2.1/2.2; numbers.yaml (cyber 31,700; kdense 39,503; anthropics 172,643) |
| 2 | **X / community** | The ASD-STE100 race was decided by distribution, not content: same week, three variants → SimpleEnglish (2,979★ live; launched with evals, 74.6% fewer violations) vs danyuchn (1,584★) vs hakimzulkufli (0★). Evals + launch marketing were the difference. X is where the dev-tools crowd finds OSS libraries (K-Dense runs X/LinkedIn/YouTube). | brief 09 §1.10/§2.2; numbers.yaml |
| 3 | **Aerospace engineering communities** | Small (≈71.6K US aero engineers) but standards-bound and well-paid; the audience that actually cares about DO-178C/ARP4754A. Slower, higher-quality adoption. AIAA SciTech presence is the long play (brief 11 Phase 3). | brief 11 §2.2; brief 01 |
| 4 | **Hacker News (Show HN)** | The OSS-library launch pattern; SimpleEnglish's HN launch (232 points) fed its star run. One post, no follow-ups, no voting rings. | brief 09 §1.10 |
| 5 | **agentskills.io ecosystem** | We already ship the format (`npx skills add`, agentskills.io conformance, cross-harness). Marketplace listings are an amplifier, not primary distribution (brief 11 §3.1d). SEP-2640 participation = protocol-level first mover. | brief 09 §3.1; brief 11 §3.1 |
| 6 | **Technical newsletters** | Long-tail, cheap. K-Dense's docs-as-product + benchmark content is the pattern; our replayable-gates story is the hook. Low effort after launch-day assets exist. | brief 09 §2.2 |

Order matters: GitHub first (the artifact), X + HN second (the spikes),
aerospace communities third (the real buyers), ecosystem + newsletters
fourth (the compounding).

## 3. The verification wedge as the distribution asset

The proof artifact is not a claim — it is a command:

    git clone https://github.com/arjun-0077/aeroskills.git
    cd aeroskills
    make validate    # 5/5 REAL gates, offline, deterministic
    make attest      # number snapshot + brief audit + content policy

- Gate 5 (Hit@1) runs 28 corpus tasks: 25 domain tasks + 3 adversarial
  cross-pair tasks, all asserting top-1 routing (harness-contract.md).
  "Hit@1 28/28" is a headline number every reader can re-run.
- The lane is empty: total aerospace ≈ 228★ across all attempts, vs
  cybersecurity 31.7k★ and K-Dense Scientific Agent Skills 39.5k★
  adjacent. The largest dedicated aerospace skills repo is 62★
  (Soljourner, 3 commits, abandoned). The largest active aerospace
  repo is ajhcs/mbse-agents at 22★; devideamax/aerospace-team is 21★.
- AeroSkills launches with 12 verified skills, each spec-linted,
  behavior-tested, router-asserted, and copyright-gated — where every
  competitor ships claims, we ship receipts.
- Every marketing claim maps to a replayable command. That is the
  answer to "yet another skills repo".

## 4. Launch sequence

### 4.0 Pre-launch (now — prepare only, nothing sent)
- [ ] README + docs final pass (buyer-facing v0.1 exists, draft)
- [ ] FAQ final: "is it certified?", ITAR question, standards copyright
      (summary-not-copy), license — pre-answer the skeptics
- [ ] Founder/legal sign-off on the publish package (VETO gate)
- [ ] Draft all launch posts in-tree: X thread (3-5 messages), Show HN,
      subreddit posts, newsletter pitch — drafts only
- [ ] Release prep: tag v0.1.0 + changelog (K-Dense auto-release pattern)
- [ ] agentskills.io listing metadata; verify `npx skills add` path
- [ ] Fresh `make snapshot-live` + numbers.yaml reconcile (evidence as
      of the GO commit)

### 4.1 Launch day (post-GO)
- Flip repo public (the only publish event).
- Post cadence: 3-5 messages max per channel, no repeats, no spam.
- GitHub: release v0.1.0 + README star request.
- X: one thread, 3-5 posts — empty-lane, verification wedge, install,
  ask. No follow-up posting.
- HN: one Show HN post. No self-upvotes, no engagement bait.
- Aerospace communities: one post in 2-3 subreddits/Discord servers
  max, phrased for engineers (standards + verification, not hype).
- Newsletters: one pitch to a short founder-approved list.

### 4.2 Post-launch (D1-D30)
- Daily: triage issues/PRs, respond within 24h (issue templates exist).
- Weekly: metrics review vs targets (§5); update README top line from
  what the data says.
- D7: first iteration loop — what do the top issues say about the
  library? Fix fast, ship fixes on main.
- D30: founder review — stars/clones/adoptions vs targets; decide
  whether Phase 2 (monetization prep, brief 11 Phase 2) starts.

## 5. First-30-day targets (founder-approval required)

All rows are TARGETS for founder approval, not commitments. Aerospace
adoption is slower than infosec (brief 01: smaller audience, more
conservative) — the SimpleEnglish 2.9k★ week was a viral exception, not
a baseline. Basis: brief 11 §2.3 (500-2,000★ in 90 days organic
baseline; we target the lower third for 30d).

| Metric | 30-day target | Basis |
|---|---|---|
| Stars | 150-400 (target) | brief 11 §2.3 lower third of 90d baseline; aerospace lag |
| Forks | 15-40 (target) | cyber forks/stars ≈ 12%, kdense ≈ 9% |
| Clones | 300-1,000 (target) | estimate; measured via owner traffic API |
| Skill adoptions | 30-100 (target) | `npx skills add` + manual installs; issue/PR + registry signals |
| Issues/PRs | 5-20 (target) | quality signal; 24h response commitment |
| Hit@1 | 28/28 across every commit (hard gate, not a target) | harness-contract |

## 6. Risks + fallbacks

| Risk | Fallback |
|---|---|
| Legal sign-off delay | Plan is executable-on-GO; keep drafting, no public activity. Re-review at founder cadence. |
| "Yet another skills repo" skepticism | Verification wedge (§3) is the counter: replayable gates, Hit@1 28/28, empty-lane evidence. Shift weight to aerospace communities where standards matter. FAQ pre-answers "is it certified?" |
| Standards-copyright questions | Summary-not-copy rule (STANDARDS.md), no-verbatim gate (gate 4) enforces zero verbatim text; compliance banner in README. Show STANDARDS.md + gate output as receipts. |
| Competitor copycats | Navier (navier.ai) and Vecteur (vecteur.space) are closed Operator-SKU platforms — agent-driven simulation/computation products, not open skill libraries. They validate demand, not the format. The moat is the standards map + eval-gated authoring (brief 09 §Part 4/5: no competitor has a machine-readable clause map; hundreds of hours of expert work) + traction compounding. Position as the knowledge layer, never the platform (brief 11). |
| Launch flop (low stars) | Iterate top line + channel mix; aerospace adoption is slower. D30 review decides whether to add academic/campus channel (brief 07) or pull AIAA SciTech earlier. |

## 7. Definition of done for P3.1

- [ ] This plan reviewed and approved by founder
- [ ] Pre-launch checklist (§4.0) complete in-tree
- [ ] Repo clean, gates green (make validate + make attest), plan
      committed to main

P3.2 = execute pre-launch prep. P3.3 = launch on GO.

Related: research/briefs/04-gtm-pricing.md (pricing HOLD),
06-legal-export-control.md (compliance posture), 09-competitor-deepdive.md
(channel evidence), 11-product-strategy-integration.md (phases, funnel,
moat); marketing/positioning-1pager.md; docs/harness-contract.md;
README.md; ops/automation/numbers.yaml.
