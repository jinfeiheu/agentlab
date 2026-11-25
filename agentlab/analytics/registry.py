"""Skill 注册与按角色/租户的动态子集。"""

from dataclasses import dataclass, field


class SkillNotAllowed(PermissionError):
    """Skill 不存在，或当前用户/租户无权使用。"""


@dataclass
class SkillSpec:
    """一个可发现的 Skill；roles/tenant_ids 为空表示不限制。"""

    name: str
    description: str
    input_schema: dict = field(default_factory=dict)
    output_schema: dict = field(default_factory=dict)
    permissions: set[str] = field(default_factory=set)
    cost_hint: float = 0.0
    latency_hint: float = 0.0
    roles: set[str] = field(default_factory=set)
    tenant_ids: set[str] = field(default_factory=set)


class SkillRegistry:
    """维护 Skill 列表，并按用户角色/租户返回子集。"""

    def __init__(self, specs: list[SkillSpec] | None = None) -> None:
        self._specs = list(specs or [])

    def register(self, spec: SkillSpec) -> None:
        self._specs.append(spec)

    def get(self, name: str) -> SkillSpec | None:
        for spec in self._specs:
            if spec.name == name:
                return spec
        return None

    def _allowed(self, spec: SkillSpec, user) -> bool:
        roles = set(getattr(user, "roles", set()) or set())
        tenant_id = getattr(user, "tenant_id", None)
        if spec.roles and not (spec.roles & roles):
            return False
        if spec.tenant_ids and tenant_id not in spec.tenant_ids:
            return False
        return True

    def skills_for(self, user, question: str) -> list[SkillSpec]:
        """按角色/租户过滤；question 预留给后续动态选择。"""
        return [
            spec for spec in self._specs if self._allowed(spec, user)
        ]

    def require(self, name: str, user) -> SkillSpec:
        spec = self.get(name)
        if spec is None or not self._allowed(spec, user):
            raise SkillNotAllowed(f"未知或无权的技能：{name}")
        return spec


DEFAULT_SKILLS = [
    SkillSpec(name="query", description="执行只读 SQL 查询"),
    SkillSpec(name="verify", description="校验步骤结果"),
    SkillSpec(name="clarify", description="向用户澄清歧义"),
    SkillSpec(name="chart", description="生成 Vega-Lite 图表"),
]

_DEFAULT_REGISTRY = SkillRegistry(DEFAULT_SKILLS)


def skills_for(user, question: str) -> list[SkillSpec]:
    """默认注册表的动态子集。"""
    return _DEFAULT_REGISTRY.skills_for(user, question)
