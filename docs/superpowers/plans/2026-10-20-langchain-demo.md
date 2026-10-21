# LangChain × LangGraph 学习示例 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个约 200 行的终端中文问答机器人,用一条主链路演示 LangChain / LangGraph 的核心技术栈。

**Architecture:** `main.py` 用 LangGraph `StateGraph` 组织 agent ↔ tools 循环,流式渲染并处理 `interrupt()` 恢复;`rag.py` 用 Ollama `bge-m3` + `InMemoryVectorStore` 提供检索;`tools.py` 提供计算器、检索、发送报告三个工具;`--simple` 模式用 `create_agent` 构建同一机器人用于对比。

**Tech Stack:** Python 3.12、uv、LangChain 1.4、LangGraph 1.2、langchain-deepseek、langchain-ollama、bge-m3、InMemoryVectorStore、pytest。

**Spec:** `docs/superpowers/specs/2026-10-20-langchain-demo-design.md`

## Global Constraints

- Python `>=3.10`,实际使用 3.12.3;依赖用 `uv` 管理。
- 终端交互,所有用户可见文字和代码注释使用中文。
- 核心代码仅 `main.py`、`rag.py`、`tools.py`,合计约 200 行(不含测试与 README)。
- 依赖仅:`langchain>=1.4,<2`、`langchain-core>=1.6,<2`、`langchain-deepseek>=1.1,<2`、`langchain-ollama>=1.1,<2`、`langgraph>=1.2,<2`、`langchain-text-splitters>=1.1,<2`、`numpy>=1.26`、`python-dotenv>=1.2`;开发依赖 `pytest>=8`。
- 模型默认 `deepseek-chat`,通过 `DEEPSEEK_MODEL` 覆盖;Key 只从 `.env` / 环境变量读取,绝不写死。
- 嵌入固定为 Ollama `bge-m3`(`http://localhost:11434`),DeepSeek 不提供 embedding。
- 不做 Web、多 Agent、MCP、长期记忆 Store、向量库持久化。
- 不做 git 提交(用户未要求);如需版本管理,由用户另行初始化。

## Review Focus

1. **缺少 `DEEPSEEK_API_KEY`**:用户还没配 `.env` 就运行。期望:启动时给出中文提示并退出,而不是在第一次对话时抛裸异常。
2. **Ollama 未启动或没拉 `bge-m3`**:期望:启动阶段提示“请确认 Ollama 已启动且已拉取 bge-m3”,并带上原始错误。
3. **计算器的恶意/超长/巨大指数输入**:期望:安全拒绝,绝不执行任意代码或长时间卡死。
4. **知识库检索无结果**:期望:工具返回“没有找到相关内容”,Agent 仍能正常回答,不崩溃。
5. **HITL 取消**:用户在确认时输入 `n`。期望:工具返回“已取消发送”,图继续运行到正常结束,不挂起。

---

### Task 1: 项目骨架、依赖与知识库

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `data/knowledge.md`

**Interfaces:**
- Consumes: 无
- Produces: 可用的 `uv` 环境;`data/knowledge.md` 供 Task 2 的 `build_retriever()` 读取。

- [ ] **Step 1: 写 `pyproject.toml`**

```toml
[project]
name = "langchain-graph-demo"
version = "0.1.0"
description = "LangChain / LangGraph 终端学习示例"
requires-python = ">=3.10"
dependencies = [
  "langchain>=1.4,<2",
  "langchain-core>=1.6,<2",
  "langchain-deepseek>=1.1,<2",
  "langchain-ollama>=1.1,<2",
  "langgraph>=1.2,<2",
  "langchain-text-splitters>=1.1,<2",
  "numpy>=1.26",
  "python-dotenv>=1.2",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

- [ ] **Step 2: 写 `.env.example`**

```dotenv
# 必填:DeepSeek API Key(复制本文件为 .env 后填写)
DEEPSEEK_API_KEY=sk-your-key-here
# 可选:默认 deepseek-chat
DEEPSEEK_MODEL=deepseek-chat
# 本地 Ollama 嵌入
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBED_MODEL=bge-m3
RAG_TOP_K=3
# 可选:LangSmith 追踪(没有 key 就保持注释)
# LANGSMITH_TRACING=true
# LANGSMITH_API_KEY=lsv2_...
# LANGSMITH_PROJECT=langchain-demo
```

- [ ] **Step 3: 写 `.gitignore`**

```gitignore
.venv/
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 4: 写 `data/knowledge.md`**

