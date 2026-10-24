# LangGraph 运行时与状态

## Checkpointer 表结构

Postgres checkpointer 使用三张表:checkpoints 保存每个 thread 的最新检查点,checkpoint_blobs 保存序列化状态,checkpoint_writes 保存待提交的写入。thread_id 由 user_id:session_id 组成。

## Checkpoint 保留策略

checkpoint 数据默认保留 90 天,由运维脚本每周清理;清理只删除超过保留期的 thread,不影响 Store 中的长期记忆。

## Store 命名空间

长期记忆按 ("user", user_id, type) 分命名空间,type 取 profile、fact、preference 或 episode。查询画像时使用前缀 ("user", user_id) 搜索。

## 上下文压缩

当消息估算 token 达到 CONTEXT_MAX_TOKENS 的 80% 时触发压缩。默认 CONTEXT_MAX_TOKENS=6000,即约 4800 token 触发。压缩会保留最近约 50% 的消息,其余旧消息摘要后用 RemoveMessage 删除。

## 压缩的持久化

压缩摘要写入 state.summary,并随 checkpoint 持久化;下一次模型调用会把它拼进 system prompt。原始旧消息在压缩后不再保留。

## 多 Agent 路由

多 Agent 图由 supervisor、researcher、writer、critic 四个节点组成,最大步数 MAX_STEPS=6。路由顺序为 researcher → writer → critic;critic 判定不忠实且未到上限时回到 writer。

## HITL 恢复

send_report 通过 interrupt 暂停,resume 在同一 thread 上继续。同一个 interrupt 只能恢复一次,第二次恢复返回 409。POST /chat/resume 需要 Bearer token。
