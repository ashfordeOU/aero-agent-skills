#!/usr/bin/env python3
"""Reference implementation of the Aero Agent Skills offline router.

Standard library only. No network, no model, no state: the same query over
the same skill tree always produces the same ranking, on any machine.

Scoring (one pass over every indexed skill):

    score = 3.0 * |query tokens INTERSECT tags|
          + 2.0 * |query tokens INTERSECT name tokens|
          + 1.0 * |query tokens INTERSECT description tokens|
          + 0.5 * |query tokens INTERSECT body tokens|
          + 4.0 if the normalised query phrase occurs verbatim in
                 "<name> <description>" lowercased

Tokens are `[a-z0-9][a-z0-9-]*` runs of the lowercased text with a fixed
stop-word list removed. Intersections are over SETS, so a token repeated in
a skill counts once. Ranking is by score descending, then by skill path
ascending; the winner is the top of that order, and Hit@1 asks whether the
winner is the skill the case names.

This file is the executable definition of the claim. It is written to be
read: an outside reviewer should be able to check that it matches the
description above, and then check that it reproduces the published number.
"""

import hashlib
import os
import re

import yaml_subset

__all__ = ["STOP_WORDS", "tokenize", "SkillIndex", "SkillEntry"]

# Fixed stop-word list. Part of the router definition, not a tuning knob:
# changing it changes the claim, so the manifest records its digest.
STOP_WORDS = frozenset([
    "a", "an", "the", "for", "or", "and", "of", "to", "in", "on", "with",
    "is", "are", "was", "be", "at", "by", "from", "as", "into", "onto",
    "under", "over", "per", "via", "it", "its", "this", "that", "these",
    "those", "their", "our", "we", "you", "your", "do", "does", "did",
    "can", "could", "should", "would", "will", "shall", "must", "not", "no",
])

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9-]*")

WEIGHT_TAGS = 3.0
WEIGHT_NAME = 2.0
WEIGHT_DESCRIPTION = 1.0
WEIGHT_BODY = 0.5
PHRASE_BONUS = 4.0


def tokenize(text):
    """Lowercase, cut into `[a-z0-9][a-z0-9-]*` runs, drop stop words."""
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP_WORDS]


def stopwords_digest():
    """Digest of the stop-word list, so a later run can prove it is the same."""
    joined = ",".join(sorted(STOP_WORDS))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


class SkillEntry(object):
    """One indexed skill: the four token sets the scorer reads, plus the
    lowercased name+description the phrase bonus searches."""

    __slots__ = ("path", "name", "description", "tags", "name_tokens",
                 "description_tokens", "body_tokens", "haystack", "body_sha256")

    def __init__(self, path, name, description, tags, body):
        self.path = path
        self.name = name
        self.description = description
        self.tags = frozenset(str(t).lower() for t in tags)
        self.name_tokens = frozenset(tokenize(name))
        self.description_tokens = frozenset(tokenize(description))
        self.body_tokens = frozenset(tokenize(body))
        self.haystack = (name + " " + description).lower()
        self.body_sha256 = hashlib.sha256(body.encode("utf-8")).hexdigest()

    def score(self, query_tokens, phrase):
        """Score this skill against a pre-tokenized query."""
        total = 0.0
        total += WEIGHT_TAGS * len(query_tokens & self.tags)
        total += WEIGHT_NAME * len(query_tokens & self.name_tokens)
        total += WEIGHT_DESCRIPTION * len(query_tokens & self.description_tokens)
        total += WEIGHT_BODY * len(query_tokens & self.body_tokens)
        if phrase and phrase in self.haystack:
            total += PHRASE_BONUS
        return total


class SkillIndex(object):
    """Every SKILL.md under a skills root, read once and pre-tokenized.

    Pre-tokenizing is the only difference from a naive implementation: the
    arithmetic is identical, the token sets are identical, and the ranking is
    identical -- the work is simply not repeated for every case.
    """

    def __init__(self, entries):
        self.entries = entries

    @classmethod
    def from_tree(cls, skills_root):
        """Index every SKILL.md under `skills_root` (recursive, sorted)."""
        entries = []
        skipped = []
        for full_path in _walk_skill_files(skills_root):
            rel_dir = os.path.relpath(os.path.dirname(full_path), skills_root)
            rel_dir = rel_dir.replace(os.sep, "/")
            with open(full_path, "r", encoding="utf-8") as handle:
                text = handle.read()
            front, body = yaml_subset.read_frontmatter(text)
            if front is None:
                skipped.append(rel_dir)
                continue
            metadata = front.get("metadata")
            if not isinstance(metadata, dict):
                metadata = {}
            tags = metadata.get("tags") or []
            if not isinstance(tags, list):
                tags = []
            entries.append(SkillEntry(
                path=rel_dir,
                name=front.get("name") or "",
                description=front.get("description") or "",
                tags=tags,
                body=body,
            ))
        entries.sort(key=lambda e: e.path)
        index = cls(entries)
        index.skipped = skipped
        return index

    def __len__(self):
        return len(self.entries)

    def rank(self, query, top_k=1):
        """Return the top `top_k` (score, path) pairs for `query`."""
        query_tokens = frozenset(tokenize(query))
        phrase = " ".join(tokenize(query))
        if not query_tokens:
            scored = [(0.0, e.path) for e in self.entries]
        else:
            scored = [(e.score(query_tokens, phrase), e.path) for e in self.entries]
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return scored[:top_k]

    def top1(self, query):
        """Return (score, path) for the single winning skill."""
        return self.rank(query, top_k=1)[0]

    def digest(self):
        """Content hash binding this index to the exact text it was built from.

        Covers, for every skill in path order: the path, the name, the
        description, the tag list and a hash of the body. Two runs that print
        the same digest scored the same corpus.
        """
        sha = hashlib.sha256()
        for entry in self.entries:
            sha.update(entry.path.encode("utf-8"))
            sha.update(b"\x00")
            sha.update(entry.name.encode("utf-8"))
            sha.update(b"\x00")
            sha.update(entry.description.encode("utf-8"))
            sha.update(b"\x00")
            sha.update(",".join(sorted(entry.tags)).encode("utf-8"))
            sha.update(b"\x00")
            sha.update(entry.body_sha256.encode("utf-8"))
            sha.update(b"\n")
        return sha.hexdigest()


def _walk_skill_files(skills_root):
    """Yield every SKILL.md under `skills_root`, in sorted path order."""
    found = []
    for dirpath, dirnames, filenames in os.walk(skills_root):
        dirnames.sort()
        if "SKILL.md" in filenames:
            found.append(os.path.join(dirpath, "SKILL.md"))
    found.sort()
    return found