至少包含以下 8 个小节,每节 2–4 句中文,内容与真实技术栈一致:

1. LangChain 是什么:框架分层(`langchain-core`、`langchain`、模型适配包)。
2. LangGraph 是什么:`StateGraph`、节点、条件边、循环。
3. Checkpointer 与 `thread_id`:短期记忆、断点续跑、time travel。
4. 工具调用与 ReAct 循环:模型返回 `tool_calls`,工具节点执行后回到模型。
5. RAG 流程:加载 → 切分 → 嵌入 → 向量库 → 检索 → 拼上下文。
6. 流式输出:`stream_mode="messages"` 与 `"updates"` 的区别。
7. LangSmith:追踪、评估、Prompt 管理,通过环境变量开启。
8. 本项目的模型与嵌入:DeepSeek `deepseek-chat` 负责生成,Ollama `bge-m3`(1024 维)负责嵌入。

- [ ] **Step 5: 安装依赖**

Run: `uv sync --all-groups`
Expected: 创建 `.venv` 并成功安装,末尾显示 `Installed ... packages` 或 `Audited ... packages`。

- [ ] **Step 6: 验证依赖可导入**

Run: `uv run python -c "import langchain, langgraph, langchain_deepseek, langchain_ollama, numpy; print('ok')"`
Expected: 输出 `ok`。

---

### Task 2: RAG 模块

**Files:**
- Create: `rag.py`
- Test: `tests/test_rag.py`

**Interfaces:**
- Consumes: `data/knowledge.md`
- Produces:
  - `load_document(path: Path) -> Document`
  - `split_documents(docs: list[Document], chunk_size: int = 500, chunk_overlap: int = 80) -> list[Document]`
  - `format_docs(docs: list[Document]) -> str`
  - `build_retriever(knowledge_path: Path) -> BaseRetriever`

- [ ] **Step 1: 写失败的测试 `tests/test_rag.py`**

```python
from langchain_core.documents import Document

from rag import format_docs, split_documents


def test_split_documents_produces_multiple_chunks():
    docs = [Document(page_content="第一段。" * 200, metadata={"source": "k.md"})]
    chunks = split_documents(docs, chunk_size=100, chunk_overlap=20)
    assert len(chunks) > 1
    assert all(chunk.page_content for chunk in chunks)
    assert all(chunk.metadata["source"] == "k.md" for chunk in chunks)


def test_format_docs_includes_source_and_content():
    out = format_docs(
        [Document(page_content="checkpointer 保存状态", metadata={"source": "k.md"})]
    )
    assert "k.md" in out
    assert "checkpointer 保存状态" in out
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_rag.py -v`
Expected: FAIL,`ModuleNotFoundError: No module named 'rag'`。

- [ ] **Step 3: 实现 `rag.py`**

- `load_document` 用 `Path.read_text(encoding="utf-8")` 读取,返回带 `metadata={"source": path.name}` 的 `Document`。
- `split_documents` 用 `RecursiveCharacterTextSplitter`,分隔符含中文句号:`["\n\n", "\n", "。", "！", "？", " ", ""]`。
- `format_docs` 每段输出 `[来源:{source}]\n{page_content}`,段间用 `\n\n---\n\n`。
- `build_retriever` 用 `OllamaEmbeddings(model=os.getenv("OLLAMA_EMBED_MODEL", "bge-m3"), base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))`,`InMemoryVectorStore.from_documents(chunks, embeddings)`,返回 `store.as_retriever(search_kwargs={"k": int(os.getenv("RAG_TOP_K", "3"))})`。

- [ ] **Step 4: 运行单元测试确认通过**

Run: `uv run pytest tests/test_rag.py -v`
Expected: 2 passed。

- [ ] **Step 5: 集成验证检索(需要 Ollama)**

