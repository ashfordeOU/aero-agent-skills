"""Traceability depth reached by lowest assurance class commercial EEE parts.

Anchor: ECSS-Q-ST-60-13C clause 6.5.4 (traceability records kept for commercial
parts at the lowest assurance class, from goods-in through to the assembly they
are fitted to). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the traceability records and the installations that consume them.
2. Resolve each installation back along parent references to a goods-in root,
   refusing a chain that loops and naming a chain that dies on a reference no
   record supplies.
3. Reduce every record on the chain to its effective depth, applying the cap a
   pooled batch may claim before anything is compared.
4. Take the achieved depth of an installation as the weakest link on its chain.
5. Compare every record date on the chain with the day the part was fitted.
6. Count the installations reaching the declared depth and compare that count
   with the coverage floor by exact integer cross-multiplication.
"""

__all__ = [
    "DEPTH_RANKS",
    "POOLED_DEPTH_CEILING",
    "DEFAULT_TRACEABILITY_POLICY",
    "TRACEABLE_TO_DEPTH",
    "TRACEABLE_WITH_SHORTFALLS",
    "COVERAGE_BELOW_FLOOR",
    "DATE_ORDER_CONTRADICTED",
    "CHAIN_UNRESOLVED",
    "validate_traceability_policy",
    "depth_rank",
    "validate_record",
    "index_records",
    "validate_installation",
    "effective_depth",
    "resolve_chain",
    "chain_depth",
    "coverage_meets_floor",
    "assess_traceability_depth",
]

# The four record depths this class recognises, weakest first. The rank is what
# gets compared; the token is what a record carries.
DEPTH_RANKS = {
    "part-number-only": 0,
    "delivery-batch": 1,
    "manufacturing-lot": 2,
    "unit-serial": 3,
}

# Once several deliveries have been drawn into one working batch the individual
# manufacturing identity is gone, so a pooled record cannot claim more than the
# batch it became, whatever its own label says.
POOLED_DEPTH_CEILING = 1

TRACEABLE_TO_DEPTH = "traceable-to-declared-depth"
TRACEABLE_WITH_SHORTFALLS = "traceable-with-shortfalls"
COVERAGE_BELOW_FLOOR = "coverage-below-floor"
DATE_ORDER_CONTRADICTED = "record-date-order-contradicted"
CHAIN_UNRESOLVED = "trace-chain-unresolved"

DEFAULT_TRACEABILITY_POLICY = {
    # Depth every fitted part is expected to reach at this class.
    "required_depth": "delivery-batch",
    # Share of fitted parts that must reach it, as an exact integer ratio.
    "coverage_numerator": 9,
    "coverage_denominator": 10,
    # Longest chain of records a resolution may walk before the folder is
    # treated as unmanageable rather than deep.
    "max_chain_hops": 6,
    # Whether a chain must terminate on a record marked as the goods-in entry.
    "require_goods_in_root": True,
}


def validate_traceability_policy(policy=None):
    """Return a complete traceability policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_TRACEABILITY_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("traceability policy must be a mapping")
    merged = dict(DEFAULT_TRACEABILITY_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_TRACEABILITY_POLICY:
            raise ValueError("unknown traceability policy key %r" % (key,))
        merged[key] = value
    if merged["required_depth"] not in DEPTH_RANKS:
        raise ValueError("unknown required_depth %r" % (merged["required_depth"],))
    for key in ("coverage_numerator", "coverage_denominator", "max_chain_hops"):
        value = merged[key]
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (key, value))
    if not isinstance(merged["require_goods_in_root"], bool):
        raise ValueError("require_goods_in_root must be a boolean")
    if merged["coverage_denominator"] <= 0:
        raise ValueError("coverage_denominator must be positive")
    if merged["coverage_numerator"] < 0:
        raise ValueError("coverage_numerator must not be negative")
    if merged["coverage_numerator"] > merged["coverage_denominator"]:
        raise ValueError("the coverage floor must not exceed the whole population")
    if merged["max_chain_hops"] < 1:
        raise ValueError("max_chain_hops must be at least one")
    return merged


def depth_rank(token):
    """Return the comparable rank of a declared record depth token."""
    if not isinstance(token, str) or not token.strip():
        raise ValueError("depth must be a non-empty token")
    name = token.strip()
    if name not in DEPTH_RANKS:
        raise ValueError("unknown record depth %r" % (token,))
    return DEPTH_RANKS[name]


def validate_record(record):
    """Return a normalised traceability record, raising on a malformed one."""
    if not isinstance(record, dict):
        raise ValueError("each record must be a mapping, got %r" % (type(record).__name__,))
    reference = record.get("reference")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("each record needs a non-empty 'reference'")
    normalised = {"reference": reference.strip()}
    normalised["depth"] = record.get("depth")
    normalised["rank"] = depth_rank(normalised["depth"])
    day = record.get("day")
    if not isinstance(day, int) or isinstance(day, bool):
        raise ValueError(
            "record %s needs an integer 'day'; a record without a date cannot be "
            "placed on the chain" % (normalised["reference"],)
        )
    if day < 0:
        raise ValueError("record %s has a negative day" % (normalised["reference"],))
    normalised["day"] = day
    parent = record.get("parent")
    if parent is not None:
        if not isinstance(parent, str) or not parent.strip():
            raise ValueError(
                "record %s has a blank 'parent'; use None for a goods-in root"
                % (normalised["reference"],)
            )
        parent = parent.strip()
    normalised["parent"] = parent
    pooled = record.get("pooled", False)
    if not isinstance(pooled, bool):
        raise ValueError("record %s has a non-boolean 'pooled'" % (normalised["reference"],))
    normalised["pooled"] = pooled
    goods_in = record.get("goods_in", parent is None)
    if not isinstance(goods_in, bool):
        raise ValueError("record %s has a non-boolean 'goods_in'" % (normalised["reference"],))
    normalised["goods_in"] = goods_in
    return normalised


def index_records(records):
    """Return the validated records keyed by reference."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    index = {}
    for record in records:
        normalised = validate_record(record)
        if normalised["reference"] in index:
            raise ValueError("duplicate record reference %r" % (normalised["reference"],))
        index[normalised["reference"]] = normalised
    return index


