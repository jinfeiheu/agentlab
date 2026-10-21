# LangGraph 状态图

## StateGraph
StateGraph 用状态、节点和边描述工作流。先定义状态结构（通常是 TypedDict），再 add_node 注册节点函数，add_edge 连接固定路径，最后 compile 得到可执行图。节点返回状态的部分更新，图负责把更新合并进全局状态。编译时可以传入 checkpointer 和 store。

## Reducer
Reducer 决定同一个状态键的多次更新如何合并。默认行为是覆盖，后写覆盖先写；用 `Annotated[list, add_messages]` 可以改成追加，这正是 MessagesState 保存多轮消息的方式。选择 reducer 时要明确语义：消息历史应追加，当前计划或计数器通常应覆盖。

## Checkpointer
Checkpointer 是 LangGraph 的状态持久化机制。图在每一个 super-step 结束后，都会把当前状态写成一个 checkpoint，并用 thread_id 作为索引。调用方在 config 里传入 `{"configurable": {"thread_id": "..."}}`，同一个 thread_id 的多次 invoke 就会共享同一条状态历史。状态里通常包含消息列表、节点返回值、下一步要执行的节点，以及中断信息。

有了 checkpoint，工作流可以从上次的位置继续。进程重启、请求超时或人工中断之后，只要 thread_id 不变，再次调用就能恢复上下文；这也让多轮对话不需要应用自己拼接历史。`get_state` 可以读取当前快照和待执行的下一步，`update_state` 可以手工修改状态，配合历史 checkpoint 还能做时间旅行，从某个旧版本重新分支执行。

Checkpointer 只负责短期状态，不负责长期知识。`InMemorySaver` 把 checkpoint 放在进程内存里，适合测试和单机演示，进程退出就丢失；`PostgresSaver` 把 checkpoint 写入 Postgres，适合服务化部署和多实例共享。选择持久化后端时要考虑并发、清理策略和敏感数据，thread_id 也必须由服务端根据用户身份生成，不能直接信任客户端传入的值。

Checkpointer 与 HITL 的关系很紧密：`interrupt` 暂停时，当前状态正是靠 checkpoint 保存下来的；没有 checkpointer，恢复时就找不到中断点。它也不能替代 Store：checkpoint 保存的是某个会话的执行现场，Store 保存的是跨会话的用户偏好和事实。前者按 thread_id 隔离，后者通常按 `("user", user_id)` 命名空间隔离，两者解决的问题不同。

## 条件边与循环
add_conditional_edges 根据状态决定下一步走向，是实现分支和循环的核心。ReAct 模式就是 agent 节点判断是否调用工具：有 tool_calls 走 tools 节点，没有则结束；tools 执行完再回到 agent。tools_condition 是 LangGraph 提供的现成判断函数。

## ToolNode 与工具调用
ToolNode 接收工具列表，读取 AIMessage 中的 tool_calls，逐个执行并返回 ToolMessage。工具结果会带着对应的 tool_call_id 回到消息历史，模型据此继续推理。ToolNode 支持 wrap_tool_call 钩子，可在执行前后做权限校验、日志或结果改写。

## 中断与 HITL
interrupt(value) 会在节点内暂停图，并把 value 暴露给调用方；状态由 checkpointer 保存。调用方确认后用 Command(resume=answer) 继续，interrupt 的返回值就是 answer。这个机制适合发送邮件、下单、删数据等需要人工确认的高风险操作。
