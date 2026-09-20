#!/usr/bin/env python3
"""Gate: this corpus still satisfies the roles that bind into it.

THE INVARIANT, AND WHY IT LIVES ON BOTH SIDES
---------------------------------------------
A role in the aero-agent-roles corpus declares the leaves it is built on, as
`family/pack/leaf` slugs in its own frontmatter. Those leaves live HERE, and
the two corpora version independently. So there is an invariant neither
corpus can check alone:

    every leaf a role binds must exist in the skills corpus it is paired with

Adding leaves cannot break it. RENAMING OR RETIRING A BOUND LEAF CAN, and
that is a qualification event rather than a data change. This corpus grows
every hour; a rename here is the live risk, and until now nothing in this
repository's publish chain would have noticed. The invariant was measured by
hand once, which is a fact about that afternoon.

WHY A PINNED CONTRACT AND NOT A LOOKUP
--------------------------------------
The gate runs inside the publish export, offline, with no roles checkout and
no network. Reaching for one would make this a check that can pass because
something was reachable. ops/contracts/role-bindings.json is the roles
corpus's declaration, committed here: the set of slugs it binds, the roles
that bind them, and a digest over the lot.

WHAT IT DOES NOT COVER, SAID PLAINLY
------------------------------------
A pinned contract is a snapshot. A role added tomorrow that binds a leaf
renamed the day after is invisible to this gate until the contract is
refreshed. That gap is closed from the other side -- the roles corpus
resolves its own bindings on every one of its runs, against a live corpus or
its own pinned ledger -- and `make gate-bindings` in the harness closes it
completely whenever both corpora are present at once. Three enforcement
points; each names what it cannot see.

Usage:
  role_bindings_contract.py                      gate: check this tree
  role_bindings_contract.py --refresh <roles>    rewrite the contract
"""

import hashlib
import io
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT = os.path.join(ROOT, "ops", "contracts", "role-bindings.json")
CONTEXT = "aero-role-binding-contract/v1"

_FRONTMATTER = re.compile(r"\A﻿?---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
                          re.S)
_ITEM = re.compile(r"^[ \t]+-[ \t]+(.+?)[ \t]*$")
_KEY = re.compile(r"^([A-Za-z0-9_-]+):[ \t]*(.*?)[ \t]*$")
_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*){2}$")
KEY = "skills_bound"


def _unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
        return v[1:-1]
    return v


def declared(text):
    """The slugs one role document binds, and the ones that are malformed.

    A malformed declaration is returned rather than dropped: a typo that
    silently vanishes is how a role ends up claiming fewer leaves than it
    declares, and the count still looks right.
    """
    m = _FRONTMATTER.match(text or "")
    if not m:
        return [], []
    good, bad, in_list = [], [], False
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = _ITEM.match(line)
        if in_list and item:
            raw = _unquote(item.group(1))
            (good if _SLUG.match(raw) else bad).append(raw)
            continue
        k = _KEY.match(line)
        if k:
            in_list = False
            if k.group(1) != KEY:
                continue
            v = k.group(2)
            if v.startswith("[") and v.endswith("]"):
                for raw in (p.strip() for p in v[1:-1].split(",")):
                    if raw:
                        raw = _unquote(raw)
                        (good if _SLUG.match(raw) else bad).append(raw)
            elif v:
                raw = _unquote(v)
                (good if _SLUG.match(raw) else bad).append(raw)
            else:
                in_list = True
    return good, bad


def digest(mapping):
    """Over the role->slugs mapping, so a hand edit is caught on read."""
    blob = "\n".join("%s %s" % (r, ",".join(sorted(v)))
                     for r, v in sorted(mapping.items()))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def leaves_here():
    """family/pack/leaf for every leaf in THIS tree."""
    base = os.path.join(ROOT, "skills")
    depth = base.count(os.sep)
    out = set()
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in (".git", "__pycache__")]
        if "SKILL.md" in fn and dp.count(os.sep) == depth + 3:
            out.add(os.path.relpath(dp, base))
    return out


def load():
    if not os.path.isfile(CONTRACT):
        return None
    with io.open(CONTRACT, encoding="utf-8") as fh:
        doc = json.load(fh)
    if doc.get("context") != CONTEXT:
        raise ValueError("%s carries context %r, not %r"
                         % (CONTRACT, doc.get("context"), CONTEXT))
    roles = doc.get("roles") or {}
    if not roles:
        raise ValueError("%s names no roles -- a pass over zero bindings is "
                         "the sentence a broken contract would print"
                         % CONTRACT)
    if digest(roles) != doc.get("bindings_digest"):
        raise ValueError("%s: the role map does not hash to the digest it "
                         "carries -- it was edited by hand" % CONTRACT)
    return doc


