"""Prompt/模型版本 registry 与请求级成本预算。

YAML 是 prompt 版本的单一来源；active 可被环境变量覆盖用于回滚：
`ANALYTICS_PROMPT_UNDERSTAND_VERSION=v2`。
"""

import os
from dataclasses import dataclass
from pathlib import Path
from string import Template

import yaml

from agentlab.config import (
    ANALYTICS_MODEL_CALL_COST,
    ANALYTICS_PROMPT_DIR,
    ANALYTICS_REQUEST_BUDGET,
)


class PromptNotFound(KeyError):
    """prompt id 或版本不存在。"""


class BudgetExceeded(RuntimeError):
    """请求级模型调用预算超限。"""


@dataclass(frozen=True)
class PromptSpec:
    """一个可执行 prompt：版本、模型 id 与模板。"""

    prompt_id: str
    version: str
    model: str
    template: str


class PromptRegistry:
    """读取 `configs/analytics/prompts/*.yaml`，按 active/override 选版本。"""

    def __init__(
        self,
        config_dir: Path | str | None = None,
        overrides: dict[str, str] | None = None,
    ) -> None:
        self.config_dir = Path(config_dir or ANALYTICS_PROMPT_DIR)
        self.overrides = dict(overrides or {})
        self._prompts = self._load()

    def _load(self) -> dict[str, dict]:
        prompts: dict[str, dict] = {}
        for path in sorted(self.config_dir.glob("*.yaml")):
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            prompt_id = str(data.get("id") or path.stem)
            versions = data.get("versions") or {}
            if not versions:
                raise PromptNotFound(f"{path} 没有 versions")
            active = data.get("active")
            if active not in versions:
                raise PromptNotFound(
                    f"{prompt_id} 的 active 版本不存在：{active}"
                )
            data["id"] = prompt_id
            prompts[prompt_id] = data
        if not prompts:
            raise PromptNotFound(f"目录中没有 prompt YAML：{self.config_dir}")
        return prompts

    def versions(self, prompt_id: str) -> list[str]:
        data = self._data(prompt_id)
        return sorted(data["versions"])

    def active_version(self, prompt_id: str) -> str:
        data = self._data(prompt_id)
        override = self.overrides.get(prompt_id) or os.getenv(
            f"ANALYTICS_PROMPT_{prompt_id.upper()}_VERSION"
        )
        version = override or data["active"]
        if version not in data["versions"]:
            raise PromptNotFound(
                f"{prompt_id} 版本不存在：{version}"
            )
        return str(version)

    def get(
        self, prompt_id: str, version: str | None = None
    ) -> PromptSpec:
        data = self._data(prompt_id)
        selected = version or self.active_version(prompt_id)
        spec = data["versions"].get(selected)
        if spec is None:
            raise PromptNotFound(
                f"{prompt_id} 版本不存在：{selected}"
            )
        return PromptSpec(
            prompt_id=prompt_id,
            version=str(selected),
            model=str(spec.get("model") or "default"),
            template=str(spec.get("template") or ""),
        )

    def render(self, prompt_id: str, version: str | None = None, **variables) -> str:
        spec = self.get(prompt_id, version)
        return Template(spec.template).safe_substitute(**variables)

    def snapshot(self) -> dict[str, str]:
        return {
            prompt_id: self.active_version(prompt_id)
            for prompt_id in sorted(self._prompts)
        }

    def _data(self, prompt_id: str) -> dict:
        data = self._prompts.get(prompt_id)
        if data is None:
            raise PromptNotFound(f"未知 prompt：{prompt_id}")
        return data


class ModelRouter:
    """按 YAML 中的 model id 取模型；同一 id 复用实例。"""

    def __init__(self, factory):
        self.factory = factory
        self._cache = {}

    def __call__(self, model_id: str):
        key = model_id or "default"
        if key not in self._cache:
            self._cache[key] = self.factory(key)
        return self._cache[key]


def build_model_router(temperature: float = 0):
    """生产用 router：default 使用 DEEPSEEK_MODEL，其他 id 直接传给模型工厂。"""
    from agentlab.models import build_chat_model

    def factory(model_id: str):
        selected = None if model_id in {None, "", "default"} else model_id
        return build_chat_model(temperature=temperature, model=selected)

    return ModelRouter(factory)


@dataclass(frozen=True)
class CostBudget:
    """请求级模型调用预算；spent 存在图状态里，避免跨请求共享。"""

    max_cost: float = ANALYTICS_REQUEST_BUDGET
    cost_per_call: float = ANALYTICS_MODEL_CALL_COST

    def charge(self, spent: float) -> float:
        next_spent = float(spent) + self.cost_per_call
        if next_spent > self.max_cost + 1e-12:
            raise BudgetExceeded(
                "本次分析超出成本预算"
                f"（上限 ¥{self.max_cost:.4f}），请缩小范围后重试。"
            )
        return next_spent