Run:
```bash
uv run python -c "from pathlib import Path; from rag import build_retriever; r = build_retriever(Path('data/knowledge.md')); print(r.invoke('checkpointer 是做什么的')[0].page_content[:120])"
```
Expected: 打印一段包含 `checkpointer` 的中文内容。若报连接错误,先执行 `ollama serve`,并确认 `ollama list` 有 `bge-m3`。

---

### Task 3: 工具模块

**Files:**
- Create: `tools.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: `rag.format_docs(docs) -> str`;`BaseRetriever`
- Produces:
  - `calculator(expression: str) -> str`(`@tool`)
  - `make_search_tool(retriever: BaseRetriever) -> BaseTool`
  - `send_report(content: str) -> str`(`@tool`,内部调用 `interrupt`)

- [ ] **Step 1: 写失败的测试 `tests/test_tools.py`**

```python
from langchain_core.documents import Document

from tools import calculator, make_search_tool


def test_calculator_evaluates_expression():
    assert calculator.invoke({"expression": "2+3*4"}) == "14"


def test_calculator_handles_division():
    assert calculator.invoke({"expression": "10/4"}) == "2.5"


def test_calculator_rejects_zero_division():
    assert "除数" in calculator.invoke({"expression": "1/0"})


def test_calculator_rejects_code_execution():
    result = calculator.invoke({"expression": "__import__('os').system('echo hi')"})
    assert result.startswith("错误")


def test_calculator_rejects_huge_exponent():
    assert "指数" in calculator.invoke({"expression": "2**1000000"})


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs

    def invoke(self, query):
        return self.docs


def test_search_tool_formats_results():
    tool = make_search_tool(
        FakeRetriever(
            [Document(page_content="checkpointer 保存状态", metadata={"source": "k.md"})]
        )
    )
    out = tool.invoke({"query": "checkpointer"})
    assert "checkpointer 保存状态" in out
    assert "k.md" in out


def test_search_tool_handles_no_results():
    tool = make_search_tool(FakeRetriever([]))
    assert "没有找到" in tool.invoke({"query": "不存在的内容"})
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_tools.py -v`
Expected: FAIL,`ModuleNotFoundError: No module named 'tools'`。

- [ ] **Step 3: 实现 `tools.py`**

- `calculator`:用 `ast.parse(expression, mode="eval")` + 手写 AST 求值,**禁止 `eval`/`exec`**。支持 `+ - * / // % **`、一元正负号、括号;表达式长度上限 100;`Pow` 指数绝对值超过 1000 时返回“错误:指数过大”;除零返回“错误:除数不能为 0”;其他异常返回 `错误:...`。
- `make_search_tool`:在工厂内用 `@tool` 定义 `search_knowledge(query: str)`,调用 `retriever.invoke(query)`,有结果用 `format_docs`,无结果返回“知识库中没有找到相关内容。”。
- `send_report`:`@tool`,先 `answer = interrupt({"question": "确认发送这份报告吗?", "content": content})`;`answer` 归一化后属于 `{"y", "yes", "是", "确认", "ok"}` 时返回 `已发送(模拟):{content}`,否则返回 `已取消发送。`。
- 三个工具的 docstring 用中文,它们会作为工具描述发给模型。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_tools.py -v`
Expected: 7 passed。

---

### Task 4: LangGraph 图与 HITL

**Files:**
- Create: `main.py`(本任务先实现图相关部分)
- Test: `tests/test_graph.py`

**Interfaces:**
- Consumes: `tools.calculator`、`tools.send_report`、任意 `BaseChatModel`
- Produces:
  - `SYSTEM_PROMPT: str`
  - `build_graph(model, tools, checkpointer=None) -> CompiledStateGraph`
  - `build_simple_graph(model, tools, checkpointer=None) -> CompiledStateGraph`

- [ ] **Step 1: 写失败的测试 `tests/test_graph.py`**

```python
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from main import build_graph
from tools import calculator, send_report


