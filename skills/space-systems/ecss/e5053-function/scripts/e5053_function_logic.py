"""Function-subclause audit for SpaceWire service primitives.

Anchor: ECSS-E-ST-50-53 clause 5.2.2.1 (the function subclause of a service
primitive specification). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the service definition and every primitive record in it.
2. Resolve each primitive's function statement; absent, null and
   whitespace-only are the same defect.
3. Tokenise the primitive name and the statement, subtract the name tokens
   and a closed stopword set, and measure the informative content that is
   left. Below the floor the statement only restates the name.
4. Group any term owned by a neighbouring subclause (semantics, when
   generated, effect on receipt) so the finding names where it belongs.
5. Flag normative wording inside an informative subclause and a statement
   that runs past the sentence budget.
6. Compare normalised statements across the whole set and report every
   group of primitives that share one.
"""

import re

__all__ = [
    "MIN_INFORMATIVE_TOKENS",
    "MAX_SENTENCES",
    "STOPWORDS",
    "NORMATIVE_MARKERS",
    "LEAKAGE_TERMS",
    "SERVICE_ACTION_TERMS",
    "MAX_INFLECTION_SUFFIX",
    "normalize_statement",
    "tokenize",
    "primitive_name_tokens",
    "informative_tokens",
    "is_restatement",
    "sentence_count",
    "find_normative_wording",
    "detect_leakage",
    "action_terms",
    "assess_function_clause",
    "assess_primitive_set",
]

# A statement carrying fewer informative tokens than this adds nothing the
# primitive name did not already give the implementer.
MIN_INFORMATIVE_TOKENS = 3

# A function subclause running past this many sentences is normally two
# subclauses that have been merged.
MAX_SENTENCES = 2

STOPWORDS = frozenset(
    """a an and are as at be by for from in into is it its of on or that the this
    to with which while when whose primitive service used use uses using shall""".split()
)

NORMATIVE_MARKERS = (
    "shall",
    "must",
    "is required to",
    "are required to",
    "it is mandatory",
)

# Terms owned by the neighbouring subclauses of the same primitive. The key is
# the subclause the term belongs to, so a finding can name the destination.
LEAKAGE_TERMS = {
    "semantics": (
        "parameter",
        "parameters",
        "argument",
        "data type",
        "octet",
        "octets",
        "encoding",
        "field width",
        "bit field",
    ),
    "when generated": (
        "when generated",
        "is issued when",
        "is generated when",
        "on expiry",
        "timer expires",
        "timer expiry",
        "upon the event",
    ),
    "effect on receipt": (
        "on receipt",
        "effect on receipt",
        "the receiver enters",
        "receiving entity enters",
        "the peer enters",
        "state transition",
    ),
}