def validate_installation(installation):
    """Return a normalised installation record."""
    if not isinstance(installation, dict):
        raise ValueError(
            "each installation must be a mapping, got %r" % (type(installation).__name__,)
        )
    normalised = {}
    for field in ("part_id", "assembly", "record"):
        value = installation.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("each installation needs a non-empty '%s'" % field)
        normalised[field] = value.strip()
    day = installation.get("day")
    if not isinstance(day, int) or isinstance(day, bool):
        raise ValueError(
            "installation %s needs an integer 'day'" % (normalised["part_id"],)
        )
    if day < 0:
        raise ValueError("installation %s has a negative day" % (normalised["part_id"],))
    normalised["day"] = day
    return normalised


def effective_depth(record):
    """Return the depth a record may actually claim, pooling cap applied."""
    normalised = record if "rank" in record else validate_record(record)
    if normalised["pooled"]:
        return min(normalised["rank"], POOLED_DEPTH_CEILING)
    return normalised["rank"]


def resolve_chain(index, reference, max_hops):
    """Walk parent references from one record back towards a goods-in root.

    Returns a dict with the resolved chain, whether it terminated, and the
    reference it died on when it did not. A chain that loops is malformed input.
    """
    if not isinstance(index, dict) or not index:
        raise ValueError("index must be a non-empty mapping of records")
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("reference must be a non-empty string")
    if not isinstance(max_hops, int) or isinstance(max_hops, bool) or max_hops < 1:
        raise ValueError("max_hops must be a positive integer")
    chain = []
    seen = set()
    current = reference.strip()
    truncated = False
    while True:
        if current in seen:
            raise ValueError("traceability chain loops at record %r" % (current,))
        seen.add(current)
        record = index.get(current)
        if record is None:
            return {
                "chain": chain,
                "resolved": False,
                "missing_reference": current,
                "truncated": False,
                "hops": len(chain),
            }
        chain.append(record)
        if len(chain) > max_hops:
            truncated = True
            break
        if record["parent"] is None:
            break
        current = record["parent"]
    return {
        "chain": chain,
        "resolved": not truncated,
        "missing_reference": None,
        "truncated": truncated,
        "hops": len(chain),
    }


def chain_depth(chain):
    """Return the weakest effective depth on a resolved chain, and its link."""
    if not isinstance(chain, (list, tuple)) or not chain:
        raise ValueError("chain must be a non-empty sequence of records")
    weakest = None
    weakest_reference = None
    for record in chain:
        value = effective_depth(record)
        if weakest is None or value < weakest:
            weakest = value
            weakest_reference = record["reference"]
    return {"rank": weakest, "set_by": weakest_reference}


