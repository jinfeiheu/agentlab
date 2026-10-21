# Agent Interview Lab — 设计说明

- 日期：2026-10-21
- 状态：已与用户确认（2026-10-21）
- 定位：面试作品 + 学习载体，从现有 `langchain-demo` 演进为可评测、可观测、可部署、可演示的 Agent 项目。

## 意图与理由

用户要用这个项目准备 Agent / LLM 应用工程师面试，并希望亲手理解岗位要求里的技能是“怎么做出来的”，而不只是知道名词。现有 `langchain-demo` 已经覆盖模型接入、Prompt、工具、RAG、LangGraph 状态图、checkpoint、HITL、流式和单元测试；缺的是**评测、可观测、生产服务、RAG 质量、MCP、安全、记忆、多 Agent**。

项目按四个阶段演进，每个阶段都能独立运行、独立演示，并配一段“面试时怎么讲”。代码保持精简：新增约 1000–1200 行，每个文件只做一件事，避免企业级样板代码。

## 目标

1. **阶段 1：评测 + 可观测** — golden set、LLM-as-judge、回归测试、Phoenix trace、token/成本/延迟。
2. **阶段 2：服务化** — FastAPI + SSE、会话、Docker、健康检查、限流/超时、最小网页。
3. **阶段 3：RAG 升级** — 文档摄入、pgvector、BM25 + 向量混合检索、RRF、rerank、引用溯源、检索评测。
4. **阶段 4：MCP + 安全 + 记忆 + 多 Agent** — MCP Server/Client、工具权限、prompt injection/PII、长期记忆、上下文压缩、supervisor 多 Agent。

最终能演示：CLI、FastAPI/SSE、Phoenix trace、eval 报告、pgvector 混合检索、MCP 工具调用、安全测试、长期记忆、多 Agent。

## 非目标

- 不做生产级多租户 SaaS、K8s、高可用、完整 RBAC、复杂前端；但做一个 **3 个合成用户的 demo 隔离**（服务端绑定身份，验证 memory/ticket 不能跨用户）。
- 不复用工作区里的 `bank-cs-agent`；两者保持独立，避免数据和身份模型耦合。
- 不训练/微调模型，不做语音/多模态，不追求 benchmark SOTA。
- 不引入大型工作流平台；所有编排保持手写、可读。
- 使用 git：先做基线提交；之后每个任务完成后先与用户讨论，确认后再提交，再进入下一个任务。提交信息带 `Co-Authored-By: Claude Code <noreply@anthropic.com>`。

## 约束与环境

- WSL2，Python 3.12，`uv` 管理依赖。
- 模型：DeepSeek（对话/裁判），Ollama `bge-m3`（嵌入），Ollama `qwen3:8b`（可选 fallback）。
- Docker daemon 可用；无 `docker compose` 插件；Docker Hub 直连超时，使用 `docker.m.daocloud.io` 镜像。
- 无 LangSmith Key；可观测性使用本地 **Arize Phoenix**（OpenTelemetry），不依赖云 Key。
- 语料：以现有技术栈说明为基础扩写为 **8 篇技术栈文档（约 50–55 个 chunk）**，作为阶段 1/3 的冻结语料；golden set **27 条（含 4 条不可回答）**，closed-book，标签由实现者生成、用户抽查。
- 身份：**3 个合成用户**（user_a/user_b/user_c），服务端登录后签发简单 HMAC token；API 从 token 解析 `user_id`，客户端不能自选。
- 用户界面/注释使用中文；代码量优先，不追求抽象层级。

## 架构

```
Browser / curl / CLI
        │
        ▼
FastAPI (SSE) 或 CLI
        │
        ▼
LangGraph 图（单 Agent / supervisor 多 Agent）
        │
        ├─ 模型：ChatDeepSeek（可选 Ollama fallback）
        ├─ 工具：search_docs / calculator / send_report / memory / MCP tools
        ├─ 检索：pgvector 向量检索 + BM25 → RRF → rerank
        └─ Checkpointer + Store：Postgres（测试用 InMemory）
        │
        ▼
Postgres + pgvector        Phoenix（trace UI）        eval harness
```

