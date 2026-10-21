from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

import main


def test_ensure_prerequisites_requires_deepseek_key(monkeypatch, tmp_path):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    knowledge = tmp_path / "knowledge.md"
    knowledge.write_text("x", encoding="utf-8")
    monkeypatch.setattr(main, "KNOWLEDGE_PATH", knowledge)
    with pytest.raises(SystemExit) as exc:
        main.ensure_prerequisites()
    assert "DEEPSEEK_API_KEY" in str(exc.value)


def test_ensure_prerequisites_requires_knowledge_file(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(main, "KNOWLEDGE_PATH", tmp_path / "missing.md")
    with pytest.raises(SystemExit) as exc:
        main.ensure_prerequisites()
    assert "知识库" in str(exc.value)


def test_build_retriever_or_exit_reports_ollama_failure(monkeypatch):
    def broken(_path):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(main, "build_retriever", broken)
    with pytest.raises(SystemExit) as exc:
        main.build_retriever_or_exit()
    assert "Ollama" in str(exc.value)
    assert "connection refused" in str(exc.value)


class FakeGraph:
    def __init__(self, chunk):
        self.chunk = chunk

    def stream(self, payload, config, stream_mode):
        yield ("messages", (self.chunk, {}))

    def get_state(self, config):
        return SimpleNamespace(interrupts=())


def test_run_turn_prints_full_ai_message(capsys):
    main.run_turn(FakeGraph(AIMessage(content="答案是 14")), {}, "算一下")
    assert "答案是 14" in capsys.readouterr().out


def test_run_turn_prints_ai_chunk(capsys):
    main.run_turn(FakeGraph(AIMessageChunk(content="答案是 14")), {}, "算一下")
    assert "答案是 14" in capsys.readouterr().out


class FakeToolGraph:
    def stream(self, payload, config, stream_mode):
        yield (
            "updates",
            {
                "tools": {
                    "messages": [
                        ToolMessage(
                            content="长" * 300,
                            name="search_docs",
                            tool_call_id="c1",
                        )
                    ]
                }
            },
        )

    def get_state(self, config):
        return SimpleNamespace(interrupts=())


def test_run_turn_truncates_long_tool_result(capsys):
    main.run_turn(FakeToolGraph(), {}, "查一下")
    out = capsys.readouterr().out
    assert "已截断" in out
    assert out.count("长") < 300
