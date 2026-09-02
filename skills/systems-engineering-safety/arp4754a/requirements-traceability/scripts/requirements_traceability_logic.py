#!/usr/bin/env python3
"""Requirements traceability logic per ARP4754A (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, arp4754a: gated):
ARP4754A development assurance relies on bidirectional requirements
traceability through the development levels: system requirements
(SRATS) to high-level requirements (HLR) to low-level requirements
(LLR) to code and test. Closure requires each level to trace down and
back up, derived requirements must be flagged, and verification of each
trace must be completed before closure can be claimed.
"""

LEVELS = ("srats", "hlr", "llr", "code", "test")
_PREFIXES = ("srats", "hlr", "llr", "code", "test")


def _level_of(requirement_id):
    """Development level of a requirement id, from its level prefix
    (srats/hlr/llr/code/test, case-insensitive)."""
    rid = requirement_id.lower()
    for prefix in _PREFIXES:
        if rid.startswith(prefix):
            return prefix
    raise ValueError(
        "cannot determine level of requirement id: %r" % (requirement_id,)
    )


def _validate_links(links):
    if not isinstance(links, list):
        raise ValueError("links must be a list")
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("each link must be a dict")
        for key in ("from", "to", "verified"):
            if key not in link:
                raise ValueError("link missing key %r: %r" % (key, link))


def _index_links(links):
    """Index links by outgoing/incoming and collect ids per level."""
    out = {}
    inn = {}
    ids_by_level = {lvl: set() for lvl in LEVELS}
    for link in links:
        frm, to = link["from"], link["to"]
        lf, lt = _level_of(frm), _level_of(to)
        out.setdefault(frm, []).append(link)
        inn.setdefault(to, []).append(link)
        ids_by_level[lf].add(frm)
        ids_by_level[lt].add(to)
    return out, inn, ids_by_level


def _has_trace_to(out, req_id, target_levels):
    return any(_level_of(l["to"]) in target_levels for l in out.get(req_id, []))


def _has_trace_from(inn, req_id, source_levels):
    return any(
        _level_of(l["from"]) in source_levels for l in inn.get(req_id, [])
    )


def closure_status(links):
    """Closure of the trace matrix: (status, gaps).

    links is a list of {"from", "to", "verified"} dicts. Closure
    requires every srats to trace to an hlr, every hlr to have an
    incoming srats trace and an outgoing llr trace, every llr to have
    an incoming hlr trace and an outgoing code or test trace, and every
    traced pair to be verified. Returns ('closed', []) or ('open',
    gaps) with human-readable gap strings."""
    _validate_links(links)
    out, inn, ids_by_level = _index_links(links)
    gaps = []
    for srats in sorted(ids_by_level["srats"]):
        if not _has_trace_to(out, srats, ("hlr",)):
            gaps.append("srats %s has no trace to any hlr" % srats)
    for hlr in sorted(ids_by_level["hlr"]):
        if not _has_trace_from(inn, hlr, ("srats",)):
            gaps.append("hlr %s has no incoming srats trace" % hlr)
        if not _has_trace_to(out, hlr, ("llr",)):
            gaps.append("hlr %s has no trace to any llr" % hlr)
    for llr in sorted(ids_by_level["llr"]):
        if not _has_trace_from(inn, llr, ("hlr",)):
            gaps.append("llr %s has no incoming hlr trace" % llr)
        if not _has_trace_to(out, llr, ("code", "test")):
            gaps.append("llr %s has no trace to code or test" % llr)
    for link in sorted(links, key=lambda l: (l["from"], l["to"])):
        if link["verified"] is not True:
            gaps.append(
                "unverified trace %s -> %s" % (link["from"], link["to"])
            )
    return ("closed" if not gaps else "open", gaps)


def trace_gaps(links, level):
    """Gaps for one development level: the structural gaps at that level
    plus any unverified trace touching it."""
    if level not in LEVELS:
        raise ValueError("unknown level: %r" % (level,))
    _validate_links(links)
    out, inn, ids_by_level = _index_links(links)
    gaps = []
    if level == "srats":
        for req in sorted(ids_by_level["srats"]):
            if not _has_trace_to(out, req, ("hlr",)):
                gaps.append("srats %s has no trace to any hlr" % req)
    elif level == "hlr":
        for req in sorted(ids_by_level["hlr"]):
            if not _has_trace_from(inn, req, ("srats",)):
                gaps.append("hlr %s has no incoming srats trace" % req)
            if not _has_trace_to(out, req, ("llr",)):
                gaps.append("hlr %s has no trace to any llr" % req)
    elif level == "llr":
        for req in sorted(ids_by_level["llr"]):
            if not _has_trace_from(inn, req, ("hlr",)):
                gaps.append("llr %s has no incoming hlr trace" % req)
            if not _has_trace_to(out, req, ("code", "test")):
                gaps.append("llr %s has no trace to code or test" % req)
    else:  # code or test: each id must have an incoming trace
        for req in sorted(ids_by_level[level]):
            if not inn.get(req):
                gaps.append("%s %s has no incoming trace" % (level, req))
    for link in sorted(links, key=lambda l: (l["from"], l["to"])):
        if link["verified"] is not True:
            if _level_of(link["from"]) == level or _level_of(link["to"]) == level:
                gaps.append(
                    "unverified trace %s -> %s" % (link["from"], link["to"])
                )
    return gaps


def derived_requirement_flag(requirement_id):
    """True when the requirement id marks the requirement as derived."""
    return "derived" in requirement_id.lower()


def closure_ratio(links):
    """Fraction of traces verified, 0.0..1.0. Raises ValueError when the
    trace matrix is empty."""
    _validate_links(links)
    if not links:
        raise ValueError("links must not be empty")
    verified = sum(1 for l in links if l["verified"] is True)
    return verified / float(len(links))
