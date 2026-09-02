# Aero Agent Skills release runbook: Ashforde public publish

**Status: EXECUTED 2026-09-02.** github.com/ashfordeOU/aero-agent-skills
is LIVE (public, single branch `main`, tagged `v1.0.0`), and
`aero-agent-skills@1.0.0` is LIVE on npm (verified via `npx
aero-agent-skills search` against the published registry copy, not
just the publish exit code). arjun-0077/aero-agent-skills remains the
private TEST environment (founder 2026-09-02: "we will maintain test
environment in arjun account and publish the public release via
ashfordeOU"). Section 10 below is the actual command sequence that
worked, superseding the fictional `/Users/enterprisehq/...` paths and
untested assumptions in sections 1-7 (kept for their reasoning, not
their exact paths — three assumptions in the original draft turned out
wrong when actually executed, see section 10's notes).

**Status:** runbook, executable-on-GO. Nothing here executes without
founder GO (publish = founder VETO, AGENTS.md). This document is the
operating procedure for the CORRECTED publish path.

**Correction (founder decision-ledger, 2026-08-31):** NEVER flip the
arjun-0077 dev repo public. Dev repos stay PRIVATE on the profile.
Public release = Ashforde org ONLY. The founder connects the Ashforde
org token, then Ops Manager publishes CLEAN repos (no dev history,
secrets swept, tagged, README-ready). The arjun-0077 origin remains
private forever; the only push it ever received beyond main was the
release-candidate TAG (allowed, stays private).

**Rework (CEO audit 2026-08-31, HEAD f001e1b):** four defects fixed.
(1) Package rebuilt from the FINAL RC commit (the commit tagged
v1.0.0-rc1); the previous package was built from 7fd559d and missed
the release-notes and the SEP-2640 split. (2) The RC tag was MOVED
from 7fd559d to the final RC commit (delete + recreate, force-push to
the private origin only, a one-time sanctioned correction, documented
in section 4). (3) An explicit public-tree content policy was added
(section 3a): the package ships ONLY the allowlist; internal docs
(research/, security/audits/, development/, finance/, people/,
support/, marketing/launch-draft, marketing/distribution-plan-P3.md,
docs/ops-notes.md, docs/release-runbook-ashforde.md, docs/superpowers/,
ops/automation/test/) never ship. (4) The SEP-2640 split (13 domain
standards + SEP-2640 as separate delivery format) is applied to all
packaged marketing copy.

**Owner:** Ops Manager executes every step below on GO.
**Gate:** founder/legal sign-off on the publish package + CEO audit
GO. CEO handles the founder DM ("READY TO PUBLISH: connect Ashforde
token") after the 9.5 audit.

---

## 0. Preconditions (all must hold)

- [ ] Founder has connected a GitHub token for the Ashforde org
      (gh auth with the org's scope; verify: `gh auth status`,
      `gh api orgs/Ashforde/repos` returns 200).
- [ ] Founder/legal sign-off on the publish package (plan P3 section 1).
- [ ] Pricing HOLD honored: no prices anywhere in public artifacts.
- [ ] Release candidate evidence fresh: HEAD == the final RC commit
      (the commit tagged v1.0.0-rc1; see section 1).
- [ ] Public-tree content policy (section 3a) satisfied: package
      contains exactly the allowlist, nothing else.

## 1. Verify the release source

From the PRIVATE dev repo (/Users/enterprisehq/Aero Agent Skills):

    git log --oneline -1        # expect the final RC commit (tagged v1.0.0-rc1)
    git rev-parse --short v1.0.0-rc1^{commit}   # prints the same short hash
    git status --porcelain      # expect empty (clean at rest)
    git tag -l v1.0.0-rc1       # expect the annotated RC tag at the final RC commit
    make validate               # expect PASS 5/5 (81 SKILL.md, 69 contract
                                # tests, 154/154 Hit@1, gate 4 zero markers)
    make attest                 # expect PASS 3/3 (number snapshot offline,
                                # brief audit, content policy 0 hits)
    bash ops/automation/test/run-tests.sh   # expect ALL TESTS PASS

Release package (local, not pushed anywhere): the clean tree at HEAD
already built at /Users/enterprisehq/releases/aero-agent-skills-v1.0.0-rc1/
(144 files, no .git, no dev fixtures, secrets sweep 0 hits,
content-policy sweep 0 hits, make validate PASS inside the package).
Rebuild command and exact contents: section 3a.

## 2. Create the Ashforde org repo (no dev history)

The org repo must NOT be created with --source: that would push the
dev repo's full history. Create it empty, private, then push the CLEAN
tree as a single initial commit.

    gh repo create Ashforde/aero-agent-skills --private --description \
      "Aerospace engineering skills for AI agents: standards-mapped, eval-gated, Apache-2.0"

(The org slug and repo name to be confirmed by the founder at token
connect; `aero-agent-skills` is the working name everywhere in this repo.)

## 3. Build + push the clean tree (single squashed commit)

Rebuild the clean tree if the package above is stale; otherwise reuse
it. The archive command below is the ONLY sanctioned way to build the
package: it reproduces the public tree EXACTLY (section 3a allowlist;
no drift, no extra files). Do not use a bare `git archive HEAD -- .`
or `cp -R` of the dev tree: that ships internal docs.

    mkdir -p /Users/enterprisehq/releases/aero-agent-skills-v1.0.0-rc1
    cd /Users/enterprisehq/Aero Agent Skills
    git archive --format=tar HEAD -- \
      .gitignore .github/ CITATION.cff CODE_OF_CONDUCT.md CONTRIBUTING.md LICENSE Makefile NOTICE README.md SECURITY.md STANDARDS.md standards-map.yaml \
      skills/ scripts/ eval/ \
      docs/FAQ.md docs/glossary.md docs/harness-contract.md docs/harness-integration.md docs/company-of-departments.md \
      marketing/README.md marketing/release-notes-v1.0.0-rc1.md marketing/positioning-1pager.md \
      ops/automation/ ':(exclude)ops/automation/test' \
      | tar -x -C /Users/enterprisehq/releases/aero-agent-skills-v1.0.0-rc1

    cd /Users/enterprisehq/releases/aero-agent-skills-v1.0.0-rc1
    git init -b main
    git add -A
    git commit -m "Aero Agent Skills v1.0.0-rc1: 69 skills, 36 sub-domain packs, eval-gated

69 aerospace engineering skills across 36 installable sub-domain packs
in 12 families, each passing make validate 5/5 (spec lint, desc lint,
behavior contract, no-verbatim, Hit@1 154/154). Clean tree from dev HEAD
v1.0.0-rc1 (the final RC commit), no dev history, secrets swept,
content policy green. Public-tree allowlist only: skills, scripts,
eval, standards-map, docs (5 public files), marketing (3 public
files), ops/automation (minus dev fixtures). Apache-2.0, published by
Ashforde OU (Estonia)."
    git remote add origin https://github.com/Ashforde/aero-agent-skills.git
    git push -u origin main

Pre-push hygiene (every one must pass before the push):
- `find . -name .git -o -name __pycache__ -o -name .pytest_cache -o -name '*.pyc'`
  returns nothing.
- `grep -rniE 'ghp_|github_pat_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|BEGIN (RSA|EC|OPENSSH|PGP) PRIVATE KEY' .`
  returns nothing.
- `bash ops/automation/content-policy-sweep.sh` prints PASS 0 hits.
- `find . -path ./ops/automation/state -prune -o -type f -print | grep -E 'research/|security/audits|development/|finance/|people/|support/|launch-draft|distribution-plan|ops-notes|superpowers|fixture'` returns nothing.

## 3a. Public-tree content policy (the allowlist)

The public package ships EXACTLY this list and nothing else. This is
the founder doctrine: public release = CLEAN repos (clean export, no
dev history, secrets sweep, README-ready). Every file in the package
must be on the allowlist below.

IN (allowlist):
- Root: .gitignore, .github/, CITATION.cff, CODE_OF_CONDUCT.md,
  CONTRIBUTING.md, LICENSE, Makefile, NOTICE, README.md, SECURITY.md,
  STANDARDS.md, standards-map.yaml
- skills/ (all 69 leaf skills + 12 family routers, 81 SKILL.md + their
  scripts/ and test_*.py behavior contracts)
- scripts/ (gate scripts + eval machinery), eval/ (hit1 corpus)
- docs/FAQ.md, docs/glossary.md, docs/harness-contract.md,
  docs/harness-integration.md, docs/company-of-departments.md
- marketing/README.md, marketing/release-notes-v1.0.0-rc1.md,
  marketing/positioning-1pager.md
- ops/automation/ EXCEPT ops/automation/test/ (gate scripts,
  numbers.yaml, state/ snapshots, needed for `make attest` and the
  content-policy sweep to run inside the package)

OUT (never ship):
- research/ (incl. briefs/ + peer-skill-repo-audit)
- security/audits/
- development/ (incl. builds/ + expansion-pipeline)
- finance/, people/, support/ (dept stubs)
- legal/ (dept stub; LICENSE/NOTICE at root are the legal artifacts)
- marketing/launch-draft-2026-08-31.md (founder-gated, not posted)
- marketing/distribution-plan-P3.md (internal GTM)
- marketing/content/ (internal drafts)
- docs/ops-notes.md, docs/release-runbook-ashforde.md (internal ops,
  dev-only), docs/superpowers/
- ops/automation/test/ (dev fixtures + negative-control suite)
- AGENTS.md (DECISION: EXCLUDE). It is the internal operating/coding
  standard for agents in the dev repo (departments, VETO domains,
  delivery rules). Public contributors use CONTRIBUTING.md +
  CODE_OF_CONDUCT.md instead. Keeping AGENTS.md out of the package
  keeps internal process out of the public tree.

The .github/workflows/attest.yml runs `make validate` + `make attest`
in CI; both work inside the package (scripts/ + ops/automation minus
test/ are present). The run-tests.sh negative-control step is dev-only
and is skipped when ops/automation/test/ is absent (the workflow
checks for the file).

## 3b. Amendment 2026-09-02: distribution channels (npm + MCP + Claude Code plugin)

Distribution channels shipped at dev HEAD 17615ea, AFTER the RC tag and
after the Design v5 generated-README rework — so sections 3/3a above are
stale in two ways this amendment corrects. Apply all of it at GO.

Allowlist ADDITIONS (the public tree is broken without them):

- `.claude-plugin/` (plugin.json + marketplace.json): README's
  `claude plugin marketplace add` command fails without them. Both pass
  `claude plugin validate --strict`.
- `packages/aero-agent-skills/` (npm CLI + MCP server sources,
  generated manifest.json, smoke battery): README + harness-integration
  sections 8-9 document it, `.ci-native` runs `make package-test` (full
  Hit@1 corpus replayed through the JS router), and the npm publish must
  build from the public tree. The skills/LICENSE/NOTICE/standards-map
  payload inside the package dir is gitignored and produced by prepack —
  ship the sources, not a payload copy.
- Generated data + EXACTLY the images the README embeds (verified by
  grepping README.md's `src="docs/...` — do not ship the whole docs/
  image set, only what's actually `<img>`-referenced): docs/metrics.json,
  docs/DOMAINS.md, docs/logo-mark.png, and the FULL matched light+dark
  set scripts/gen_visuals.py's outputs() manages — title[.svg/.png],
  title-dark[.svg/.png], statline[-dark], domain-radar[-dark],
  domain-polar[-dark], structure[-dark], skill-anatomy[-dark],
  how-it-works[-dark], gates[-dark]. README only embeds the -dark
  PNGs, but the light variants are the SAME public diagrams (not
  marketing collateral) and outputs() checks both — an export missing
  either half fails that export's own `make visuals-check` (learned
  the hard way 2026-09-02: a first cut shipped -dark only, and
  visuals-check inside the exported tree immediately flagged every
  missing light .svg/.png as stale). Rule of thumb: whatever
  scripts/gen_visuals.py's outputs() function generates IS the public
  set, by definition — ship all of it, don't hand-pick a subset.

  EXPLICIT EXCLUSION (founder 2026-09-02: "marketing and branding
  stuff can't be pushed to public repo"): NEVER ship
  docs/logo-full.png (unused raw brand asset, wordmark not yet
  regenerated), anything scripts/gen_visuals.py's marketing_outputs()
  produces — docs/social-card-dark.svg/.png and
  marketing/launch-post-linkedin.md (LinkedIn collateral, never
  embedded in README), docs/ashforde-seal.svg (the Ashforde OÜ
  corporate seal, vendored from ashforde-site/assets/brand/ solely for
  the social card's footer lockup — not the Aero Agent Skills product
  logo, not a gen_visuals PUBLIC output), docs/DESIGN.md (internal
  build law), or anything under marketing/. marketing_outputs() is
  itself gated on docs/ashforde-seal.svg existing, so an export that
  omits the seal file naturally can't generate or require these two —
  that gating is what makes a public checkout's own visuals-check
  pass without them (see the gen_visuals.py commit fixing the
  FileNotFoundError this exclusion caused on the first export
  attempt).

Frozen numbers: the examples above say 69 skills / 36 packs / Hit@1
154 — those are the 08-31 RC snapshot. At GO, regenerate with
`make visuals` and take every count from docs/metrics.json at the
packaged commit; hand-carrying any number violates the visuals law.

npm registry state (2026-09-02): `aero-agent-skills@0.0.1` and
`aero-skills@0.0.1` are LIVE as README-only name reservations,
publisher `ashfordeou`, no repository field (dev account never appears
publicly). GO-day step: from the PUBLIC packaged tree,
`cd packages/aero-agent-skills && npm publish` (0.1.0 supersedes the
placeholder; `aero-skills` stays a reservation pointing at the
canonical name). Verify with `npm view aero-agent-skills version` —
never with exit codes or job status; a fresh publish 404s on read for
about a minute (replication lag), so poll before concluding failure.

README slug flips: DONE at GO (2026-09-02) — the public home is
github.com/ashfordeOU/aero-agent-skills (founder: user account, not an
org; dev/test stays on arjun-0077 private). The DEV tree itself now
carries the public slug everywhere (README install commands, clone
URL, package.json repository, plugin.json, launch post, live star
badge), so packaging needs zero rewrites and cannot drift. Release notes for v1.0.0 must gain a
Distribution section (npm CLI, MCP server + host list, Claude Code
plugin, npx skills); the ashforde.org/aeroagentskills landing page
gains its npm/MCP install blocks the same day, not before. After the
real npm publish, list the MCP server in the official MCP registry
(registry.modelcontextprotocol.io) and the community directories so
MCP hosts can discover it from their publisher catalogs, and flip the
README's static npm badge to a live shields npm/v badge.

Launch collateral (2026-09-02): the old marketing/ tree (launch draft,
release notes, positioning) was PURGED in the public-readiness cleanup
commit, so the allowlist's three marketing files no longer exist —
v1.0.0 release notes must be written fresh at GO. The launch post now
lives at marketing/launch-post-linkedin.md, GENERATED by gen_visuals
(numbers can never go stale; regenerate before posting, attach
docs/social-card-dark.png — the generated 1200x627 hero card, with a
real per-family bar chart and the founder logo — as the post image).
BOTH ARE DEV-REPO-ONLY, never public (corrected 2026-09-02, see the
explicit exclusion list above): marketing/ in full, plus
docs/social-card-dark.svg/.png specifically. Post to LinkedIn straight
from the dev-repo files; do not copy either into the public package
or use the card as the repo's og/share image.

## 4. Tag the org repo

Annotated tag, same message discipline as the private tag:

    git tag -a v1.0.0-rc1 -m "Aero Agent Skills v1.0.0-rc1: clean public tree, gates validate 5/5 + attest 3/3"
    git push origin v1.0.0-rc1

At final release (after any RC review fixes), tag v1.0.0 the same way
on the org repo and re-run the verification of step 6 on that commit.

### 4a. Private-origin RC tag correction (rework 2026-08-31, DONE)

The v1.0.0-rc1 annotated tag on the PRIVATE dev origin was created at
7fd559d (before the final RC commit f001e1b + rework landed), so the
tag excluded its own release notes, runbook, and the SEP-2640 fix.
Correction (one-time, sanctioned by the CEO audit; repo is private, no
consumers):

    git tag -d v1.0.0-rc1
    git push origin :refs/tags/v1.0.0-rc1
    git tag -a v1.0.0-rc1 -m "Aero Agent Skills v1.0.0-rc1 (final RC commit): clean package, gates validate 5/5 + attest 3/3, public-tree allowlist"
    git push origin v1.0.0-rc1

This is the ONLY sanctioned force-push/delete-recreate on the private
dev origin: an RC-tag pointer correction before public release, tag
ref only (never main, never history). Guardrail section 9 still
forbids pushing dev history or force-pushing main.

## 5. README live edits (do these BEFORE the visibility flip)

- [ ] Strip the draft banner: the badge `[![Status: draft]...]` and the
      italic line `*Draft v0.2. Buyer-facing draft, in-tree only;
      release is founder-gated.*` (README.md lines ~8 and ~14).
- [ ] Update the clone URL in Install (currently
      https://github.com/arjun-0077/aero-agent-skills.git) to the Ashforde
      org URL.
- [ ] Verify the badge counts still match the tree: Skills 43,
      Standards 14, Gates 5/5 REAL. The standards-map badge stays 14
      (map total); see the SEP-2640 note below.
- [ ] Confirm the compliance notice, FAQ links, SECURITY.md,
      CONTRIBUTING.md, STANDARDS.md, LICENSE, NOTICE are present and
      unchanged (legal checklist, plan P3 section 1).
- [ ] Re-run `make validate` and `make attest` in the org clone after
      the edits; both must exit 0 on the commit being published.

## 6. Visibility flip (the GO event)

    gh repo edit Ashforde/aero-agent-skills --visibility public

This is the single publish event (plan P3 section 4.1). It is the
founder-timed GO; nobody flips it early. After the flip:
- [ ] Public page loads; README renders; badges resolve.
- [ ] `git ls-remote --tags` on the public URL shows v1.0.0-rc1.
- [ ] `git log --oneline` on a fresh clone shows the single clean
      commit, no dev history.
- [ ] `make validate` exits 0 on a fresh PUBLIC clone (replayable
      proof, this is the only "verified" claim that ships).
- [ ] Secrets re-sweep on the public clone returns zero hits.
- [ ] arjun-0077/aero-agent-skills remains PRIVATE. Never flip it.

## 7. Launch (per marketing/distribution-plan-P3.md)

Sequence and owners (plan P3 section 4.1):
1. GitHub release v1.0.0-rc1 + README star request. Owner: Ops Manager.
2. X thread, 3-5 posts, from marketing/launch-draft-2026-08-31.md.
   Owner: Content Writer (copy), Market Strategist (post). The draft
   already carries the SEP-2640 split (see below).
3. Show HN: one post. Owner: Market Strategist.
4. Aerospace communities: one post in 2-3 subreddits/Discord servers.
   Owner: Market Strategist.
5. Newsletters: one pitch to a short founder-approved list.
   Owner: Market Strategist.

No repeats, no spam, no follow-up posting. D1-D30 per plan P3
section 4.2.

## 8. SEP-2640 split (Intel R4 note, applied 2026-08-31)

SEP-2640 is the skills-over-MCP DELIVERY FORMAT (open spec, emerging,
not yet stable: standards-map.yaml family open-spec, gated false). It
is NOT a domain standard. Public lists must enumerate the 13 DOMAIN
standards and mention SEP-2640 separately as the delivery layer:

- Domain standards (13): DO-178C, DO-254, ARP4754A, ARP4761A, AS9100,
  DO-330, DO-160G, AS9102, MMPDS, FAR-25/CS-25, ECSS, NACA TR-824.
- Delivery format (separate): SEP-2640 skills-over-MCP, adapter over
  the open agentskills.io SKILL.md format.

Applied: marketing/launch-draft-2026-08-31.md line 1 and
marketing/release-notes-v1.0.0-rc1.md. Keep the split in any new
public copy (X thread, Show HN, newsletter).

PACKAGED copy (rework 2026-08-31): the launch-draft itself is OUT of
the public package (founder-gated, not posted); the packaged
release-notes and positioning-1pager carry the split in the
allowlist. README's "Standards map" enumeration (13 domain standards
+ SEP-2640 as delivery format, separately named) matches the split.

Map-coverage docs state the live map total: README "Standards map" badge,
marketing/positioning-1pager.md ("covers 16 standards") state the
standards-MAP total (16 entries including sep-2640) and the 10 gated
set. That is a map-coverage claim, enforced against
standards-map.yaml by ops/automation/gated-set-check.sh (R2 expects
16, R1/R3 expect 10). Do not "fix" those to 15; it would break the
guard and misstate map coverage.

## 9. Guardrails (never)

- Never flip arjun-0077/aero-agent-skills public.
- Never push the dev repo history (no --source, no force-push of
  main on the dev repo). The ONE exception is the RC-tag pointer
  correction documented in section 4a (tag ref only, private origin,
  no consumers).
- Never send anything externally without founder GO (publish, posts,
  newsletters are all VETO domains).
- Never write a price (pricing HOLD until founder lifts it).
- Never claim certification, approval, airworthiness, or export
  control compliance; the content-policy sweep enforces this on
  publishable content (the pattern list is in
  ops/automation/content-policy-sweep.sh).
- Never ship dev-only artifacts: __pycache__, .pytest_cache, *.pyc,
  scratch, ops/automation/test/ fixtures, or any path not on the
  section 3a allowlist.

## 10. Actual execution log (2026-09-02) — the proven procedure

What actually ran, from the dev checkout (~/Code/aeroskills, ordinary
local path — no iCloud, no scratch-clone dance needed for THIS repo):

    # 1. Export the clean tree. This exact pathspec list is the
    #    corrected allowlist (section 3a/3b): everything
    #    scripts/gen_visuals.py's outputs() manages (full light+dark
    #    set, not just -dark), .claude-plugin/, packages/aero-agent-skills/,
    #    skills/ scripts/ eval/, the curated docs/*.md set, ops/automation
    #    minus test/. Never marketing/, never the seal/social-card/
    #    logo-full/DESIGN.md marketing-only assets.
    rm -rf /tmp/aero-public-release && mkdir -p /tmp/aero-public-release
    git archive --format=tar HEAD -- \
      .gitignore .github CITATION.cff CODE_OF_CONDUCT.md CONTRIBUTING.md \
      LICENSE Makefile NOTICE README.md SECURITY.md STANDARDS.md standards-map.yaml \
      .claude-plugin skills scripts eval packages/aero-agent-skills \
      docs/FAQ.md docs/glossary.md docs/harness-contract.md \
      docs/harness-integration.md docs/company-of-departments.md \
      docs/metrics.json docs/DOMAINS.md docs/logo-mark.png \
      docs/title.svg docs/title.png docs/title-dark.svg docs/title-dark.png \
      docs/statline.svg docs/statline.png docs/statline-dark.svg docs/statline-dark.png \
      docs/domain-radar.svg docs/domain-radar.png docs/domain-radar-dark.svg docs/domain-radar-dark.png \
      docs/domain-polar.svg docs/domain-polar.png docs/domain-polar-dark.svg docs/domain-polar-dark.png \
      docs/structure.svg docs/structure.png docs/structure-dark.svg docs/structure-dark.png \
      docs/skill-anatomy.svg docs/skill-anatomy.png docs/skill-anatomy-dark.svg docs/skill-anatomy-dark.png \
      docs/how-it-works.svg docs/how-it-works.png docs/how-it-works-dark.svg docs/how-it-works-dark.png \
      docs/gates.svg docs/gates.png docs/gates-dark.svg docs/gates-dark.png \
      ops/automation ':(exclude)ops/automation/test' \
      | tar -x -C /tmp/aero-public-release

    # 2. Hygiene: secrets grep (0 hits), stray __pycache__/.pyc check
    #    (git handles this via .gitignore once init'd), excluded-name
    #    leak check for social-card/ashforde-seal/logo-full/DESIGN.md/
    #    marketing — all clean.

    # 3. PROVE the export is self-contained: run the real gates INSIDE
    #    it before touching git or GitHub. This caught two real bugs
    #    (below) that a "looks right" read of the allowlist would have
    #    missed — never skip this step.
    cd /tmp/aero-public-release
    make validate && make attest && make visuals-check && make package-test

    # 4. Init, commit, create the repo, push, tag.
    git init -b main
    git config user.name "ashfordeOU"; git config user.email "contact@ashforde.org"
    git add -A && git commit -m "Aero Agent Skills v1.0.0: ..."
    gh repo create ashfordeOU/aero-agent-skills --public \
      --description "..." --homepage "https://ashforde.org/aeroagentskills"
    git remote add origin https://github.com/ashfordeOU/aero-agent-skills.git
    # the machine's global fail-closed pre-push hook needs a LOCAL gate
    # declaration in the export too — same requirement as any repo:
    printf 'make validate\nmake attest\nmake visuals-check\nmake package-test\n' > .ci-native
    git add .ci-native && git commit -m "ci: add local pre-push gate"
    git push -u origin main   # replays the battery again, ~7 min; run in background
    git tag -a v1.0.0 -m "..."
    git push origin v1.0.0    # tag pushes ALSO trigger the pre-push hook — background this too

    # 5. Publish npm from THIS tree, not the dev tree (npm token
    #    already configured machine-local as `ashfordeou`):
    cd packages/aero-agent-skills && npm publish --access public
    # verify against the registry directly, never the exit code:
    npm view aero-agent-skills version   # poll — replication lag ~1 min on a fresh version
    npx aero-agent-skills@1.0.0 search "..."   # real end-user smoke test

    # 6. Verify the Claude Code plugin channel against the REAL repo
    #    (not a local-path marketplace, which only proves the manifest
    #    parses — this proves GitHub resolution + discovery):
    claude plugin marketplace add ashfordeOU/aero-agent-skills
    claude plugin install aero-agent-skills@aero-agent-skills
    claude plugin details aero-agent-skills   # confirm version + skill inventory
    claude plugin uninstall aero-agent-skills; claude plugin marketplace remove aero-agent-skills

Three assumptions in the original draft (sections 1-7) that step 3
proved WRONG on first attempt — fix before trusting this runbook's
older prose over this log:

1. The original allowlist had NO docs/*.png or docs/*.svg at all
   (written before Design v5 existed). A "-dark only" first correction
   also failed: scripts/gen_visuals.py's outputs() checks the FULL
   light+dark set as one unit, so shipping half fails the export's own
   `make visuals-check`. Fix: ship everything outputs() manages — see
   section 3b's final form.
2. scripts/gen_visuals.py originally read docs/ashforde-seal.svg (a
   marketing-only vendored asset, correctly excluded from the public
   tree) unconditionally at import time. Any invocation of the script
   in the exported tree crashed. Fixed in the script itself:
   ashforde_seal_svg() is lazy, and marketing_outputs() (the social
   card + launch post) is gated on the seal file's existence — its
   absence in an export IS the public-tree signal.
3. Every dev-repo push and the export's own bootstrap push HANGS past
   the default 60s tool timeout because the pre-push hook replays the
   ~7-minute battery — this includes branch DELETES and TAG pushes,
   not just content pushes. Always background these, then verify with
   `git ls-remote` / `git rev-parse` rather than trusting a timed-out
   foreground command's silence.

Branch hygiene enforced same day (founder: "both repos only maintain
one branch"): arjun-0077's stale `release-clean` branch (pre-dated the
330-leaf/identity-rewrite era, never merged into main) was deleted;
ashfordeOU/aero-agent-skills was git-init'd fresh with only `main`, so
it was single-branch from birth.

## 11. Related

- Plan: marketing/distribution-plan-P3.md (launch sequence, targets,
  risks) and marketing/launch-draft-2026-08-31.md (X thread copy).
- Release notes: marketing/release-notes-v1.0.0-rc1.md.
- Contract: docs/harness-contract.md (the 5 gate definitions).
- Policy: research/briefs/06-legal-export-control.md (compliance
  posture), research/briefs/04-gtm-pricing.md (pricing HOLD).
- Source of truth for numbers: ops/automation/numbers.yaml.