def refresh(roles_root):
    base = os.path.join(roles_root, "roles")
    if not os.path.isdir(base):
        base = roles_root
    mapping, malformed = {}, []
    for entry in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        p = os.path.join(base, entry, "ROLE.md")
        if not os.path.isfile(p):
            continue
        good, bad = declared(io.open(p, encoding="utf-8").read())
        if good:
            mapping[entry] = sorted(set(good))
        for raw in bad:
            malformed.append((entry, raw))
    for role, raw in malformed:
        print("FAIL contract: role %s declares %r, which is not a "
              "family/pack/leaf slug" % (role, raw), file=sys.stderr)
    if malformed:
        return 1
    if not mapping:
        print("FAIL contract: 0 roles with bindings found under %s -- "
              "refusing to write a contract that asserts nothing" % roles_root,
              file=sys.stderr)
        return 1
    bound = sorted(set(s for v in mapping.values() for s in v))
    os.makedirs(os.path.dirname(CONTRACT), exist_ok=True)
    doc = {
        "_comment": [
            "What the aero-agent-roles corpus binds into this one.",
            "",
            "GENERATED -- never edit by hand; bindings_digest is over the",
            "role map and a hand edit is caught on the next read.",
            "",
            "This corpus grows every hour. Adding leaves cannot break a",
            "binding; renaming or retiring a BOUND leaf can, and that is a",
            "qualification event. make role-bindings refuses to pass a tree",
            "that has stopped satisfying this, so a rename cannot reach the",
            "public repository unnoticed.",
            "",
            "Refresh with: make role-bindings-refresh ROLES=<path>",
        ],
        "context": CONTEXT,
        "role_count": len(mapping),
        "binding_count": sum(len(v) for v in mapping.values()),
        "bound_leaf_count": len(bound),
        "bindings_digest": digest(mapping),
        "bound_leaves": bound,
        "roles": mapping,
    }
    with io.open(CONTRACT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")
    print("PASS contract: %d role(s), %d binding(s) over %d distinct leaf/"
          "leaves, digest %s" % (doc["role_count"], doc["binding_count"],
                                 len(bound), doc["bindings_digest"][:16]))
    return 0


def gate():
    try:
        doc = load()
    except ValueError as exc:
        print("FAIL role-bindings: %s" % exc, file=sys.stderr)
        return 1
    if doc is None:
        print("FAIL role-bindings: %s is missing. With no contract there is "
              "nothing to check a rename against, and a rename is the one "
              "change here that breaks a paired corpus." % CONTRACT,
              file=sys.stderr)
        return 1

    here = leaves_here()
    if not here:
        print("FAIL role-bindings: 0 leaves found in this tree -- every "
              "binding would read as broken, which is louder and more "
              "misleading than saying the scan found nothing", file=sys.stderr)
        return 1

    missing = 0
    for role in sorted(doc["roles"]):
        for slug in doc["roles"][role]:
            if slug in here:
                continue
            print("FAIL role-bindings: role %s binds %s, which no longer "
                  "exists in this corpus -- a renamed or retired bound leaf "
                  "is a qualification event, not a data change"
                  % (role, slug), file=sys.stderr)
            missing += 1

    if missing:
        print("FAIL role-bindings: %d of %d binding(s) no longer resolve "
              "against %d leaf/leaves" % (missing, doc["binding_count"],
                                          len(here)), file=sys.stderr)
        return 1

    print("PASS role-bindings: %d role(s), %d binding(s) over %d distinct "
          "leaf/leaves, all resolving against %d leaf/leaves in this tree"
          % (doc["role_count"], doc["binding_count"], doc["bound_leaf_count"],
             len(here)))
    return 0


def main(argv):
    if "--refresh" in argv:
        rest = [a for a in argv[1:] if a != "--refresh"]
        if len(rest) != 1:
            print("usage: role_bindings_contract.py --refresh <roles-root>",
                  file=sys.stderr)
            return 2
        root = os.path.abspath(rest[0])
        if not os.path.isdir(root):
            print("FAIL contract: %s is not a directory" % root,
                  file=sys.stderr)
            return 2
        return refresh(root)
    return gate()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
