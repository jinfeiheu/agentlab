# 面试口述稿

> 用法：每个主题先讲“问题”，再讲“方案与取舍”，最后用一个数字或失败案例收尾。数字来自 2026-10-24 的本地运行，复现时以 `eval/results/*.json` 为准。

## 60 秒项目介绍

- 这是一个中文 RAG / Agent 项目，不是单轮 demo：有 CLI、FastAPI/SSE、pgvector、混合检索、重排、评测、Phoenix trace、MCP、安全、长期记忆和多 Agent。
- 四阶段：先把评测和可观测做出来，再服务化，再升级检索，最后加 MCP/安全/记忆/多 Agent。
- 两个数据集：easy 27 条冻结回归，hard 100 条覆盖单跳、多跳、时间/版本、歧义、不可回答和表格。
- 核心结果：easy 接近饱和(task_success 0.96–1.0)；hard 0.83–0.89；closed-book 的 answerable_success 只有 3.5%(open-book 81.2%)，说明检索有实际贡献。
- 我关注的不只是“分数”，还有失败模式：歧义题 0.30、多跳 0.76、表格 0.80，以及不同裁判模型的偏差。

## 1. 为什么用 LangGraph

- 问题：纯 LCEL 链适合线性流程，但 Agent 需要“模型决定是否调工具、工具结果回到模型”的循环。
- LangGraph 用显式状态图和条件边表达这个循环：`agent → tools → agent`，终止条件清楚。
- checkpointer 按 `thread_id` 保存每一步状态，才能做多轮、断点续跑、HITL 和时间旅行。
- HITL 用 `interrupt()` 暂停、`Command(resume=...)` 恢复；恢复和重置是两种不同语义，必须显式设计。
- 取舍：手写图比 `create_agent` 多写代码，但每个节点、边、状态键都可解释；`--simple` 保留高层写法做对照。
- 数字/案例：同一张图既跑 CLI 又跑 API/SSE，HITL 在 API 里重启后还能 resume。

## 2. 评测：golden set、judge 偏差、指标定义

- 问题：没有 golden set，“回答变好”只能靠感觉；没有分层，平均值会掩盖失败类别。
- easy 27 条(4 条不可回答)冻结做回归；hard 100 条只追加，六类各 10–30 条，带 `reference_answer`。
- hard 语料是合成的 AgentLab 文档世界：HNSW 参数、90 天保留期、历史成本等是刻意放置的版本冲突/噪声，不是本仓库真实配置；hard 指标衡量文档世界里的检索与推理，不是代码审计。
- 指标：Recall@3/MRR/nDCG@3 看检索；correctness/faithfulness/citation_support 看生成；`answerable_success=correctness≥4`，开卷 task_success 还要求 citation_support，闭卷只看 correctness。
- 不可回答题不能只看“有没有说无法回答”：还要 faithfulness≥4，拒答后继续编造同样算失败。
- 分母要分开：answerable_success/tool_accuracy/citation_support 只算可回答题，refusal_rate 只算不可回答题；tool_accuracy 用“必需工具子集”，额外安全工具不扣分。
- judge 只使用 agent 实际检索到的 ToolMessage，不把预取 top-k 算进 citation；否则 citation_support 会被虚高。
- judge 偏差：同一套 hard baseline，DeepSeek 裁判 task_success 0.83 / correctness 4.45，qwen3.5:4b 是 0.86 / 4.12；qwen 对引用更宽松、对正确性更严格。
- 结论：跨模型对照、人工抽查、分层报告三者缺一不可；单模型 judge 的绝对值不能当真理。

## 3. RAG：chunking、混合检索、RRF、rerank、引用

- chunking：先按 Markdown `##` 切小节，再对超长小节递归切；`chunk_id=source::index` 保证稳定，评测标签才能复用。
- 问题：纯向量对专有名词、版本号、表格不敏感；BM25 对这些词更强。
- 方案：向量和 BM25 各取 8 条，RRF(k=60)融合取 6；再用 bge-reranker-v2-m3 cross-encoder 重排取 3。
- RRF 只看排名不看分数，避免两路分数量纲不同；常数 k 控制头部权重。
- rerank 的输入要把 `source#section` 拼进文本，否则短片段和章节语义丢失；实测 q02 的相关片段从第 5 名升到第 1 名。
- 引用：回答必须标 `[来源:文件#章节]`；judge 检查引用是否被工具证据支持，另有 citation_precision 做标签级统计。
- 数字：easy R@3 0.8696→0.9130，MRR 0.8188→0.8623；hard MRR 0.8490→0.8878。rerank 把 citation_precision 提到 0.9412，但本轮 task_success 0.83 低于 hybrid 的 0.86，p50 增加约 0.75 秒——收益要用更多样本验证。
- 取舍：检索指标衡量预取管线，rerank 只作用于 agent 证据，所以两套指标的归因要分开说。

