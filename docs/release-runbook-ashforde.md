# AeroSkills release runbook: Ashforde public publish

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

From the PRIVATE dev repo (/Users/enterprisehq/AeroSkills):

    git log --oneline -1        # expect the final RC commit (tagged v1.0.0-rc1)
    git rev-parse --short v1.0.0-rc1^{commit}   # prints the same short hash
    git status --porcelain      # expect empty (clean at rest)
    git tag -l v1.0.0-rc1       # expect the annotated RC tag at the final RC commit
    make validate               # expect PASS 5/5 (52 SKILL.md, 43 contract
                                # tests, 102/102 Hit@1, gate 4 zero markers)
    make attest                 # expect PASS 3/3 (number snapshot offline,
                                # brief audit, content policy 0 hits)
    bash ops/automation/test/run-tests.sh   # expect ALL TESTS PASS

Release package (local, not pushed anywhere): the clean tree at HEAD
already built at /Users/enterprisehq/releases/aeroskills-v1.0.0-rc1/
(144 files, no .git, no dev fixtures, secrets sweep 0 hits,
content-policy sweep 0 hits, make validate PASS inside the package).
Rebuild command and exact contents: section 3a.

## 2. Create the Ashforde org repo (no dev history)

The org repo must NOT be created with --source: that would push the
dev repo's full history. Create it empty, private, then push the CLEAN
tree as a single initial commit.

    gh repo create Ashforde/aeroskills --private --description \
      "Aerospace engineering skills for AI agents: standards-mapped, eval-gated, Apache-2.0"

(The org slug and repo name to be confirmed by the founder at token
connect; `aeroskills` is the working name everywhere in this repo.)

## 3. Build + push the clean tree (single squashed commit)

Rebuild the clean tree if the package above is stale; otherwise reuse
it. The archive command below is the ONLY sanctioned way to build the
package: it reproduces the public tree EXACTLY (section 3a allowlist;
no drift, no extra files). Do not use a bare `git archive HEAD -- .`
or `cp -R` of the dev tree: that ships internal docs.

    mkdir -p /Users/enterprisehq/releases/aeroskills-v1.0.0-rc1
    cd /Users/enterprisehq/AeroSkills
    git archive --format=tar HEAD -- \
      .gitignore .github/ CITATION.cff CODE_OF_CONDUCT.md CONTRIBUTING.md LICENSE Makefile NOTICE README.md SECURITY.md STANDARDS.md standards-map.yaml \
      skills/ scripts/ eval/ \
      docs/FAQ.md docs/glossary.md docs/harness-contract.md docs/harness-integration.md docs/company-of-departments.md \
      marketing/README.md marketing/release-notes-v1.0.0-rc1.md marketing/positioning-1pager.md \
      ops/automation/ ':(exclude)ops/automation/test' \
      | tar -x -C /Users/enterprisehq/releases/aeroskills-v1.0.0-rc1

    cd /Users/enterprisehq/releases/aeroskills-v1.0.0-rc1
    git init -b main
    git add -A
    git commit -m "AeroSkills v1.0.0-rc1: 43 skills, 27 sub-domain packs, eval-gated

43 aerospace engineering skills across 27 installable sub-domain packs
in 9 families, each passing make validate 5/5 (spec lint, desc lint,
behavior contract, no-verbatim, Hit@1 102/102). Clean tree from dev HEAD
v1.0.0-rc1 (the final RC commit), no dev history, secrets swept,
content policy green. Public-tree allowlist only: skills, scripts,
eval, standards-map, docs (5 public files), marketing (3 public
files), ops/automation (minus dev fixtures). Apache-2.0, published by
Ashforde OU (Estonia)."
    git remote add origin https://github.com/Ashforde/aeroskills.git
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
- skills/ (all 43 leaf skills + 9 family routers, 52 SKILL.md + their
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

## 4. Tag the org repo

Annotated tag, same message discipline as the private tag:

    git tag -a v1.0.0-rc1 -m "AeroSkills v1.0.0-rc1: clean public tree, gates validate 5/5 + attest 3/3"
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
    git tag -a v1.0.0-rc1 -m "AeroSkills v1.0.0-rc1 (final RC commit): clean package, gates validate 5/5 + attest 3/3, public-tree allowlist"
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
      https://github.com/arjun-0077/aeroskills.git) to the Ashforde
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

    gh repo edit Ashforde/aeroskills --visibility public

This is the single publish event (plan P3 section 4.1). It is the
founder-timed GO; nobody flips it early. After the flip:
- [ ] Public page loads; README renders; badges resolve.
- [ ] `git ls-remote --tags` on the public URL shows v1.0.0-rc1.
- [ ] `git log --oneline` on a fresh clone shows the single clean
      commit, no dev history.
- [ ] `make validate` exits 0 on a fresh PUBLIC clone (replayable
      proof, this is the only "verified" claim that ships).
- [ ] Secrets re-sweep on the public clone returns zero hits.
- [ ] arjun-0077/aeroskills remains PRIVATE. Never flip it.

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

Map-coverage docs keep 14 on purpose: README "Standards map" badge,
marketing/positioning-1pager.md ("covers 14 standards") state the
standards-MAP total (14 entries including sep-2640) and the 9 gated
set. That is a map-coverage claim, enforced against
standards-map.yaml by ops/automation/gated-set-check.sh (R2 expects
14, R1/R3 expect 9). Do not "fix" those to 13; it would break the
guard and misstate map coverage.

## 9. Guardrails (never)

- Never flip arjun-0077/aeroskills public.
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

## 10. Related

- Plan: marketing/distribution-plan-P3.md (launch sequence, targets,
  risks) and marketing/launch-draft-2026-08-31.md (X thread copy).
- Release notes: marketing/release-notes-v1.0.0-rc1.md.
- Contract: docs/harness-contract.md (the 5 gate definitions).
- Policy: research/briefs/06-legal-export-control.md (compliance
  posture), research/briefs/04-gtm-pricing.md (pricing HOLD).
- Source of truth for numbers: ops/automation/numbers.yaml.
