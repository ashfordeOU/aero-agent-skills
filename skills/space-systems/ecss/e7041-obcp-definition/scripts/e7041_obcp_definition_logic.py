"""Definition of an on-board control procedure (OBCP).

Anchor: ECSS-E-ST-70-41C clause 6.18.4.1 (paraphrased into an
implementable procedure; no standard text is reproduced).

What an OBCP definition is. An on-board control procedure is a small
program the spacecraft runs by itself, so that a sequence that must
react faster than a round trip -- a safing chain, a deployment, an
instrument warm-up -- does not have to wait for the ground. The
definition is everything the ground hands over before the procedure can
ever be run: an identity, a version, the engine that interprets it, the
code itself, the arguments the ground may set at activation, and the
observability level the ground expects to watch it at.

A definition is not a running procedure. It is the static, checkable
part, and checking it here is the last chance to catch a mistake while
it is still cheap. Every fault this module raises is one that would
otherwise be found by an on-board engine that cannot ask a question.

The four things a definition has to settle:

  identity   -- an id unique in the on-board store, and a version, so
                the ground and the spacecraft can never disagree about
                which of two procedures with the same name is aboard.
  engine     -- which interpreter runs it. An engine has a language and
                a maximum procedure size, and a procedure written for
                one engine is not runnable by another.
  arguments  -- the named, typed values the ground supplies when it
                activates the procedure. A declared argument either has
                a default or it is mandatory; a mandatory one with no
                value at activation is an activation that must not
                happen.
  observability -- the level at which the ground expects to see the
                procedure run. It belongs to the definition because it
                decides what the engine has to instrument before the
                procedure is ever loaded, not after.

Stdlib only, offline, deterministic.
"""

import hashlib

ARG_TYPE_INTEGER = "integer"
ARG_TYPE_REAL = "real"
ARG_TYPE_BOOLEAN = "boolean"
ARG_TYPE_STRING = "string"
VALID_ARGUMENT_TYPES = (
    ARG_TYPE_INTEGER,
    ARG_TYPE_REAL,
    ARG_TYPE_BOOLEAN,
    ARG_TYPE_STRING,
)

OBSERVABILITY_NONE = "none"
OBSERVABILITY_PROCEDURE = "procedure"
OBSERVABILITY_STEP = "step"
VALID_OBSERVABILITY_LEVELS = (
    OBSERVABILITY_NONE,
    OBSERVABILITY_PROCEDURE,
    OBSERVABILITY_STEP,
)

ADMISSIBLE = "admissible"
REJECTED_UNKNOWN_ENGINE = "rejected-unknown-engine"
REJECTED_OVER_ENGINE_LIMIT = "rejected-over-engine-procedure-size-limit"
REJECTED_STORE_FULL = "rejected-definition-store-full"


def _integer(label, value, minimum=None):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %d, got %d" % (label, minimum, value))
    return value


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def value_matches_type(declared_type, value):
    """Does a supplied value match a declared argument type?"""
    if declared_type not in VALID_ARGUMENT_TYPES:
        raise ValueError("unknown argument type %r" % (declared_type,))
    if declared_type == ARG_TYPE_BOOLEAN:
        return isinstance(value, bool)
    if declared_type == ARG_TYPE_INTEGER:
        return isinstance(value, int) and not isinstance(value, bool)
    if declared_type == ARG_TYPE_REAL:
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, str)


def validate_argument(argument):
    """Validate one declared procedure argument and return a normalized copy."""
    if not isinstance(argument, dict):
        raise ValueError("procedure argument must be a mapping")
    name = _text("argument name", argument.get("name"))
    arg_type = argument.get("type")
    if arg_type not in VALID_ARGUMENT_TYPES:
        raise ValueError(
            "argument %s has unknown type %r (expected one of %s)"
            % (name, arg_type, ", ".join(VALID_ARGUMENT_TYPES))
        )
    normalized = {"name": name, "type": arg_type, "has_default": False,
                  "default": None}
    if "default" in argument and argument["default"] is not None:
        default = argument["default"]
        if not value_matches_type(arg_type, default):
            raise ValueError(
                "argument %s declares a %s default of %r, which is not a %s"
                % (name, arg_type, default, arg_type)
            )
        normalized["has_default"] = True
        normalized["default"] = default
    return normalized