SERVICE_ACTION_TERMS = (
    "abort",
    "acknowledge",
    "carry",
    "confirm",
    "convey",
    "deliver",
    "establish",
    "indicate",
    "notify",
    "release",
    "report",
    "request",
    "reset",
    "signal",
    "transfer",
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_SENTENCE_RE = re.compile(r"[.!?]+")


def _require_text(value, label):
    """Return value as a str, raising when it is not text."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, type(value).__name__))
    return value


def normalize_statement(text):
    """Return the statement with collapsed whitespace and no surrounding space."""
    return " ".join(_require_text(text, "statement").split())


def tokenize(text):
    """Return the lowercase word tokens of a piece of text."""
    return _TOKEN_RE.findall(_require_text(text, "text").lower())


def primitive_name_tokens(name):
    """Return the token set of a primitive name such as T-Data.request."""
    text = _require_text(name, "primitive name").strip()
    if not text:
        raise ValueError("primitive name must not be empty")
    return frozenset(tokenize(text))


def informative_tokens(name, statement):
    """Return statement tokens that are neither name tokens nor stopwords.

    Order is preserved and repeats are dropped, so the result is what the
    statement adds over the primitive name, read left to right.
    """
    name_set = primitive_name_tokens(name)
    seen = set()
    out = []
    for token in tokenize(statement):
        if token in name_set or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def is_restatement(name, statement):
    """True when the statement adds too little over the primitive name."""
    return len(informative_tokens(name, statement)) < MIN_INFORMATIVE_TOKENS


def sentence_count(statement):
    """Return the number of sentences in a normalised statement."""
    text = normalize_statement(statement)
    if not text:
        return 0
    parts = [p.strip() for p in _SENTENCE_RE.split(text)]
    return len([p for p in parts if p])


def find_normative_wording(statement):
    """Return the normative markers present in an informative statement."""
    low = normalize_statement(statement).lower()
    return tuple(marker for marker in NORMATIVE_MARKERS if marker in low)


def detect_leakage(statement):
    """Return matched neighbouring-subclause terms grouped by owning subclause."""
    low = normalize_statement(statement).lower()
    grouped = {}
    for subclause, terms in LEAKAGE_TERMS.items():
        hits = tuple(term for term in terms if term in low)
        if hits:
            grouped[subclause] = hits
    return grouped


# A service-action term is written in whatever form the sentence needs, so the
# match tolerates the regular English inflections rather than the bare stem.
MAX_INFLECTION_SUFFIX = 3


def _matches_term(token, term):
    """True when a statement token is the term or a regular inflection of it."""
    if token == term:
        return True
    return token.startswith(term) and 0 < len(token) - len(term) <= MAX_INFLECTION_SUFFIX


def action_terms(statement):
    """Return the service-action terms the statement uses, inflections included."""
    tokens = tokenize(statement)
    return tuple(
        term
        for term in SERVICE_ACTION_TERMS
        if any(_matches_term(token, term) for token in tokens)
    )


def _resolve_record(record, index):
    """Return (primitive_name, raw_statement_or_None) from one record."""
    if not isinstance(record, dict):
        raise ValueError("primitive record %d must be a mapping" % index)
    if "primitive" not in record:
        raise ValueError("primitive record %d has no 'primitive' name" % index)
    name = _require_text(record["primitive"], "primitive record %d name" % index).strip()
    if not name:
        raise ValueError("primitive record %d has an empty name" % index)
    raw = record.get("function")
    if raw is not None and not isinstance(raw, str):
        raise ValueError("function subclause of %s must be text or null" % name)
    return name, raw


def assess_function_clause(record, index=0):
    """Assess the clause 5.2.2.1 function subclause of one primitive."""
    name, raw = _resolve_record(record, index)
    result = {
        "primitive": name,
        "statement": None,
        "present": False,
        "informative_tokens": [],
        "action_terms": (),
        "leakage": {},
        "normative_wording": (),
        "sentence_count": 0,
        "findings": [],
        "compliant": False,
    }
    statement = normalize_statement(raw) if isinstance(raw, str) else ""
    if not statement:
        result["findings"].append("%s has no function subclause" % name)
        return result
    result["statement"] = statement
    result["present"] = True
    result["informative_tokens"] = informative_tokens(name, statement)
    result["action_terms"] = action_terms(statement)
    result["leakage"] = detect_leakage(statement)
    result["normative_wording"] = find_normative_wording(statement)
    result["sentence_count"] = sentence_count(statement)
    if len(result["informative_tokens"]) < MIN_INFORMATIVE_TOKENS:
        result["findings"].append(
            "%s function statement restates the primitive name (%d informative token(s), "
            "floor %d)" % (name, len(result["informative_tokens"]), MIN_INFORMATIVE_TOKENS)
        )
    if not result["action_terms"]:
        result["findings"].append(
            "%s function statement names no service action" % name
        )
    for subclause in sorted(result["leakage"]):
        result["findings"].append(
            "%s function statement carries %s detail (%s)"
            % (name, subclause, ", ".join(result["leakage"][subclause]))
        )
    if result["normative_wording"]:
        result["findings"].append(
            "%s function statement uses normative wording (%s) in an informative subclause"
            % (name, ", ".join(result["normative_wording"]))
        )
    if result["sentence_count"] > MAX_SENTENCES:
        result["findings"].append(
            "%s function statement runs to %d sentences, budget %d"
            % (name, result["sentence_count"], MAX_SENTENCES)
        )
    result["compliant"] = not result["findings"]
    return result


def assess_primitive_set(records):
    """Audit the function subclause across a whole service definition."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of primitive records")
    results = []
    names = set()
    duplicates = {}
    for index, record in enumerate(records):
        result = assess_function_clause(record, index)
        key = result["primitive"].lower()
        if key in names:
            raise ValueError(
                "primitive %s is declared twice in the service definition"
                % result["primitive"]
            )
        names.add(key)
        results.append(result)
        if result["present"]:
            duplicates.setdefault(result["statement"].lower(), []).append(
                result["primitive"]
            )
    findings = []
    shared = []
    for statement in sorted(duplicates):
        owners = duplicates[statement]
        if len(owners) > 1:
            shared.append(tuple(owners))
            findings.append(
                "primitives %s share one function statement; all but one are undescribed"
                % ", ".join(owners)
            )
            for result in results:
                if result["primitive"] in owners:
                    result["compliant"] = False
    compliant_count = sum(1 for r in results if r["compliant"])
    return {
        "primitives": results,
        "shared_statements": shared,
        "findings": findings,
        "compliant_count": compliant_count,
        "total": len(results),
        "compliant": compliant_count == len(results) and not findings,
    }
