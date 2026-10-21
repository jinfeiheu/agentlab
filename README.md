# LangChain × LangGraph 终端问答机器人

一个约 350 行的学习型示例：在终端里运行的中文问答机器人。它用一条主链路把 LangChain / LangGraph 的核心组件串起来：模型接入、Prompt/LCEL、RAG、工具调用、状态图、Checkpointer、流式输出、Human-in-the-loop，以及 LangSmith 的开关方式。

## 目录结构

```
langchain-demo/
├── main.py            # 配置 / LangGraph 图 / 流式渲染 / CLI
├── rag.py             # 加载 → 切分 → bge-m3 嵌入 → 向量库 → 检索
├── tools.py           # 计算器 / 知识库检索 / 发送报告(HITL)
├── data/knowledge.md  # 示例知识库(内容就是这套技术栈说明)
├── tests/             # 20 个离线测试
├── pyproject.toml
├── .env.example
└── README.md
```

## 架构

```
你(终端)
   │
   ▼
main.py CLI
   │  /new 换 thread_id    /quit 退出
   ▼
LangGraph StateGraph(MessagesState)
   │
   ├─ agent 节点:ChatPromptTemplate | ChatDeepSeek.bind_tools(tools)
   │        │ 有 tool_calls
   │        ▼
   ├─ tools 节点:ToolNode
   │        ├─ calculator          安全 AST 计算
   │        ├─ search_knowledge ──► rag.py
   │        │                        └─ bge-m3(Ollama) → InMemoryVectorStore → retriever
   │        └─ send_report ──► interrupt() ──► 你输入 y/n ──► Command(resume=...)
   │        │
   │        └──► 回到 agent
   │
   └─ InMemorySaver:按 thread_id 保存多轮消息
```

## 快速开始

```bash
cd langchain-demo

# 1. 配置 DeepSeek Key
cp .env.example .env
#    编辑 .env,把 DEEPSEEK_API_KEY 换成你的 Key

# 2. 启动 Ollama(若服务未运行;该命令会占用当前终端,建议另开终端)
ollama serve

# 3. 首次拉取 bge-m3,并确认存在
ollama pull bge-m3
ollama list | grep bge-m3

# 4. 安装依赖
uv sync --all-groups

# 5. 运行
uv run python main.py

# 6. 对比 LangChain 高层写法
uv run python main.py --simple
```

运行测试(不需要网络和 API Key):

```bash
uv run pytest -v
# 20 passed
```

## 技术栈对照表

| 技术栈 | 代码位置 | 说明 |
|---|---|---|
| 模型接入 | `main.py` 的 `main()` | `ChatDeepSeek(model=...)`,Key 从 `DEEPSEEK_API_KEY` 读取 |
| Prompt / LCEL | `main.py` 的 `build_graph()` | `ChatPromptTemplate.from_messages(...)`,agent 节点里 `prompt \| llm` |
| 工具定义 | `tools.py` | `@tool` 装饰器,docstring 会作为工具描述 |
| 工具绑定 | `main.py` 的 `build_graph()` | `model.bind_tools(tools)` |
| 工具执行 | `main.py` 的 `build_graph()` | `ToolNode(tools)` |
| 状态图 | `main.py` 的 `build_graph()` | `StateGraph(MessagesState)` + 节点 + 条件边 |
| 条件路由 | `main.py` 的 `build_graph()` | `tools_condition`:有 tool_calls 去 `tools`,否则结束 |
| 短期记忆 | `main.py` 的 `main()` | `InMemorySaver()` + `thread_id` |
| Human-in-the-loop | `tools.py` 的 `send_report()`;`main.py` 的 `run_turn()` | 工具内 `interrupt()`;CLI 用 `Command(resume=...)` 恢复 |
| 流式输出 | `main.py` 的 `run_turn()` | `stream_mode=["messages", "updates"]` |
| 文档加载与切分 | `rag.py` 的 `load_document()` / `split_documents()` | 读取 Markdown,按中文标点切块 |
| 嵌入 | `rag.py` 的 `build_retriever()` | `OllamaEmbeddings(model="bge-m3")`,1024 维 |
| 向量库 | `rag.py` 的 `build_retriever()` | `InMemoryVectorStore` |
| 检索 | `rag.py` 的 `build_retriever()` | `store.as_retriever(search_kwargs={"k": ...})` |
| Agentic RAG | `tools.py` 的 `make_search_tool()` | 检索封装成工具,由模型决定何时调用 |
| 高层 Agent API | `main.py` 的 `build_simple_graph()` | `create_agent(...)`,内部同样是 LangGraph |
| 观测 | `.env.example` 的 `LANGSMITH_*` | 有 Key 时设 `LANGSMITH_TRACING=true` 即可,无需改代码 |
| 启动错误处理 | `main.py` 的 `ensure_prerequisites()` / `build_retriever_or_exit()` | 缺 Key、Ollama 不可用时给出中文提示 |