## 4. 可观测：trace 里看什么、如何定位失败

- 一次问答的 span：LangGraph → agent → ChatDeepSeek → search_docs → rerank；工具和模型调用各有独立 span。
- 先按 `thread_id` 过滤整条链路，再看每轮模型输入、tool_calls、工具返回和最终回答。
- 定位顺序：回答错 → 看 tool 返回是否有正确证据；证据错 → 看检索 query 和 rerank 排序；query 错 → 看模型为什么改写；都没有 → 看 prompt/上下文。
- token、成本、p50/p95 都从消息的 usage 和 recorder 汇总；成本按 deepseek-flash 输入 2 元/输出 8 元每百万 token 估算。
- 坑：BatchSpanProcessor 默认 5 秒才导出，进程退出必须 `shutdown_tracing()`，否则最后一批 span 丢失。
- 坑：API 早期没有初始化 tracing，Phoenix 里看不到；现在 lifespan 里 setup/shutdown，CLI 用 try/finally。
- 安全：span 属性不放原始用户输入，PII 先脱敏。

## 5. 服务化：SSE、超时、限流、会话、线程 ID

- FastAPI + `StreamingResponse`，事件类型：token、tool_call、tool_result、interrupt、error、done。
- `thread_id = user_id:session_id`，user_id 来自 JWT，不能由请求体指定；同一 thread 用 `asyncio.Lock` 串行，避免并发交错 checkpoint。
- SSE 断连用 `request.is_disconnected()` 和 `asyncio.CancelledError` 清理；图异常转成 error 事件，不让连接挂起。
- 超时用 `asyncio.wait_for` 包住一轮；限流是每用户每分钟 30 次的内存滑动窗口，超限 429。
- HITL：中断后 `/chat/resume` 或 `/chat/stream/resume` 恢复；没有 pending interrupt 返回 409，第二次 resume 也返回 409。
- 坑：中断/并发会留下 assistant tool_calls 没有对应 ToolMessage，LangGraph 直接 400；现在每轮前补齐或重置，保证不 400。
- 取舍：限流是单进程内存计数，生产要换 Redis/网关；超时和取消是两套路径，需要测试覆盖。

## 6. 身份与安全：token 边界、跨用户隔离、prompt injection、PII

- 身份只从服务端校验后的 HS256 JWT 读取；请求体伪造 user_id 无效；thread_id 和记忆命名空间都带 user_id。
- 工单只允许 owner 查询，跨用户统一返回“未找到或无权限”，不泄露工单是否存在。
- prompt injection 在进入图之前拦截：忽略之前指令、system prompt、泄露提示词、你现在是等模式；命中不调用模型。
- PII 在日志、SSE 工具参数/结果、trace span 属性统一脱敏：`[EMAIL]`、`[PHONE]`、`[ID]`、`[CARD]`。
- 工具白名单 9 个；`ensure_tools_allowed()` 在构建图时做漂移检查，未知工具在 ToolNode 返回拒绝消息。
- 取舍：demo 密码在内存、JWT 只签名不加密、限流是单进程；生产要换密钥轮换、HTTPS、真实用户库和分布式限流。
- 测试：跨用户 ticket/memory、注入、PII、未知工具、伪造 user_id 都有离线测试。

## 7. MCP：server/client、权限边界

- 两个 server：`agentlab` 暴露 search_docs/list_sources/doc_stats，`utils` 暴露 calculator/word_count；全部公共、只读。
- 默认 stdio：客户端拉起子进程，不占端口；需要多客户端/跨机器时用 streamable HTTP，8811/8812。
- `mcp_client.py` 用 MultiServerMCPClient 聚合两个 server，能发现 5 个工具并调用。
- `USE_MCP=true` 时 API 用 MCP 的 search_docs+calculator，缺一个就启动失败；ticket/memory/send_report 留在本地。
- 权限边界：MCP 不暴露私有数据、不暴露写操作；HTTP 模式必须自己加 TLS、Bearer/OAuth 和限流。
- 什么时候不该用 MCP：只有一个工具、只在一个进程里调用时，本地函数更简单、更快、类型更安全。
- 取舍：MCP 的价值是协议边界/多客户端/多 server 聚合，不是“工具数量”。