class ScriptedModel(BaseChatModel):
    responses: list[AIMessage]
    calls: int = 0

    @property
    def _llm_type(self):
        return "scripted"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        message = self.responses[self.calls % len(self.responses)]
        self.calls += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def test_graph_runs_tool_loop():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "calculator", "args": {"expression": "2+3*4"}, "id": "c1"}
                ],
            ),
            AIMessage(content="答案是 14"),
        ]
    )
    graph = build_graph(model, [calculator])
    result = graph.invoke(
        {"messages": [("user", "算一下")]}, {"configurable": {"thread_id": "t1"}}
    )
    assert result["messages"][-1].content == "答案是 14"
    assert any(m.type == "tool" and m.content == "14" for m in result["messages"])


def test_send_report_interrupt_and_resume():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "send_report", "args": {"content": "周报"}, "id": "c2"}
                ],
            ),
            AIMessage(content="处理完成"),
        ]
    )
    graph = build_graph(model, [send_report], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t2"}}
    graph.invoke({"messages": [("user", "发送周报")]}, config)
    assert graph.get_state(config).interrupts
    result = graph.invoke(Command(resume="y"), config)
    assert result["messages"][-1].content == "处理完成"
    assert any(m.type == "tool" and "已发送" in m.content for m in result["messages"])


def test_send_report_cancel():
    model = ScriptedModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {"name": "send_report", "args": {"content": "周报"}, "id": "c3"}
                ],
            ),
            AIMessage(content="已取消"),
        ]
    )
    graph = build_graph(model, [send_report], checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t3"}}
    graph.invoke({"messages": [("user", "发送周报")]}, config)
    result = graph.invoke(Command(resume="n"), config)
    assert any(m.type == "tool" and "已取消" in m.content for m in result["messages"])
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_graph.py -v`
Expected: FAIL,`ModuleNotFoundError: No module named 'main'`。

- [ ] **Step 3: 实现 `main.py` 的图部分**

- 顶部 `load_dotenv()`;导入 `ChatDeepSeek`、`ChatPromptTemplate`、`MessagesPlaceholder`、`StateGraph`、`START`、`MessagesState`、`ToolNode`、`tools_condition`、`create_agent`。
- `SYSTEM_PROMPT`:中文,说明“技术栈问题先用 search_knowledge 检索;算术用 calculator;发送报告用 send_report;引用知识库时注明来源”。
- `build_graph(model, tools, checkpointer=None)`:
  - `llm = model.bind_tools(tools)`
  - prompt = `[("system", SYSTEM_PROMPT), MessagesPlaceholder("messages")]`
  - `agent` 节点返回 `{"messages": [(prompt | llm).invoke({"messages": state["messages"]})]}`
  - 图:`START → agent`;`agent` 用 `tools_condition` 条件边;`tools` 用 `ToolNode(tools)`;`tools → agent`
  - `builder.compile(checkpointer=checkpointer)`
- `build_simple_graph(model, tools, checkpointer=None)`:`create_agent(model, tools, system_prompt=SYSTEM_PROMPT, checkpointer=checkpointer)`。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_graph.py -v`
Expected: 3 passed。

---

### Task 5: CLI、`--simple` 模式、README 与端到端验证

**Files:**
- Modify: `main.py`(追加 CLI 部分)
- Create: `tests/test_main.py`
- Create: `README.md`

**Interfaces:**
- Consumes: Task 2–4 的全部接口
- Produces:
  - `ensure_prerequisites() -> None`
  - `build_retriever_or_exit() -> BaseRetriever`
  - `run_turn(graph, config, user_input: str) -> None`
  - `main() -> None`

- [ ] **Step 1: 写失败的测试 `tests/test_main.py`**

```python
import pytest

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
```

- [ ] **Step 2: 运行测试确认失败**

Run: `uv run pytest tests/test_main.py -v`
Expected: FAIL,`AttributeError: module 'main' has no attribute 'ensure_prerequisites'`。

- [ ] **Step 3: 在 `main.py` 中实现 CLI**

- `KNOWLEDGE_PATH = Path(__file__).resolve().parent / "data" / "knowledge.md"`。
- `ensure_prerequisites()`:缺少 `DEEPSEEK_API_KEY` → `SystemExit("缺少 DEEPSEEK_API_KEY:请复制 .env.example 为 .env 并填入你的 DeepSeek Key。")`;知识库文件不存在 → 中文 `SystemExit`。
- `build_retriever_or_exit()`:调用 `build_retriever(KNOWLEDGE_PATH)`,捕获异常后 `SystemExit` 提示“知识库构建失败,请确认 Ollama 已启动且已拉取 bge-m3”,并附原始错误。
- `run_turn(graph, config, user_input)`:
  - `payload = {"messages": [("user", user_input)]}`
  - 循环 `graph.stream(payload, config=config, stream_mode=["messages", "updates"])`:
    - `messages` 模式:只打印 `isinstance(chunk, AIMessageChunk)` 且 `content` 为非空字符串的 token。
    - `updates` 模式:对 `update["messages"]` 中的 `AIMessage` 打印 `🔧 调用工具 {name}({args})`;对 `ToolMessage` 打印 `📄 工具结果 [{name}]: {content}`。
  - 流结束后 `state = graph.get_state(config)`;没有 `interrupts` 就返回。
  - 有中断:打印 `⚠️ {question}` 和 `content`(若有),`input("确认? (y/n) > ")`,`payload = Command(resume=answer)`,继续循环。
- `main()`:
  - `ensure_prerequisites()` → 提示“正在构建知识库索引...” → `build_retriever_or_exit()`。
  - `model = ChatDeepSeek(model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"), temperature=0)`;tools = `[calculator, make_search_tool(retriever), send_report]`;checkpointer = `InMemorySaver()`。
  - `--simple` 在 `sys.argv` 中时用 `build_simple_graph`,否则 `build_graph`;启动横幅注明当前模式。
  - 命令:`/new` 换 `uuid4` 的 `thread_id`;`/help` 打印命令;`/quit`、`/exit`、`quit`、`exit` 退出;空行忽略。
  - `run_turn` 外包 `try/except`,异常时打印中文“调用失败:...”,不退出程序。
- 流式输出结束换行,保证提示符在下一行。

- [ ] **Step 4: 运行测试确认通过**

Run: `uv run pytest tests/test_main.py -v`
Expected: 3 passed。

- [ ] **Step 5: 写 `README.md`**

包含:
1. 一句话定位与目录结构。
2. ASCII 架构图(CLI → StateGraph → agent/tools → DeepSeek / bge-m3 / checkpointer)。
3. 快速开始:复制 `.env.example` 为 `.env` 填 Key;`ollama serve`;`ollama pull bge-m3`;`uv sync`;`uv run python main.py`。
4. 技术栈对照表:每个概念 → 对应文件/函数。
5. 试这几句话:RAG 问题、多轮记忆、算术、发送报告(确认/取消)、`/new`。
6. “改一行看效果”练习:改 system prompt、chunk size、top-k、加工具、换 SqliteSaver、换 Chroma、打开 LangSmith。
7. `--simple` 对比说明:`create_agent` 是 LangChain 1.x 高层 API,内部仍是 LangGraph。
8. 进阶方向(README 提及即可):多 Agent、MCP、Store、Web 部署。

- [ ] **Step 6: 运行全部测试**

Run: `uv run pytest -v`
Expected: 15 passed(2 + 7 + 3 + 3)。

- [ ] **Step 7: 端到端验证**

先确认 `.env` 已填真实 Key,然后 Run: `uv run python main.py`,依次输入:

1. `LangGraph 的 checkpointer 有什么用?` → 应看到 `🔧 调用工具 search_knowledge`,回答包含来源。
2. `我叫小明` → 正常回答。
3. `我叫什么?` → 回答能说出“小明”。
4. `帮我算 (12+8)*3` → 应看到 `🔧 调用工具 calculator`,结果为 60。
5. `把今天的结论发送报告` → 出现 `⚠️ 确认发送...`;输入 `y` → 看到“已发送(模拟)”;再试一次输入 `n` → 看到“已取消发送”。
6. `/new` 后输入 `我叫什么?` → 不应记得“小明”。
7. `/quit` 退出。
8. `uv run python main.py --simple`,重复第 1 条 → 应能正常检索并回答。

Expected: 以上全部符合;无裸 traceback。