def validate_engine(engine):
    """Validate one OBCP engine declaration."""
    if not isinstance(engine, dict):
        raise ValueError("engine must be a mapping")
    engine_id = _text("engine id", engine.get("id"))
    language = _text("engine %s language" % engine_id, engine.get("language"))
    limit = _integer(
        "engine %s max_procedure_octets" % engine_id,
        engine.get("max_procedure_octets"), 1,
    )
    levels = engine.get("observability_levels", list(VALID_OBSERVABILITY_LEVELS))
    if not isinstance(levels, (list, tuple)) or not levels:
        raise ValueError(
            "engine %s must support at least one observability level" % engine_id
        )
    for level in levels:
        if level not in VALID_OBSERVABILITY_LEVELS:
            raise ValueError(
                "engine %s declares unknown observability level %r"
                % (engine_id, level)
            )
    return {
        "id": engine_id,
        "language": language,
        "max_procedure_octets": limit,
        "observability_levels": list(levels),
    }


def validate_definition(definition):
    """Validate one OBCP definition and return a normalized copy."""
    if not isinstance(definition, dict):
        raise ValueError("OBCP definition must be a mapping")
    proc_id = _text("OBCP id", definition.get("id"))
    version = _integer("OBCP %s version" % proc_id, definition.get("version"), 1)
    engine_id = _text("OBCP %s engine_id" % proc_id, definition.get("engine_id"))
    code_octets = _integer(
        "OBCP %s code_octets" % proc_id, definition.get("code_octets"), 1
    )
    step_count = _integer(
        "OBCP %s step_count" % proc_id, definition.get("step_count"), 1
    )
    level = definition.get("observability_level", OBSERVABILITY_PROCEDURE)
    if level not in VALID_OBSERVABILITY_LEVELS:
        raise ValueError(
            "OBCP %s declares unknown observability level %r" % (proc_id, level)
        )
    raw_arguments = definition.get("arguments", [])
    if not isinstance(raw_arguments, (list, tuple)):
        raise ValueError("OBCP %s arguments must be a list" % proc_id)
    arguments = []
    seen = set()
    for argument in raw_arguments:
        normalized = validate_argument(argument)
        if normalized["name"] in seen:
            raise ValueError(
                "OBCP %s declares argument %s twice"
                % (proc_id, normalized["name"])
            )
        seen.add(normalized["name"])
        arguments.append(normalized)
    return {
        "id": proc_id,
        "version": version,
        "engine_id": engine_id,
        "code_octets": code_octets,
        "step_count": step_count,
        "observability_level": level,
        "arguments": arguments,
    }


def argument_signature(definition):
    """Ordered list of declared argument names."""
    return [a["name"] for a in validate_definition(definition)["arguments"]]


def mandatory_arguments(definition):
    """Names of arguments the ground must supply at activation."""
    return [
        a["name"]
        for a in validate_definition(definition)["arguments"]
        if not a["has_default"]
    ]


def default_arguments(definition):
    """Mapping of argument name to declared default, defaults only."""
    return {
        a["name"]: a["default"]
        for a in validate_definition(definition)["arguments"]
        if a["has_default"]
    }


def bind_arguments(definition, supplied):
    """Bind ground-supplied values onto a definition's declared arguments."""
    working = validate_definition(definition)
    if supplied is None:
        supplied = {}
    if not isinstance(supplied, dict):
        raise ValueError("supplied arguments must be a mapping")
    declared = {a["name"]: a for a in working["arguments"]}
    unknown = sorted(set(supplied) - set(declared))
    if unknown:
        raise ValueError(
            "OBCP %s was given undeclared argument(s): %s"
            % (working["id"], ", ".join(unknown))
        )
    bound = {}
    for name, argument in declared.items():
        if name in supplied:
            value = supplied[name]
            if not value_matches_type(argument["type"], value):
                raise ValueError(
                    "OBCP %s argument %s expects a %s, got %r"
                    % (working["id"], name, argument["type"], value)
                )
            bound[name] = value
        elif argument["has_default"]:
            bound[name] = argument["default"]
        else:
            raise ValueError(
                "OBCP %s argument %s is mandatory and was not supplied"
                % (working["id"], name)
            )
    return bound