## 8. 记忆：短期/长期、命名空间、遗忘

- 短期：checkpointer 保存单个 thread 的执行现场；长期：Store 保存跨会话的 profile/fact/preference/episode。
- 命名空间 `("user", user_id, type)`；查询画像用前缀搜索；用户 A 的搜索结果不会包含用户 B。
- 写入：规则命中的消息才调用抽取模型，避免每轮多一次调用；显式 save_memory 时跳过自动抽取。
- 去重：先语义搜索，再用 SequenceMatcher 比较，相似度 ≥0.9 合并到已有 key。
- 遗忘：episode 默认 TTL 30 天；profile/fact/preference 没有 TTL，需要后续加容量/衰减策略。
- 压缩：上下文到 `CONTEXT_MAX_TOKENS` 的 80% 时，把旧消息摘要进 `state.summary` 并删除旧消息；摘要随 checkpoint 持久化。
- 坑：InMemoryStore 没有 TTL；CLI 的长期记忆只在进程内；跨重启要用 API + `USE_DB=true`。
- 取舍：自动记忆默认关闭；`--simple`/`--multi` 不注入画像或不做压缩。

## 9. 多 Agent：supervisor 的收益与代价

- 图：supervisor → researcher → writer → critic → supervisor/END；MAX_STEPS=6。
- researcher 负责检索和笔记，writer 负责带引用草稿，critic 用结构化输出判断忠实，supervisor 用 `Command(goto=...)` 路由。
- 收益：职责分离，每一步可观测、可单独评测；适合“检索→写作→审阅”这类流程。
- 代价：多一跳模型调用；状态字段多；critic 失败要设默认值，否则可能无限循环。
- 坑：writer 每轮必须清空旧 review，否则 supervisor 会一直回到 writer；CLI 每轮开始要重置 research/draft/review/steps。
- 取舍：多 Agent 不绑定工具、不做压缩/画像注入，和单 Agent 共享 checkpointer/Store；它不是单 Agent 的替代品。
- 数字：CLI 实测 supervisor → researcher → writer → critic → __end__，草稿带 `[来源:02-langgraph.md#Checkpointer]`。

## 9.1 数据分析 Agent：single vs multi 的 A/B 结论

- 我先做单 Agent 显式状态机，再做多 Agent：Supervisor → Scout → SQL Analyst → Critic → Reporter，`Command(goto=...)`，`MAX_STEPS=6`。多 Agent 的 Critic 默认 fail-closed，Reporter 不执行 SQL。
- 50 条 golden（40 answer / 5 clarify / 5 refuse）上做单/多/auto A/B：single 1.000、multi 0.980、auto 1.000；复杂子集都是 17/17。
- multi 没有提升，但 P95 8.37s → 14.23s（+70%）、平均步骤 0.8 → 3.5、平均成本 ¥0.00558 → ¥0.00638（+14.5%）。所以默认 single，multi 只保留为可选深分析模式。
- multi 的 0.98 不是“多 Agent 更差”，而是 forced multi 让 Scout 重新判意图，一条“上个月退款情况如何”从 clarify 漂移成 answer；auto 先把 clarify/refuse 留在 single，所以 auto 仍是 1.000。
- 另一个真实失败：AnswerOutput 解析返回 null，整个请求变成 error。修复是 answer 节点兜底——保留已查到的 result，用确定性文字回答；这比为了“解释好看”丢掉正确答案更合理。
- 成本守卫：`EXPLAIN` 成本超阈值走 `interrupt`；没有 checkpointer/thread_id 时 fail closed，直接拒绝执行，不静默返回空状态。
- Prompt 版本放 `configs/analytics/prompts/*.yaml`，每个版本带 model id；审计和 span 都记录 `prompt_version`/`model_id`。回滚只改环境变量 `ANALYTICS_PROMPT_UNDERSTAND_VERSION=v2`，不改代码。
- 另有请求级模型调用预算（`ANALYTICS_REQUEST_BUDGET` / `ANALYTICS_MODEL_CALL_COST`）：超预算返回可读答案、审计 status=budget，不把预算问题变成 500。
- API：`/analytics/chat` 返回 answer/sql/rows/chart_spec/audit_id；`/analytics/chat/stream` 发 `plan_created → step_* → verification/replan → final`；租户由 token 映射，请求体带其他 tenant_id 返回 403；`/analytics/cancel` 取消当前 asyncio 任务。
- 多轮：会话按 `user_id:session_id` 隔离，追问复用上一轮 metrics/dimensions/time_range；上下文超 `ANALYTICS_SESSION_MAX_CHARS` 时丢最旧轮次，避免 prompt 无界增长。
- 结论：多 Agent 不是默认，是数据证明后的路由选择。要让 multi 成为默认，必须在复杂子集上看到 ≥5 个百分点的提升，并覆盖它增加的延迟/成本。

