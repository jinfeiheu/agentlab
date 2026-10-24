# 记忆与多 Agent

## 短期与长期记忆

checkpointer 保存单个 thread 的执行现场,属于短期记忆;Store 保存跨会话的用户事实、偏好和 episode,属于长期记忆。两者命名空间和生命周期不同,不能互相替代。

## 记忆类型

profile 保存姓名、角色等稳定属性;preference 保存颜色、语言等偏好;fact 保存用户陈述的事实;episode 保存压缩或会话结束时生成的对话摘要。

## 抽取触发

自动抽取只在用户消息命中规则(例如“我叫”“我喜欢”“记住”)时调用模型。用户显式调用 save_memory 时跳过自动抽取,避免同一事实写两次。

## 记忆检索

search_memory 默认按语义相似度返回前 3 条;它只搜索当前 user_id 的命名空间,不会跨用户检索。

## 去重与保留

写入前先做语义搜索,再用 SequenceMatcher 比较,相似度不低于 0.9 视为重复并合并到已有 key。episode 默认保留 30 天,profile、fact 和 preference 没有 TTL。

## 记忆隔离

记忆命名空间包含 user_id,用户 A 的搜索结果不会包含用户 B 的数据。bob 询问 alice 的姓名时应回答不知道。

## 多 Agent 分工

researcher 负责检索并写 research_notes;writer 基于笔记生成带引用的 draft;critic 用结构化输出判断是否忠实;supervisor 根据状态选择下一个节点。

## 多 Agent 限制

多 Agent 模式不绑定工具、不做上下文压缩,也不注入用户画像;它与单 Agent 模式共享 checkpointer 和 Store。critic 调用失败时默认 faithful=true,避免无限重试。
