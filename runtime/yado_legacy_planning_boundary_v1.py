"""Maintain the inherited precedence contract without editing the frozen G0 source.

The legacy sorter appends cyclic roles to an otherwise valid order. Current
callers must reject that impossible plan before delegating deterministic ordering.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
import sys

_LEGACY = Path(__file__).resolve().parent / "yado_rc8_v36"
if str(_LEGACY) not in sys.path:
    sys.path.insert(0, str(_LEGACY))

from yado_organ_runtime_native_v1 import plan_with_edges as _inherited_plan


def plan_with_edges(actions, edges):
    actions = list(actions)
    roles = {str(action.get("role")) for action in actions}
    if isinstance(edges, Mapping) and edges.get("kind") == "CONTEXTUAL_PRECEDENCE":
        branch = "present_edges" if edges.get("marker") in roles else "absent_edges"
        edges = edges.get(branch, [])
    edges = list(edges or [])
    outgoing = {role: set() for role in roles}
    indegree = {role: 0 for role in roles}
    for edge in edges:
        before, after = str(edge.get("before")), str(edge.get("after"))
        if before in roles and after in roles and after not in outgoing[before]:
            outgoing[before].add(after)
            indegree[after] += 1
    ready = [role for role, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        before = ready.pop()
        visited += 1
        for after in outgoing[before]:
            indegree[after] -= 1
            if indegree[after] == 0:
                ready.append(after)
    if visited != len(roles):
        raise ValueError("LEGACY_PRECEDENCE_CYCLE")
    return _inherited_plan(actions, edges)


def plan_multicontext(model, context, actions):
    if not isinstance(model, Mapping) or model.get("kind") != "MULTICONTEXT_PRECEDENCE":
        return plan_with_edges(actions, model)
    if isinstance(context, Mapping):
        context = {str(key): bool(value) for key, value in context.items()}
    else:
        context = {str(key): True for key in context}
    signature = "".join("1" if context.get(key, False) else "0"
                        for key in (model.get("context_keys") or []))
    edges = (model.get("graphs") or {}).get(signature, model.get("fallback_edges") or [])
    return plan_with_edges(actions, edges)


__all__ = ["plan_with_edges", "plan_multicontext"]
