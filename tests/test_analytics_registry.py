"""Skill 注册与动态子集测试。"""

from types import SimpleNamespace

import pytest

from agentlab.analytics.registry import (
    SkillNotAllowed,
    SkillRegistry,
    SkillSpec,
    skills_for,
)


def _spec(
    name: str,
    roles: set[str] | None = None,
    tenants: set[str] | None = None,
) -> SkillSpec:
    return SkillSpec(
        name=name,
        description=f"{name} skill",
        roles=roles or set(),
        tenant_ids=tenants or set(),
    )


def test_skills_for_filters_by_role_and_tenant():
    registry = SkillRegistry(
        [
            _spec("query", roles={"analyst"}, tenants={"tenant_a"}),
            _spec("verify", roles={"analyst"}),
            _spec("admin", roles={"admin"}),
            _spec("chart", tenants={"tenant_b"}),
        ]
    )
    user = SimpleNamespace(roles={"analyst"}, tenant_id="tenant_a")

    names = [
        skill.name for skill in registry.skills_for(user, "收入")
    ]

    assert names == ["query", "verify"]


def test_skills_for_excludes_other_tenant():
    registry = SkillRegistry(
        [
            _spec("query", tenants={"tenant_a"}),
            _spec("chart", tenants={"tenant_b"}),
        ]
    )
    user = SimpleNamespace(roles={"analyst"}, tenant_id="tenant_b")

    names = [
        skill.name for skill in registry.skills_for(user, "收入")
    ]

    assert names == ["chart"]


def test_unknown_skill_rejected():
    registry = SkillRegistry([_spec("query")])
    user = SimpleNamespace(roles={"analyst"}, tenant_id="tenant_a")

    with pytest.raises(SkillNotAllowed, match="未知"):
        registry.require("delete_orders", user)


def test_default_skills_for_returns_core_skills():
    user = SimpleNamespace(roles={"analyst"}, tenant_id="tenant_a")

    names = {skill.name for skill in skills_for(user, "收入")}

    assert {"query", "verify", "clarify", "chart"} <= names
