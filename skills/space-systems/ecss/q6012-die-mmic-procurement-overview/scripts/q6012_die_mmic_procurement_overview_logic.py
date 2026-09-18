"""Clause routing and scope map for a die-form MMIC procurement case.

Anchor: ECSS-Q-ST-60-12C clause 4.1 (the context in which bare monolithic
microwave dies are bought, and the map of the clauses that follow from it).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate and normalise the procurement case: whether the item is bought in
   die form or already packaged, the standing of the foundry, the model the
   dies are destined for, the quality level on the order, the programme floor
   the order is placed against, and whether lot acceptance data comes with it.
2. Fire every clause area's own applicability rule against the case and keep
   the reason the rule returned, so a routed area carries why it was routed.
3. Close the routed set under its prerequisites: an area whose output another
   routed area consumes is pulled in, and a pulled-in area is marked as such
   instead of being merged with the directly applicable ones.
4. Order the closed set so no area is entered before the areas it depends on,
   breaking ties on registry order so the map is reproducible, and refusing a
   dependency cycle rather than emitting an arbitrary order for it.
5. Report the ordered map, the fraction of the registry it covers, and the
   findings a reviewer clears before the order leaves the building.
"""

__all__ = [
    "DIE_FORMS",
    "FOUNDRY_STANDINGS",
    "BUILD_MODELS",
    "QUALITY_TOKENS",
    "CLAUSE_KEYS",
    "validate_case",
    "clause_titles",
    "clause_dependencies",
    "applicable_clauses",
    "close_under_dependencies",
    "topological_order",
    "dependency_order",
    "route_map",
    "coverage_ratio",
    "scope_findings",
    "assess_procurement_scope",
]

# The standard covers bare die; a packaged part is bought through a different
# route and is reported as out of scope rather than mapped anyway.
DIE_FORMS = ("die", "packaged")

FOUNDRY_STANDINGS = ("qualified", "evaluated", "unassessed")

BUILD_MODELS = ("em", "eqm", "fm")

# Ascending quality order. Only the ordering is used here; the floor itself is
# the job of the minimum-baseline clause, not of the scope map.
QUALITY_TOKENS = ("commercial", "industrial", "level-3", "level-2", "level-1")

_REQUIRED_CASE_KEYS = (
    "form",
    "foundry_standing",
    "model",
    "quality_level",
    "programme_floor",
)

_OPTIONAL_CASE_DEFAULTS = {
    "lot_acceptance_data": False,
    "assembled_in_house": False,
    "radiation_environment": False,
    "die_count": 1,
}


def _rule_scope(case):
    return True, "every die-form purchase is entered through the scope clause"


def _rule_foundry_selection(case):
    standing = case["foundry_standing"]
    if standing == "qualified":
        return True, "a qualified foundry still has to be confirmed valid at wafer start"
    return True, "foundry standing is '%s', so selection evidence is owed" % standing


def _rule_quality_baseline(case):
    return True, "the lowest acceptable die quality level is set for every build"


def _rule_lot_procurement(case):
    if case["model"] in ("eqm", "fm"):
        return True, "a %s build buys its dies as one identified wafer lot" % case["model"].upper()
    return False, "an EM build may draw dies from stock without a dedicated lot"


def _rule_lot_acceptance(case):
    if case["model"] == "fm":
        return True, "a flight lot owes lot acceptance evidence before delivery"
    if case["lot_acceptance_data"]:
        return True, "lot acceptance data is offered with the order and has to be graded"
    return False, "no flight lot and no offered acceptance data"


def _rule_die_screening(case):
    if case["model"] == "fm":
        return True, "flight dies are screened before they reach an assembly"
    if _below_floor(case):
        return True, "the offered level sits under the programme floor, so screening is the bridge"
    return False, "the offered level already meets the programme floor on a non-flight build"


def _rule_radiation_evaluation(case):
    if case["radiation_environment"]:
        return True, "the dies see a radiation environment, so evaluation data is owed"
    return False, "no radiation environment declared for this equipment"


def _rule_handling_and_storage(case):
    return True, "bare die is handled and stored under its own controls from delivery"


def _rule_assembly_and_attachment(case):
    if case["assembled_in_house"]:
        return True, "the dies are attached in house, so the attachment process is in the map"
    return False, "the dies are delivered already attached by the supplier"


def _rule_traceability(case):
    return True, "die identity is carried from wafer through to the equipment build"