## 10. 失败案例(真实调试故事)

### 10.1 悬空 tool_call 导致 400

- 现象：页面多次工具调用/中断后报 `assistant message with tool_calls must be followed by tool messages`。
- 根因：中断或并发留下 assistant tool_calls，但对应 ToolMessage 没写入 checkpoint。
- 修复：每轮前 `_prepare_thread` 检查未完成 tool_calls，能补就补 ToolMessage，不能修复就删除线程；同 thread 加 `asyncio.Lock`。
- 教训：checkpoint 里也可能有“不合法”的历史；恢复逻辑必须防御历史遗留状态。

### 10.2 q18 的引用超出工具证据

- 现象：easy 集 q18 回答正确但 citation_support=false，task_success 失败。
- 根因：回答里加了“降采样不等于脱敏/按环境动态调整”等工具片段没有的事实；judge 只看 ToolMessage 证据。
- 修复：把 judge contexts 限定为 agent 实际 ToolMessage，预取 top-k 只用于检索指标；q18 在早期运行中失败，当前 easy baseline 已通过，但保留为回归案例。
- 教训：引用支持率是“回答 vs 证据”的约束，不是“回答看起来合理”的评分。

### 10.3 PostgresIndexConfig 导入路径

- 现象：Task 14 集成测试报 `ImportError: PostgresIndexConfig`。
- 根因：从 `langgraph.store.postgres` 根包导入，实际在 `langgraph.store.postgres.aio`。
- 修复：改导入路径；集成测试显式开启，离线测试不会掩盖。
- 教训：第三方库的公开导入路径要跑真实集成测试验证，不能只靠类型提示。

### 10.4 裁判模型缺字段与跨模型偏差

- 现象：qwen3.5:4b 在 hard-hybrid 有 1 条输出缺少 `reason`，`JudgeResult` 校验失败，走了安全默认 0 分。
- 根因：小模型不总是严格按 schema 输出；`judge_answer` 设计成失败返回 `JudgeResult(0,0,False,"judge failed: ...")`，保证评测不中断。
- 影响：该条是不可回答题，task_success 由拒答检测决定，指标不受影响；但 faithfulness 被记为 0。
- 更大的发现：DeepSeek 与 qwen3.5:4b 对同一 hard baseline 的 task_success/correctness 结论不同，说明 judge 本身是测量误差来源。
- 教训：schema 失败要安全降级；跨模型对照 + 人工抽查比单一 judge 可信。

### 10.5 easy 集饱和后加 hard 集

- 现象：easy 集 task_success 接近 1.0，任何改动都看不出差异。
- 根因：easy 语料干净、问题单跳、答案集中；指标饱和。
- 修复：新增 100 条 hard golden 和独立 docs_hard 语料，覆盖多跳、版本冲突、歧义、干扰证据和表格；easy 冻结不动。
- 结果：hard baseline task_success 0.83，歧义题 0.30，多跳 0.76，表格 0.80，重新有区分度。
- 教训：评测集饱和时先扩难度和失败类别，不要用更多同质样本刷分。

## 11. 如果面试官追问

- **为什么不用更简单的向量检索？** 因为 hard 集的关键词/版本/表格题需要 BM25；RRF 让两路互补，rerank 再把证据压到 3 条。
- **为什么 task_success 要求 citation_support？** 这是 RAG 而不是闭卷问答；没有证据支持的正确答案在生产里不可审计。
- **为什么 hard 只有 0.83 也算成功？** 评测的目的不是刷到 1.0，而是暴露失败类别；0.83 比 easy 的 1.0 更有信息量。
- **怎么证明检索有贡献？** closed-book 消融：同一 hard golden，移除 search_docs 后 answerable_success 从 0.812 掉到 0.035(3/85)。
- **怎么处理 judge 偏差？** 跨模型对照、参考答案 rubric、人工抽查、报告分层；不把单一 judge 的绝对值当结论。
- **生产化还差什么？** 真实用户库/密钥轮换/HTTPS、分布式限流、MCP HTTP 鉴权、hard 集多人标注、置信区间和 CI。
