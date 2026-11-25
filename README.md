# Agent Interview Lab

一个可直接跑起来、可度量、可演示的中文 RAG / Agent 项目。它把 LangChain、LangGraph、pgvector、混合检索、重排、LLM-as-judge、OpenTelemetry/Phoenix、FastAPI/SSE、MCP、安全、长期记忆和多 Agent 串成四个阶段，并用一套冻结的 easy 集和一套 100 条的 hard 集记录真实取舍与失败模式。

项目不是“调用一次模型就结束”的 demo：每一轮回答都经过检索工具、引用校验、上下文预算、身份边界和可观测性；每次改动都用离线测试和真实评测验证。

## 目录结构

```
langchain-demo/
├── agentlab/
│   ├── cli.py               # CLI:手写图 / --simple / --multi / --user
│   ├── config.py            # 全部环境变量与项目路径
│   ├── models.py            # 对话、嵌入、裁判、fallback 模型工厂
│   ├── api/
│   │   ├── app.py           # FastAPI:JWT、限流、SSE、HITL resume、健康检查
│   │   └── static/index.html# 最小网页客户端
│   ├── agent/
│   │   ├── graph.py         # 单 Agent 图:压缩 → agent ⇄ tools
│   │   ├── multi_agent.py   # Supervisor 多 Agent:researcher/writer/critic
│   │   ├── memory.py        # 结构化长期记忆、画像、episode、TTL
│   │   └── context.py       # token 估算、裁剪、压缩、摘要
│   ├── rag/
│   │   ├── loaders.py       # Markdown 加载、标题切分、稳定 chunk_id
│   │   ├── retrieval.py     # 混合检索(BM25 + 向量 + RRF)、rerank、引用抽取
│   │   └── ingest.py        # easy/hard 语料到 pgvector
│   ├── tools/
│   │   ├── builtin.py       # calculator / search_docs / send_report
│   │   └── tickets.py       # 私有工单查询与跨用户隔离
│   ├── security/
│   │   ├── auth.py          # demo 用户、HS256 JWT、UserContext
│   │   └── guard.py         # 注入检测、PII 脱敏、工具白名单
│   ├── mcp/
│   │   ├── knowledge_server.py  # MCP 知识库 server
│   │   ├── utils_server.py      # MCP 工具 server
│   │   └── client.py            # 聚合两个 MCP server
│   ├── analytics/
│   │   ├── graph.py         # 单 Agent：理解→SQL→守卫→成本→执行→修复→回答
│   │   ├── multi_agent.py   # Supervisor→Scout→Analyst→Critic→Reporter
│   │   ├── routing.py       # single/multi/auto 路由
│   │   ├── sql_guard.py     # sqlglot 只读守卫与 allowlist
│   │   ├── db.py            # 只读连接、租户上下文、EXPLAIN 成本
│   │   ├── seed.py          # 合成数仓、指标口径、RLS
│   │   ├── versioning.py    # prompt/model 版本 registry + 请求预算
│   │   └── audit.py         # 审计与 PII 脱敏
│   └── observability/
│       ├── tracing.py       # OpenTelemetry / OpenInference → Phoenix
│       └── metrics.py       # token、成本与延迟指标
├── configs/analytics/prompts/# Analytics prompt 版本 YAML
├── data/docs/               # easy 冻结语料:8 篇 / 54 chunks
├── data/docs_hard/          # hard 语料:10 篇 / 66 chunks(噪声/冲突/表格)
├── eval/                    # golden 集、judge、指标、runner
│   ├── golden.jsonl         # easy:27 条(4 条不可回答)
│   ├── golden_hard.jsonl    # hard:100 条(六类)
│   ├── judge.py             # LLM-as-judge,支持参考答案与跨模型
│   ├── retrieval_metrics.py
│   ├── text_metrics.py      # token F1 / Exact Match
│   ├── run_eval.py          # 分层报告与 closed-book 消融
│   ├── analytics_golden.jsonl  # 50 条：40 answer / 5 clarify / 5 refuse
│   └── run_analytics_eval.py   # single/multi/auto、门禁、轨迹指标
├── scripts/
│   ├── start_db.sh          # 启动 pgvector 并写入 demo 工单
│   ├── start_analytics_db.sh # Analytics 只读角色 + 合成数仓
│   ├── ci_analytics.sh      # 单测 + 20 条 smoke + 越权/PII/回归门禁
│   ├── start_phoenix.sh     # 启动 Phoenix
│   ├── seed_demo.sql        # users/tickets 种子
│   └── demo.sh              # 一键演示脚本(见下)
├── docs/
│   ├── interview-notes.md   # 面试口述稿与真实调试故事
│   ├── mcp-clients.md       # Claude Desktop/Code/Cursor 配置
│   ├── results/             # 最终评测矩阵 Markdown 摘要
│   └── archive/             # 2026-10-20 旧计划与规格
├── tests/                   # 402 个离线测试,27 个集成测试默认跳过
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 架构

```
                    ┌──────────────────────────────┐
