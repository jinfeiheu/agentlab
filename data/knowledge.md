# LangChain × LangGraph 技术栈速览

## 1. LangChain 是什么

LangChain 是构建大模型应用的框架。核心抽象在 langchain-core 里,包括消息、提示词、模型、工具、检索器和 Runnable/LCEL。上层 langchain 包提供智能体等高层组件,各模型和向量库通过独立适配包接入,例如 langchain-deepseek、langchain-ollama。

## 2. LangGraph 是什么

LangGraph 是构建有状态、可循环智能体的编排运行时。开发者用 StateGraph 定义状态、节点和边,用条件边控制 agent 与工具之间的循环。LangChain 1.x 的 create_agent 也构建在 LangGraph 之上。

## 3. Checkpointer 与多轮记忆

Checkpointer 在每一步保存图的状态,按 thread_id 区分会话,因此同一个 thread_id 的后续调用能读到之前的消息。它还支持断点续跑和时间旅行。生产环境常用 SqliteSaver 或 PostgresSaver,学习示例用 InMemorySaver。

## 4. 工具调用与 ReAct 循环

模型通过 tool calling 返回工具名和参数,图把消息交给 ToolNode 执行工具,工具结果再回到模型,直到模型不再调用工具。这个循环就是常见的 ReAct 模式。calculator、search_knowledge、send_report 都是这里的工具。

## 5. RAG 流程

RAG 先加载文档,用文本切分器切成块,再调用嵌入模型得到向量并存入向量库。用户提问时,用问题向量检索最相似的片段,把片段拼进上下文交给大模型回答。本项目用 bge-m3 生成 1024 维向量,用 InMemoryVectorStore 存储。

## 6. 流式输出

LangGraph 的 stream 支持多种模式。messages 模式逐 token 输出模型内容,updates 模式输出每个节点的状态更新,例如工具调用和工具结果。多种模式可以组合使用,实现打字机效果并展示执行过程。

## 7. LangSmith 观测

LangSmith 提供追踪、评估、数据集和 Prompt 管理。设置 LANGSMITH_TRACING=true 和 LANGSMITH_API_KEY 后,LangChain/LangGraph 的调用会自动上报,无需改业务代码。没有 Key 时项目照常运行,只是没有追踪。

## 8. 本项目的模型与嵌入

对话模型使用 DeepSeek 的 deepseek-chat,通过 langchain-deepseek 接入。DeepSeek 不提供 embedding 接口,所以嵌入使用本地 Ollama 部署的 bge-m3,输出 1024 维向量。两者分工:DeepSeek 负责生成和工具调用,bge-m3 负责语义检索。
