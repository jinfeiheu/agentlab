# 可观测性

## Trace 与 Span
Trace 表示一次完整请求，span 表示请求中的一个步骤，多个 span 组成树状结构。一次问答通常包含检索、模型调用、工具执行等 span，每个 span 记录开始时间、耗时、状态和属性。通过 trace 可以看到时间花在哪一步，以及错误发生在哪一层。

## OpenTelemetry
OpenTelemetry 是厂商中立的可观测标准，提供 API、SDK 和 OTLP 协议。应用创建 TracerProvider，配置 exporter 把 span 发送到后端；开发时可用 BatchSpanProcessor，测试时可用内存 exporter。属性值要控制基数和敏感信息，不要把完整用户输入直接写入。

## OpenInference
OpenInference 为 LLM 应用定义 span 语义约定，例如模型名、token 数、提示和工具调用。LangChainInstrumentor 可以自动给 LangChain/LangGraph 的模型和工具调用埋点，减少手写代码。自动埋点之外，检索和 rerank 等自定义步骤仍建议手动加 span。

## Phoenix
Arize Phoenix 是本地可运行的 LLM trace UI，默认在 6006 端口提供界面和 OTLP 接收端。应用把 span 导出到 `http://localhost:6006/v1/traces`，打开浏览器就能按 trace 查看模型输入输出、工具调用和耗时。它不需要云账号，适合学习和本地调试。

## 关键指标
可观测性不只记录 trace，还要聚合指标：请求量、错误率、P50/P95 延迟、首 token 延迟、输入输出 token 和估算成本。指标用于发现趋势和告警，trace 用于定位单次失败。两者结合才能回答“是否变慢”和“为什么变慢”。

## 隐私与采样
trace 可能包含用户输入、检索片段和工具结果，属于敏感数据。生产环境应做 PII 脱敏、限制属性长度、设置保留期，并通过采样控制成本。调试时可以临时提高采样率，但不要把含密钥或身份证号的原始内容写入 span。