用户 ── CLI agentlab/cli.py │ 手写 StateGraph / create_agent │
   │   --multi      │ Supervisor 多 Agent           │
   │                └──────────────┬───────────────┘
   │                               │
   └─ 浏览器 → FastAPI agentlab/api/app.py │  JWT / 限流 / SSE / HITL
        (static/index.html)        │
                                   ▼
                    ┌──────────────────────────────┐
                    │ compact → agent ⇄ tools      │
                    │ checkpointer + Store         │
                    └───────┬──────────────┬───────┘
                            │              │
              ┌─────────────▼───┐   ┌──────▼─────────────────────┐
              │ 工具             │   │ 检索与重排                  │
              │ search_docs      │   │ pgvector / InMemory         │
              │ calculator       │   │ + BM25 + RRF + bge rerank   │
              │ get_ticket       │   └──────┬─────────────────────┘
              │ send_report      │          │
              │ save/search_memory│         │
              └──────────────────┘          │
                                            ▼
                    Postgres: checkpoints / Store / tickets / docs
                    OTel/OpenInference → Phoenix (http://localhost:6006)
                    MCP servers: agentlab/mcp/knowledge_server.py + utils_server.py
```

## 快速开始

前置条件：Python 3.12 + [uv](https://docs.astral.sh/uv/)、Docker（仅用于 pgvector 等依赖）、Ollama、一个 DeepSeek API Key。Phoenix 需要 `uvx`，只在看 trace 时使用。

本地开发**不需要构建应用镜像**：源码直接用 `uv run` 运行，Docker 只承载 pgvector/Postgres 依赖；`Dockerfile` 和 `docker-compose.yml` 仅作为部署示例保留。

```bash
cd langchain-demo
cp .env.example .env
# 编辑 .env，把 DEEPSEEK_API_KEY 换成真实 Key

# 安装全部依赖组(serve/rag/mcp/observability/dev)
uv sync --all-groups

# 另开一个终端启动 Ollama，并拉取嵌入模型
ollama serve
ollama pull bge-m3

# 启动 pgvector，并写入 demo 工单
bash scripts/start_db.sh

# 把 easy 语料切成 54 个 chunk 写入 docs collection
uv run python -m agentlab.rag.ingest --reset

# 离线测试(不需要网络/API Key/数据库)
uv run pytest -q
# 268 passed, 7 skipped

# 启动 CLI
uv run agentlab
```

`agentlab` 的几种模式：

```bash
uv run agentlab                       # 手写 StateGraph
uv run agentlab --simple              # create_agent 高层封装
uv run agentlab --multi --user alice  # Supervisor 多 Agent
uv run agentlab --user bob            # 切换 demo 用户
```

对话中可用 `/new` 开新会话、`/help` 看命令、`/quit` 退出。

### 启动 API 与网页

```bash
# 默认内存 checkpointer/Store；只适合本地快速试用
uv run uvicorn agentlab.api.app:app --host 0.0.0.0 --port 8000

# 使用 Postgres 持久化；重启后同一 session_id 仍能继续
USE_DB=true uv run uvicorn agentlab.api.app:app --host 0.0.0.0 --port 8000
```

浏览器打开 `http://localhost:8000`，用 `alice / alice-pass`、`bob / bob-pass` 或 `carol / carol-pass` 登录。页面支持流式输出、工具块、HITL 确认/取消、新会话。

命令行调用：

```bash
TOKEN=$(curl -s localhost:8000/login \
  -H 'content-type: application/json' \
  -d '{"username":"alice","password":"alice-pass"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["token"])')

curl -N localhost:8000/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -H 'content-type: application/json' \
  -d '{"message":"checkpointer 是什么","session_id":"demo"}'
```

SSE 事件类型：`token`、`tool_call`、`tool_result`、`interrupt`、`error`、`done`。`send_report` 触发 `interrupt` 后，用 `POST /chat/resume` 或 `POST /chat/stream/resume` 恢复；没有 pending interrupt 时返回 409。

### Phoenix trace

```bash
# 另开终端
bash scripts/start_phoenix.sh
# UI: http://localhost:6006

# 启动 CLI 或 API 时打开导出
TRACING_ENABLED=true uv run agentlab
# 或
TRACING_ENABLED=true USE_DB=true uv run uvicorn agentlab.api.app:app --port 8000
```

### MCP

```bash
# 默认 stdio：客户端拉起两个 server 子进程
uv run python -m agentlab.mcp.client
# 工具: ['calculator', 'doc_stats', 'list_sources', 'search_docs', 'word_count']

# API 通过 MCP 使用公共检索/计算工具(仍保留本地 ticket/memory/send_report)
USE_MCP=true uv run uvicorn agentlab.api.app:app --port 8001
```

HTTP transport 与外部客户端配置见 [docs/mcp-clients.md](docs/mcp-clients.md)。

### 一键演示

```bash
bash scripts/demo.sh
```

脚本会依次检查环境、安装依赖、跑离线测试、启动数据库、摄入 easy/hard 语料、跑 3 条硬评测、演示 MCP 工具发现，并打印 API 与多 Agent CLI 的启动命令。需要 DeepSeek Key 的步骤会先检查 `.env`；交互式/常驻命令默认只打印，不自动占用终端。

## 四阶段地图

### 阶段 1：评测与可观测(问题 → 方案 → 取舍 → 指标 → 失败模式)

- **问题**：没有 golden set 和 trace 时，“回答变好了”只能靠感觉；RAG 的失败也无法归因到检索、重排还是生成。
- **方案**：8 篇冻结语料 + 27 条 easy golden(4 条不可回答)；LLM-as-judge 输出 correctness/faithfulness/citation_support；OpenTelemetry + OpenInference 导出到 Phoenix。
- **取舍**：judge 用 DeepSeek 的 JSON mode(thinking mode 不支持 tool_choice)；judge 只看 agent 实际检索到的 ToolMessage，不把预取 top-k 算进 citation_support，指标更严格但更接近真实证据。
- **指标**：easy baseline `task_success=1.0`、`citation_support=1.0`、`R@3=0.8696`、`MRR=0.8188`、`nDCG@3=0.8081`。
- **失败模式**：easy 集接近饱和；q18 曾出现回答加入“降采样不等于脱敏”等工具证据不支持的内容，citation_support=false。
- **代码入口**：`eval/`、`agentlab/observability/tracing.py`、`scripts/start_phoenix.sh`。

### 阶段 2：服务化与持久化

- **问题**：CLI 无法演示多用户、并发、断线、HITL 和重启恢复。
- **方案**：FastAPI + SSE；JWT(HS256)只从服务端 token 解析 user_id；`thread_id = user_id:session_id`；同一 thread 用 `asyncio.Lock` 串行化；Postgres checkpointer/Store；`/chat/resume` 消费 interrupt，第二次返回 409。
- **取舍**：限流是进程内内存计数，不是分布式；超时用 `asyncio.wait_for`；中断后若用户直接发新消息，`_prepare_thread` 会修复/重置悬空 tool_call，优先保证不 400。
- **指标/验证**：重启 API 后同一 session_id 能继续；SSE 的 tool_call/tool_result 用 id 配对；HITL 确认/取消可用。
- **失败模式**：中断/并发会留下 assistant tool_calls 没有对应 ToolMessage，LangGraph 会报 400；现在每轮前补齐或重置。
- **代码入口**：`agentlab/api/app.py`、`agentlab/security/auth.py`、`scripts/start_db.sh`、`agentlab/api/static/index.html`。

### 阶段 3：RAG 升级

- **问题**：纯向量 top-3 对关键词、表格和版本冲突不敏感。
- **方案**：pgvector 摄入；BM25 + 向量各取 8 条，RRF(k=60)融合取 6；默认 bge-reranker-v2-m3 作为 cross-encoder 重排，top_n=3；引用格式 `[来源:文件#章节]`。
- **取舍**：cross-encoder 在 CPU 上让 p50 增加约 0.7–1.4 秒(hard 约 0.75 秒，easy 约 1.35 秒)；LLM rerank 保留为可选第二层，默认关闭；rerank 只作用于 agent 的工具证据，预取检索指标不经过 rerank，因此 R@3/MRR 在 hybrid 与 hybrid+rerank 之间相同。
- **指标**：easy baseline → hybrid+rerank：R@3 0.8696 → 0.9130，MRR 0.8188 → 0.8623，nDCG@3 0.8081 → 0.8462；hard baseline → hybrid+rerank：answerable_success 0.8118 → 0.8588，MRR 0.8490 → 0.8878。rerank 在本轮 hard 上没有提升 task_success(0.83 vs hybrid 0.86)，但 citation_precision 从 0.9294 提升到 0.9412，代价是 p50 增加约 0.75 秒。
- **失败模式**：中文长表格仍可能被 chunk 边界截断；hard 集的多跳和歧义题暴露召回与聚合不足。
- **代码入口**：`agentlab/rag/ingest.py`、`agentlab/rag/retrieval.py`、`agentlab/rag/loaders.py`、`agentlab/tools/builtin.py`、`eval/retrieval_metrics.py`。

### 阶段 4：MCP、安全、记忆、多 Agent

- **问题**：工具边界、跨用户数据、上下文膨胀和多 Agent 协作都需要真实实现，而不是概念演示。
- **方案**：
  - MCP：两个公共只读 server，stdio 默认、streamable HTTP 可选；API 用 `USE_MCP=true` 聚合 5 个工具，ticket/memory 留在本地。
  - 安全：进入图前拒绝 prompt injection；PII 在日志/SSE/span 中脱敏；工具 allowlist + 构建期 drift 检查；ticket 只允许 owner。
  - 记忆：checkpointer 短期、Store 长期；profile/fact/preference/episode 分命名空间；规则触发抽取、去重、episode TTL；上下文达 80% 时压缩，摘要写入 state.summary。
  - 多 Agent：Supervisor + researcher/writer/critic，MAX_STEPS=6；critic 失败默认 faithful=true，避免无限循环。
- **取舍**：多 Agent 不绑定工具、不做压缩/画像注入，换来清晰的路由与更低的实现复杂度；自动记忆默认关闭，避免每轮多一次模型调用；`--simple` 也不做压缩/画像。
- **指标**：hard closed-book 消融的 answerable_success 为 0.0353，对比 open-book baseline 的 0.8118；task_success 为 0.12 vs 0.83(两者定义不同，见指标说明)。MCP 发现 5 个工具并成功调用；跨用户 ticket/memory 测试通过。
- **失败模式**：hard 集的歧义题经常选择“请求澄清”而不是列出多种解释，judge 按参考答案只给部分分；qwen3.5:4b 裁判有 1 条缺 `reason` 的解析失败，走了安全默认。
- **代码入口**：`agentlab/mcp/knowledge_server.py`、`agentlab/mcp/utils_server.py`、`agentlab/mcp/client.py`、`agentlab/security/guard.py`、`agentlab/tools/tickets.py`、`agentlab/agent/memory.py`、`agentlab/agent/context.py`、`agentlab/agent/multi_agent.py`。

## 评测方法与结果

### 数据集

| 集合 | 条数 | 不可回答 | 用途 |
|---|---:|---:|---|
| easy | 27 | 4 | 冻结回归集，不允许改动 |
| hard | 100 | 15 | 加固评测：单跳 30、多跳 25、时间/版本 10、歧义 10、表格/数值 10 |

hard 语料 `data/docs_hard/` 包含噪声、重复、过期版本、互相冲突的内容和 Markdown 表格；它与 easy 的 `docs` collection 完全隔离。hard golden 每条带 `difficulty`、`category` 和 `reference_answer`。

**hard 语料是一个合成的 AgentLab 文档世界，不是本仓库配置的说明书。** 其中 HNSW 参数、90 天 checkpoint 保留期、历史成本/延迟、以及“某功能有独立 span”等说法，是刻意放置的版本冲突、过期信息或噪声材料，用来测试模型的版本判断和抗干扰能力；它们不代表当前代码的真实行为。hard 指标衡量的是模型在这个文档世界里的检索、多跳推理和引用能力，而不是对代码配置的核查。真实行为以 README、`agentlab/config.py`、测试和实际 trace 为准。

### 指标定义

- 检索：Recall@3、MRR、nDCG@3；新增 Context Precision@3、Context Recall@3。
- 生成：`answerable_success = correctness>=4`(可回答题，跨开/闭卷可比)；开卷 `task_success = answerable_success 且 citation_support`；闭卷 `task_success = answerable_success`；不可回答题 `task_success = 拒答 且 faithfulness>=4`(拒答后继续编造不算成功)。
- `tool_accuracy` 采用“必需工具子集”口径：额外的安全工具(例如算术题同时用 calculator)不扣分，缺少必需工具才算失败。`citation_support_rate` 只统计可回答题；`refusal_rate` 只统计不可回答题。
- 新指标：Token F1、Exact Match(分词后)；Citation Precision(引用被工具证据支持的比例)。
- 延迟/成本：p50/p95、总 token、按 DeepSeek 单价估算的成本。

### 完整矩阵(qwen 裁判 = 本机 `qwen3.5:4b`)

**easy(27 条)**

| retriever | judge | task_success | answerable_success | correctness | citation_support | R@3 | MRR | nDCG@3 | p50 ms | cost 元 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | DeepSeek | 1.0000 | 1.0000 | 5.0000 | 1.0000 | .8696 | .8188 | .8081 | 3038 | .1879 |
| baseline | qwen3.5:4b | .9630 | .9565 | 4.5556 | 1.0000 | .8696 | .8188 | .8081 | 3396 | .1933 |
| hybrid | DeepSeek | .9630 | 1.0000 | 4.9259 | .9565 | .9130 | .8623 | .8462 | 2986 | .1858 |
| hybrid | qwen3.5:4b | 1.0000 | 1.0000 | 4.8148 | 1.0000 | .9130 | .8623 | .8462 | 2850 | .1873 |
| hybrid+rerank | DeepSeek | 1.0000 | 1.0000 | 5.0000 | 1.0000 | .9130 | .8623 | .8462 | 4391 | .1889 |
| hybrid+rerank | qwen3.5:4b | 1.0000 | 1.0000 | 4.6296 | 1.0000 | .9130 | .8623 | .8462 | 4570 | .1906 |

**hard(100 条)**

| retriever | judge | task_success | answerable_success | correctness | citation_support | R@3 | MRR | nDCG@3 | p50 ms | cost 元 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | DeepSeek | .8300 | .8118 | 4.4500 | .9294 | .7875 | .8490 | .7698 | 2552 | .6371 |
| baseline | qwen3.5:4b | .8600 | .8706 | 4.1200 | .9647 | .7875 | .8490 | .7698 | 2733 | .6649 |
| hybrid | DeepSeek | .8600 | .8706 | 4.6600 | .9412 | .7722 | .8878 | .7808 | 2680 | .6423 |
| hybrid | qwen3.5:4b | .8800 | .9059 | 4.3000 | .9647 | .7722 | .8878 | .7808 | 2669 | .6447 |
| hybrid+rerank | DeepSeek | .8300 | .8588 | 4.5600 | .9176 | .7722 | .8878 | .7808 | 3426 | .6356 |
| hybrid+rerank | qwen3.5:4b | .8900 | .9059 | 4.1700 | .9647 | .7722 | .8878 | .7808 | 3429 | .6318 |

**closed-book 消融(hard,DeepSeek 裁判)**：移除 `search_docs` 后 `answerable_success=0.0353`(3/85)、`task_success=0.12`、correctness=1.27、refusal_rate=0.7333、cost=0.2310；open-book baseline 的 `answerable_success=0.8118`、`task_success=0.83`。开卷/闭卷的 task_success 定义不同，检索贡献主要看 `answerable_success`：3.5% vs 81.2%。

### 关键结论

1. **easy 已饱和，hard 才有区分度**：easy 的 task_success 在 0.963–1.0；hard 在 0.83–0.89，且按难度分层可见 easy .946 / medium .765 / hard .759(DeepSeek baseline)。
2. **失败集中在歧义、多跳、表格**：hard baseline 按类别 task_success：歧义 0.30、多跳 0.76、表格 0.80、单跳 0.967、时间/版本 1.0、不可回答 0.933。歧义题常选择“请求澄清”而非列出所有解释，参考答案严格 rubric 只给部分分；表格题有时不调用检索、直接凭记忆回答；不可回答题中有一条拒答后仍加了证据不支持的建议，被 faithfulness 判失败。
3. **混合检索提升排序，rerank 不是免费午餐**：hard MRR 0.8490(baseline) → 0.8878(hybrid)，nDCG@3 0.7698 → 0.7808；rerank 把 citation_precision 从 0.9294 提到 0.9412，但本轮 task_success 为 0.83(hybrid 0.86)，且 p50 增加约 0.75 秒。样本量小加上严格 judge，rerank 的收益需要更多样本验证。
4. **closed-book 明显更差**：`answerable_success` 3.5% vs 81.2%，说明检索不是装饰。
5. **裁判模型会改变结论**：hard baseline 下 DeepSeek 裁判 task_success .83 / correctness 4.45，qwen3.5:4b 为 .86 / 4.12；easy baseline 下 qwen 的 correctness 4.56 vs DeepSeek 5.0。qwen 对 citation_support 更宽松、对 correctness 更严格。跨模型对照是必要的，不能只看单一 judge。
6. **Token F1/EM 只作词面参考**：参考答案较长、回答措辞自由，hard 的 avg_token_f1 约 0.22、EM=0；这不能说明回答错，主指标仍是 reference-based judge。

### 复现命令

```bash
# easy baseline / hybrid / hybrid+rerank
uv run python -m eval.run_eval --corpus easy --retriever baseline \
  --output eval/results/easy-baseline-deepseek.md
uv run python -m eval.run_eval --corpus easy --retriever hybrid \
  --output eval/results/easy-hybrid-deepseek.md
uv run python -m eval.run_eval --corpus easy --retriever hybrid --rerank \
  --output eval/results/easy-hybrid-rerank-deepseek.md

# hard 三种检索 × 两种裁判
uv run python -m eval.run_eval --corpus hard --retriever baseline \
  --output eval/results/hard-baseline-deepseek.md
uv run python -m eval.run_eval --corpus hard --retriever hybrid \
  --output eval/results/hard-hybrid-deepseek.md
uv run python -m eval.run_eval --corpus hard --retriever hybrid --rerank \
  --output eval/results/hard-hybrid-rerank-deepseek.md
uv run python -m eval.run_eval --corpus hard --retriever baseline \
  --judge-model qwen3.5:4b \
  --output eval/results/hard-baseline-qwen35-4b.md

# closed-book 消融
uv run python -m eval.run_eval --corpus hard --retriever baseline \
  --closed-book --output eval/results/hard-closed-book.md

# 快速 smoke
uv run python -m eval.run_eval --corpus hard --limit 3
```

hard 语料首次评测前需要摄入：

```bash
uv run python -m agentlab.rag.ingest --docs-dir data/docs_hard --collection docs_hard --reset
```

## 安全模型

- **身份**：`user_id` 只从服务端校验后的 HS256 JWT 读取，请求体不能指定；API 的 `thread_id` 固定为 `user_id:session_id`，用户 A 不能用 B 的 session_id 接着 B 的会话。
- **私有数据**：`get_ticket` 只返回当前用户自己的工单；跨用户统一返回“未找到或无权限”，不泄露工单是否存在。长期记忆命名空间包含 user_id，bob 问 alice 的姓名应回答不知道。
- **Prompt injection**：输入命中“忽略之前的指令 / ignore previous instructions / system prompt / 泄露提示词 / 你现在是”等模式时，在进入图之前直接拒绝，不调用模型。
- **PII**：日志、SSE 工具参数/结果、trace span 属性统一脱敏为 `[EMAIL]`、`[PHONE]`、`[ID]`、`[CARD]`。
- **工具边界**：只允许白名单内的 9 个工具；`ensure_tools_allowed()` 在构建图时检查漂移，未知工具直接拒绝并返回 ToolMessage。
- **限流/超时**：每用户每分钟 30 次，单轮 60 秒；超限 429，超时 504/SSE error。
- **已知边界**：JWT 只签名不加密；demo 密码在内存字典；限流是单进程内存计数；生产必须换密钥、加 HTTPS、用真正的用户库和分布式限流。

## MCP

- `agentlab` server：`search_docs`、`list_sources`、`doc_stats`(公共只读)。
- `utils` server：`calculator`、`word_count`(纯工具)。
- 默认 stdio；需要多客户端/跨机器时用 `--transport streamable-http`，端口 8811/8812。
- 公共 MCP 不暴露 ticket/memory 和写操作；`send_report` 留在 API 进程内做 HITL。
- `USE_MCP=true` 时 API 使用 MCP 的 `search_docs` + `calculator`，要求两者都存在，否则启动失败并给出中文错误。
- 外部客户端配置与 stdio/HTTP 取舍见 [docs/mcp-clients.md](docs/mcp-clients.md)。

## 记忆与上下文

- **短期**：checkpointer 按 thread 保存执行现场；默认 InMemory，`USE_DB=true` 时用 AsyncPostgresSaver。项目本身没有自动清理策略，部署时可按需加保留期与清理任务。
- **长期**：Store 按 `("user", user_id, type)` 分命名空间；type 为 profile/fact/preference/episode。episode 默认 TTL 30 天，其他类型无 TTL。
- **写入**：规则命中的用户消息触发结构化抽取；显式 `save_memory` 优先于自动抽取；去重使用语义搜索 + `SequenceMatcher >= 0.9`。
- **压缩**：上下文达到 `CONTEXT_MAX_TOKENS` 的 80% 时，把旧消息摘要进 `state.summary`，用 `RemoveMessage` 删除旧消息，并随 checkpoint 持久化；原始旧消息不再保留。
- **开关**：`ENABLE_AUTO_MEMORY=false` 默认关闭；`MEMORY_EPISODE_TTL_DAYS=30`；`CONTEXT_MAX_TOKENS=6000`。
- **限制**：InMemoryStore 没有 TTL；`--simple` 不压缩/不注入画像；多 Agent 模式不做压缩/画像。

## 多 Agent

```bash
uv run agentlab --multi --user alice
# 问:checkpointer 是什么?
# 观察:supervisor → researcher → writer → critic → __end__
```

- 节点：researcher 检索写 research_notes；writer 基于笔记生成带引用的 draft；critic 用结构化输出判断是否忠实；supervisor 用 `Command(goto=...)` 路由。
- 上限：`MAX_STEPS=6`；critic 判定不忠实且未到上限时回到 writer；critic 调用失败默认 faithful=true。
- 取舍：多 Agent 不绑定工具、不做上下文压缩、不注入用户画像；它适合演示“检索 → 写作 → 审阅”的分工，不适合替代单 Agent 的工具循环。
- 代码入口：`agentlab/agent/multi_agent.py`、`agentlab/cli.py` 的 `--multi`。

## 数据分析 Agent（Text-to-SQL）

Analytics Agent 是独立于 RAG 主线的第二个作品：面向多租户数仓的自然语言分析，重点不是“生成 SQL”，而是评测、安全、成本与可靠性。

### 架构与安全

- 单 Agent 显式状态机：`understand → clarify/refuse → plan_sql → validate_sql → estimate_cost → approve → execute → repair → answer`。
- 三层 SQL 安全：`sqlglot` 守卫（单条 SELECT、表 allowlist、默认/最大 LIMIT）、只读角色 `analytics_reader`、PostgreSQL RLS（`SET LOCAL app.tenant_id`）。
- PII：`customers_safe` 视图（`security_invoker=true`），原始 `customers` 只给列级 SELECT；DB 错误、审计 question/sql、结构化日志统一 `redact_pii`。
- 成本守卫：`EXPLAIN (FORMAT JSON)` 解析 Total Cost；超阈值触发 `interrupt` 人工审批；没有 checkpointer/thread_id 时 fail closed，不静默返回空结果。
- 审计：每次公共入口 `run_analytics_question` 写一条 `analytics_audit`，`request_id` 关联 trace/metrics。
- 多 Agent（非默认）：Supervisor → Scout → SQL Analyst → Critic → Reporter，`Command(goto=...)` 路由，`MAX_STEPS=6`。Scout 产出 `schema_brief`，Analyst 产出 `sql/result`，Critic 只评审不执行 SQL，Reporter 只读结果；Critic 失败默认不通过，重复 SQL 会被检测并停止重试。

### Prompt/模型版本与预算

- Prompt 模板与版本在 `configs/analytics/prompts/*.yaml`：每个 prompt 有 `active` 版本，每个版本可指定 `model` id；运行时由 `PromptRegistry` 读取。
- 回滚不改代码：`ANALYTICS_PROMPT_UNDERSTAND_VERSION=v2` 覆盖 active 版本，或在构造 `PromptRegistry(overrides=...)` 时指定。
- 模型路由按 YAML 的 model id 取模型并缓存；`default` 表示 `DEEPSEEK_MODEL`。
- 每次模型调用把 `prompt_id/version/model_id` 写入 span；`run_analytics_question` 把汇总写进 `analytics_audit.prompt_version` / `model_id`。
- 请求级模型调用预算：`ANALYTICS_REQUEST_BUDGET` + `ANALYTICS_MODEL_CALL_COST`。超预算返回可读答案（“本次分析超出成本预算…”），审计 status=`budget`，不抛 500。
- 当前 registry 覆盖默认单 Agent 的 understand/plan_sql/repair/answer；multi 的 Scout/Critic/Reporter prompt 仍是代码内常量，等 multi 成为默认或需要灰度时再迁入。

### 评测集与指标

- 50 条 golden：40 可回答 / 5 歧义 / 5 不可回答，覆盖 join、聚合、窗口、时间、退款、权限、PII、昂贵查询。
- 结果归一化：行顺序无关、数值 `rel_tol=1e-9 + abs_tol=0.01`、空值与重复行严格计数。
- 指标：`task_success`、`execution_accuracy`、clarification/refusal rate、P50/P95、真实 token/成本、`route_accuracy`、`plan_validity`、`avg_step_count`、Critic 拦截率、9 类 failure class 与恢复率。
- CI：`scripts/ci_analytics.sh` 跑全量单测 + 20 条 smoke；越权 >0、PII >0、task_success 回退 >3% 都会失败。

### single vs multi vs auto（50 条）

成本按真实 token、¥2/百万 token 混合单价估算。“复杂子集”= tags 含 `join`/`window`/`expensive` 的 17 条。

| 架构 | task_success | 复杂子集 | P95 | 平均成本/题 | 平均 token | 平均步骤 | Critic 拦截率 | 路由 single/multi |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| single | 1.000 | 17/17 | 8.37s | ¥0.00558 | 2788 | 0.8 | — | 50 / 0 |
| multi | 0.980 | 17/17 | 14.23s | ¥0.00638 | 3192 | 3.5 | 2.4% | 0 / 50 |
| auto | 1.000 | 17/17 | 9.77s | ¥0.00552 | 2761 | 0.86 | 0% | 49 / 1 |

**结论：多 Agent 不是默认，是数据证明后的路由选择。**

- multi 在复杂子集上没有提升（1.000 vs 1.000），但 P95 +70%、平均步骤 0.8→3.5、成本 +14.5%，因此默认 single。
- forced multi 的 0.98 来自一条歧义题被 Scout 误判为 answer；auto 在进入 multi 前先用同一意图解析器把 clarify/refuse 留在 single，所以 auto 仍为 1.000。
- auto 只把 1/50 路由到 multi，成功率和 single 相同；它保留为路由实验入口，暂不设为默认。
- multi 保留为可选深分析模式：适合需要显式 Scout/Critic 轨迹、或未来接入多步计划执行的场景。

### 复现

```bash
bash scripts/start_analytics_db.sh

# 50 条 single / multi / auto；--auto-approve 只用于评测昂贵查询
uv run python -m eval.run_analytics_eval --arch single --limit 50 --auto-approve
uv run python -m eval.run_analytics_eval --arch multi  --limit 50 --auto-approve
uv run python -m eval.run_analytics_eval --arch auto   --limit 50 --auto-approve

# CI 门禁：单测 + 20 条 smoke + 越权/PII/回归阈值
bash scripts/ci_analytics.sh
```

汇总文件：`eval/analytics_baseline_50.json`、`eval/analytics_ab_summary.json`；完整 trace/报告在本地 `eval/results/`（gitignore）。

## 已知限制与下一步

1. **hard 标签由实现者生成**，未做多人标注/仲裁；reference_answer 和 relevant_chunk_ids 有主观性，样本量 100 仍不足以给出窄置信区间。
2. **裁判偏差**：DeepSeek 与 qwen3.5:4b 的结论不同；同一模型裁判可能偏爱自己的表达；qwen3.5:4b 在 hard-hybrid 有 1 条缺 `reason` 的解析失败(安全默认，不影响不可回答题的 task_success)。
3. **检索指标与 rerank 分离**：R@3/MRR/nDCG 衡量预取管线，rerank 只作用于 agent 工具证据，所以 hybrid 与 hybrid+rerank 的检索指标相同；要看 rerank 收益应看 citation_precision/task_success。
4. **closed-book 消融较粗**：移除 search_docs 但保留原 system prompt，模型可能用参数知识作答；task_success 又要求引用，因此 answerable 行结构性地接近 0，适合看趋势而非绝对分数。
5. **Token F1/EM 不适合作为主指标**：参考答案较长、回答措辞自由，词面指标天然偏低。
6. **InMemory 与 Postgres 行为不同**：InMemoryStore 无 TTL；CLI 的长期记忆只在进程内；跨重启需要 API + `USE_DB=true`。
7. **`--simple`/`--multi` 功能不完整**：缺少压缩、画像注入或工具绑定；这是有意的取舍。
8. **生产化缺口**：demo 用户/JWT/限流/MCP HTTP 鉴权都需要替换；仓库没有 GitHub Actions（Analytics 只有本地 `scripts/ci_analytics.sh`），也缺分布式锁、密钥轮换和真正的监控告警。
9. **Analytics golden 绑定合成数据**：50 条 expected_result 绑定 `scale=1.0` 的固定 seed；换数仓、改口径或重新灌数都要重算，不能直接当生产回归集。
10. **多步计划尚未接线**：`planning`/`verification`/`executor` 已有库级测试，但默认图仍是单 SQL；因此 `plan_validity`/`step_count` 对 single 是单步基线，`unnecessary_steps` 只统计重复 SQL。
11. **auto 路由是启发式**：按 metrics/dimensions/关键词判断，50 条里只把 1 条路由到 multi；需要更多复杂样本校准阈值，否则“多 Agent 路由”可能只是名义上的。
12. **Analytics 尚无语义层/数仓适配器**：指标口径写在 `catalog.py`，没有 dbt/Semantic Layer 或 MySQL/BigQuery 方言适配；下一步是 metric catalog 版本化、BIRD/Spider 子集和客服 domain adapter。

下一步优先级：多人标注 hard 集并计算置信区间 → 固定生成结果后做 judge 一致性研究 → 引入上下文 precision/recall 的 retrieval 诊断 → 把 MCP HTTP 放到带 TLS/Bearer 的网关后 → Analytics 接多步计划执行与语义层。

## 常见问题

- **`缺少 DEEPSEEK_API_KEY`**：复制 `.env.example` 为 `.env` 并填写真实 Key。
- **Ollama connection refused**：先 `ollama serve`，再 `ollama pull bge-m3`；首次 rerank 会下载 `BAAI/bge-reranker-v2-m3`。
- **Postgres 连接失败/健康检查 503**：运行 `bash scripts/start_db.sh`；hard 评测还要先摄入 `docs_hard`。
- **Phoenix 看不到 trace**：确认 `TRACING_ENABLED=true`、Phoenix 在 6006、进程退出时调用了 `shutdown_tracing`；API 只在真实启动(未注入 fake services)时初始化 tracing。
- **MCP 启动失败**：`USE_MCP=true` 要求两个 server 都可用且提供 `search_docs`+`calculator`；先单独跑 `uv run python -m agentlab.mcp.client`。
- **评测结果和 README 不完全一样**：模型输出有随机性；本 README 记录的是 2026-10-24 的具体运行。最终矩阵的 Markdown 摘要见 `docs/results/`，原始 JSON 在本地 `eval/results/`（被 gitignore）。

## 面试怎么讲

每个主题的 5–8 行口述稿、指标解释和 5 个真实调试故事见 [docs/interview-notes.md](docs/interview-notes.md)。