def definition_digest(definition):
    """Deterministic digest over the fields that make a definition itself."""
    working = validate_definition(definition)
    parts = [
        working["id"],
        str(working["version"]),
        working["engine_id"],
        str(working["code_octets"]),
        str(working["step_count"]),
        working["observability_level"],
    ]
    for argument in working["arguments"]:
        parts.append(
            "%s:%s:%s:%r"
            % (
                argument["name"], argument["type"],
                "d" if argument["has_default"] else "m", argument["default"],
            )
        )
    payload = "|".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def definitions_agree(left, right):
    """Do two definitions describe the same procedure in every graded field?"""
    return definition_digest(left) == definition_digest(right)


def assess_definition(definition, engines):
    """Assess one definition against the engines the spacecraft carries."""
    working = validate_definition(definition)
    catalogue = {}
    for engine in engines:
        normalized = validate_engine(engine)
        if normalized["id"] in catalogue:
            raise ValueError("duplicate engine id %r" % (normalized["id"],))
        catalogue[normalized["id"]] = normalized
    findings = []
    engine = catalogue.get(working["engine_id"])
    if engine is None:
        return {
            "id": working["id"],
            "version": working["version"],
            "disposition": REJECTED_UNKNOWN_ENGINE,
            "findings": [
                "no engine %s aboard; the definition names an interpreter "
                "the spacecraft does not carry" % working["engine_id"]
            ],
            "code_octets": working["code_octets"],
        }
    if working["code_octets"] > engine["max_procedure_octets"]:
        return {
            "id": working["id"],
            "version": working["version"],
            "disposition": REJECTED_OVER_ENGINE_LIMIT,
            "findings": [
                "procedure is %d octets against an engine limit of %d"
                % (working["code_octets"], engine["max_procedure_octets"])
            ],
            "code_octets": working["code_octets"],
        }
    if working["observability_level"] not in engine["observability_levels"]:
        findings.append(
            "engine %s cannot observe at level %s; the ground will see less "
            "than the definition promises"
            % (engine["id"], working["observability_level"])
        )
    if mandatory_arguments(working):
        findings.append(
            "activation needs %d mandatory argument(s): %s"
            % (
                len(mandatory_arguments(working)),
                ", ".join(mandatory_arguments(working)),
            )
        )
    return {
        "id": working["id"],
        "version": working["version"],
        "disposition": ADMISSIBLE,
        "findings": findings,
        "code_octets": working["code_octets"],
    }


def assess_definition_set(definitions, engines, store_capacity_octets):
    """Assess a whole set of definitions against the engines and the store."""
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("definitions must be a non-empty list")
    capacity = _integer("store_capacity_octets", store_capacity_octets, 1)
    seen = {}
    results = []
    used = 0
    for definition in definitions:
        working = validate_definition(definition)
        key = (working["id"], working["version"])
        if key in seen:
            raise ValueError(
                "definition %s version %d appears twice" % (working["id"],
                                                            working["version"])
            )
        seen[key] = True
        result = assess_definition(working, engines)
        if result["disposition"] == ADMISSIBLE:
            if used + working["code_octets"] > capacity:
                result = dict(result)
                result["disposition"] = REJECTED_STORE_FULL
                result["findings"] = [
                    "definition store has %d of %d octets free, the procedure "
                    "needs %d" % (capacity - used, capacity,
                                  working["code_octets"])
                ]
            else:
                used += working["code_octets"]
        results.append(result)
    admissible = [r for r in results if r["disposition"] == ADMISSIBLE]
    grouped = {}
    for result in results:
        grouped.setdefault(result["disposition"], []).append(result["id"])
    return {
        "results": results,
        "grouped_by_disposition": grouped,
        "admissible_count": len(admissible),
        "rejected_count": len(results) - len(admissible),
        "used_octets": used,
        "free_octets": capacity - used,
        "capacity_octets": capacity,
        "fill_fraction": used / float(capacity),
        "all_admissible": len(admissible) == len(results),
    }