## 阶段与验收

### 阶段 1：评测 + 可观测

**代码**
- `eval/golden.jsonl`：27 条中文问题（含 4 条语料外/不可回答），含期望来源、相关 chunk、关键点、期望工具；closed-book（只依据检索片段回答，找不到就说不知道）。
- 语料：`data/docs/*.md` 8 篇技术栈文档（由现有技术栈说明扩写），约 50–55 个 chunk，阶段 1 冻结；标签由实现者生成，用户抽查。
- `eval/judge.py`：DeepSeek + Pydantic 结构化输出，评 correctness / faithfulness / citation_support。
- `eval/run_eval.py`：跑 golden set，输出 Markdown + JSON 报告；指标含任务成功率、工具选择准确率、引用支持率、P50/P95 延迟、单任务成本。
- `eval/retrieval_metrics.py`：Recall@k、MRR、nDCG@k（纯 Python）。
- `tracing.py`：Phoenix/OTel 初始化 + 手动 span（retrieve / rerank / model / tool）。
- `scripts/start_phoenix.sh`：本地启动 trace UI。
- `metrics.py`：token/成本/延迟记录，DeepSeek 价格表。

**验收**
- `uv run python eval/run_eval.py` 输出报告；基线指标可复现。
- 浏览器打开 Phoenix，能看到一次问答的模型、工具、检索 span。
- 离线单元测试通过；真实 eval 需要 API Key，单独标记。

**面试讲点**：golden set 怎么建、LLM-as-judge 偏差、如何从 trace 定位失败、成本/延迟怎么算。

### 阶段 2：服务化

**代码**
- `api.py`：FastAPI。
  - `POST /login`：3 个合成用户登录，返回 HMAC token。
  - `POST /chat/stream`：SSE 流式 token + 工具事件。
  - `POST /chat`：非流式 JSON。
  - `POST /chat/resume`：HITL 恢复（可选）。
  - `GET /healthz`、`GET /sessions/{id}`、`GET /`（最小网页）。
- `auth.py`：demo 用户表、HMAC 签名/校验、FastAPI 依赖 `get_current_user`。
- `static/index.html`：最小聊天页（登录 + `fetch` 读取 SSE）。
- 会话：`session_id` / `user_id`，checkpointer 持久化；`user_id` 只从 token 解析。
- 稳定性：每会话限流、请求超时、简单重试、结构化日志。
- `Dockerfile`、`docker-compose.yml`、`scripts/start_db.sh`（compose 不可用时用 `docker run`）。

**验收**
- `curl -N` 能看到 SSE token；浏览器能对话。
- 重启 API 后同一 `session_id` 仍能继续。
- 未登录/伪造 token 被拒绝；用户不能通过请求体指定别人的 `user_id`。
- 健康检查、超时、限流可用；离线 API 测试通过。

**面试讲点**：SSE vs WebSocket、无状态 API + 状态存储、超时/重试/幂等、demo 身份 vs 生产 OAuth/OIDC、容器化与配置。

### 阶段 3：RAG 升级

**代码**
- `ingest.py`：`data/docs/*.md` → Markdown 标题切分 → 递归切块 → bge-m3 → pgvector。
- `retrieval.py`：向量 top-k + jieba/BM25 top-k → RRF 融合 → LLM rerank（可配置开关）→ 带 source/section 的引用。
- 检索评测：golden 中标注相关 chunk，计算 Recall@k/MRR/nDCG。
- `scripts/init_db.sh`：启动 pgvector、建扩展/表。

**验收**
- `uv run python ingest.py --reset` 可重建索引。
- 混合检索相比纯向量在 golden set 上 Recall/MRR 有提升（或至少可比较）。
- 回答带 `[来源:文件#章节]`；API 返回 `sources`。
- 检索评测报告可复现。

**面试讲点**：chunking 策略、混合检索、RRF、rerank 的收益/成本、引用与忠实度、向量库选型。

### 阶段 4：MCP + 安全 + 记忆 + 多 Agent

