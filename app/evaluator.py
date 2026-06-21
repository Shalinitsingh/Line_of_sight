"""
Hardened formula evaluator. The expression string is AI/user-influenced text, so it is
NEVER passed to eval(). asteval runs it in a restricted interpreter: no imports, no
attribute access to dunder, no file/system access.

Variables are numeric arrays pulled from JSONB. Aggregation helpers (sum/avg/...) turn
them into the scalar a KPI needs. The LLM only proposes the string; math happens here.
"""

from __future__ import annotations

from asteval import Interpreter


def _avg(x):
    x = list(x)
    return sum(x) / len(x) if x else 0.0


_AGG = {
    "sum": lambda x: float(sum(x)),
    "avg": _avg,
    "mean": _avg,
    "min": lambda x: float(min(x)) if x else 0.0,
    "max": lambda x: float(max(x)) if x else 0.0,
    "count": lambda x: float(len(x)),
    "abs": abs,
    "round": round,
}


class FormulaError(ValueError):
    pass


def evaluate(expression: str, variables: dict[str, list[float]]):
    """
    Evaluate `expression` with each variable bound to its numeric array.
    Returns a scalar (or list). Raises FormulaError on any failure.
    """
    aeval = Interpreter(
        usersyms={**variables, **_AGG},
        no_print=True,
        minimal=True,
        readonly_symbols=set(_AGG),
    )
    try:
        result = aeval(expression, raise_errors=True)
    except Exception as exc:  # asteval re-raises sandbox + math errors
        raise FormulaError(str(exc)) from exc
    if aeval.error:
        raise FormulaError("; ".join(e.get_error()[1] for e in aeval.error))
    if result is None:
        raise FormulaError("expression produced no value")
    return result
