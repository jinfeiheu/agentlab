# LangChain × LangGraph 学习示例:设计说明

- 日期:2026-10-20
- 状态:范围已与用户确认

## 意图与理由

用户想通过一个可运行的小项目学习 LangChain / LangGraph 的代码写法、组件用法和框架架构。项目不是生产系统,第一优先级是**可读、可改、能跑**;第二优先级才是功能完整。用户明确要求“代码少一点、技术栈全一点、终端里跑”。

## 目标

- 一个中文多轮问答机器人,终端交互,流式输出。
- 通过一条主链路覆盖下列技术栈:
  - 模型接入:`langchain-deepseek` 的 `ChatDeepSeek`
  - Prompt / LCEL:`ChatPromptTemplate` + `bind_tools`
  - RAG:Markdown 加载 → 切分 → Ollama `bge-m3` 嵌入 → `InMemoryVectorStore` → retriever
  - Agentic RAG:检索封装为工具,由模型决定何时调用
  - 工具调用:计算器、知识库检索、发送报告
  - 编排:LangGraph `StateGraph`,agent ↔ tools 条件边
  - 短期记忆:`InMemorySaver` + `thread_id`
  - Human-in-the-loop:`interrupt()` 确认后恢复执行
  - 流式:`stream_mode=["messages", "updates"]`
  - 观测:LangSmith 仅通过环境变量开启,没有 key 不影响运行
  - 高层 API 对比:`--simple` 模式用 `create_agent` 构建同一个机器人
- 中文注释,关键代码块标注对应技术栈层。
- 核心 Python 代码控制在 3 个文件、约 200 行(不含测试和 README)。

## 非目标

- 不做 Web / GUI,不做 FastAPI 部署。
- 不做多 Agent、MCP、长期记忆 `Store`、向量库持久化。
- 不做完整的生产级错误处理、鉴权、限流。
- 不引入 `langchain-community`、Chroma、sentence-transformers 等重依赖。
- 不做 git 提交(除非用户另行要求)。

## 约束

- 环境:WSL2,Python 3.12,`uv 0.12+`;Ollama 0.30+,已拉取 `bge-m3`(1024 维)。
- 模型:DeepSeek,API Key 由用户写入 `.env` 的 `DEEPSEEK_API_KEY`;默认模型 `deepseek-chat`,可用 `DEEPSEEK_MODEL` 覆盖。
- 终端 UI 与所有面向用户的文字使用中文。
- 依赖尽量少:`langchain`、`langchain-core`、`langchain-deepseek`、`langchain-ollama`、`langgraph`、`langchain-text-splitters`、`numpy`、`python-dotenv`;开发依赖 `pytest`。
- DeepSeek 不提供 embedding 接口,嵌入固定走本地 Ollama `bge-m3`。

## 架构

```
终端 CLI(main.py)
   │  用户输入 / /new / /quit
   ▼
LangGraph StateGraph(MessagesState)
   │
   ├─ agent 节点:ChatPromptTemplate | ChatDeepSeek.bind_tools(tools)
   │       │ 有 tool_calls
   │       ▼
   ├─ tools 节点:ToolNode
   │       ├─ calculator         纯本地计算
   │       ├─ search_knowledge   → rag.py → bge-m3(Ollama)→ InMemoryVectorStore
   │       └─ send_report        → interrupt() 等用户确认 → Command(resume=...)
   │       │
   │       └──► 回到 agent
   │
   └─ InMemorySaver:按 thread_id 保存多轮消息
```

- `main.py` 负责配置、图构建、流式渲染、CLI 循环、HITL 恢复。
- `rag.py` 只负责文档 → 切分 → 嵌入 → 向量库 → retriever,以及检索结果格式化。
- `tools.py` 只负责三个工具;`search_knowledge` 通过工厂函数注入 retriever,便于测试。
- `--simple` 模式用 `langchain.agents.create_agent(model, tools, system_prompt=..., checkpointer=...)` 构建同能力的图,复用同一个 CLI。
- 知识库 `data/knowledge.md` 的内容就是这套技术栈的中文说明,机器人可以“讲解自己”。

## 文件结构

```
langchain-demo/
├── main.py            # 配置 / 图 / 流式 / CLI
├── rag.py             # 加载→切分→嵌入→向量库→检索
├── tools.py           # 计算器 / 检索 / 发送报告(HITL)
├── data/knowledge.md  # 示例知识库
├── tests/
│   ├── test_rag.py
│   ├── test_tools.py
│   ├── test_graph.py
│   └── test_main.py
├── pyproject.toml
├── .env.example
├── .gitignore
├── README.md
└── docs/superpowers/...  # 本设计与实现计划
```

## 关键接口

- `rag.py`
  - `load_document(path: Path) -> Document`
  - `split_documents(docs: list[Document], chunk_size: int = 500, chunk_overlap: int = 80) -> list[Document]`
  - `format_docs(docs: list[Document]) -> str`
  - `build_retriever(knowledge_path: Path) -> BaseRetriever`
- `tools.py`
  - `calculator(expression: str) -> str`(LangChain `@tool`)
  - `make_search_tool(retriever: BaseRetriever) -> BaseTool`
  - `send_report(content: str) -> str`(`@tool`,内部 `interrupt`)
- `main.py`
  - `SYSTEM_PROMPT: str`
  - `ensure_prerequisites() -> None`
  - `build_retriever_or_exit() -> BaseRetriever`
  - `build_graph(model, tools, checkpointer=None) -> CompiledStateGraph`
  - `build_simple_graph(model, tools, checkpointer=None) -> CompiledStateGraph`
  - `run_turn(graph, config, user_input: str) -> None`
  - `main() -> None`

## 成功标准

1. `uv run pytest` 全部通过(不依赖网络/API)。
2. 配置 `.env` 后,`uv run python main.py` 能连续对话,并观察到:
   - 知识库问题触发 `search_knowledge`,回答带来源;
   - 第二轮能记住第一轮的名字;
   - 算术问题触发 `calculator`;
   - 发送报告触发确认,输入 `y` 后继续,输入 `n` 后取消;
   - `/new` 后不再记得之前的名字。
3. `uv run python main.py --simple` 同样能完成知识库问答。
4. 缺 Key、Ollama 未启动等常见错误给出中文提示,而不是裸 traceback。

## 待定

用户看完运行效果后再决定是否追加:多 Agent、MCP、`Store` 长期记忆、Web 部署、持久化向量库、SqliteSaver 等。