**代码**
- `mcp_server.py`：FastMCP 暴露 `search_docs`（只读、公共知识库）工具；**不暴露用户私有 ticket**，避免把身份边界带进 MCP。
- `mcp_client.py`：`langchain-mcp-adapters` 加载 MCP 工具并注入 agent。
- `tickets.py`：本地 `get_ticket(ticket_id)` 工具，从 runtime context 取当前 `user_id`，校验 ticket owner；跨用户返回拒绝。
- `security.py`：输入注入检测、PII 脱敏、工具 allowlist/风险等级、输出脱敏；`send_report` 仍需 HITL；“越权”包括工具策略拒绝、跨用户 ticket/memory 访问。
- `memory.py`：LangGraph `Store` + `save_memory` / `search_memory` 工具；按 `("user", user_id)` 命名空间；每轮后摘要保存（可开关）；3 个用户记忆互相隔离。
- `context.py`：token 估算、历史裁剪/摘要、工具结果压缩。
- `multi_agent.py`：手写 supervisor → researcher → writer → critic，使用 `Command(goto=...)`；CLI `--multi` 演示。
- `models.py`：主模型 + 可选 fallback（DeepSeek → Ollama qwen3:8b）。
- 安全测试：注入样例、PII、越权工具调用、恶意参数。

**验收**
- MCP 工具能在 agent 中被发现并调用。
- 安全测试全部通过；越权工具被拒绝；日志中 PII 已脱敏。
- 跨会话能检索到用户偏好；`/new` 只清短期记忆，不清长期记忆。
- 用户 A 不能读取用户 B 的 ticket 或 memory（单元测试 + 集成测试）。
- `--multi` 能演示 supervisor 路由和 critic 回环；单 Agent 模式仍可用。
- eval 在升级后仍可运行，指标不劣化。

**面试讲点**：MCP 协议与权限、prompt injection 防御层次、记忆策略与遗忘、supervisor 的收益/代价、上下文压缩。

## 目标文件结构