def coverage_meets_floor(met, total, numerator, denominator):
    """Return whether met/total reaches numerator/denominator, in integers only."""
    for name, value in (("met", met), ("total", total),
                        ("numerator", numerator), ("denominator", denominator)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer, got %r" % (name, value))
    if total <= 0:
        raise ValueError("total must be positive")
    if met < 0 or met > total:
        raise ValueError("met must lie between zero and the total")
    if denominator <= 0:
        raise ValueError("denominator must be positive")
    # Cross-multiplied: a population sitting exactly on the floor is met, and it
    # is met identically on every machine.
    return met * denominator >= numerator * total


def assess_traceability_depth(case):
    """Run the clause 6.5.4 traceability assessment over a fitted population.

    case keys: records (sequence of traceability records), installations
    (sequence of fitted-part records), optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("records", "installations"):
        if key not in case:
            raise ValueError("case missing required key %r" % (key,))
    settings = validate_traceability_policy(case.get("policy"))
    index = index_records(case["records"])
    raw_installations = case["installations"]
    if not isinstance(raw_installations, (list, tuple)) or not raw_installations:
        raise ValueError("installations must be a non-empty sequence")
    installations = []
    seen_parts = set()
    for entry in raw_installations:
        normalised = validate_installation(entry)
        if normalised["part_id"] in seen_parts:
            raise ValueError("duplicate installed part id %r" % (normalised["part_id"],))
        seen_parts.add(normalised["part_id"])
        installations.append(normalised)

    required_rank = DEPTH_RANKS[settings["required_depth"]]
    findings = []
    results = []
    unresolved = []
    date_conflicts = []
    shortfalls = []
    met = 0

    for installation in installations:
        walk = resolve_chain(index, installation["record"], settings["max_chain_hops"])
        entry = {
            "part_id": installation["part_id"],
            "assembly": installation["assembly"],
            "hops": walk["hops"],
        }
        if not walk["resolved"]:
            entry["achieved_depth"] = None
            entry["achieved_rank"] = None
            entry["resolved"] = False
            if walk["missing_reference"] is not None:
                entry["missing_reference"] = walk["missing_reference"]
                findings.append(
                    "part %s has a chain dying on record %s, which no folder supplies"
                    % (installation["part_id"], walk["missing_reference"])
                )
            else:
                entry["missing_reference"] = None
                findings.append(
                    "part %s walks more than %d records without reaching goods-in"
                    % (installation["part_id"], settings["max_chain_hops"])
                )
            unresolved.append(installation["part_id"])
            results.append(entry)
            continue

        entry["resolved"] = True
        entry["missing_reference"] = None
        weakest = chain_depth(walk["chain"])
        entry["achieved_rank"] = weakest["rank"]
        entry["achieved_depth"] = _depth_token(weakest["rank"])
        entry["depth_set_by"] = weakest["set_by"]

        late = [r["reference"] for r in walk["chain"] if r["day"] > installation["day"]]
        entry["records_dated_after_installation"] = late
        if late:
            date_conflicts.append(installation["part_id"])
            findings.append(
                "part %s was fitted on day %d ahead of record %s"
                % (installation["part_id"], installation["day"], late[0])
            )

        root = walk["chain"][-1]
        entry["root_is_goods_in"] = bool(root["goods_in"])
        if settings["require_goods_in_root"] and not root["goods_in"]:
            unresolved.append(installation["part_id"])
            entry["resolved"] = False
            findings.append(
                "part %s terminates on record %s, which is not a goods-in entry"
                % (installation["part_id"], root["reference"])
            )
            results.append(entry)
            continue

        if weakest["rank"] >= required_rank:
            met += 1
        else:
            shortfalls.append(installation["part_id"])
            findings.append(
                "part %s reaches only %s against the required %s, set by record %s"
                % (installation["part_id"], entry["achieved_depth"],
                   settings["required_depth"], weakest["set_by"])
            )
        results.append(entry)

    total = len(installations)
    coverage_met = coverage_meets_floor(
        met, total, settings["coverage_numerator"], settings["coverage_denominator"]
    )

    if unresolved:
        verdict = CHAIN_UNRESOLVED
    elif date_conflicts:
        verdict = DATE_ORDER_CONTRADICTED
    elif not coverage_met:
        verdict = COVERAGE_BELOW_FLOOR
    elif shortfalls:
        verdict = TRACEABLE_WITH_SHORTFALLS
    else:
        verdict = TRACEABLE_TO_DEPTH

    return {
        "verdict": verdict,
        "required_depth": settings["required_depth"],
        "installations_assessed": total,
        "installations_at_depth": met,
        "coverage_fraction": float(met) / float(total),
        "coverage_meets_floor": coverage_met,
        "unresolved_parts": unresolved,
        "date_conflict_parts": date_conflicts,
        "shortfall_parts": shortfalls,
        "per_installation": results,
        "traceable": verdict in (TRACEABLE_TO_DEPTH, TRACEABLE_WITH_SHORTFALLS),
        "findings": findings,
    }


def _depth_token(rank):
    """Return the depth token carrying a given rank."""
    for token, value in DEPTH_RANKS.items():
        if value == rank:
            return token
    raise ValueError("no depth token for rank %r" % (rank,))
