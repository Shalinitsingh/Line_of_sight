"""
AI Formula Assistant (the 'Cognitive Translator' from the PRD).

Given a plain-language KPI goal and the available numeric columns, it proposes a
math STRING plus which columns map to which variables. It never does arithmetic and
never touches raw data — that is the calculator's job. Output is a proposal that lands
in the 'placeholder' as a DRAFT formula until a human validates it.

Falls back to a deterministic heuristic when no ANTHROPIC_API_KEY is set, so the system
is fully runnable offline.
"""

from __future__ import annotations

import json

from .config import get_settings

settings = get_settings()

_SYSTEM = (
    "You translate a business KPI goal into a single math expression over provided "
    "column variables. Use only these aggregate functions: sum, avg, min, max, count. "
    "Reference variables by their exact `key`. Respond ONLY with JSON: "
    '{"expression": "...", "variables": ["key1","key2"], "rationale": "..."}. '
    "No prose, no code fences."
)


def _heuristic(goal: str, columns: list[dict]) -> dict:
    """Cheap, deterministic proposal: ratio of two goal-relevant numeric columns."""
    numeric = [c for c in columns if c.get("numeric")]
    if not numeric:
        raise ValueError("no numeric columns available to build a formula")
    g = goal.lower()
    scored = sorted(
        numeric,
        key=lambda c: sum(t in c["key"] for t in g.replace("/", " ").split()),
        reverse=True,
    )
    if len(scored) >= 2:
        a, b = scored[0]["key"], scored[1]["key"]
        return {
            "expression": f"sum({a}) / sum({b})",
            "variables": [a, b],
            "rationale": f"Ratio of total {a} to total {b} (heuristic).",
        }
    a = scored[0]["key"]
    return {
        "expression": f"avg({a})",
        "variables": [a],
        "rationale": f"Average of {a} (heuristic).",
    }


def propose_formula(goal: str, columns: list[dict]) -> dict:
    """columns: [{"key","header","type","numeric"}]. Returns proposal dict."""
    if not settings.anthropic_api_key:
        return _heuristic(goal, columns)

    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    catalog = [
        {"key": c["key"], "type": c["type"], "numeric": c["numeric"]} for c in columns
    ]
    msg = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=400,
        system=_SYSTEM,
        messages=[
            {"role": "user", "content": f"Goal: {goal}\nColumns: {json.dumps(catalog)}"}
        ],
    )
    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    try:
        proposal = json.loads(text)
        assert "expression" in proposal and "variables" in proposal
        return proposal
    except Exception:
        # Model misbehaved; fall back rather than fail the request.
        return _heuristic(goal, columns)
