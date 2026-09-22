# Leaf build template — one leaf per claude session

CRITICAL description rule: the SKILL.md frontmatter `description` MUST
contain a BARE action verb from this list somewhere (not a gerund:
"generating" fails, "generate" passes): produce|determine|draft|plan|
size|run|analyze|build|create|configure|manage|calculate|evaluate|
generate|write|develop|design|compute|validate|verify|estimate|
implement|deploy|test|troubleshoot|audit|scope|map|convert|extract|
monitor|automate|review|assess|simulate|model|synthesize|document|
maintain|calibrate|optimize|derive|allocate|define|execute|perform|
support|guide|structure|prepare|coordinate|classify|identify.
Start the description "Use when <BARE-VERB> ..." and include Trigger:.

NEVER use the words "classified"/"unclassified" in any file content —
the content-policy gate flags them as security markings. Use
"categorized"/"uncategorized" when you mean classify-by-type.

You are the Aero skills builder. Build ONE ECSS leaf in this repo.

Leaf: {LEAF_SLUG} ({LEAF_SCOPE})

Steps:
1. Read the house format: skills/space-systems/ecss/systems-engineering/SKILL.md
   (existing leaf) + skills/space-systems/ecss/software-engineering/SKILL.md.
2. Read the leaf inventory row for {LEAF_SLUG} in
   ops/ecss-program/e-st-10-system-scope.md to get the exact anchor clause.
3. Create skills/space-systems/ecss/{LEAF_SLUG}/ with:
   - SKILL.md: frontmatter (name, description, trigger) + body:
     when-to-use, step-by-step procedure (concrete, implementable),
     verification section. Cite the ECSS clause as anchor ONLY.
   - scripts/{LEAF_SLUG}_logic.py: deterministic offline module
     implementing the checkable logic (stdlib only, no deps).
   - scripts/test_{LEAF_SLUG}.py: offline unittest, deterministic, passes.
   - OPTIONAL, the clause-obligation binding (docs/OBLIGATIONS.md). When
     the leaf makes the practitioner do or check lettered items of the
     clause, declare those items in the frontmatter and anchor each one
     to the step of the numbered `## Workflow` that does it:

         clauses:
           - standard: ECSS-E-ST-50C Rev.2
             clause: 5.6.11.8
             items: [a, b]
             relation: implements

         ## Obligations

         | Item | Step |
         |---|---|
         | ECSS-E-ST-50C Rev.2 5.6.11.8a | 2 |
         | ECSS-E-ST-50C Rev.2 5.6.11.8b | 3 |

     relation is `implements` (the practitioner does the item) or
     `verifies` (the practitioner checks it was met); `cites-clause` is
     refused. Quote a clause with fewer than two dots ("5.10"), write
     items inline, and put no comment on a binding line. Read the items
     with `python3 tools/obligations/earm_items.py items --export <EARM>
     --standard "<edition>" --clause <n>` (terminal only; paraphrase,
     never paste), then run `make obligations`. Declare only items the
     workflow really makes the practitioner discharge.
4. NO verbatim ECSS text (copyright) — paraphrase into implementable
   procedure. Common knowledge + procedure, standard+clause as citation.
5. Run the test locally to prove it passes.
6. Commit with message "ECSS E-ST-10C: add {LEAF_SLUG} leaf (SKILL.md + scripts + test)".
7. Report the commit hash + test result.