## 试这几句话

1. `LangGraph 的 checkpointer 有什么用?` → 触发 `search_knowledge`,回答带来源。
2. `我叫小明` → 然后 `我叫什么?` → 验证多轮记忆。
3. `帮我算 (12+8)*3` → 触发 `calculator`,结果为 60。
4. `把今天的结论发送报告` → 触发 `send_report`,先出现确认提示:
   - 输入 `y` → 工具返回“已发送(模拟)”;
   - 再试一次输入 `n` → 返回“已取消发送”。
5. `/new` → 再问 `我叫什么?` → 验证新会话不记得旧名字。
6. `/quit` → 退出。

## 改一行看效果

| 想试什么 | 改哪里 |
|---|---|
| 改变回答风格 | `main.py` 的 `SYSTEM_PROMPT` |
| 改变切块大小 | `rag.py` 的 `split_documents()` 默认 `chunk_size` / `chunk_overlap` |
| 改变检索条数 | `.env` 的 `RAG_TOP_K` |
| 加一个工具 | 在 `tools.py` 写 `@tool`,再把它加进 `main.py` 的 `tools` 列表 |
| 换持久化记忆 | 把 `InMemorySaver()` 换成 `SqliteSaver.from_conn_string("checkpoints.db")`,并安装 `langgraph-checkpoint-sqlite` |
| 换持久化向量库 | 把 `InMemoryVectorStore` 换成 `Chroma` 或 `pgvector`,接口仍是 `as_retriever()` |
| 打开 LangSmith | `.env` 里取消注释 `LANGSMITH_TRACING=true` 并填 `LANGSMITH_API_KEY` |
| 换模型 | `.env` 的 `DEEPSEEK_MODEL`(例如换成账号可用的其他 DeepSeek 模型) |

## `--simple` 模式在对比什么

`main.py` 里有两套构建方式:

```python
# 手写:能看清每个节点和边
graph = build_graph(model, tools, checkpointer)

# 高层:一行拿到同样的 ReAct Agent
graph = create_agent(model, tools, system_prompt=SYSTEM_PROMPT, checkpointer=checkpointer)
```

`create_agent` 返回的也是编译好的 LangGraph 图,所以 `run_turn()`、流式输出、`/new`、HITL 都能复用。建议先读手写版,再跑 `--simple` 感受封装掉了什么。

## 进阶方向

- **持久化**:`SqliteSaver` / `PostgresSaver` 替换 `InMemorySaver`,重启后继续同一会话。
- **长期记忆**:LangGraph `Store` 跨 thread 保存用户偏好。
- **多 Agent**:`langgraph-supervisor`、`langgraph-swarm` 或子图。
- **MCP**:`langchain-mcp-adapters` 把外部工具接进来。
- **Web 部署**:FastAPI + SSE 包装 `graph.stream`,或使用 LangGraph Platform。
- **评估与监控**:LangSmith 数据集、评估器和线上追踪。

## 常见问题

- **`缺少 DEEPSEEK_API_KEY`**:复制 `.env.example` 为 `.env` 并填写真实 Key。
- **`知识库构建失败...connection refused`**:Ollama 没启动,执行 `ollama serve`;首次还需 `ollama pull bge-m3`,再用 `ollama list` 确认。
- **DeepSeek 能不能做 embedding?** 不能,它没有 embeddings 接口。本项目用本地 Ollama 的 `bge-m3`。
- **模型名报错**:在 `.env` 用 `DEEPSEEK_MODEL` 指定账号可用的模型;默认 `deepseek-chat`。
- **LangSmith 没数据**:确认 `LANGSMITH_TRACING=true` 和 `LANGSMITH_API_KEY` 已在启动前写入 `.env`。
