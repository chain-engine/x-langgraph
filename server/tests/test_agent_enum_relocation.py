# -*- coding: utf-8 -*-
"""Verify AgentType/AgentStatus live in constants."""
from agent.base import AgentConfig, AgentResult
from constants import AgentType, AgentStatus


def test_agents_exposed_in_constants():
    assert AgentType.REACT.value == "react"
    assert AgentType.PLAN_EXECUTE.value == "plan_execute"
    assert AgentType.REFLEXION.value == "reflexion"
    assert AgentStatus.IDLE.value == "idle"
    assert AgentStatus.MAX_ITERATIONS.value == "max_iterations"


def test_agent_base_uses_constants_enums():
    cfg = AgentConfig(name="demo")
    assert cfg.agent_type is AgentType.REACT
    assert AgentResult(success=True).status is AgentStatus.IDLE


def test_no_redefinition_in_agent_base():
    import agent.base as agent_base
    assert not hasattr(agent_base, "AgentType") or agent_base.AgentType is AgentType
    assert not hasattr(agent_base, "AgentStatus") or agent_base.AgentStatus is AgentStatus
