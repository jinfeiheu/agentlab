from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, AIMessageChunk, ToolMessage

import main


def test_ensure_prerequisites_requires_deepseek_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(SystemExit) as exc:
        main.ensure_prerequisites()
    assert "DEEPSEEK_API_KEY" in str(exc.value)


def test_ensure_prerequisites_requires_docs_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test")
    monkeypatch.setattr(main, "DOCS_DIR", tmp_path / "missing")
    with pytest.raises(SystemExit) as exc:
        main.ensure_prerequisites()
    assert "语料" in str(exc.value)


def test_build_retriever_or_exit_reports_ollama_failure(monkeypatch):
    def broken(_docs_dir):
        raise RuntimeError("connection refused")

    monkeypatch.setattr(main, "build_inmemory_retriever", broken)
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


def test_main_sets_up_and_shuts_down_tracing(monkeypatch):
    calls = []

    class FakeCliGraph:
        def get_graph(self):
            return SimpleNamespace(draw_mermaid=lambda: "")

    def raise_eof(_prompt):
        raise EOFError

    monkeypatch.setattr(main, "ensure_prerequisites", lambda: None)
    monkeypatch.setattr(
        main, "setup_tracing", lambda: calls.append("setup"), raising=False
    )
    monkeypatch.setattr(
        main, "shutdown_tracing", lambda: calls.append("shutdown"), raising=False
    )
    monkeypatch.setattr(main, "build_retriever_or_exit", lambda: object())
    monkeypatch.setattr(main, "build_chat_model", lambda **_: object())
    monkeypatch.setattr(main, "build_graph", lambda *args, **kwargs: FakeCliGraph())
    monkeypatch.setattr("builtins.input", raise_eof)

    main.main()

    assert calls == ["setup", "shutdown"]