```
langchain-demo/
├── main.py              # CLI 入口（保留）
├── graph.py             # 单 Agent 图构建（从 main.py 拆出）
├── api.py               # FastAPI + SSE
├── auth.py              # demo 用户 + HMAC token
├── tickets.py           # 用户私有 ticket + owner 校验
├── models.py            # 模型/fallback
├── tools.py             # 本地工具
├── rag.py               # 基线 RAG（保留，作为对照）
├── retrieval.py         # pgvector + BM25 + RRF + rerank
├── ingest.py            # 文档摄入
├── memory.py            # 长期记忆
├── security.py          # 输入/输出/工具策略
├── context.py           # token 预算、裁剪、摘要
├── tracing.py           # Phoenix/OTel
├── metrics.py           # token/成本/延迟
├── multi_agent.py       # supervisor 多 Agent
├── mcp_server.py        # MCP Server
├── mcp_client.py        # MCP Client 适配
├── eval/
│   ├── golden.jsonl
│   ├── judge.py
│   ├── run_eval.py
│   └── retrieval_metrics.py
├── data/docs/*.md
├── static/index.html
├── scripts/start_db.sh
├── scripts/seed_demo.sql
├── scripts/start_phoenix.sh
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

## 关键决策（实现者的判断）

- **可观测用 Phoenix 而不是 LangSmith**：无云 Key、可本地跑、有 LLM trace UI；同时保留 JSONL 日志作为兜底。
- **评测自研小框架，不用 RAGAS**：用户要理解指标怎么算；LLM-as-judge + 纯 Python 检索指标更直观。RAGAS/DeepEval 在 README 里作为生产替代提到。
- **RAG 用 pgvector + BM25 + RRF + LLM rerank**：pgvector 是岗位高频；BM25 用 jieba 解决中文；LLM rerank 避免引入 torch，且能讲清“rerank 的价值与成本”。
- **Postgres 同时存向量、checkpoint、Store**：一个容器，减少基础设施种类；测试用 `InMemorySaver`/`InMemoryStore`，不依赖 DB。
- **FastAPI + 手写 SSE**：不引入 sse-starlette，事件格式自己定义，便于讲清流式原理。
- **手写 supervisor 多 Agent**：不用 `langgraph-supervisor`，为了看清路由、状态和回环。
- **安全用启发式 + 工具策略**：不接商业 guardrails；README 说明生产应加分类模型/规则引擎。
- **保留现有 CLI**：阶段 1/3/4 的能力先在 CLI 演示；API 是阶段 2 的增量，不替换 CLI。
- **不新增前端框架**：一个 HTML 文件 + fetch。
- **3 用户 demo 隔离，而不是完整多租户**：用 stdlib HMAC 签发/校验 token，服务端绑定 `user_id`；不引入 OAuth/JWT 库，但能讲清身份信任边界。
- **MCP 只暴露公共 `search_docs`**：私有 ticket 留在本地工具，通过 runtime context 注入 `user_id`，避免模型伪造身份。
- **语料冻结**：8 篇技术栈文档、27 条 golden（含 4 条不可回答），阶段 1 基线与阶段 3 对比使用同一份；标签由实现者生成，用户抽查。
- **与 `bank-cs-agent` 保持独立**：不复用其银行语料/用户/评测集，避免两个项目的目录、端口、DB 和身份模型耦合。

## 依赖（按阶段分组）

- 现有：`langchain`、`langchain-core`、`langchain-deepseek`、`langchain-ollama`、`langgraph`、`langchain-text-splitters`、`numpy`、`python-dotenv`。
- 阶段 1：`arize-phoenix`、`openinference-instrumentation-langchain`（可能含 OTel 依赖）。
- 阶段 2：`fastapi`、`uvicorn[standard]`、`langgraph-checkpoint-postgres`、`psycopg[binary,pool]`、`httpx`、`pytest-asyncio`。
- 阶段 3：`langchain-postgres`、`psycopg[binary]`、`rank-bm25`、`jieba`。
- 阶段 4：`mcp`、`langchain-mcp-adapters`、`langgraph-checkpoint-postgres`（Store/checkpoint）。
- 依赖按 `uv` 的 dependency groups 或 optional extras 管理，避免一次性安装全部重型包。

## 风险与待验证

- Phoenix 与 LangGraph/LangChain 的自动/手动埋点 API 版本兼容性；失败则退化为 JSONL trace + 简单 HTML 查看器。
- `langchain-postgres` 的 PGVector 与 `langgraph-checkpoint-postgres` 的异步接口；实现前先用小脚本验证。
- MCP 适配器 API 变动；必要时直接用官方 `mcp` client 手写工具调用。
- DeepSeek judge 的一致性/成本；golden set 控制在 24–27 条（当前 27 条），temperature=0，结果缓存。
- Docker Hub 不可直连；镜像通过 `docker.m.daocloud.io`，README 说明可替换。
- 中文 BM25 依赖 jieba 分词；如果效果不好，对比“字符 n-gram + BM25”作为备选。
- demo 身份不是生产方案：README 明确说明生产应使用 OAuth/OIDC/JWT、短期 token、服务端会话和 RBAC；本项目只演示“客户端不能自选 user_id + 资源 owner 校验”。
- 跨用户隔离会增加测试夹具和 ~100–150 行代码；如果时间紧张，优先保证 memory 和 ticket 两条隔离路径可测。

## 成功标准

1. 四个阶段的代码都能在本地跑起来，且每阶段有独立 README 段落和演示命令。
2. `uv run pytest` 离线测试通过；真实 eval/集成测试有明确的跳过/运行方式。
3. `eval/run_eval.py` 能输出可复现的指标报告（含基线 vs 升级后对比）。
4. Phoenix 能看到一次完整问答的 trace。
5. FastAPI SSE + 浏览器页面可用；重启后会话可恢复。
6. MCP 工具、安全测试、长期记忆、多 Agent 都有可演示的最小例子。
7. 3 个合成用户的隔离成立：跨用户 ticket/memory 访问被拒绝，且有测试覆盖。
8. 阶段 1 与阶段 3 使用同一份冻结语料，指标可对比。
9. README 每阶段都有“面试怎么讲”：问题、方案、取舍、指标、失败模式。
