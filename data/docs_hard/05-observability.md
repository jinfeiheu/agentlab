# 可观测性与 Trace

## OTLP 配置

应用通过 OTLP HTTP 导出到 Phoenix,端点 http://localhost:6006/v1/traces。只有 TRACING_ENABLED=true 时才导出,默认关闭。本地 Phoenix 用 scripts/start_phoenix.sh 启动。

## Span 结构

一次问答通常产生 LangGraph、agent、ChatDeepSeek、search_docs 等 span。检索工具、模型调用与 rerank 各自有独立 span,可以按 thread_id 过滤整条链路。

## 批处理与刷新

生产路径使用 BatchSpanProcessor,默认 schedule_delay_millis 为 5000 毫秒。进程退出前必须调用 shutdown_tracing,否则最后一批 span 可能丢失。

## 成本计算

deepseek-flash 按每百万 token 计费:输入 2 元,输出 8 元。一次 1000 输入 + 500 输出的调用成本为 0.006 元。本地 bge-m3 不按 token 计费。对话模型默认 deepseek-flash,裁判默认使用同一模型。

## 关键指标

报告记录 p50/p95 延迟、总 token、总成本、平均检索次数。延迟只统计一轮图执行的墙钟时间,不包含评测脚本启动和模型加载。

## 常见排查

Phoenix 看不到 trace 时依次检查 TRACING_ENABLED、PHOENIX_ENDPOINT、网络连通性和是否调用了 shutdown_tracing。只有 API 进程启动 tracing 时,CLI 不会自动导出。