# key, title, dependency keys, applicability rule.
_CLAUSE_REGISTRY = (
    ("scope-and-applicability", "Die-form scope and applicability", (), _rule_scope),
    ("foundry-selection", "Foundry selection and standing", ("scope-and-applicability",), _rule_foundry_selection),
    ("quality-baseline", "Minimum die quality baseline", ("scope-and-applicability",), _rule_quality_baseline),
    ("handling-and-storage", "Bare die handling and storage", ("scope-and-applicability",), _rule_handling_and_storage),
    ("lot-procurement", "Flight die lot procurement", ("foundry-selection",), _rule_lot_procurement),
    ("traceability-records", "Die traceability records", ("foundry-selection",), _rule_traceability),
    ("lot-acceptance", "Wafer lot acceptance evidence", ("lot-procurement",), _rule_lot_acceptance),
    ("die-screening", "Die screening and upgrade", ("quality-baseline",), _rule_die_screening),
    ("radiation-evaluation", "Radiation evaluation of the die", ("quality-baseline",), _rule_radiation_evaluation),
    ("assembly-and-attachment", "Die attachment and assembly", ("handling-and-storage",), _rule_assembly_and_attachment),
)

CLAUSE_KEYS = tuple(entry[0] for entry in _CLAUSE_REGISTRY)

_CLAUSE_INDEX = {key: i for i, key in enumerate(CLAUSE_KEYS)}


def clause_titles():
    """Return the registry as an ordered mapping of clause key to title."""
    return {entry[0]: entry[1] for entry in _CLAUSE_REGISTRY}


def clause_dependencies():
    """Return the registry dependency graph as clause key to prerequisite keys."""
    return {entry[0]: tuple(entry[2]) for entry in _CLAUSE_REGISTRY}


def _below_floor(case):
    """Return True when the ordered quality level sits under the programme floor."""
    return QUALITY_TOKENS.index(case["quality_level"]) < QUALITY_TOKENS.index(case["programme_floor"])


def validate_case(spec):
    """Return the normalised procurement case built from spec.

    Unknown keys are refused rather than ignored: a misspelt flag that silently
    defaults would drop a whole clause area out of the map.
    """
    if not isinstance(spec, dict):
        raise ValueError("procurement case must be a mapping")
    for key in _REQUIRED_CASE_KEYS:
        if key not in spec:
            raise ValueError("procurement case missing required key '%s'" % key)
    allowed = set(_REQUIRED_CASE_KEYS) | set(_OPTIONAL_CASE_DEFAULTS)
    for key in spec:
        if key not in allowed:
            raise ValueError("procurement case carries unknown key '%s'" % key)

    case = {}
    for key, table in (
        ("form", DIE_FORMS),
        ("foundry_standing", FOUNDRY_STANDINGS),
        ("model", BUILD_MODELS),
        ("quality_level", QUALITY_TOKENS),
        ("programme_floor", QUALITY_TOKENS),
    ):
        value = spec[key]
        if not isinstance(value, str):
            raise ValueError("%s must be a string token" % key)
        token = value.strip().lower()
        if token not in table:
            raise ValueError("%s '%s' is not one of %s" % (key, value, ", ".join(table)))
        case[key] = token

    for key, default in _OPTIONAL_CASE_DEFAULTS.items():
        value = spec.get(key, default)
        if key == "die_count":
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("die_count must be an integer")
            if value < 1:
                raise ValueError("die_count must be at least 1, got %d" % value)
            case[key] = value
        else:
            if not isinstance(value, bool):
                raise ValueError("%s must be a boolean" % key)
            case[key] = value
    return case


def applicable_clauses(case):
    """Return the directly applicable clause records, in registry order."""
    if not isinstance(case, dict) or "form" not in case:
        raise ValueError("case must be a normalised procurement case mapping")
    records = []
    for key, title, _deps, rule in _CLAUSE_REGISTRY:
        applies, reason = rule(case)
        if applies:
            records.append({"key": key, "title": title, "reason": reason, "pulled_in": False})
    return records


def close_under_dependencies(keys):
    """Return the key set closed under its prerequisites, plus the pulled-in keys."""
    if not isinstance(keys, (list, tuple, set, frozenset)):
        raise ValueError("keys must be a collection of clause keys")
    graph = clause_dependencies()
    selected = set()
    for key in keys:
        if key not in graph:
            raise ValueError("unknown clause key '%s'" % (key,))
        selected.add(key)
    direct = set(selected)
    pending = list(selected)
    while pending:
        key = pending.pop()
        for dep in graph[key]:
            if dep not in selected:
                selected.add(dep)
                pending.append(dep)
    pulled_in = sorted(selected - direct, key=lambda k: _CLAUSE_INDEX[k])
    closed = sorted(selected, key=lambda k: _CLAUSE_INDEX[k])
    return closed, pulled_in


