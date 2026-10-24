# AgentLab RAG 管线(当前版本)

## 管线概览

AgentLab 的 RAG 链路分为摄入、检索和生成三段:摄入把 Markdown 切成稳定 chunk 并写入 pgvector;检索同时走向量与 BM25;生成由 agent 根据工具返回的证据作答并标注来源。

## 切分参数

当前默认 chunk_size=400 字符,chunk_overlap=100 字符。先按 Markdown 标题切小节,超长小节再递归切分。稳定 chunk_id 格式为 source::index。

## 检索参数

当前 RAG_TOP_K=6;候选池由向量检索与 BM25 各取 8 条,再用 RRF 融合,RRF 常数 k=60。混合检索是默认路径。

## 重排参数

当前默认使用专用 cross-encoder BAAI/bge-reranker-v2-m3,top_n=3,运行在 CPU。首轮加载模型约需数秒,之后 6 个候选的重排耗时约 300 毫秒。可选的第二层 LLM rerank 默认关闭。

## 嵌入模型

当前嵌入模型为 Ollama 本地 bge-m3,向量维度 1024。嵌入不调用外部 API,没有按 token 计费。

## 版本变更

RAG v2 于 2026-08-15 上线,替代 2026-03-01 的 v1。v1 的切分、检索参数已废弃,只能用于历史审计。

## 已知限制

中文长表格在按 Markdown 标题切分后仍可能被截断;跨表格的多跳问题需要同时检索多个片段。扫描版 PDF 不在语料范围内。
