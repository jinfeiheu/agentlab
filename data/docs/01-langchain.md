# LangChain 核心概念

## 模型与消息
LangChain 用 ChatModel 统一不同厂商的对话模型。输入输出都是消息对象：HumanMessage 表示用户，AIMessage 表示模型回复，SystemMessage 设置角色，ToolMessage 承载工具结果。调用方式有 invoke（同步）、ainvoke（异步）和 stream（流式）。切换供应商通常只需换模型类，消息与调用代码保持不变。

## Prompt 与 LCEL
ChatPromptTemplate 把系统提示、历史消息和用户输入组织成消息列表，MessagesPlaceholder 用于插入多轮历史。LCEL 用管道符 `|` 把 Runnable 串起来，前一个的输出作为后一个的输入，例如 prompt | model | parser。所有 Runnable 都支持 invoke、batch、stream 和对应的异步方法。

## 工具定义
用 `@tool` 装饰普通函数即可定义工具。函数名是工具名，docstring 会作为工具描述发给模型，类型注解生成参数 schema。模型通过 bind_tools 看到工具列表，并以 tool_calls 的形式返回要调用的工具名和参数；真正的执行由应用或 LangGraph 的 ToolNode 完成。

## 结构化输出
`with_structured_output(PydanticModel)` 让模型按给定 schema 返回结构化对象，而不是自由文本。LangChain 会生成 JSON schema、解析模型输出并做校验，失败时抛出异常。它适合分类、打分、信息抽取等场景，评测中的 LLM-as-judge 常用这种写法。

## 流式输出
流式接口 stream/astream 逐块返回结果。对话模型通常返回 AIMessageChunk，多个 chunk 可以相加合并。流式适合终端和网页的逐字显示，但工具调用参数也可能分块到达，需要按完整消息聚合后再执行。

## 异步与批处理
ainvoke、abatch 和 astream 提供异步接口，适合 FastAPI 这类高并发服务。batch 会把多个输入并发处理，可通过 max_concurrency 限制并发度。同步接口在异步服务里会阻塞事件循环，应在请求处理函数中使用异步版本。
