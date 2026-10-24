"""Golden set 的数据结构与加载函数。"""

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class GoldenItem(BaseModel):
    """一条评测样本;hard 集额外带难度、类别和参考答案。"""

    id: str
    question: str
    answerable: bool
    expected_sources: list[str] = Field(default_factory=list)
    relevant_chunk_ids: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    expected_tools: list[str] = Field(default_factory=list)
    difficulty: Literal["easy", "medium", "hard"] = "easy"
    category: str = "unspecified"
    reference_answer: str | None = None


def load_golden(path: Path) -> list[GoldenItem]:
    """逐行读取 JSONL,忽略空行。"""
    items: list[GoldenItem] = []
    with path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if line:
                items.append(GoldenItem.model_validate(json.loads(line)))
    return items
