# R1 view: Messaging + Content + Support lens (Content Writer)

**Date:** 2026-08-31 · **Status:** prepare-only, at founder fence
**Related:** research/briefs/00-CEO-REPORT.md, 06-legal-export-control.md,
09-competitor-deepdive.md, 11-product-strategy-integration.md,
05-domain-taxonomy.md; README.md; marketing/README.md; support/README.md

## R1 view

**STRONG**
- Buyer-correct spine in briefs 09/11: the knowledge layer, not the
  platform; standards map = moat; compliance hooks = proof (09 §Part 4,
  11 §1.2). The ajhcs lesson stands: clause-level beats Wikipedia summary.
- Legal 06 §8.4 provides the exact README compliance banner template and
  the publish-safe/publish-gated framing. Not affiliated notice prudent.
- Tool-licensing findings are ready-made Support content: canonical
  failure modes (NaN/CFL, SPICE paths, CMake staleness, AVL whitespace,
  JSBSim XSD) and fork/version differences (OpenFOAM Foundation vs ESI,
  SU2 v7 to v8).

**WEAK**
- Zero buyer-facing artifacts. README.md is an internal company org chart:
  no pitch, no compliance banner, no install path, no star request. For an
  OSS wedge the README is the landing page (K-Dense, cybersecurity model).
- marketing/ and support/ READMEs point at workspace dirs (strategy/,
  content/, docs/, faq/, tickets/) that do not exist. No positioning doc,
  no docs, no FAQ, no glossary.
- "Standards-mapped, verified, cross-harness" is roadmap, not artifact.
  Shipping "verified" before the eval harness exists replicates the
  failure brief 09 mocks in competitors (devideamax: claims validation,
  no test suite). Evals were the ASD-STE100 race growth driver: 2,937 vs
  1,574 vs 0 stars, same week (09 §1.10).
- Term discipline is legal-adjacent: "standards-mapped" is factual,
  "certified"/"ITAR-compliant" implies certification. Mis-marking public
  content is itself a compliance failure (06 §8.3.9). Copy must say "not
  controlled technical data as published, verify before use".
- Number hygiene: K-Dense stars unreconciled (31.9k brief vs 39,082 Intel
  live vs 37,955 Ops). No buyer-facing figure ships without a reconcile.
- Clean-at-rest broken: research/briefs/00-CEO-REPORT.html untracked
  (AGENTS.md rule). Dogfood credibility claim needs a clean repo.

**Preparing at the fence**
1. Positioning 1-pager: category = knowledge layer; buyer = engineer;
   wedge = standards map; proof = evals; never "the platform".
2. README v0.1 draft: pitch + compliance banner (06 §8.4) + install +
   standards map + roadmap + star request.
3. docs/ skeleton: standards-map page, skill anatomy, per-host install,
   worked examples.
4. FAQ: is it certified? (no, methodology inside certified workflows),
   ITAR question, standards copyright (summarize, never copy), tool
   support, license. Glossary: DAL A-E, FDAL/IDAL, DO-178C/254,
   ARP4754A/4761A, AS9100, V&V, PSSA/SSA, trace matrix, compliance hook.
5. Support: troubleshooting from canonical failure modes, per-skill
   Verification sections, ticket-to-doc loop (support rule 2).

## Group post (sent 2026-08-31, telegram team channel)

Content Writer R1 (messaging, content, support).

STRONG: briefs 09/11 give a buyer-correct spine, knowledge layer not
platform, standards map as the moat, compliance hooks as the proof.
Legal 06 ships the README compliance banner and publish-safe framing.
Tool brief is ready-made troubleshooting: NaN/CFL, SPICE paths, CMake
staleness, fork versions.

WEAK: zero buyer-facing artifacts exist. README is an internal org chart,
no pitch, no banner, no install path. marketing and support point at
workspace dirs that do not exist. No positioning doc, no docs, no FAQ,
no glossary.

WEAK: standards-mapped, verified, cross-harness is roadmap, not artifact.
Shipping verified before the eval harness exists replicates the failure
brief 09 mocks in competitors. Evals were the ASD-STE100 winner growth
driver (2,937 vs 1,574 vs 0 stars, same week).

WEAK: term discipline is legal-adjacent. Standards-mapped is ok, never
certified or ITAR-compliant, mis-marking is itself a compliance failure
(06). K-Dense stars unreconciled (31.9k vs 39,082), no figure ships
without a reconcile. Repo not clean at rest, 00-CEO-REPORT.html untracked.

Preparing at the fence: positioning 1-pager, README v0.1 with compliance
banner, docs/FAQ/glossary skeleton, troubleshooting from canonical
failure modes.

@OpsManager: what is the definition of done for the eval harness and by
when? Verified in my copy is blocked on that artifact.
