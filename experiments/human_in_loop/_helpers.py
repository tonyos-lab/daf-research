"""Shared helpers for HIL experiments."""
from __future__ import annotations
import sys
from pathlib import Path

_r = Path(__file__).resolve().parents[2]
if str(_r) not in sys.path:
    sys.path.insert(0, str(_r))

from daf.testing import FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.agents import StubAgent
from daf.tools import StubTool

# Use HIL-specific policy matrix with a require_human_gate compliance rule
POLICY_MATRIX = str(Path(__file__).parent / "hil_policy.yaml")

# data_required value that triggers the GATE-HIL-001 compliance rule
GATED_DATA   = "requires_review"   # triggers gate
SAFE_DATA    = "internal"          # no gate


def make_registries():
    tool_registry = ToolRegistry()
    tool_registry.register(StubTool(name="read_db", idempotent=True))
    agent_registry = AgentRegistry()
    agent_registry.register(
        type("DocAgent", (StubAgent,), {"role": "document_reader"})
    )
    return agent_registry, tool_registry


def gated_plan():
    """A plan with one task that triggers HITL gate via compliance rule."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   data_sources=[GATED_DATA])
        .build()
    )


def safe_plan():
    """A plan with no gated tasks."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   data_sources=[SAFE_DATA])
        .build()
    )


def mixed_plan():
    """Plan: ST-01 safe, ST-02 gated."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   data_sources=[SAFE_DATA])
        .with_task("ST-02", agent="document_reader", tools=["read_db"],
                   data_sources=[GATED_DATA], depends_on=["ST-01"])
        .build()
    )