def topological_order(nodes, graph, rank=None):
    """Order nodes so no node precedes a prerequisite; refuse a cycle.

    graph maps a node to the nodes it depends on. rank, when given, maps a node
    to a sort key used to break ties so the order is reproducible.
    """
    if not isinstance(graph, dict):
        raise ValueError("graph must be a mapping of node to prerequisite nodes")
    selected = list(nodes)
    seen = set()
    for node in selected:
        if node in seen:
            raise ValueError("node '%s' listed more than once" % (node,))
        seen.add(node)
        if node not in graph:
            raise ValueError("node '%s' is absent from the graph" % (node,))
    if rank is None:
        order_key = {node: i for i, node in enumerate(selected)}
        rank = order_key.__getitem__
    remaining = set(selected)
    ordered = []
    while remaining:
        ready = [n for n in remaining if not (set(graph[n]) & remaining)]
        if not ready:
            raise ValueError(
                "dependency cycle among %s" % ", ".join(sorted(str(n) for n in remaining))
            )
        ready.sort(key=rank)
        chosen = ready[0]
        ordered.append(chosen)
        remaining.discard(chosen)
    return ordered


def dependency_order(keys):
    """Return the given clause keys in prerequisite-respecting registry order."""
    closed, _pulled = close_under_dependencies(keys)
    return topological_order(closed, clause_dependencies(), rank=_CLAUSE_INDEX.__getitem__)


def route_map(case):
    """Return the ordered clause route for a normalised case."""
    direct = applicable_clauses(case)
    titles = clause_titles()
    graph = clause_dependencies()
    closed, pulled_in = close_under_dependencies([r["key"] for r in direct])
    ordered = topological_order(closed, graph, rank=_CLAUSE_INDEX.__getitem__)
    by_key = {r["key"]: r for r in direct}
    route = []
    for position, key in enumerate(ordered, start=1):
        record = by_key.get(key)
        if record is None:
            record = {
                "key": key,
                "title": titles[key],
                "reason": "pulled in as a prerequisite of a routed clause area",
                "pulled_in": True,
            }
        else:
            record = dict(record)
            record["pulled_in"] = key in pulled_in
        record["position"] = position
        record["depends_on"] = graph[key]
        route.append(record)
    return route


def coverage_ratio(route):
    """Return the fraction of the clause registry the route covers."""
    if not isinstance(route, (list, tuple)):
        raise ValueError("route must be a sequence of clause records")
    keys = set()
    for record in route:
        if not isinstance(record, dict) or "key" not in record:
            raise ValueError("each route record must be a mapping carrying 'key'")
        if record["key"] not in _CLAUSE_INDEX:
            raise ValueError("unknown clause key '%s' in route" % (record["key"],))
        keys.add(record["key"])
    return len(keys) / float(len(CLAUSE_KEYS))


def scope_findings(case):
    """Return the findings a reviewer clears before the die order is released."""
    findings = []
    if case["form"] != "die":
        findings.append(
            "the case declares a packaged part; the die-form clause map does not cover it"
        )
    if case["model"] == "fm" and case["foundry_standing"] == "unassessed":
        findings.append(
            "a flight build is pointed at an unassessed foundry; selection evidence is owed first"
        )
    if case["model"] == "fm" and not case["lot_acceptance_data"]:
        findings.append(
            "a flight build carries no lot acceptance data; the lot cannot be graded on delivery"
        )
    if _below_floor(case):
        findings.append(
            "offered level '%s' sits below the programme floor '%s'; an upgrade route is required"
            % (case["quality_level"], case["programme_floor"])
        )
    if case["assembled_in_house"] and case["model"] == "fm" and not case["radiation_environment"]:
        findings.append(
            "flight dies are attached in house with no radiation environment declared; "
            "confirm the omission is deliberate"
        )
    return findings


def assess_procurement_scope(spec):
    """Run the full clause 4.1 scope-and-route assessment for a procurement case."""
    case = validate_case(spec)
    findings = scope_findings(case)
    if case["form"] != "die":
        route = route_map({**case, "form": "die"})
        route = [r for r in route if r["key"] == "scope-and-applicability"]
        return {
            "case": case,
            "in_scope": False,
            "route": route,
            "pulled_in": [],
            "coverage_ratio": coverage_ratio(route),
            "findings": findings,
            "clear": False,
        }
    route = route_map(case)
    pulled_in = [r["key"] for r in route if r["pulled_in"]]
    return {
        "case": case,
        "in_scope": True,
        "route": route,
        "pulled_in": pulled_in,
        "coverage_ratio": coverage_ratio(route),
        "findings": findings,
        "clear": not findings,
    }
